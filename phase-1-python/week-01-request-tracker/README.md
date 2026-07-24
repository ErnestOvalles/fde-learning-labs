# Week 1: Python Essentials and VS Code Workflow

## Outcome

Build a terminal-based **Customer Request Tracker CLI** that can add, list, view, update, and close customer requests stored in JSON.

## Setup Checklist

- [ ] Install Git
- [ ] Install VS Code with Python, Pylance, and Ruff extensions
- [ ] Install `uv`
- [ ] Run `uv python install 3.13`
- [ ] Create `pyproject.toml` with `uv init`
- [ ] Confirm `uv run python --version` works

## Learning Path (60–90 minutes)

**Best approach:** Learn Python by translating familiar JavaScript concepts.

### Learn in this order

1. **Values and variables** — int, float, str, bool, None
2. **Collections** — list, dict, tuple, set
3. **Control flow** — if, for, while
4. **Functions** — def, parameters, return, scope
5. **Imports and modules** — import, from X import Y
6. **Exceptions** — try/except/finally
7. **File I/O** — open(), read(), write()
8. **JSON** — json.load(), json.dump()
9. **Git basics** — status, add, commit, diff

### Free Resources

- [Official Python Tutorial](https://docs.python.org/3/tutorial/) — sections 3, 4, 5, 6, 7.2, and 8.1–8.4
- [Google's Free Python Class](https://developers.google.com/edu/python) — introductory exercises if the official tutorial feels compressed
- [VS Code Python Tutorial](https://code.visualstudio.com/docs/python/python-tutorial) — environment selection, running, debugging
- [uv Project Guide](https://docs.astral.sh/uv/guides/projects/) — uv init, uv run, uv add

**Tip:** Type every example. Change each one and predict the result before running it.

## Micro-Exercises (45–60 minutes)

Create `practice.py` and complete these:

1. Create a dictionary representing one support request
2. Put three request dictionaries into a list
3. Print only requests with status `open`
4. Write `find_request(requests, request_id)`
5. Write `close_request(request)` that changes its status
6. Serialize the list to JSON and load it back
7. Trigger and catch a `FileNotFoundError`
8. Set a breakpoint and inspect a variable in VS Code's debugger

## Main Lab: Customer Request Tracker CLI (4–5 hours)

### Scenario

A consulting team needs a lightweight way to track customer requests before a proper system is available.

### Data Shape

Each request must contain:

```python
{
    "id": "REQ-001",
    "customer_name": "Acme Corp",
    "title": "Login system upgrade",
    "description": "Users report slow login times",
    "priority": "high",              # low, medium, high
    "status": "open",                # open, in_progress, closed
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
}
```

### Required Commands

Your first version can use a numbered menu:

```
1. Add request
2. List requests
3. View one request
4. Change status
5. Close request
6. Exit
```

### Build Steps

**Commit after each step.** Use commit messages like:
- `feat: add request to in-memory list`
- `feat: add JSON persistence`
- `feat: add input validation`

1. Create one hardcoded request and print it
2. Replace hardcoded data with user input (`input()`)
3. Store requests in a list for the current session
4. Generate a unique ID (e.g., REQ-001, REQ-002)
5. Add filtering by status and priority
6. Save the list to `data/requests.json` after every change
7. Load existing data at startup
8. Handle missing file by starting with empty list
9. Handle corrupt JSON with a helpful error message
10. Add confirmation before closing a request
11. Split repeated behavior into functions
12. Write a `README.md` with setup and usage instructions

### Required Manual Tests

Run these before you consider yourself done:

- [ ] Start with no data file
- [ ] Add two requests
- [ ] Exit and restart; confirm both remain
- [ ] Filter by priority
- [ ] Try to view an unknown request ID
- [ ] Enter an invalid priority
- [ ] Corrupt a copy of the JSON file and observe the error
- [ ] Try to close an already-closed request

### Acceptance Criteria

- [ ] No uncaught exception for expected bad input
- [ ] Data survives restart
- [ ] IDs are unique
- [ ] Invalid status and priority values are rejected
- [ ] `created_at` does not change during an update
- [ ] `updated_at` changes on every update
- [ ] Functions are small enough to explain
- [ ] At least 5 meaningful commits in git history

## AI-Off Check (30 minutes)

**Without looking at your code**, write a function that accepts a list of request dictionaries and returns only the open, high-priority requests sorted by customer name.

## Reflection Questions

After you finish, write answers to these in `REFLECTION.md`:

1. Why did you choose your ID format?
2. What can go wrong if the process stops while writing JSON?
3. Which functions mix user-interface logic with business logic?
4. What would make this difficult to test automatically?

## Next Steps

Once you pass all acceptance criteria:

1. Record a 1-minute demo showing the tracker in action
2. Write the reflection answers
3. Commit with message: `docs: week 1 complete`
4. Move to Week 2

---

**Ready?** Start by running:

```bash
uv init
```

Then follow the learning path above. Good luck! 🎯
