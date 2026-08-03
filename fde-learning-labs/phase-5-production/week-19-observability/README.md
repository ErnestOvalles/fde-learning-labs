# Week 19: Observability, Logging, and Monitoring

## Outcome

Replace `print()` and free-text logs in the **Customer Engagement Tracker** with **structured JSON logs** that carry request IDs, switch the app's logging to `structlog`, expose **Prometheus metrics** for HTTP requests and LLM token usage, and wire an **alerting rule** that fires when the 5-minute error rate crosses 5%. By the end of the week a single `curl` to `/metrics` returns real numbers, every log line in the terminal is parseable JSON, and a sample Grafana / alert rule would catch a regression in production.

## Setup Checklist

- [ ] `uv add structlog prometheus-client prometheus-fastapi-instrumentator`
- [ ] `uv add --dev pytest pytest-asyncio`
- [ ] Docker installed (Week 17) so you can run Prometheus + Grafana locally
- [ ] Existing FastAPI app from Week 5/8

### Setup Walkthrough

```bash
# 1. Add the observability stack
cd /path/to/your/tracker
uv add structlog
uv add prometheus-client prometheus-fastapi-instrumentator
uv add --dev pytest pytest-asyncio

# 2. Create the observability folder
mkdir -p app/observability
touch app/observability/__init__.py
touch app/observability/logging.py
touch app/observability/metrics.py
touch app/observability/middleware.py

# 3. Spin up Prometheus + Grafana for local exploration
cat > docker-compose.observability.yml <<'EOF'
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./ops/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    ports: ["9090:9090"]
  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
EOF

mkdir -p ops
cat > ops/prometheus.yml <<'EOF'
global:
  scrape_interval: 5s
scrape_configs:
  - job_name: tracker
    static_configs:
      - targets: ["host.docker.internal:8000"]
EOF

# 4. Sanity-check
uv run python -c "import structlog, prometheus_client; print('ok')"
```

## Learning Path (60–90 minutes)

**Best approach:** Treat observability as a **production feature** with three layers — emit, aggregate, alert. Each layer is one decision.

### Learn in this order

1. **Three pillars** — logs (events), metrics (numbers), traces (causality); what each is good for
2. **Structured logging** — what JSON logs give you over free text, why `structlog` exists
3. **Log context** — binding request-scoped data (request ID, user ID, route) to every log line
4. **Prometheus model** — counters, gauges, histograms, summaries; pull-based scraping
5. **Metric naming** — `<namespace>_<subsystem>_<name>_<unit>` (`http_requests_total`, `llm_tokens_total`)
6. **Labels and cardinality** — what to put in a label, what blows up Prometheus
7. **Instrumentation libraries** — `prometheus-fastapi-instrumentator`, custom counters
8. **Alerting basics** — PromQL expressions, the `for` clause, what "alert fatigue" is
9. **Sampling and cost** — when to drop traces or sample logs, never log secrets

### Free Resources

- [structlog: Getting started](https://www.structlog.org/en/stable/getting-started.html) — read this first
- [structlog: Contextvars](https://www.structlog.org/en/stable/contextvars.html) — how request-scoped data flows
- [Prometheus: Concepts](https://prometheus.io/docs/concepts/data_model/) — the data model in 10 minutes
- [Prometheus: Naming](https://prometheus.io/docs/practices/naming/) — the rules that keep your dashboards sane
- [Prometheus: Metric types](https://prometheus.io/docs/concepts/metric_types/) — counter, gauge, histogram
- [prometheus-fastapi-instrumentator](https://github.com/trallnag/prometheus-fastapi-instrumentator) — drop-in middleware
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/) — when you outgrow Prometheus-only
- [Grafana: Alerting 101](https://grafana.com/docs/grafana/latest/alerting/fundamentals/) — the alerting primer

**Tip:** Read the Prometheus **Concepts** page first. It is the mental model the rest of the ecosystem assumes.

## Micro-Exercises (45–60 minutes)

Create a `practice.py` in a scratch folder and complete these:

### Exercise 1 — Print a structured log line with structlog

```python
# practice.py
import structlog

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

log = structlog.get_logger()

log.info("server.started", port=8000, env="dev")
log.warning("rate_limit.near", user_id="u-42", current=98, limit=100)
log.error("db.connection_failed", host="db", retries=3)
```

**Step-by-step:**
1. Run with `uv run python practice.py`.
2. Confirm the output is one JSON object per line — **not** a free-text string.
3. The keys after the event name (`port`, `user_id`, `retries`) become JSON fields automatically. That is the whole point.

### Exercise 2 — Bind context to a logger for a request scope

```python
import structlog, uuid

log = structlog.get_logger()

def handle_request(user_id: str) -> None:
    request_log = log.bind(request_id=str(uuid.uuid4()), user_id=user_id)
    request_log.info("request.received")
    request_log.info("request.processed", status_code=200)
    request_log.info("request.finished", duration_ms=42)

handle_request("u-42")
```

**Step-by-step:**
1. `log.bind(...)` returns a **new** logger with extra fields. Every later log line carries them.
2. The pattern is: bind once at the top of a request, then log freely.
3. Notice the `request_id` is the same on all three lines — that is what lets you correlate them in your log search.

### Exercise 3 — Use `contextvars` so context propagates across awaits and threads

```python
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars, bound_contextvars

log = structlog.get_logger()

async def fetch_user(user_id: str) -> None:
    bind_contextvars(request_id="req-1", user_id=user_id)
    log.info("user.fetched")
    await some_async_call()
    log.info("user.cache_warmed")

def some_other_handler() -> None:
    with bound_contextvars(request_id="req-2"):
        log.info("background.tick")
    clear_contextvars()
```

**Step-by-step:**
1. `bind_contextvars` writes to a `ContextVar`, which is automatically carried across `await` and thread boundaries.
2. `clear_contextvars()` at the end of a request prevents leaks between requests in the same worker.
3. In FastAPI middleware you call `clear_contextvars()` on response, then `bind_contextvars(request_id=...)` on request.

### Exercise 4 — Expose a Prometheus counter and increment it

```python
from prometheus_client import Counter, start_http_server

REQUESTS = Counter(
    "app_requests_total",
    "Total HTTP requests",
    labelnames=("method", "path", "status"),
)

# start an exporter on port 9000
start_http_server(9000)

REQUESTS.labels(method="GET", path="/health", status="200").inc()

# now visit http://localhost:9000/metrics
```

**Step-by-step:**
1. `Counter` only goes up. Use it for things like total requests, total errors, total tokens.
2. `start_http_server` opens a tiny HTTP server that Prometheus will scrape.
3. With `labelnames=("method", "path", "status")` every unique combo becomes a new time series. Keep cardinality low — **never** label by user ID or raw URL.

### Exercise 5 — Expose a Histogram for request latency

```python
from prometheus_client import Histogram

LATENCY = Histogram(
    "app_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=("method", "path"),
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

import time
start = time.perf_counter()
time.sleep(0.07)
LATENCY.labels(method="GET", path="/health").observe(time.perf_counter() - start)
```

**Step-by-step:**
1. Histograms are how you compute p50 / p95 / p99 latency in PromQL with `histogram_quantile()`.
2. Bucket boundaries matter — they should match the SLO you care about. For an LLM app, add `5`, `10`, `30` second buckets.
3. `observe()` records one sample. `time()` is a context manager that times a block and calls `observe()` for you.

### Exercise 6 — Use `Histogram.time()` to make a code block measurable

```python
with LATENCY.labels(method="POST", path="/llm/query").time():
    answer = call_llm(...)
```

**Step-by-step:**
1. This is the same as Exercise 5 but you do not have to manage start/end manually.
2. The histogram label is set **once** at the `with` statement — pick stable labels.
3. Combine with `try/except` if you also want a "failed" counter; the timer still records on exception.

### Exercise 7 — Scrape a Prometheus endpoint from the local stack

```bash
docker compose -f docker-compose.observability.yml up -d
uv run python practice.py
open http://localhost:9090
```

In the Prometheus UI, run:

```promql
rate(app_requests_total[1m])
```

**Step-by-step:**
1. After starting Prometheus, its targets page (Status → Targets) should show your `host.docker.internal:8000` job as **UP**.
2. The expression above is the most common one you'll write — `rate(counter[window])`.
3. If the target is DOWN, check that your exporter is bound to `0.0.0.0` (not `127.0.0.1`) so Docker can reach it.

### Exercise 8 — Write a sample alert rule

```yaml
# ops/alerts.yml
groups:
  - name: tracker-slo
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(app_requests_total{status=~"5.."}[5m]))
            /
          sum(rate(app_requests_total[5m]))
            > 0.05
        for: 2m
        labels:
          severity: page
        annotations:
          summary: "Error rate above 5% for 2m"
          description: "5xx rate is {{ $value | humanizePercentage }}"
```

**Step-by-step:**
1. The `for: 2m` clause means the alert only fires after the condition has been true for two full minutes — that prevents a one-second spike from paging anyone.
2. `severity: page` is a label, not a magic word; downstream tools (Grafana, Alertmanager) decide what it means.
3. Always include a human-readable `summary` and `description`. The `$value` interpolator is what makes the alert message self-explanatory.

---

## Main Lab: Structured Logging, Metrics, and Alerts for the Engagement Tracker (4–5 hours)

### Scenario

The Customer Engagement Tracker logs free text to stdout and has no metrics. You are adding a production observability stack that:

1. Emits **one JSON object per log line**, with `request_id`, `user_id`, `route`, and `latency_ms` bound to every line within a request.
2. Exposes `/metrics` with at least: `http_requests_total`, `http_request_duration_seconds`, `llm_tokens_total{type=input|output}`.
3. Defines three alert rules: high error rate, high p95 latency, and LLM token spend spike.

### Target File Layout

```
app/
  main.py                 # existing FastAPI app
  observability/
    __init__.py
    logging.py            # structlog configuration
    middleware.py         # request-id + access log
    metrics.py            # Prometheus counters/histograms
ops/
  prometheus.yml          # scrape config
  alerts.yml              # alert rules
tests/
  test_observability.py
```

### Build Steps

**Commit after each step.** Suggested messages are listed in italics.

#### Step 1 — Configure structlog to emit JSON to stdout

*`obs: configure structlog for json output`*

```python
# app/observability/logging.py
import logging
import sys

import structlog

def configure_logging(level: str = "INFO") -> None:
    """Configure stdlib logging and structlog to emit JSON to stdout."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper())),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
```

**Step-by-step:**
1. Drop the file in `app/observability/logging.py`.
2. Call `configure_logging()` from your `main.py` startup hook (or a `lifespan` context manager).
3. Confirm: a `log.info("server.started", port=8000)` call produces a single JSON object on stdout.

#### Step 2 — Add a middleware that binds a request ID and emits an access log

*`obs: add request-id middleware with bound logger`*

```python
# app/observability/middleware.py
import time
import uuid
from typing import Awaitable, Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

log = structlog.get_logger()

class RequestContextMiddleware(BaseHTTPMiddleware):
    """Bind a request_id, log when the request starts and finishes."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Clear any leftover context from a previous request in this worker
        structlog.contextvars.clear_contextvars()
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        start = time.perf_counter()
        log.info("request.received")

        try:
            response = await call_next(request)
        except Exception:
            log.exception("request.failed")
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            structlog.contextvars.bind_contextvars(duration_ms=round(duration_ms, 2))

        log.info(
            "request.finished",
            status_code=response.status_code,
        )
        response.headers["x-request-id"] = request_id
        return response
```

Wire it in `main.py`:

```python
from fastapi import FastAPI
from app.observability.logging import configure_logging
from app.observability.middleware import RequestContextMiddleware

configure_logging()
app = FastAPI()
app.add_middleware(RequestContextMiddleware)
```

**Step-by-step:**
1. Add the middleware to your app.
2. `curl -i http://localhost:8000/health` — the response has an `x-request-id` header. Every log line carries the same `request_id`.
3. Trigger a 500 by hitting a non-existent route after `app.debug = False` — the access log shows `status_code` and the duration.

#### Step 3 — Add Prometheus metrics for HTTP requests

*`obs: add http request metrics`*

```python
# app/observability/metrics.py
from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests handled",
    labelnames=("method", "path", "status"),
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=("method", "path"),
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

LLM_TOKENS = Counter(
    "llm_tokens_total",
    "LLM tokens consumed",
    labelnames=("model", "type"),  # type: input|output
)
```

```python
# app/observability/metrics_middleware.py
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.observability.metrics import HTTP_REQUESTS, HTTP_REQUEST_DURATION

class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        # Use the route template, not the raw URL — keeps cardinality low
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)

        HTTP_REQUESTS.labels(
            method=request.method,
            path=path,
            status=str(response.status_code),
        ).inc()
        HTTP_REQUEST_DURATION.labels(
            method=request.method,
            path=path,
        ).observe(duration)
        return response
```

Expose `/metrics` with `prometheus-fastapi-instrumentator` (it adds its own metrics, but the explicit counters above are clearer for the lab):

```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

**Step-by-step:**
1. Wire both middlewares. Order matters: request-context first, prometheus second, so duration measures the full app time.
2. `curl http://localhost:8000/metrics` — you should see `http_requests_total` and `http_request_duration_seconds` series.
3. Hit `/healthz` 20 times and confirm the counter ticks up.

#### Step 4 — Instrument the LLM call with token usage

*`obs: emit llm_tokens_total counter`*

```python
# app/llm/client.py
from app.observability.metrics import LLM_TOKENS
import structlog

log = structlog.get_logger()

def record_llm_usage(model: str, input_tokens: int, output_tokens: int) -> None:
    LLM_TOKENS.labels(model=model, type="input").inc(input_tokens)
    LLM_TOKENS.labels(model=model, type="output").inc(output_tokens)
    log.info(
        "llm.usage",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
```

```python
# Wherever you call the LLM
from app.llm.client import record_llm_usage

response = openai_client.chat.completions.create(...)
record_llm_usage(
    model=response.model,
    input_tokens=response.usage.prompt_tokens,
    output_tokens=response.usage.completion_tokens,
)
```

**Step-by-step:**
1. Wrap the LLM call so every completion records tokens.
2. `curl http://localhost:8000/metrics | grep llm_tokens_total` — you should see a new series.
3. Add a Grafana panel: `rate(llm_tokens_total{type="output"}[5m])` shows tokens per second.

#### Step 5 — Add a `/healthz` and a `/readyz`

*`obs: split liveness from readiness`*

```python
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/readyz")
def readyz():
    # Add real checks: DB reachable, cache reachable, model reachable
    try:
        db.execute("SELECT 1")
        return {"status": "ready"}
    except Exception:
        return Response(status_code=503, content="not ready")
```

**Step-by-step:**
1. `/healthz` answers "the process is alive" — never check downstream dependencies here.
2. `/readyz` answers "I can serve traffic right now" — check DB, cache, LLM provider.
3. K8s (and most orchestrators) treat a failing `/healthz` as a reason to restart the pod, and a failing `/readyz` as a reason to stop sending traffic. Conflating them causes restart loops.

#### Step 6 — Write a Prometheus alert file for the tracker

*`obs: add prometheus alert rules`*

```yaml
# ops/alerts.yml
groups:
  - name: tracker-slo
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m]))
            /
          sum(rate(http_requests_total[5m]))
            > 0.05
        for: 2m
        labels:
          severity: page
        annotations:
          summary: "HTTP 5xx rate above 5% for 2m"
          description: "5xx rate is {{ $value | humanizePercentage }}"

      - alert: HighP95Latency
        expr: |
          histogram_quantile(
            0.95,
            sum by (le, path) (rate(http_request_duration_seconds_bucket[5m]))
          ) > 1.0
        for: 5m
        labels:
          severity: warn
        annotations:
          summary: "p95 latency above 1s for 5m on {{ $labels.path }}"

      - alert: LLMTokensSpike
        expr: |
          sum(rate(llm_tokens_total[5m])) > 10000
        for: 10m
        labels:
          severity: warn
        annotations:
          summary: "LLM token rate above 10k tok/s"
          description: "Investigate runaway loops or large prompts"
```

**Step-by-step:**
1. Mount the rules file in `prometheus.yml`:
   ```yaml
   rule_files:
     - /etc/prometheus/alerts.yml
   ```
2. Restart Prometheus, then **Status → Rules** — your three rules should appear.
3. Trigger a 500 deliberately and watch the `HighErrorRate` alert enter "pending" then "firing".

#### Step 7 — Add a dashboard file (Grafana JSON or a text sketch)

*`obs: add grafana dashboard sketch`*

```json
{
  "title": "Tracker — SLO",
  "panels": [
    {
      "title": "Request rate (req/s)",
      "targets": [{"expr": "sum(rate(http_requests_total[1m]))"}],
      "type": "graph"
    },
    {
      "title": "Error rate (%)",
      "targets": [{"expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m))) / sum(rate(http_requests_total[5m]))"}],
      "type": "graph"
    },
    {
      "title": "p95 latency (s)",
      "targets": [{"expr": "histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))"}],
      "type": "graph"
    },
    {
      "title": "LLM tokens/s",
      "targets": [{"expr": "sum by (type) (rate(llm_tokens_total[1m]))"}],
      "type": "graph"
    }
  ]
}
```

**Step-by-step:**
1. Import the dashboard in Grafana (**+ → Import**).
2. Each panel should populate within 30 seconds if Prometheus is scraping successfully.
3. Add at least one alert derived from a panel — usually a copy of the `HighErrorRate` rule.

#### Step 8 — Add a smoke test that asserts JSON logs are emitted

*`obs: add tests for json logging and metrics`*

```python
# tests/test_observability.py
import io
import logging
import json

from app.observability.logging import configure_logging

def test_log_emits_json(capsys):
    configure_logging()
    log = structlog.get_logger()
    log.info("test.event", foo="bar")
    captured = capsys.readouterr()
    # The last line should be a JSON object
    last = captured.out.strip().splitlines()[-1]
    obj = json.loads(last)
    assert obj["event"] == "test.event"
    assert obj["foo"] == "bar"
    assert "timestamp" in obj
```

```python
# tests/test_metrics.py
from fastapi.testclient import TestClient
from app.main import app
from app.observability.metrics import HTTP_REQUESTS

def test_http_requests_counter_increments():
    before = HTTP_REQUESTS.labels(method="GET", path="/healthz", status="200")._value.get()
    client = TestClient(app)
    client.get("/healthz")
    after = HTTP_REQUESTS.labels(method="GET", path="/healthz", status="200")._value.get()
    assert after == before + 1
```

**Step-by-step:**
1. Add both tests, run with `uv run pytest -q`.
2. The metrics test is order-dependent when the app module is imported elsewhere — wrap the assertion in `try / finally` if you have flaky runs.
3. For a real suite, use `prometheus_client.REGISTRY` snapshots before/after, not `_value.get()`.

### Required Manual Tests

- [ ] Hit `/healthz` — the response includes an `x-request-id` header
- [ ] All log lines in stdout are valid JSON (one object per line)
- [ ] The same `request_id` appears on `request.received` and `request.finished`
- [ ] `curl http://localhost:8000/metrics` returns Prometheus exposition format
- [ ] `http_requests_total` and `http_request_duration_seconds` are present
- [ ] `llm_tokens_total` increments after a real LLM call
- [ ] Trigger a 500 — the alert expression in `ops/alerts.yml` evaluates to non-zero in Prometheus
- [ ] Tail stdout in `jq` and confirm you can filter on a `request_id` (`jq 'select(.request_id == "...") .event'`)

### Acceptance Criteria

- [ ] All logs are JSON, one per line, written to stdout
- [ ] `request_id` is generated if missing, preserved if present in `x-request-id`
- [ ] `request_id` is bound for the full request and cleared afterwards
- [ ] `/metrics` is exposed and contains at least: HTTP requests, HTTP duration, LLM tokens
- [ ] At least three alert rules are defined with `for:` durations
- [ ] Tests cover: JSON log shape, counter increments, request-id propagation
- [ ] No secrets (API keys, user prompts) appear in any log line
- [ ] At least 5 meaningful commits in the week
- [ ] You can explain the difference between a counter and a histogram, and the role of `rate()` in PromQL

## AI-Off Check (30 minutes)

**Without looking at your code**, write from memory:

1. A structlog configuration that emits JSON to stdout with timestamps
2. A Prometheus counter called `app_logins_total` with labels `success` (true/false)
3. A 3-line PromQL expression for the 5-minute rate of failed logins

```python
import structlog, sys
structlog.configure(processors=[structlog.processors.JSONRenderer()])
structlog.get_logger().info("login", user="u-1")
```

```python
from prometheus_client import Counter
LOGINS = Counter("app_logins_total", "Logins", labelnames=("success",))
LOGINS.labels(success="false").inc()
```

```promql
sum(rate(app_logins_total{success="false"}[5m]))
```

Write each piece cold, then diff against your working files. The point is to be able to read a log line in your head and write a counter that records the same thing.

## Reflection Questions

After you finish, write answers to these in `REFLECTION.md`:

1. Why bind `request_id` via `contextvars` instead of passing the logger as a parameter through every function?
2. Why is "label by `user_id`" a bad idea in Prometheus? What cardinality budget should you design for?
3. The `rate()` function in PromQL requires a counter. What happens if you apply it to a gauge? How would you know?
4. What is the difference between a log line and a metric? When would you choose one over the other?
5. If your service is silently producing 500s but your dashboards look fine, what is the most likely blind spot?

## Next Steps

Once you pass all acceptance criteria:

1. Record a 1-minute screen capture showing the Grafana dashboard populating live
2. Write the reflection answers
3. Commit with message: `docs: week 19 complete`
4. Move to Week 20 (Security)

---

**Ready?** Start by adding the deps:

```bash
uv add structlog prometheus-client prometheus-fastapi-instrumentator
```

Then build Step 1 and run your app — you should see JSON on stdout. Good luck! 🎯
