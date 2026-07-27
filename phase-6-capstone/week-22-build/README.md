# Week 22: Build the Capstone

## Outcome

Deliver a **working end-to-end capstone product** that solves the scenario from Week 21. The system must run locally with one command, exercise the LLM feature with a real (or stubbed) provider, persist data, expose an HTTP API, and have at least one automated test per functional requirement from `scenario/03-requirements.md`. By the end of the week you have a GitHub repo that someone else can clone, run, and use in under five minutes.

This is the longest week. You are not done when you have written code — you are done when the system runs end to end on a fresh machine.

## Setup Checklist

- [ ] `phase-6-capstone/week-21-discovery/scenario/` complete and frozen
- [ ] A fresh clone of your capstone repo (or a new folder under `phase-6-capstone/week-22-build/`)
- [ ] Local Postgres (Docker) from Week 6
- [ ] `uv` and Python 3.13 from Week 1
- [ ] An API key for the LLM provider you chose, or Ollama running locally (Week 9)
- [ ] A scratch `OPENAI_API_KEY` (or equivalent) — never commit it

### Setup Walkthrough

```bash
cd /path/to/your/capstone-repo

# 1. Read your Week 21 scenario one more time before writing code
cat ../week-21-discovery/scenario/03-requirements.md

# 2. Initialize a fresh project (or copy your Week 8 repo as a starting point)
uv init --package my-capstone
cd my-capstone
uv add fastapi "uvicorn[standard]" sqlmodel psycopg[binary] alembic
uv add "pydantic-ai"          # or the LLM SDK you chose in Phase 3
uv add --dev pytest pytest-asyncio httpx ruff mypy

# 3. Add Docker and a docker-compose
touch Dockerfile
touch docker-compose.yml

# 4. Add the .env.example from Week 20
cat > .env.example <<'EOF'
DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/app
OPENAI_API_KEY=sk-replace-me
APP_ENV=development
LOG_LEVEL=INFO
EOF
grep -qxF ".env" .gitignore || echo ".env" >> .gitignore

# 5. Verify the empty app boots
uv run uvicorn my_capstone.main:app --reload
```

## Learning Path (60–90 minutes)

**Best approach:** Read your own requirements doc, not a new tutorial. Every tutorial this week is a distraction unless it is the one your scenario needs.

### Learn in this order

1. **Re-read `scenario/03-requirements.md`** — every requirement is a deliverable
2. **Application factory pattern** — `create_app()` returns a configured FastAPI app, easy to test
3. **Service layer** — routes call services, services use repositories, repositories talk to the database
4. **LLM adapter pattern** — one interface, multiple providers, swap in tests
5. **Background tasks** — long LLM calls should not block the request
6. **One-command setup** — `make run`, `make test`, `make migrate`
7. **The "smoke test" pattern** — one end-to-end test that exercises the happy path

### Free Resources

- [FastAPI: Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/) — the file structure for a non-trivial app
- [SQLModel: Relationships](https://sqlmodel.tiangolo.com/tutorial/relationship-attributes/) — the ORM you'll likely use
- [Pydantic AI](https://ai.pydantic.dev/) — the Pythonic LLM SDK
- [Anthropic: Tool use](https://docs.anthropic.com/en/docs/tool-use) — if you need an agent
- [PostgreSQL: Tutorial](https://www.postgresql.org/docs/current/tutorial.html) — when in doubt, the docs
- [12-Factor App](https://12factor.net/) — the rules you have been following all along

**Tip:** This week is not about learning new libraries. It is about **applying** the libraries you already know to a scenario you own. The hardest part is saying "no, that is out of scope" to your own ideas.

## Micro-Exercises (45–60 minutes)

Complete these in order. Each is a small, self-contained piece of the system.

### Exercise 1 — Define the data model

```python
# app/models.py
from datetime import datetime
from sqlmodel import Field, SQLModel
from enum import Enum

class ReportStatus(str, Enum):
    draft = "draft"
    review = "review"
    approved = "approved"
    distributed = "distributed"

class WeeklyReport(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    week_of: datetime = Field(index=True, unique=True)
    status: ReportStatus = Field(default=ReportStatus.draft)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    data_json: str        # raw ingest snapshot
    deck_json: str        # generated cells, one per slide section

class AuditEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    actor: str
    action: str
    target: str
    ts: datetime = Field(default_factory=datetime.utcnow)
    details: str = "{}"
```

**Step-by-step:**
1. List every noun in your requirements doc — every noun is a candidate model.
2. List every "audit" action in the requirements doc — every one becomes an `AuditEvent`.
3. Use `Field(default_factory=datetime.utcnow)` for any timestamp so you do not forget to set it.
4. Keep enums in the same file as the model that uses them; do not pre-abstract.

### Exercise 2 — Define the LLM adapter interface

```python
# app/llm/base.py
from typing import Protocol
from pydantic import BaseModel

class DeckCells(BaseModel):
    summary: str
    highlights: list[str]
    risks: list[str]

class LLMClient(Protocol):
    def draft_deck_cells(self, report_data: dict) -> DeckCells: ...
    def summarize_cell_change(self, before: str, after: str) -> str: ...
```

```python
# app/llm/openai_impl.py
import os
from openai import OpenAI
from .base import LLMClient, DeckCells

class OpenAIClient:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def draft_deck_cells(self, report_data: dict) -> DeckCells:
        resp = self.client.responses.parse(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": "You draft executive summaries from weekly KPIs."},
                {"role": "user", "content": f"Here is this week's data: {report_data}"},
            ],
            text_format=DeckCells,
        )
        return resp.output_parsed
```

```python
# app/llm/fake.py
from .base import LLMClient, DeckCells

class FakeClient:
    """Deterministic client used in tests and local dev without a key."""
    def draft_deck_cells(self, report_data: dict) -> DeckCells:
        return DeckCells(
            summary="[stub] Auto-generated summary.",
            highlights=["[stub] +12% net adds", "[stub] -3% churn"],
            risks=["[stub] One segment trending down"],
        )
    def summarize_cell_change(self, before: str, after: str) -> str:
        return f"[stub] {before!r} -> {after!r}"
```

**Step-by-step:**
1. Define the interface in `app/llm/base.py` so callers depend on it, not on OpenAI.
2. Provide at least two implementations: a real one and a fake. Tests use the fake.
3. Keep the real client's prompt and parsing logic in one method, so swapping providers is a one-file change.
4. The fake must be **deterministic** — same input, same output, every time.

### Exercise 3 — Define the service layer

```python
# app/services/reports.py
from datetime import datetime
from sqlmodel import Session, select
from app.models import WeeklyReport, ReportStatus
from app.llm.base import LLMClient

class ReportService:
    def __init__(self, session: Session, llm: LLMClient) -> None:
        self.session = session
        self.llm = llm

    def ingest(self, week_of: datetime, raw_data: dict) -> WeeklyReport:
        import json
        report = WeeklyReport(
            week_of=week_of,
            status=ReportStatus.draft,
            data_json=json.dumps(raw_data),
        )
        self.session.add(report)
        self.session.commit()
        self.session.refresh(report)
        return report

    def draft(self, report_id: int) -> WeeklyReport:
        import json
        report = self.session.get(WeeklyReport, report_id)
        if report is None:
            raise LookupError(f"Report {report_id} not found")
        if report.status not in (ReportStatus.draft, ReportStatus.review):
            raise ValueError(f"Cannot draft from status {report.status}")
        cells = self.llm.draft_deck_cells(json.loads(report.data_json))
        report.deck_json = cells.model_dump_json()
        report.status = ReportStatus.review
        self.session.add(report)
        self.session.commit()
        self.session.refresh(report)
        return report

    def approve(self, report_id: int, actor: str) -> WeeklyReport:
        report = self.session.get(WeeklyReport, report_id)
        if report is None:
            raise LookupError(f"Report {report_id} not found")
        if report.status != ReportStatus.review:
            raise ValueError(f"Cannot approve from status {report.status}")
        report.status = ReportStatus.approved
        self.session.add(report)
        self.session.commit()
        self.session.refresh(report)
        return report
```

**Step-by-step:**
1. Each service method does **one** thing the requirements doc names. If your method does two things, split it.
2. The service raises `ValueError` for invalid state transitions — the route layer translates that to 409.
3. The service does not know about HTTP. That is the point.
4. Every state change is committed immediately; there is no "save" method that batches.

### Exercise 4 — Define the HTTP routes

```python
# app/api/reports.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from datetime import datetime
from app.db import get_session
from app.services.reports import ReportService
from app.llm.fake import FakeClient
from app.llm.openai_impl import OpenAIClient
import os

router = APIRouter(prefix="/reports", tags=["reports"])

def get_service(session: Session = Depends(get_session)) -> ReportService:
    llm = OpenAIClient() if os.environ.get("APP_ENV") == "production" else FakeClient()
    return ReportService(session, llm)

@router.post("", status_code=201)
def create_report(week_of: datetime, data: dict,
                  svc: ReportService = Depends(get_service)):
    return svc.ingest(week_of, data)

@router.post("/{report_id}/draft")
def draft_report(report_id: int, svc: ReportService = Depends(get_service)):
    try:
        return svc.draft(report_id)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(409, str(e))

@router.post("/{report_id}/approve")
def approve_report(report_id: int, actor: str,
                   svc: ReportService = Depends(get_service)):
    try:
        return svc.approve(report_id, actor)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(409, str(e))
```

**Step-by-step:**
1. The route depends on a session (DB) and provides a service. The service depends on the LLM.
2. `FakeClient` vs `OpenAIClient` is chosen by environment — tests get the fake.
3. Errors from the service are translated to HTTP errors at the route layer. The service stays HTTP-free.
4. Every route is one screen long. If a route is longer, push logic into the service.

### Exercise 5 — Wire the app factory

```python
# app/main.py
from fastapi import FastAPI
from app.api import reports

def create_app() -> FastAPI:
    app = FastAPI(title="Acme Monday Report")
    app.include_router(reports.router)
    return app

app = create_app()
```

```python
# app/db.py
from sqlmodel import Session, create_engine

_engine = create_engine(
    "postgresql+psycopg://app:app@localhost:5432/app",
    echo=False,
)

def get_session() -> Session:
    with Session(_engine) as session:
        yield session
```

**Step-by-step:**
1. `create_app()` returns a configured app. Tests call `create_app()` to get a fresh instance.
2. The module-level `app = create_app()` is for `uvicorn app.main:app`. Tests don't need it.
3. `get_session` is a generator that yields and closes — FastAPI's dependency system handles the teardown.
4. Do **not** import `app` at the top of `db.py`; that creates a circular import.

### Exercise 6 — Write the smoke test

```python
# tests/test_smoke.py
from datetime import datetime
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from app.main import create_app
from app.db import get_session

def _test_engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine

def test_end_to_end_draft_and_approve(monkeypatch):
    engine = _test_engine()

    def _override():
        with Session(engine) as s:
            yield s

    app = create_app()
    app.dependency_overrides[get_session] = _override
    client = TestClient(app)

    r = client.post("/reports",
                    params={"week_of": "2026-04-13T00:00:00"},
                    json={"net_adds": 100, "churn": 5})
    assert r.status_code == 201
    rid = r.json()["id"]

    r = client.post(f"/reports/{rid}/draft")
    assert r.status_code == 200
    assert r.json()["status"] == "review"

    r = client.post(f"/reports/{rid}/approve", params={"actor": "dr-reyes"})
    assert r.status_code == 200
    assert r.json()["status"] == "approved"
```

**Step-by-step:**
1. SQLite in-memory is enough for the smoke test. The real Postgres is exercised in Week 23's integration tests.
2. The test overrides the DB dependency; it never touches the real database.
3. The LLM is the `FakeClient` from Exercise 2 — no API key needed.
4. One end-to-end test is more valuable than ten unit tests. Write it first, then add the unit tests around it.

### Exercise 7 — Add `make` targets for the common operations

```makefile
# Makefile
.PHONY: install run test lint migrate smoke

install:
	uv sync --frozen

run:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	uv run pytest -q

lint:
	uv run ruff check .
	uv run ruff format --check .

migrate:
	uv run alembic upgrade head

smoke:
	curl -s http://localhost:8000/health | jq .
```

**Step-by-step:**
1. The Makefile is a contract: any contributor can run `make install` and `make run` and have a working app.
2. Keep the targets small and obvious. No build pipelines, no "magic" steps.
3. If you need secrets to run a target, the target should fail loudly if they are missing.
4. The `smoke` target assumes the app is already running. Document that in the README.

### Exercise 8 — Add a Dockerfile and a docker-compose

*`Dockerfile` (from Week 17)*

```dockerfile
FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY app ./app
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

*`docker-compose.yml`*

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: app
    ports: ["5432:5432"]
    volumes: ["dbdata:/var/lib/postgresql/data"]

  app:
    build: .
    environment:
      DATABASE_URL: postgresql+psycopg://app:app@db:5432/app
      APP_ENV: development
    ports: ["8000:8000"]
    depends_on: [db]

volumes:
  dbdata:
```

**Step-by-step:**
1. The `app` service waits for `db` via `depends_on`; a stronger version adds a healthcheck.
2. The compose file is **not** production. It exists so a new contributor can run the system in one command.
3. Mount the source as a volume in dev so code edits are picked up without rebuilding.
4. The Dockerfile uses uv at build time — fast, deterministic, no `pip install` lottery.

### Exercise 9 — Write the README

*`README.md`*

```markdown
# Acme Monday Report

AI-assisted weekly report drafting for the Operations Excellence team at Acme.

## What it does
1. The team uploads 4 CSV exports on Monday morning.
2. The system ingests them, drafts a deck with the LLM, and flags
   anything that changed >10% week-over-week.
3. The reviewer (Dr. Reyes) edits, approves, and exports .pptx.
4. The VP receives the deck on Wednesday, one week fresher than before.

## Run it

```bash
git clone https://github.com/<you>/acme-monday-report
cd acme-monday-report
cp .env.example .env
# edit .env, set OPENAI_API_KEY
make install
docker compose up -d db
make migrate
make run
```

## Test it
```bash
make test        # unit + smoke
make smoke       # curl against a running app
```

## Architecture
See `docs/architecture.md` for a Mermaid diagram and rationale.
```

**Step-by-step:**
1. The README's first 20 lines answer: what is it, how do I run it, how do I test it.
2. Anything below the first 20 lines is "nice to know" — link to it, do not dump it inline.
3. A reviewer reading the README alone should be able to land the system in 5 minutes.
4. If a section is more than 5 lines, link to a separate doc.

### Exercise 10 — Add a CHANGELOG

```markdown
# Changelog

## 0.1.0 — 2026-04-20
### Added
- Initial working end-to-end build
- Ingest, draft, approve, export endpoints
- Fake LLM client for local dev
- Smoke test that runs the full flow
- Dockerfile and docker-compose for local Postgres

### Known limitations
- Real OpenAI client is wired but not yet tested against live data
- No PPTX export yet — `deck_json` is the source of truth
- No auth on the API (added in Week 23)
```

**Step-by-step:**
1. The changelog is the artifact reviewers read to know what is in the build.
2. The "known limitations" section is more useful than the "added" list — it tells the reviewer what is **not** done.
3. Update the changelog at the end of every week, not at the end of the project.
4. Use semantic versioning: `0.1.0` is the first end-to-end build, `0.2.0` adds a feature, `0.1.1` is a fix.

---

## Main Lab: Build the Capstone (4–5 hours)

### Scenario

You are 2 weeks into a 4-week engagement. The customer (the synthetic persona from Week 21) has approved your requirements doc and your scope statement. Your job this week is to deliver a working end-to-end system against the requirements. Next week (Week 23) you will harden it. This week you ship a working product, not a perfect one.

### Target File Layout

```
my-capstone/
  app/
    __init__.py
    main.py
    db.py
    models.py
    api/
      __init__.py
      reports.py
    services/
      __init__.py
      reports.py
    llm/
      __init__.py
      base.py
      openai_impl.py
      fake.py
  tests/
    test_smoke.py
    test_services.py
  Dockerfile
  docker-compose.yml
  Makefile
  pyproject.toml
  uv.lock
  README.md
  CHANGELOG.md
  docs/
    architecture.md
```

### Build Steps

**Commit after each step.** A typical week has 8–12 commits. Aim for at least one per step.

#### Step 1 — Initialize the project and the data model

*`feat: bootstrap capstone project`*

Run the Setup Walkthrough above. The first commit should include: `pyproject.toml`, `uv.lock`, `app/__init__.py`, `app/main.py` (the empty `create_app`), and `.gitignore`.

#### Step 2 — Implement the data model and migrations

*`feat: add data model and alembic migrations`*

Add the models from Exercise 1 and run `uv run alembic init migrations`. Create one initial migration that creates all tables.

```bash
uv run alembic init migrations
uv run alembic revision --autogenerate -m "initial"
uv run alembic upgrade head
```

**Step-by-step:**
1. Verify the migration runs cleanly against a fresh Postgres.
2. Run it twice — the second should be a no-op.
3. Commit the migration file, not the `migrations/versions/` cache.

#### Step 3 — Implement the LLM adapter with both a real and a fake client

*`feat: add LLM adapter with real and fake implementations`*

Copy the three files from Exercise 2. Confirm `from app.llm.fake import FakeClient` works without an `OPENAI_API_KEY` set.

#### Step 4 — Implement the service layer

*`feat: add report service`*

Copy the service from Exercise 3. Add at least one test per method, in `tests/test_services.py`:

```python
def test_draft_transitions_status_to_review():
    # arrange
    # act
    # assert
```

#### Step 5 — Wire the HTTP routes

*`feat: add HTTP routes`*

Copy the routes from Exercise 4. Confirm the OpenAPI docs at `/docs` render correctly.

#### Step 6 — Add the smoke test

*`test: add end-to-end smoke test`*

Copy the smoke test from Exercise 6. Run it. It must pass before you move on. This is the single most important commit of the week.

#### Step 7 — Add the Makefile and run scripts

*`chore: add makefile and convenience scripts`*

Copy the Makefile from Exercise 7. Verify `make install`, `make run`, `make test`, `make smoke` all work on a fresh shell.

#### Step 8 — Add Docker and docker-compose

*`feat: add docker and docker-compose`*

Copy the Dockerfile and compose from Exercise 8. Verify `docker compose up --build` brings the system up.

#### Step 9 — Write the README and CHANGELOG

*`docs: add readme and changelog`*

Copy the README and CHANGELOG from Exercises 9 and 10. The README's first 20 lines must be enough.

#### Step 10 — Demo the system end to end and record it

*`docs: record end-to-end demo`*

Run the following scenario from a clean clone and record the screen:

1. `git clone ... && cd ...`
2. `cp .env.example .env` (use a fake key — the system uses the fake LLM)
3. `make install`
4. `docker compose up -d db && make migrate`
5. `make run &`
6. `curl http://localhost:8000/health` → 200
7. Open `http://localhost:8000/docs` in a browser
8. Create a report, draft it, approve it — show the response bodies
9. `make test` → all green

This is the demo you will polish and re-record in Week 24.

### Required Manual Tests

- [ ] Fresh clone, no env, only `make install` and `make test` — passes
- [ ] Fresh clone, with env, `make run` and the full flow — works
- [ ] `docker compose up` brings the system up
- [ ] `make test` shows the smoke test passing
- [ ] `/docs` renders all routes with their request/response models
- [ ] No secrets in the repo (`git log -p | grep -i "api_key"` is empty)
- [ ] The README's "Run it" block works on a colleague's machine
- [ ] The CHANGELOG is up to date

### Acceptance Criteria

- [ ] `make test` passes on a fresh clone
- [ ] `make run` starts the app and the smoke flow works
- [ ] `docker compose up` works
- [ ] Every functional requirement from `scenario/03-requirements.md` has at least one test
- [ ] The LLM adapter has both a real and a fake implementation
- [ ] The smoke test exercises the full flow without an `OPENAI_API_KEY`
- [ ] No secrets in the repo (use `gitleaks` or `git log -p | grep` to verify)
- [ ] The README's first 20 lines are enough to land the system
- [ ] At least 5 meaningful commits
- [ ] The end-to-end demo recording exists and is under 10 minutes

## AI-Off Check (30 minutes)

**Without looking at your code**, write a one-paragraph description of your system that names:

1. The user (from the persona)
2. The action they perform
3. The system's response
4. The data the system touches

```text
Dr. Reyes (Senior Manager, Operations Excellence) uploads four weekly CSV
exports to the system. The system ingests them into the `weekly_reports`
table, calls the LLM to draft a deck, and stores the cells in `deck_json`.
Dr. Reyes then reviews and approves the draft through the API. The system
records an `AuditEvent` for every state change and produces a downloadable
.pptx on request.
```

If you cannot write this paragraph cold, the system is not yet internalised. The goal is to be able to describe the capstone in 60 seconds, without notes, in any room.

## Reflection Questions

After you finish, write answers to these in `REFLECTION.md`:

1. Which requirement from `03-requirements.md` took longer than you expected? Why?
2. Which "out of scope" item tempted you this week? How did you resist?
3. Where did the LLM's output surprise you? Was the surprise a feature or a bug?
4. If you had two more days, which item would have the biggest impact on the customer?
5. What did you learn this week that would change how you build the next system?

## Next Steps

Once you pass all acceptance criteria:

1. Save the demo recording as `docs/demo-week-22.mp4`
2. Write the reflection answers
3. Commit with message: `docs: week 22 complete`
4. Move to Week 23 (Production Hardening)

---

**Ready?** Start by re-reading `scenario/03-requirements.md` and writing a list of every requirement on a sticky note. Each sticky is a step. Good luck! 🎯
