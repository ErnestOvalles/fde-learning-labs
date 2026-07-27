# Week 2: Data Models, Validation, and Clean Structure

## Outcome

Refactor Week 1's tracker into a **layered, typed application** using Pydantic models, repositories, services, and a CLI.

By the end of this week you will be able to:

- Explain the difference between a `dataclass` and a `BaseModel`
- Replace loose dictionaries with a validated model that rejects bad input
- Move file I/O out of the CLI into a repository
- Move business rules out of the CLI into a service
- Import and export the same data as CSV
- Run `ruff check` and `mypy src` and fix what they report

## Setup Checklist

- [ ] Confirm Week 1's `tracker` folder still runs
- [ ] Copy it into `phase-1-python/week-02-layered-tracker/` (or start fresh)
- [ ] `uv add pydantic`
- [ ] `uv add --dev ruff mypy pytest`
- [ ] Verify `uv run python -c "import pydantic; print(pydantic.VERSION)"`

### Setup Walkthrough

```bash
# 1. Make a new project folder for this week
mkdir week-02-layered-tracker && cd week-02-layered-tracker
uv init
uv python pin 3.13

# 2. Add runtime and dev dependencies
uv add pydantic
uv add --dev ruff mypy pytest

# 3. Create the layered source tree
mkdir -p src/request_tracker data tests
touch src/request_tracker/__init__.py

# 4. Sanity-check imports
uv run python -c "from pydantic import BaseModel; print('pydantic ok')"
```

## Learning Path (60–90 minutes)

**Best approach:** Refactor your working Week 1 code. Feel which problems each abstraction solves rather than learning OOP as a vocabulary exercise.

### Learn in this order

1. **Type hints and unions** — `str | int`, `Optional[T]`
2. **Dataclasses vs. Pydantic** — which to use and why
3. **Classes, constructors, instance methods, composition**
4. **Enums** — `RequestStatus`, `Priority`
5. **Validation** — Pydantic validators and field constraints
6. **Custom exceptions** — domain-specific error types
7. **Dependency direction** — how to structure layers
8. **Repository pattern** — separate data access from business logic
9. **Service layer** — where business rules live
10. **CSV reading/writing** — multi-format persistence
11. **Ruff and mypy** — automated formatting and type checking

### Free Resources

- [Python typing documentation](https://docs.python.org/3/library/typing.html)
- [Python classes tutorial](https://docs.python.org/3/tutorial/classes.html)
- [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/)
- [Pydantic validators](https://docs.pydantic.dev/latest/concepts/validators/)
- [Ruff tutorial](https://docs.astral.sh/ruff/tutorial/)
- [mypy getting started](https://mypy.readthedocs.io/en/stable/getting_started.html)

## Micro-Exercises (45–60 minutes)

Create `practice.py` at the project root and complete these:

1. Model a request using `dataclass`
2. Model the same request with Pydantic
3. Pass invalid priority to both; compare behavior
4. Create `RequestStatus` and `Priority` enums
5. Write a validator that rejects blank titles
6. Export two request instances to CSV
7. Run Ruff against deliberately poorly formatted code
8. Add a type error and confirm mypy finds it

## Main Lab: Layered Request Tracker (4–5 hours)

### Target Structure

```
week-02-layered-tracker/
├── pyproject.toml
├── README.md
├── src/
│   └── request_tracker/
│       ├── __init__.py
│       ├── cli.py          # input() and print() only
│       ├── models.py       # Pydantic models, enums, validation
│       ├── exceptions.py   # domain-specific errors
│       ├── repositories.py # load, save, find, list
│       └── services.py     # business rules
├── data/
└── tests/
    └── (covered in Week 3)
```

### Responsibilities

- **`models.py`:** validated data shapes, enums
- **`repositories.py`:** load, save, find, list data
- **`services.py`:** business rules and transitions
- **`cli.py`:** input/output only — no file or business logic
- **`exceptions.py`:** custom error types

### Build Steps

1. Copy Week 1 into a new folder
2. Introduce enums (`RequestStatus`, `Priority`) without changing behavior
3. Replace dictionaries with `CustomerRequest` Pydantic model
4. Create `JsonRequestRepository` with load/save methods
5. Move status-transition rules to `RequestService`
6. Keep `input()` and `print()` only in `cli.py`
7. Add rule: closed requests cannot move back to in-progress
8. Add rule: closing requires a resolution note
9. Add CSV export with `csv.DictWriter`
10. Add CSV import with row-level validation errors
11. Report valid and rejected row counts
12. Configure Ruff and mypy in `pyproject.toml`

## Step-by-Step Walkthrough

> Follow these sub-sections in order. Every snippet is runnable. Cross-reference Week 01's `find_request` and `save_requests` for the patterns being replaced here.

### Exercise 1 — Model a request using `dataclass`

A `dataclass` is the simplest way to bundle typed fields together. It does **no validation**, so it's appropriate for trusted internal data.

```python
# practice.py
from dataclasses import dataclass, field
from datetime import datetime, UTC

@dataclass
class RequestDC:
    id: str
    customer_name: str
    title: str
    description: str
    priority: str
    status: str = "open"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

r = RequestDC(
    id="REQ-001",
    customer_name="Acme Corp",
    title="Login system upgrade",
    description="Users report slow login times",
    priority="high",
)
print(r)
# Notice: nothing stopped us from passing priority="purple".
```

**Step-by-step:**
1. Paste the snippet into `practice.py` and run `uv run python practice.py`.
2. Try `RequestDC(id="REQ-002", ..., priority="purple")` — confirm the dataclass happily accepts it.
3. Compare with Exercise 2 — this is exactly what Pydantic will reject.

### Exercise 2 — Model the same request with Pydantic

```python
# practice.py
from pydantic import BaseModel, Field

class CustomerRequest(BaseModel):
    id: str = Field(pattern=r"^REQ-\d{3,}$")
    customer_name: str = Field(min_length=1)
    title: str = Field(min_length=3)
    description: str
    priority: str = Field(pattern=r"^(low|medium|high)$")
    status: str = Field(default="open", pattern=r"^(open|in_progress|closed)$")

ok = CustomerRequest(
    id="REQ-001",
    customer_name="Acme Corp",
    title="Login system upgrade",
    description="Users report slow login times",
    priority="high",
)
print(ok.model_dump())

# This will raise ValidationError:
# bad = CustomerRequest(id="REQ-002", customer_name="X", title="ab",
#                       description="", priority="purple")
```

**Step-by-step:**
1. `BaseModel.__init__` validates every field as it is assigned — bad input raises `pydantic.ValidationError` instead of silently producing a broken record.
2. `Field(pattern=...)` is a regular-expression constraint. `Field(min_length=...)` is for strings, lists, and dicts.
3. `model_dump()` returns a plain dict (similar to Week 01's dict-of-requests JSON shape).

### Exercise 3 — Pass invalid priority to both; compare behavior

```python
from dataclasses import dataclass
from pydantic import BaseModel, ValidationError

@dataclass
class RequestDC:
    id: str
    priority: str = "low"

class RequestPD(BaseModel):
    id: str
    priority: str = "low"

# dataclass accepts anything
bad_dc = RequestDC(id="REQ-001", priority="purple")
print("dataclass:", bad_dc.priority)

# pydantic rejects
try:
    RequestPD(id="REQ-001", priority="purple")
except ValidationError as e:
    print("pydantic blocked:", e.errors()[0]["msg"])
```

**Step-by-step:**
1. The dataclass produces a broken record silently. The Pydantic model raises a `ValidationError`.
2. This is the single biggest reason to use Pydantic for data that crosses boundaries (CLI input, file load, API response).

### Exercise 4 — Create `RequestStatus` and `Priority` enums

```python
# src/request_tracker/models.py
from enum import Enum

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class RequestStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"
```

**Step-by-step:**
1. Inheriting from `str` lets the enum values compare equal to plain strings: `Priority.HIGH == "high"` is `True`.
2. Use the enum in your Pydantic model: `priority: Priority`. Pydantic accepts `"high"` from input and produces `Priority.HIGH` internally.
3. Replace every literal `"open"` / `"high"` in your Week 1 code with the enum members.

### Exercise 5 — Write a validator that rejects blank titles

```python
# src/request_tracker/models.py
from pydantic import BaseModel, Field, field_validator

class CustomerRequest(BaseModel):
    id: str
    title: str = Field(min_length=3)
    customer_name: str
    description: str
    priority: Priority
    status: RequestStatus = RequestStatus.OPEN

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title cannot be blank or whitespace")
        return v.strip()

CustomerRequest(id="REQ-001", title="   ", customer_name="X",
                description="y", priority=Priority.LOW)
# ValueError: title cannot be blank or whitespace
```

**Step-by-step:**
1. `Field(min_length=3)` rejects too-short titles. `@field_validator` is for business-shaped rules that length alone can't express.
2. Returning the stripped value means the rest of the app never has to worry about leading/trailing whitespace.
3. Always use `@classmethod` on Pydantic v2 validators.

### Exercise 6 — Export two request instances to CSV

```python
# src/request_tracker/csv_io.py
import csv
from pathlib import Path
from .models import CustomerRequest, Priority, RequestStatus

def export_csv(requests: list[CustomerRequest], path: Path) -> None:
    fieldnames = ["id", "customer_name", "title", "description",
                  "priority", "status", "created_at", "updated_at"]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in requests:
            writer.writerow({
                "id": r.id,
                "customer_name": r.customer_name,
                "title": r.title,
                "description": r.description,
                "priority": r.priority.value,
                "status": r.status.value,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            })

sample = [
    CustomerRequest(id="REQ-001", title="Login upgrade",
                    customer_name="Acme", description="slow",
                    priority=Priority.HIGH),
    CustomerRequest(id="REQ-002", title="Export bug",
                    customer_name="Beta", description="missing fields",
                    priority=Priority.LOW),
]
export_csv(sample, Path("data/requests.csv"))
```

**Step-by-step:**
1. `csv.DictWriter` is the right tool for exporting a list of dict-shaped records.
2. `.value` on an enum gives you the string the file should store.
3. The `newline=""` argument is required for cross-platform CSV correctness on Windows.

### Exercise 7 — Run Ruff against deliberately poorly formatted code

```python
# bad_style.py
def   add(a,b):
    return a+b
class thing:
    def __init__(self,x): self.x=x
```

```bash
uv run ruff check bad_style.py
uv run ruff format bad_style.py
```

**Step-by-step:**
1. `ruff check` reports unused imports, undefined names, and style violations.
2. `ruff format` rewrites the file in place using Black-compatible rules.
3. Configure Ruff in `pyproject.toml` under `[tool.ruff]` (later, when you wire up Step 12).

### Exercise 8 — Add a type error and confirm mypy finds it

```python
# bad_types.py
def add(a: int, b: int) -> int:
    return a + b

result: str = add(1, 2)   # mypy should flag: expected str, got int
```

```bash
uv run mypy bad_types.py
# success: found 1 error in 1 file (basic)
```

**Step-by-step:**
1. The runtime will not complain — Python is dynamically typed.
2. `mypy` reads the annotations and reports the mismatch.
3. mypy is most valuable on service and repository code, not on scripts that do `input()`.

---

### Step 1 — Copy Week 1 into a new folder

```bash
cp -r ../week-01-request-tracker/tracker week-02-layered-tracker
cd week-02-layered-tracker
uv init --bare
uv add pydantic
uv add --dev ruff mypy pytest
```

**Why:** Starting from a working baseline lets you refactor with confidence. Each step will keep the same behavior, just better organized.

### Step 2 — Introduce enums without changing behavior

Replace the literal strings `"open"`, `"in_progress"`, `"closed"`, `"low"`, `"medium"`, `"high"` with the enum members from Exercise 4. Because the enums inherit from `str`, equality with old string literals still works — no call site has to change yet.

```python
# before
"status": "open"

# after
"status": RequestStatus.OPEN.value
```

**Why:** This is a no-behavior-change step. It exists so the diff in Step 3 is purely about validation, not about renaming.

### Step 3 — Replace dictionaries with `CustomerRequest`

```python
# src/request_tracker/models.py
from datetime import datetime, UTC
from pydantic import BaseModel, Field, field_validator
from enum import Enum

class Priority(str, Enum):
    LOW, MEDIUM, HIGH = "low", "medium", "high"

class RequestStatus(str, Enum):
    OPEN, IN_PROGRESS, CLOSED = "open", "in_progress", "closed"

class CustomerRequest(BaseModel):
    id: str = Field(pattern=r"^REQ-\d{3,}$")
    customer_name: str = Field(min_length=1)
    title: str = Field(min_length=3)
    description: str
    priority: Priority
    status: RequestStatus = RequestStatus.OPEN
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title cannot be blank")
        return v.strip()
```

**Why:** From now on, no dict with `"priority": "purple"` can ever enter the system. Validation is enforced at the boundary, not in scattered `if` checks.

### Step 4 — Create `JsonRequestRepository`

```python
# src/request_tracker/repositories.py
import json
from pathlib import Path
from .models import CustomerRequest

DATA_FILE = Path("data/requests.json")

class JsonRequestRepository:
    def __init__(self, path: Path = DATA_FILE) -> None:
        self.path = path

    def load(self) -> list[CustomerRequest]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text())
        except json.JSONDecodeError as e:
            raise RuntimeError(f"{self.path} is not valid JSON: {e}") from e
        return [CustomerRequest.model_validate(item) for item in raw]

    def save(self, requests: list[CustomerRequest]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [r.model_dump(mode="json") for r in requests]
        self.path.write_text(json.dumps(payload, indent=2))

    def next_id(self, requests: list[CustomerRequest]) -> str:
        nums = [int(r.id.split("-")[1]) for r in requests if r.id.startswith("REQ-")]
        return f"REQ-{(max(nums) if nums else 0) + 1:03d}"
```

**Why:** This replaces Week 01's free-standing `save_requests` and `load_requests` functions. The repository owns *how* data is stored; the service owns *what* to do with it. `model_dump(mode="json")` ensures the stored JSON has string enum values, not enum objects.

### Step 5 — Move status-transition rules to `RequestService`

```python
# src/request_tracker/exceptions.py
class RequestNotFound(LookupError): ...
class IllegalStatusTransition(ValueError): ...
class ResolutionNoteRequired(ValueError): ...

# src/request_tracker/services.py
from datetime import datetime, UTC
from .exceptions import (IllegalStatusTransition,
                         RequestNotFound,
                         ResolutionNoteRequired)
from .models import CustomerRequest, RequestStatus
from .repositories import JsonRequestRepository

ALLOWED_TRANSITIONS = {
    RequestStatus.OPEN: {RequestStatus.IN_PROGRESS, RequestStatus.CLOSED},
    RequestStatus.IN_PROGRESS: {RequestStatus.CLOSED, RequestStatus.OPEN},
    RequestStatus.CLOSED: set(),  # terminal
}

class RequestService:
    def __init__(self, repo: JsonRequestRepository) -> None:
        self.repo = repo
        self.requests: list[CustomerRequest] = repo.load()

    def add(self, **fields) -> CustomerRequest:
        fields["id"] = self.repo.next_id(self.requests)
        request = CustomerRequest(**fields)
        self.requests.append(request)
        self.repo.save(self.requests)
        return request

    def change_status(self, request_id: str, new: RequestStatus,
                      resolution_note: str | None = None) -> CustomerRequest:
        target = self._find(request_id)
        if new == RequestStatus.CLOSED and not (resolution_note or "").strip():
            raise ResolutionNoteRequired(
                "closing a request requires a non-empty resolution note"
            )
        if new not in ALLOWED_TRANSITIONS[target.status]:
            raise IllegalStatusTransition(
                f"cannot move {request_id} from {target.status.value} to {new.value}"
            )
        target.status = new
        target.updated_at = datetime.now(UTC).isoformat()
        self.repo.save(self.requests)
        return target

    def _find(self, request_id: str) -> CustomerRequest:
        for r in self.requests:
            if r.id == request_id:
                return r
        raise RequestNotFound(f"no request with id {request_id}")
```

**Why:** Week 01's `close_request` mixed business rules and persistence. Now the service raises typed exceptions on rule violations, and the CLI can decide how to print them. The repository has no idea what "closing" means.

### Step 6 — Keep `input()` and `print()` only in `cli.py`

```python
# src/request_tracker/cli.py
from .exceptions import (IllegalStatusTransition, RequestNotFound,
                         ResolutionNoteRequired)
from .models import Priority, RequestStatus
from .repositories import JsonRequestRepository
from .services import RequestService

MENU = """
1. Add request
2. List requests
3. View one request
4. Change status
5. Close request
6. Exit
"""

def main() -> None:
    service = RequestService(JsonRequestRepository())
    while True:
        print(MENU)
        choice = input("> ").strip()
        try:
            if choice == "1": _add(service)
            elif choice == "2": _list(service)
            elif choice == "3": _view(service)
            elif choice == "4": _change(service)
            elif choice == "5": _close(service)
            elif choice == "6": return
            else: print("Pick 1-6.")
        except (RequestNotFound, IllegalStatusTransition,
                ResolutionNoteRequired) as e:
            print(f"Error: {e}")

def _add(service: RequestService) -> None:
    new = service.add(
        customer_name=input("Customer name: "),
        title=input("Title: "),
        description=input("Description: "),
        priority=Priority(input("Priority (low/medium/high): ").lower()),
    )
    print(f"Created {new.id}")

def _list(service: RequestService) -> None:
    for r in service.requests:
        print(f"{r.id}  {r.priority.value:<6}  {r.status.value:<11}  {r.title}")

def _view(service: RequestService) -> None:
    rid = input("Request id: ").upper()
    r = next(x for x in service.requests if x.id == rid)
    print(r.model_dump_json(indent=2))

def _change(service: RequestService) -> None:
    rid = input("Request id: ").upper()
    new = RequestStatus(input("New status (open/in_progress/closed): "))
    service.change_status(rid, new)

def _close(service: RequestService) -> None:
    rid = input("Request id: ").upper()
    note = input("Resolution note: ")
    service.change_status(rid, RequestStatus.CLOSED, resolution_note=note)
    print(f"{rid} closed.")
```

**Why:** Every `input()` and `print()` lives here, and nowhere else. The CLI becomes a thin shell that translates user keystrokes into service calls and service errors into user-readable text.

### Step 7 — Add rule: closed requests cannot move back to in-progress

Already enforced in Step 5 by `ALLOWED_TRANSITIONS[RequestStatus.CLOSED] = set()`. Confirm it works:

```python
service.change_status("REQ-001", RequestStatus.IN_PROGRESS)
# IllegalStatusTransition: cannot move REQ-001 from closed to in_progress
```

### Step 8 — Add rule: closing requires a resolution note

Also in Step 5. The `ResolutionNoteRequired` exception is raised before the transition check, so it fires even for legal transitions. Confirm it works:

```python
service.change_status("REQ-001", RequestStatus.CLOSED, resolution_note="")
# ResolutionNoteRequired: closing a request requires a non-empty resolution note
```

### Step 9 — Add CSV export with `csv.DictWriter`

```python
# src/request_tracker/csv_io.py
import csv
from pathlib import Path
from .models import CustomerRequest

def export_csv(requests: list[CustomerRequest], path: Path) -> None:
    fieldnames = list(CustomerRequest.model_fields.keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in requests:
            row = r.model_dump(mode="json")
            writer.writerow(row)
```

**Why:** `model_fields` reads the model's field list — adding a new field to `CustomerRequest` automatically extends the CSV header.

### Step 10 — Add CSV import with row-level validation errors

```python
# src/request_tracker/csv_io.py
import csv
from pathlib import Path
from pydantic import ValidationError
from .models import CustomerRequest

def import_csv(path: Path) -> tuple[list[CustomerRequest], list[tuple[int, str]]]:
    """Return (valid_records, errors) where errors is (row_number, message)."""
    valid: list[CustomerRequest] = []
    errors: list[tuple[int, str]] = []
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # header is line 1
            try:
                valid.append(CustomerRequest.model_validate(row))
            except ValidationError as e:
                errors.append((i, e.errors()[0]["msg"]))
    return valid, errors
```

**Why:** Returning `(valid, errors)` lets the CLI report the exact row and reason for each rejection instead of failing the whole import.

### Step 11 — Report valid and rejected row counts

```python
# in cli.py
def _import(service: RequestService) -> None:
    from pathlib import Path
    from .csv_io import import_csv
    valid, errors = import_csv(Path(input("CSV path: ")))
    service.requests.extend(valid)
    service.repo.save(service.requests)
    print(f"Imported {len(valid)} valid row(s).")
    for line, msg in errors:
        print(f"  line {line}: {msg}")
```

**Why:** The acceptance criterion is "10 rows in, 2 invalid, 8 imported, 2 errors reported." This is exactly what `_import` does.

### Step 12 — Configure Ruff and mypy in `pyproject.toml`

```toml
# pyproject.toml
[project]
name = "request-tracker"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = ["pydantic>=2.6"]

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.mypy]
python_version = "3.13"
strict = true
files = ["src"]

[tool.pytest.ini_options]
addopts = "-q"
testpaths = ["tests"]
```

```bash
uv run ruff check .
uv run ruff format .
uv run mypy src
```

**Why:** `strict = true` forces every annotation to be checked; `files = ["src"]` keeps mypy from complaining about your throwaway `practice.py`. The CI in Week 18 will run all three of these commands.

---

## Acceptance Criteria

- [ ] Invalid models cannot be created
- [ ] CLI imports no modules from `repositories.py` or `models.py` directly (only `services.py`)
- [ ] Repository contains no `input()` or `print()`
- [ ] Service contains no JSON or CSV code
- [ ] Importing 10 rows with 2 invalid rows imports 8 and reports 2 errors
- [ ] `ruff check .` passes
- [ ] `mypy src/` passes on application code
- [ ] Week 1 behavior still works
- [ ] At least 5 meaningful commits

## AI-Off Check

**Without looking at your code**, draw the dependency direction among CLI, service, repository, and model. Then add a new business rule (e.g., "high-priority requests must have a description > 20 characters") without placing any logic in the CLI.

## Reflection Questions

1. Why use Pydantic rather than plain dictionaries?
2. Which logic belongs in the model vs. the service?
3. What would you change if storage moved from JSON to a database?
4. Did any abstraction make the code harder without providing value?

---

**Tip:** Commit after each step. Your git history should tell the story of the refactor.

**Next:** Move to Week 3 when all acceptance criteria pass.
