# Glossary: Forward-Deployed AI Engineer Terms

## Python & Software Engineering

**Async/await** — Python keywords for writing concurrent code. `async def` defines a coroutine; `await` pauses execution until an async operation completes.

**Dataclass** — A Python class decorator (@dataclass) that auto-generates `__init__`, `__repr__`, and other methods. Lighter weight than Pydantic for simple cases.

**Dependency injection** — Passing dependencies (like a repository) to a function or class rather than hardcoding them. Makes code testable.

**Enum** — A finite set of named values (e.g., `RequestStatus.OPEN`, `Priority.HIGH`). Type-safe alternative to strings.

**Fixture** — In pytest, a reusable setup function (decorated with `@pytest.fixture`) that creates test data or resources.

**Linting** — Automated code style checking (Ruff, pylint, flake8). Catches unused variables, inconsistent formatting, etc.

**Middleware** — Code that processes every request/response in a web framework (e.g., logging, auth, CORS).

**Mocking** — Replacing a real object with a fake one in tests so you control its behavior and inspect calls.

**Pydantic** — Python library for data validation using type hints. `BaseModel` ensures fields match declared types.

**Repository pattern** — A layer that abstracts data storage (JSON, database, API). Business logic depends on the interface, not the implementation.

**Type hint** — Annotation showing expected input/output types: `def greet(name: str) -> str: ...`

## Web & APIs

**CRUD** — Create, Read, Update, Delete. The four basic operations on data.

**FastAPI** — Modern Python web framework for building REST APIs. Auto-generates OpenAPI docs.

**HTTP** — HyperText Transfer Protocol. Methods: GET (retrieve), POST (create), PUT (replace), DELETE (remove).

**JSON** — JavaScript Object Notation. Lightweight data format: `{"key": "value", "count": 42}`.

**JWT (JSON Web Token)** — A compact token encoding identity claims. Used for authentication without sessions.

**OAuth** — A standard for delegated authorization. Let users log in via Google/Microsoft without sharing passwords.

**RBAC** — Role-Based Access Control. Users have roles (admin, engineer, customer); roles have permissions.

**REST** — Representational State Transfer. APIs using HTTP methods on resource URLs.

**Schema** — In databases, the structure of tables, columns, types, and constraints.

**SQLAlchemy** — Python ORM (Object-Relational Mapping). Maps Python classes to database tables.

## LLMs & AI

**Agent** — An AI system that iteratively reasons, calls tools, and takes actions toward a goal.

**Embeddings** — Vector representations of text. Similar concepts have similar vectors. Used for semantic search.

**Evaluation** — Measuring an LLM system's correctness, latency, cost, and safety.

**Fine-tuning** — Adapting a pre-trained model on your specific data. Expensive; use only when needed.

**Inference** — Running a trained model on new inputs to generate predictions.

**LLM** — Large Language Model. A neural network trained on vast text, good at prediction and reasoning tasks.

**Prompt** — The text instruction given to an LLM to generate a response.

**RAG** — Retrieval-Augmented Generation. Retrieve relevant documents, then feed them to an LLM for context.

**Structured output** — Constraining an LLM to return JSON or other structured formats (not free text).

**Temperature** — A parameter controlling randomness (0 = deterministic, 1+ = random).

**Token** — A unit of text the LLM processes. Roughly 4 characters or 1 word.

**Tool calling** — Letting an LLM decide when and how to call your APIs (functions) as part of reasoning.

## DevOps & Deployment

**CI/CD** — Continuous Integration / Continuous Deployment. Automated testing and deployment pipelines.

**Container** — A lightweight, isolated environment (Docker). Includes your app, dependencies, and runtime.

**Docker** — Platform for building and running containers. `Dockerfile` defines the image.

**Observability** — Ability to understand system behavior via logs, metrics, traces.

**Secrets** — Sensitive data (API keys, passwords). Never commit to git; use environment variables or secret managers.

**SQL** — Structured Query Language. Language for querying relational databases.

---

## Key Concepts from Your Learning Path

**Forward-Deployed Engineer (FDE)** — A role combining full-stack development, AI/ML, customer discovery, and infrastructure. You prototype, deploy, and iterate with customers.

**Layered architecture** — Separating concerns: CLI, services (business rules), repositories (data access), models (data shapes). Each layer has one job.

**Production-ready** — Code that handles errors, logs issues, has tests, doesn't leak secrets, and runs reliably.

**Evaluation-driven development** — Measuring your AI system's behavior before shipping. Test on real scenarios, not just "does it run?"

---

**Contributing to this glossary?** Open a PR with new terms and definitions as you encounter them!
