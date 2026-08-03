# Week 23: Production Hardening

## Outcome

Take the working capstone from Week 22 and turn it into a system you would be willing to hand to a real customer: comprehensive test coverage, security and compliance controls, deployment infrastructure, and a cost / performance analysis. By the end of the week the system has a `make audit` target that runs every check the security review from Week 20 demanded, a `make deploy` that ships to your platform of choice, and a one-page `docs/perf.md` that names the current bottleneck.

The deliverable is the same code, but with a much smaller surface area for "the auditor will catch this" risk.

## Setup Checklist

- [ ] The capstone repo from Week 22, with the smoke test passing
- [ ] The Week 20 hardening work merged in (or rebased onto this branch)
- [ ] The Week 18 CI workflow merged in
- [ ] A `docker compose` that brings the system up locally
- [ ] A staging environment for one of: Fly.io, Render, Railway, AWS, or a self-hosted VM

### Setup Walkthrough

```bash
cd /path/to/your/capstone-repo

# 1. Create a feature branch
git checkout -b harden/week-23

# 2. Add the audit / deploy tooling
uv add --dev bandit pip-audit gitleaks-action
uv add slowapi                  # rate limiting for FastAPI
uv add httpx                     # for synthetic checks in deploy

# 3. Create the docs and infra folders
mkdir -p docs/audit
mkdir -p deploy
mkdir -p perf

# 4. Confirm the smoke test still passes
make test
```

## Learning Path (60–90 minutes)

**Best approach:** Work from a checklist. The output of Week 23 is **proof** that a set of properties hold, not the act of adding them.

### Learn in this order

1. **Test pyramid in practice** — unit, integration, contract, smoke, load; what each catches
2. **Rate limiting in FastAPI** — `slowapi`, per-IP, per-user, per-tenant
3. **Audit log pipeline** — what to send where, retention, immutability
4. **Backup and restore** — pg_dump, restore to a different host, verify the restore
5. **Performance profiling** — `py-spy`, `cProfile`, OpenTelemetry spans
6. **Cost modelling** — tokens, request count, storage; what scales linearly
7. **Disaster recovery** — RPO and RTO written down, not implied

### Free Resources

- [FastAPI: Testing](https://fastapi.tiangolo.com/tutorial/testing/) — official testing guide
- [Hypothesis](https://hypothesis.readthedocs.io/) — property-based testing for Python
- [slowapi](https://github.com/laurentS/slowapi) — rate limiting library for FastAPI
- [OWASP: Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) — what to log, what not to log
- [PostgreSQL: Continuous Archiving](https://www.postgresql.org/docs/current/continuous-archiving.html) — the official backup story
- [py-spy](https://github.com/benfred/py-spy) — sampling profiler for Python
- [Fly.io: Backups](https://fly.io/docs/postgres/backup-and-restore/) — managed Postgres backup story
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/) — traces, metrics, logs
- [Litestar / pydantic benchmarking](https://github.com/samuelcolvin/python-performance-tips) — Samuel Colvin's perf tips

**Tip:** Read the [OWASP logging cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) and the [PostgreSQL continuous archiving docs](https://www.postgresql.org/docs/current/continuous-archiving.html) — both are short and both change your threat model.

## Micro-Exercises (45–60 minutes)

Complete these in order. Each produces evidence the auditor can read.

### Exercise 1 — Build a coverage report and a coverage gate

```bash
uv run pytest --cov=app --cov-report=term-missing --cov-report=xml
uv add --dev coverage
```

```toml
# pyproject.toml
[tool.coverage.run]
source = ["app"]
branch = true
omit = ["app/migrations/*", "app/main.py"]

[tool.coverage.report]
fail_under = 80
exclude_lines = ["pragma: no cover", "if TYPE_CHECKING:", "raise NotImplementedError"]
```

**Step-by-step:**
1. Run the tests; note the current coverage.
2. Set `fail_under` to a number just below the current number, then commit it.
3. Each subsequent commit that drops coverage below the gate fails CI.
4. Do **not** game coverage by writing tests that don't assert anything. The point is meaningful coverage, not the number.

### Exercise 2 — Add a property-based test for the service layer

```python
# tests/test_properties.py
from hypothesis import given, strategies as st
from datetime import datetime
from app.services.reports import ReportService

@given(
    week=st.datetimes(min_value=datetime(2024, 1, 1), max_value=datetime(2026, 12, 31)),
    net_adds=st.integers(min_value=-1000, max_value=1000),
)
def test_draft_is_idempotent_on_data(week, net_adds):
    # arrange a service
    # act twice with the same data
    # assert: cells are equal
    ...
```

**Step-by-step:**
1. Hypothesis explores edge cases you would not think to type. Run it for 30 seconds and read the failures.
2. Add `@example(...)` to seed a known input that previously caused a failure.
3. Property-based tests are best for pure functions. For DB-touching services, use them to test the **invariants** of the data.
4. If a property test is flaky, the production code is flaky. Do not silence the test.

### Exercise 3 — Add rate limiting with slowapi

```python
# app/main.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/reports")
@limiter.limit("5/minute")
async def create_report(...):
    ...
```

**Step-by-step:**
1. The 5/minute limit is for unauthenticated endpoints. Authenticated endpoints can be higher.
2. Add a 429 handler so the client gets a useful error, not a generic 500.
3. For per-user limits, use `key_func=lambda: request.state.user["sub"]` — but only after auth has run.
4. Test the rate limit: `for i in {1..6}; do curl -X POST .../reports; done` — the 6th returns 429.

### Exercise 4 — Make the audit log append-only

```python
# app/security/audit.py
import json
import time
import os
from pathlib import Path

AUDIT_PATH = Path(os.environ.get("AUDIT_LOG_PATH", "audit.log"))

def audit(actor: str, action: str, target: str, **extra) -> None:
    event = {
        "ts": time.time(),
        "actor": actor,
        "action": action,
        "target": target,
        **extra,
    }
    line = json.dumps(event) + "\n"
    with open(AUDIT_PATH, "ab") as f:
        f.write(line)
    # Belt-and-braces: also write to stdout for the log pipeline
    print(line, end="")
```

```bash
# Mark audit.log as append-only for the app user
sudo chattr +a /var/log/app/audit.log
```

**Step-by-step:**
1. Open the file in `ab` (append binary) mode — the OS enforces append-only.
2. Belt-and-braces: also `print` so the log shipper picks it up. The two paths are independent.
3. In production, ship to a managed log service. The local file is for the dev loop.
4. Verify the append-only flag with `lsattr audit.log` — the `a` flag should be set.

### Exercise 5 — Add a backup script and a restore test

```bash
#!/usr/bin/env bash
# deploy/backup.sh
set -euo pipefail
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
BACKUP_DIR="${BACKUP_DIR:-/var/backups/app}"
mkdir -p "$BACKUP_DIR"
pg_dump "$DATABASE_URL" | gzip > "$BACKUP_DIR/app-$TIMESTAMP.sql.gz"
echo "Wrote $BACKUP_DIR/app-$TIMESTAMP.sql.gz"
```

```bash
#!/usr/bin/env bash
# deploy/restore-test.sh
set -euo pipefail
LATEST=$(ls -1t /var/backups/app/app-*.sql.gz | head -1)
TEST_DB="restore_test_$(date +%s)"
createdb "$TEST_DB"
gunzip -c "$LATEST" | psql "$TEST_DB" >/dev/null
# Smoke: count rows in the most important table
psql "$TEST_DB" -c "SELECT count(*) FROM weekly_reports"
dropdb "$TEST_DB"
```

**Step-by-step:**
1. Run `backup.sh` — confirm a `.sql.gz` file appears.
2. Run `restore-test.sh` — confirm the row count matches production.
3. Schedule `backup.sh` nightly via cron. Schedule `restore-test.sh` weekly; a backup that has never been restored is a hope, not a backup.
4. Document the RPO (data loss budget) and RTO (recovery time) in `docs/disaster-recovery.md`.

### Exercise 6 — Add a one-shot performance benchmark

```python
# perf/bench_draft.py
"""Run N concurrent draft requests and report p50/p95/p99 latencies."""
import asyncio
import time
import statistics
import httpx

URL = "http://localhost:8000"

async def one_draft(client, report_id):
    t0 = time.perf_counter()
    r = await client.post(f"{URL}/reports/{report_id}/draft")
    return (time.perf_counter() - t0) * 1000, r.status_code

async def main():
    async with httpx.AsyncClient(timeout=60) as client:
        # create a few reports first
        ids = []
        for i in range(5):
            r = await client.post(f"{URL}/reports",
                                  params={"week_of": f"2026-01-{i+1:02d}T00:00:00"},
                                  json={"net_adds": i * 10})
            ids.append(r.json()["id"])

        # now run drafts
        latencies = []
        for _ in range(20):
            t, status = await one_draft(client, ids[0])
            assert status == 200, f"draft failed: {status}"
            latencies.append(t)

        print(f"n={len(latencies)}  p50={statistics.median(latencies):.0f}ms  "
              f"p95={sorted(latencies)[int(len(latencies)*0.95)]:.0f}ms  "
              f"max={max(latencies):.0f}ms")

asyncio.run(main())
```

**Step-by-step:**
1. Run the bench against a fresh local stack. Record the numbers.
2. The numbers are the **baseline**. Anything you tune in production you compare against this.
3. The bench is **not** a load test — 20 requests is not enough to find a memory leak. Use `locust` or `k6` for that.
4. Save the output of every run to `perf/results/<date>.txt`. Over time, trends appear.

### Exercise 7 — Add a cost model

```markdown
# docs/cost.md

## Assumptions
- 50 reports/week, 12 cells/report
- LLM cost: $0.15 / 1M input tokens, $0.60 / 1M output tokens
- Postgres storage: 1 KB / report row
- Object storage for .pptx: 200 KB / report

## Per-week cost (single customer)
- LLM draft: 50 × 12 cells × 1k input tokens × $0.15 / 1M = $0.09
- LLM draft: 50 × 12 cells × 200 output tokens × $0.60 / 1M = $0.72
- DB storage: 50 reports × 1 KB = 50 KB / week → $0.00 (negligible)
- Object storage: 50 reports × 200 KB = 10 MB / week → $0.00
- Compute (1× shared Fly app): $5/mo ≈ $1.15 / week

**Total per week, single customer: ~$2.00**

## At 100 customers
- LLM: 100 × ~$0.81 = ~$81 / week
- Compute: still ~$5 / week on the same instance until ~50 customers
- Storage: 100 × 50 KB / week ≈ 5 MB / week → still negligible

**Total per week, 100 customers: ~$90**
**Per customer: $0.90 / week**

## What scales linearly
- LLM cost (proportional to reports)
- DB storage (proportional to history)
- Object storage (proportional to .pptx count)

## What does NOT scale linearly
- Compute (one app, many customers, until ~500 customers)
- Engineering time (the cost of building v2 is one-time)

## Decision
For 0–100 customers, the **LLM cost is the variable that matters**.
For 100+, the **LLM cost plus the cache hit rate** is what matters.
```

**Step-by-step:**
1. Every number in the cost doc is a calculation or a measurement. No "approximately $X" without a source.
2. Update the doc every time you change the system. A stale cost model is worse than no model.
3. Link the cost model to the non-functional requirements from `03-requirements.md`. If the cost is too high, the requirement is unmet.
4. The cost model is a contract with the customer. If real cost exceeds the model, escalate.

### Exercise 8 — Add a disaster-recovery one-pager

```markdown
# Disaster recovery

## Definitions
- **RPO (Recovery Point Objective):** maximum data we are willing to lose
- **RTO (Recovery Time Objective):** maximum downtime we are willing to accept

## Targets
- **RPO: 24 hours** — one full backup every night, plus point-in-time recovery on Postgres
- **RTO: 4 hours** — from page to fully restored service

## Backup
- **What:** `pg_dump` of the application database, run nightly at 02:00 UTC
- **Where:** `/var/backups/app/` on the primary, offsite-replicated to S3
- **Retention:** 30 days

## Restore
1. Page on-call, acknowledge within 15 minutes
2. Provision a new Postgres instance (15 minutes)
3. Restore the latest backup (30 minutes)
4. Run schema migrations (5 minutes)
5. Deploy the latest app image (15 minutes)
6. Run the smoke test (5 minutes)
7. Update DNS or load balancer (15 minutes)
8. Post-incident review within 48 hours

## Restore test
- Weekly: `deploy/restore-test.sh` against the latest backup
- Monthly: full restore into a staging environment, run the smoke test

## Single point of failure
- The Postgres primary is the only SPOF in the system. Mitigated by the offsite
  backup and a 4-hour RTO. The next iteration is a hot standby.
```

**Step-by-step:**
1. The numbers in this document are **decisions**, not measurements. If the customer wants a tighter RPO, the cost of the next iteration changes.
2. The restore procedure is **stepwise** and **time-boxed**. If a step is "figure it out", the document is not done.
3. The restore test is automated. A backup that has never been restored is not a backup.
4. Read this document out loud to someone who has never seen the system. If they cannot follow it, rewrite it.

### Exercise 9 — Add a rate-limited public route with a real test

```python
# app/api/public.py
from fastapi import APIRouter, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/public", tags=["public"])
limiter = Limiter(key_func=get_remote_address)

@router.get("/status")
@limiter.limit("60/minute")
def public_status(request: Request):
    return {"ok": True}
```

```python
# tests/test_rate_limit.py
def test_public_status_returns_429_after_limit(client):
    for _ in range(60):
        r = client.get("/public/status")
        assert r.status_code == 200
    r = client.get("/public/status")
    assert r.status_code == 429
```

**Step-by-step:**
1. The limit is per remote address in this test. In production, it should be per-tenant.
2. The test takes 60 requests; if your rate limit is different, adjust the test.
3. The 429 response should include `Retry-After` — verify it does.
4. Add a `RateLimit-*` log line for every 429 so you can see who is being limited.

### Exercise 10 — Add a synthetic uptime check

```python
# perf/uptime_check.py
"""Hit /health every 5 seconds for 1 hour. Report any non-200."""
import time
import httpx

URL = "http://localhost:8000/health"
WINDOW = 3600   # seconds
PERIOD = 5

failures = 0
for i in range(WINDOW // PERIOD):
    r = httpx.get(URL, timeout=5)
    if r.status_code != 200:
        failures += 1
        print(f"FAIL at {i*PERIOD}s: {r.status_code} {r.text}")
    time.sleep(PERIOD)

print(f"failures: {failures}/{WINDOW // PERIOD}")
```

**Step-by-step:**
1. The uptime check is a separate process from the app. Run it as a cron or a sidecar.
2. In production, replace this with a real uptime monitor (Pingdom, BetterStack, Checkly).
3. Treat any non-200 as a failure. The check is only useful if it never lies.
4. Save the output to `perf/uptime-results/<date>.log` and look for trends.

---

## Main Lab: Harden the Capstone (4–5 hours)

### Scenario

A security review is scheduled for next week. The auditor will read the codebase, run `bandit`, and click through the deployed app. The cost of an unexpected finding is one more week of remediation. Your job this week is to land every property the auditor will check, and to leave evidence in the repo.

### Target File Layout (additions)

```
my-capstone/
  deploy/
    backup.sh
    restore-test.sh
    deploy.sh
  perf/
    bench_draft.py
    uptime_check.py
    results/
  docs/
    audit/
      bandit.txt
      pip-audit.txt
      secrets-scan.txt
    cost.md
    disaster-recovery.md
    perf.md
    security.md
  tests/
    test_smoke.py
    test_services.py
    test_security.py
    test_properties.py
    test_rate_limit.py
```

### Build Steps

**Commit after each step.** A typical hardening week has 8–10 commits.

#### Step 1 — Land the Week 20 hardening on this branch

*`chore: rebase week-20 hardening onto capstone`*

If your security work is on a different branch, rebase it onto `harden/week-23`. Run the Week 20 manual tests again — none of them should regress.

#### Step 2 — Raise the coverage gate to 80%

*`test: set coverage gate to 80%`*

Add the `tool.coverage` block from Exercise 1. Run the suite. If the gate fails, write one more test before lowering the gate — never raise it.

#### Step 3 — Add a property-based test for the service invariants

*`test: add property-based tests for service invariants`*

Copy the example from Exercise 2. Find at least one invariant in your service code that the test can express. A common one: "drafting twice with the same data produces the same cells."

#### Step 4 — Add rate limiting to the public routes

*`feat: add rate limiting to public routes`*

Apply slowapi to at least one public route (e.g. `/health` or a future `/signup`). Verify the test from Exercise 9 passes.

#### Step 5 — Make the audit log append-only

*`feat(security): make audit log append-only`*

Use `chattr +a` (or your platform's equivalent) and the `ab` open mode from Exercise 4. Document the change in `docs/security.md`.

#### Step 6 — Add the backup and restore scripts

*`ops: add backup and restore scripts`*

Copy `deploy/backup.sh` and `deploy/restore-test.sh` from Exercise 5. Run them locally. Schedule them in cron (or in a managed scheduler for the platform you chose).

#### Step 7 — Add the performance benchmark

*`perf: add end-to-end benchmark`*

Copy `perf/bench_draft.py` from Exercise 6. Run it. Save the output to `perf/results/<date>.txt`. Write a one-paragraph interpretation in `docs/perf.md`.

#### Step 8 — Write the cost model

*`docs: add cost model`*

Copy the template from Exercise 7. Fill in the numbers for your actual system. Save the file at `docs/cost.md`.

#### Step 9 — Write the disaster-recovery one-pager

*`docs: add disaster-recovery one-pager`*

Copy the template from Exercise 8. Fill in the actual numbers. Save the file at `docs/disaster-recovery.md`.

#### Step 10 — Run a full audit sweep and commit the reports

*`chore: run full audit sweep and commit reports`*

```bash
# Run every check the auditor might run
uv run bandit -r app -lll > docs/audit/bandit.txt
uv run pip-audit -r <(uv export --no-hashes) > docs/audit/pip-audit.txt
gitleaks detect --no-banner --report-path docs/audit/secrets-scan.txt || true
uv run pytest --cov=app > docs/audit/coverage.txt
uv run ruff check . > docs/audit/ruff.txt
```

**Step-by-step:**
1. Each report goes into `docs/audit/` with a date in the filename if you re-run later.
2. A non-empty `secrets-scan.txt` is a **blocker**. Investigate before continuing.
3. A non-empty `bandit.txt` at high severity is a **blocker**. Fix or justify.
4. A failing `pip-audit` is usually a known CVE in a transitive dep — fix or document the override.

### Required Manual Tests

- [ ] `make test` passes
- [ ] `make test` includes the coverage gate and passes
- [ ] `make audit` (a new target) runs bandit, pip-audit, and gitleaks — all clean
- [ ] `deploy/backup.sh` runs and produces a backup file
- [ ] `deploy/restore-test.sh` restores the backup into a scratch DB and runs the smoke test
- [ ] `perf/bench_draft.py` runs and produces a `results/<date>.txt`
- [ ] `docs/cost.md` has numbers, not adjectives
- [ ] `docs/disaster-recovery.md` has RPO and RTO, both with units
- [ ] `docs/security.md` lists the controls from Week 20 and where to find them
- [ ] The Week 20 manual tests still pass (no regression)
- [ ] The Week 22 smoke test still passes (no regression)

### Acceptance Criteria

- [ ] Coverage gate is set to ≥ 80% and the suite passes
- [ ] At least one property-based test exists and passes
- [ ] Rate limiting is in place on the public routes and verified by a test
- [ ] Audit log is append-only on disk and shipped to stdout
- [ ] Backup and restore scripts exist and have been run successfully
- [ ] `docs/cost.md`, `docs/disaster-recovery.md`, `docs/perf.md`, `docs/security.md` exist and have content
- [ ] `make audit` is a single command that runs every audit
- [ ] `docs/audit/` contains the latest reports from every tool
- [ ] At least 5 meaningful commits
- [ ] No secrets in the repo
- [ ] The Week 22 acceptance criteria still hold (smoke test, docker compose, etc.)

## AI-Off Check (30 minutes)

**Without looking at your docs**, write a one-paragraph response to each of the following questions:

1. What is your RPO and RTO?
2. What is your per-customer weekly cost?
3. What is the current bottleneck in your system?

```text
1. RPO: 24 hours (one nightly pg_dump, offsite replicated). RTO: 4 hours
   (page on-call, provision new Postgres, restore backup, redeploy).
2. Per-customer weekly cost: ~$2.00 at 1 customer, ~$0.90 at 100 customers.
   Dominated by LLM output tokens.
3. Current bottleneck: the LLM draft call. p50 ~1.2s, p95 ~3.5s on a fresh
   local stack. The next thing to measure is the time to first byte on the
   API.
```

If you cannot answer cold, the system is not yet internalised. The goal is to be able to defend every number in the auditor's room.

## Reflection Questions

After you finish, write answers to these in `REFLECTION.md`:

1. Which of the 10 hardening steps had the biggest impact? Why?
2. Which would you have skipped if you had less time? How would you document that skip?
3. What did the coverage gate force you to test that you would otherwise have skipped?
4. If the auditor asked you to prove one control, which one would you demo, and how?
5. What is the next hardening item you would do, given two more days?

## Next Steps

Once you pass all acceptance criteria:

1. Save the output of `make audit` to `docs/audit/<date>.txt`
2. Write the reflection answers
3. Commit with message: `docs: week 23 complete`
4. Move to Week 24 (Demo and Reflection)

---

**Ready?** Start by running the Setup Walkthrough and confirming the Week 22 smoke test still passes. Then add the coverage gate — every other step depends on it. Good luck! 🎯
