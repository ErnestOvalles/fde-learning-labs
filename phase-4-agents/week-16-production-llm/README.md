# Week 16: Production LLM Integrations

## Outcome

Take the LLM features from Weeks 9–15 (chatbot, structured output, RAG, agent, multi-turn memory, reliable tool calling, evaluation) and ship them with the safety, observability, and cost discipline real customers require. By the end of this week your LLM endpoints will have:

- A **Redis cache** that short-circuits duplicate calls and drops latency to single-digit ms
- A **token counter** that logs prompt/completion tokens on every call
- A **rate limiter** middleware that protects you from runaway prompts and runaway bills
- A **cost tracker** that attributes spend per request, per user, per day
- **Structured logs** (JSON via `structlog`) that carry `request_id`, `model`, `tokens`, `latency_ms`, `cost_usd`
- A **model fallback chain** (`gpt-4o-mini` → `gpt-3.5-turbo`) that survives a primary-model outage
- **Prompt version pinning** so a system-prompt edit cannot silently change downstream behaviour
- A **deprecation checker** that fails loudly when a configured model is scheduled for retirement
- A **`/health`** endpoint that reports liveness, Redis liveness, and the active model
- A small pytest suite that proves the non-LLM machinery works without hitting the OpenAI API
- An **ops runbook** the next on-call engineer (probably you, in three months) can follow

You should be able to look at one log line and answer: *who* called, *with what prompt version*, *how much it cost*, *how long it took*, and *whether it came from cache*.

## Setup Checklist

- [ ] Reuse the OpenAI client from Week 9 and the agent from Week 14
- [ ] Have an OpenAI API key in `.env` (never commit it)
- [ ] Have Docker (or `podman`) running locally — you need Redis on a known port
- [ ] `uv add redis slowapi structlog tiktoken tenacity httpx pytest pytest-asyncio freezegun`
- [ ] Confirm `uv run python -c "import redis, tiktoken, structlog, slowapi; print('ok')"`
- [ ] Start a local Redis: `docker run -d --name redis-week16 -p 6379:6379 redis:7-alpine`

### Setup Walkthrough

```bash
cd phase-4-agents/week-16-production-llm
uv init
uv python pin 3.13

uv add openai redis slowapi structlog tiktoken tenacity httpx
uv add --dev pytest pytest-asyncio freezegun ruff mypy

# Sanity-check the toolchain
uv run python - <<'PY'
import redis, tiktoken, structlog, slowapi
print("redis:", redis.__version__)
print("tiktoken:", tiktoken.__encoding_for_model("gpt-4o-mini").name)
print("structlog:", structlog.__version__)
print("slowapi:", slowapi.__version__)
PY
```

```bash
# .env (do not commit)
OPENAI_API_KEY=sk-...
REDIS_URL=redis://localhost:6379/0
PRIMARY_MODEL=gpt-4o-mini
FALLBACK_MODEL=gpt-3.5-turbo
DAILY_BUDGET_USD=5.00
```

```bash
# Start Redis in the background
docker run -d --name redis-week16 -p 6379:6379 redis:7-alpine
docker ps | grep redis-week16   # confirm it's up

# Smoke-test Redis
uv run python -c "import redis; print(redis.from_url('redis://localhost:6379/0').ping())"
```

By the end of this setup you should have a project that imports cleanly, talks to Redis, and can count tokens with `tiktoken` — three of the four pillars of this week.

## Learning Path (60–90 minutes)

**Best approach:** Production hardening is mostly about *measurement and defaults*, not exotic libraries. Build the thinnest possible wrapper around the OpenAI client, then layer caching, rate limiting, and logging on top of it. Every layer adds latency, cost, or failure modes — every layer is *worth it* because the alternative is silent bills and silent breakage.

### Learn in this order

1. **Token economics** — what a token is, how `tiktoken` counts them, how pricing maps to tokens, why you should *always* log both counts
2. **Caching shape** — key design (model + prompt version + messages hash + temperature), TTL tradeoffs, invalidation strategy
3. **Rate limiting** — fixed window vs. sliding window vs. token bucket, where to enforce (middleware vs. inside the call)
4. **Exponential backoff** — `tenacity` retries with jitter, when to retry (5xx, 429), when *not* to (4xx except 429)
5. **Fallback chains** — primary, secondary, default; what to log; how to expose the active model
6. **Structured logging** — `structlog` JSON renderer, request_id propagation, what to put on every log line
7. **Cost attribution** — per-request rollup, daily budget alert, where to store the rollup (Redis counter)
8. **Prompt version pinning** — treat the system prompt as code; a model + version pair is the cache key
9. **Deprecation lifecycle** — the OpenAI retirement page, `is_model_deprecated()` checks at startup
10. **Observability primitives** — what to log, what to chart, what to alert on

### Free Resources

- [OpenAI Usage & Pricing](https://platform.openai.com/docs/pricing) — the source of truth for what you pay
- [`tiktoken` README](https://github.com/openai/tiktoken) — the encoder for OpenAI models
- [`structlog` Docs](https://www.structlog.org/) — JSON logging cookbook
- [Redis Caching Patterns](https://redis.io/docs/manual/client-side-caching/) — TTL, eviction, namespacing
- [`slowapi` README](https://github.com/laurents/slowapi) — Flask-style rate limiting for Starlette/FastAPI
- [`tenacity` Docs](https://tenacity.readthedocs.io/) — retry strategies, jitter, exception filters
- [OpenAI Deprecations](https://platform.openai.com/docs/deprecations) — which models are going away when
- [Anthropic: Production LLM Patterns](https://docs.anthropic.com/en/docs/intro) — useful priors on cost and latency

**Tip:** Every layer in this lab exists to make a *future failure* visible. Caching prevents the failure of "we re-billed the same prompt 10k times". Rate limiting prevents "one user spent our entire budget". Logging prevents "we have no idea why this answer changed". Pick the failure that scares you most — that is the layer to write first.

## Micro-Exercises (45–60 minutes)

Create `practice.py` at the root of the week folder and work through these. None of them hit the OpenAI API — they build the primitives you will compose in the Main Lab.

### Exercise 1 — Redis cache get/set with a TTL

```python
# practice.py
import json, hashlib, redis

r = redis.from_url("redis://localhost:6379/0")

def cache_get(key: str):
    raw = r.get(key)
    return json.loads(raw) if raw else None

def cache_set(key: str, value: dict, ttl_s: int = 3600) -> None:
    r.set(key, json.dumps(value), ex=ttl_s)

cache_set("greet:hello", {"text": "hi"}, ttl_s=60)
print(cache_get("greet:hello"))   # {'text': 'hi'}
print(cache_get("greet:missing")) # None
```

**Step-by-step:**
1. `r.set(key, value, ex=...)` sets a value with an expiry in seconds — the simplest form of a TTL.
2. `r.get(key)` returns bytes (or `None`); `json.loads` round-trips dicts cleanly.
3. Prefix every key with a namespace (`greet:` here, `llm:` in the lab) so you can `KEYS llm:*` or `FLUSHDB` selectively.
4. Try `r.ttl("greet:hello")` — it should be a positive integer counting down.

### Exercise 2 — Build a stable cache key from model + prompt version + messages

```python
import hashlib, json

def hash_call(model: str, prompt_version: str, messages: list[dict],
              temperature: float) -> str:
    payload = json.dumps(
        {"model": model, "prompt_version": prompt_version,
         "messages": messages, "temperature": temperature},
        sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]

key = hash_call(
    model="gpt-4o-mini",
    prompt_version="router-v1",
    messages=[{"role": "user", "content": "hi"}],
    temperature=0.0,
)
print(key)  # 32-char deterministic string
```

**Step-by-step:**
1. The cache key must change when *any* of the call inputs change — model, system-prompt version, messages, or temperature.
2. `sort_keys=True` and `separators=(",", ":")` make the JSON canonical so a logical-equivalent dict always hashes the same.
3. Truncate to 32 chars — collisions are still astronomically unlikely and 32 chars is a friendlier key in `redis-cli`.
4. Same inputs produce the same key (run the snippet twice); change temperature and the key changes.

### Exercise 3 — Count tokens with `tiktoken`

```python
import tiktoken

def count_tokens(model: str, messages: list[dict]) -> dict:
    enc = tiktoken.encoding_for_model(model)
    per_message = 4  # every message carries ~4 framing tokens
    total = 0
    for m in messages:
        total += per_message + len(enc.encode(m["content"]))
    total += 2  # assistant priming
    return {"prompt_tokens": total, "completion_tokens": 0, "total": total}

print(count_tokens("gpt-4o-mini",
                   [{"role": "system", "content": "You are brief."},
                    {"role": "user",   "content": "Say hi in one word."}]))
```

**Step-by-step:**
1. `encoding_for_model()` returns the BPE encoding the *billing* uses — counting with the wrong encoder is a common source of cost surprises.
2. The `+4` per message and `+2` priming are from the OpenAI cookbook; if you skip them, your counts are systematically low by ~2 tokens per turn.
3. This is the **estimate** before the call. The *real* token counts come back in `usage.prompt_tokens` and `usage.completion_tokens` — log both.
4. If you call an unknown model name, `tiktoken` falls back to `cl100k_base` and prints a warning.

### Exercise 4 — Compute cost from token counts

```python
# Cost per 1M tokens (USD) — keep these in one place.
PRICING = {
    "gpt-4o-mini":   {"prompt": 0.15, "completion": 0.60},
    "gpt-3.5-turbo": {"prompt": 0.50, "completion": 1.50},
}

def cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    p = PRICING.get(model, {"prompt": 0.0, "completion": 0.0})
    return (prompt_tokens / 1_000_000) * p["prompt"] \
         + (completion_tokens / 1_000_000) * p["completion"]

print(f"{cost_usd('gpt-4o-mini', 1_000, 250):.6f} USD")
```

**Step-by-step:**
1. Use floating-point division (`/`) so the answer is in dollars, not micro-dollars.
2. Keep `PRICING` in a single dict — when OpenAI changes a price, you change one constant.
3. A 1000-token prompt + 250-token completion on `gpt-4o-mini` should print `$0.000300` USD — compute it by hand to confirm.
4. This is the *single number* that goes on every log line.

### Exercise 5 — Token-bucket rate limiter (in-process)

```python
import time

class TokenBucket:
    def __init__(self, rate_per_sec: float, capacity: int):
        self.rate = rate_per_sec
        self.capacity = capacity
        self.tokens = capacity
        self.last = time.monotonic()

    def take(self, n: int = 1) -> bool:
        now = time.monotonic()
        self.tokens = min(self.capacity,
                          self.tokens + (now - self.last) * self.rate)
        self.last = now
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False

bucket = TokenBucket(rate_per_sec=2.0, capacity=4)
for _ in range(6):
    print(bucket.take())   # 4 True, then 2 False
```

**Step-by-step:**
1. Capacity is the burst size; `rate_per_sec` is the sustained throughput. Production limits almost always need both.
2. `time.monotonic()` — never `time.time()`, which can jump on NTP corrections.
3. The in-process bucket is fine for a single worker. For multiple workers or replicas, use Redis with a Lua script (the Main Lab shows the simpler version).
4. Try `bucket.take(2)` to consume multiple tokens at once.

### Exercise 6 — Exponential backoff with `tenacity`

```python
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

class RateLimitedError(Exception): ...
class ServerError(Exception):     ...

@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=0.5, max=8.0),
    retry=retry_if_exception_type((RateLimitedError, ServerError)),
)
def call_flaky_api(n: int):
    if n < 3:
        raise ServerError("transient")
    return "ok"

print(call_flaky_api(n=3))   # "ok"
# call_flaky_api(n=99)       # would exhaust attempts and re-raise
```

**Step-by-step:**
1. `wait_exponential_jitter` doubles the delay and adds random jitter — this is what stops a thundering herd.
2. **Whitelist** which exceptions trigger a retry. Retrying on `BadRequestError` is a great way to spend your whole budget on the same broken payload.
3. `reraise=True` re-raises the *original* exception, not the final `RetryError` — easier to read in stack traces.
4. `stop_after_attempt(5)` caps the total tries. Without a stop, a permanently-broken call burns your whole retry budget.

### Exercise 7 — Structured logs with `structlog` (JSON)

```python
import structlog, uuid

log = structlog.get_logger()

def handle_request(payload: dict) -> dict:
    rid = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(request_id=rid)
    log.info("request.received", payload_size=len(payload))
    # ... work ...
    log.info("request.done", cost_usd=0.0012, tokens=350)
    return {"request_id": rid}

print(handle_request({"q": "hi"}))
# One log line above per `log.info` call, in JSON.
```

**Step-by-step:**
1. `contextvars.bind_contextvars` adds fields to *every* subsequent log line in this async/sync path — the simplest way to thread `request_id` through.
2. JSON output (`structlog.processors.JSONRenderer()`) is what makes logs parseable by Loki, Datadog, ELK, etc.
3. Render the log line once; you should see `"request_id":"..."` and a flat list of keyword fields.
4. Never log the raw prompt or the raw answer at info level; redact to a hash + byte length for token-billable calls.

### Exercise 8 — Detect a deprecated model on startup

```python
DEPRECATED = {
    "gpt-3.5-turbo-0301", "gpt-3.5-turbo-0613",
    "gpt-4-0314",         "gpt-4-0613",
}

def is_model_deprecated(model: str) -> bool:
    return model in DEPRECATED

def startup_check(model: str) -> None:
    if is_model_deprecated(model):
        raise RuntimeError(f"Configured model {model!r} is deprecated. "
                           f"Pick a current model and bump PR_MODEL.")
    print(f"PR_MODEL={model} OK")

startup_check("gpt-4o-mini")              # OK
# startup_check("gpt-3.5-turbo-0613")      # raises RuntimeError
```

**Step-by-step:**
1. The check runs once at process start — not on every call — so it never adds latency to the hot path.
2. Keep `DEPRECATED` updated. A weekly cron or a pre-deploy job should refresh it from the OpenAI deprecations page.
3. Pair the check with `PR_MODEL_VERSION` so you can answer "which prompt + which model was running at 02:14 UTC on Tuesday?".
4. A more sophisticated version reads the OpenAI deprecations RSS feed; for the lab the hardcoded list is enough.

---

## Main Lab: Hardened LLM Service for the Engagement Tracker (4–5 hours)

### Scenario

The LLM-powered features you built in Weeks 9–15 (`/chat`, `/parse_request`, `/search_similar`, `/reliable/chat`, `/summary`) work, but they have no cache, no rate limit, no structured logs, no cost ceiling, no fallback, and a single point of failure (any 5xx from OpenAI takes the feature down). The Week 16 lab wraps every LLM call with the production discipline above, then exposes a `/metrics`-style endpoint and an ops runbook.

### Target File Layout

```
app/
  llm/
    client.py          # OpenAI wrapper: retry + fallback + cache
    cache.py           # Redis-backed response cache
    tokens.py          # tiktoken counters + cost
    rate_limit.py      # slowapi + token-bucket fallback
    prompts.py         # versioned prompt registry
    obs.py             # structlog config + helpers
    health.py          # /health + readiness
  routers/
    chat.py            # the user-facing endpoints
ops/
  runbook.md           # on-call cheat sheet
tests/
  test_cache.py
  test_tokens.py
  test_rate_limit.py
  test_client.py       # monkey-patches the OpenAI client
  test_fallback.py
  test_health.py
```

### Build Steps

**Commit after each step.** Use messages like:
- `feat: cache LLM responses in Redis`
- `feat: rate limit /chat with slowapi`
- `feat: count tokens on every call`
- `feat: fallback model on primary failure`
- `ci: add pytest for non-LLM machinery`

#### Step 1 — Configure `structlog` to emit JSON

*`feat: structured JSON logging`*

```python
# app/llm/obs.py
import logging, structlog, uuid

def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(format="%(message)s", level=level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

def new_request_id() -> str:
    return str(uuid.uuid4())
```

```python
# app/main.py  (illustrative)
from app.llm.obs import configure_logging
configure_logging()
```

**Step-by-step:**
1. `JSONRenderer()` is the magic line — every log line becomes one valid JSON object per line.
2. `contextvars.merge_contextvars` lets you call `bind_contextvars(request_id=...)` once and see that field on every later line.
3. Use the same logger from FastAPI middleware (`request_id`, `path`, `status`), from the LLM client (`tokens`, `cost_usd`, `model`), and from the rate limiter.
4. The cost of structured logging is ~50 µs per line. The benefit is the difference between "it broke" and a queryable timeline.

#### Step 2 — Build the Redis-backed response cache

*`feat: Redis cache for LLM responses`*

```python
# app/llm/cache.py
import json, hashlib, redis
from typing import Any

class LLMCache:
    def __init__(self, url: str, namespace: str = "llm", ttl_s: int = 3600):
        self.r = redis.from_url(url, decode_responses=True)
        self.ns = namespace
        self.ttl = ttl_s

    @staticmethod
    def _key(model: str, prompt_version: str, messages: list[dict],
             temperature: float) -> str:
        payload = json.dumps(
            {"model": model, "prompt_version": prompt_version,
             "messages": messages, "temperature": temperature},
            sort_keys=True, separators=(",", ":"),
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]
        return f"{namespace_marker}:{digest}"

    def get(self, model: str, prompt_version: str, messages: list[dict],
            temperature: float) -> dict | None:
        key = self._key(model, prompt_version, messages, temperature)
        raw = self.r.get(key)
        return json.loads(raw) if raw else None

    def set(self, model: str, prompt_version: str, messages: list[dict],
            temperature: float, value: dict) -> None:
        key = self._key(model, prompt_version, messages, temperature)
        self.r.set(key, json.dumps(value), ex=self.ttl)

    def stats(self) -> dict:
        return {
            "keys": self.r.dbsize(),
            "memory": self.r.info("memory").get("used_memory_human"),
        }
```

**Step-by-step:**
1. The cache key includes model, prompt version, messages, **and** temperature. Two calls that differ only in `seed` will share a key — that is OK because the response is structurally what matters for most loads.
2. Default TTL is one hour. Lower it (`ttl_s=300`) for fast-moving contexts; raise it (24 hours) for stable system prompts.
3. `stats()` is something you can curl from your ops dashboard — it answers "is Redis even being used?".
4. **Do not** cache responses that contain PII or random seeds; check your retention policy before turning the cache on for a new endpoint.

#### Step 3 — Count tokens and compute cost

*`feat: tiktoken counters + cost calculator`*

```python
# app/llm/tokens.py
import tiktoken

PRICING = {
    "gpt-4o-mini":   {"prompt": 0.15, "completion": 0.60},
    "gpt-3.5-turbo": {"prompt": 0.50, "completion": 1.50},
}

# 4 tokens per message framing + 2 priming tokens, per OpenAI cookbook
_FRAMING = 4
_PRIMING = 2

def count_prompt_tokens(model: str, messages: list[dict]) -> int:
    enc = tiktoken.encoding_for_model(model)
    total = _PRIMING
    for m in messages:
        total += _FRAMING + len(enc.encode(m.get("content") or ""))
    return total

def cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    p = PRICING.get(model, {"prompt": 0.0, "completion": 0.0})
    return (prompt_tokens / 1_000_000) * p["prompt"] \
         + (completion_tokens / 1_000_000) * p["completion"]
```

**Step-by-step:**
1. `count_prompt_tokens` is the **estimate**; the real counts come back in `usage.*` after the call. Always log both.
2. Pricing belongs in one place. Update it on the day OpenAI ships a change; never inline numbers in routes.
3. If the configured model is unknown (`PRICING.get(...)` returns zeros), log a warning at startup so you do not silently get free calls.
4. A common bug: not counting system messages. The loop above intentionally iterates **all** messages.

#### Step 4 — A prompt registry with explicit versions

*`feat: versioned prompt registry`*

```python
# app/llm/prompts.py
# Adding a new prompt? Add a new version, never edit in place.
ROUTER_SYSTEM = {
    "v1": (
        "You are a router for an internal request tracker. "
        "Decide whether the user's message is answerable from context, "
        "requires a tool call, or should be refused. Output JSON only."
    ),
}

def get_prompt(name: str, version: str) -> str:
    table = {"router": ROUTER_SYSTEM}
    try:
        return table[name][version]
    except KeyError as e:
        raise RuntimeError(
            f"Unknown prompt {name!r}@{version!r}. "
            f"Known versions: {list(table[name].keys())}"
        ) from e
```

**Step-by-step:**
1. The version string is part of the cache key — bumping `v1` → `v2` invalidates every cached response for that prompt. That is the feature, not a bug.
2. Do not store prompts in environment variables for this lab. Environment variables are great for *secrets* (API keys), bad for *behavioural config* you want to diff in git.
3. The `try/except KeyError` style raises a *named* error rather than `KeyError("'v3'")` — easier to grep in logs.
4. A self-imposed rule: every PR that changes a prompt also updates the version string. Treat prompts like schema migrations.

#### Step 5 — Token-bucket + slowapi rate limiter

*`feat: rate limit /chat with slowapi and token bucket`*

```python
# app/llm/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

# Per-IP coarse-grained limiter — slowapi handles the plumbing.
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# Per-user fine-grained bucket — Redis-backed so it works across replicas.
import redis, time

class DistributedTokenBucket:
    """Atomic token bucket using a Lua script."""
    _LUA = """
    local key = KEYS[1]
    local rate = tonumber(ARGV[1])
    local cap = tonumber(ARGV[2])
    local n = tonumber(ARGV[3])
    local now = tonumber(ARGV[4])
    local data = redis.call('HMGET', key, 'tokens', 'ts')
    local tokens = tonumber(data[1]) or cap
    local ts = tonumber(data[2]) or now
    tokens = math.min(cap, tokens + (now - ts) * rate)
    if tokens >= n then
        redis.call('HMSET', key, 'tokens', tokens - n, 'ts', now)
        redis.call('EXPIRE', key, 60)
        return 1
    else
        redis.call('HMSET', key, 'tokens', tokens, 'ts', now)
        redis.call('EXPIRE', key, 60)
        return 0
    end
    """

    def __init__(self, redis_url: str, rate_per_sec: float, capacity: int):
        self.r = redis.from_url(redis_url)
        self.rate = rate_per_sec
        self.capacity = capacity
        self.script = self.r.register_script(self._LUA)

    def take(self, user_id: str, n: int = 1) -> bool:
        return bool(self.script(
            keys=[f"rate:{user_id}"],
            args=[self.rate, self.capacity, n, time.time()],
        ))
```

**Step-by-step:**
1. `slowapi` gives you the 429 response and the per-route decorator for free. Use it as the outer perimeter.
2. The Lua-script bucket is *atomic* on the Redis side. Without the script, two workers checking-then-decrementing in Python will over-grant.
3. The key is per-user (`user_id`), not per-IP — two users behind one NAT should not share a budget.
4. If `take()` returns `False`, you return HTTP 429 from the route, *and* you log the rejection so you can chart rejected traffic.

#### Step 6 — Daily cost counter in Redis

*`feat: per-day cost roll-up with a soft cap`*

```python
# app/llm/cost.py
import redis, time

class DailyCostCounter:
    """INCRBYFLOAT-based counter; rolls over at UTC midnight."""

    def __init__(self, redis_url: str, day_budget_usd: float):
        self.r = redis.from_url(redis_url)
        self.budget = day_budget_usd

    def _key(self) -> str:
        return f"cost:day:{time.strftime('%Y-%m-%d', time.gmtime())}"

    def add(self, usd: float) -> float:
        total = float(self.r.incrbyfloat(self._key(), usd))
        self.r.expire(self._key(), 60 * 60 * 36)  # 1.5 days, safe across midnight
        return total

    def over_budget(self) -> bool:
        raw = self.r.get(self._key())
        return float(raw or 0.0) > self.budget

    def today(self) -> float:
        return float(self.r.get(self._key()) or 0.0)
```

```python
# usage inside the client (preview of Step 7):
counter = DailyCostCounter(redis_url, day_budget_usd)
counter.add(0.0003)
if counter.over_budget():
    log.warning("cost.over_budget", today_usd=counter.today(),
                budget_usd=counter.budget)
```

**Step-by-step:**
1. `INCRBYFLOAT` is one Redis command — no race, no locks. The whole "daily cost" is one key.
2. The `EXPIRE` of 36 hours gives you a single rollover boundary; the next day's first `INCRBYFLOAT` will create a new key with the new date.
3. The **soft** cap logs a warning; the **hard** cap (in the route) raises 503 with a `Retry-After` header.
4. The cost key should be visible to your metrics dashboard. Plot `cost_today_usd` once a day; the slope is your burn rate.

#### Step 7 — The OpenAI client: cache, retry, fallback, log, count

*`feat: production OpenAI client with the full wrapping`*

```python
# app/llm/client.py
import os, time
from openai import OpenAI, RateLimitError, APIStatusError, APIConnectionError
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

from .cache import LLMCache
from .tokens import count_prompt_tokens, cost_usd
from .cost import DailyCostCounter
from .prompts import get_prompt
from .obs import new_request_id
import structlog

log = structlog.get_logger()

_RETRY = (RateLimitError, APIStatusError, APIConnectionError)

class HardenedClient:
    def __init__(self, cache: LLMCache, counter: DailyCostCounter):
        self.openai = OpenAI()
        self.cache = cache
        self.counter = counter

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential_jitter(initial=0.5, max=8.0),
        retry=retry_if_exception_type(_RETRY),
    )
    def _call(self, model: str, messages: list[dict], temperature: float) -> dict:
        resp = self.openai.chat.completions.create(
            model=model, messages=messages, temperature=temperature,
        )
        return {
            "text": resp.choices[0].message.content,
            "prompt_tokens": resp.usage.prompt_tokens,
            "completion_tokens": resp.usage.completion_tokens,
            "model": model,
        }

    def chat(self, prompt_name: str, prompt_version: str,
             user_messages: list[dict], temperature: float = 0.0) -> dict:
        rid = new_request_id()
        structlog.contextvars.bind_contextvars(request_id=rid)
        system = {"role": "system", "content": get_prompt(prompt_name, prompt_version)}
        messages = [system, *user_messages]

        primary   = os.getenv("PRIMARY_MODEL", "gpt-4o-mini")
        fallback  = os.getenv("FALLBACK_MODEL", "gpt-3.5-turbo")
        log.info("llm.call.begin", prompt=prompt_name, version=prompt_version,
                 model=primary, temperature=temperature)

        # 1) cache lookup
        cached = self.cache.get(primary, prompt_version, messages, temperature)
        if cached:
            log.info("llm.call.cache_hit", cost_usd=0.0)
            return {**cached, "cache_hit": True}

        # 2) try primary, fall back on retryable errors
        for model in (primary, fallback):
            try:
                t0 = time.perf_counter()
                result = self._call(model, messages, temperature)
                result["latency_ms"] = int((time.perf_counter() - t0) * 1000)
                result["cache_hit"]  = False

                # 3) account for cost
                cost = cost_usd(model, result["prompt_tokens"],
                                result["completion_tokens"])
                self.counter.add(cost)

                # 4) populate cache
                self.cache.set(primary, prompt_version, messages, temperature, result)

                log.info("llm.call.ok", model=model, cost_usd=cost,
                         prompt_tokens=result["prompt_tokens"],
                         completion_tokens=result["completion_tokens"],
                         latency_ms=result["latency_ms"])
                return result
            except _RETRY as e:
                log.warning("llm.call.fallback", from_model=model, error=type(e).__name__)
                continue
            except Exception as e:
                log.error("llm.call.error", from_model=model, error=str(e))
                raise
        raise RuntimeError("Both primary and fallback models failed")
```

**Step-by-step:**
1. Order of operations matters: **cache → call → cost → cache-write → log**. Doing cost *before* the call would mean charging for failures.
2. The retry decorator only wraps `_call`; the fallback loop is *outside* the decorator. Otherwise a failure on `gpt-4o-mini` would be retried four times before falling back.
3. Fallback only triggers on retryable errors (429, 5xx, connection). A 400 (bad request) means your *prompt* is wrong — retrying is the wrong response.
4. The log lines are the contract with the on-call engineer. If you cannot answer "what happened to request X?" from a single log query, the contract is broken.

#### Step 8 — Health and readiness endpoints

*`feat: /health and /ready`*

```python
# app/llm/health.py
import os, time, structlog
from fastapi import APIRouter, Response, status
import redis

from app.llm.cache import LLMCache
from app.llm.client import HardenedClient

log = structlog.get_logger()
router = APIRouter()

@router.get("/health")
def health():
    """Liveness — is the process responsive at all?"""
    return {"status": "ok", "ts": int(time.time())}

@router.get("/ready")
def ready(response: Response):
    """Readiness — can we actually serve traffic?"""
    checks = {}

    # Redis
    try:
        cache = LLMCache(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        cache.r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e!s}"

    # Model config
    checks["primary_model"]  = os.getenv("PRIMARY_MODEL",  "gpt-4o-mini")
    checks["fallback_model"] = os.getenv("FALLBACK_MODEL", "gpt-3.5-turbo")

    failing = [k for k, v in checks.items() if isinstance(v, str) and v.startswith("error")]
    if failing:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"checks": checks, "failing": failing}
```

**Step-by-step:**
1. Two endpoints, not one: `/health` answers "is the process alive" (cheap, never depends on Redis); `/ready` answers "should I get traffic" (touches Redis).
2. Liveness checks should never fail because of a downstream dependency. If Redis dies, the liveness probe still passes; only `/ready` flips to 503, so Kubernetes drains traffic but does not restart the pod.
3. The 503 response is what your load balancer needs to redirect traffic. The detailed `checks` dict is for the operator running `curl /ready` manually.
4. The probe timeout matters: `/ready` should respond inside 200 ms, otherwise the orchestrator will kill the pod before it returns.

#### Step 9 — Mount the rate limiter and the cost guard in FastAPI

*`feat: route-level rate limit + cost guard`*

```python
# app/routers/chat.py
from fastapi import APIRouter, HTTPException, Request, Depends
from slowapi.errors import RateLimitExceeded

from app.llm.client import HardenedClient
from app.llm.rate_limit import limiter, DistributedTokenBucket
from app.llm.cost import DailyCostCounter

router = APIRouter()
client = HardenedClient.from_env()   # assume you've added this convenience
counter = DailyCostCounter.from_env()
bucket  = DistributedTokenBucket.from_env()

@router.post("/chat")
@limiter.limit("20/minute")          # IP-level outer limit
def chat(request: Request, payload: dict):
    user_id = payload.get("user_id", "anonymous")

    # Per-user token bucket
    if not bucket.take(user_id, n=1):
        raise HTTPException(status_code=429, detail="slow down")

    # Daily budget guard
    if counter.over_budget():
        raise HTTPException(status_code=503,
                            headers={"Retry-After": "3600"},
                            detail="daily budget exceeded")

    return client.chat(
        prompt_name="router",
        prompt_version="v1",
        user_messages=[{"role": "user", "content": payload["message"]}],
    )
```

**Step-by-step:**
1. Two layers: `slowapi` is the outer wall (per-IP, per-minute), the token bucket is the inner wall (per-user, sustained rate).
2. The `Retry-After` header is required by the HTTP spec for 503 with "try later". Clients that respect it will back off correctly.
3. The cost guard fires *before* the LLM call — the difference between "we exceeded budget" and "we exceeded budget on a no-answer call" matters in the runbook.
4. Keep the payload schema (`{"user_id", "message"}`) deliberately small. The larger the payload, the harder caching gets.

#### Step 10 — Pytest suite that covers the non-LLM machinery

*`test: cover cache, tokens, rate limit, fallback`*

```python
# tests/test_cache.py
import pytest
from app.llm.cache import LLMCache

@pytest.fixture
def cache():
    return LLMCache("redis://localhost:6379/0", namespace="test", ttl_s=10)

def test_set_then_get(cache):
    cache.set("m", "v", [{"role": "user", "content": "hi"}], 0.0,
              {"text": "hello", "tokens": 1})
    got = cache.get("m", "v", [{"role": "user", "content": "hi"}], 0.0)
    assert got["text"] == "hello"

def test_key_changes_with_temperature(cache):
    k1 = cache._key("m", "v", [{"role": "user", "content": "hi"}], 0.0)
    k2 = cache._key("m", "v", [{"role": "user", "content": "hi"}], 0.5)
    assert k1 != k2
```

```python
# tests/test_tokens.py
from app.llm.tokens import count_prompt_tokens, cost_usd

def test_count_includes_system_message():
    n = count_prompt_tokens("gpt-4o-mini", [
        {"role": "system", "content": "You are brief."},
        {"role": "user",   "content": "hi"},
    ])
    assert n > 4

def test_cost_is_zero_for_unknown_model():
    assert cost_usd("nonexistent-model", 1_000_000, 1_000_000) == 0.0

def test_cost_uses_correct_pricing():
    # 1M prompt tokens at $0.15/M + 250k completion at $0.60/M = $0.30
    assert abs(cost_usd("gpt-4o-mini", 1_000_000, 250_000) - 0.30) < 1e-9
```

```python
# tests/test_rate_limit.py
import time
from app.llm.rate_limit import TokenBucket

def test_token_bucket_burst_then_deny():
    b = TokenBucket(rate_per_sec=1.0, capacity=3)
    assert b.take() and b.take() and b.take()
    assert not b.take()
    time.sleep(1.1)
    assert b.take()      # one earned back
```

```python
# tests/test_fallback.py
from unittest.mock import MagicMock, patch
from app.llm.client import HardenedClient
from app.llm.cache import LLMCache
from app.llm.cost import DailyCostCounter

def test_falls_back_on_rate_limit_error(monkeypatch):
    cache   = LLMCache("redis://localhost:6379/0", namespace="t")
    counter = DailyCostCounter("redis://localhost:6379/0", day_budget_usd=1000)

    fake = HardenedClient(cache, counter)
    calls = {"n": 0}

    def fake_call(self, model, messages, temperature):
        calls["n"] += 1
        if model == "primary" and calls["n"] == 1:
            from openai import RateLimitError
            raise RateLimitError("rate limited", response=MagicMock(), body={})
        return {"text": "fallback-ok", "prompt_tokens": 5,
                "completion_tokens": 3, "model": model}

    monkeypatch.setattr(HardenedClient, "_call", fake_call)
    out = fake.chat("router", "v1", [{"role": "user", "content": "hi"}])
    assert out["text"] == "fallback-ok"
    assert out["model"] == "fallback"
```

```bash
# Run only the tests that do NOT touch the OpenAI API
uv run pytest tests/test_cache.py tests/test_tokens.py \
                  tests/test_rate_limit.py tests/test_fallback.py -v
```

**Step-by-step:**
1. The whole point of these tests is to prove the wrapping works without paying OpenAI. Every test touches Redis or a pure function; none of them call the API.
2. `monkeypatch` is the cleanest way to swap `_call` for a fake — it is scoped to the test and undoes itself.
3. `RateLimitError` is a real OpenAI exception class; the test proves your fallback path actually triggers on it.
4. Add a `tests/test_health.py` that asserts `/health` returns 200 and `/ready` returns 200 when Redis is up; that becomes your smoke test in Week 18.

#### Step 11 — Deprecation check on startup

*`feat: refuse to start with a deprecated model`*

```python
# app/llm/startup.py
import os, structlog

DEPRECATED = {
    "gpt-3.5-turbo-0301", "gpt-3.5-turbo-0613",
    "gpt-4-0314",         "gpt-4-0613",
    "gpt-4-1106-preview",
}

def check_models() -> None:
    log = structlog.get_logger()
    for var in ("PRIMARY_MODEL", "FALLBACK_MODEL"):
        model = os.getenv(var)
        if not model:
            raise RuntimeError(f"{var} is not set in the environment")
        if model in DEPRECATED:
            raise RuntimeError(
                f"{var}={model!r} is deprecated. "
                f"Update the env var or the deploy will misbehave."
            )
        log.info("startup.model_ok", var=var, model=model)
```

```python
# at the top of app/main.py
from app.llm.startup import check_models
check_models()
```

**Step-by-step:**
1. Run `check_models()` in the lifespan, not on every call — startup is when you can afford the few-hundred-ms check.
2. Hard-fail is the right response. A "soft warn" with no break-glass in deploy means the deprecated model ships silently until OpenAI actually retires it.
3. Keep `DEPRECATED` in the codebase as the durable source; your weekly cron refreshes it from the OpenAI deprecations page.
4. Bonus: log every configured model name on startup. The first on-call nightmare is "which model is *this* pod using?".

#### Step 12 — Ops runbook

*`docs: ops runbook for Week 16`*

```markdown
# ops/runbook.md

## LLM service on-call

### Health
- `curl https://<host>/health`  → 200 means the process is alive.
- `curl https://<host>/ready`   → 503 means Redis is unhealthy.

### Logs to look at first
- `llm.call.begin`  — one line per call. Look for runaway volume from one IP.
- `llm.call.cache_hit` — should be > 30% during business hours.
- `llm.call.fallback` — anything here means primary is degraded.
- `cost.over_budget` — daily budget breached; feature will start 503-ing.

### Common incidents

#### "Primary model is 429-ing"
1. Check `llm.call.fallback` in logs. If non-zero, fallback is already absorbing.
2. If both failing, scale down `PRIMARY_MODEL` RPM in OpenAI dashboard or
   increase the rate-limit window (`20/minute` → `30/minute`).
3. If persistent, switch `PRIMARY_MODEL` and `FALLBACK_MODEL` and redeploy.

#### "Daily budget breached"
1. `redis-cli GET cost:day:YYYY-MM-DD` to see today's spend.
2. Identify the top spender: `redis-cli --scan --pattern 'user:*' | head`.
3. Lower the per-user bucket in `app/llm/rate_limit.py`, redeploy.

#### "Cache hit rate dropped"
1. `redis-cli INFO memory` — confirm Redis has not filled.
2. `redis-cli DBSIZE` — should grow over the day, not shrink.
3. If `ttl_s` was changed recently, revert.

### Emergency levers
- Set `PRIMARY_MODEL=gpt-3.5-turbo` and `FALLBACK_MODEL=` (empty) to
  reduce cost instantly; redeploy.
- Set `DAILY_BUDGET_USD=0` to hard-stop all calls (returns 503).
- `redis-cli FLUSHDB` clears the cache (and makes the next minute expensive).
```

**Step-by-step:**
1. Every on-call rotation eventually ends with someone trying to remember what the env vars do. The runbook answers that question in one place.
2. Every "common incident" section starts with **symptom → check → next step**. That is the order the on-call will follow under pressure.
3. "Emergency levers" is short on purpose. Long emergency procedures are not read during incidents.
4. Commit the runbook *with* the code. A runbook in a Notion page lags a deploy by hours; a runbook in git cannot drift from the code it documents.

---

### Required Manual Tests

Before you consider Week 16 done, verify all of the following:

- [ ] `curl /ready` returns 200 when Redis is up and 503 when Redis is down
- [ ] Calling `/chat` twice with the same payload, the second call shows `cache_hit: true` in the response and `llm.call.cache_hit` in the logs
- [ ] Setting an artificial rate limit (`1/minute`) produces a 429 with a clear message
- [ ] Setting an artificial daily budget (`0.0001 USD`) produces a 503 with `Retry-After` within ~100 calls
- [ ] Stopping Redis, calling `/chat`, and observing the fallback log line; restarting Redis
- [ ] Changing `PRIMARY_MODEL` in `.env` shows up in `/ready` output and in `llm.call.ok` log lines
- [ ] Removing `PRIMARY_MODEL` from `.env` produces a startup error
- [ ] Setting `PRIMARY_MODEL` to a value in `DEPRECATED` raises on startup
- [ ] `uv run pytest tests/ -v` passes for the non-LLM tests
- [ ] At least one log line per call contains `request_id`, `model`, `cost_usd`, `tokens`, and `latency_ms`

### Acceptance Criteria

- [ ] A `LLMCache` wrapper that does Redis-backed `get/set` with explicit TTL
- [ ] A `count_prompt_tokens` function using `tiktoken` that matches the framing formula
- [ ] A `cost_usd` function driven by a single `PRICING` constant
- [ ] A token bucket that is atomic across multiple workers (Lua script)
- [ ] An `HardenedClient` that combines cache, retry, fallback, cost, and structured logging in one call
- [ ] A `DailyCostCounter` in Redis with `add()`, `today()`, `over_budget()`
- [ ] `/health` and `/ready` endpoints with the right status codes
- [ ] A startup `check_models()` that hard-fails on deprecated model names
- [ ] Tests cover cache, tokens, rate limit, and fallback without ever calling the OpenAI API
- [ ] An `ops/runbook.md` with health checks, log patterns, and emergency levers
- [ ] At least 5 meaningful commits in the week (one per build step is fine)
- [ ] You can explain the order of operations inside `HardenedClient.chat` (cache → call → cost → cache-write → log)

## AI-Off Check (30 minutes)

**Without looking at your code**, write a function that takes a `model: str`, `messages: list[dict]`, and returns a tuple of `(prompt_tokens_estimate, cost_estimate_usd)` assuming the model is in your `PRICING` constant. Do *not* use `tiktoken` — count whitespace-separated words and multiply by 1.3 (the standard heuristic is that one token ≈ 0.75 words).

```python
def estimate_tokens_and_cost(model: str, messages: list[dict],
                              pricing: dict) -> tuple[int, float]:
    """Skeleton to fill in cold."""
    raise NotImplementedError
```

Then write a second function that builds a stable cache key from the same inputs but only hashes the user-role messages (skipping system).

```python
def cache_key_user_only(model: str, prompt_version: str,
                        messages: list[dict], temperature: float) -> str:
    """Skeleton to fill in cold."""
    raise NotImplementedError
```

Compare your version with your real code. The goal is to internalize two things:
1. **Cost is the dominant signal** in any LLM system — you should be able to estimate it from memory.
2. **Cache keys have to be deliberate** — version, model, and temperature matter; the choice of *which* messages to include is a design decision.

## Reflection Questions

After you finish, write answers to these in `REFLECTION.md`:

1. Why does `cache → call → cost → cache-write → log` get that exact order? What breaks if you flip any two adjacent steps?
2. When does the fallback chain *hide* a real outage instead of solving it? How would your runbook catch that?
3. What is the difference between `slowapi`'s per-IP limit and the `DistributedTokenBucket`'s per-user limit? Why use both?
4. How does prompt version pinning interact with the cache? What is the unit of invalidation?
5. If your daily budget is hit, what is the *right* user experience — 503 for everyone, or a soft degradation? Defend your answer.
6. What part of this lab would you *not* ship to a customer without a paid observability vendor (Datadog, Grafana Cloud, Langfuse)? Why?

## Next Steps

Once you pass all acceptance criteria:

1. Run `uv run pytest tests/ -v` and commit the green report
2. Write the reflection answers
3. Commit with message: `docs: week 16 complete`
4. Move to Week 17 (Docker and Containerization) — the LLM service you built here is the artifact you will containerize

---

**Ready?** Start by running:

```bash
uv init
uv add openai redis slowapi structlog tiktoken tenacity httpx
uv add --dev pytest pytest-asyncio freezegun
docker run -d --name redis-week16 -p 6379:6379 redis:7-alpine
```

Then follow the learning path above. Good luck! 🎯
