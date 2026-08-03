# Week 10: Structured Output and Parsing

## Outcome

Constrain LLM responses to **validated, typed JSON** using Pydantic models, `response_format`, and tool/function calling. Build a **Request Triage** service that ingests free-text customer messages and emits a typed `TriageResult` (intent, category, urgency, entities).

## Setup Checklist

- [ ] Reuse the `tracker` FastAPI app from Week 5 (or stand up a fresh one)
- [ ] Have an OpenAI API key (or use Ollama for local-only work — see Week 9)
- [ ] `uv add openai pydantic python-dotenv pytest`
- [ ] Confirm `uv run python -c "import openai, pydantic; print('ok')"` works
- [ ] Have `pytest` available for the validation tests

### Setup Walkthrough

```bash
# 1. Enter the week's folder (or create a fresh project)
cd phase-3-llm-apps/week-10-structured-output
uv init
uv python pin 3.13

# 2. Add the dependencies we need
uv add openai pydantic python-dotenv pytest ruff

# 3. Create a .env file (never commit this)
cat > .env <<'EOF'
OPENAI_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4o-mini
EOF

# 4. Verify the environment loads
uv run python - <<'PY'
import os
from dotenv import load_dotenv
load_dotenv()
print("model:", os.getenv("LLM_MODEL"))
print("key set:", bool(os.getenv("OPENAI_API_KEY")))
PY
```

Add `.env` to `.gitignore` immediately:

```bash
echo ".env" >> .gitignore
git add .gitignore
git commit -m "chore: ignore .env"
```

## Learning Path (60–90 minutes)

**Best approach:** Treat the LLM like an untrusted parser. Every response must be **validated against a schema before your code touches it**.

### Learn in this order

1. **Why structured output matters** — stringly-typed LLM responses are the #1 source of bugs in production agents
2. **JSON mode** — `response_format={"type": "json_object"}` forces valid JSON, but does not enforce shape
3. **Pydantic models** — declare the shape once, get validation, serialization, and docs for free
4. **`response_format` with a schema** — OpenAI's "Structured Outputs" feature enforces a JSON Schema
5. **Tool/function calling as a schema mechanism** — describe a function, the model produces arguments that fit
6. **Parsing + retry loop** — if the model hallucinates, parse, detect failure, and retry with feedback
7. **Error surfaces** — `ValidationError`, missing fields, wrong types, off-schema enums

### Free Resources

- [OpenAI Structured Outputs Guide](https://platform.openai.com/docs/guides/structured-outputs) — `response_format` and JSON Schema
- [Pydantic v2 Models](https://docs.pydantic.dev/latest/concepts/models/) — `BaseModel`, `Field`, validators
- [Instructor (library)](https://python.useinstructor.com/) — `instructor.from_openai(...)` wraps Pydantic + retries (optional but excellent)
- [OpenAI Function Calling Guide](https://platform.openai.com/docs/guides/function-calling) — tool-spec style schema
- [JSON Schema Reference](https://json-schema.org/learn/getting-started-step-by-step) — for the `response_format` schema you pass in

**Tip:** Always start with a **plain Pydantic class** and `model_validate_json()`. Add libraries like Instructor only after you can do it by hand.

## Micro-Exercises (45–60 minutes)

Create `practice.py` and work through these:

### Exercise 1 — Declare a Pydantic model for a triage result

```python
# practice.py
from pydantic import BaseModel, Field
from enum import Enum

class Intent(str, Enum):
    NEW_REQUEST = "new_request"
    STATUS_CHECK = "status_check"
    COMPLAINT = "complaint"
    OTHER = "other"

class Category(str, Enum):
    BILLING = "billing"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    GENERAL = "general"

class Urgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TriageResult(BaseModel):
    intent: Intent
    category: Category
    urgency: Urgency
    summary: str = Field(min_length=10, max_length=240)
    entities: list[str] = Field(default_factory=list)

# Validating dict-shaped data
raw = {
    "intent": "new_request",
    "category": "billing",
    "urgency": "high",
    "summary": "Customer cannot access last month's invoice PDF.",
    "entities": ["invoice", "PDF", "billing portal"],
}
result = TriageResult.model_validate(raw)
print(result.summary)
print(result.urgency.value)
```

**Step-by-step:**
1. Define each `Enum` — `str, Enum` makes them serialize as plain strings.
2. Define `TriageResult` with constraints (`min_length`, `max_length`, default factory).
3. Run `model_validate()` on a dict — Pydantic coerces, validates, and returns a typed object.
4. Try mutating the dict (e.g., `"urgency": "EXTREME"`) and re-validate — you'll see a clear `ValidationError`.

### Exercise 2 — Validate JSON the LLM returns, and read the error

```python
import json
from pydantic import ValidationError

# Pretend the model returned this (valid JSON, wrong shape)
bad_json = '{"intent": "new_request", "urgency": "super-high"}'

try:
    result = TriageResult.model_validate_json(bad_json)
except ValidationError as e:
    print("Validation failed:")
    print(e)
    # Walk the structured error if you want machine-readable detail
    for err in e.errors():
        print(f"  - {err['loc']}: {err['msg']}")
```

**Step-by-step:**
1. Paste the snippet.
2. Run — observe the list of errors (missing `category`, `urgency` not in enum).
3. Replace `bad_json` with a fully-shaped payload and confirm validation passes.

### Exercise 3 — Call OpenAI with `response_format={"type": "json_object"}`

```python
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

SYSTEM = (
    "You classify incoming customer messages. "
    "Always respond with a single JSON object and no other text."
)

USER = "Our login is broken and we cannot reach the dashboard. This is blocking 30 users."

resp = client.chat.completions.create(
    model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
    messages=[
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": USER},
    ],
    response_format={"type": "json_object"},
    temperature=0,
)

raw = resp.choices[0].message.content
print(raw)
print("usage tokens:", resp.usage.total_tokens)
```

**Step-by-step:**
1. Confirm `.env` has `OPENAI_API_KEY`.
2. Run with `uv run python practice.py`.
3. Inspect `raw` — it must be valid JSON, but the *shape* is whatever the model decided.
4. Wrap `raw` with `TriageResult.model_validate_json(raw)` from Exercise 2.

### Exercise 4 — Force a JSON Schema with `response_format` + `TriageResult.model_json_schema()`

```python
import json, os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

# Pydantic gives us a JSON Schema dict for free
schema = TriageResult.model_json_schema()
print(json.dumps(schema, indent=2)[:400], "...")

resp = client.chat.completions.create(
    model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
    messages=[
        {
            "role": "system",
            "content": (
                "You classify incoming customer messages. "
                "Respond with a JSON object that conforms to the supplied schema."
            ),
        },
        {"role": "user", "content": "I want a refund for invoice #44102."},
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "triage_result",
            "schema": schema,
            "strict": True,
        },
    },
    temperature=0,
)

raw = resp.choices[0].message.content
result = TriageResult.model_validate_json(raw)
print(result.model_dump_json(indent=2))
```

**Step-by-step:**
1. Print the schema Pydantic generates — notice enums become `enum: [...]` lists.
2. Pass that schema to OpenAI via `response_format`.
3. Validate `raw` with `TriageResult.model_validate_json(...)` — should always succeed because the model is constrained.
4. Change the user message to "hello" — confirm `urgency` and `category` are still valid values.

### Exercise 5 — Use tool/function calling as an alternate schema mechanism

```python
import json, os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

tools = [{
    "type": "function",
    "function": {
        "name": "triage_message",
        "description": "Classify a customer message into a structured triage result.",
        "parameters": TriageResult.model_json_schema(),
    },
}]

resp = client.chat.completions.create(
    model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
    messages=[{"role": "user", "content": "I was charged twice for order #8821, please refund."}],
    tools=tools,
    tool_choice={"type": "function", "function": {"name": "triage_message"}},
    temperature=0,
)

tool_call = resp.choices[0].message.tool_calls[0]
args_json = tool_call.function.arguments
print("raw args:", args_json)

result = TriageResult.model_validate_json(args_json)
print(result.intent, result.category, result.urgency)
```

**Step-by-step:**
1. Notice the tool's `parameters` is the same JSON Schema Pydantic produced.
2. Force the model to call it with `tool_choice`.
3. The model's "arguments" come back as JSON in `tool_call.function.arguments` — validate before use.
4. Compare this approach with Exercise 4. Both work; pick one consistently per project.

### Exercise 6 — Build a parse-or-retry loop

```python
import os, time
from openai import OpenAI
from pydantic import ValidationError
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

SYSTEM = "Classify customer messages into the supplied JSON schema."

def triage(message: str, max_retries: int = 2) -> TriageResult:
    schema = TriageResult.model_json_schema()
    last_err: Exception | None = None

    for attempt in range(max_retries + 1):
        feedback = "" if last_err is None else (
            f"\n\nYour previous output failed validation: {last_err}. "
            "Fix it and respond with a single JSON object."
        )
        resp = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": SYSTEM + feedback},
                {"role": "user", "content": message},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "triage_result",
                    "schema": schema,
                    "strict": True,
                },
            },
            temperature=0,
        )
        raw = resp.choices[0].message.content
        try:
            return TriageResult.model_validate_json(raw)
        except ValidationError as e:
            last_err = e
            print(f"attempt {attempt}: validation error")
            time.sleep(0.5)

    raise RuntimeError(f"could not produce valid triage after {max_retries+1} attempts: {last_err}")

print(triage("Production DB is down, urgent help needed!").model_dump())
```

**Step-by-step:**
1. Run — first attempt should succeed; the retry branch is for hostile or unusual inputs.
2. To force a retry, deliberately drop `strict: True` (use `response_format={"type": "json_object"}` only) and feed a tricky message.
3. Confirm the loop logs `attempt N: validation error` and either fixes itself or raises `RuntimeError`.
4. **Hard rule:** never return the model's string to the rest of your code without validating.

### Exercise 7 — Write a pytest that validates the schema is honored

```python
# test_triage_schema.py
import json
from pydantic import ValidationError
from practice import TriageResult   # if you keep TriageResult in practice.py

def test_minimal_valid_payload():
    result = TriageResult.model_validate({
        "intent": "complaint",
        "category": "billing",
        "urgency": "high",
        "summary": "Customer was double-charged on order #8821.",
        "entities": ["#8821"],
    })
    assert result.urgency.value == "high"

def test_unknown_urgency_rejected():
    try:
        TriageResult.model_validate({
            "intent": "other",
            "category": "general",
            "urgency": "super-extreme",
            "summary": "This should be rejected because urgency is not in the enum.",
            "entities": [],
        })
    except ValidationError:
        return
    raise AssertionError("expected ValidationError")

def test_summary_too_short_rejected():
    try:
        TriageResult.model_validate({
            "intent": "other",
            "category": "general",
            "urgency": "low",
            "summary": "short",
            "entities": [],
        })
    except ValidationError:
        return
    raise AssertionError("expected ValidationError for short summary")
```

```bash
uv run pytest -q
```

**Step-by-step:**
1. Save as `test_triage_schema.py`.
2. Run `uv run pytest -q`.
3. All three tests should pass; the rejection cases are just as important as the happy path.

---

## Main Lab: `triage_service.py` + FastAPI endpoint (4–5 hours)

### Scenario

Customers send free-text messages via email and chat. The current request tracker in `tracker/` accepts structured input only. Build a **triage endpoint** that accepts raw text and emits a typed `TriageResult` that the rest of your API can safely consume.

### Data Shape

```python
class TriageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    context: dict | None = None  # optional caller-supplied hints

class TriageResponse(BaseModel):
    result: TriageResult
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
```

### Required Endpoints

```
POST /triage           — classify one message, return TriageResult
POST /triage/batch     — classify up to 20 messages in one call
GET  /triage/health    — confirm OpenAI key + model are reachable
```

### Build Steps

**Commit after each step.** Use messages like:
- `feat: TriageResult pydantic model`
- `feat: openai client wrapper`
- `feat: /triage endpoint`
- `feat: batch endpoint`
- `feat: validation + retry loop`

#### Step 1 — Define the schema module

```python
# triage/schema.py
from enum import Enum
from pydantic import BaseModel, Field

class Intent(str, Enum):
    NEW_REQUEST = "new_request"
    STATUS_CHECK = "status_check"
    COMPLAINT = "complaint"
    OTHER = "other"

class Category(str, Enum):
    BILLING = "billing"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    GENERAL = "general"

class Urgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TriageResult(BaseModel):
    intent: Intent
    category: Category
    urgency: Urgency
    summary: str = Field(min_length=10, max_length=240)
    entities: list[str] = Field(default_factory=list)
```

```bash
git add triage/schema.py
git commit -m "feat: TriageResult schema"
```

#### Step 2 — Build a typed OpenAI client wrapper

```python
# triage/llm.py
import os, time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_client = OpenAI()
DEFAULT_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

def call_llm_json(
    system: str,
    user: str,
    schema: dict,
    schema_name: str = "response",
    model: str = DEFAULT_MODEL,
    temperature: float = 0,
) -> tuple[str, int, int, int]:
    """Call the chat model with strict JSON-Schema output. Returns (raw, tok_in, tok_out, latency_ms)."""
    t0 = time.perf_counter()
    resp = _client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": schema_name, "schema": schema, "strict": True},
        },
        temperature=temperature,
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    raw = resp.choices[0].message.content or ""
    return raw, resp.usage.prompt_tokens, resp.usage.completion_tokens, latency_ms
```

#### Step 3 — Implement `triage_message()` with validation + retry

```python
# triage/triage.py
from pydantic import ValidationError
from .schema import TriageResult
from .llm import call_llm_json

SYSTEM = (
    "You are a customer-message triage assistant. "
    "Classify the user's message according to the supplied JSON schema. "
    "Be conservative with urgency: critical is reserved for outages or data loss."
)

def triage_message(message: str, max_retries: int = 2) -> tuple[TriageResult, dict]:
    """Return (TriageResult, metadata). Raises ValueError after retries exhausted."""
    schema = TriageResult.model_json_schema()
    last_err: Exception | None = None
    total_in = total_out = 0
    latency_ms = 0

    for attempt in range(max_retries + 1):
        feedback = "" if last_err is None else (
            f"\n\nYour previous response failed validation: {last_err}. "
            "Respond again with a single JSON object that satisfies the schema."
        )
        raw, tok_in, tok_out, ms = call_llm_json(
            system=SYSTEM + feedback,
            user=message,
            schema=schema,
            schema_name="triage_result",
        )
        total_in += tok_in
        total_out += tok_out
        latency_ms += ms
        try:
            result = TriageResult.model_validate_json(raw)
            meta = {
                "tokens_in": total_in,
                "tokens_out": total_out,
                "latency_ms": latency_ms,
                "attempts": attempt + 1,
            }
            return result, meta
        except ValidationError as e:
            last_err = e

    raise ValueError(f"could not produce valid triage: {last_err}")
```

#### Step 4 — Expose a FastAPI endpoint

```python
# triage/api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .schema import TriageResult
from .triage import triage_message

app = FastAPI(title="triage-service")

class TriageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    context: dict | None = None

class TriageResponse(BaseModel):
    result: TriageResult
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    attempts: int

@app.post("/triage", response_model=TriageResponse)
def triage(req: TriageRequest) -> TriageResponse:
    try:
        result, meta = triage_message(req.message)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return TriageResponse(
        result=result,
        model="gpt-4o-mini",
        tokens_in=meta["tokens_in"],
        tokens_out=meta["tokens_out"],
        latency_ms=meta["latency_ms"],
        attempts=meta["attempts"],
    )

@app.get("/triage/health")
def health() -> dict:
    return {"ok": True, "model": "gpt-4o-mini"}
```

```bash
uv run uvicorn triage.api:app --reload --port 8000
```

Test in another shell:

```bash
curl -s -X POST localhost:8000/triage \
  -H 'content-type: application/json' \
  -d '{"message":"Production DB is down and customers cannot place orders."}' | jq
```

#### Step 5 — Add a batch endpoint that validates each item

```python
# triage/api.py  (append)
from typing import List

class BatchRequest(BaseModel):
    messages: List[str] = Field(min_length=1, max_length=20)

class BatchItem(BaseModel):
    index: int
    ok: bool
    result: TriageResult | None = None
    error: str | None = None
    latency_ms: int = 0

class BatchResponse(BaseModel):
    items: List[BatchItem]
    total_tokens_in: int
    total_tokens_out: int

@app.post("/triage/batch", response_model=BatchResponse)
def triage_batch(req: BatchRequest) -> BatchResponse:
    items: list[BatchItem] = []
    tok_in = tok_out = 0
    for i, msg in enumerate(req.messages):
        try:
            result, meta = triage_message(msg)
            tok_in += meta["tokens_in"]
            tok_out += meta["tokens_out"]
            items.append(BatchItem(index=i, ok=True, result=result,
                                   latency_ms=meta["latency_ms"]))
        except ValueError as e:
            items.append(BatchItem(index=i, ok=False, error=str(e)))
    return BatchResponse(items=items, total_tokens_in=tok_in, total_tokens_out=tok_out)
```

#### Step 6 — Cap retries and add request-level timeout

```python
# triage/triage.py  (replace signature)
import asyncio

async def triage_message_async(message: str, max_retries: int = 2,
                                timeout_s: float = 10.0) -> tuple[TriageResult, dict]:
    return await asyncio.wait_for(
        asyncio.to_thread(triage_message, message, max_retries),
        timeout=timeout_s,
    )
```

Update `/triage` endpoint to call the async version with `await`.

#### Step 7 — Log structured events for every triage

```python
# triage/logging_setup.py
import json, logging, sys

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        for k, v in record.__dict__.items():
            if k in ("args", "msg", "levelname", "levelno", "name", "pathname",
                     "filename", "module", "exc_info", "exc_text", "stack_info",
                     "lineno", "funcName", "created", "msecs", "relativeCreated",
                     "thread", "threadName", "processName", "process", "message"):
                continue
            payload[k] = v
        return json.dumps(payload)

def setup_logging() -> None:
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [h]
    root.setLevel(logging.INFO)
```

Then inside `triage_message`:

```python
import logging
log = logging.getLogger("triage")

# after successful return:
log.info("triage.ok", extra={"tokens_in": total_in, "tokens_out": total_out,
                            "latency_ms": latency_ms, "attempts": attempt + 1})
```

#### Step 8 — Write a pytest that runs the endpoint with a fake LLM

```python
# tests/test_triage_api.py
from fastapi.testclient import TestClient
from triage.api import app
from triage import triage as triage_mod

client = TestClient(app)

def fake_triage_message(message, max_retries=2):
    from triage.schema import TriageResult, Urgency, Category, Intent
    return (
        TriageResult(
            intent=Intent.NEW_REQUEST,
            category=Category.TECHNICAL,
            urgency=Urgency.HIGH,
            summary=f"Fake summary for: {message[:40]}",
            entities=[],
        ),
        {"tokens_in": 5, "tokens_out": 5, "latency_ms": 1, "attempts": 1},
    )

def test_triage_endpoint(monkeypatch):
    monkeypatch.setattr(triage_mod, "triage_message", fake_triage_message)
    r = client.post("/triage", json={"message": "Login is broken"})
    assert r.status_code == 200
    body = r.json()
    assert body["result"]["urgency"] == "high"
    assert body["attempts"] == 1

def test_triage_validation_error_returns_502(monkeypatch):
    def boom(message, max_retries=2):
        raise ValueError("nope")
    monkeypatch.setattr(triage_mod, "triage_message", boom)
    r = client.post("/triage", json={"message": "anything"})
    assert r.status_code == 502
```

```bash
uv run pytest -q
```

#### Step 9 — Save sample requests and outputs as fixtures

```python
# tests/fixtures.py
SAMPLES = [
    "Our production DB is down, customers cannot place orders.",
    "I want a refund for invoice #44102, I was double charged.",
    "Can you tell me the status of REQ-002?",
    "How do I add a teammate to my account?",
]
```

Run them through `/triage/batch` and save the response JSON to `tests/fixtures/triage_sample.json`. These become regression data when you change the schema.

#### Step 10 — Wire the triage endpoint into the tracker

Inside the tracker FastAPI app (Week 5), add a `POST /requests/from-message` endpoint:

```python
from triage.triage import triage_message
from triage.schema import Urgency

PRIORITY_MAP = {
    Urgency.LOW: "low",
    Urgency.MEDIUM: "medium",
    Urgency.HIGH: "high",
    Urgency.CRITICAL: "high",  # capped — humans review
}

@app.post("/requests/from-message")
def create_from_message(req: TriageRequest):
    result, meta = triage_message(req.message)
    new = {
        "id": next_request_id(requests),
        "customer_name": req.context.get("customer_name") if req.context else "unknown",
        "title": result.summary[:80],
        "description": req.message,
        "priority": PRIORITY_MAP[result.urgency],
        "status": "open",
        "category": result.category.value,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    requests.append(new)
    save_requests(requests)
    return {"request": new, "triage": result.model_dump(), "tokens": meta}
```

Now a single free-text submission becomes a structured tracker entry.

#### Step 11 — Update the project README with a usage section

```markdown
# triage-service

Classify customer messages into structured TriageResults.

## Setup
    uv sync
    cp .env.example .env   # fill in OPENAI_API_KEY

## Run
    uv run uvicorn triage.api:app --reload --port 8000

## Test
    uv run pytest -q

## Endpoints
- POST /triage           — classify one message
- POST /triage/batch     — classify up to 20 messages
- GET  /triage/health    — liveness
```

### Required Manual Tests

- [ ] `GET /triage/health` returns `{"ok": true, ...}`
- [ ] `POST /triage` with `"Production DB is down"` returns `urgency` = `critical` or `high`
- [ ] `POST /triage` with `"How do I add a teammate?"` returns `category` = `account`
- [ ] `POST /triage` with an empty message returns `422` from FastAPI
- [ ] `POST /triage/batch` with 5 messages returns 5 items, each with `ok=true`
- [ ] Forcing a `ValidationError` (mock the LLM to return bad JSON) returns `502`
- [ ] Inspect stdout — every successful call logs a `triage.ok` JSON line

### Acceptance Criteria

- [ ] Every LLM response is validated by `TriageResult.model_validate_json` before use
- [ ] `/triage` rejects empty messages with `422`, not `500`
- [ ] `/triage/batch` returns per-item `ok` flags; one bad message does not fail the whole batch
- [ ] Retry loop exists and is covered by a unit test
- [ ] Structured logs include token counts and latency
- [ ] At least 5 meaningful commits
- [ ] You can explain when to choose `response_format=json_schema` vs tool calling

## AI-Off Check (30 minutes)

Without looking at your code, write a function that:

1. Calls the LLM with a strict JSON Schema for `TriageResult`.
2. Validates the response with Pydantic.
3. If validation fails, retries once with the error message appended to the system prompt.
4. Returns `(TriageResult, attempts_used)` or raises after the final failure.

```python
def triage_no_ai_assist(message: str) -> tuple[TriageResult, int]:
    """Skeleton to fill in cold."""
    raise NotImplementedError
```

Compare your version to `triage/triage.py`. The goal is to internalize: **prompt → JSON Schema → validate → retry → structured log**.

## Reflection Questions

After you finish, write answers to these in `REFLECTION.md`:

1. Why is `response_format={"type": "json_object"}` alone **not** enough for a production pipeline?
2. When would you prefer tool/function calling over `response_format=json_schema`?
3. What kinds of inputs cause the validation/retry loop to fail repeatedly? How would you detect them?
4. If the model is allowed to choose new enum values later, what changes in your schema?

## Next Steps

Once you pass all acceptance criteria:

1. Run `uv run pytest -q` and record the output
2. Write reflection answers
3. Commit with message: `docs: week 10 complete`
4. Move to Week 11 (RAG) — you will reuse `TriageResult` as the structured output for the retrieval-augmented agent

---

**Ready?** Start by running:

```bash
uv init
uv add openai pydantic python-dotenv pytest ruff
```

Then follow the learning path above. Good luck! 🎯
