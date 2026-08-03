# Week 3: Automated Testing and Debugging

## Outcome

Create a trustworthy test suite for the layered tracker and learn to diagnose failures systematically.

By the end of this week you will be able to:

- Write tests in the **Arrange / Act / Assert** pattern
- Use `pytest` fixtures and `tmp_path` to keep tests isolated
- Parametrize tests over many inputs without copy-pasting
- Decide when to use a real object, a fake, or a mock
- Catch a real bug with a regression test
- Read a stack trace and use the VS Code debugger to inspect state

## Setup Checklist

- [ ] Use the Week 2 project as the starting point
- [ ] `uv add --dev pytest pytest-cov`
- [ ] Create the `tests/` directory
- [ ] Confirm `uv run pytest` finds zero tests yet
- [ ] Open the VS Code Testing sidebar (`Ctrl+Shift+T` on Windows/Linux, `Cmd+Shift+T` on macOS)

### Setup Walkthrough

```bash
cd week-02-layered-tracker           # or copy it forward
uv add --dev pytest pytest-cov
mkdir -p tests
touch tests/__init__.py tests/conftest.py

# Run from project root
uv run pytest
# expected: no tests ran (or "collected 0 items")
```

Add a `pytest` configuration block to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = "-q --strict-markers"
testpaths = ["tests"]
```

## Learning Path (60–90 minutes)

**Best approach:** Testing is learned by watching a test catch a real defect.

For every important rule:
1. Write the expected behavior in plain English
2. Write a **failing** test
3. Confirm it fails for the right reason
4. Implement the smallest fix
5. Refactor while the test stays green

Do not chase coverage percentages. Examine what behavior is actually covered.

### Learn in this order

1. **Arrange, Act, Assert** — the three-phase test pattern
2. **Unit vs. integration tests** — when to use each
3. **pytest discovery and assertions**
4. **Fixtures and temporary paths** (`tmp_path`, `@pytest.fixture`)
5. **Parametrization** — test multiple inputs
6. **Mocks and when NOT to mock** — real vs. fake objects
7. **Regression tests** — tests that catch re-introduced bugs
8. **VS Code test explorer and debugger**
9. **Logging levels and stack traces**

### Free Resources

- [pytest getting started](https://docs.pytest.org/en/stable/getting-started.html)
- [pytest fixtures](https://docs.pytest.org/en/stable/explanation/fixtures.html)
- [pytest parametrization](https://docs.pytest.org/en/stable/how-to/parametrize.html)
- [VS Code Python testing](https://code.visualstudio.com/docs/python/testing)
- [VS Code Python debugging](https://code.visualstudio.com/docs/python/debugging)
- [Python logging HOWTO](https://docs.python.org/3/howto/logging.html)

## Micro-Exercises (45–60 minutes)

1. Test a pure `calculate_sla_hours(priority)` function (parametrize all 3 priorities)
2. Use `tmp_path` to test writing and reading a file
3. Create three request fixtures in `conftest.py`
4. Create a regression test for corrupt JSON handling
5. Mock a clock so timestamps are predictable
6. Debug a deliberately failing test with a breakpoint
7. Add one intentional bug and prove a test catches it

## Main Lab: Test and Harden the Tracker (4–5 hours)

### Test File Structure

Create these test files:

```
tests/
├── conftest.py              # shared fixtures
├── test_models.py
├── test_service.py
├── test_json_repository.py
└── test_csv_import.py
```

### Required Tests

**Models** (`test_models.py`):
- [ ] Blank title rejected
- [ ] Invalid priority rejected
- [ ] Default status is `open`

**Service** (`test_service.py`):
- [ ] Allowed and forbidden status transitions
- [ ] Closing requires resolution note
- [ ] Unknown request produces a domain error
- [ ] Update changes `updated_at`, not `created_at`

**Repository** (`test_json_repository.py`):
- [ ] Empty repository
- [ ] Save/load round trip
- [ ] Missing file (starts empty)
- [ ] Corrupt file (helpful error message)
- [ ] Duplicate ID detection

**CSV** (`test_csv_import.py`):
- [ ] All valid rows import
- [ ] Mix of valid and invalid rows
- [ ] Missing required headers
- [ ] Extra columns handled gracefully
- [ ] Empty file

### Build Steps

1. Add pytest to `pyproject.toml` (`uv add --dev pytest`)
2. Write 3 simple model tests
3. Create shared fixtures in `conftest.py`
4. Write service tests *before* changing service code
5. Add repository integration tests using `tmp_path`
6. Parametrize all status transitions
7. Replace global time calls with injected clock if needed
8. Add structured logging to repository/service boundaries
9. Introduce one deliberate defect and prove a test catches it
10. Configure one command that runs lint, type checks, and tests

## Step-by-Step Walkthrough

> Every snippet below is runnable. Add it to the indicated file, then run `uv run pytest` to watch it pass (or fail, on purpose).

### Exercise 1 — Test a pure `calculate_sla_hours(priority)` function

First, add the function under test:

```python
# src/request_tracker/services.py
def calculate_sla_hours(priority: str) -> int:
    return {"high": 4, "medium": 24, "low": 72}.get(priority, 72)
```

Then the test:

```python
# tests/test_services_helpers.py
import pytest
from request_tracker.services import calculate_sla_hours

@pytest.mark.parametrize(
    "priority,expected",
    [("high", 4), ("medium", 24), ("low", 72), ("unknown", 72)],
)
def test_calculate_sla_hours(priority: str, expected: int) -> None:
    assert calculate_sla_hours(priority) == expected
```

**Step-by-step:**
1. `pytest.mark.parametrize` runs the test once per row of inputs.
2. Use the "Arrange" inputs as the first argument; "Act" is the function call; "Assert" is the single `assert` line.
3. `("unknown", 72)` documents the fallback behavior — without it, future readers wonder if it's intentional.

### Exercise 2 — Use `tmp_path` to test writing and reading a file

`tmp_path` is a built-in pytest fixture that gives each test its own private directory. No cleanup needed.

```python
# tests/test_json_repository.py
from pathlib import Path
from request_tracker.repositories import JsonRequestRepository

def test_save_then_load_round_trip(tmp_path: Path) -> None:
    repo = JsonRequestRepository(tmp_path / "requests.json")
    repo.save([{"id": "REQ-001", "title": "Login",
                "customer_name": "Acme", "description": "x",
                "priority": "high", "status": "open",
                "created_at": "2025-01-15T10:30:00Z",
                "updated_at": "2025-01-15T10:30:00Z"}])
    loaded = repo.load()
    assert len(loaded) == 1
    assert loaded[0].id == "REQ-001"
```

**Step-by-step:**
1. `tmp_path` is unique per test, so parallel runs never collide.
2. Pass the file path into the repository constructor rather than relying on a global constant — this is what makes the testable.
3. After this test, `tmp_path/requests.json` is gone automatically. No `os.remove` calls.

### Exercise 3 — Create three request fixtures in `conftest.py`

```python
# tests/conftest.py
import pytest
from request_tracker.models import CustomerRequest, Priority, RequestStatus

@pytest.fixture
def low_request() -> CustomerRequest:
    return CustomerRequest(
        id="REQ-001", customer_name="Acme", title="Email bounce",
        description="SMTP errors", priority=Priority.LOW,
    )

@pytest.fixture
def high_request() -> CustomerRequest:
    return CustomerRequest(
        id="REQ-002", customer_name="Beta", title="Login outage",
        description="Users locked out", priority=Priority.HIGH,
        status=RequestStatus.IN_PROGRESS,
    )

@pytest.fixture
def closed_request() -> CustomerRequest:
    return CustomerRequest(
        id="REQ-003", customer_name="Gamma", title="Resolved",
        description="Done", priority=Priority.MEDIUM,
        status=RequestStatus.CLOSED,
    )

@pytest.fixture
def sample_requests(low_request, high_request, closed_request):
    return [low_request, high_request, closed_request]
```

**Step-by-step:**
1. Tests that take a `sample_requests` parameter get all three pre-built — pytest resolves fixtures by name.
2. A fixture can request other fixtures (notice `sample_requests` lists three above).
3. Use `scope="session"` on a fixture if it is expensive to create and read-only.

### Exercise 4 — Create a regression test for corrupt JSON handling

A *regression test* pins down a bug that already happened, so it can never silently come back.

```python
# tests/test_json_repository.py
import json
from pathlib import Path
import pytest
from request_tracker.repositories import JsonRequestRepository

def test_corrupt_json_raises_helpful_error(tmp_path: Path) -> None:
    bad = tmp_path / "requests.json"
    bad.write_text("{ not valid json")
    repo = JsonRequestRepository(bad)
    with pytest.raises(RuntimeError, match="not valid JSON"):
        repo.load()
```

**Step-by-step:**
1. Write the bad file directly with `Path.write_text` — no need to trigger the bug through real app code.
2. `pytest.raises` asserts the exception type. `match=` is a regex against the message.
3. This is the test you would have wished for on the day the bug shipped.

### Exercise 5 — Mock a clock so timestamps are predictable

The trick: depend on a clock function, then swap it in tests.

```python
# src/request_tracker/services.py (modified)
from datetime import datetime, UTC
from typing import Callable

Clock = Callable[[], datetime]

def utc_now() -> datetime:
    return datetime.now(UTC)

class RequestService:
    def __init__(self, repo, clock: Clock = utc_now) -> None:
        self.repo = repo
        self.clock = clock
        # ...
```

```python
# tests/test_service.py
from datetime import datetime
from request_tracker.repositories import JsonRequestRepository
from request_tracker.services import RequestService

class FakeClock:
    def __init__(self, fixed: datetime) -> None:
        self.fixed = fixed
    def __call__(self) -> datetime:
        return self.fixed

def test_change_status_bumps_updated_at(tmp_path) -> None:
    repo = JsonRequestRepository(tmp_path / "requests.json")
    service = RequestService(repo, clock=FakeClock(datetime(2025, 6, 1, 12)))
    service.requests.append(service.add(
        customer_name="Acme", title="X", description="y",
        priority="low",
    ))
    # Add a second time point by changing the clock:
    service.clock.fixed = datetime(2025, 6, 2, 9)
    target = service.requests[0]
    service.change_status(target.id, "in_progress")
    assert target.updated_at.startswith("2025-06-02")
    assert target.created_at.startswith("2025-06-01")
```

**Step-by-step:**
1. Inject a `clock` callable rather than calling `datetime.now` directly.
2. In production, the default `utc_now` is used. In tests, a `FakeClock` returns whatever you set.
3. A *fake* (a real object with a working implementation) is usually better than `unittest.mock.patch` for time — fakes have no surprise behavior.

### Exercise 6 — Debug a deliberately failing test with a breakpoint

```python
# tests/test_service.py
def test_placeholder() -> None:
    from request_tracker.services import RequestService
    repo = None                              # Intentional bug
    service = RequestService(repo)          # will raise AttributeError
    assert service.requests == []
```

```bash
uv run pytest tests/test_service.py::test_placeholder --maxfail=1
```

**Step-by-step:**
1. VS Code: open `test_service.py`, click in the gutter next to the failing line, then `F5` → "Python File" or use the Testing sidebar's debug icon.
2. The debugger pauses on the breakpoint; inspect `repo`, `service`, and the call stack.
3. Step over (`F10`), step into (`F11`), continue (`F5`).

### Exercise 7 — Add one intentional bug and prove a test catches it

```python
# src/request_tracker/services.py  (introduce bug)
def change_status(self, request_id, new, resolution_note=None):
    target = self._find(request_id)
    # BUG: forgot to enforce the resolution note rule for CLOSED
    if new not in ALLOWED_TRANSITIONS[target.status]:
        raise IllegalStatusTransition(...)
    target.status = new
    self.repo.save(self.requests)
```

```python
# tests/test_service.py
def test_closing_requires_resolution_note(tmp_path) -> None:
    service = RequestService(JsonRequestRepository(tmp_path / "requests.json"))
    service.requests.append(service.add(
        customer_name="Acme", title="X", description="y", priority="low",
    ))
    rid = service.requests[0].id
    with pytest.raises(ResolutionNoteRequired):
        service.change_status(rid, "closed", resolution_note="")
```

```bash
uv run pytest tests/test_service.py::test_closing_requires_resolution_note
# expected: FAILED (because of the bug)
```

**Step-by-step:**
1. Run the test — it fails for the right reason (the bug you introduced).
2. Restore the correct implementation. The test now passes.
3. Leave the test in place forever — this is your regression net for that rule.

---

### Step 1 — Add pytest to `pyproject.toml`

Already done in Setup. Confirm:

```bash
uv run pytest --version
# pytest 8.x
```

### Step 2 — Write 3 simple model tests

```python
# tests/test_models.py
import pytest
from pydantic import ValidationError
from request_tracker.models import CustomerRequest, Priority, RequestStatus

def test_blank_title_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CustomerRequest(id="REQ-001", customer_name="Acme",
                        title="  ", description="x",
                        priority=Priority.LOW)

def test_invalid_priority_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CustomerRequest(id="REQ-001", customer_name="Acme",
                        title="ok", description="x",
                        priority="purple")  # type: ignore[arg-type]

def test_default_status_is_open() -> None:
    r = CustomerRequest(id="REQ-001", customer_name="Acme",
                        title="ok", description="x",
                        priority=Priority.LOW)
    assert r.status is RequestStatus.OPEN
```

**Why:** Three tests, one behavior each. They are the smallest possible trust contract for `CustomerRequest`.

### Step 3 — Create shared fixtures in `conftest.py`

Already done in Exercise 3. Each test file can now reference `sample_requests` without rebuilding data.

### Step 4 — Write service tests *before* changing service code

This is the test-first rule. For one behavior — "unknown request raises `RequestNotFound`" — write:

```python
# tests/test_service.py
import pytest
from request_tracker.exceptions import RequestNotFound
from request_tracker.repositories import JsonRequestRepository
from request_tracker.services import RequestService

def test_change_status_unknown_id_raises(tmp_path) -> None:
    service = RequestService(JsonRequestRepository(tmp_path / "requests.json"))
    with pytest.raises(RequestNotFound):
        service.change_status("REQ-999", "in_progress")
```

Run the test; if the code already satisfies the rule, it passes immediately. If not, fix the code, not the test.

### Step 5 — Add repository integration tests using `tmp_path`

```python
# tests/test_json_repository.py
import json
from pathlib import Path
import pytest
from request_tracker.repositories import JsonRequestRepository
from request_tracker.models import CustomerRequest, Priority

def test_missing_file_returns_empty_list(tmp_path: Path) -> None:
    repo = JsonRequestRepository(tmp_path / "nope.json")
    assert repo.load() == []

def test_round_trip_preserves_priority_enum(tmp_path: Path) -> None:
    repo = JsonRequestRepository(tmp_path / "r.json")
    repo.save([CustomerRequest(id="REQ-001", customer_name="A",
                               title="X", description="y",
                               priority=Priority.HIGH)])
    assert repo.load()[0].priority is Priority.HIGH
```

**Why:** `tmp_path` is the only fixture you need to keep tests hermetic. Never `cd` into a test directory or write to the real `data/`.

### Step 6 — Parametrize all status transitions

```python
# tests/test_service.py
import pytest
from request_tracker.models import RequestStatus
from request_tracker.exceptions import IllegalStatusTransition
from request_tracker.repositories import JsonRequestRepository
from request_tracker.services import RequestService, ALLOWED_TRANSITIONS

@pytest.mark.parametrize("from_status,to_status,allowed", [
    (RequestStatus.OPEN,        RequestStatus.IN_PROGRESS, True),
    (RequestStatus.OPEN,        RequestStatus.CLOSED,      True),
    (RequestStatus.IN_PROGRESS, RequestStatus.CLOSED,      True),
    (RequestStatus.IN_PROGRESS, RequestStatus.OPEN,        True),
    (RequestStatus.CLOSED,      RequestStatus.OPEN,        False),
    (RequestStatus.CLOSED,      RequestStatus.IN_PROGRESS, False),
])
def test_all_transitions(tmp_path, from_status, to_status, allowed) -> None:
    service = RequestService(JsonRequestRepository(tmp_path / "r.json"))
    service.requests.append(service.add(
        customer_name="A", title="X", description="y", priority="low",
    ))
    target = service.requests[0]
    target.status = from_status
    if allowed:
        service.change_status(target.id, to_status)
        assert target.status is to_status
    else:
        with pytest.raises(IllegalStatusTransition):
            service.change_status(target.id, to_status)
```

**Why:** A matrix like this is much harder to misread than six separate tests. The expected outcomes are literally the data.

### Step 7 — Replace global time calls with injected clock

Already done in Exercise 5. Make sure every test that depends on time uses the `FakeClock`.

### Step 8 — Add structured logging to repository/service boundaries

```python
# src/request_tracker/repositories.py
import logging
log = logging.getLogger(__name__)

class JsonRequestRepository:
    def load(self) -> list[CustomerRequest]:
        log.info("loading requests", extra={"path": str(self.path)})
        # ... existing code ...

    def save(self, requests: list[CustomerRequest]) -> None:
        log.info("saving requests", extra={"count": len(requests),
                                           "path": str(self.path)})
        # ... existing code ...
```

```python
# src/request_tracker/__init__.py or cli.py
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
```

**Why:** Logs at the boundary between layers tell you *where* time was spent. They are not a replacement for tests — they are a complement that pays off in Week 19 (observability).

### Step 9 — Introduce one deliberate defect and prove a test catches it

You already did this in Exercise 7. Re-introduce the bug, run the suite, watch exactly one test fail, then fix it. The point is to build the muscle memory of "test fails → investigate → fix."

### Step 10 — Configure one command that runs lint, type checks, and tests

```toml
# pyproject.toml
[tool.pdm.scripts]   # or use `task`/`make` if you prefer
# pdm is not a dep here — use a Makefile instead
```

```makefile
# Makefile
.PHONY: check
check:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src
	uv run pytest
```

```bash
make check
```

**Why:** When CI runs in Week 18, it will be a near-copy of `make check`. Building the habit now means CI is a safety net, not a surprise.

---

## Acceptance Criteria

- [ ] Tests run from a clean clone
- [ ] No test depends on real user files
- [ ] Tests are deterministic (same result every run)
- [ ] All status-transition combinations covered
- [ ] A deliberately introduced defect causes test failure
- [ ] Logs add diagnostic value without printing sensitive data
- [ ] README explains how to run quality checks
- [ ] At least 5 meaningful commits

## AI-Off Check

**Without looking at examples**, write the failing tests for this new rule: "High-priority requests cannot be closed without an owner assignment." Then implement the rule.

## Reflection Questions

1. Which tests describe actual business value?
2. Which test is too tightly coupled to implementation?
3. What's the difference between a fake repository and a mocked repository?
4. When did the debugger reveal more than a print statement?

---

**Next:** Move to Week 4 when all tests pass and acceptance criteria are met.
