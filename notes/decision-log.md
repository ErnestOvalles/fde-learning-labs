# Decision Log

Record architecture and design decisions here. Document *why* you chose something, not just *what*.

Format:
```
## [WEEK/TOPIC] - Decision Title
**Date:** YYYY-MM-DD  
**Context:** Why this decision mattered  
**Options considered:** A, B, C  
**Chosen:** A  
**Rationale:** Why A was better  
**Tradeoffs:** What we gave up choosing A  
**Status:** Active / Superseded / Archived  
```

---

## Example: Phase 1 — Request ID Format

**Date:** 2025-01-15  
**Context:** Week 1 tracker needs unique IDs for requests.  
**Options considered:**
- UUID (e.g., `550e8400-e29b-41d4-a716-446655440000`)
- Sequential integers (1, 2, 3)
- Sequential with prefix (REQ-001, REQ-002)

**Chosen:** Sequential with prefix (REQ-001)  
**Rationale:** Human-readable in CLI menus, easy to debug, no UUID complexity needed for a learning project  
**Tradeoffs:** Not distributed-safe if we later shard across systems; UUID would be safer there  
**Status:** Active (revisit in Week 6 if moving to multi-user database)

---

## Add Your Decisions

As you complete each week, document key decisions here. Examples:

- **Why Pydantic over dataclasses?** (Week 2)
- **Why repository pattern?** (Week 2)
- **Why pytest fixtures instead of setup methods?** (Week 3)
- **Why FastAPI over Flask?** (Week 5)
- **Why PostgreSQL over SQLite for production?** (Week 6)
- **Why JWT instead of sessions?** (Week 7)
- **Why RAG for document retrieval?** (Week 11)

---

**Goal:** By the end of 24 weeks, you'll have a record of your architectural thinking. Useful for interviews and future projects.
