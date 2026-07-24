# Forward-Deployed AI Engineer Learning Labs

A hands-on 24-week learning path to become competitive for AI forward-deployed engineer, applied AI engineer, and AI solutions engineer roles.

**Default pace:** 8–10 hours per week | **Total duration:** 24 weeks  
**Primary editor:** VS Code | **Language:** Python 3.12+ & TypeScript | **Cost:** $0–$20 per month

---

## Repository Structure

```
fde-learning-labs/
├── README.md                          # This file
├── LEARNING_PATH.md                   # 24-week overview and learning philosophy
├── notes/
│   ├── glossary.md                    # Technical terms and references
│   ├── decision-log.md                # Architecture and design decisions
│   └── weekly-retrospectives.md       # Learnings from each week
├── phase-1-python/                    # Weeks 1–4: Python fundamentals
│   ├── week-01-request-tracker/
│   ├── week-02-layered-tracker/
│   ├── week-03-testing-debugging/
│   └── week-04-http-apis/
├── phase-2-full-stack/                # Weeks 5–8: Backend + Database + Frontend
│   ├── week-05-fastapi/
│   ├── week-06-sql-postgres/
│   ├── week-07-auth-rbac/
│   └── week-08-frontend/
├── phase-3-llm-apps/                  # Weeks 9–12: LLM fundamentals
│   ├── week-09-llm-behavior/
│   ├── week-10-structured-output/
│   ├── week-11-retrieval/
│   └── week-12-agents/
├── phase-4-agents/                    # Weeks 13–16: Agentic systems
│   ├── week-13-multi-turn/
│   ├── week-14-tool-use/
│   ├── week-15-evaluation/
│   └── week-16-production-llm/
├── phase-5-production/                # Weeks 17–20: Deployment & Ops
│   ├── week-17-docker/
│   ├── week-18-ci-cd/
│   ├── week-19-observability/
│   └── week-20-security/
└── phase-6-capstone/                  # Weeks 21–24: Portfolio project
    ├── week-21-discovery/
    ├── week-22-build/
    ├── week-23-hardening/
    └── week-24-demo/
```

---

## Quick Start

### 1. Clone this repo
```bash
git clone <repo-url>
cd fde-learning-labs
```

### 2. Set up your environment
```bash
# Install uv (one-time)
# On macOS: brew install uv
# On Linux: curl -LsSf https://astral.sh/uv/install.sh | sh
# Or see: https://docs.astral.sh/uv/guides/installation/

# Verify Python 3.12+
uv python install 3.13
```

### 3. Start Week 1
```bash
cd phase-1-python/week-01-request-tracker
uv init
```

---

## The Learning Loop (Each Week)

Follow this 20/70/10 split:

| Phase | Duration | Activity |
|-------|----------|----------|
| **Preview** | 10 min | Read outcomes, skim lab criteria, note what you know |
| **Learn** | 60–90 min | Read/watch resources, type every example, change & predict |
| **Recall** | 15 min | Close resources, explain concepts from memory, correct mistakes |
| **Micro-exercises** | 45–60 min | Complete small exercises without copying solutions |
| **Main lab** | 4–5 hours | Build incrementally, commit after each milestone |
| **Hardening** | 1–2 hours | Add tests, error handling, logging, documentation |
| **Demo & Reflect** | 30 min | Record a demo, write what failed and what you learned |

---

## Using AI Assistants (ChatGPT Plus & Claude Pro)

**Do not ask them to build the whole lab.** Instead:

1. Attempt the problem for 20–30 minutes first
2. Ask for a hint or explanation (not code)
3. Type or deliberately adapt the code yourself
4. Explain every file in your own words
5. Complete an "AI-off" 45-minute session each week

**Useful escalation prompts:**
- "Ask me questions that lead me toward the bug"
- "Give me one conceptual hint"
- "Show a smaller unrelated example of this concept"
- "Review my attempted fix and point out the flaw"
- "Interview me about this architecture"

---

## Completion Checklist (Each Week)

A week is complete only when:

- [ ] The required behavior works
- [ ] Automated tests pass (where required)
- [ ] A fresh clone can be set up via README
- [ ] No secrets are committed
- [ ] You can explain the design without reading code
- [ ] You complete the "AI-off" check
- [ ] You write a retrospective entry

---

## Phases at a Glance

### Phase 1: Python & Engineering Foundations (Weeks 1–4)
- **Week 1:** Python essentials → Customer Request Tracker CLI
- **Week 2:** Data models, validation, clean structure → Layered architecture
- **Week 3:** Automated testing, debugging, Git workflow
- **Week 4:** HTTP APIs, async, resilience, mocking

**Phase gate:** Build a typed Python program from scratch, test it, debug it, explain it—no tutorials.

### Phase 2: Production Backend & Data (Weeks 5–8)
- **Week 5:** FastAPI → REST API
- **Week 6:** PostgreSQL, SQLAlchemy, migrations
- **Week 7:** Authentication, authorization, RBAC
- **Week 8:** Frontend (React + TypeScript or server-rendered)

**Portfolio Project 1:** Full-stack Customer Engagement Tracker with tests, setup script, and 5-minute demo.

### Phase 3: LLM Application Fundamentals (Weeks 9–12)
- **Week 9:** How LLM applications behave, evaluation frameworks
- **Week 10:** Structured output, Pydantic + LLM, parsing
- **Week 11:** Retrieval-augmented generation (RAG)
- **Week 12:** Agents, tool calling, multi-step reasoning

### Phase 4: Agentic Systems (Weeks 13–16)
- **Week 13:** Multi-turn conversations, memory, context
- **Week 14:** Tool use, reliable function calling
- **Week 15:** Evaluation and safety
- **Week 16:** Production LLM integrations

**Portfolio Project 2:** LLM-powered application with evaluation suite and infrastructure.

### Phase 5: Deployment & Operations (Weeks 17–20)
- **Week 17:** Docker, containerization
- **Week 18:** GitHub Actions, CI/CD, testing pipelines
- **Week 19:** Observability, logging, monitoring
- **Week 20:** Security, secrets, compliance

### Phase 6: Capstone Portfolio (Weeks 21–24)
- **Week 21:** Customer discovery (synthetic scenario)
- **Week 22:** Build the product end-to-end
- **Week 23:** Harden: tests, docs, security, infrastructure
- **Week 24:** Demo, retrospective, interview prep

---

## Tools & Cost

| Need | Tool | Cost |
|------|------|------|
| Editor | VS Code | $0 |
| Python | 3.12+ | $0 |
| Environment | `uv` | $0 |
| Version control | Git + GitHub | $0 |
| Backend | FastAPI + Pydantic | $0 |
| Tests & linting | pytest, Ruff, mypy | $0 |
| Database | SQLite → PostgreSQL | $0 (local) |
| Containers | Docker Desktop | $0 |
| Local LLMs | Ollama | $0 |
| CI/CD | GitHub Actions | $0 (public) |
| API tutor | ChatGPT Plus / Claude Pro | Already paid |

**Spending policy:**
- **Weeks 1–8:** $0 additional
- **Weeks 9–16:** $5–$10 total, hard alerts set
- **Weeks 17–24:** $10–$20/month max for portfolio demos only

---

## Notes & Glossary

- **[Glossary](notes/glossary.md)** — Technical terms, concepts, and references
- **[Decision Log](notes/decision-log.md)** — Architecture decisions and tradeoffs
- **[Weekly Retrospectives](notes/weekly-retrospectives.md)** — What you learned each week

---

## Getting Started Now

1. Read [LEARNING_PATH.md](LEARNING_PATH.md) for the full 24-week overview
2. Set up your environment (Python, uv, VS Code)
3. Navigate to `phase-1-python/week-01-request-tracker`
4. Follow the README in that folder

---

## Resources

- [Official Python Tutorial](https://docs.python.org/3/tutorial/)
- [VS Code Python Docs](https://code.visualstudio.com/docs/python/)
- [uv Project Guide](https://docs.astral.sh/uv/guides/projects/)
- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAI API Docs](https://platform.openai.com/docs)
- [Anthropic Claude API](https://docs.anthropic.com/)

---

## License

MIT

---

**Ready to start?** See you in Week 1! 🚀
