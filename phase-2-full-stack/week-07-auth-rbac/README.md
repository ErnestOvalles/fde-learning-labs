# Week 7: Authentication, Authorization, and RBAC

## Outcome

Add **authentication** (who are you?) and **authorization** (what are you allowed to do?) to the tracker API using **JWT bearer tokens** and **role-based access control** with three roles: `admin`, `engineer`, `customer`.

By the end of this week you will be able to:

- Explain the difference between authentication and authorization
- Issue and verify a JWT signed with HS256
- Protect endpoints with FastAPI dependencies
- Enforce role-based access (RBAC) consistently across the API
- Test that one user cannot read or modify another customer's data
- Store and rotate secrets via environment variables (no secrets in code)

## Setup Checklist

- [ ] Carry forward Week 6's API + database
- [ ] `uv add "pyjwt[crypto]" passlib[bcrypt]`
- [ ] `uv add --dev pytest`
- [ ] Generate a development secret: `uv run python -c "import secrets; print(secrets.token_urlsafe(48))"`
- [ ] Add `JWT_SECRET` and `JWT_ALGORITHM` to `.env.example`

### Setup Walkthrough

```bash
cd week-06-sql-postgres
uv add "pyjwt[crypto]" "passlib[bcrypt]"
uv run python -c "import jwt; print(jwt.__version__)"
```

Update `.env.example`:

```bash
JWT_SECRET=change-me-to-a-long-random-string
JWT_ALGORITHM=HS256
JWT_EXPIRES_MIN=60
```

## Learning Path (60–90 minutes)

**Best approach:** Treat auth as a small, isolated subsystem. The rest of the app should know about *roles*, not about *tokens*.

### Learn in this order

1. **Authentication vs. authorization** — vocabulary and tradeoffs
2. **Hashing passwords** — `passlib` + bcrypt
3. **JWT structure** — header, payload, signature
4. **Issuing tokens** at `/auth/login`
5. **Verifying tokens** in a FastAPI dependency
6. **RBAC** — mapping roles to permissions
7. **Object-level authorization** — "this customer owns that request"
8. **Audit logging** — who did what, when

### Free Resources

- [JWT.io introduction](https://jwt.io/introduction)
- [FastAPI security docs](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP authentication cheatsheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [passlib documentation](https://passlib.readthedocs.io/en/stable/)

## Micro-Exercises (45–60 minutes)

1. Hash and verify a password with `passlib`
2. Sign a JWT with `pyjwt` and decode it
3. Build a `get_current_user` FastAPI dependency
4. Write a `require_role("admin")` dependency
5. Add a `/auth/login` route that returns a token
6. Protect an endpoint and confirm a missing token is 401
7. Confirm a wrong role returns 403
8. Confirm one customer cannot read another customer's request

## Main Lab: Authenticated Tracker API (4–5 hours)

### Roles and Permissions

| Role       | Can read all requests? | Can change status? | Can manage users? |
|------------|------------------------|--------------------|-------------------|
| `admin`    | yes                    | yes                | yes               |
| `engineer` | yes                    | yes                | no                |
| `customer` | only their own         | only `closed` on own | no              |

### Endpoints to Add

| Method | Path                  | Auth        | Notes                              |
|--------|-----------------------|-------------|------------------------------------|
| POST   | `/auth/register`      | admin       | Create a new user                  |
| POST   | `/auth/login`         | public      | Returns JWT                        |
| GET    | `/auth/me`            | any         | Current user from token            |
| GET    | `/admin/users`        | admin       | List users                         |
| GET    | `/requests`           | any         | Customer sees only their own       |
| GET    | `/requests/{id}`      | any         | 404 if not yours (and not staff)   |
| PATCH  | `/requests/{id}/status` | engineer/admin | 403 for customer            |
| POST   | `/requests/{id}/close` | owner or engineer | Owner can close own request |

### Build Steps

1. Add a `users` table and `roles` enum
2. Hash passwords on registration; never store plaintext
3. Issue JWTs at `/auth/login`
4. Verify JWTs in a `get_current_user` dependency
5. Add `require_role(*roles)` dependency factory
6. Enforce object-level access in the service layer
7. Update the API to use the new dependencies
8. Write tests for happy path, wrong role, and cross-tenant access
9. Add an audit log entry for every successful login
10. Document authentication in the README

## Step-by-Step Walkthrough

### Exercise 1 — Hash and verify a password

```python
# practice.py
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
hashed = pwd.hash("hunter2")
print("hash:", hashed[:20], "...")

print(pwd.verify("hunter2", hashed))     # True
print(pwd.verify("Hunter2", hashed))     # False (case-sensitive)
```

**Step-by-step:**
1. `bcrypt` is the workhorse for password hashing — slow on purpose, so brute force is expensive.
2. The `CryptContext` is configured once; reuse it everywhere. `verify` is constant-time.
3. Never log or echo the plaintext password.

### Exercise 2 — Sign and decode a JWT

```python
# practice.py
import jwt, time

SECRET = "dev-only-do-not-use-in-prod"
payload = {"sub": "user-42", "role": "engineer",
           "iat": int(time.time()), "exp": int(time.time()) + 300}
token = jwt.encode(payload, SECRET, algorithm="HS256")
print("token:", token[:30], "...")

decoded = jwt.decode(token, SECRET, algorithms=["HS256"])
print("decoded:", decoded)
```

**Step-by-step:**
1. The header (`alg`, `typ`) is automatic.
2. The signature is HMAC-SHA256 of `base64(header).base64(payload)` using `SECRET`.
3. Always pass `algorithms=[...]` to `jwt.decode`. Never trust the `alg` from the token.

### Exercise 3 — Build a `get_current_user` dependency

```python
# src/request_tracker/security.py
from datetime import datetime, UTC, timedelta
from typing import Annotated
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from .config import load_settings

bearer = HTTPBearer(auto_error=False)

class Principal(BaseModel):
    id: int
    username: str
    role: str  # 'admin' | 'engineer' | 'customer'

def issue_token(principal: Principal) -> str:
    s = load_settings()
    now = datetime.now(UTC)
    payload = {"sub": str(principal.id),
               "username": principal.username,
               "role": principal.role,
               "iat": int(now.timestamp()),
               "exp": int((now + timedelta(minutes=s.jwt_expires_min)).timestamp())}
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)

def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Principal:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    s = load_settings()
    try:
        payload = jwt.decode(creds.credentials, s.jwt_secret,
                             algorithms=[s.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"invalid token: {e}")
    return Principal(id=int(payload["sub"]),
                     username=payload["username"],
                     role=payload["role"])
```

**Step-by-step:**
1. `HTTPBearer` parses the `Authorization: Bearer <token>` header for you.
2. Decode errors become 401 — never 500. A bad token is the *client's* fault.
3. The returned `Principal` is what the rest of the app uses; the JWT never leaks past the dependency.

### Exercise 4 — Write a `require_role` dependency factory

```python
# src/request_tracker/security.py
def require_role(*allowed: str):
    def _checker(user: Annotated[Principal, Depends(get_current_user)]) -> Principal:
        if user.role not in allowed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"role {user.role!r} not in {list(allowed)}",
            )
        return user
    return _checker
```

Usage:

```python
@app.post("/admin/users", dependencies=[Depends(require_role("admin"))])
def create_user(...): ...
```

**Why:** A factory means the role list is *data*, not duplicated across decorators. Tests can ask for `require_role("engineer")` and not change the route.

### Exercise 5 — Add `/auth/login`

```python
# src/request_tracker/api.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from .db import SessionLocal
from .orm import User
from .security import issue_token, Principal
from .schemas import LoginIn

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter()

def get_db():
    s = SessionLocal()
    try: yield s
    finally: s.close()

@router.post("/auth/login")
def login(payload: LoginIn, db: Annotated[Session, Depends(get_db)]) -> dict:
    user = db.query(User).filter(User.username == payload.username).one_or_none()
    if user is None or not pwd.verify(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad credentials")
    token = issue_token(Principal(id=user.id, username=user.username, role=user.role))
    return {"access_token": token, "token_type": "bearer"}
```

**Step-by-step:**
1. Always return a generic error — "bad credentials" — to prevent username enumeration.
2. `issue_token` centralizes JWT creation. The login route does not know the secret.
3. Use `HTTPBearer` parsing in the dependency; the login route just returns the token.

### Exercise 6 — Protect an endpoint and confirm a missing token is 401

```python
@router.get("/auth/me")
def me(user: Annotated[Principal, Depends(get_current_user)]) -> Principal:
    return user
```

```python
# tests/test_auth.py
from fastapi.testclient import TestClient
from request_tracker.api import app

c = TestClient(app)

def test_me_without_token_is_401() -> None:
    r = c.get("/auth/me")
    assert r.status_code == 401

def test_me_with_bad_token_is_401() -> None:
    r = c.get("/auth/me", headers={"Authorization": "Bearer junk"})
    assert r.status_code == 401
```

### Exercise 7 — Confirm a wrong role returns 403

```python
# tests/test_auth.py
from request_tracker.security import issue_token, Principal

def test_customer_cannot_list_all_requests() -> None:
    token = issue_token(Principal(id=1, username="alice", role="customer"))
    r = c.get("/requests", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
```

**Why:** 401 (unauthenticated) and 403 (forbidden) are *different* — clients react to them differently. 401 prompts re-login; 403 prompts "you don't have access here."

### Exercise 8 — Confirm one customer cannot read another customer's request

```python
# tests/test_authz.py
def test_cross_customer_access_is_forbidden() -> None:
    alice_t = issue_token(Principal(id=1, username="alice", role="customer"))
    bob_t   = issue_token(Principal(id=2, username="bob",   role="customer"))

    # Alice creates a request (her customer_id = 1)
    create = c.post("/requests", json={
        "customer_name": "Acme", "title": "X",
        "description": "", "priority": "low",
    }, headers={"Authorization": f"Bearer {alice_t}"})
    rid = create.json()["id"]

    # Bob (customer_id = 2) tries to read it
    r = c.get(f"/requests/{rid}", headers={"Authorization": f"Bearer {bob_t}"})
    assert r.status_code == 404   # do not leak existence
```

**Why:** Return 404 (not 403) when the user lacks *object* access. The 403 leaks the fact that the request exists.

---

### Step 1 — Add a `users` table and `roles` enum

```python
# src/request_tracker/orm.py
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
    )

    __table_args__ = (
        CheckConstraint("role IN ('admin','engineer','customer')", name="ck_role"),
    )
```

```bash
uv run alembic revision --autogenerate -m "add users"
uv run alembic upgrade head
```

### Step 2 — Hash passwords on registration

```python
# src/request_tracker/api.py
@router.post("/auth/register", dependencies=[Depends(require_role("admin"))])
def register_user(payload: RegisterIn, db: Annotated[Session, Depends(get_db)]) -> dict:
    user = User(
        username=payload.username,
        password_hash=pwd.hash(payload.password),
        role=payload.role,
        customer_id=payload.customer_id,
    )
    db.add(user); db.commit()
    return {"id": user.id, "username": user.username, "role": user.role}
```

### Step 3 — Issue JWTs at `/auth/login`

Already in Exercise 5.

### Step 4 — Verify JWTs in a `get_current_user` dependency

Already in Exercise 3.

### Step 5 — Add `require_role` dependency factory

Already in Exercise 4.

### Step 6 — Enforce object-level access in the service layer

```python
# src/request_tracker/services.py
def list_requests_for(self, user: Principal) -> list[CustomerRequest]:
    if user.role in ("admin", "engineer"):
        return self.requests
    # customer: only requests for their own customer
    own = self.repo.customer_id_for_user(user.id)
    return [r for r in self.requests if r.customer_id == own]

def change_status(self, user: Principal, request_id: str, new: RequestStatus,
                  resolution_note: str | None = None) -> CustomerRequest:
    target = self._find(request_id)
    if user.role == "customer":
        if user.id != target.customer_id:
            raise RequestNotFound(f"no request with id {request_id}")
        if new != RequestStatus.CLOSED:
            raise IllegalStatusTransition("customers may only close their own requests")
    # ... rest of the existing logic ...
```

**Why:** Authorization in the *service* layer means CLI and API both inherit the same rules. Putting it only in the API leaves a back door.

### Step 7 — Update the API to use the new dependencies

```python
@router.get("/requests", response_model=list[RequestOut])
def list_requests(
    user: Annotated[Principal, Depends(get_current_user)],
    svc: RequestService = Depends(get_service),
):
    return [RequestOut.model_validate(r)
            for r in svc.list_requests_for(user)]
```

### Step 8 — Write tests for happy path, wrong role, and cross-tenant access

Exercises 6–8 are the seed. Add a parametrized table for "admin can X, engineer can X, customer can X."

### Step 9 — Add an audit log entry for every successful login

```python
# in login() after pwd.verify:
db.add(AuditEvent(kind="login", payload={"user_id": user.id}))
db.commit()
```

### Step 10 — Document authentication in the README

```markdown
## Authentication

1. POST /auth/login with `{username, password}` → `{access_token, token_type}`
2. Send `Authorization: Bearer <access_token>` on every protected route
3. Tokens expire after 60 minutes (configurable via `JWT_EXPIRES_MIN`)

## Roles

| Role     | Can read all? | Can change status? | Can manage users? |
|----------|---------------|--------------------|-------------------|
| admin    | yes           | yes                | yes               |
| engineer | yes           | yes                | no                |
| customer | own only      | close own only     | no                |
```

---

## Acceptance Criteria

- [ ] `/auth/login` returns a valid JWT for a real user
- [ ] Missing token → 401; bad token → 401; expired token → 401
- [ ] Wrong role → 403 on a protected endpoint
- [ ] Customer can read only their own requests
- [ ] Engineer/admin can read all requests
- [ ] Passwords are stored as bcrypt hashes — never plaintext
- [ ] Cross-tenant access returns 404 (not 403)
- [ ] Audit event recorded for each successful login
- [ ] At least 5 meaningful commits

## AI-Off Check

**Without looking at your code**, add a new role `viewer` that can read everything but cannot change anything. Decide: should it inherit from `engineer` minus mutations, or be its own dependency? Why?

## Reflection Questions

1. Why does this lab use JWT instead of server-side sessions?
2. What's the difference between authentication and authorization? Where does each happen?
3. Why return 404 instead of 403 for cross-tenant access?
4. How would you rotate the JWT signing secret without logging everyone out?

---

**Next:** Move to Week 8 when all acceptance criteria pass and your authz tests cover every role on every endpoint.
