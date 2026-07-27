# Week 20: Security and Secrets

## Outcome

Harden the **Customer Engagement Tracker** end to end: passwords are hashed with **argon2**, JWTs are verified with a shared key, every SQL call goes through parameterized statements (no string formatting), CORS is restricted to an allow-list, every response carries modern security headers, secrets live in environment variables only, and an **audit log** records every privileged action. By the end of the week a `bandit -r app` scan returns zero high-severity issues, the security headers are present on every response, and you can show that a SQL-injection attempt is rejected at the database layer.

This is the most concrete week of Phase 5. Security is not a "feel" — it is a checklist of behaviours you can demonstrate.

## Setup Checklist

- [ ] FastAPI app from Week 5/8/15 with at least one authenticated endpoint
- [ ] `uv add argon2-cffi python-jose[cryptography] passlib[argon2]`
- [ ] `uv add --dev bandit ruff ruff`
- [ ] A `.env.example` file that lists every variable the app reads
- [ ] `.env` listed in `.gitignore` (this week it actually matters)

### Setup Walkthrough

```bash
cd /path/to/your/tracker

# 1. Add the security libraries
uv add "passlib[argon2]"
uv add "python-jose[cryptography]"
uv add python-multipart        # needed for OAuth2PasswordRequestForm

# 2. Add the static analysis tool
uv add --dev bandit

# 3. Create a security module
mkdir -p app/security
touch app/security/__init__.py
touch app/security/passwords.py
touch app/security/tokens.py
touch app/security/middleware.py
touch app/security/audit.py

# 4. Confirm .env is git-ignored
grep -qxF ".env" .gitignore || echo ".env" >> .gitignore
grep -qxF "*.pem" .gitignore || echo "*.pem" >> .gitignore

# 5. Run bandit on the existing codebase — note any high-severity issues
uv run bandit -r app
```

## Learning Path (60–90 minutes)

**Best approach:** Security is the topic where "learn by reading" pays off most. The OWASP Top 10 is short, free, and applies to every API you will ever build.

### Learn in this order

1. **Threat modelling in 5 minutes** — assets, attackers, attack surface
2. **Password storage** — why plain SHA-256 is broken, why bcrypt was the default, why argon2id is now recommended
3. **JWT basics** — header, payload, signature, where the secret lives, common attacks
4. **SQL injection** — what it is, why parameterized queries prevent it, why ORMs help
5. **CORS** — preflight, allow-list vs. wildcard, why `*` + credentials is invalid
6. **Security headers** — HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, CSP
7. **Secrets management** — env vars, secret managers, what **never** to commit
8. **Audit logs** — what to record, where to send them, retention

### Free Resources

- [OWASP Top 10 (2021)](https://owasp.org/Top10/) — the canonical list, 30 minutes to read
- [OWASP API Security Top 10](https://owasp.org/API-Security/editions/2023/en/0x11-t10/) — REST-specific
- [Passlib documentation](https://passlib.readthedocs.io/) — `CryptContext` for password hashing
- [argon2-cffi](https://argon2-cffi.readthedocs.io/) — the underlying argon2 library
- [Auth0: JWT introduction](https://jwt.io/introduction) — visual JWT breakdown
- [FastAPI: Security](https://fastapi.tiangolo.com/tutorial/security/) — OAuth2 with Password + JWT
- [Mozilla: Security headers](https://infosec.mozilla.org/guidelines/web_security) — what to send and why
- [Bandit](https://bandit.readthedocs.io/) — Python static analyzer
- [12-Factor App: Config](https://12factor.net/config) — the original "env vars" essay

**Tip:** Read the OWASP Top 10 once. Do not memorize it — just remember that it exists, so when you face a new endpoint you can run the list against it.

## Micro-Exercises (45–60 minutes)

Create `practice_security.py` and complete these:

### Exercise 1 — Hash and verify a password with argon2

```python
# practice_security.py
from passlib.context import CryptContext

pwd = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(plain: str) -> str:
    return pwd.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd.verify(plain, hashed)

h = hash_password("correct horse battery staple")
print(h)                              # starts with $argon2id$
print(verify_password("correct horse battery staple", h))   # True
print(verify_password("wrong", h))     # False
```

**Step-by-step:**
1. `argon2id` is the recommended default since 2019 — it resists both GPU and side-channel attacks.
2. `pwd.verify` is **constant-time** so it does not leak how many characters matched.
3. Passlib can also re-hash on verify if you increase the cost; that is the upgrade path.

### Exercise 2 — Hash the same password twice and confirm the salt differs

```python
h1 = hash_password("hunter2")
h2 = hash_password("hunter2")
print(h1 == h2)        # False — different salt each call
print(h1.split("$")[-1])   # the salt and digest differ
```

**Step-by-step:**
1. Same plaintext produces different hashes. That is the salt doing its job.
2. Without a salt, an attacker who cracks one password cracks every user with the same password.
3. The cost is in the third field, e.g. `$argon2id$v=19$m=65536,t=3,p=4$...`. Larger `m` and `t` mean slower hashing.

### Exercise 3 — Create and decode a JWT

```python
from jose import jwt
from datetime import datetime, timedelta, timezone

SECRET = "dev-secret-do-not-use-in-prod"
ALG = "HS256"

def make_token(sub: str) -> str:
    payload = {
        "sub": sub,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    return jwt.encode(payload, SECRET, algorithm=ALG)

def read_token(token: str) -> dict:
    return jwt.decode(token, SECRET, algorithms=[ALG])

t = make_token("user-42")
print(t)
print(read_token(t)["sub"])   # user-42
```

**Step-by-step:**
1. `jwt.encode` returns a string; `jwt.decode` validates the signature and the expiry in one call.
2. The secret **must** come from an environment variable. Hard-coding it here is fine for the exercise; it would be a CVE in production.
3. The `iat` and `exp` claims are conventional. The `sub` claim is the subject (usually the user id).

### Exercise 4 — Reject a token signed with the wrong key

```python
bad = jwt.encode({"sub": "x", "exp": 9_999_999_999},
                 "different-secret", algorithm=ALG)
try:
    read_token(bad)
except Exception as e:
    print("rejected:", type(e).__name__, e)    # JWTError
```

**Step-by-step:**
1. The wrong key produces a different signature; `jwt.decode` raises.
2. In FastAPI, raise `HTTPException(status_code=401, detail="Invalid token")` from this.
3. Never catch this exception silently — that is how token-validation bugs hide.

### Exercise 5 — Parameterize a SQL query (the safe way)

```python
# SAFE — parameterized, the database engine escapes the value
def safe_select_user(cursor, user_id: str) -> dict | None:
    cursor.execute("SELECT id, email FROM users WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    return {"id": row[0], "email": row[1]} if row else None

# UNSAFE — string formatting, vulnerable to injection
def unsafe_select_user(cursor, user_id: str) -> None:
    cursor.execute(f"SELECT id, email FROM users WHERE id = '{user_id}'")  # NEVER do this
```

**Step-by-step:**
1. The difference is **who** builds the SQL string. When you build it, the database cannot tell the user input from the SQL.
2. When you pass parameters separately, the database treats them as values, not code.
3. SQLAlchemy / SQLModel give you this for free: `session.execute(select(User).where(User.id == user_id))`.

### Exercise 6 — Send a CORS preflight and read the headers

```python
# Run this against your running app
import httpx

r = httpx.options(
    "http://localhost:8000/requests",
    headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type, authorization",
    },
)
print(r.status_code, r.headers.get("access-control-allow-origin"))
```

**Step-by-step:**
1. A preflight is an `OPTIONS` request the browser sends before a "non-simple" cross-origin request.
2. The server must respond with `Access-Control-Allow-Origin` and `Access-Control-Allow-Methods`.
3. If `Access-Control-Allow-Origin: *` ever appears together with `Access-Control-Allow-Credentials: true`, the browser will reject the response. That is a **bug**, not a setting.

### Exercise 7 — Add security headers in a Starlette middleware

```python
# practice_security.py — append
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        resp: Response = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        resp.headers["Content-Security-Policy"] = "default-src 'self'"
        return resp
```

**Step-by-step:**
1. `nosniff` stops browsers from guessing the content type and executing scripts in JSON responses.
2. `X-Frame-Options: DENY` blocks clickjacking by refusing to be embedded in an iframe.
3. `Strict-Transport-Security` is only meaningful over HTTPS — keep it for production, drop it for local dev.

### Exercise 8 — Read a secret from the environment and fail fast if missing

```python
import os
from typing import Final

def required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

JWT_SECRET: Final[str] = required("JWT_SECRET")
DATABASE_URL: Final[str] = required("DATABASE_URL")
```

**Step-by-step:**
1. Failing fast at startup is better than failing at the first request with a generic 500.
2. The `Final` type hint signals "this will not be reassigned" to readers and to mypy.
3. Never default secrets to a non-empty string — that hides the misconfiguration in production.

### Exercise 9 — Build a tiny audit-log emitter

```python
# practice_security.py — append
import json
import time
from pathlib import Path

AUDIT_PATH = Path("audit.log")

def audit(actor: str, action: str, target: str, **extra) -> None:
    event = {
        "ts": time.time(),
        "actor": actor,
        "action": action,
        "target": target,
        **extra,
    }
    with AUDIT_PATH.open("a") as f:
        f.write(json.dumps(event) + "\n")

audit(actor="user-42", action="request.close", target="REQ-007", reason="resolved")
print(AUDIT_PATH.read_text())
```

**Step-by-step:**
1. Every privileged action (close, delete, role change) should call `audit(...)`.
2. In production, append to a write-only sink (file, syslog, or a managed log service).
3. The audit log is for **after-the-fact** review. Do not gate operations on its success.

### Exercise 10 — Run Bandit and read the report

```bash
uv run bandit -r app -lll
```

**Step-by-step:**
1. `-lll` shows only high-severity issues. Drop it to see medium and low.
2. Each finding includes a confidence level. Treat "High confidence, High severity" as a bug.
3. Add `bandit` to the CI pipeline from Week 18 so a new high-severity finding fails the build.

---

## Main Lab: Secure the Engagement Tracker (4–5 hours)

### Scenario

A security review of the Engagement Tracker has been scheduled. The auditor will read the diff between Week 15 and Week 20, run `bandit`, and click through the running app with a proxy. You have to land the security hardening without breaking the existing tests.

### Target File Layout

```
app/
  security/
    __init__.py
    passwords.py        # argon2 helpers
    tokens.py           # JWT issue + verify
    middleware.py       # security headers, CORS, trusted host
    audit.py            # audit log emitter
  main.py               # app factory
  ...
tests/
  test_security.py      # new
  ...
.env.example            # new, lists every required env var
```

### Build Steps

**Commit after each step.**

#### Step 1 — Add the password helpers and replace the storage path

*`feat(security): add argon2 password hashing`*

```python
# app/security/passwords.py
from passlib.context import CryptContext

_pwd = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(plain: str) -> str:
    return _pwd.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)

def needs_rehash(hashed: str) -> bool:
    return _pwd.needs_rehash(hashed)
```

```python
# wherever you create users
from app.security.passwords import hash_password

user.password_hash = hash_password(plain_text_from_form)
```

**Step-by-step:**
1. Remove any code that calls `hashlib.sha256(plain).hexdigest()`.
2. Existing users with sha256 hashes will need to reset — that is acceptable; document it in the release notes.
3. `needs_rehash` lets you upgrade the cost factor over time without forcing a password reset.

#### Step 2 — Add JWT issue and verify helpers

*`feat(security): add JWT helpers`*

```python
# app/security/tokens.py
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from jose import jwt, JWTError

ALG = "HS256"
TOKEN_TTL = timedelta(minutes=15)
SECRET = os.environ["JWT_SECRET"]   # raised KeyError at import if missing

class InvalidToken(Exception):
    pass

def issue_token(sub: str, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": sub,
        "iat": now,
        "exp": now + TOKEN_TTL,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, SECRET, algorithm=ALG)

def verify_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, SECRET, algorithms=[ALG])
    except JWTError as e:
        raise InvalidToken(str(e)) from e
```

**Step-by-step:**
1. Read `JWT_SECRET` at import time. If it is missing, the app refuses to start — exactly what you want.
2. `algorithms=[ALG]` is **not** optional. The default in some libraries is `none`, which is a CVE.
3. 15 minutes is a reasonable access-token TTL. Refresh tokens are a separate problem you can add in Week 22.

#### Step 3 — Add a FastAPI dependency that requires a valid token

*`feat(security): add auth dependency`*

```python
# app/security/tokens.py — append
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    try:
        return verify_token(token)
    except InvalidToken as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
```

```python
# usage in a route
from app.security.tokens import current_user

@app.get("/me")
def me(user: dict = Depends(current_user)):
    return {"id": user["sub"]}
```

**Step-by-step:**
1. `OAuth2PasswordBearer` declares the URL where clients obtain tokens; FastAPI uses it to render the **Authorize** button in `/docs`.
2. The dependency raises 401 with `WWW-Authenticate: Bearer` — clients can react to that header.
3. Test it: `curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/me` returns 200; without the header it returns 401.

#### Step 4 — Replace every string-formatted SQL with parameterized SQL

*`fix(security): parameterize all SQL queries`*

```python
# BEFORE — never do this
cursor.execute(f"SELECT * FROM requests WHERE id = '{request_id}'")

# AFTER — safe
cursor.execute("SELECT * FROM requests WHERE id = %s", (request_id,))
```

```python
# SQLAlchemy / SQLModel — already safe
result = session.execute(select(Request).where(Request.id == request_id)).scalar_one_or_none()
```

**Step-by-step:**
1. Search the repo for `f"SELECT`, `f"INSERT`, `f"UPDATE`, `f"DELETE`. Every hit is a candidate for a fix or a justification comment.
2. SQLAlchemy and SQLModel take care of this for you when you use the expression API. The risk is `text()` with string formatting.
3. Add a test that submits `' OR '1'='1` as the id; it must return 404, not every row.

#### Step 5 — Add a CORS middleware restricted to an allow-list

*`feat(security): restrict CORS to allow-list`*

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGINS = [
    "http://localhost:5173",   # vite dev
    "http://localhost:3000",   # next.js dev
    "https://tracker.example.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)
```

**Step-by-step:**
1. Read allowed origins from `CORS_ALLOWED_ORIGINS` env var, parsed as a comma-separated list.
2. `allow_origins=["*"]` together with `allow_credentials=True` is invalid and the browser will refuse the response.
3. In dev you can add a test origin; in production only the real frontend should be there.

#### Step 6 — Add a TrustedHost middleware

*`feat(security): add trusted host middleware`*

```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost").split(",")

app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
```

**Step-by-step:**
1. Without this, anyone with a Host header can hit your app behind a misconfigured proxy and trigger cache poisoning.
2. In production, set `ALLOWED_HOSTS=tracker.example.com`.
3. The middleware is **strict** — `localhost` works locally; a request with `Host: evil.com` returns 400.

#### Step 7 — Add a security-headers middleware

*`feat(security): add security headers middleware`*

```python
# app/security/middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        resp: Response = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'"
        )
        resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return resp
```

**Step-by-step:**
1. Register it **first** so it runs last on the way out.
2. CSP starts strict and loosens as you find what the frontend needs. The default here permits the basics.
3. `Permissions-Policy` tells the browser which features your site will never use.

#### Step 8 — Add an audit-log emitter and call it from every privileged route

*`feat(security): add audit log`*

```python
# app/security/audit.py
import json
import time
from pathlib import Path

AUDIT_PATH = Path(os.environ.get("AUDIT_LOG_PATH", "audit.log"))

def audit(actor: str, action: str, target: str, **extra: object) -> None:
    event = {
        "ts": time.time(),
        "actor": actor,
        "action": action,
        "target": target,
        **extra,
    }
    with AUDIT_PATH.open("a") as f:
        f.write(json.dumps(event) + "\n")
```

```python
# in a route that closes a request
from app.security.audit import audit
from app.security.tokens import current_user

@router.post("/requests/{request_id}/close")
def close_request(request_id: str, user: dict = Depends(current_user)):
    # ... do the close ...
    audit(actor=user["sub"], action="request.close", target=request_id)
```

**Step-by-step:**
1. Every state-changing endpoint should call `audit`. Read-only endpoints do not need to.
2. In production, write to a dedicated sink — a file is fine for the lab.
3. Append a `.json` parser to your log pipeline so the audit log is structured, not free text.

#### Step 9 — Create `.env.example` and ensure `.env` is git-ignored

*`docs(security): document required env vars`*

```bash
# .env.example  (commit this; the values are placeholders)
JWT_SECRET=replace-me-with-a-32-byte-random-string
DATABASE_URL=postgresql://tracker:tracker@localhost:5432/tracker
CORS_ALLOWED_ORIGINS=http://localhost:5173
ALLOWED_HOSTS=localhost
AUDIT_LOG_PATH=audit.log
```

```bash
# .gitignore
.env
*.pem
audit.log
```

```bash
# generate a real JWT secret
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**Step-by-step:**
1. `.env.example` is committed; `.env` is not. Contributors copy the example to `.env` and fill in real values.
2. The `secrets.token_urlsafe(48)` output is a fine default for `JWT_SECRET`. Store it in your password manager.
3. `git log -- .env` — if `.env` was ever committed, the secret is compromised; rotate immediately.

#### Step 10 — Run Bandit and clean up every high-severity finding

*`chore(security): zero bandit high-severity findings`*

```bash
uv run bandit -r app -lll
```

**Step-by-step:**
1. Treat any "High" finding as a bug, even if the code "works".
2. Common offenders: `B303` (insecure hash), `B105` (hard-coded password), `B608` (SQL injection). Read the [Bandit plugin index](https://bandit.readthedocs.io/en/latest/plugins/index.html) for each.
3. Add Bandit to the CI workflow from Week 18 as a new job.

### Required Manual Tests

- [ ] POST to `/auth/token` with valid credentials returns a JWT
- [ ] POST to `/auth/token` with the wrong password returns 401
- [ ] GET `/me` without `Authorization` returns 401
- [ ] GET `/me` with a valid token returns the user id
- [ ] GET `/me` with a token signed by a different secret returns 401
- [ ] GET `/me` with an expired token returns 401
- [ ] `curl -H "Origin: http://evil.com" -i http://localhost:8000/requests` does **not** return `Access-Control-Allow-Origin: http://evil.com`
- [ ] `curl -H "Host: evil.com" -i http://localhost:8000/requests` returns 400
- [ ] `curl -i http://localhost:8000/health` includes all six security headers
- [ ] Submitting `' OR '1'='1` as a request id returns 404
- [ ] `bandit -r app -lll` returns zero high-severity issues
- [ ] Closing a request appends a line to `audit.log`

### Acceptance Criteria

- [ ] Passwords are hashed with argon2 — no sha256, no md5
- [ ] JWTs are issued and verified with HS256 + a secret from the environment
- [ ] Every authenticated route uses `Depends(current_user)`
- [ ] Every SQL call uses parameterized queries (or SQLAlchemy expression API)
- [ ] CORS is restricted to a configured allow-list
- [ ] TrustedHost middleware is registered
- [ ] Every response includes the six security headers
- [ ] `.env` is in `.gitignore`; `.env.example` is committed
- [ ] `audit(...)` is called from every state-changing route
- [ ] `bandit -r app -lll` reports no high-severity issues
- [ ] Tests cover the happy path and at least one negative case per security behaviour
- [ ] At least 5 meaningful commits

## AI-Off Check (30 minutes)

**Without looking at your code**, write a FastAPI dependency that:

1. Reads `Authorization: Bearer <token>` from the request
2. Verifies the JWT with HS256 and a secret from the environment
3. Returns the `sub` claim
4. Raises 401 on any failure

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
import os

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
SECRET = os.environ["JWT_SECRET"]
ALG = "HS256"

def current_user(token: str = Depends(oauth2_scheme)) -> str:
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALG])
        return payload["sub"]
    except (JWTError, KeyError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
```

Write it cold. Then diff against your `app/security/tokens.py`. The goal is to internalize: dependency → token → decode → 401 on failure.

## Reflection Questions

After you finish, write answers to these in `REFLECTION.md`:

1. Why is `algorithms=[ALG]` required in `jwt.decode`? What attack does omitting it enable?
2. Why is `Access-Control-Allow-Origin: *` incompatible with `Access-Control-Allow-Credentials: true`?
3. Why does parameterized SQL prevent injection when string formatting does not?
4. What is the difference between *authentication* and *authorization*? Which did you add this week?
5. If a `.env` file is accidentally committed to GitHub, what is the correct response? What about a private repo — is that different?

## Next Steps

Once you pass all acceptance criteria:

1. Record a 1-minute walkthrough showing a request without a token being rejected
2. Write the reflection answers
3. Commit with message: `docs: week 20 complete`
4. Move to Week 21 (Customer Discovery) — Phase 6 begins

---

**Ready?** Start by:

```bash
uv add "passlib[argon2]" "python-jose[cryptography]"
uv add --dev bandit
mkdir -p app/security
```

Then commit Step 1 and run the auth endpoint. Good luck! 🎯
