# Week 6: SQL, PostgreSQL, and Migrations

## Outcome

Move the tracker from JSON files to a real relational database using **PostgreSQL**, **SQLAlchemy 2.x** (or SQLModel), and **Alembic** migrations.

By the end of this week you will be able to:

- Design tables with primary keys, foreign keys, and indexes
- Write SELECT/INSERT/UPDATE/DELETE that join across tables
- Map Python classes to tables with SQLAlchemy 2.x style
- Generate and apply Alembic migrations
- Replace the JSON repository with a `SqlRequestRepository`

## Setup Checklist

- [ ] Decide: use a real PostgreSQL instance OR use SQLite for development
- [ ] Install PostgreSQL locally (Docker is the easiest path)
- [ ] `uv add sqlalchemy alembic psycopg[binary]`
- [ ] `uv add --dev pytest-postgresql` (or just rely on SQLite for tests)
- [ ] Confirm `psql --version` (or `docker ps` for the container path)

### Setup Walkthrough

```bash
# Option A: PostgreSQL via Docker (recommended for parity with production)
docker run --name pg-tracker -e POSTGRES_PASSWORD=postgres \
    -e POSTGRES_DB=tracker -p 5432:5432 -d postgres:16

# Option B: local install
# macOS:  brew install postgresql@16 && brew services start postgresql@16
# Linux:  sudo apt install postgresql-16
```

Then in the project:

```bash
uv add sqlalchemy alembic "psycopg[binary]"
uv run python -c "import sqlalchemy; print(sqlalchemy.__version__)"
```

Add to `.env.example`:

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/tracker
```

## Learning Path (60–90 minutes)

**Best approach:** Write SQL by hand first, then map it to SQLAlchemy. ORM fluency comes from knowing what queries your ORM is generating.

### Learn in this order

1. **Tables, rows, columns, primary keys, foreign keys**
2. **Constraints** — NOT NULL, UNIQUE, CHECK
3. **Indexes** — when and why
4. **JOINs** — INNER, LEFT, RIGHT
5. **Aggregates** — COUNT, AVG, GROUP BY
6. **Transactions** — BEGIN, COMMIT, ROLLBACK
7. **SQLAlchemy 2.x** — `Mapped[...]` declarative style
8. **Sessions and the unit of work**
9. **Alembic** — autogenerate and manual migrations
10. **Repository pattern with SQLAlchemy**

### Free Resources

- [SQLBolt](https://sqlbolt.com/) — interactive SQL practice
- [PostgreSQL tutorial](https://www.postgresql.org/docs/current/tutorial.html)
- [SQLAlchemy 2.0 ORM tutorial](https://docs.sqlalchemy.org/en/20/orm/tutorial.html)
- [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [Use The Index, Luke](https://use-the-index-luke.com/) — indexing guide

## Micro-Exercises (45–60 minutes)

1. `CREATE TABLE` for `customers`, `requests`, `audit_events` with foreign keys
2. `INSERT` a row and `SELECT` it back
3. Write a JOIN that returns request + customer name
4. Add an index on `requests.status` and run `EXPLAIN`
5. Use a transaction to update two tables atomically
6. Define a SQLAlchemy model with `Mapped` and `mapped_column`
7. Run an Alembic autogenerate and review the diff
8. Write a pytest fixture that creates a fresh schema per test

## Main Lab: PostgreSQL-Backed Tracker (4–5 hours)

### Target Structure

```
week-06-sql-postgres/
├── pyproject.toml
├── README.md
├── alembic.ini
├── migrations/
│   ├── env.py
│   └── versions/
├── src/
│   └── request_tracker/
│       ├── db.py              # engine, session, Base
│       ├── orm.py             # SQLAlchemy models
│       ├── repositories_sql.py# SqlRequestRepository
│       └── api.py             # FastAPI app, adapted
├── tests/
│   ├── conftest.py            # engine-per-test fixture
│   ├── test_orm.py
│   └── test_repositories_sql.py
└── data/                      # gone for SQL
```

### Schema Sketch

```sql
CREATE TABLE customers (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    country     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE requests (
    id            TEXT PRIMARY KEY,                 -- e.g., REQ-001
    customer_id   INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    priority      TEXT NOT NULL CHECK (priority IN ('low','medium','high')),
    status        TEXT NOT NULL CHECK (status IN ('open','in_progress','closed')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_requests_status   ON requests(status);
CREATE INDEX idx_requests_priority ON requests(priority);

CREATE TABLE audit_events (
    id          BIGSERIAL PRIMARY KEY,
    request_id  TEXT NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL,         -- e.g., 'status_change'
    payload     JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Build Steps

1. Start a local PostgreSQL and create the `tracker` database
2. Define SQLAlchemy ORM models for `Customer`, `Request`, `AuditEvent`
3. Initialize Alembic and write the first migration
4. Apply the migration; verify tables in `psql`
5. Implement `SqlRequestRepository` with CRUD methods
6. Replace the JSON repository in `RequestService`
7. Add a `Customer` model and seed data
8. Use the `audit_events` table to record status changes
9. Add API tests against a real engine (SQLite in-memory is fine)
10. Update the API to expose `?customer_id=` filter

## Step-by-Step Walkthrough

### Exercise 1 — `CREATE TABLE` with foreign keys

Connect to your DB and run:

```sql
CREATE TABLE customers (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    country     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE requests (
    id          TEXT PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    priority    TEXT NOT NULL CHECK (priority IN ('low','medium','high')),
    status      TEXT NOT NULL CHECK (status IN ('open','in_progress','closed')) DEFAULT 'open',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Step-by-step:**
1. `SERIAL` is shorthand for `INT GENERATED ALWAYS AS IDENTITY`.
2. `CHECK` constraints keep bad data out at the database level — last line of defense after Pydantic.
3. `ON DELETE CASCADE` automatically removes a customer's requests when the customer is deleted.

### Exercise 2 — `INSERT` and `SELECT`

```sql
INSERT INTO customers (name, country) VALUES ('Acme Corp', 'US') RETURNING id;
-- assume id=1

INSERT INTO requests (id, customer_id, title, priority)
VALUES ('REQ-001', 1, 'Login upgrade', 'high');

SELECT r.id, c.name, r.title, r.priority
FROM requests r
JOIN customers c ON c.id = r.customer_id;
```

**Step-by-step:**
1. `RETURNING` is the cheapest way to grab the new ID without a second `SELECT`.
2. Always alias the joined tables — once you have three or four, `WHERE` clauses become unreadable.

### Exercise 3 — JOIN across tables

```sql
SELECT r.id, r.title, c.name AS customer, c.country
FROM requests r
LEFT JOIN customers c ON c.id = r.customer_id
WHERE r.status = 'open'
ORDER BY r.created_at DESC
LIMIT 50;
```

**Why:** This is the most common shape in the tracker: "give me the open requests, with the customer name attached." Practice until it reads as English.

### Exercise 4 — Add an index and `EXPLAIN`

```sql
CREATE INDEX idx_requests_status ON requests(status);

EXPLAIN ANALYZE
SELECT * FROM requests WHERE status = 'open';
```

**Step-by-step:**
1. Before the index, expect a `Seq Scan` (table scan). After, expect an `Index Scan` (or `Bitmap Index Scan`).
2. Don't add indexes speculatively. Add them when a slow query proves a column is read often.
3. `EXPLAIN ANALYZE` actually runs the query — never run it on `UPDATE`/`DELETE` in production.

### Exercise 5 — Use a transaction to update two tables atomically

```sql
BEGIN;
UPDATE requests SET status = 'closed', updated_at = now()
WHERE id = 'REQ-001';

INSERT INTO audit_events (request_id, kind, payload)
VALUES ('REQ-001', 'status_change',
        '{"from":"open","to":"closed"}'::jsonb);
COMMIT;
```

**Why:** If the second statement fails, the first is rolled back. The status change and its audit log are inseparable.

### Exercise 6 — Define a SQLAlchemy 2.x model

```python
# src/request_tracker/orm.py
from datetime import datetime, UTC
from sqlalchemy import (String, Text, ForeignKey, DateTime, Integer,
                        CheckConstraint, Index)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

class Base(DeclarativeBase):
    pass

class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    country: Mapped[str | None] = mapped_column(String(2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC),
    )
    requests: Mapped[list["Request"]] = relationship(back_populates="customer")

class Request(Base):
    __tablename__ = "requests"
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(15), default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC),
    )
    customer: Mapped["Customer"] = relationship(back_populates="requests")

    __table_args__ = (
        CheckConstraint("priority IN ('low','medium','high')", name="ck_priority"),
        CheckConstraint("status IN ('open','in_progress','closed')",   name="ck_status"),
        Index("idx_requests_status",   "status"),
        Index("idx_requests_priority", "priority"),
    )

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[str] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE"),
    )
    kind: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC),
    )
```

**Step-by-step:**
1. `Mapped[T]` is the SQLAlchemy 2.x hint for the column type. Use `Mapped[T | None]` for nullable.
2. `__table_args__` lets you attach `CHECK` constraints and `Index` definitions on the same model.
3. The `relationship` lines are how ORM queries can navigate from `request.customer.name` without a manual JOIN.

### Exercise 7 — Run Alembic autogenerate and review the diff

```bash
uv run alembic init -t async migrations        # or omit -t for sync
```

Edit `migrations/env.py` so it points at your models:

```python
from request_tracker.orm import Base
target_metadata = Base.metadata
```

```bash
uv run alembic revision --autogenerate -m "initial schema"
uv run alembic upgrade head
```

**Step-by-step:**
1. `alembic revision --autogenerate` reads `Base.metadata` and compares it to the live DB.
2. **Always read the generated migration.** Autogenerate misses column renames, table renames, and CHECK changes.
3. Commit the migration file to git — it *is* the schema.

### Exercise 8 — pytest fixture that creates a fresh schema per test

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from request_tracker.orm import Base

@pytest.fixture
def engine():
    eng = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()

@pytest.fixture
def session(engine):
    Session = sessionmaker(bind=engine, autoflush=False)
    with Session() as s:
        yield s
```

**Why:** `:memory:` SQLite gives you a fresh, zero-setup database for every test. For PostgreSQL-only features (JSONB, partial indexes), use `pytest-postgresql` or a Testcontainers setup.

---

### Step 1 — Start a local PostgreSQL and create the `tracker` database

```bash
docker exec -it pg-tracker psql -U postgres -c "CREATE DATABASE tracker;"
```

### Step 2 — Define SQLAlchemy ORM models

Already in Exercise 6. Place this in `src/request_tracker/orm.py`.

### Step 3 — Initialize Alembic and write the first migration

```bash
uv run alembic init -t async migrations
```

Edit `migrations/env.py`:

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from request_tracker.orm import Base
from request_tracker.config import load_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", load_settings().database_url)
target_metadata = Base.metadata
```

```bash
uv run alembic revision --autogenerate -m "initial schema"
```

### Step 4 — Apply the migration; verify tables in `psql`

```bash
uv run alembic upgrade head
docker exec -it pg-tracker psql -U postgres -d tracker -c "\dt"
```

Expected: `customers`, `requests`, `audit_events`, plus `alembic_version`.

### Step 5 — Implement `SqlRequestRepository`

```python
# src/request_tracker/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .config import load_settings

def make_engine():
    return create_engine(load_settings().database_url, future=True,
                         pool_pre_ping=True)

SessionLocal = sessionmaker(bind=make_engine(), autoflush=False)

# src/request_tracker/repositories_sql.py
from sqlalchemy import select
from sqlalchemy.orm import Session
from .orm import Request, Customer, AuditEvent
from .models import CustomerRequest, Priority, RequestStatus
from .exceptions import RequestNotFound, DuplicateId

class SqlRequestRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def load(self) -> list[CustomerRequest]:
        rows = self.session.execute(select(Request)).scalars().all()
        return [self._to_domain(r) for r in rows]

    def save(self, requests: list[CustomerRequest]) -> None:
        for r in requests:
            self._upsert(r)
        self.session.commit()

    def find(self, request_id: str) -> CustomerRequest:
        row = self.session.get(Request, request_id)
        if row is None:
            raise RequestNotFound(f"no request with id {request_id}")
        return self._to_domain(row)

    def next_id(self) -> str:
        last = self.session.execute(
            select(Request.id).order_by(Request.id.desc()).limit(1)
        ).scalar_one_or_none()
        n = int(last.split("-")[1]) if last else 0
        return f"REQ-{n + 1:03d}"

    def add_audit(self, request_id: str, kind: str, payload: dict) -> None:
        self.session.add(AuditEvent(request_id=request_id, kind=kind, payload=payload))
        self.session.commit()

    def _upsert(self, r: CustomerRequest) -> None:
        if self.session.get(Request, r.id) is not None:
            raise DuplicateId(f"{r.id} already exists")
        row = Request(
            id=r.id, customer_id=self._customer_id(r.customer_name),
            title=r.title, description=r.description,
            priority=r.priority.value, status=r.status.value,
            created_at=r.created_at, updated_at=r.updated_at,
        )
        self.session.add(row)

    def _customer_id(self, name: str) -> int:
        c = self.session.execute(
            select(Customer).where(Customer.name == name)
        ).scalar_one_or_none()
        if c is None:
            c = Customer(name=name)
            self.session.add(c)
            self.session.flush()
        return c.id

    def _to_domain(self, row: Request) -> CustomerRequest:
        return CustomerRequest(
            id=row.id, customer_name=row.customer.name, title=row.title,
            description=row.description,
            priority=Priority(row.priority), status=RequestStatus(row.status),
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat(),
        )
```

**Why:** `session.get(...)` is the right way to look up by primary key in 2.x — it bypasses the unit of work. `select(Request).order_by(...)` is the new way to express queries (no more `Query` object).

### Step 6 — Replace the JSON repository in `RequestService`

```python
# src/request_tracker/services.py
from .repositories_sql import SqlRequestRepository
from .db import SessionLocal

class RequestService:
    def __init__(self, repo: SqlRequestRepository | None = None) -> None:
        self.repo = repo or SqlRequestRepository(SessionLocal())
        self.requests = self.repo.load()
```

`RequestService.add(...)` now calls `self.repo.save([...])`; status changes call `self.repo.add_audit(...)` in the same transaction (or close to it).

### Step 7 — Add a `Customer` model and seed data

```python
# src/request_tracker/seed.py
from sqlalchemy import select
from .db import SessionLocal
from .orm import Customer

SEED = [
    ("Acme Corp", "US"),
    ("Beta Ltd", "UK"),
    ("Gamma SA", "FR"),
]

def run() -> None:
    with SessionLocal() as s:
        for name, country in SEED:
            if s.execute(select(Customer).where(Customer.name == name)).scalar_one_or_none():
                continue
            s.add(Customer(name=name, country=country))
        s.commit()
```

```bash
uv run python -m request_tracker.seed
```

### Step 8 — Use `audit_events` to record status changes

```python
# in services.py, inside change_status:
old = target.status
target.status = new
self.repo.add_audit(target.id, "status_change",
                    {"from": old.value, "to": new.value,
                     "resolution_note": resolution_note})
```

**Why:** Audit trails are an FDE staple — customer audits and SOC 2 reviews will ask for them.

### Step 9 — Add API tests against a real engine

```python
# tests/test_repositories_sql.py
from request_tracker.repositories_sql import SqlRequestRepository
from request_tracker.models import CustomerRequest, Priority

def test_save_and_find_round_trip(session) -> None:
    repo = SqlRequestRepository(session)
    r = CustomerRequest(
        id="REQ-001", customer_name="Acme Corp",
        title="Login", description="slow",
        priority=Priority.HIGH,
    )
    repo.save([r])
    found = repo.find("REQ-001")
    assert found.title == "Login"
    assert found.priority is Priority.HIGH
```

### Step 10 — Update the API to expose `?customer_id=`

```python
# src/request_tracker/api.py
from sqlalchemy import select
from .orm import Request

@router.get("/requests", response_model=list[RequestOut])
def list_requests(
    customer_id: int | None = None,
    status_filter: RequestStatus | None = None,
    limit: int = 50,
    offset: int = 0,
    svc: RequestService = Depends(get_service),
):
    stmt = select(Request).offset(offset).limit(limit)
    if customer_id is not None:
        stmt = stmt.where(Request.customer_id == customer_id)
    if status_filter is not None:
        stmt = stmt.where(Request.status == status_filter.value)
    rows = svc.repo.session.execute(stmt).scalars().all()
    return [RequestOut.model_validate(svc.repo._to_domain(r)) for r in rows]
```

**Why:** Filtering on the database (not in Python) is the only way this scales past a few hundred rows.

---

## Acceptance Criteria

- [ ] `alembic upgrade head` creates all tables and indexes
- [ ] `SqlRequestRepository` round-trips a request (insert, fetch, update, delete)
- [ ] All API endpoints work against PostgreSQL
- [ ] Status changes write to `audit_events`
- [ ] `psql` queries confirm the data is really in PostgreSQL (not in a file)
- [ ] Tests use an isolated engine per test (no shared mutable state)
- [ ] `EXPLAIN` shows index usage for filtered queries
- [ ] At least 5 meaningful commits

## AI-Off Check

**Without referencing docs**, write the SQL (then the SQLAlchemy) for "average hours to close a request, grouped by priority, only counting requests closed in the last 30 days." Then write a test that proves the query returns the right shape.

## Reflection Questions

1. What did the database give you that JSON files couldn't? When would JSON still be the right call?
2. Why define `__table_args__` constraints on the model instead of only in Alembic?
3. When does an `AuditEvent` belong in the same transaction as the change it records?
4. What's the most expensive query in the tracker right now? How would you know?

---

**Next:** Move to Week 7 when all acceptance criteria pass and you can demo a full PostgreSQL-backed round trip in under 5 minutes.
