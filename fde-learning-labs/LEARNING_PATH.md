# Forward-Deployed AI Engineer: 24-Week Learning Path

## The Goal

Become competitive for **AI forward-deployed engineer (FDE)**, **applied AI engineer**, and **AI solutions engineer** roles by building and deploying real systems—not by collecting certificates.

This plan is tailored to someone with experience in **solution architecture, customer delivery, SQL, JavaScript, ALM, governance**, but needing deeper **Python, full-stack, AI-system, and production deployment** skills.

### Default Pace
- **8–10 hours per week**
- **24 weeks total**
- If 5 hours/week: 9–10 months
- If 12–15 hours/week: ~4 months

---

## What Real FDEs Do

Current FDE roles (OpenAI, Anthropic, Palantir) emphasize:

1. **Discovering** a customer's real workflow and defining measurable success
2. **Prototyping quickly**, then turning the prototype into stable production
3. **Writing production-grade Python and JavaScript** across backend and frontend
4. **Integrating models** with customer data, APIs, databases, identity, and infrastructure
5. **Evaluating model behavior** — reliability, latency, safety, cost
6. **Communicating tradeoffs** to engineers, business owners, and executives
7. **Converting one-off work** into reusable tools and patterns

Success requires **full-stack delivery**, **customer embedding**, **Python/JavaScript fluency**, **LLM deployment**, **scoping**, and **reusable playbooks**.

---

## Your Advantages & Gaps

### Skills That Already Transfer

✅ Solution architecture and ambiguous requirements  
✅ Customer-facing technical delivery  
✅ Power Platform governance, RBAC, ALM, regulated work  
✅ SQL, JavaScript, APIs, Azure DevOps, automation  
✅ Translating between technical and nontechnical stakeholders

### Skills to Build Deliberately

❌ **Production Python** and software-engineering fluency  
❌ **Backend API** and relational-database development  
❌ **LLM APIs** — structured output, tool calling, retrieval, agents  
❌ **Evaluation-driven AI** — measuring system behavior  
❌ **Docker, CI/CD, cloud deployment**, observability, infrastructure  
❌ **Coding interviews** and live problem-solving without AI  
❌ **Portfolio proof** — discovery-to-production delivery

**Note:** You do NOT need to become an ML researcher. Learn enough ML to reason about embeddings, inference, model selection, evaluation, and failure modes. Skip deep learning and foundation model training for now.

---

## How to Learn Each Week: 20/70/10 Split

```
20% LEARN      | 70% BUILD      | 10% EXPLAIN
documentation  | write the      | demo, README,
short lesson   | project        | state tradeoffs
one chapter    | debug          |
               | test           |
```

### Suggested Weekly Schedule

| Session | Time | Activity |
|---------|------|----------|
| 1 | 90 min | Learn concepts, make a tiny example |
| 2 | 2 hrs | Build main feature |
| 3 | 2 hrs | Continue building, debug |
| 4 | 2 hrs | Add tests, errors, logging, docs |
| 5 | 1–2 hrs | Demo, retrospective, interview question |

### Rules for Using ChatGPT Plus and Claude Pro

Use them as **tutors, reviewers, and simulated customers**—not as code generators.

1. **Attempt the problem** for 20–30 minutes first
2. **Ask for a hint** or explanation before asking for complete code
3. **Type or deliberately adapt** the code yourself
4. **Explain every file** and important function in your own words
5. **Do not call a lab complete** until tests pass and you can rebuild the key part without AI
6. **Once per week**, do a 45-minute "AI-off" coding session

**Useful escalation prompts:**
- "Do not write the solution. Ask me questions and give one hint at a time."
- "Review this as a senior engineer. Identify the three highest-risk issues."
- "Act as a skeptical customer and challenge my assumptions and metrics."
- "Give me a failing test for this behavior, but let me implement the fix."
- "Interview me about this architecture and press me on tradeoffs."

---

## Cost-Conscious Tool Stack

All of these have **$0 additional cost** except where noted:

| Need | Recommended | Cost |
|------|-------------|------|
| Editor | VS Code | $0 |
| Language | Python 3.12+, TypeScript | $0 |
| Env manager | `uv` | $0 |
| Source control | Git + GitHub | $0 |
| Backend | FastAPI + Pydantic | $0 |
| Testing | pytest, Ruff, mypy | $0 |
| Database | SQLite → PostgreSQL | $0 (local) |
| Containers | Docker Desktop | $0 |
| Local LLMs | Ollama | $0 |
| CI/CD | GitHub Actions | $0 (public repos) |
| API testing | VS Code REST Client or Bruno | $0 |
| AI tutor | ChatGPT Plus / Claude Pro | Already paid |

**Spending policy:**
- **Weeks 1–8:** $0 additional. Use stubs and local models.
- **Weeks 9–16:** $5–$10 total, hard alerts set.
- **Weeks 17–24:** $10–$20/month max for portfolio benchmarking only.

Use the cheapest capable model for routine calls. Cache responses during development. Keep model names behind one adapter so you can switch providers.

**Never send employer, patient, federal, or customer data to personal AI accounts. Use synthetic data.**

---

## The 24-Week Path

### Phase 1: Python & Engineering Foundations (Weeks 1–4)

#### Week 1: Python Essentials and Developer Workflow
- **Learn:** Variables, collections, control flow, functions, modules, git, basic type hints
- **Lab:** **Customer Request Tracker CLI** — add, list, update, close requests in JSON
- **Definition of done:** Runs from terminal, clear README, handles bad input, you explain basics

#### Week 2: Python Data Modeling and Clean Code
- **Learn:** Classes, dataclasses, Pydantic, exceptions, file I/O, comprehensions, Ruff/mypy
- **Lab:** Refactor tracker into **layered architecture** (models, services, repositories, CLI)
- **Add:** CSV import/export, typed models

#### Week 3: Testing and Debugging
- **Learn:** pytest, fixtures, parametrized tests, mocks, unit vs. integration, logging
- **Lab:** **Test suite for the layered tracker** — cover business rules, edge cases
- **Add:** Regression tests, structured logging, deliberate defects caught by tests

#### Week 4: HTTP, APIs, Async, and Resilience
- **Learn:** HTTP methods/status, JSON, httpx, error handling, retries, async/await basics
- **Lab:** Integrate external API with **timeouts, retries, validation, mocking**
- **Add:** Environment variables for secrets, CLI health check

**Phase 1 Gate:** Build a typed Python program from scratch, test it, debug it, explain it—no tutorials.

---

### Phase 2: Production Backend & Data (Weeks 5–8)

#### Week 5: FastAPI
- Turn the tracker into a **REST API**
- CRUD endpoints, Pydantic models, validation, consistent errors, OpenAPI docs

#### Week 6: SQL and PostgreSQL
- **Learn:** Table design, keys, indexes, joins, transactions, SQLAlchemy/SQLModel, migrations
- **Lab:** Move from JSON to **PostgreSQL**
- **Add:** Customers, engagements, requests, audit events

#### Week 7: Authentication and Authorization
- **Learn:** Authentication vs. authorization, JWT/OAuth concepts, RBAC, least privilege
- **Lab:** Add admin, engineer, customer **roles**
- **Prove:** Tests verifying users can't access other customers' records

#### Week 8: Minimal Frontend
- Use your JavaScript experience: React + TypeScript or simple server-rendered HTML
- API calls, state, forms, loading/error states
- Dashboard for requests and metrics
- **Keep it modest.** FDE value comes from end-to-end systems, not visual polish.

**Portfolio Project 1: Customer Engagement Tracker**
- Full-stack application with clean architecture
- Tests covering critical paths
- Automated setup script (one-command deploy)
- 5-minute demo
- Architecture diagram explaining decisions

---

### Phase 3: LLM Application Fundamentals (Weeks 9–12)

#### Week 9: How LLM Applications Behave
- **Learn:** LLM fundamentals, tokens, temperature, evaluation frameworks
- **Lab:** Build a simple **chatbot** using OpenAI API or open models
- **Understand:** Cost, latency, reliability, safety concerns

#### Week 10: Structured Output and Parsing
- **Learn:** Constraining LLM outputs to JSON, Pydantic validation
- **Lab:** Use Pydantic + LLM to generate **predictable, validated responses**
- **Example:** Parse customer request into structured data (intent, category, urgency)

#### Week 11: Retrieval-Augmented Generation (RAG)
- **Learn:** Document indexing, semantic search, embeddings, chunking strategies
- **Lab:** Build a **RAG system** over your tracker's requests
- **Example:** "Which past requests are similar to this new one?"

#### Week 12: Agents and Tool Calling
- **Learn:** Multi-step reasoning, tool definitions, reliable function calling
- **Lab:** Build an **AI agent** that can create, update, query requests
- **Example:** "Create a request for Acme Corp" → agent calls your APIs as tools

---

### Phase 4: Agentic Systems (Weeks 13–16)

#### Week 13: Multi-Turn Conversations and Memory
- Conversation history, context management, session persistence
- Implement chat-like experiences, not just single-turn QA

#### Week 14: Reliable Tool Use and Function Calling
- Master tool calling patterns, error recovery, chaining multiple tools
- Handle hallucinated function calls, recover from failures

#### Week 15: Evaluation and Safety
- Build evaluation frameworks
- Measure: reliability, latency, cost, factuality
- Implement guardrails and safety checks

#### Week 16: Production LLM Integrations
- Deploy LLM features safely
- Caching, rate limiting, observability, cost tracking
- Handle model deprecations

**Portfolio Project 2: LLM-Powered Application**
- Intelligent system (agent, RAG, chatbot, etc.) using LLM APIs
- Evaluation suite proving it works
- Infrastructure and deployment story
- Cost analysis and safety considerations

---

### Phase 5: Deployment & Operations (Weeks 17–20)

#### Week 17: Docker and Containerization
- Package your app in containers
- Multi-stage Dockerfiles, image optimization
- Run PostgreSQL + your app locally with Docker Compose

#### Week 18: CI/CD with GitHub Actions
- Automate testing, linting, and deployment
- Build matrices for multiple Python versions
- Deploy to a cloud service (or local test environment)

#### Week 19: Observability, Logging, Monitoring
- Structured logging (JSON, not free text)
- Metrics collection (latency, errors, LLM token usage)
- Alerting on anomalies

#### Week 20: Security and Secrets
- Handle credentials safely (never commit secrets)
- Implement RBAC properly
- Audit logs
- SQL injection prevention
- CORS and other HTTP security

---

### Phase 6: Capstone Portfolio (Weeks 21–24)

#### Week 21: Customer Discovery (Synthetic Scenario)
- Define a realistic AI product
- Write requirements and success metrics
- Identify customer workflows and pain points

#### Week 22: Build the Capstone
- Deliver a working end-to-end product
- Apply all skills from Phases 1–5
- Real business scenario, real constraints

#### Week 23: Production Hardening
- Add comprehensive tests
- Write clear documentation
- Implement security and compliance controls
- Set up deployment infrastructure
- Cost and performance analysis

#### Week 24: Portfolio Demo and Reflection
- Record a 10-minute demo
- Explain architecture and tradeoffs
- Write a retrospective covering what you learned
- Prepare for technical interviews
- Identify what to study next

---

## Portfolio Milestones

You'll complete **3 substantial projects**:

1. **Phase 1 Gate:** Typed Python program with tests and clean architecture
2. **Portfolio Project 1 (Week 8):** Full-stack Customer Engagement Tracker
3. **Portfolio Project 2 (Week 16):** LLM-powered application with evaluation
4. **Capstone (Week 24):** End-to-end AI product

Each includes:
- Working code on GitHub
- Comprehensive README and setup script
- Test suite
- Architecture diagram
- 5–10 minute demo video
- Reflection on decisions and tradeoffs

---

## Interview Readiness

By week 24, you'll be ready for technical interviews because:

- ✅ You've built real systems, not tutorials
- ✅ You understand tradeoffs, not just syntax
- ✅ You've integrated LLMs into production (constraint, cost, safety, eval)
- ✅ You've debugged real failures
- ✅ You have a portfolio to show

**Interview prep:** Each week includes a live coding problem to solve without AI. By week 24, you'll have solved 24 problems of increasing complexity.

---

## How to Use This Learning Path

1. **Read this file once** — get the big picture
2. **Start with Phase 1, Week 1** — follow the week-by-week README
3. **Update decision log and retrospectives** as you go
4. **Share your journey** — LinkedIn posts on what you're learning
5. **Solve the weekly interview problem** — this builds interview muscle

You've got this. 🚀

---

## Resources (Links)

- [Official Python Tutorial](https://docs.python.org/3/tutorial/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Pydantic Docs](https://docs.pydantic.dev/)
- [pytest Docs](https://docs.pytest.org/)
- [OpenAI API Docs](https://platform.openai.com/docs)
- [Anthropic Claude Docs](https://docs.anthropic.com/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Docker Docs](https://docs.docker.com/)

---

**Let's build something real. See you in Week 1.** 🎯
