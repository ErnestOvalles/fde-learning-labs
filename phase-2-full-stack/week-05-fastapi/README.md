# Week 5: FastAPI and REST APIs

## Outcome

Turn your tracker into a **production REST API** with Pydantic validation, automatic OpenAPI documentation, and consistent error responses.

By the end of this week you will be able to:

- Define CRUD endpoints with FastAPI and type-annotated handlers
- Use Pydantic models to validate request and response bodies
- Translate domain exceptions to proper HTTP status codes
- Run the app with `uvicorn` and explore the auto-generated `/docs`
- Write API tests with FastAPI's `TestClient` and pytest

## Setup Checklist

- [ ] Carry forward the Week 4 project (or start fresh from Week 2's models)
- [ ] `uv add fastapi uvicorn[standard]`
- [ ] `uv add --dev httpx` (already added; `TestClient` uses it)
- [ ] Confirm `uv run uvicorn --version`
- [ ] Create `src/request_tracker/api.py` (the FastAPI app)

### Setup Walkthrough

```bash
cd week-02-layered-tracker        # reuse the layered tracker
uv add fastapi "uvicorn[standard]"

# Add a run script entry-point
mkdir -p src/request_tracker
touch src/request_tracker/api.py
```

Add a console script in `pyproject.toml`:

```toml
[project.scripts]
tracker-api = "request_tracker.api:run"
```

## Learning Path (60–90 minutes)

**Best approach:** Build a tiny FastAPI app first, then attach the tracker to it. The framework rewards small, focused handlers.

### Learn in this order

1. **Path operations** — `@app.get`, `@app.post`, `@app.put`, `@app.delete`
2. **Pydantic request and response models**
3. **Dependency injection** — `Depends(...)`
4. **Status codes** — `201 Created`, `204 No Content`, `404 Not Found`
5. **Error handling** — `HTTPException` and exception handlers
6. **OpenAPI** — automatic `/docs` and `/openapi.json`
7. **TestClient** — pytest-friendly way to call the API
8. **CORS basics** — when the API is called from a different origin

### Free Resources

- [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/)
- [FastAPI user guide](https://fastapi.tiangolo.com/advanced/)
- [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/) (carried from Week 2)
- [HTTP status codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)

## Micro-Exercises (45–60 minutes)

1. Return JSON from a single `@app.get` endpoint
2. Accept a JSON body in an `@app.post` endpoint
3. Use `Query` and `Path` for URL parameters
4. Return proper status codes with `status_code=201`
5. Raise `HTTPException` for a 404 case
6. Add a custom exception handler that returns a structured error
7. Use `TestClient` to assert on a response body and status

## Main Lab: Tracker REST API (4–5 hours)

### Target Structure

```
week-05-fastapi/
├── pyproject.toml
├── README.md
├── src/
│   └── request_tracker/
│       ├── __init__.py
│       ├── api.py           # FastAPI app
│       ├── deps.py          # DI: get_service, get_settings
│       ├── models.py        # Pydantic models
│       ├── services.py      # carried forward
│       ├── repositories.py  # carried forward
│       └── exceptions.py    # carried forward
├── data/
└── tests/
    ├── test_api_requests.py
    └── test_api_errors.py
```

### Required Endpoints

| Method | Path                       | Purpose                        | Status codes      |
|--------|----------------------------|--------------------------------|-------------------|
| POST   | `/requests`                | Create a request               | 201, 422          |
| GET    | `/requests`                | List requests (filter+paginate)| 200               |
| GET    | `/requests/{id}`           | Fetch one                      | 200, 404          |
| PATCH  | `/requests/{id}/status`    | Change status                  | 200, 400, 404     |
| POST   | `/requests/{id}/close`     | Close with resolution note     | 200, 400, 404     |
| GET    | `/health`                  | Liveness check                 | 200               |

### Build Steps

1. Define Pydantic request/response schemas
2. Create the FastAPI app and `/health` endpoint
3. Wire the service via `Depends`
4. Implement `POST /requests`
5. Implement `GET /requests` with filters
6. Implement `GET /requests/{id}` and 404 handling
7. Implement `PATCH /requests/{id}/status`
8. Implement `POST /requests/{id}/close`
9. Add a global exception handler
10. Write tests with `TestClient`
11. Run the app with `uvicorn` and explore `/docs`

## Step-by-Step Walkthrough

> Every snippet is runnable. After pasting, run `uv run uvicorn request_tracker.api:app --reload` and visit `http://127.0.0.1:8000/docs`.

### Exercise 1 — Return JSON from a single `@app.get` endpoint

```python
# src/request_tracker/api.py
from fastapi import FastAPI

app = FastAPI(title="Request Tracker", version="0.1.0")

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

```bash
uv run uvicorn request_tracker.api:app --reload
# In another terminal:
curl -s http://127.0.0.1:8000/health | python -m json.tool
```

**Step-by-step:**
1. `FastAPI()` is the application object. Every `@app.<verb>` decorator registers a route.
2. Type-annotated return values become part of the OpenAPI schema.
3. The reload flag restarts the server on every file save — invaluable while developing.

### Exercise 2 — Accept a JSON body in an `@app.post` endpoint

```python
# src/request_tracker/api.py
from pydantic import BaseModel, Field
from fastapi import FastAPI

app = FastAPI()

class EchoIn(BaseModel):
    message: str = Field(min_length=1, max_length=200)

class EchoOut(BaseModel):
    received: str
    length: int

@app.post("/echo", response_model=EchoOut)
def echo(payload: EchoIn) -> EchoOut:
    return EchoOut(received=payload.message, length=len(payload.message))
```

```bash
curl -s -X POST http://127.0.0.1:8000/echo \
     -H "content-type: application/json" \
     -d '{"message":"hello"}' | python -m json.tool
```

**Step-by-step:**
1. The Pydantic model acts as the schema *and* the validator — bad JSON returns a 422 with details.
2. `response_model=EchoOut` ensures the response is filtered through that schema. Anything not declared is dropped.
3. This is the same validation pattern you'll use for the real `POST /requests`.

### Exercise 3 — Use `Query` and `Path` for URL parameters

```python
# src/request_tracker/api.py
from fastapi import FastAPI, Path, Query

app = FastAPI()

@app.get("/items/{item_id}")
def get_item(
    item_id: int = Path(..., ge=1),
    verbose: bool = Query(False),
):
    return {"id": item_id, "verbose": verbose}
```

```bash
curl -s "http://127.0.0.1:8000/items/42?verbose=true"
curl -s "http://127.0.0.1:8000/items/0"        # 422: ge=1 violated
```

**Step-by-step:**
1. `Path(..., ge=1)` means "required, must be >= 1".
2. `Query(False)` is optional with a default.
3. Type coercion happens automatically: `?verbose=true` becomes the Python `True`.

### Exercise 4 — Return proper status codes with `status_code=201`

```python
# src/request_tracker/api.py
from fastapi import FastAPI, status
from pydantic import BaseModel

app = FastAPI()

class Thing(BaseModel):
    name: str

@app.post("/things", status_code=status.HTTP_201_CREATED)
def create_thing(thing: Thing) -> Thing:
    # In real code, persist `thing` and return the stored representation.
    return thing
```

**Step-by-step:**
1. `status.HTTP_201_CREATED` is a constant; using the alias avoids magic numbers.
2. FastAPI still validates the *response* matches `response_model` if you supply one.
3. `201` is the right code for "the resource was created" — never use `200` for POSTs that create.

### Exercise 5 — Raise `HTTPException` for a 404 case

```python
# src/request_tracker/api.py
from fastapi import FastAPI, HTTPException, status

app = FastAPI()
DATA: dict[str, dict] = {}

@app.get("/things/{thing_id}")
def read_thing(thing_id: str) -> dict:
    if thing_id not in DATA:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"no thing with id {thing_id}",
        )
    return DATA[thing_id]
```

**Step-by-step:**
1. `HTTPException` short-circuits the handler; FastAPI formats the JSON response for you.
2. `detail` becomes the message body — keep it human-readable.
3. For consistency, prefer a *custom* exception handler (Exercise 6) over scattered `HTTPException` calls.

### Exercise 6 — Add a custom exception handler that returns a structured error

```python
# src/request_tracker/api.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from request_tracker.exceptions import (RequestNotFound,
                                        IllegalStatusTransition,
                                        ResolutionNoteRequired)

app = FastAPI()

@app.exception_handler(RequestNotFound)
async def handle_not_found(_: Request, exc: RequestNotFound) -> JSONResponse:
    return JSONResponse(status_code=404,
                        content={"error": "not_found", "message": str(exc)})

@app.exception_handler(IllegalStatusTransition)
async def handle_illegal_transition(_: Request, exc: IllegalStatusTransition) -> JSONResponse:
    return JSONResponse(status_code=400,
                        content={"error": "illegal_transition", "message": str(exc)})

@app.exception_handler(ResolutionNoteRequired)
async def handle_no_note(_: Request, exc: ResolutionNoteRequired) -> JSONResponse:
    return JSONResponse(status_code=400,
                        content={"error": "resolution_note_required",
                                 "message": str(exc)})
```

**Step-by-step:**
1. Each domain exception maps to exactly one HTTP code — no business code decides HTTP semantics.
2. `error` is a stable machine-readable code; `message` is for humans.
3. Handlers are async, but they don't have to do async work — FastAPI supports both.

### Exercise 7 — Use `TestClient` to assert on a response body and status

```python
# tests/test_api_smoke.py
from fastapi.testclient import TestClient
from request_tracker.api import app

client = TestClient(app)

def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

**Step-by-step:**
1. `TestClient` is a thin wrapper around `httpx` — same mental model as Exercise 4 from Week 4.
2. It runs the app in-process, so tests are fast and isolated.
3. No need to start a real uvicorn server in your tests.

---

### Step 1 — Define Pydantic request/response schemas

```python
# src/request_tracker/schemas.py
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from .models import Priority, RequestStatus

class RequestCreate(BaseModel):
    customer_name: str = Field(min_length=1)
    title: str = Field(min_length=3)
    description: str = ""
    priority: Priority

class RequestUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: Priority | None = None

class StatusChange(BaseModel):
    new_status: RequestStatus

class CloseRequest(BaseModel):
    resolution_note: str = Field(min_length=1)

class RequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    customer_name: str
    title: str
    description: str
    priority: Priority
    status: RequestStatus
    created_at: datetime
    updated_at: datetime
```

**Why:** Separate **input** schemas (`RequestCreate`) from **output** schemas (`RequestOut`) so internal fields never leak out and external-only fields never sneak in.

### Step 2 — Create the FastAPI app and `/health` endpoint

```python
# src/request_tracker/api.py
from fastapi import FastAPI
app = FastAPI(title="Request Tracker", version="0.1.0")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

### Step 3 — Wire the service via `Depends`

```python
# src/request_tracker/deps.py
from functools import lru_cache
from fastapi import Depends
from .repositories import JsonRequestRepository
from .services import RequestService

@lru_cache(maxsize=1)
def get_repository() -> JsonRequestRepository:
    return JsonRequestRepository()

def get_service(repo: JsonRequestRepository = Depends(get_repository)) -> RequestService:
    return RequestService(repo)
```

```python
# src/request_tracker/api.py
from fastapi import APIRouter, Depends
from .deps import get_service
from .services import RequestService

router = APIRouter()

@router.get("/health")
def health(svc: RequestService = Depends(get_service)) -> dict[str, str]:
    return {"status": "ok", "tracked": str(len(svc.requests))}

app.include_router(router)
```

**Why:** `Depends` lets tests inject a fake `RequestService` without touching the filesystem.

### Step 4 — Implement `POST /requests`

```python
# src/request_tracker/api.py
from fastapi import status
from .schemas import RequestCreate, RequestOut

@router.post("/requests", response_model=RequestOut, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: RequestCreate,
    svc: RequestService = Depends(get_service),
) -> RequestOut:
    new = svc.add(**payload.model_dump())
    return RequestOut.model_validate(new)
```

**Step-by-step:**
1. `payload.model_dump()` gives a plain dict ready for `svc.add(**...)`.
2. `response_model=RequestOut` filters and shapes the response.
3. `201 Created` matches REST conventions for resource creation.

### Step 5 — Implement `GET /requests` with filters

```python
# src/request_tracker/api.py
from typing import Optional
from .models import Priority, RequestStatus

@router.get("/requests", response_model=list[RequestOut])
def list_requests(
    status_filter: Optional[RequestStatus] = None,
    priority: Optional[Priority] = None,
    limit: int = 50,
    offset: int = 0,
    svc: RequestService = Depends(get_service),
) -> list[RequestOut]:
    items = svc.requests
    if status_filter is not None:
        items = [r for r in items if r.status is status_filter]
    if priority is not None:
        items = [r for r in items if r.priority is priority]
    page = items[offset: offset + limit]
    return [RequestOut.model_validate(r) for r in page]
```

**Why:** Filtering on the server is far better than asking the client to filter megabytes of JSON.

### Step 6 — Implement `GET /requests/{id}` and 404 handling

```python
# src/request_tracker/api.py
from .exceptions import RequestNotFound

@router.get("/requests/{request_id}", response_model=RequestOut)
def get_request(
    request_id: str,
    svc: RequestService = Depends(get_service),
) -> RequestOut:
    for r in svc.requests:
        if r.id == request_id:
            return RequestOut.model_validate(r)
    raise RequestNotFound(f"no request with id {request_id}")
```

**Step-by-step:**
1. We let the domain exception bubble up — the handler from Exercise 6 turns it into a 404.
2. Returning `RequestOut.model_validate(r)` validates the response shape one last time.

### Step 7 — Implement `PATCH /requests/{id}/status`

```python
@router.patch("/requests/{request_id}/status", response_model=RequestOut)
def change_status(
    request_id: str,
    payload: StatusChange,
    svc: RequestService = Depends(get_service),
) -> RequestOut:
    target = svc.change_status(request_id, payload.new_status)
    return RequestOut.model_validate(target)
```

### Step 8 — Implement `POST /requests/{id}/close`

```python
@router.post("/requests/{request_id}/close", response_model=RequestOut)
def close_request(
    request_id: str,
    payload: CloseRequest,
    svc: RequestService = Depends(get_service),
) -> RequestOut:
    target = svc.change_status(
        request_id, RequestStatus.CLOSED,
        resolution_note=payload.resolution_note,
    )
    return RequestOut.model_validate(target)
```

**Why:** A dedicated `/close` route documents the intent and the *required* `resolution_note` body. A `PATCH /status` to `closed` with a missing note would be a 400 — same outcome, less clarity.

### Step 9 — Add a global exception handler

Already done in Exercise 6. Mount it once on `app`, and the routes never need to know about HTTP.

### Step 10 — Write tests with `TestClient`

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from request_tracker.api import app
from request_tracker.deps import get_service
from request_tracker.services import RequestService
from request_tracker.repositories import JsonRequestRepository

@pytest.fixture
def client(tmp_path) -> TestClient:
    repo = JsonRequestRepository(tmp_path / "r.json")
    svc = RequestService(repo)
    app.dependency_overrides[get_service] = lambda: svc
    return TestClient(app)

# tests/test_api_requests.py
def test_create_then_list(client: TestClient) -> None:
    r = client.post("/requests", json={
        "customer_name": "Acme", "title": "Login upgrade",
        "description": "slow", "priority": "high",
    })
    assert r.status_code == 201
    rid = r.json()["id"]

    r = client.get("/requests")
    assert r.status_code == 200
    assert any(item["id"] == rid for item in r.json())

def test_get_missing_returns_404(client: TestClient) -> None:
    r = client.get("/requests/REQ-999")
    assert r.status_code == 404
    assert r.json()["error"] == "not_found"

def test_close_requires_resolution_note(client: TestClient) -> None:
    r = client.post("/requests", json={
        "customer_name": "A", "title": "X",
        "description": "", "priority": "low",
    })
    rid = r.json()["id"]
    bad = client.post(f"/requests/{rid}/close", json={"resolution_note": ""})
    assert bad.status_code == 400
    good = client.post(f"/requests/{rid}/close", json={"resolution_note": "fixed"})
    assert good.status_code == 200
    assert good.json()["status"] == "closed"
```

**Step-by-step:**
1. `app.dependency_overrides[get_service] = lambda: svc` swaps the real service for a fresh, in-memory one per test.
2. The "happy path" test confirms the round-trip; the missing-id test confirms error handling; the close test confirms the Week 2 business rule survived the move to HTTP.

### Step 11 — Run the app with `uvicorn` and explore `/docs`

```bash
uv run uvicorn request_tracker.api:app --reload --port 8000
# Open http://127.0.0.1:8000/docs in your browser.
```

**Why:** The auto-generated Swagger UI is a deliverable. Customers and frontend developers will read it before reading your code. Treat it as part of the product.

---

## Acceptance Criteria

- [ ] All required endpoints implemented with the right status codes
- [ ] Pydantic request/response models validate inputs and shape outputs
- [ ] Domain exceptions map to HTTP errors via a single handler
- [ ] `/docs` renders without errors and shows every endpoint
- [ ] `TestClient` tests cover create, list, get, status, close
- [ ] 404 returned for unknown IDs, 422 for invalid bodies, 400 for illegal transitions
- [ ] `uvicorn` runs the app and `/health` returns 200
- [ ] At least 5 meaningful commits

## AI-Off Check

**Without consulting your code**, add a `GET /requests/{id}/history` endpoint that returns the audit trail of status changes for one request. Decide: where does the history come from? Does the service know about it, or is it a separate concern?

## Reflection Questions

1. Why split `RequestCreate` (input) from `RequestOut` (output)?
2. What's the cost of using `HTTPException` everywhere instead of domain exceptions + a handler?
3. When would you version this API (`/v1/requests`)? What would force a new version?
4. How does FastAPI's auto-generated `/docs` change the way you design endpoints?

---

**Next:** Move to Week 6 when all acceptance criteria pass and you can demo the API end-to-end.
