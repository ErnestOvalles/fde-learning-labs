# Week 14: Reliable Tool Use and Function Calling

## Outcome

Harden the tool-calling loop from Weeks 12–13. Build a **production-grade tool dispatcher** that:

1. Validates arguments against Pydantic models before execution
2. Recovers from **hallucinated argument values** (model invents enum values, wrong types, missing required fields)
3. **Retries structured** — sends the validation error back to the model with the schema and asks for a fixed call
4. Supports **parallel tool calls** when the model returns multiple at once
5. Caps runaway loops with explicit timeouts and turn limits
6. Emits structured logs of every attempt, retry, and outcome

## Setup Checklist

- [ ] Reuse `tracker_agent` from Weeks 12–13
- [ ] Reuse `InMemorySessionStore` and `SessionManager` from Week 13
- [ ] `uv add openai pydantic python-dotenv pytest pytest-asyncio ruff`
- [ ] Confirm `uv run pytest -q` is green on Week 13 before starting

### Setup Walkthrough

```bash
cd phase-4-agents/week-14-tool-use
uv init
uv python pin 3.13

uv add openai pydantic python-dotenv pytest pytest-asyncio ruff

# Sanity check
uv run python - <<'PY'
from pydantic import BaseModel, Field, ValidationError
class Args(BaseModel):
    priority: str = Field(pattern="^(low|medium|high)$")
try:
    Args.model_validate({"priority": "URGENT"})
except ValidationError as e:
    print("OK — caught:", e.errors()[0]["msg"])
PY
```

## Learning Path (60–90 minutes)

**Best approach:** Treat every tool call as **untrusted input**. The model is just one of many untrusted sources in your system.

### Learn in this order

1. **Failure modes of tool calling** — wrong shape, missing fields, hallucinated enum values, type confusion, model calls nonexistent tool
2. **Argument validation as a wall** — Pydantic is the gate; nothing runs through
3. **Structured retry** — feed `ValidationError.errors()` back, not free text
4. **Tool whitelisting** — refuse any tool the dispatcher doesn't recognize
5. **Parallel tool calls** — `message.tool_calls` is a list; execute concurrently when independent
6. **Timeouts and circuit breakers** — never let one bad tool hang a turn
7. **Idempotency keys** — make retried side effects safe
8. **Observability** — every attempt logged with model, args, error, decision

### Free Resources

- [OpenAI Function Calling — parallel tool calls](https://platform.openai.com/docs/guides/function-calling/parallel-function-calling)
- [Pydantic ValidationError reference](https://docs.pydantic.dev/latest/errors/validation_errors/)
- [Instructor retry library](https://python.useinstructor.com/) — see how they implement retries
- [Anthropic Tool Use — best practices](https://docs.anthropic.com/en/docs/tool-use)
- [Designing reliable LLM tool loops — LangChain blog](https://blog.langchain.dev/tool-calling-with-langchain/)

**Tip:** A single bad tool call should not blow up an entire turn. Plan for failure on every call.

## Micro-Exercises (45–60 minutes)

Create `practice.py` and work through these:

### Exercise 1 — Define strict argument schemas

```python
# practice.py
from pydantic import BaseModel, Field

class CreateRequestArgs(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    title:         str = Field(min_length=3, max_length=200)
    description:   str = Field(min_length=1, max_length=4000)
    priority:      str = Field(pattern="^(low|medium|high)$")

class UpdateRequestArgs(BaseModel):
    request_id: str = Field(min_length=1, pattern=r"^REQ-\d{3,}$")
    status:     str | None = Field(default=None, pattern="^(open|in_progress|closed)$")
    priority:   str | None = Field(default=None, pattern="^(low|medium|high)$")

class SearchSimilarArgs(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
```

**Step-by-step:**
1. `pattern="^(low|medium|high)$"` — anchor both ends to forbid `"highish"`.
2. `request_id` regex catches `REQ-abc` immediately.
3. Use `Field(default=None)` for optional fields so callers may omit them.

### Exercise 2 — Build a validating dispatcher

```python
from pydantic import ValidationError

TOOLS = {
    "create_request": CreateRequestArgs,
    "update_request": UpdateRequestArgs,
    "search_similar": SearchSimilarArgs,
}

class ToolError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

class ToolDispatcher:
    def __init__(self, implementations: dict[str, callable], schemas: dict[str, type[BaseModel]]):
        self.impls = implementations
        self.schemas = schemas

    def dispatch(self, name: str, raw_args: str) -> str:
        if name not in self.impls:
            raise ToolError("UNKNOWN_TOOL", f"tool '{name}' is not registered")
        schema = self.schemas[name]
        try:
            args = schema.model_validate_json(raw_args or "{}")
        except ValidationError as e:
            raise ToolError("BAD_ARGS", "argument validation failed",
                            details={"errors": e.errors()})
        try:
            return self.impls[name](**args.model_dump(exclude_none=True))
        except Exception as e:
            raise ToolError("TOOL_FAILED", f"tool '{name}' raised: {e}")
```

**Step-by-step:**
1. `ToolError` carries a `code` so the model can react differently per failure.
2. The dispatcher never executes before validating.
3. `details={"errors": e.errors()}` is the structured payload we feed back to the model in the retry.

### Exercise 3 — Test the dispatcher with a hallucinated enum

```python
def fake_create(**kwargs):
    return f"Created {kwargs}"

d = ToolDispatcher({"create_request": fake_create}, TOOLS)

# Valid call
print(d.dispatch("create_request",
                 '{"customer_name":"Acme","title":"Login broken","description":"...","priority":"high"}'))

# Hallucinated priority
try:
    d.dispatch("create_request",
               '{"customer_name":"Acme","title":"Login broken","description":"...","priority":"urgent"}')
except ToolError as e:
    print("caught:", e.code, "->", e.details["errors"][0]["msg"])

# Unknown tool
try:
    d.dispatch("delete_database", "{}")
except ToolError as e:
    print("caught:", e.code)
```

**Step-by-step:**
1. The valid call returns a string.
2. The hallucinated priority raises `ToolError("BAD_ARGS", ...)` with the enum error in `details`.
3. The unknown tool raises `ToolError("UNKNOWN_TOOL", ...)`.

### Exercise 4 — Build the structured retry helper

```python
import os
from openai import OpenAI

client = OpenAI()

def retry_with_schema_feedback(
    tool_name: str,
    raw_args: str,
    error: ToolError,
    schema: type[BaseModel],
    original_messages: list[dict],
) -> tuple[str, str]:
    """Ask the model to fix the args given the validation error. Returns (fixed_args, model_text)."""
    schema_dict = schema.model_json_schema()
    prompt = (
        f"Your previous call to `{tool_name}` failed validation with:\n"
        f"{error.details}\n\n"
        f"Re-emit ONLY the JSON arguments for `{tool_name}` that conform to this schema:\n"
        f"{schema_dict}\n\n"
        "Do not include any other text."
    )
    resp = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        messages=original_messages + [{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content, resp.choices[0].message.content
```

**Step-by-step:**
1. The error includes the precise Pydantic error (e.g., `priority: string does not match regex ...`).
2. The schema is included verbatim — the model has everything it needs to fix the call.
3. We use `response_format=json_object` to avoid another parse failure on the way out.

### Exercise 5 — Glue it into the agent loop

```python
def run_reliable(user_msg: str, dispatcher: ToolDispatcher,
                 tools_spec: list[dict], max_turns: int = 6,
                 max_retries_per_call: int = 2) -> str:
    messages = [
        {"role": "system", "content": "You are a tracker agent. Use tools when needed."},
        {"role": "user", "content": user_msg},
    ]

    for turn in range(max_turns):
        resp = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=messages, tools=tools_spec, tool_choice="auto", temperature=0,
        )
        msg = resp.choices[0].message
        messages.append(msg)
        if not msg.tool_calls:
            return msg.content or ""

        for call in msg.tool_calls:
            args = call.function.arguments or "{}"
            for attempt in range(max_retries_per_call + 1):
                try:
                    result = dispatcher.dispatch(call.function.name, args)
                    messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
                    break
                except ToolError as e:
                    if e.code == "UNKNOWN_TOOL" or attempt == max_retries_per_call:
                        messages.append({"role": "tool", "tool_call_id": call.id,
                                         "content": f"ERROR [{e.code}]: {e.message}"})
                        break
                    if e.code == "BAD_ARGS" and call.function.name in dispatcher.schemas:
                        fixed, _ = retry_with_schema_feedback(
                            call.function.name, args, e,
                            dispatcher.schemas[call.function.name], messages,
                        )
                        args = fixed   # loop again with corrected args
                    else:
                        messages.append({"role": "tool", "tool_call_id": call.id,
                                         "content": f"ERROR [{e.code}]: {e.message}"})
                        break

    return "Agent exceeded max turns."
```

**Step-by-step:**
1. The inner `attempt` loop gives the model up to `max_retries_per_call` chances to fix a single bad call.
2. `UNKNOWN_TOOL` is treated as terminal — retrying won't fix a hallucinated tool name.
3. `BAD_ARGS` triggers `retry_with_schema_feedback` to ask the model for corrected args.

### Exercise 6 — Parallel tool calls

```python
def execute_parallel(calls: list, dispatcher: ToolDispatcher) -> list[str]:
    """Execute independent tool calls concurrently."""
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(max_workers=min(8, len(calls))) as ex:
        futures = [ex.submit(dispatcher.dispatch, c.function.name,
                              c.function.arguments) for c in calls]
        results = []
        for f in futures:
            try:
                results.append(f.result())
            except ToolError as e:
                results.append(f"ERROR [{e.code}]: {e.message}")
        return results
```

Wire it into the loop:

```python
for call in msg.tool_calls:
    if len(msg.tool_calls) > 1 and are_independent(msg.tool_calls):
        outputs = execute_parallel(msg.tool_calls, dispatcher)
        for c, out in zip(msg.tool_calls, outputs):
            messages.append({"role": "tool", "tool_call_id": c.id, "content": out})
        break  # done with this turn
    else:
        # sequential, validated path
        ...
```

`are_independent` is a domain check — for now, treat any pair that don't reference each other's outputs as independent.

### Exercise 7 — End-to-end mock test

```python
# tests/test_reliable.py
import os, sys, types
sys.path.insert(0, ".")
from practice import (TOOLS, ToolDispatcher, ToolError, CreateRequestArgs,
                       run_reliable, client)

# Stub OpenAI client to avoid network
class FakeMessage:
    def __init__(self, content="", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []

class FakeChoice:
    def __init__(self, message, usage):
        self.message = message
        self.usage = usage

class FakeResp:
    def __init__(self, message, usage):
        self.choices = [FakeChoice(message, usage)]
        self.usage = usage

class FakeUsage:
    def __init__(self): self.prompt_tokens = 0; self.completion_tokens = 0

def make_resp(content="", tool_calls=None):
    return FakeResp(FakeMessage(content=content, tool_calls=tool_calls), FakeUsage())

def test_hallucinated_priority_recovers(monkeypatch):
    # First call returns "urgent" (bad), second returns "high" (good)
    bad_call  = type("TC", (), {"id": "1", "function": type("F", (), {
        "name": "create_request",
        "arguments": '{"customer_name":"Acme","title":"Login broken","description":"x","priority":"urgent"}',
    })()})()
    good_call = type("TC", (), {"id": "1", "function": type("F", (), {
        "name": "create_request",
        "arguments": '{"customer_name":"Acme","title":"Login broken","description":"x","priority":"high"}',
    })()})()

    msgs = [make_resp(tool_calls=[bad_call]),
            make_resp(tool_calls=[good_call]),
            make_resp(content="Created.")]

    monkeypatch.setattr(client.chat.completions, "create", lambda **kw: msgs.pop(0))

    def fake_create(**kwargs):
        return f"Created for {kwargs['customer_name']}"

    d = ToolDispatcher({"create_request": fake_create}, TOOLS)
    out = run_reliable("create one", d, [])
    assert "Created" in out

def test_unknown_tool_does_not_retry(monkeypatch):
    bad = type("TC", (), {"id": "1", "function": type("F", (), {
        "name": "delete_database", "arguments": "{}"})()})()
    final = type("TC", (), {"id": "1", "function": type("F", (), {
        "name": "delete_database", "arguments": "{}"})()})()
    msgs = [make_resp(tool_calls=[bad]), make_resp(content="Sorry, can't do that.")]
    monkeypatch.setattr(client.chat.completions, "create", lambda **kw: msgs.pop(0))
    d = ToolDispatcher({"create_request": lambda **kw: "ok"}, TOOLS)
    out = run_reliable("delete the db", d, [])
    assert "Sorry" in out
```

```bash
uv run pytest -q
```

---

## Main Lab: `reliable_agent` (4–5 hours)

### Scenario

Week 12's agent runs tool calls but trusts the model too much. Production needs:
- Hallucinated enum values are caught and recovered
- Wrong request IDs (e.g., `REQ-12` instead of `REQ-012`) are fixed before being sent
- A `delete_*` hallucination is refused immediately
- Two independent searches in one turn run in parallel
- Every retry is logged with the validation error

### Data Shape

```python
class ToolAttempt(BaseModel):
    call_id: str
    tool: str
    attempt: int
    args: dict
    outcome: Literal["ok", "retry", "fail"]
    error_code: str | None = None
    error_message: str | None = None
    latency_ms: int

class AgentRun(BaseModel):
    final: str
    attempts: list[ToolAttempt]
    tokens_in: int
    tokens_out: int
    duration_ms: int
```

### Required Endpoints

```
POST /reliable/chat     — runs the user message through the reliable agent
GET  /reliable/health   — confirms tool registry + dispatcher reachable
```

### Build Steps

**Commit after each step.** Use messages like:
- `feat: tool schemas + dispatcher`
- `feat: structured retry on BAD_ARGS`
- `feat: parallel tool execution`
- `feat: timeout per call`
- `feat: structured logging of every attempt`

#### Step 1 — Centralize tool schemas and implementations

```python
# reliable/tools.py
from pydantic import BaseModel, Field
from typing import Literal

class CreateRequestArgs(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    title:         str = Field(min_length=3, max_length=200)
    description:   str = Field(min_length=1, max_length=4000)
    priority:      Literal["low", "medium", "high"]

class UpdateRequestArgs(BaseModel):
    request_id: str = Field(pattern=r"^REQ-\d{3,}$")
    status:     Literal["open", "in_progress", "closed"] | None = None
    priority:   Literal["low", "medium", "high"] | None = None

class SearchSimilarArgs(BaseModel):
    question: str = Field(min_length=3, max_length=2000)

class ListRequestsArgs(BaseModel):
    status:   Literal["open", "in_progress", "closed"] | None = None
    priority: Literal["low", "medium", "high"] | None = None

SCHEMAS = {
    "create_request": CreateRequestArgs,
    "update_request": UpdateRequestArgs,
    "search_similar": SearchSimilarArgs,
    "list_requests":  ListRequestsArgs,
}

# JSON Schema list for OpenAI
def tools_for_openai() -> list[dict]:
    out = []
    for name, schema in SCHEMAS.items():
        out.append({"type": "function", "function": {
            "name": name,
            "description": schema.__doc__ or name,
            "parameters": schema.model_json_schema(),
        }})
    return out
```

`schema.__doc__` is `None` here — replace with explicit descriptions in a real schema file.

#### Step 2 — Build the dispatcher with timeout

```python
# reliable/dispatcher.py
import time, concurrent.futures as cf
from pydantic import BaseModel, ValidationError
from typing import Callable

class ToolError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

class ToolDispatcher:
    def __init__(self, impls: dict[str, Callable], schemas: dict[str, type[BaseModel]],
                 timeout_s: float = 8.0, max_workers: int = 8):
        self.impls = impls
        self.schemas = schemas
        self.timeout_s = timeout_s
        self.max_workers = max_workers

    def dispatch_one(self, name: str, raw_args: str) -> str:
        if name not in self.impls:
            raise ToolError("UNKNOWN_TOOL", f"tool '{name}' is not registered")
        schema = self.schemas[name]
        try:
            args = schema.model_validate_json(raw_args or "{}")
        except ValidationError as e:
            raise ToolError("BAD_ARGS", "argument validation failed",
                            details={"errors": e.errors()})
        try:
            with cf.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(self.impls[name], **args.model_dump(exclude_none=True))
                return fut.result(timeout=self.timeout_s)
        except cf.TimeoutError:
            raise ToolError("TIMEOUT", f"tool '{name}' exceeded {self.timeout_s}s")
        except ToolError:
            raise
        except Exception as e:
            raise ToolError("TOOL_FAILED", f"tool '{name}' raised: {e}")

    def dispatch_many(self, calls: list[dict]) -> list[str]:
        """calls is [{name, arguments}] in the order we want results back."""
        results: list[str | None] = [None] * len(calls)
        with cf.ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            futures = {ex.submit(self.dispatch_one, c["name"], c["arguments"]): i
                       for i, c in enumerate(calls)}
            for fut in cf.as_completed(futures, timeout=self.timeout_s * 2):
                i = futures[fut]
                try:
                    results[i] = fut.result()
                except ToolError as e:
                    results[i] = f"ERROR [{e.code}]: {e.message}"
        return results  # type: ignore[return-value]
```

#### Step 3 — Build the structured retry helper

```python
# reliable/retry.py
import os
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv
from reliable.dispatcher import ToolError

load_dotenv()
_client = OpenAI()

def fix_args(tool_name: str, raw_args: str, error: ToolError,
             schema: type[BaseModel], prior_messages: list[dict]) -> tuple[str, int]:
    """Ask the model to fix invalid arguments; return (fixed_args, tokens_used)."""
    schema_dict = schema.model_json_schema()
    prompt = (
        f"Your previous call to `{tool_name}` failed validation:\n"
        f"{error.details}\n\n"
        f"Re-emit ONLY a JSON object that conforms to this schema:\n"
        f"{schema_dict}\n"
        f"Do not add commentary."
    )
    resp = _client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        messages=prior_messages + [{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return resp.choices[0].message.content or "{}", resp.usage.total_tokens
```

#### Step 4 — Build the reliable loop

```python
# reliable/loop.py
import os, time
from openai import OpenAI
from dotenv import load_dotenv
from reliable.dispatcher import ToolDispatcher, ToolError
from reliable.retry import fix_args
from reliable.tools import tools_for_openai
from reliable.schemas import AgentRun, ToolAttempt

load_dotenv()
_client = OpenAI()
MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

SYSTEM = "You are a tracker agent. Use the registered tools when needed."

def run(user_msg: str, dispatcher: ToolDispatcher,
        max_turns: int = 6, max_retries_per_call: int = 2) -> AgentRun:
    t0 = time.perf_counter()
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user",   "content": user_msg}]
    attempts: list[ToolAttempt] = []
    tok_in = tok_out = 0

    for turn in range(max_turns):
        resp = _client.chat.completions.create(
            model=MODEL, messages=messages, tools=tools_for_openai(),
            tool_choice="auto", temperature=0,
        )
        tok_in += resp.usage.prompt_tokens
        tok_out += resp.usage.completion_tokens
        msg = resp.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            return AgentRun(final=msg.content or "",
                            attempts=attempts, tokens_in=tok_in, tokens_out=tok_out,
                            duration_ms=int((time.perf_counter() - t0) * 1000))

        # Independent calls (heuristic: no shared request_id ref) run in parallel
        independent = len(msg.tool_calls) > 1
        if independent:
            t_call = time.perf_counter()
            results = dispatcher.dispatch_many([
                {"name": c.function.name, "arguments": c.function.arguments or "{}"}
                for c in msg.tool_calls
            ])
            latency = int((time.perf_counter() - t_call) * 1000)
            for c, r in zip(msg.tool_calls, results):
                attempts.append(ToolAttempt(
                    call_id=c.id, tool=c.function.name, attempt=1,
                    args=_safe_args(c.function.arguments),
                    outcome="ok" if not r.startswith("ERROR") else "fail",
                    error_code=_extract_code(r) or None,
                    error_message=r if r.startswith("ERROR") else None,
                    latency_ms=latency,
                ))
                messages.append({"role": "tool", "tool_call_id": c.id, "content": r})
        else:
            for call in msg.tool_calls:
                _handle_call(call, messages, dispatcher, attempts)

    return AgentRun(final="Agent exceeded max turns.", attempts=attempts,
                    tokens_in=tok_in, tokens_out=tok_out,
                    duration_ms=int((time.perf_counter() - t0) * 1000))


def _handle_call(call, messages, dispatcher: ToolDispatcher,
                 attempts: list[ToolAttempt], max_retries: int = 2) -> None:
    args = call.function.arguments or "{}"
    name = call.function.name
    for attempt in range(max_retries + 1):
        t0 = time.perf_counter()
        try:
            result = dispatcher.dispatch_one(name, args)
            latency = int((time.perf_counter() - t0) * 1000)
            attempts.append(ToolAttempt(
                call_id=call.id, tool=name, attempt=attempt + 1,
                args=_safe_args(args), outcome="ok", latency_ms=latency,
            ))
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
            return
        except ToolError as e:
            latency = int((time.perf_counter() - t0) * 1000)
            if e.code == "UNKNOWN_TOOL" or attempt == max_retries:
                attempts.append(ToolAttempt(
                    call_id=call.id, tool=name, attempt=attempt + 1,
                    args=_safe_args(args), outcome="fail",
                    error_code=e.code, error_message=e.message, latency_ms=latency,
                ))
                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "content": f"ERROR [{e.code}]: {e.message}"})
                return
            if e.code == "BAD_ARGS" and name in dispatcher.schemas:
                fixed, _ = fix_args(name, args, e, dispatcher.schemas[name], messages)
                args = fixed
                attempts.append(ToolAttempt(
                    call_id=call.id, tool=name, attempt=attempt + 1,
                    args=_safe_args(args), outcome="retry",
                    error_code=e.code, error_message=str(e.details), latency_ms=latency,
                ))
            else:
                attempts.append(ToolAttempt(
                    call_id=call.id, tool=name, attempt=attempt + 1,
                    args=_safe_args(args), outcome="fail",
                    error_code=e.code, error_message=e.message, latency_ms=latency,
                ))
                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "content": f"ERROR [{e.code}]: {e.message}"})
                return


def _safe_args(raw: str | None) -> dict:
    import json
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {"_raw": raw}


def _extract_code(result: str) -> str | None:
    if not result.startswith("ERROR"):
        return None
    rest = result[len("ERROR ["):]
    end = rest.find("]")
    return rest[:end] if end != -1 else None
```

#### Step 5 — Wire FastAPI endpoint

```python
# reliable/api.py
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from reliable.loop import run
from reliable.dispatcher import ToolDispatcher
from reliable.tools import SCHEMAS

# Real implementations from Week 12
from agent.impl import (search_similar, create_request, update_request, list_requests)

app = FastAPI(title="reliable-agent")

def get_dispatcher() -> ToolDispatcher:
    return ToolDispatcher(
        impls={
            "create_request": create_request,
            "update_request": update_request,
            "search_similar": search_similar,
            "list_requests":  list_requests,
        },
        schemas=SCHEMAS,
        timeout_s=8.0,
    )

class ReliableChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)

@app.post("/reliable/chat")
def chat(req: ReliableChatRequest, dispatcher: ToolDispatcher = Depends(get_dispatcher)) -> dict:
    try:
        result = run(req.message, dispatcher)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return result.model_dump()

@app.get("/reliable/health")
def health() -> dict:
    return {"ok": True, "tools": list(SCHEMAS.keys())}
```

```bash
uv run uvicorn reliable.api:app --reload --port 8004
```

Smoke test:

```bash
curl -s -X POST localhost:8004/reliable/chat \
  -H 'content-type: application/json' \
  -d '{"message":"Create a high-priority request for Acme Corp: login is broken."}' | jq
```

#### Step 6 — Add timeout observability

```python
# inside _handle_call, log structured events
import logging, json
log = logging.getLogger("reliable")

log.info("tool.attempt", extra={
    "tool": name, "attempt": attempt + 1,
    "outcome": "ok" if not e else "retry",
    "latency_ms": latency,
    "error_code": getattr(e, "code", None),
})
```

Set up JSON logging once at import time:

```python
# reliable/log_setup.py
import logging, sys, json

class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {"ts": self.formatTime(record), "level": record.levelname,
                   "msg": record.getMessage()}
        for k, v in record.__dict__.items():
            if k.startswith("_") or k in ("args", "msg", "levelname", "name"):
                continue
            payload[k] = v
        return json.dumps(payload)

def setup():
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [h]
    root.setLevel(logging.INFO)
```

#### Step 7 — Test against real hallucination cases

```python
# tests/test_reliable_loop.py
import json
from unittest.mock import patch
from reliable.dispatcher import ToolDispatcher, ToolError
from reliable.tools import SCHEMAS

def test_hallucinated_priority_is_caught():
    def fake_create(**kw):
        if kw["priority"] not in ("low", "medium", "high"):
            raise ValueError("bad priority")
        return f"Created {kw['customer_name']}"

    d = ToolDispatcher({"create_request": fake_create}, SCHEMAS)
    try:
        d.dispatch_one("create_request",
                       '{"customer_name":"Acme","title":"Login broken",'
                       '"description":"...","priority":"URGENT"}')
    except ToolError as e:
        assert e.code == "BAD_ARGS"
        assert any("priority" in err["loc"] for err in e.details["errors"])

def test_unknown_tool_is_refused():
    d = ToolDispatcher({"create_request": lambda **kw: "ok"}, SCHEMAS)
    try:
        d.dispatch_one("delete_database", "{}")
    except ToolError as e:
        assert e.code == "UNKNOWN_TOOL"

def test_timeout_raises():
    import time
    def slow(**kw):
        time.sleep(2)
        return "ok"
    d = ToolDispatcher({"create_request": slow}, SCHEMAS, timeout_s=0.5)
    try:
        d.dispatch_one("create_request",
                       '{"customer_name":"A","title":"abc","description":"x","priority":"high"}')
    except ToolError as e:
        assert e.code == "TIMEOUT"
```

```bash
uv run pytest -q
```

#### Step 8 — Add idempotency keys for retried side effects

```python
import uuid

def make_idempotency_key(call_id: str, attempt: int) -> str:
    """Stable across attempts of the SAME call; different across calls."""
    return f"{call_id}:{attempt}"

# Wire it into create_request / update_request via header
import httpx
def create_request_idempotent(call_id: str, attempt: int, **payload):
    headers = {"Idempotency-Key": make_idempotency_key(call_id, attempt)}
    r = httpx.post(f"{TRACKER}/requests", json=payload, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()
```

If a retry re-runs `create_request` for the same `call_id`, the tracker returns the existing record instead of creating a duplicate.

#### Step 9 — Add metrics

```python
# reliable/metrics.py
from collections import Counter
import threading

class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.attempts_total = Counter()
        self.outcomes = Counter()
        self.latency_ms_total = 0
        self.latency_count = 0

    def record(self, tool: str, outcome: str, latency_ms: int):
        with self._lock:
            self.attempts_total[tool] += 1
            self.outcomes[outcome] += 1
            self.latency_ms_total += latency_ms
            self.latency_count += 1

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "attempts": dict(self.attempts_total),
                "outcomes": dict(self.outcomes),
                "avg_latency_ms": (self.latency_ms_total / self.latency_count
                                    if self.latency_count else 0),
            }
```

Expose via `GET /reliable/metrics`. Reset is intentionally not exposed — restart the process.

#### Step 10 — Document

```markdown
# reliable-agent

Hardened tool-calling agent with validation, retries, parallel execution, and observability.

## Setup
    uv sync
    cp .env.example .env
    uv run uvicorn reliable.api:app --reload --port 8004

## Endpoints
- POST /reliable/chat       — run a message through the reliable agent
- GET  /reliable/health     — liveness + tool list
- GET  /reliable/metrics    — counters + avg latency

## Failure Handling
- BAD_ARGS       → structured retry with schema feedback, up to 2 attempts
- UNKNOWN_TOOL   → refused immediately, no retry
- TIMEOUT        → tool-level timeout, fed back as ERROR
- TOOL_FAILED    → tool exception surfaced, fed back as ERROR
- Idempotency keys attached on every mutating call
```

### Required Manual Tests

- [ ] Ask the agent to "delete everything" — `UNKNOWN_TOOL` appears in `attempts`
- [ ] Force a hallucinated priority — observe one `outcome=retry` followed by `outcome=ok`
- [ ] Two parallel searches in one prompt complete in roughly max(latencies), not sum
- [ ] A slow tool (sleep 5s) is aborted with `outcome=fail, error_code=TIMEOUT`
- [ ] Retried `create_request` does not duplicate the tracker row (idempotency)
- [ ] `GET /reliable/metrics` shows non-zero `attempts` after one chat call
- [ ] Logs are valid JSON with `tool.attempt` events

### Acceptance Criteria

- [ ] Every tool call is validated against a Pydantic schema before execution
- [ ] `BAD_ARGS` triggers structured retry with schema + error feedback
- [ ] `UNKNOWN_TOOL` is refused without retry
- [ ] Parallel tool calls execute concurrently via `ThreadPoolExecutor`
- [ ] Each tool has an explicit timeout (default 8s)
- [ ] Idempotency keys attached to mutating calls
- [ ] Every attempt is logged with `tool`, `attempt`, `outcome`, `latency_ms`
- [ ] At least 5 meaningful commits
- [ ] You can explain why `BAD_ARGS` is retryable but `UNKNOWN_TOOL` is not

## AI-Off Check (30 minutes)

Without looking at your code, write a function `dispatch_with_retry(name, raw_args, dispatcher, schema, model_call)` that:

1. Validates `raw_args` against `schema`.
2. On validation failure, calls `model_call(schema_json, error_details)` to get fixed args.
3. Retries up to 2 times.
4. Returns `(result, attempts_made)` or raises after exhaustion.

```python
def dispatch_with_retry(name, raw_args, dispatcher, schema, model_call):
    """Skeleton to fill in cold."""
    raise NotImplementedError
```

Compare with `_handle_call` in `reliable/loop.py`. The goal is to internalize the validated-retry pattern.

## Reflection Questions

After you finish, write answers to these in `REFLECTION.md`:

1. Why is "structured retry" better than "free-text retry"?
2. When is parallelism worth it for tool calls?
3. How do you decide a reasonable per-tool timeout?
4. What failure modes does this loop still NOT handle?

## Next Steps

Once you pass all acceptance criteria:

1. Run `uv run pytest -q` and save the output
2. Write reflection answers
3. Commit with message: `docs: week 14 complete`
4. Move to Week 15 (Evaluation) — you will build the eval suite that proves this loop is reliable

---

**Ready?** Start by running:

```bash
uv init
uv add openai pydantic python-dotenv pytest pytest-asyncio ruff
```

Then follow the learning path above. Good luck! 🎯
