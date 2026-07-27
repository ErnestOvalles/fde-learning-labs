# Week 4: HTTP APIs, Async, and Resilience

## Outcome

Integrate an external HTTP API through a tested client with timeouts, retries, validation, and a local fake server.

By the end of this week you will be able to:

- Read a `Response` object and pick apart status, headers, and JSON
- Distinguish a timeout from a connection error from a 4xx/5xx
- Implement retry with exponential backoff
- Use environment variables for configuration and secrets
- Use `pytest-httpx` or a local fake server to test API code without the network
- Explain when to reach for `async/await` and when not to

## Setup Checklist

- [ ] Carry forward the Week 2 / Week 3 project
- [ ] `uv add httpx tenacity python-dotenv`
- [ ] `uv add --dev pytest-httpx respx`
- [ ] Confirm a real `httpx.get("https://jsonplaceholder.typicode.com/todos/1")` returns JSON
- [ ] Create a `.env.example` file (no secrets) and a `.gitignore` line for `.env`

### Setup Walkthrough

```bash
cd week-02-layered-tracker
uv add httpx tenacity python-dotenv
uv add --dev pytest-httpx respx

# Confirm httpx works
uv run python -c "import httpx; print(httpx.get('https://jsonplaceholder.typicode.com/todos/1').json())"
```

Add a `.gitignore` line:

```
.env
data/secrets.*
```

Create a `.env.example` (committed) and `.env` (ignored):

```bash
# .env.example
API_BASE_URL=https://jsonplaceholder.typicode.com
API_TIMEOUT=5
MAX_RETRIES=3
```

## Learning Path (60–90 minutes)

**Best approach:** Learn HTTP by inspecting actual requests and responses.

1. Send a request
2. Inspect method, URL, headers, body, status, timing
3. Predict app behavior for each type of failure
4. Handle timeouts, retries, invalid responses

### Learn in this order

1. **HTTP fundamentals** — GET, POST, PUT, DELETE, status codes, headers
2. **JSON encoding/decoding** — request and response bodies
3. **httpx** — simple HTTP client for Python
4. **Error handling** — timeouts, connection errors, bad status
5. **Retry logic** — exponential backoff, jitter
6. **async/await** — syntax and basic patterns (not deep async knowledge)
7. **Mocking HTTP** — local fake server or library-level mocking
8. **Environment variables and secrets** — API keys, endpoints
9. **API client architecture** — testable, swappable integrations

### Free Resources

- [httpx documentation](https://www.python-httpx.org/)
- [Python async/await guide](https://docs.python.org/3/library/asyncio.html) (sections 18.5.1–18.5.3)
- [HTTP status codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)
- [pytest with async](https://docs.pytest.org/en/stable/how-to/fixtures.html#async-fixtures)

## Micro-Exercises (45–60 minutes)

1. Make a simple GET request with httpx; inspect the response object
2. Construct a POST request with JSON body
3. Handle a timeout error gracefully
4. Mock an HTTP endpoint using `pytest` and a fake response
5. Write a function with exponential backoff retry logic
6. Test the retry function without making real network calls
7. Load an API key from environment and validate it exists

## Main Lab: API Integration with Resilience (4–5 hours)

### Scenario

Integrate a public API (e.g., [JSONPlaceholder](https://jsonplaceholder.typicode.com/)) to enrich customer requests with external data (e.g., fetch company info by name).

### Requirements

1. Create an `ApiClient` class with:
   - Configurable base URL and timeout
   - Request/response logging
   - Error handling (timeouts, bad status, invalid JSON)
   - Retry logic with exponential backoff
2. Integrate the client into your tracker:
   - On request creation, fetch company info from a public API
   - Store the fetched data in the request
   - Handle API failures gracefully (no blocking)
3. Add configuration via environment variables:
   - `API_BASE_URL`
   - `API_TIMEOUT` (seconds)
   - `MAX_RETRIES`
   - `API_KEY` (if needed)
4. Write tests:
   - Mock API responses (use `pytest` fixtures)
   - Test retry logic
   - Test timeout handling
   - Test malformed API responses
5. Add a CLI command to verify the API connection

### Build Steps

1. Design the `ApiClient` interface
2. Implement basic GET request
3. Add error handling (timeouts, bad status)
4. Add retry logic with exponential backoff
5. Integrate into `RequestService`
6. Add environment variable loading with defaults
7. Mock API responses in tests using `pytest`
8. Write tests for happy path and error cases
9. Add integration test with a local fake server (optional)
10. Document API integration in README

## Step-by-Step Walkthrough

### Exercise 1 — Make a simple GET request with httpx; inspect the response

```python
# practice.py
import httpx

resp = httpx.get("https://jsonplaceholder.typicode.com/todos/1", timeout=5.0)
print("status:", resp.status_code)
print("headers content-type:", resp.headers.get("content-type"))
print("elapsed ms:", resp.elapsed.total_seconds() * 1000)
print("json:", resp.json())
print("ok?:", resp.is_success)        # 2xx shortcut
print("client error?:", resp.is_client_error)  # 4xx shortcut
```

**Step-by-step:**
1. `httpx.get(...)` returns a `Response` immediately — no need to call `.send()`.
2. `resp.elapsed` is a `timedelta` you can log for latency tracking.
3. `is_success` / `is_client_error` / `is_server_error` are clearer than comparing integers to 200/400/500.

### Exercise 2 — Construct a POST request with JSON body

```python
# practice.py
import httpx

payload = {"title": "hello", "body": "world", "userId": 1}
resp = httpx.post(
    "https://jsonplaceholder.typicode.com/posts",
    json=payload,
    timeout=5.0,
    headers={"X-Request-Id": "demo-001"},
)
print(resp.status_code, resp.json()["id"])
```

**Step-by-step:**
1. `json=payload` is shorthand for `data=json.dumps(payload), headers={"content-type": "application/json"}`.
2. The custom `X-Request-Id` header is useful for tracing one request through server logs.
3. POST endpoints usually return the created resource — extract the new ID from `resp.json()`.

### Exercise 3 — Handle a timeout error gracefully

```python
# practice.py
import httpx

try:
    httpx.get("https://httpbin.org/delay/10", timeout=2.0)
except httpx.TimeoutException as e:
    print("Timed out:", e)
except httpx.HTTPError as e:            # base class for all httpx errors
    print("Other HTTP error:", e)
```

**Step-by-step:**
1. `httpx.TimeoutException` is raised when the timeout fires.
2. Catch the **specific** exception first, then `httpx.HTTPError` as a fallback.
3. Decide on a fallback: empty result, cached value, or a domain-level "unknown" status — never let a timeout bubble up as a 500 to your CLI user.

### Exercise 4 — Mock an HTTP endpoint using `pytest-httpx`

```python
# tests/test_api_client.py
import httpx
import pytest
from request_tracker.api_client import ApiClient

@pytest.fixture
def client() -> ApiClient:
    return ApiClient(base_url="https://example.test", timeout=2.0)

def test_get_company_returns_dict(httpx_mock, client: ApiClient) -> None:
    httpx_mock.add_response(
        url="https://example.test/companies?name=Acme",
        json={"name": "Acme", "country": "US"},
        status_code=200,
    )
    result = client.get_company("Acme")
    assert result["country"] == "US"
```

**Step-by-step:**
1. `httpx_mock` is a pytest fixture that intercepts every HTTP call made by the test.
2. You assert on real `url=`, headers, and method matching — no string-concatenated URLs in your assertions.
3. The mock is automatically reset between tests, so there's no leakage.

### Exercise 5 — Write a function with exponential backoff retry logic

```python
# src/request_tracker/api_client.py
import logging
import random
import httpx
from tenacity import (retry, retry_if_exception_type,
                      stop_after_attempt, wait_exponential_jitter)

log = logging.getLogger(__name__)

RETRYABLE = (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)

class ApiClient:
    def __init__(self, base_url: str, timeout: float = 5.0,
                 max_retries: int = 3) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

    @retry(
        retry=retry_if_exception_type(RETRYABLE),
        wait=wait_exponential_jitter(initial=0.2, max=2.0),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def get_company(self, name: str) -> dict:
        log.info("fetching company", extra={"name": name})
        resp = self._client.get("/companies", params={"name": name})
        resp.raise_for_status()           # raises for 4xx/5xx
        return resp.json()
```

**Step-by-step:**
1. `retry_if_exception_type(RETRYABLE)` only retries on transient errors — never on 4xx, since those are not going to fix themselves.
2. `wait_exponential_jitter` doubles the wait each attempt and adds randomness so retries don't synchronize.
3. `reraise=True` lets the original exception propagate after the final attempt.

### Exercise 6 — Test the retry function without making real network calls

```python
# tests/test_api_client.py
import httpx
import pytest
from request_tracker.api_client import ApiClient

def test_get_company_retries_on_timeout(httpx_mock) -> None:
    httpx_mock.add_exception(httpx.TimeoutException("slow"))
    httpx_mock.add_exception(httpx.TimeoutException("slow"))
    httpx_mock.add_response(
        url="https://example.test/companies?name=Acme",
        json={"name": "Acme"},
    )
    client = ApiClient("https://example.test", timeout=1.0, max_retries=3)
    assert client.get_company("Acme")["name"] == "Acme"

def test_get_company_gives_up_after_max_retries(httpx_mock) -> None:
    for _ in range(3):
        httpx_mock.add_exception(httpx.TimeoutException("still slow"))
    client = ApiClient("https://example.test", timeout=1.0, max_retries=3)
    with pytest.raises(httpx.TimeoutException):
        client.get_company("Acme")
```

**Step-by-step:**
1. `add_exception` queues one fake error per call — the third call finally gets a real `Response`.
2. The first test verifies "we eventually succeed."
3. The second test verifies "we don't retry forever" — important for back-pressure on a downstream outage.

### Exercise 7 — Load an API key from environment and validate it exists

```python
# src/request_tracker/config.py
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()  # no-op if .env is absent

@dataclass(frozen=True)
class Settings:
    api_base_url: str
    api_timeout: float
    max_retries: int
    api_key: str | None

def load_settings() -> Settings:
    api_key = os.environ.get("API_KEY", "").strip()
    if not api_key:
        api_key = None        # treat empty as "no auth"
    try:
        timeout = float(os.environ.get("API_TIMEOUT", "5"))
    except ValueError:
        raise RuntimeError("API_TIMEOUT must be a number")
    if timeout <= 0:
        raise RuntimeError("API_TIMEOUT must be positive")
    return Settings(
        api_base_url=os.environ.get("API_BASE_URL", "https://jsonplaceholder.typicode.com"),
        api_timeout=timeout,
        max_retries=int(os.environ.get("MAX_RETRIES", "3")),
        api_key=api_key,
    )
```

```python
# usage
from request_tracker.config import load_settings
from request_tracker.api_client import ApiClient

s = load_settings()
client = ApiClient(s.api_base_url, s.api_timeout, s.max_retries)
```

**Step-by-step:**
1. `load_dotenv()` reads `.env` into `os.environ` at startup.
2. Defaults keep the app runnable with zero config; explicit `RuntimeError` for values that are present but invalid.
3. The `Settings` dataclass is the single source of truth — pass it to anything that needs configuration, instead of reading `os.environ` everywhere.

---

### Step 1 — Design the `ApiClient` interface

Sketched in Exercise 5. The interface is: `ApiClient(base_url, timeout, max_retries)` plus a method per upstream endpoint you need. Constructor takes config; methods take domain arguments. No method reads `os.environ` directly.

### Step 2 — Implement basic GET request

```python
def get_company(self, name: str) -> dict:
    resp = self._client.get("/companies", params={"name": name})
    resp.raise_for_status()
    return resp.json()
```

**Why:** `raise_for_status()` converts 4xx/5xx into `HTTPStatusError` so you handle them in one place rather than checking status everywhere.

### Step 3 — Add error handling (timeouts, bad status)

Wrap calls and translate to domain errors:

```python
# src/request_tracker/api_client.py
class CompanyLookupError(RuntimeError): ...

def get_company(self, name: str) -> dict:
    try:
        resp = self._client.get("/companies", params={"name": name})
        resp.raise_for_status()
        return resp.json()
    except httpx.TimeoutException as e:
        raise CompanyLookupError("upstream timeout") from e
    except httpx.HTTPStatusError as e:
        raise CompanyLookupError(f"upstream {e.response.status_code}") from e
    except (httpx.HTTPError, ValueError) as e:
        # ValueError covers json.JSONDecodeError
        raise CompanyLookupError("upstream parse error") from e
```

**Why:** Translating *technical* errors to *domain* errors at the boundary keeps the rest of the app free of `httpx` imports.

### Step 4 — Add retry logic with exponential backoff

Already wired in Exercise 5 with `tenacity`. Keep the decorator on the *public* method, not the raw httpx call, so you can re-use the same client in tests without retry interference.

### Step 5 — Integrate into `RequestService`

```python
# src/request_tracker/services.py
class RequestService:
    def __init__(self, repo, api_client: ApiClient | None = None,
                 clock=utc_now) -> None:
        self.repo = repo
        self.api = api_client
        self.clock = clock
        self.requests = repo.load()

    def add(self, **fields) -> CustomerRequest:
        fields["id"] = self.repo.next_id(self.requests)
        company_note = ""
        if self.api is not None and (name := fields.get("customer_name")):
            try:
                info = self.api.get_company(name)
                company_note = f" (country: {info.get('country', '?')})"
            except CompanyLookupError as e:
                log.warning("company lookup failed", extra={"err": str(e)})
        fields.setdefault("description", "")
        fields["description"] = (fields["description"] + company_note).strip()
        request = CustomerRequest(**fields)
        self.requests.append(request)
        self.repo.save(self.requests)
        return request
```

**Why:** Failure of the external API never blocks the user from creating a request. The service degrades gracefully — exactly what an FDE deliverable should do.

### Step 6 — Add environment variable loading with defaults

Already done in Exercise 7 via `load_settings()`.

### Step 7 — Mock API responses in tests using `pytest`

Use `httpx_mock` (Exercise 4/6) to replace the real `httpx.Client` with a fake transport.

### Step 8 — Write tests for happy path and error cases

```python
# tests/test_service_integration.py
from request_tracker.api_client import ApiClient
from request_tracker.repositories import JsonRequestRepository
from request_tracker.services import RequestService

def test_add_enriches_description_with_country(httpx_mock, tmp_path) -> None:
    httpx_mock.add_response(
        url="https://example.test/companies?name=Acme",
        json={"name": "Acme", "country": "US"},
    )
    service = RequestService(
        JsonRequestRepository(tmp_path / "r.json"),
        api_client=ApiClient("https://example.test"),
    )
    new = service.add(customer_name="Acme", title="X",
                      description="please help", priority="low")
    assert "country: US" in new.description

def test_add_succeeds_even_if_api_fails(httpx_mock, tmp_path) -> None:
    httpx_mock.add_exception(Exception("network down"))
    service = RequestService(
        JsonRequestRepository(tmp_path / "r.json"),
        api_client=ApiClient("https://example.test", max_retries=1),
    )
    new = service.add(customer_name="Acme", title="X",
                      description="please help", priority="low")
    assert new.description == "please help"
```

**Step-by-step:**
1. The first test proves enrichment *works* when the API cooperates.
2. The second test proves the app *still works* when the API doesn't — this is the property that matters most for an FDE.

### Step 9 — Add integration test with a local fake server (optional)

```python
# tests/test_api_integration.py
import threading
import time
import httpx
import pytest
from request_tracker.api_client import ApiClient

def _start_fake_server() -> str:
    from http.server import BaseHTTPRequestHandler, HTTPServer
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.path.startswith("/companies"):
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"name":"Acme","country":"US"}')
            else:
                self.send_response(404); self.end_headers()
        def log_message(self, *a, **kw): pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{port}"

def test_end_to_end_with_fake_server() -> None:
    base = _start_fake_server()
    client = ApiClient(base, timeout=2.0)
    assert client.get_company("Acme")["country"] == "US"
```

**Why:** A real socket round-trip exercises `httpx` transport, DNS, and serialization paths that `httpx_mock` does not. Useful once per project; do not overuse.

### Step 10 — Document API integration in README

Add a section:

```markdown
## Environment Variables

| Variable        | Default                              | Purpose                       |
|-----------------|--------------------------------------|-------------------------------|
| API_BASE_URL    | https://jsonplaceholder.typicode.com | Upstream base URL             |
| API_TIMEOUT     | 5                                    | Request timeout (seconds)     |
| MAX_RETRIES     | 3                                    | Retries on transient errors   |
| API_KEY         | (unset)                              | Optional bearer token         |

## Verifying the Connection

Run the CLI's health check:

    uv run python -m request_tracker health
```

**Why:** Every teammate who later needs to set up local dev should be able to copy a `.env.example` and run one command to confirm connectivity.

---

## Acceptance Criteria

- [ ] ApiClient handles timeouts without crashing
- [ ] Failed requests retry up to N times with exponential backoff
- [ ] Tests mock API responses (no real network calls in tests)
- [ ] Invalid API responses fail gracefully
- [ ] Environment variables are read and validated
- [ ] No secrets are logged
- [ ] CLI validates API connection on startup
- [ ] All tests pass
- [ ] At least 5 meaningful commits

## AI-Off Check

**Without examples**, implement a circuit breaker pattern that prevents excessive API calls to a failing endpoint (e.g., fail fast after 3 consecutive errors for 60 seconds).

## Reflection Questions

1. Why separate the API client from the business logic?
2. What happens if the API times out during a request? How should the app respond?
3. Why mock API responses instead of calling the real API in tests?
4. When would you use async/await instead of synchronous httpx calls?

## Phase 1 Gate: Python Fundamentals

**You've completed Phase 1 when:**

- [ ] You can build a typed Python program from a blank folder
- [ ] You can test it, debug it, and explain it without consulting tutorials
- [ ] Your code is clean, layered, and doesn't mix concerns
- [ ] Your tests are meaningful and catch real defects
- [ ] Your git history tells the story of the work

**Next:** Move to Phase 2 (FastAPI and full-stack development).
