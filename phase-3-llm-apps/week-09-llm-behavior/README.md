# Week 9: How LLM Applications Behave

## Outcome

Build a simple, observable **chatbot** that calls an LLM API, and learn to reason about **tokens, temperature, latency, cost, and reliability** — the same concerns you'll apply in every later LLM lab.

By the end of this week you will be able to:

- Call an LLM API (OpenAI or local Ollama) from Python
- Explain how `temperature`, `top_p`, and `max_tokens` change the output
- Measure and log latency and token usage
- Detect and recover from rate limits and timeouts
- Write a tiny evaluation harness that runs the same prompt N times and reports variance

## Setup Checklist

Pick a provider. Both are $0 for the limits in this lab.

### OpenAI path

- [ ] Create an OpenAI account and add a $5 credit
- [ ] Generate an API key at <https://platform.openai.com/api-keys>
- [ ] `uv add openai`
- [ ] `export OPENAI_API_KEY="sk-..."` (or store in `.env`)

### Local Ollama path

- [ ] Install Ollama: <https://ollama.com>
- [ ] `ollama pull llama3.2`
- [ ] `uv add openai` (Ollama serves an OpenAI-compatible API)
- [ ] `export OPENAI_BASE_URL="http://localhost:11434/v1"`
- [ ] `export OPENAI_API_KEY="ollama"` (any string)

### Setup Walkthrough

```bash
uv add openai tiktoken
# Confirm
uv run python -c "import openai, tiktoken; print('ok')"
```

Add to `.env.example`:

```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
LLM_TIMEOUT=20
```

## Learning Path (60–90 minutes)

**Best approach:** Build a single-turn call first, then add logging and a tiny eval. Skip agent or RAG features until Weeks 11–14.

### Learn in this order

1. **Anatomy of an LLM call** — model, messages, parameters
2. **Tokens** — what they are, how to count them
3. **Temperature and top_p** — randomness controls
4. **Streaming** — chunk-by-chunk output
5. **Error handling** — rate limits, timeouts, content filters
6. **Logging and metrics** — latency, tokens, cost
7. **Evaluation basics** — running the same prompt N times, comparing outputs
8. **Prompt design** — system messages, few-shot, structured output (preview of Week 10)

### Free Resources

- [OpenAI quickstart](https://platform.openai.com/docs/quickstart)
- [Ollama quickstart](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Andrej Karpathy intro to LLMs (video)](https://www.youtube.com/watch?v=zjkBMFhNj_g)
- [Token costs and context windows](https://platform.openai.com/docs/models)
- [How to evaluate LLM applications (deeplearning.ai short course)](https://www.deeplearning.ai/short-courses/evaluating-ai-agents/)

## Micro-Exercises (45–60 minutes)

1. Send a single message and print the reply
2. Inspect the response: model, usage, finish reason
3. Count tokens with `tiktoken`
4. Set `temperature=0` and run the same prompt 5 times; observe identical output
5. Set `temperature=1.0` and run the same prompt 5 times; observe variance
6. Stream a reply and print chunks as they arrive
7. Catch a `RateLimitError` and back off
8. Log latency, prompt tokens, and completion tokens

## Main Lab: Triage Assistant (4–5 hours)

### Scenario

A chatbot that reads a free-text customer request and suggests:
- A one-line summary
- A likely `priority` (low / medium / high)
- A likely `category` (bug / question / feature)

The chatbot **never** updates the tracker itself; it only *suggests* values. The human decides.

### Output Schema (preview of Week 10)

```json
{
  "summary": "Login system is intermittently slow for EU users",
  "priority": "high",
  "category": "bug"
}
```

### Build Steps

1. Build a `ChatClient` that wraps the OpenAI/Ollama client
2. Add structured logging for every call
3. Add token counting and cost tracking
4. Add retry with exponential backoff
5. Add a small CLI `python -m request_tracker.triage "free text"`
6. Add a tiny eval harness with 5 hand-written prompts
7. Add streaming support to the CLI
8. Add a `/triage` endpoint to the FastAPI app
9. Document cost and latency in the README
10. Set a hard monthly spend alert on your OpenAI account

## Step-by-Step Walkthrough

### Exercise 1 — Send a single message and print the reply

```python
# practice.py
import os
from openai import OpenAI

client = OpenAI()  # reads OPENAI_API_KEY from env

resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful support triage assistant."},
        {"role": "user",   "content": "Our login page is throwing 500 errors."},
    ],
)
print(resp.choices[0].message.content)
```

**Step-by-step:**
1. The `client` is module-level — instantiate once, reuse for every call.
2. `messages` is a list of dicts with `role` and `content`. The model does not have memory between calls; *you* send the history.
3. `choices[0]` is almost always the only choice for a single response.

### Exercise 2 — Inspect the response: model, usage, finish reason

```python
# practice.py
print("model:", resp.model)
print("finish_reason:", resp.choices[0].finish_reason)
print("usage:", resp.usage.model_dump())
# usage: {"prompt_tokens": 27, "completion_tokens": 38, "total_tokens": 65}
```

**Step-by-step:**
1. `finish_reason` is one of `stop`, `length`, `content_filter`, `tool_calls`.
2. `usage` is what you bill against — log it on every call.
3. `model` may differ from what you requested if the platform auto-routes to a newer model.

### Exercise 3 — Count tokens with `tiktoken`

```python
# practice.py
import tiktoken

enc = tiktoken.encoding_for_model("gpt-4o-mini")
ids = enc.encode("How many tokens is this sentence?")
print(len(ids), "tokens")
```

**Step-by-step:**
1. `tiktoken` is OpenAI's tokenizer. It runs locally — no API call.
2. Token counts are an *estimate* of the API's internal counter, but the match is very close.
3. Use this to budget prompt size before sending.

### Exercise 4 — Set `temperature=0` and observe identical output

```python
# practice.py
for i in range(3):
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Name a color."}],
        temperature=0,
    )
    print(r.choices[0].message.content)
# expected: "Blue" or "Red" three times in a row (deterministic at temp=0)
```

**Step-by-step:**
1. `temperature=0` makes the model pick the most likely next token every time.
2. Output is *mostly* identical, but not guaranteed — providers may add small internal randomness.
3. Use this for classification and structured extraction.

### Exercise 5 — Set `temperature=1.0` and observe variance

```python
# practice.py
for i in range(3):
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Name a color."}],
        temperature=1.0,
    )
    print(r.choices[0].message.content)
# expected: "Cerulean", "Crimson", "Teal" — different each time
```

**Step-by-step:**
1. `temperature=1.0` is the model's "natural" entropy. Don't go above 2.
2. Higher temperature helps with creative writing; lower helps with classification.
3. Combine with `top_p=0.9` for finer control.

### Exercise 6 — Stream a reply and print chunks

```python
# practice.py
stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Write a haiku about Python."}],
    stream=True,
)
for chunk in stream:
    piece = chunk.choices[0].delta.content or ""
    print(piece, end="", flush=True)
print()
```

**Step-by-step:**
1. `stream=True` returns a generator instead of one big response.
2. `delta.content` may be `None` for chunks that only carry metadata — guard with `or ""`.
3. `flush=True` ensures the user sees the text as it arrives.

### Exercise 7 — Catch a `RateLimitError` and back off

```python
# practice.py
import time
from openai import RateLimitError

for attempt in range(3):
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "hi"}],
        )
        print(r.choices[0].message.content)
        break
    except RateLimitError as e:
        wait = 2 ** attempt
        print(f"rate limited, sleeping {wait}s")
        time.sleep(wait)
```

**Step-by-step:**
1. `RateLimitError` is a subclass of `APIError` — you can catch the parent if you prefer.
2. Exponential backoff (1s, 2s, 4s) is the standard pattern.
3. After max retries, surface the error to the caller; never loop forever.

### Exercise 8 — Log latency, prompt tokens, and completion tokens

```python
# practice.py
import logging, time
log = logging.getLogger("llm")

t0 = time.perf_counter()
r = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "hi"}],
)
elapsed = (time.perf_counter() - t0) * 1000
log.info("llm_call",
         extra={"model": r.model,
                "prompt_tokens": r.usage.prompt_tokens,
                "completion_tokens": r.usage.completion_tokens,
                "latency_ms": round(elapsed, 1)})
```

**Step-by-step:**
1. `time.perf_counter()` is the right clock for measuring intervals (monotonic, high resolution).
2. Logging in `extra={...}` keeps the call site terse; a JSON formatter in Week 19 turns this into structured logs.
3. The `model` in the response can differ from what you asked for — log the *actual* model.

---

### Step 1 — Build a `ChatClient` that wraps the OpenAI/Ollama client

```python
# src/request_tracker/llm.py
import logging
import time
from dataclasses import dataclass
from openai import OpenAI
from .config import load_settings

log = logging.getLogger(__name__)

@dataclass
class ChatResult:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float

class ChatClient:
    def __init__(self, client: OpenAI | None = None) -> None:
        s = load_settings()
        self.client = client or OpenAI()
        self.model = s.openai_model
        self.timeout = s.llm_timeout

    def chat(self, system: str, user: str,
             temperature: float = 0.0) -> ChatResult:
        t0 = time.perf_counter()
        r = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user",   "content": user}],
            temperature=temperature,
            timeout=self.timeout,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return ChatResult(
            text=r.choices[0].message.content or "",
            model=r.model,
            prompt_tokens=r.usage.prompt_tokens,
            completion_tokens=r.usage.completion_tokens,
            latency_ms=round(elapsed_ms, 1),
        )
```

**Why:** Wrapping the SDK gives you one place to add logging, retries, fallbacks, and evaluation hooks.

### Step 2 — Add structured logging for every call

```python
# in ChatClient.chat, after r is received:
log.info("llm_call",
         extra={"model": r.model,
                "prompt_tokens": r.usage.prompt_tokens,
                "completion_tokens": r.usage.completion_tokens,
                "latency_ms": round(elapsed_ms, 1),
                "temperature": temperature})
```

### Step 3 — Add token counting and cost tracking

```python
# src/request_tracker/llm_cost.py
PRICES = {  # USD per 1M tokens, as of late 2025
    "gpt-4o-mini":        {"in": 0.15,  "out": 0.60},
    "gpt-4o":             {"in": 2.50,  "out": 10.00},
}

def estimate_cost_usd(model: str, prompt: int, completion: int) -> float:
    p = PRICES.get(model, {"in": 0, "out": 0})
    return (prompt / 1_000_000) * p["in"] + (completion / 1_000_000) * p["out"]
```

**Why:** Storing prices in one place means swapping models only changes one constant. Always show users a cost estimate, even if rough.

### Step 4 — Add retry with exponential backoff

```python
# src/request_tracker/llm.py
from openai import RateLimitError, APITimeoutError, APIError

def chat_with_retry(self, system: str, user: str,
                    temperature: float = 0.0,
                    max_retries: int = 3) -> ChatResult:
    for attempt in range(max_retries):
        try:
            return self.chat(system, user, temperature)
        except (RateLimitError, APITimeoutError) as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            log.warning("llm_retry", extra={"err": str(e), "wait_s": wait})
            time.sleep(wait)
        except APIError as e:
            log.error("llm_api_error", extra={"err": str(e)})
            raise
```

### Step 5 — Add a small CLI `python -m request_tracker.triage "free text"`

```python
# src/request_tracker/triage.py
import argparse, json
from .llm import ChatClient

SYSTEM = """You are a support triage assistant. Reply with a single JSON
object of the form {"summary": str, "priority": "low|medium|high",
"category": "bug|question|feature"}. No other text."""

def triage(text: str) -> dict:
    client = ChatClient()
    result = client.chat(SYSTEM, text, temperature=0.0)
    return json.loads(result.text)

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("text")
    args = p.parse_args()
    print(json.dumps(triage(args.text), indent=2))

if __name__ == "__main__":
    main()
```

```bash
uv run python -m request_tracker.triage "Our login page throws 500 errors every morning"
```

### Step 6 — Add a tiny eval harness

```python
# tests/eval_triage.py
import json
from request_tracker.triage import triage
from request_tracker.llm import ChatClient

CASES = [
    {"text": "Login returns 500 for 10% of users",
     "expected_priority": "high", "expected_category": "bug"},
    {"text": "How do I add a user?",
     "expected_priority": "low", "expected_category": "question"},
    {"text": "It would be nice to have SSO",
     "expected_priority": "low", "expected_category": "feature"},
    {"text": "Database is completely down",
     "expected_priority": "high", "expected_category": "bug"},
    {"text": "Can the report include last quarter?",
     "expected_priority": "low", "expected_category": "question"},
]

def run_eval() -> None:
    correct = 0
    for c in CASES:
        out = triage(c["text"])
        ok = (out.get("priority") == c["expected_priority"] and
              out.get("category") == c["expected_category"])
        correct += int(ok)
        print(f"{'OK' if ok else 'FAIL'}: {out}")
    print(f"\n{correct}/{len(CASES)} correct "
          f"({correct / len(CASES) * 100:.0f}%)")
```

```bash
uv run python -m tests.eval_triage
```

**Why:** A 5-case eval is not statistically meaningful, but it *is* useful as a smoke test after a model upgrade or a prompt change.

### Step 7 — Add streaming support

```python
# src/request_tracker/llm.py
def stream(self, system: str, user: str):
    s = self.client.chat.completions.create(
        model=self.model,
        messages=[{"role": "system", "content": system},
                  {"role": "user",   "content": user}],
        stream=True,
    )
    for chunk in s:
        piece = chunk.choices[0].delta.content or ""
        if piece:
            yield piece
```

```python
# src/request_tracker/triage_stream.py
import sys
from .llm import ChatClient

for piece in ChatClient().stream("You are concise.", sys.argv[1]):
    print(piece, end="", flush=True)
```

### Step 8 — Add a `/triage` endpoint to the FastAPI app

```python
# src/request_tracker/api.py
from .llm import ChatClient
from .security import get_current_user, require_role, Principal

@router.post("/triage")
def triage_request(
    payload: TriageIn,
    user: Annotated[Principal, Depends(require_role("admin", "engineer"))],
):
    client = ChatClient()
    result = client.chat(SYSTEM, payload.text, temperature=0.0)
    return {"text": result.text,
            "model": result.model,
            "usage": {"prompt_tokens": result.prompt_tokens,
                      "completion_tokens": result.completion_tokens}}
```

### Step 9 — Document cost and latency in the README

```markdown
## Triage Assistant

The `/triage` endpoint calls `gpt-4o-mini` with temperature 0.
Expected:
- Latency: 0.5–2.0 s for inputs under 500 tokens
- Cost: ~$0.0001 per call (≈$0.10 per 1,000 calls)
- Variance: 0–1% disagreement with the eval suite
```

### Step 10 — Set a hard monthly spend alert

On <https://platform.openai.com/account/limits>, set a billing limit equal to your monthly cap. **Required before moving on.**

---

## Acceptance Criteria

- [ ] `ChatClient` makes real API calls and returns `ChatResult`
- [ ] Every call logs model, tokens, and latency
- [ ] Retry handles 429 and 5xx without crashing
- [ ] CLI `python -m request_tracker.triage "text"` prints JSON
- [ ] Eval harness runs the 5 hand-written prompts and reports a score
- [ ] Streaming variant prints chunks as they arrive
- [ ] `/triage` endpoint is auth-gated and returns the model's choice
- [ ] README documents cost and latency expectations
- [ ] OpenAI monthly spend limit is set
- [ ] At least 5 meaningful commits

## AI-Off Check

**Without AI**, write the system prompt for a chatbot that *refuses* to suggest a `priority` of `high` unless the user's text contains one of: "outage", "down", "critical", "production", "error", "broken". Test that a benign prompt and an "outage" prompt behave differently.

## Reflection Questions

1. Why is `temperature=0` the right default for triage but wrong for a creative-writing bot?
2. What does "tokens" mean and why should you budget them on both sides of the call?
3. How would you detect a silent model upgrade? (Hint: log the `model` in the response.)
4. What's the most expensive thing in this lab? How would you halve the cost?

---

**Next:** Move to Week 10 when all acceptance criteria pass and you can demo the triage assistant on 5 real customer messages.
