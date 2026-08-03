# Week 13: Multi-Turn Conversations and Memory

## Outcome

Add **persistent, multi-turn conversation memory** to the tracker agent from Week 12. Build two interchangeable session stores — an **in-memory list** (for tests and single-process dev) and a **Redis-backed store** (for production). The agent must remember prior tool calls, last user intents, and gracefully handle context-window limits by **summarizing or truncating** old turns.

## Setup Checklist

- [ ] Reuse the `tracker_agent` from Week 12
- [ ] Have a local Redis available (`docker run -p 6379:6379 redis:7-alpine`)
- [ ] `uv add redis pydantic python-dotenv pytest fakeredis`
- [ ] Confirm `uv run python -c "import redis; r=redis.Redis(); r.ping()"` returns `True`
- [ ] For tests without a real Redis: `fakeredis` is acceptable

### Setup Walkthrough

```bash
cd phase-4-agents/week-13-multi-turn
uv init
uv python pin 3.13

uv add redis pydantic python-dotenv pytest fakeredis ruff

# Stand up Redis locally (Docker)
docker run -d --name redis-dev -p 6379:6379 redis:7-alpine

# Verify
uv run python - <<'PY'
import redis, os
r = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379, decode_responses=True)
print(r.ping())  # True
PY
```

```bash
# .env (do not commit)
REDIS_HOST=localhost
REDIS_PORT=6379
LLM_MODEL=gpt-4o-mini
MAX_CONTEXT_TOKENS=8000
```

## Learning Path (60–90 minutes)

**Best approach:** Treat the conversation history like a **bounded resource**. Every turn you store is a turn the model will eventually pay to read.

### Learn in this order

1. **Why sessions need persistence** — without it, every HTTP request is single-turn
2. **Session identity** — opaque `session_id`; never trust user-supplied IDs
3. **Message format** — roles (`user`, `assistant`, `tool`, `system`), timestamps, monotonic ordering
4. **In-memory storage** — `dict[session_id, list[Message]]`; works for one process, dies on restart
5. **Redis-backed storage** — `LIST` per session with `LRANGE`/`RPUSH`; survives restart and scales horizontally
6. **TTL and eviction** — set `EXPIRE` so abandoned sessions disappear
7. **Context window limits** — count tokens, summarize or truncate when approaching the limit
8. **Sliding-window vs summarization** — tradeoffs

### Free Resources

- [Redis Lists — RPUSH / LRANGE / LTRIM](https://redis.io/docs/latest/develop/data-types/lists/)
- [OpenAI Token Counting with tiktoken](https://github.com/openai/tiktoken)
- [LangChain ConversationMemory](https://python.langchain.com/docs/concepts/memory/) — for reference patterns
- [Anthropic Prompt Caching Guide](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) — caching strategies you can mirror in Redis
- [Redis EXPIRE and eviction policies](https://redis.io/docs/latest/operate/oss_and_stack/management/config-file/)

**Tip:** If your sessions are short (< 20 turns), keep everything. Only add summarization when you actually hit context limits.

## Micro-Exercises (45–60 minutes)

Create `practice.py` and work through these:

### Exercise 1 — Define a `Message` schema

```python
# practice.py
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import Literal

Role = Literal["system", "user", "assistant", "tool"]

class Message(BaseModel):
    role: Role
    content: str | None = None
    name: str | None = None                # for tool calls
    tool_call_id: str | None = None
    tool_calls: list[dict] | None = None
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

m = Message(role="user", content="Create a request for Acme: login broken.")
print(m.model_dump_json())
```

**Step-by-step:**
1. Notice `ts` is auto-stamped; useful for ordering and debugging.
2. `tool_calls` is a list of dicts — store the raw `tool_calls` from the OpenAI response so we can re-feed them later.
3. Don't worry about tokens yet — count them in Exercise 4.

### Exercise 2 — Build an in-memory session store

```python
import threading

class InMemorySessionStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, list[Message]] = {}

    def load(self, session_id: str) -> list[Message]:
        with self._lock:
            return list(self._data.get(session_id, []))

    def append(self, session_id: str, msg: Message) -> None:
        with self._lock:
            self._data.setdefault(session_id, []).append(msg)

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._data.pop(session_id, None)

    def all_sessions(self) -> list[str]:
        with self._lock:
            return list(self._data.keys())

store = InMemorySessionStore()
store.append("s1", Message(role="user", content="hello"))
store.append("s1", Message(role="assistant", content="hi!"))
print(store.load("s1"))
print(store.all_sessions())
```

**Step-by-step:**
1. The lock prevents races when two HTTP requests land on the same session.
2. `load()` returns a **copy** — callers can mutate without affecting the store.
3. `clear()` is for tests and for explicit user "reset" actions.

### Exercise 3 — Build the Redis-backed equivalent

```python
import os, json
import redis
from dotenv import load_dotenv

load_dotenv()
r = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                decode_responses=True)

SESSION_PREFIX = "chat:session:"
SESSION_TTL = 60 * 60 * 24  # 24h

class RedisSessionStore:
    def __init__(self, client: redis.Redis, ttl_s: int = SESSION_TTL) -> None:
        self.r = client
        self.ttl = ttl_s

    def _key(self, sid: str) -> str:
        return f"{SESSION_PREFIX}{sid}"

    def load(self, session_id: str) -> list[Message]:
        raw = self.r.lrange(self._key(session_id), 0, -1)
        return [Message.model_validate_json(s) for s in raw]

    def append(self, session_id: str, msg: Message) -> None:
        key = self._key(session_id)
        pipe = self.r.pipeline()
        pipe.rpush(key, msg.model_dump_json())
        pipe.expire(key, self.ttl)
        pipe.execute()

    def clear(self, session_id: str) -> None:
        self.r.delete(self._key(session_id))

    def all_sessions(self) -> list[str]:
        keys = self.r.keys(f"{SESSION_PREFIX}*")
        return [k.removeprefix(SESSION_PREFIX) for k in keys]

store = RedisSessionStore(r)
store.append("s2", Message(role="user", content="ping"))
print(store.load("s2"))
print(store.all_sessions())
```

**Step-by-step:**
1. `RPUSH` adds to the right; `LRANGE 0 -1` reads everything — sessions are append-only logs.
2. `EXPIRE` is reset on every append, so an active session lives forever; abandoned ones expire.
3. `KEYS` is fine for dev, but in production use `SCAN` to avoid blocking Redis.

### Exercise 4 — Count tokens with tiktoken

```python
import tiktoken

def count_tokens(messages: list[Message], model: str = "gpt-4o-mini") -> int:
    enc = tiktoken.encoding_for_model(model)
    # Per-message overhead approximated as 4 tokens; role/name add a couple more
    total = 0
    for m in messages:
        total += 4
        if m.content:
            total += len(enc.encode(m.content))
        if m.name:
            total += len(enc.encode(m.name))
        # tool_calls have arguments; serialize them
        if m.tool_calls:
            total += len(enc.encode(json.dumps(m.tool_calls)))
    return total

msgs = [Message(role="user", content="Create a high-priority request for Acme Corp: login broken.")]
print("tokens:", count_tokens(msgs))
```

**Step-by-step:**
1. The 4-token overhead is the OpenAI convention; close enough for budgeting.
2. Use the count to decide when to summarize.
3. **Do not** send the entire history every turn — it gets expensive fast.

### Exercise 5 — Sliding window of last N turns

```python
def truncate_to_last_n(messages: list[Message], n: int) -> list[Message]:
    """Always keep the system message (if any) plus the last n non-system messages."""
    system = [m for m in messages if m.role == "system"]
    rest   = [m for m in messages if m.role != "system"]
    return system + rest[-n:]

history = [Message(role="system", content="you are a tracker agent")]
for i in range(10):
    history.append(Message(role="user", content=f"turn {i}"))
    history.append(Message(role="assistant", content=f"reply {i}"))

print("before:", len(history))
trimmed = truncate_to_last_n(history, 4)
print("after :", len(trimmed), "— kept system + last 4 turns")
```

**Step-by-step:**
1. Always preserve the system message; it carries the agent's identity.
2. Trim tool turns together — never break a tool call away from its result.
3. **Pitfall:** simple sliding window can lose the *start* of a long reasoning chain.

### Exercise 6 — Summarize old turns when over budget

```python
import os
from openai import OpenAI

client = OpenAI()

def summarize(messages: list[Message], model: str = None) -> str:
    text = "\n".join(f"{m.role}: {m.content or ''}" for m in messages)
    resp = client.chat.completions.create(
        model=model or os.getenv("LLM_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system",
             "content": "Summarize the conversation in 3-5 bullet points. "
                        "Preserve any concrete IDs, customer names, and decisions."},
            {"role": "user", "content": text},
        ],
        temperature=0,
    )
    return resp.choices[0].message.content or ""

old_turns = history[1:6]   # 5 user/assistant pairs
summary = summarize(old_turns)
print("summary:", summary)
```

**Step-by-step:**
1. Keep summaries short — they replace the entire history they summarize.
2. The `EXTRACTER` should preserve IDs and decisions; test that.
3. **Cost consideration:** summarization itself is an LLM call. Cache summaries keyed by hash of the trimmed history.

### Exercise 7 — Glue it together: a session manager with a budget

```python
class SessionManager:
    def __init__(self, store, model="gpt-4o-mini", max_tokens=8000,
                 keep_last_n=10, summarize_threshold=0.8):
        self.store = store
        self.model = model
        self.max_tokens = max_tokens
        self.keep_last_n = keep_last_n
        self.summarize_threshold = summarize_threshold

    def history(self, sid: str) -> list[Message]:
        msgs = self.store.load(sid)
        used = count_tokens(msgs, self.model)
        if used < self.max_tokens * self.summarize_threshold:
            return msgs
        system = [m for m in msgs if m.role == "system"]
        rest   = [m for m in msgs if m.role != "system"]
        if len(rest) <= self.keep_last_n:
            return msgs
        old, recent = rest[:-self.keep_last_n], rest[-self.keep_last_n:]
        summary = summarize(old, self.model)
        new_system = list(system) + [Message(role="system",
                                              content=f"Prior conversation summary:\n{summary}")]
        return new_system + recent

    def append(self, sid: str, msg: Message) -> None:
        self.store.append(sid, msg)

sm = SessionManager(InMemorySessionStore(), max_tokens=4000, keep_last_n=4)
sid = "demo"
sm.append(sid, Message(role="system", content="you are a tracker agent"))
for i in range(8):
    sm.append(sid, Message(role="user", content=f"turn {i}: customer asks about request #{i}"))
    sm.append(sid, Message(role="assistant", content=f"reply {i}"))
hist = sm.history(sid)
print("returned turns:", len(hist))
print("first system msg len:", len(hist[0].content or ""))
```

**Step-by-step:**
1. Run with `max_tokens=4000` and many turns — observe summarization kick in.
2. Set `max_tokens=10**9` to disable summarization and confirm the full history is returned.
3. Replace `InMemorySessionStore()` with `RedisSessionStore(r)` and confirm behavior is identical.

---

## Main Lab: Persistent multi-turn agent (4–5 hours)

### Scenario

The tracker agent from Week 12 is currently stateless. Customer success wants: *"I can keep using the agent across browser tabs and Slack threads, and it remembers what I asked earlier."* Build that.

### Data Shape

```python
class SessionInfo(BaseModel):
    session_id: str
    created_at: datetime
    updated_at: datetime
    turn_count: int
    tokens_used: int

class ChatRequest(BaseModel):
    session_id: str | None = None          # if None, server allocates
    message: str = Field(min_length=1)
    backend: Literal["raw", "langchain"] = "raw"
    max_tokens: int = Field(default=8000, ge=512, le=32000)

class ChatResponse(BaseModel):
    session_id: str
    final: str
    steps: list[AgentStep]
    tokens_in: int
    tokens_out: int
    tokens_history: int
    summarized: bool
```

### Required Endpoints

```
POST /chat                     — send a message, get a reply, persist session
GET  /chat/{session_id}        — fetch session metadata + recent turns
DELETE /chat/{session_id}      — clear a session
POST /chat/{session_id}/reset  — same as DELETE but returns the new empty session
GET  /chat/health              — confirm Redis reachable + session count
```

### Build Steps

**Commit after each step.** Use messages like:
- `feat: Message schema`
- `feat: in-memory + redis stores behind one interface`
- `feat: session manager with token budget`
- `feat: wire to /agent endpoint`
- `feat: /chat endpoints`

#### Step 1 — Define the `SessionStore` interface

```python
# sessions/base.py
from abc import ABC, abstractmethod
from agent.schemas import Message  # reuse Week 12's schema; or define here

class SessionStore(ABC):
    @abstractmethod
    def load(self, session_id: str) -> list[Message]: ...

    @abstractmethod
    def append(self, session_id: str, msg: Message) -> None: ...

    @abstractmethod
    def clear(self, session_id: str) -> None: ...

    @abstractmethod
    def all_sessions(self) -> list[str]: ...
```

#### Step 2 — Implement the in-memory store

```python
# sessions/memory.py
import threading
from agent.schemas import Message
from sessions.base import SessionStore

class InMemorySessionStore(SessionStore):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, list[Message]] = {}

    def load(self, session_id):
        with self._lock:
            return list(self._data.get(session_id, []))

    def append(self, session_id, msg):
        with self._lock:
            self._data.setdefault(session_id, []).append(msg)

    def clear(self, session_id):
        with self._lock:
            self._data.pop(session_id, None)

    def all_sessions(self):
        with self._lock:
            return list(self._data.keys())
```

#### Step 3 — Implement the Redis store

```python
# sessions/redis_store.py
import os, json
import redis
from agent.schemas import Message
from sessions.base import SessionStore

PREFIX = "chat:session:"

class RedisSessionStore(SessionStore):
    def __init__(self, client: redis.Redis | None = None,
                 ttl_s: int = 60 * 60 * 24) -> None:
        self.r = client or redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True,
        )
        self.ttl = ttl_s

    def _key(self, sid: str) -> str:
        return f"{PREFIX}{sid}"

    def load(self, session_id):
        raw = self.r.lrange(self._key(session_id), 0, -1)
        return [Message.model_validate_json(s) for s in raw]

    def append(self, session_id, msg):
        key = self._key(session_id)
        pipe = self.r.pipeline()
        pipe.rpush(key, msg.model_dump_json())
        pipe.expire(key, self.ttl)
        pipe.execute()

    def clear(self, session_id):
        self.r.delete(self._key(session_id))

    def all_sessions(self):
        return [k.removeprefix(PREFIX) for k in self.r.scan_iter(f"{PREFIX}*")]
```

#### Step 4 — Build the token-budgeted session manager

```python
# sessions/manager.py
import os, hashlib
from openai import OpenAI
from agent.schemas import Message
from sessions.base import SessionStore

_client = OpenAI()

def count_tokens(messages: list[Message], model: str = "gpt-4o-mini") -> int:
    import tiktoken, json as _json
    enc = tiktoken.encoding_for_model(model)
    total = 0
    for m in messages:
        total += 4
        if m.content:
            total += len(enc.encode(m.content))
        if m.tool_calls:
            total += len(enc.encode(_json.dumps(m.tool_calls)))
    return total

def _summarize(messages: list[Message], model: str) -> str:
    text = "\n".join(f"{m.role}: {m.content or ''}" for m in messages)
    resp = _client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system",
             "content": "Summarize in 3-5 bullets. Preserve IDs, customer names, and decisions."},
            {"role": "user", "content": text},
        ],
        temperature=0,
    )
    return resp.choices[0].message.content or ""

class SessionManager:
    def __init__(self, store: SessionStore, model: str = "gpt-4o-mini",
                 max_tokens: int = 8000, keep_last_n: int = 10,
                 summarize_ratio: float = 0.8) -> None:
        self.store = store
        self.model = model
        self.max_tokens = max_tokens
        self.keep_last_n = keep_last_n
        self.summarize_ratio = summarize_ratio

    def history(self, sid: str) -> tuple[list[Message], bool]:
        msgs = self.store.load(sid)
        used = count_tokens(msgs, self.model)
        if used < self.max_tokens * self.summarize_ratio:
            return msgs, False
        system = [m for m in msgs if m.role == "system"]
        rest   = [m for m in msgs if m.role != "system"]
        if len(rest) <= self.keep_last_n:
            return msgs, False
        old, recent = rest[:-self.keep_last_n], rest[-self.keep_last_n:]
        summary = _summarize(old, self.model)
        new_system = list(system) + [Message(
            role="system",
            content=f"Prior conversation summary:\n{summary}",
        )]
        return new_system + recent, True

    def append(self, sid: str, msg: Message) -> None:
        self.store.append(sid, msg)

    def tokens_used(self, sid: str) -> int:
        return count_tokens(self.store.load(sid), self.model)
```

#### Step 5 — Plug the session manager into the agent

```python
# agent/with_sessions.py
from agent.schemas import AgentTrace, Message
from sessions.manager import SessionManager

def run_session_turn(manager: SessionManager, sid: str, user_msg: str,
                     backend: str = "raw") -> tuple[AgentTrace, list[Message], bool]:
    history, summarized = manager.history(sid)

    # Persist the user's turn first
    manager.append(sid, Message(role="user", content=user_msg))
    history.append(Message(role="user", content=user_msg))

    # Run the agent with the reconstructed history as system+user messages
    # (raw_agent.run_raw currently only takes a single user_msg; we extend it
    # to accept a full message list.)
    from agent.raw_agent import run_raw_with_messages
    trace = run_raw_with_messages(history, backend=backend)

    # Persist assistant + tool messages
    for msg in trace.messages_added:  # agent must expose this list
        manager.append(sid, msg)
    return trace, history, summarized
```

Extend `run_raw` in Week 12 to expose `messages_added`:

```python
# agent/raw_agent.py  (patch)
def run_raw_with_messages(messages: list[dict], backend: str = "raw") -> AgentTrace:
    messages = list(messages)  # copy
    steps, messages_added = [], []
    # ... existing loop ...
    for call in msg.tool_calls:
        # ... execute ...
        tool_msg = {"role": "tool", "tool_call_id": call.id, "content": result}
        messages.append(tool_msg)
        messages_added.append(tool_msg)
    messages_added.append({"role": "assistant", "content": msg.content or "",
                            "tool_calls": [tc.model_dump() for tc in (msg.tool_calls or [])]})
    trace.messages_added = messages_added
    return trace
```

#### Step 6 — Wire FastAPI endpoints

```python
# chat/api.py
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field

from sessions.memory import InMemorySessionStore
from sessions.redis_store import RedisSessionStore
from sessions.manager import SessionManager
from agent.with_sessions import run_session_turn

app = FastAPI(title="chat-service")

def get_manager() -> SessionManager:
    import os
    backend = os.getenv("SESSION_BACKEND", "memory")
    store = RedisSessionStore() if backend == "redis" else InMemorySessionStore()
    return SessionManager(store=store, max_tokens=int(os.getenv("MAX_CONTEXT_TOKENS", "8000")))

class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=4000)
    backend: str = Field(default="raw", pattern="^(raw|langchain)$")

class ChatResponse(BaseModel):
    session_id: str
    final: str
    tokens_in: int
    tokens_out: int
    tokens_history: int
    summarized: bool

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, manager: SessionManager = Depends(get_manager)):
    sid = req.session_id or f"s_{uuid.uuid4().hex[:12]}"
    if not manager.store.all_sessions() or sid not in manager.store.all_sessions():
        # brand-new sessions get the agent's identity system message
        from agent.schemas import Message
        manager.append(sid, Message(
            role="system",
            content="You are a tracker agent. Use tools when needed. Be concise.",
        ))
    try:
        trace, history, summarized = run_session_turn(manager, sid, req.message, req.backend)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return ChatResponse(
        session_id=sid, final=trace.final,
        tokens_in=trace.tokens_in, tokens_out=trace.tokens_out,
        tokens_history=manager.tokens_used(sid), summarized=summarized,
    )

@app.get("/chat/{session_id}")
def get_session(session_id: str, manager: SessionManager = Depends(get_manager)):
    if session_id not in manager.store.all_sessions():
        raise HTTPException(status_code=404, detail="session not found")
    msgs = manager.store.load(session_id)
    return {
        "session_id": session_id,
        "turn_count": sum(1 for m in msgs if m.role == "user"),
        "tokens_used": manager.tokens_used(session_id),
        "messages": [m.model_dump(mode="json") for m in msgs[-20:]],
    }

@app.delete("/chat/{session_id}", status_code=204)
def delete_session(session_id: str, manager: SessionManager = Depends(get_manager)):
    manager.store.clear(session_id)

@app.get("/chat/health")
def health(manager: SessionManager = Depends(get_manager)):
    return {"ok": True, "sessions": len(manager.store.all_sessions()),
            "backend": type(manager.store).__name__}
```

```bash
uv run uvicorn chat.api:app --reload --port 8003
```

#### Step 7 — Switch backends via env var

```bash
SESSION_BACKEND=redis uv run uvicorn chat.api:app --reload --port 8003
```

Same API, different storage. The `get_manager` dependency wires the right store.

#### Step 8 — Add session-list and per-session TTL

```python
# chat/api.py
@app.get("/chat")
def list_sessions(manager: SessionManager = Depends(get_manager)):
    return {"sessions": manager.store.all_sessions()[:100]}
```

Verify Redis TTL is set:

```bash
redis-cli TTL chat:session:s_abcd1234efgh
# should be close to 86400 (24h)
```

#### Step 9 — Write tests

```python
# tests/test_sessions.py
import os, fakeredis
from agent.schemas import Message
from sessions.memory import InMemorySessionStore
from sessions.redis_store import RedisSessionStore
from sessions.manager import SessionManager

def test_memory_store_roundtrip():
    s = InMemorySessionStore()
    s.append("a", Message(role="user", content="hi"))
    s.append("a", Message(role="assistant", content="hello"))
    msgs = s.load("a")
    assert len(msgs) == 2
    assert msgs[1].content == "hello"

def test_redis_store_roundtrip():
    fake = fakeredis.FakeRedis(decode_responses=True)
    s = RedisSessionStore(client=fake, ttl_s=60)
    s.append("b", Message(role="user", content="ping"))
    msgs = s.load("b")
    assert msgs[0].content == "ping"
    assert fake.ttl(s._key("b")) > 0

def test_session_manager_no_summarize_when_small():
    s = InMemorySessionStore()
    sm = SessionManager(s, max_tokens=10**6, keep_last_n=2)
    sid = "small"
    sm.append(sid, Message(role="system", content="sys"))
    sm.append(sid, Message(role="user",    content="u1"))
    sm.append(sid, Message(role="assistant", content="a1"))
    hist, summarized = sm.history(sid)
    assert summarized is False
    assert len(hist) == 3

def test_session_manager_summarizes_when_large():
    s = InMemorySessionStore()
    sm = SessionManager(s, max_tokens=200, keep_last_n=2, summarize_ratio=0.5)
    sid = "big"
    sm.append(sid, Message(role="system", content="sys"))
    for i in range(20):
        sm.append(sid, Message(role="user",      content=f"long user message #{i} " * 10))
        sm.append(sid, Message(role="assistant", content=f"long assistant message #{i} " * 10))
    hist, summarized = sm.history(sid)
    assert summarized is True
    # We must keep at least system + summary + last keep_last_n non-system
    assert len(hist) <= 1 + 1 + 2
```

```bash
uv run pytest -q
```

#### Step 10 — Document the project

```markdown
# chat-service

Multi-turn agent chat with persistent sessions.

## Setup
    uv sync
    docker run -d -p 6379:6379 redis:7-alpine
    cp .env.example .env

## Configuration
- SESSION_BACKEND: memory | redis
- REDIS_HOST, REDIS_PORT
- MAX_CONTEXT_TOKENS: budget for in-context history (default 8000)
- LLM_MODEL

## Endpoints
- POST /chat             — send a message, returns reply + session_id
- GET  /chat/{sid}       — fetch session messages + token usage
- DELETE /chat/{sid}     — clear a session
- GET  /chat             — list active sessions
- GET  /chat/health      — liveness + backend info
```

### Required Manual Tests

- [ ] First `POST /chat` with no `session_id` returns one; reuse it for follow-ups
- [ ] Sending 3 follow-ups with the same `session_id` accumulates history
- [ ] `GET /chat/{sid}` shows the message count grows over turns
- [ ] Setting `SESSION_BACKEND=redis` and restarting preserves sessions
- [ ] With `MAX_CONTEXT_TOKENS=500`, sending 10 long turns triggers summarization
- [ ] `DELETE /chat/{sid}` clears the session and subsequent GET returns 404
- [ ] `redis-cli TTL chat:session:*` shows ~86400 for active sessions

### Acceptance Criteria

- [ ] `SessionStore` is an interface with both implementations
- [ ] Sessions survive a process restart when using Redis
- [ ] Token budget is enforced via sliding window + summarization
- [ ] Every tool/assistant/user message is persisted exactly once
- [ ] TTL is set on every append
- [ ] Tests cover both stores via `fakeredis` (no real Redis required in CI)
- [ ] At least 5 meaningful commits
- [ ] You can explain the tradeoff between sliding window and summarization

## AI-Off Check (30 minutes)

Without looking at your code, write a function that:

1. Takes a list of `Message` and a token budget.
2. Returns the smallest prefix that fits within the budget using the last-N strategy.
3. Returns a flag indicating whether truncation occurred.

```python
def fit_history(messages: list[Message], budget_tokens: int,
                count_fn=count_tokens) -> tuple[list[Message], bool]:
    """Skeleton to fill in cold."""
    raise NotImplementedError
```

Compare with `truncate_to_last_n` from Exercise 5. The goal is to internalize the budget-fit pattern.

## Reflection Questions

After you finish, write answers to these in `REFLECTION.md`:

1. What happens to a long-running session if summarization never triggers?
2. Why is `LRANGE 0 -1` safe but `KEYS *` is not in production?
3. When would you choose Redis over a SQL table for sessions?
4. How do you decide a good `keep_last_n` for your domain?

## Next Steps

Once you pass all acceptance criteria:

1. Run `uv run pytest -q` and save the output
2. Write reflection answers
3. Commit with message: `docs: week 13 complete`
4. Move to Week 14 (Reliable Tool Use) — you will harden the tool loop you built here

---

**Ready?** Start by running:

```bash
uv init
uv add redis pydantic python-dotenv pytest fakeredis ruff
docker run -d -p 6379:6379 redis:7-alpine
```

Then follow the learning path above. Good luck! 🎯
