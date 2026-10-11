# Week 17: Docker and Containerization

## Outcome

Package the **Customer Engagement Tracker** app (the FastAPI service you built in Weeks 5–8 and hardened with LLM features in Week 16) into a **production-shaped container**, then run the whole stack — app + PostgreSQL + Redis — locally with `docker compose up`. By the end of the week you will have:

- A **multi-stage Dockerfile** that produces a runtime image < 250 MB starting from `python:3.13-slim`
- A **non-root user**, a **pinned base image**, and an **explicit `HEALTHCHECK`**
- A well-curated **`.dockerignore`** so the build context is fast and never leaks `.env`, `.venv`, or `.git`
- A **`docker-compose.yml`** that brings up app + postgres + redis with healthchecks, named volumes, and a single private network
- A **published image** (or a documented `docker load`/`save` round-trip) ready to be pushed to a registry
- A short README section that says, in one paragraph, what changed and how to verify it

A container that *runs* on your laptop is step one. A container that **runs on someone else's machine, in CI, and in a Kubernetes cluster** with the same behavior is step two — and that is what this week is really about.

## Setup Checklist

- [ ] Docker Engine 24+ and the `docker compose` plugin installed
- [ ] VS Code with the **Docker** extension (or `docker --help` on the terminal)
- [ ] Reuse the FastAPI app from Week 8 (or your Portfolio Project 1) — must run locally with `uv run uvicorn`
- [ ] The repo has a working `uv.lock`
- [ ] Confirm `docker run --rm hello-world` returns its "Hello from Docker" banner
- [ ] Confirm `docker compose version` (V2 plugin syntax, not `docker-compose` V1)

### Setup Walkthrough

```bash
# 1. Confirm Docker is alive
docker version
docker run --rm hello-world

# 2. Move into the project that ships the FastAPI app
cd /path/to/your/tracker     # the same repo from Weeks 5–8

# 3. Sanity-check the app builds and runs locally before you containerize it
uv sync
uv run pytest -q
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 &
sleep 2
curl -sS http://127.0.0.1:8000/health | head
kill %1

# 4. Create the docker housekeeping files
mkdir -p docker
touch .dockerignore Dockerfile docker-compose.yml
```

You should now have, at the repo root, the four files this week cares about:

```
.dockerignore
Dockerfile
docker-compose.yml
pyproject.toml
uv.lock
```

If any of those names looks like a placeholder, it is a placeholder — this lab writes them for real in the build steps below.

## Learning Path (60–90 minutes)

**Best approach:** Docker is mostly about **layers and caching**. Read the smallest Dockerfile that runs, then expand it one concern at a time: smaller base image, non-root user, multi-stage build, healthcheck, compose, registry. After each change, **measure the image size** with `docker images`.

### Learn in this order

1. **Image and layer model** — what an image is, what a layer is, why order matters
2. **Base image choices** — `python:3.13` vs `python:3.13-slim` vs `python:3.13-alpine` (size, glibc, debugging)
3. **Layer caching** — how Docker decides when a cache invalidates; why `COPY pyproject.toml uv.lock` must come before `COPY .`
4. **Multi-stage builds** — separating "build the wheel" from "ship the runtime"; why this matters for size and for security
5. **`.dockerignore`** — what is in your build context right now, and what should never make it
6. **Non-root user** — why `USER appuser` is a default, not an option
7. **Environment variables vs build args** — runtime vs build time, and which is which
8. **Healthchecks** — `HEALTHCHECK` in the Dockerfile vs `healthcheck:` in compose, and why both exist
9. **`docker compose`** — services, networks, volumes, healthchecks, dependency ordering
10. **Registries and image tags** — `docker tag`, `docker push`, `docker save/load`, semver-ish tags

### Free Resources

- [Docker Get Started](https://docs.docker.com/get-started/) — the official hands-on tour
- [Dockerfile reference](https://docs.docker.com/engine/reference/builder/) — every directive, with examples
- [Best practices for writing Dockerfiles](https://docs.docker.com/develop/develop-images/optimize/) — layer ordering, multi-stage, multi-arch
- [`docker compose` reference](https://docs.docker.com/compose/compose-file/) — every key, every shorthand, every healthcheck option
- [uv — Docker guide](https://docs.astral.sh/uv/guides/integration/docker/) — official uv + Docker pattern (this lab builds on it)
- [Play with Docker](https://labs.play-with-docker.com/) — a free browser-based Docker playground if your local Docker is broken

**Tip:** Build the image twice after every change. First build primes the cache; second build confirms your ordering decisions actually cache.

## Micro-Exercises (45–60 minutes)

Create `practice/` and work through these — each produces a working image you can inspect.

### Exercise 1 — Hello, world (single-stage)

```dockerfile
# practice/01-hello/Dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY hello.py ./
CMD ["python", "hello.py"]
```

```python
# practice/01-hello/hello.py
print("Hello from inside a container!")
```

```bash
cd practice/01-hello
docker build -t hello:01 .
docker run --rm hello:01
docker images hello:01   # note the size
```

**Step-by-step:**
1. `python:3.13-slim` is Debian without the build toolchain. About 120 MB base. Good default.
2. Every line in a Dockerfile is a layer. Six layers here, six pullable/runnable snapshots.
3. `CMD` is the default command; `docker run hello:01 echo bye` would override it.
4. `--rm` removes the container after exit; production containers will not use it.

### Exercise 2 — Multi-stage with a builder and a runtime

```dockerfile
# practice/02-multistage/Dockerfile
FROM python:3.13-slim AS builder
WORKDIR /build
COPY requirements.txt ./
RUN pip install --no-cache-dir --target=/install -r requirements.txt

FROM python:3.13-slim AS runtime
WORKDIR /app
COPY --from=builder /install /usr/local/lib/python3.13/site-packages
COPY hello.py ./
CMD ["python", "hello.py"]
```

```bash
cd practice/02-multistage
docker build -t hello:02 .
docker run --rm hello:02
docker images hello:02
# Compare the size to hello:01 — they should be similar because we are not
# actually pulling in extra deps, but the pattern is what matters.
```

**Step-by-step:**
1. The `builder` stage compiles dependencies; the `runtime` stage copies only the result.
2. Names after `AS` are your labels. They can be lowercase; convention is lowercase.
3. `pip install --target=/install` is a common pattern, but the modern style uses `--prefix` or `--user`. The uv-based pattern in Step 3 is cleaner.
4. Always end with the smallest possible `runtime` stage. Drop `pip`, `gcc`, `cargo`, etc. before you ship.

### Exercise 3 — Run as a non-root user

```dockerfile
# practice/03-nonroot/Dockerfile
FROM python:3.13-slim
WORKDIR /app
RUN groupadd --system appuser && useradd --system --gid appuser appuser
COPY hello.py ./
USER appuser
CMD ["python", "hello.py"]
```

```bash
cd practice/03-nonroot
docker build -t hello:03 .
docker run --rm hello:03 whoami   # prints: appuser
```

**Step-by-step:**
1. `--system` means "no password, no home, never logs in". The right default for an app user.
2. The `USER` directive must come **after** the COPY of the files the user needs to read; otherwise ownership is `root` and reads will fail.
3. Production workloads should refuse to start as root; the comment in your Dockerfile should say so plainly.
4. If a dependency refuses to run as non-root (rare), prefer fixing the dependency to relaxing the directive.

### Exercise 4 — A `.dockerignore` that is actually a `.dockerignore`

```text
# practice/04-ignore/.dockerignore
.git
.gitignore
.venv
__pycache__
*.pyc
.pytest_cache
.mypy_cache
.ruff_cache
.env
.env.*
!.env.example
README.md
tests
docs
.DS_Store
*.md.bak
```

```bash
cd practice/04-ignore
echo "print('hi')" > hello.py
docker build -t hello:04 .
docker run --rm --entrypoint ls hello:04 -la /app
# Notice that .git, .venv, .pytest_cache are NOT there — they were filtered out.
```

**Step-by-step:**
1. `.dockerignore` controls the **build context**, not the image. Files excluded here never reach `docker build` at all.
2. The single biggest speedup: exclude `.git`, `.venv`, and `node_modules` from every build.
3. `!.env.example` uses the negation syntax to keep the example file even though `.env.*` excludes everything matching the prefix.
4. Add `.dockerignore` reviews to your code-review checklist; missing entries leak secrets more often than people think.

### Exercise 5 — Layer caching that actually works

```dockerfile
# practice/05-cache/Dockerfile
FROM python:3.13-slim
WORKDIR /app
# 1. Install dependencies FIRST, and only when these files change.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# 2. THEN copy source — changes here do not invalidate the install layer.
COPY . ./
CMD ["python", "hello.py"]
```

```bash
cd practice/05-cache
echo "fastapi==0.115.0" > requirements.txt
echo "print('v1')"  > hello.py
docker build -t hello:05 .
echo "print('v2')" > hello.py
docker build -t hello:05 .
# Second build reuses every layer until the COPY.
# Now change requirements.txt; the install layer invalidates.
```

**Step-by-step:**
1. Order: copy **what changes least** first, **what changes most** last. `requirements.txt` rarely changes; source code changes every commit.
2. With `uv sync --frozen` in Step 6, your equivalent of `requirements.txt` is `pyproject.toml` + `uv.lock`.
3. The discipline is painful but the prize is real: a content-only change rebuilds in seconds, not minutes.
4. If a layer does *exactly* what you expect but does not cache, you probably forgot a `&&` and rebuilt too early.

### Exercise 6 — `HEALTHCHECK` directive

```dockerfile
# practice/06-healthcheck/Dockerfile
FROM python:3.13-slim
RUN groupadd --system appuser && useradd --system --gid appuser appuser
WORKDIR /app
RUN pip install --no-cache-dir fastapi==0.115.0 uvicorn==0.30.6 httpx==0.27.2
COPY app.py ./
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://127.0.0.1:8000/health', timeout=2).raise_for_status()" || exit 1
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

```python
# practice/06-healthcheck/app.py
from fastapi import FastAPI
import time, socket

app = FastAPI()
STARTED_AT = time.time()

@app.get("/health")
def health():
    return {"status": "ok", "uptime_s": int(time.time() - STARTED_AT),
            "host": socket.gethostname()}
```

```bash
cd practice/06-healthcheck
docker build -t hello:06 .
docker run -d --name h6 -p 8000:8000 hello:06
sleep 2
docker ps                                # STATUS shows "(healthy)" after a few seconds
docker inspect --format '{{.State.Health.Status}}' h6
docker rm -f h6
```

**Step-by-step:**
1. `--start-period` gives the app time to boot before failed healthchecks count against it.
2. `HEALTHCHECK` itself does not restart anything — `docker compose` and Kubernetes do, when they see the unhealthy status.
3. Pair a `HEALTHCHECK` in the Dockerfile with a `healthcheck:` in compose. The Dockerfile one runs even when the container is started without compose.
4. The check should hit the *real* readiness endpoint (`/health`), not a TCP connect. A socket-accept does not prove your code runs.

### Exercise 7 — `ARG` vs `ENV` (build-time vs runtime)

```dockerfile
# practice/07-args/Dockerfile
FROM python:3.13-slim
ARG APP_VERSION=0.0.0
ENV APP_VERSION=$APP_VERSION
WORKDIR /app
COPY hello.py ./
CMD ["sh", "-c", "echo running version $APP_VERSION && python hello.py"]
```

```bash
cd practice/07-args
docker build -t hello:07 --build-arg APP_VERSION=1.2.3 .
docker run --rm hello:07
# Build arg was baked into the image. Now try overriding at runtime:
docker run --rm hello:07 sh -c "echo runtime APP_VERSION=$APP_VERSION"
# $APP_VERSION is still 1.2.3 — once baked, ENV is fixed.
```

**Step-by-step:**
1. `ARG` is available **only during the build**. Use it for things that influence `RUN` (compiler flags, repo URLs, lockfile refs).
2. `ENV` is available **at runtime** AND `docker run -e KEY=value` can override it (unless `docker run --read-only` is also given with `secrets`).
3. The classic pattern: `ARG GIT_SHA` set from `--build-arg`, then `ENV GIT_SHA=$GIT_SHA`, then `CMD` echoes it on every boot so logs tell you exactly which commit is running.
4. **Secrets are `ENV` calls with your secrets exposed** to anyone with `docker history`. The answer is `--mount=type=secret` for build-time, and runtime secrets for runtime.

### Exercise 8 — Inspecting the resulting image

```bash
cd practice/01-hello
docker build -t inspect-me .
docker save inspect-me -o /tmp/inspect-me.tar
ls -lh /tmp/inspect-me.tar         # file size on disk
tar -tf /tmp/inspect-me.tar | head  # layers
```

```bash
# What changed in a layer? Run this after a couple of rebuilds.
docker history inspect-me --no-trunc
```

```bash
# Shell into a running container (for debugging only — never in prod).
docker run --rm -it inspect-me sh
```

**Step-by-step:**
1. `docker history` shows every layer and its size. Big layers mean big wins for reordering.
2. `docker save` produces a portable `.tar` you can `docker load` on another machine — useful for air-gapped clusters and the first time you push somewhere weird.
3. Trivy, Syft, and `dive` (https://github.com/wagoodman/dive) take this further — they show the *contents* of each layer. `dive inspect-me` is worth your time.
4. The shell in step 3 is not for everyday use; it is for the 02:00 incident when something just isn't running.

---

## Main Lab: Production Container Stack for the Engagement Tracker (4–5 hours)

### Scenario

You are taking the Customer Engagement Tracker (Weeks 5–8) and packaging it for shipping. The goals of this lab are:

- One `Dockerfile`, multi-stage, non-root, healthcheck, < 250 MB
- One `docker-compose.yml` that brings up `app + postgres + redis` on a single private network with healthchecks and named volumes
- One `.dockerignore` that shields secrets and virtualenvs
- A reproducible build that runs the same on your laptop, in CI, and (after a registry push) on any cluster

### Target File Layout

```
.dockerignore
Dockerfile
docker-compose.yml
docker/
  README.md          # local-only notes about the stack
app/
  main.py            # the existing FastAPI app
  ...
pyproject.toml
uv.lock
```

### Build Steps

**Commit after each step.** Use messages like:
- `feat: dockerfile multi-stage build`
- `feat: docker-compose with postgres + redis`
- `feat: non-root user and healthcheck`
- `feat: dockerignore and image size budget`
- `ci: docker build smoke test`

#### Step 1 — A `.dockerignore` that never leaks secrets

*`chore: dockerignore shields secrets and build artefacts`*

```text
# .dockerignore (root of the repo)

# Git and CI metadata
.git
.gitignore
.gitattributes
.github

# Build / virtualenv / test caches
.venv
venv
__pycache__
*.pyc
*.pyo
*.pyd
.pytest_cache
.mypy_cache
.ruff_cache
.coverage
.coverage.*
htmlcov/
dist/
build/
*.egg-info/

# Secrets
.env
.env.*
!.env.example

# Local dev notes
README.md
*.md.bak
.DS_Store
.idea
.vscode
```

```bash
# Verify the build context size
docker build -t tracker:context-test . -f Dockerfile.dev-only 2>&1 | head
# (The -f Dockerfile.dev-only above is a stand-in if your real Dockerfile does not exist yet.)
# A healthy context is tens of MB. If you see >500 MB, .dockerignore is broken.
```

**Step-by-step:**
1. The longest single line in the file is `!/.env.example` — keep one example file so devs know the keys.
2. `.git` is the most common culprit. A fresh clone is fine; a working tree with hundreds of stashed branches is not.
3. Treat `.dockerignore` like a security review. A missing line can publish a customer's API key.
4. Add a CI check that prints `du -sh` of the build context and fails above 200 MB.

#### Step 2 — A minimal single-stage Dockerfile (sanity check)

*`feat: dockerfile single-stage hello-world shape`*

This stage exists to confirm the toolchain works end-to-end before you start optimising.

```dockerfile
# Dockerfile (initial sketch — Step 3 replaces this with a multi-stage build)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev
COPY app ./app

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t tracker:stage-2 .
docker run --rm -p 8000:8000 tracker:stage-2 &
sleep 5
curl -sS http://127.0.0.1:8000/health
kill %1
docker images tracker:stage-2   # expect ~700-900 MB at this stage
```

**Step-by-step:**
1. `PYTHONDONTWRITEBYTECODE=1` keeps `__pycache__` out of the image. Without it you ship compiled bytecode for nothing.
2. `PYTHONUNBUFFERED=1` flushes stdout on every write — without it, container logs lag in unreadable batches.
3. `uv sync --frozen` uses the committed lockfile — same bit-for-bit install as CI.
4. The size at this stage is fine. Step 3 is the one that shrinks it; do not skip ahead.

#### Step 3 — A real multi-stage build

*`feat: dockerfile multi-stage with non-root user`*

```dockerfile
# syntax=docker/dockerfile:1.7
# ---- builder --------------------------------------------------------------
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

WORKDIR /build

# Install uv first — this layer only invalidates when the uv version changes.
RUN pip install --no-cache-dir uv==0.4.30

# Then the dep manifests. This layer only invalidates when pyproject/uv.lock changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Then source. This layer invalidates on every code change.
COPY app ./app
RUN uv sync --frozen --no-dev


# ---- runtime --------------------------------------------------------------
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Create a non-root user first so layer ownership is correct on first COPY.
RUN groupadd --system appuser \
 && useradd  --system --gid appuser --create-home --shell /sbin/nologin appuser

WORKDIR /app

# Copy the prepared virtualenv and the app source from the builder.
COPY --from=builder --chown=appuser:appuser /build/.venv ./app
# Note: uv sync creates .venv; for typical layouts you may need to re-point. The
# pattern below copies the whole project at /build into /app with the venv
# embedded.

# Expose and run
EXPOSE 8000
USER appuser
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import os, sys, urllib.request; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t tracker:stage-3 .
docker run --rm -p 8000:8000 tracker:stage-3 &
sleep 5
curl -sS http://127.0.0.1:8000/health
kill %1
docker images tracker:stage-3     # expect < 250 MB
docker run --rm --entrypoint whoami tracker:stage-3   # expect: appuser
docker inspect --format '{{.State.Health.Status}}' $(docker run -d --name t3 -p 8001:8000 tracker:stage-3)
sleep 3 && docker ps               # STATUS shows "(healthy)"
docker rm -f t3
```

**Step-by-step:**
1. `syntax=docker/dockerfile:1.7` opts into the modern parser — none of the directives above require it, but it future-proofs the file.
2. `UV_LINK_MODE=copy` is the easiest way to make `uv sync` cooperate with mounted filesystems inside Docker.
3. The `USER appuser` directive **must come after** the last `COPY` that writes files the user needs to read. If you put it before, every file is owned by `root` and `appuser` cannot read them.
4. The `HEALTHCHECK` references `/health`. If your app does not have one, add it before this step — Week 19 will treat observability as a first-class concern.
5. The size budget is the visible constraint. The pattern that gets you under 250 MB is "slim base + uv slim + no pip cache + no compilers in the runtime stage".

**A cleaner runtime stage (matches uv's official Docker guide):**

If your project puts code in `app/` and `uv` creates `.venv/` at the project root, this is the layout that works without surprises:

```dockerfile
# Builder
FROM python:3.13-slim AS builder
WORKDIR /build
RUN pip install --no-cache-dir uv==0.4.30
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev
COPY app ./app
RUN uv sync --frozen --no-dev

# Runtime
FROM python:3.13-slim AS runtime
ENV PYTHONUNBUFFERED=1 PATH="/build/.venv/bin:$PATH"
RUN groupadd --system appuser && useradd --system --gid appuser --no-log-init appuser
WORKDIR /build
COPY --from=builder --chown=appuser:appuser /build /build
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status==200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

The `.venv` lives *in* `/build`, and the runtime stage copies the entire prepared directory. The `PATH=.../build/.venv/bin` is the magic that makes `uvicorn` resolvable.

#### Step 4 — Pin versions and add build args

*`chore: pin base images and thread GIT_SHA`*

```dockerfile
# Add near the top of each FROM:
FROM python:3.13.0-slim-bookworm AS builder
# ...
FROM python:3.13.0-slim-bookworm AS runtime
# ...
```

```dockerfile
# Build arg pattern at the very top of the file:
ARG APP_VERSION=dev

# And inside the runtime stage, expose it for log lines:
ENV APP_VERSION=${APP_VERSION}
CMD ["sh", "-c", "echo \"tracker ${APP_VERSION} starting on $(hostname)\" && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

```bash
# Pass the build arg from your CI
GIT_SHA=$(git rev-parse --short HEAD)
docker build -t tracker:$GIT_SHA --build-arg APP_VERSION=$GIT_SHA .
docker run --rm tracker:$GIT_SHA | head -2   # shows the version on boot
```

**Step-by-step:**
1. Pin both `3.13.0` and the Debian variant (`bookworm`). Floating tags like `3.13-slim` are technically allowed to change overnight.
2. Build args cannot be used at runtime — bake them with `ENV` so `CMD` can read them.
3. The `hostname` in the echo is what your log search will key on later (`hostname=trk-7b3…`).
4. If your CI does not pass a SHA, the default `dev` keeps local builds working without flag-passing.

#### Step 5 — The `docker-compose.yml`

*`feat: compose stack with app + postgres + redis`*

```yaml
# docker-compose.yml
name: tracker

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        APP_VERSION: ${APP_VERSION:-dev}
    image: tracker:local
    environment:
      DATABASE_URL: postgresql+psycopg://tracker:tracker@db:5432/tracker
      REDIS_URL: redis://cache:6379/0
      OPENAI_API_KEY: ${OPENAI_API_KEY:?OPENAI_API_KEY must be set}
      PRIMARY_MODEL: gpt-4o-mini
      FALLBACK_MODEL: gpt-3.5-turbo
      DAILY_BUDGET_USD: "5.00"
      APP_VERSION: ${APP_VERSION:-dev}
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_healthy
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "python", "-c",
             "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status==200 else 1)"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 15s
    restart: unless-stopped
    networks: [tracker]

  db:
    image: postgres:16.4-alpine
    environment:
      POSTGRES_USER: tracker
      POSTGRES_PASSWORD: tracker
      POSTGRES_DB: tracker
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U tracker -d tracker"]
      interval: 5s
      timeout: 3s
      retries: 10
    restart: unless-stopped
    networks: [tracker]

  cache:
    image: redis:7.4-alpine
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - cache-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10
    restart: unless-stopped
    networks: [tracker]

volumes:
  db-data:
  cache-data:

networks:
  tracker:
    driver: bridge
```

```bash
# Set the secret(s) for this shell
export OPENAI_API_KEY=sk-......h

# Bring up the stack and watch the order of healthy events
docker compose up -d --build
docker compose ps                 # STATUS shows healthy within ~30 seconds
docker compose logs -f app        # press Ctrl-C when you have seen enough
curl -sS http://127.0.0.1:8000/health
docker compose down -v            # tear down, removing volumes
```

**Step-by-step:**
1. `depends_on.condition: service_healthy` is what makes `db` and `cache` actually *ready* before `app` starts — without it, `app` will race against a still-bootstrapping Postgres.
2. `name: tracker` namespaces the compose project, volumes, and network. Two side-by-side projects can both run without colliding.
3. `${OPENAI_API_KEY:?…}` fails the shell with a clear message if the variable is missing — Docker does not read your shell history for you.
4. The Compose `healthcheck` is duplicated with the Dockerfile `HEALTHCHECK`. Both are needed; the compose one drives `depends_on`, the Dockerfile one drives `docker ps`.
5. `redis-server --appendonly yes` turns on AOF persistence — without it, a `docker compose restart` loses your cache. For real workloads, swap to a managed Redis.
6. Postgres data lives in a **named volume**, not a bind mount, so backups and image bakes stay clean. Bind-mount only if you specifically want to edit files on the host.
7. Tear down with `down -v` when you are done; `-v` removes the volumes so the next `up` starts clean.

#### Step 6 — Run the tests inside the container

*`test: app-level tests inside container with compose`*

```yaml
# Add this as a new service in docker-compose.yml
  test:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        APP_VERSION: test
    image: tracker:local
    environment:
      DATABASE_URL: postgresql+psycopg://tracker:tracker@db:5432/tracker_test
      REDIS_URL: redis://cache:6379/1
    command: ["uv", "run", "pytest", "-q"]
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_healthy
    networks: [tracker]
    profiles: ["test"]        # only runs with --profile test
```

```bash
# Bring up the test database, run pytest inside the same image as production
docker compose --profile test up -d db cache
docker compose --profile test run --rm test
docker compose --profile test down -v
```

**Step-by-step:**
1. The `test` service uses the **same Dockerfile** as production — same `.venv`, same OS packages. What works in tests will work in production.
2. `profiles: ["test"]` makes the service opt-in. Without it, plain `docker compose up` would also start the test runner.
3. `--profile test run --rm test` is the right one-shot shape: compose pulls up the deps, runs the command in a new container attached to the same network, throws the test container away.
4. The URL points to a *different* database (`tracker_test`) and a *different* Redis DB index (`/1`) so tests cannot accidentally clobber development data.
5. In Week 18 this same pattern becomes a `pytest` job in CI — but the cache and the db already exist as services, so the only new thing is the runner image.

#### Step 7 — A development override file

*`feat: docker-compose.override.yml for hot reload`*

`docker-compose.override.yml` is auto-merged by Compose. The base file ships to CI; the override stays in your local repo (or `.gitignore`-d if you prefer).

```yaml
# docker-compose.override.yml  (auto-applied in development)
services:
  app:
    command: ["uv", "run", "uvicorn", "app.main:app",
              "--host", "0.0.0.0", "--port", "8000", "--reload"]
    volumes:
      - ./app:/build/app:ro       # bind-mount source for hot reload
    environment:
      APP_VERSION: dev-local
    ports:
      - "8000:8000"
```

```bash
docker compose up -d --build
curl -sS http://127.0.0.1:8000/health
# Edit app/main.py — uvicorn reloads within ~1 second.
docker compose down
```

**Step-by-step:**
1. `--reload` watches for file changes and re-executes the server. Use it *only* in development; production runs the un-reloaded command.
2. Bind-mounting `./app:/build/app:ro` lets you edit code without rebuilding the image. `:ro` (read-only) prevents the container from quietly modifying your source.
3. CI never sees this file unless you `cp docker-compose.override.yml …` it explicitly. Your base compose is the source of truth.
4. If you keep this file in `.gitignore`, your team reproduces your local setup only by talking to you — keep it in git.

#### Step 8 — Build, tag, push, save

*`docs: image lifecycle commands`*

```bash
# Build the production image locally and tag it
docker build -t tracker:1.0.0 --build-arg APP_VERSION=1.0.0 .

# Inspect what is inside
docker images tracker:1.0.0
docker history tracker:1.0.0 --no-trunc | head

# Save for an air-gapped environment
docker save tracker:1.0.0 | gzip > tracker-1.0.0.tar.gz
ls -lh tracker-1.0.0.tar.gz

# Load on another machine
gzip -dc tracker-1.0.0.tar.gz | docker load
docker images | grep tracker

# Push to a registry (replace with your actual registry)
# docker tag tracker:1.0.0 ghcr.io/<you>/tracker:1.0.0
# docker login ghcr.io
# docker push ghcr.io/<you>/tracker:1.0.0
```

**Step-by-step:**
1. Save is the fallback when push isn't an option. The `tar.gz` is a single file you can hand to a colleague or attach to a release.
2. Always tag with both a version (`1.0.0`) **and** the SHA (`1.0.0-abc1234`) when pushing; human eyes need the first, automation needs the second.
3. Check `docker history` for "unexpected" large layers. A 600 MB layer is usually a debugging tool that snuck in.
4. GitHub Container Registry (`ghcr.io`) is free for public images and a sensible default for solo portfolios. Docker Hub is fine too. ECR/GAR come later.

#### Step 9 — Document in the project `README.md`

*`docs: docker section in README`*

```markdown
# Customer Engagement Tracker

... (existing content) ...

## Run with Docker

    cp .env.example .env       # then fill in OPENAI_API_KEY
    export $(grep -v '^#' .env | xargs)
    docker compose up -d --build
    curl -sS http://127.0.0.1:8000/health

The first build takes 2–4 minutes (uv compiles wheels). Subsequent builds
reuse layers until you change `pyproject.toml` or `uv.lock`.

## Tear down

    docker compose down -v

The `-v` flag removes the named volumes (Postgres data, Redis AOF). Use it
when you want a clean slate.

## Run the test suite against real Postgres + Redis

    docker compose --profile test run --rm test
```

**Step-by-step:**
1. The two-command contract (`up` and `down -v`) is what teammates will copy-paste. Anything beyond that is a recipe for confusion.
2. Mention the first-build time. Docker's slowness on a cold build is the #1 surprise.
3. Document the `profile test` flag. Out-of-sight opt-in services cause "I forgot tests existed" debugging.
4. If you have a CI badge, add it under this section in a later week — Docker + CI is the topic of Week 18.

#### Step 10 — Smoke test the whole stack

*`test: end-to-end smoke against compose stack`*

```bash
# Bring everything up and verify
docker compose up -d --build
sleep 10

# 1. Containers are healthy
docker compose ps

# 2. App health endpoint
curl -fsS http://127.0.0.1:8000/health | jq

# 3. Postgres reachable from the app
docker compose exec db psql -U tracker -d tracker -c "select 1;"

# 4. Redis reachable from the app
docker compose exec cache redis-cli ping

# 5. End-to-end request that exercises both
curl -fsS -X POST http://127.0.0.1:8000/chat \
  -H 'content-type: application/json' \
  -d '{"user_id": "smoke", "message": "hello"}' | jq

# 6. Tear down
docker compose down -v
```

**Step-by-step:**
1. `docker compose ps` shows `(healthy)` on all three services within ~30 seconds.
2. `psql -U tracker -d tracker` proves the credential round-trip works. If this fails, your `DATABASE_URL` is wrong.
3. `redis-cli ping` returns `PONG`. If it returns `Could not connect`, your `REDIS_URL` host is wrong (`cache`, not `localhost`).
4. The `/chat` call proves the app reaches **both** db and cache *and* the LLM client. If LLM is not configured, expect a 500 — that is still a successful "the wiring works" test.

### Required Manual Tests

Before you consider Week 17 done, run all of the following on a clean shell:

- [ ] `docker version` shows Engine 24+ and the Compose V2 plugin
- [ ] `docker compose -f docker-compose.yml config` validates (no `ERROR:` lines)
- [ ] `docker build -t tracker:full .` finishes and `docker images tracker:full` reports a size under 250 MB
- [ ] `docker run --rm --entrypoint whoami tracker:full` prints `appuser`, not `root`
- [ ] `docker run --rm tracker:full` exits 0 with the boot log showing `tracker <APP_VERSION> starting on …`
- [ ] `docker compose up -d --build` brings all three services to `(healthy)` within 30 seconds
- [ ] `curl http://127.0.0.1:8000/health` returns a JSON `{"status":"ok",...}` payload
- [ ] `docker compose exec db psql -U tracker -d tracker -c 'select 1'` prints `1`
- [ ] `docker compose exec cache redis-cli ping` prints `PONG`
- [ ] After editing `app/main.py`, the dev override reloads the server without a rebuild
- [ ] `docker compose down -v` cleans up; a second `up -d` produces a fresh, working stack
- [ ] `docker save tracker:1.0.0 | gzip > tracker-1.0.0.tar.gz` produces a file you can load on another machine

### Acceptance Criteria

- [ ] `.dockerignore` excludes `.git`, `.venv`, `.env`, `__pycache__`, and `*.pyc`
- [ ] `Dockerfile` is multi-stage with a named `builder` and `runtime` stage
- [ ] Runtime base is `python:3.13.x-slim` (pinned to a patch version)
- [ ] Final image runs as non-root user `appuser`
- [ ] Final image size < 250 MB for a FastAPI app with `uvicorn`, `fastapi`, `pydantic`, `sqlalchemy`, `psycopg`, `redis`
- [ ] `HEALTHCHECK` directive is present and references the app's `/health` endpoint
- [ ] `docker compose up -d --build` brings up `app + db + cache` and all reach `(healthy)` without manual intervention
- [ ] `depends_on.condition: service_healthy` gates the `app` service on both `db` and `cache`
- [ ] Postgres data and Redis AOF live in named volumes, not bind mounts
- [ ] A `test` service exists, gated by `--profile test`, that runs pytest against the same image
- [ ] A `docker-compose.override.yml` (or equivalent) enables hot reload for local dev
- [ ] The project README has a "Run with Docker" section with `up -d --build`, `down -v`, and the test profile
- [ ] At least 5 meaningful commits in the week (one per build step is fine)
- [ ] You can explain *why* the dep-install layer comes before the source-COPY layer
- [ ] You can explain the difference between `Dockerfile`'s `HEALTHCHECK` and compose's `healthcheck:`, and which one drives `docker ps` status

## AI-Off Check (30 minutes)

**Without looking at your Dockerfile**, write from memory a multi-stage Dockerfile that:

1. Uses `python:3.13-slim` for both stages
2. Installs `uv` in the builder stage
3. Copies `pyproject.toml` and `uv.lock` first, runs `uv sync --frozen --no-dev`
4. Then copies the `app/` source
5. In the runtime stage, creates a non-root `appuser`
6. Copies the prepared `.venv` and the source from the builder
7. Sets `CMD` to run `uvicorn`
8. Includes a `HEALTHCHECK` that hits `/health`

```dockerfile
# Dockerfile — fill in cold
FROM python:3.13-slim AS builder
# ...

FROM python:3.13-slim AS runtime
# ...
```

Compare against your working file. The goal is to internalize the **shape**:

builder → install tools → copy manifests → uv sync → copy source → uv sync again  
runtime → non-root user → copy artifacts → USER → HEALTHCHECK → CMD

Everything else is variation on that skeleton.

## Reflection Questions

After you finish, write answers to these in `REFLECTION.md`:

1. Why does the dep-install layer come **before** the source-COPY layer in the builder stage? What does that ordering actually buy you, in seconds, on a content-only change?
2. When would you choose `python:3.13-slim` over `python:3.13-alpine`? What does Alpine break?
3. Your runtime stage contains a `COPY --from=builder` of `~120 MB` of `.venv`. Why is that fine on disk but a hazard in a CI registry?
4. The compose file uses `depends_on.condition: service_healthy`. What does this *not* protect you from that application-level retries do?
5. Your Postgres data is in a named volume. What is the difference between that volume and a bind mount, and which is correct for *CI* and which is correct for *local development*?
6. If your image grows past the 250 MB budget, what is the first lever you pull, and what is the second?

## Next Steps

Once you pass all acceptance criteria:

1. Run `docker compose up -d --build && curl -sS http://127.0.0.1:8000/health && docker compose down -v` and commit the working config
2. Write the reflection answers
3. Commit with message: `docs: week 17 complete`
4. Move to Week 18 (CI/CD with GitHub Actions) — that workflow will build this image on every push

---

**Ready?** Start by running:

```bash
docker version
mkdir -p docker
touch .dockerignore Dockerfile docker-compose.yml
```

Then follow the build steps above. Good luck! 🎯
