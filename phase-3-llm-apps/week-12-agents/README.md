# Week 12: Agents and Tool Calling

## Outcome

Build an **AI agent** that can reason multi-step and call your tracker API as a tool. The agent receives a natural-language request like *"Create a high-priority request for Acme Corp: their login is broken"*, decides which tool to call, supplies the right arguments, and replies with a human-readable confirmation.

You will implement the same agent **twice**: once with **raw OpenAI function calling** and once with **LangChain's tool-calling agent**, so you can compare the two abstractions.

## Setup Checklist

- [ ] Reuse the `tracker` FastAPI app from Weeks 5–6
- [ ] Reuse the `triage-service` from Week 10
- [ ] Reuse the `rag-service` from Week 11
- [ ] `uv add openai langchain langchain-openai python-dotenv httpx pytest ruff`
- [ ] Confirm the tracker is reachable at `http://localhost:8000` and the RAG service at `:8001`

### Setup Walkthrough

```bash
cd phase-3-llm-apps/week-12-agents
uv init
uv python pin 3.13

uv add openai langchain langchain-openai python-dotenv httpx pytest ruff

cat > .env <<'EOF'
OPENAI_API_KEY=***
LLM_MODEL=gpt-4o-mini
TRACKER_URL=http://localhost:8000
RAG_URL=http://localhost:8001
EOF

echo ".env" >> .gitignore
git add .gitignore
git commit -m "chore: ignore .env"
```

```bash
# Confirm tracker is up
curl -s localhost:8000/health
```

## Learning Path (60–90 minutes)

**Best approach:** Build the raw OpenAI version first. The library abstractions only make sense once you've felt the pain they remove.

### Learn in this order

1. **What an agent is** — a loop: model decides → tool runs → result fed back → model decides again
2. **Tool schemas** — JSON Schema for inputs, plus a name and description
3. **Single tool call** — `tool_choice={"type": "function", "function": {"name": "..."}}`
4. **Multi-turn tool loop** — keep calling the model until it returns a final assistant message (no `tool_calls`)
5. **Argument validation** — Pydantic-validate tool arguments before running the tool
6. **Error recovery** — feed tool errors back to the model so it can try again
7. **LangChain equivalent** — `create_tool_calling_agent` + `AgentExecutor`
8. **Tradeoffs** — control vs convenience, debugging, observability

### Free Resources

- [OpenAI Function Calling Guide](https://platform.openai.com/docs/guides/function-calling)
- [OpenAI Agents SDK (Python)](https://openai.github.io/openai-agents-python/) — newer official SDK, very small
- [LangChain Tool Calling](https://python.langchain.com/docs/how_to/tool_calling/)
- [LangChain create_tool_calling_agent](https://python.langchain.com/docs/how_to/agent_executor/)
- [LlamaIndex Function Calling](https://docs.llamaindex.ai/en/stable/examples/agent/agent/)

**Tip:** A common mistake is letting the model invent tools. Whitelist tools at the orchestrator level and refuse anything else.

## Micro-Exercises (45–60 minutes)

Create `practice.py` and work through these:

### Exercise 1 — Define three tools as plain dicts

```python
# practice.py
import json, os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_request",
            "description": "Create a new customer support request in the tracker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "title":         {"type": "string"},
                    "description":   {"type": "string"},
                    "priority":      {"type": "string", "enum": ["low", "medium", "high"]},
                },
                "required": ["customer_name", "title", "description", "priority"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_requests",
            "description": "List requests, optionally filtered by status.",
            "parameters": {
                "type": "object",
                "properties": {"status": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_similar",
            "description": "Search past requests that look like the given text.",
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
            },
        },
    },
]

print(f"defined {len(TOOLS)} tools")
print(json.dumps(TOOLS[0], indent=2)[:300], "...")
```

**Step-by-step:**
1. Notice how the schema for each tool is plain JSON Schema — no magic.
2. The `enum` on `priority` is what constrains the model.
3. Descriptions matter: the model reads them to decide *which* tool to use.

### Exercise 2 — Get a tool call from a single prompt

```python
resp = client.chat.completions.create(
    model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
    messages=[
        {"role": "system", "content": "Use the provided tools when appropriate."},
        {"role": "user", "content":
         "Create a high-priority request for Acme Corp: their login is broken."},
    ],
    tools=TOOLS,
    tool_choice="auto",
    temperature=0,
)

msg = resp.choices[0].message
print("content:", msg.content)
print("tool_calls:", msg.tool_calls)

if msg.tool_calls:
    call = msg.tool_calls[0]
    print("name:", call.function.name)
    print("args:", call.function.arguments)
```

**Step-by-step:**
1. Run — the model should pick `create_request` with priority `high`.
2. Set `tool_choice="none"` and rerun — observe the model tries to answer in plain text.
3. Try `tool_choice={"type": "function", "function": {"name": "search_similar"}}` and observe the forced choice.

### Exercise 3 — Validate tool arguments with Pydantic before running

```python
from pydantic import BaseModel, Field, ValidationError

class CreateRequestArgs(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    title:         str = Field(min_length=3, max_length=200)
    description:   str = Field(min_length=1, max_length=4000)
    priority:      str = Field(pattern="^(low|medium|high)$")

raw_args = '{"customer_name":"Acme","title":"Login broken","description":"Half the team cannot log in.","priority":"urgent"}'

try:
    args = CreateRequestArgs.model_validate_json(raw_args)
    print("valid:", args)
except ValidationError as e:
    print("invalid:", e)
```

**Step-by-step:**
1. Run — `"priority": "urgent"` fails the regex.
2. Fix the priority to `"high"` and confirm validation passes.
3. This is the wall between the LLM and your code — keep it.

### Exercise 4 — Implement a fake tool dispatcher

```python
from pydantic import BaseModel

class ToolResult(BaseModel):
    ok: bool
    output: str

def dispatch(name: str, raw_args: str) -> ToolResult:
    if name == "create_request":
        args = CreateRequestArgs.model_validate_json(raw_args)
        return ToolResult(ok=True, output=f"Created REQ-{hash(args.title) & 0xfff:03x} for {args.customer_name}.")
    if name == "list_requests":
        return ToolResult(ok=True, output="(stub) 3 open requests, 1 closed.")
    if name == "search_similar":
        return ToolResult(ok=True, output="(stub) Top match: REQ-042 about login failures.")
    return ToolResult(ok=False, output=f"unknown tool: {name}")
```

```bash
uv run python - <<'PY'
from practice import dispatch
print(dispatch("create_request", '{"customer_name":"Acme","title":"Login broken","description":"Half the team cannot log in.","priority":"high"}').output)
PY
```

### Exercise 5 — Build the multi-turn tool loop

```python
def run_agent(user_msg: str, max_turns: int = 6) -> str:
    messages = [
        {"role": "system",
         "content": "You are a tracker agent. Use the provided tools when needed. "
                    "When done, give a short confirmation to the user."},
        {"role": "user", "content": user_msg},
    ]
    for turn in range(max_turns):
        resp = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=messages, tools=TOOLS, tool_choice="auto", temperature=0,
        )
        msg = resp.choices[0].message
        messages.append(msg)  # assistant turn

        # No tool call → final answer
        if not msg.tool_calls:
            return msg.content or ""

        # Execute every tool call in this turn
        for call in msg.tool_calls:
            result = dispatch(call.function.name, call.function.arguments)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": result.output if result.ok else f"ERROR: {result.output}",
            })

    return "Agent exceeded max turns without producing a final answer."

print(run_agent("Create a high-priority request for Acme Corp: login is broken."))
print("---")
print(run_agent("Search for past requests similar to 'invoice PDF blank'."))
```

**Step-by-step:**
1. Run — observe two-turn behavior: tool call, then final confirmation.
2. Try a multi-step prompt: *"Find similar requests, then create one if there isn't already a match."* — the loop should make two tool calls.
3. Inject an error: change `dispatch` to return `ok=False` for `search_similar` — the model should adapt.

### Exercise 6 — Same agent with LangChain

```python
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor

@tool
def create_request_lc(customer_name: str, title: str, description: str, priority: str) -> str:
    """Create a new customer support request. priority must be low, medium, or high."""
    args = CreateRequestArgs(customer_name=customer_name, title=title,
                             description=description, priority=priority)
    return dispatch("create_request", args.model_dump_json()).output

@tool
def list_requests_lc(status: str = "") -> str:
    """List requests, optionally filtered by status."""
    return dispatch("list_requests", json.dumps({"status": status})).output

@tool
def search_similar_lc(question: str) -> str:
    """Search past requests similar to the given text."""
    return dispatch("search_similar", json.dumps({"question": question})).output

llm = ChatOpenAI(model=os.getenv("LLM_MODEL", "gpt-4o-mini"), temperature=0)
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a tracker agent. Use tools when needed."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, [create_request_lc, list_requests_lc, search_similar_lc], prompt)
executor = AgentExecutor(agent=agent, tools=[create_request_lc, list_requests_lc, search_similar_lc],
                          max_iterations=6, verbose=True)

print(executor.invoke({"input": "Create a high-priority request for Acme Corp: login is broken."})["output"])
```

**Step-by-step:**
1. Run — `verbose=True` shows every intermediate step.
2. Notice how `@tool` and type hints replace the manual JSON Schema.
3. Compare the line count to the raw version: LangChain is shorter but more opaque.

### Exercise 7 — Compare the two on the same prompt

```python
PROMPT = "List all open requests, then create a high-priority one for Acme Corp about invoice PDFs being blank."

print("RAW:", run_agent(PROMPT))
print()
print("LANGCHAIN:", executor.invoke({"input": PROMPT})["output"])
```

**Step-by-step:**
1. Both should reach the same end state, but the LangChain path will emit more verbose logs.
2. Note the difference in failure modes — if `dispatch` returns an error, LangChain surfaces it differently than your manual loop.

---

## Main Lab: `tracker_agent` (4–5 hours)

### Scenario

The success team wants a single Slack-style command: *"Tell me what's similar to this new customer message and log it."* Build an agent that can:

1. **Search** for similar past requests (`/rag/query` from Week 11)
2. **Create** new requests (`POST /requests` from the tracker)
3. **Update** status (`PATCH /requests/{id}`)
4. **List** requests with filters
5. **Refuse** anything not whitelisted

Provide both implementations behind a single FastAPI endpoint:

```
POST /agent      — runs the request through the agent and returns the final answer + trace
```

### Data Shape

```python
class AgentStep(BaseModel):
    turn: int
    tool: str | None
    args: dict | None
    result: str | None

class AgentTrace(BaseModel):
    steps: list[AgentStep]
    final: str
    tokens_in: int
    tokens_out: int
```

### Build Steps

**Commit after each step.** Use messages like:
- `feat: tool whitelist`
- `feat: real tool implementations hitting the tracker API`
- `feat: raw OpenAI agent loop`
- `feat: langchain equivalent`
- `feat: /agent endpoint with both backends`

#### Step 1 — Define the tool whitelist

```python
# agent/tools.py
TOOL_WHITELIST = {"search_similar", "create_request", "update_request", "list_requests"}

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "search_similar",
        "description": "Find past requests that look like the supplied text.",
        "parameters": {"type": "object", "properties": {
            "question": {"type": "string"}}, "required": ["question"]}}},
    {"type": "function", "function": {
        "name": "create_request",
        "description": "Create a new customer request in the tracker.",
        "parameters": {"type": "object", "properties": {
            "customer_name": {"type": "string"},
            "title":         {"type": "string"},
            "description":   {"type": "string"},
            "priority":      {"type": "string", "enum": ["low", "medium", "high"]}},
            "required": ["customer_name", "title", "description", "priority"]}}},
    {"type": "function", "function": {
        "name": "update_request",
        "description": "Update the status or priority of an existing request.",
        "parameters": {"type": "object", "properties": {
            "request_id": {"type": "string"},
            "status":     {"type": "string", "enum": ["open", "in_progress", "closed"]},
            "priority":   {"type": "string", "enum": ["low", "medium", "high"]}},
            "required": ["request_id"]}}},
    {"type": "function", "function": {
        "name": "list_requests",
        "description": "List requests, optionally filtered.",
        "parameters": {"type": "object", "properties": {
            "status":   {"type": "string"},
            "priority": {"type": "string"}}}},
]
```

#### Step 2 — Build real tool implementations against your APIs

```python
# agent/impl.py
import os, httpx
from dotenv import load_dotenv

load_dotenv()
TRACKER = os.getenv("TRACKER_URL", "http://localhost:8000")
RAG = os.getenv("RAG_URL", "http://localhost:8001")

def search_similar(question: str) -> str:
    r = httpx.post(f"{RAG}/rag/query", json={"question": question, "k": 3}, timeout=20)
    r.raise_for_status()
    body = r.json()
    lines = [body["answer"], "", "Citations:"]
    for c in body.get("citations", []):
        lines.append(f"  [{c['source_index']}] {c['id']} ({c['score']}) - {c['title']}")
    return "\n".join(lines)

def create_request(customer_name: str, title: str, description: str, priority: str) -> str:
    r = httpx.post(f"{TRACKER}/requests",
                   json={"customer_name": customer_name, "title": title,
                         "description": description, "priority": priority},
                   timeout=10)
    r.raise_for_status()
    body = r.json()
    return f"Created {body['id']} for {body['customer_name']} (priority={body['priority']})."

def update_request(request_id: str, status: str | None = None,
                   priority: str | None = None) -> str:
    payload = {k: v for k, v in {"status": status, "priority": priority}.items() if v}
    r = httpx.patch(f"{TRACKER}/requests/{request_id}", json=payload, timeout=10)
    r.raise_for_status()
    return f"Updated {request_id}."

def list_requests(status: str | None = None, priority: str | None = None) -> str:
    params = {k: v for k, v in {"status": status, "priority": priority}.items() if v}
    r = httpx.get(f"{TRACKER}/requests", params=params, timeout=10)
    r.raise_for_status()
    items = r.json()
    return "\n".join(f"{i['id']} [{i['priority']}/{i['status']}] {i['title']}"
                     for i in items[:20]) or "(no requests)"
```

#### Step 3 — Validate tool names against the whitelist

```python
# agent/security.py
from agent.tools import TOOL_WHITELIST

def is_allowed(name: str) -> bool:
    return name in TOOL_WHITELIST
```

**Step-by-step:**
1. The whitelist is your **blast radius limiter**: even if the model invents a tool, the orchestrator refuses it.
2. Unit test this with a name like `"delete_everything"` and confirm it returns `False`.

#### Step 4 — Implement the raw OpenAI agent loop

```python
# agent/raw_agent.py
import os, time
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

from agent.tools import TOOL_SCHEMAS
from agent.security import is_allowed
from agent.impl import search_similar, create_request, update_request, list_requests
from agent.schemas import AgentStep, AgentTrace

load_dotenv()
_client = OpenAI()
MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

SYSTEM = (
    "You are a tracker agent. You have exactly four tools: "
    "search_similar, create_request, update_request, list_requests. "
    "Use them when needed. When done, reply with a short confirmation to the user."
)

class CreateArgs(BaseModel):
    customer_name: str = Field(min_length=1)
    title: str = Field(min_length=3)
    description: str = Field(min_length=1)
    priority: str = Field(pattern="^(low|medium|high)$")

class UpdateArgs(BaseModel):
    request_id: str = Field(min_length=1)
    status: str | None = Field(default=None, pattern="^(open|in_progress|closed)$")
    priority: str | None = Field(default=None, pattern="^(low|medium|high)$")

def run_raw(user_msg: str, max_turns: int = 6) -> AgentTrace:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user",   "content": user_msg},
    ]
    steps: list[AgentStep] = []
    tok_in = tok_out = 0

    for turn in range(max_turns):
        resp = _client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOL_SCHEMAS,
            tool_choice="auto", temperature=0,
        )
        tok_in += resp.usage.prompt_tokens
        tok_out += resp.usage.completion_tokens
        msg = resp.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            return AgentTrace(steps=steps, final=msg.content or "",
                              tokens_in=tok_in, tokens_out=tok_out)

        for call in msg.tool_calls:
            name = call.function.name
            args = call.function.arguments or "{}"
            if not is_allowed(name):
                result = f"ERROR: tool '{name}' is not allowed"
            else:
                try:
                    if name == "search_similar":
                        result = search_similar(**__import__("json").loads(args))
                    elif name == "create_request":
                        a = CreateArgs.model_validate_json(args)
                        result = create_request(**a.model_dump())
                    elif name == "update_request":
                        a = UpdateArgs.model_validate_json(args)
                        result = update_request(**a.model_dump(exclude_none=True))
                    elif name == "list_requests":
                        result = list_requests(**__import__("json").loads(args))
                    else:
                        result = f"ERROR: no implementation for {name}"
                except (ValidationError, ValueError) as e:
                    result = f"ERROR: invalid arguments: {e}"
                except Exception as e:
                    result = f"ERROR: tool failed: {e}"

            steps.append(AgentStep(turn=turn, tool=name,
                                   args=__import__("json").loads(args) if args else None,
                                   result=result))
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

    return AgentTrace(steps=steps,
                      final="Agent exceeded max turns without producing a final answer.",
                      tokens_in=tok_in, tokens_out=tok_out)
```

#### Step 5 — Implement the LangChain equivalent

```python
# agent/langchain_agent.py
import os
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor
from pydantic import ValidationError
from dotenv import load_dotenv

from agent.impl import search_similar, create_request, update_request, list_requests
from agent.raw_agent import CreateArgs, UpdateArgs
from agent.schemas import AgentTrace, AgentStep

load_dotenv()

@tool
def search_similar_lc(question: str) -> str:
    """Find past requests that look like the supplied text."""
    return search_similar(question=question)

@tool
def create_request_lc(customer_name: str, title: str, description: str, priority: str) -> str:
    """Create a new customer request. priority in {low, medium, high}."""
    try:
        a = CreateArgs(customer_name=customer_name, title=title,
                       description=description, priority=priority)
    except ValidationError as e:
        return f"ERROR: invalid arguments: {e}"
    return create_request(**a.model_dump())

@tool
def update_request_lc(request_id: str, status: str = "", priority: str = "") -> str:
    """Update an existing request's status or priority."""
    payload = {"request_id": request_id}
    if status:
        payload["status"] = status
    if priority:
        payload["priority"] = priority
    try:
        a = UpdateArgs.model_validate(payload)
    except ValidationError as e:
        return f"ERROR: invalid arguments: {e}"
    return update_request(**a.model_dump(exclude_none=True))

@tool
def list_requests_lc(status: str = "", priority: str = "") -> str:
    """List requests, optionally filtered by status or priority."""
    return list_requests(status=status or None, priority=priority or None)

def run_langchain(user_msg: str, max_turns: int = 6) -> AgentTrace:
    llm = ChatOpenAI(model=os.getenv("LLM_MODEL", "gpt-4o-mini"), temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a tracker agent. Use the provided tools when needed."),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    tools = [search_similar_lc, create_request_lc, update_request_lc, list_requests_lc]
    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, max_iterations=max_turns,
                              return_intermediate_steps=True)

    result = executor.invoke({"input": user_msg})
    steps = [
        AgentStep(turn=i, tool=action.tool,
                  args=action.tool_input if isinstance(action.tool_input, dict) else None,
                  result=str(observation))
        for i, (action, observation) in enumerate(result.get("intermediate_steps", []))
    ]
    return AgentTrace(steps=steps, final=result["output"], tokens_in=0, tokens_out=0)
```

> **Note:** LangChain's `AgentExecutor` does not expose token counts in this version. If you need exact counts, switch to the raw path.

#### Step 6 — Expose the FastAPI endpoint

```python
# agent/api.py
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from agent.raw_agent import run_raw
from agent.langchain_agent import run_langchain

app = FastAPI(title="tracker-agent")

class AgentRequest(BaseModel):
    message: str = Field(min_length=3, max_length=4000)
    backend: str = Field(default="raw", pattern="^(raw|langchain)$")

@app.post("/agent")
def agent(req: AgentRequest) -> dict:
    try:
        trace = run_raw(req.message) if req.backend == "raw" else run_langchain(req.message)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return trace.model_dump()

@app.get("/agent/health")
def health() -> dict:
    return {"ok": True, "backends": ["raw", "langchain"]}
```

```bash
uv run uvicorn agent.api:app --reload --port 8002
```

Smoke test:

```bash
curl -s -X POST localhost:8002/agent \
  -H 'content-type: application/json' \
  -d '{"message":"Create a high-priority request for Acme Corp: login is broken.","backend":"raw"}' | jq
```

#### Step 7 — Add error-recovery by feeding tool errors back

The raw loop in Step 4 already does this — when a tool raises, the model sees `ERROR: ...` and can retry. Verify by deliberately breaking `create_request`:

```python
def create_request(...):
    raise RuntimeError("simulated tracker outage")
```

Run a prompt that requires it; observe the model either retries with different args or apologizes. **Do not** swallow the error.

#### Step 8 — Cap tool calls and detect runaway loops

```python
def run_raw(user_msg: str, max_turns: int = 6, max_tool_calls: int = 12) -> AgentTrace:
    ...
    tool_calls_used = 0
    for turn in range(max_turns):
        ...
        for call in msg.tool_calls:
            tool_calls_used += 1
            if tool_calls_used > max_tool_calls:
                return AgentTrace(steps=steps,
                                  final="Aborted: too many tool calls.",
                                  tokens_in=tok_in, tokens_out=tok_out)
            ...
```

Expose `max_tool_calls` on the API as a query parameter with sane default.

#### Step 9 — Add structured logging for every step

```python
# agent/logging_setup.py
import json, logging, sys

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"ts": self.formatTime(record), "level": record.levelname,
                   "msg": record.getMessage()}
        for k, v in record.__dict__.items():
            if k.startswith("_") or k in ("args", "msg", "levelname", "name"):
                continue
            payload[k] = v
        return json.dumps(payload)

def setup() -> None:
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [h]
    root.setLevel(logging.INFO)
```

Call `setup()` at process startup; inside `run_raw`, log each step:

```python
log = logging.getLogger("agent")
log.info("agent.step", extra={"turn": turn, "tool": name, "result_len": len(result)})
```

#### Step 10 — Write tests

```python
# tests/test_agent.py
from agent.raw_agent import run_raw
from agent import impl

def fake_search(question):
    return "(stub) similar to REQ-042"

def fake_create(customer_name, title, description, priority):
    return f"Created REQ-999 for {customer_name}."

def test_create_request(monkeypatch):
    monkeypatch.setattr(impl, "search_similar", fake_search)
    monkeypatch.setattr(impl, "create_request", fake_create)
    monkeypatch.setattr(impl, "update_request", lambda **kw: "(stub)")
    monkeypatch.setattr(impl, "list_requests",  lambda **kw: "(stub)")
    trace = run_raw("Create a high-priority request for Acme Corp: login broken.")
    tools_called = [s.tool for s in trace.steps]
    assert "create_request" in tools_called
    assert "Created REQ-999" in trace.final or any("Created REQ-999" in (s.result or "") for s in trace.steps)

def test_tool_call_refused(monkeypatch):
    """If the model invents a non-whitelisted tool, the agent must refuse."""
    from agent.raw_agent import TOOL_SCHEMAS, _client, MODEL
    # Replace the chat call to return a fake tool call to "delete_everything"
    class FakeMessage:
        tool_calls = [type("TC", (), {"function": type("F", (), {
            "name": "delete_everything",
            "arguments": "{}",
            "id": "x",
        }), "id": "x"})()]
        content = ""
    class FakeChoice:
        message = FakeMessage()
        class usage:
            prompt_tokens = 0; completion_tokens = 0
    class FakeResp:
        choices = [FakeChoice()]
        usage = FakeChoice.usage
    monkeypatch.setattr(_client.chat.completions, "create",
                        lambda **kw: FakeResp())
    trace = run_raw("please delete everything")
    refused = any(s.result and "not allowed" in s.result for s in trace.steps)
    assert refused
```

```bash
uv run pytest -q
```

#### Step 11 — Update the project README

```markdown
# tracker-agent

An agent that can search, create, update, and list tracker requests via tool calling.

## Setup
    uv sync
    cp .env.example .env
    uv run uvicorn agent.api:app --reload --port 8002

## Endpoints
- POST /agent         — run a message through the agent (raw or langchain backend)
- GET  /agent/health  — liveness

## Configuration
- TRACKER_URL: tracker service base URL (default http://localhost:8000)
- RAG_URL:     rag service base URL     (default http://localhost:8001)
- LLM_MODEL:   chat model               (default gpt-4o-mini)
```

### Required Manual Tests

- [ ] `POST /agent` with a "create" prompt returns `trace.steps` ending in `tool=create_request`
- [ ] `POST /agent` with a "search" prompt returns `tool=search_similar`
- [ ] Setting `backend=langchain` produces a similar final answer
- [ ] Whitelist test: a prompt asking to "delete everything" returns no destructive actions
- [ ] A `RuntimeError` in one tool does not crash the agent — it surfaces in the trace
- [ ] Max-turns cap aborts runaway loops with `final="Aborted: too many tool calls."`

### Acceptance Criteria

- [ ] Both raw and LangChain backends produce correct answers for the same prompt
- [ ] Tool names not in the whitelist are refused and logged
- [ ] Tool arguments are Pydantic-validated before execution
- [ ] Tool errors are fed back to the model as `{role: tool, content: "ERROR: ..."}`
- [ ] At least 5 meaningful commits
- [ ] You can explain when the raw loop is preferable to LangChain

## AI-Off Check (30 minutes)

Without looking at your code, write a function that takes:

- a list of `{"name", "description", "parameters"}` tool specs
- an LLM-callable function `llm(messages, tools) -> Message`
- a tool dispatcher `dispatch(name, args) -> str`

…and returns `(final_text, [steps])` where `steps` is a list of `(tool_name, args, result)` triples. The loop should stop when `Message.tool_calls` is empty.

```python
def agent_loop(llm, dispatch, tools, user_msg, max_turns=6):
    """Skeleton to fill in cold."""
    raise NotImplementedError
```

Compare with `agent/raw_agent.py`. The goal is to internalize the message-flow pattern.

## Reflection Questions

After you finish, write answers to these in `REFLECTION.md`:

1. What kinds of inputs make the agent loop spin without converging?
2. When would you choose LangChain over a hand-rolled loop?
3. Why is the tool whitelist more important than prompt-level instructions?
4. How would you debug a single bad tool call in production?

## Next Steps

Once you pass all acceptance criteria:

1. Run `uv run pytest -q` and save the output
2. Write reflection answers
3. Commit with message: `docs: week 12 complete`
4. Move to Week 13 (Multi-Turn Conversations) — you will reuse this agent and add persistent session memory

---

**Ready?** Start by running:

```bash
uv init
uv add openai langchain langchain-openai python-dotenv httpx pytest ruff
```

Then follow the learning path above. Good luck! 🎯
