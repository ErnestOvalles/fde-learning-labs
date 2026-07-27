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

### Setup Walkthrough

```bash
# 1. Verify Git is installed
git --version
# expected: git version 2.x.x

# 2. Install uv (Astral's Python toolchain manager)
# macOS / Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows (PowerShell):
# irm https://astral.sh/uv/install.ps1 | iex

# 3. Install Python 3.13 via uv
uv python install 3.13

# 4. Create the project folder
mkdir tracker && cd tracker
uv init                      # creates pyproject.toml, hello.py, .python-version
uv python pin 3.13           # pin to 3.13

# 5. Sanity-check
uv run python --version      # should print Python 3.13.x
uv run python -c "print('hi')"
```

In VS Code, open the folder, install the **Python**, **Pylance**, and **Ruff** extensions, then press `Ctrl+Shift+P` → `Python: Select Interpreter` → choose the one uv created (`.venv/bin/python`).

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

### Exercise 1 — Create a dictionary representing one support request

```python
# practice.py

request = {
    "id": "REQ-001",
    "customer_name": "Acme Corp",
    "title": "Login system upgrade",
    "description": "Users report slow login times",
    "priority": "high",
    "status": "open",
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z",
}

print(request)
print(request["title"])          # dict access like JS object
print(request.get("owner"))      # safe access (None instead of KeyError)
```

**Step-by-step:**
1. Open `practice.py` in VS Code.
2. Paste the snippet above.
3. Run with `uv run python practice.py`.
4. Predict the output before running — then verify.

### Exercise 2 — Put three request dictionaries into a list

```python
requests = [
    {"id": "REQ-001", "status": "open",    "priority": "high"},
    {"id": "REQ-002", "status": "closed",  "priority": "low"},
    {"id": "REQ-003", "status": "open",    "priority": "medium"},
]

# list length (like JS .length)
print(len(requests))

# append a new request
requests.append({"id": "REQ-004", "status": "open", "priority": "high"})

# iterate
for r in requests:
    print(r["id"], r["priority"])
```

**Step-by-step:**
1. Build a list of three dicts.
2. `print(len(requests))` to see how `len()` replaces JS `.length`.
3. Use `requests.append(...)` to add a fourth.
4. Loop with `for r in requests:` — Python's equivalent of `for...of`.

### Exercise 3 — Print only requests with status `open`

```python
open_requests = [r for r in requests if r["status"] == "open"]
print(open_requests)

# Equivalent loop form (more readable at first):
for r in requests:
    if r["status"] == "open":
        print(r)
```

**Step-by-step:**
1. Write the list comprehension (the `[... for ... if ...]` line) — it is Python's equivalent of `Array.filter()`.
2. Add the explicit `for` loop version. They produce the same output.
3. Try changing the filter to `r["priority"] == "high"` and confirm the count.

### Exercise 4 — Write `find_request(requests, request_id)`

```python
def find_request(requests, request_id: str) -> dict | None:
    """Return the matching request or None."""
    for r in requests:
        if r["id"] == request_id:
            return r
    return None

found = find_request(requests, "REQ-002")
print(found)

missing = find_request(requests, "REQ-999")
print(missing)        # None — Python's "no value" (like JS null)
```

**Step-by-step:**
1. Define the function with a type hint `dict | None` (Python 3.10+ union syntax).
2. Loop through `requests`; return the first match.
3. Return `None` explicitly when nothing is found (Python does NOT return `undefined` like JS).
4. Call it twice — once with a real ID, once with a missing one.

### Exercise 5 — Write `close_request(request)` that changes its status

```python
def close_request(request: dict) -> None:
    """Mutate the request in place: status -> closed, bump updated_at."""
    request["status"] = "closed"
    request["updated_at"] = "2025-01-16T09:00:00Z"

close_request(requests[0])
print(requests[0])
```

**Step-by-step:**
1. The function takes one request dict and mutates it in place (no `return` needed).
2. Notice that `requests[0]` reflects the change — Python passes references, not copies (same as JS objects).
3. Use `copy.deepcopy()` if you ever need to avoid mutation:
   ```python
   from copy import deepcopy
   snapshot = deepcopy(request)
   close_request(request)
   ```

### Exercise 6 — Serialize the list to JSON and load it back

```python
import json

# serialize
raw = json.dumps(requests, indent=2)
print(raw)

# round-trip through a string
parsed = json.loads(raw)
print(parsed[0]["id"])

# round-trip through a file
with open("practice.json", "w") as f:
    json.dump(requests, f, indent=2)

with open("practice.json") as f:
    loaded = json.load(f)

print(len(loaded))
```

**Step-by-step:**
1. `json.dumps()` → Python object to JSON string (like `JSON.stringify`).
2. `json.loads()` → JSON string to Python object (like `JSON.parse`).
3. `json.dump()` / `json.load()` do the same, but to/from a file.
4. The `with open(...) as f:` block is Python's equivalent of try/finally for closing files — use it every time.

### Exercise 7 — Trigger and catch a `FileNotFoundError`

```python
import json

try:
    with open("does_not_exist.json") as f:
        data = json.load(f)
except FileNotFoundError as e:
    print("File missing, starting empty:", e)
    data = []
```

**Step-by-step:**
1. Run the snippet — Python raises `FileNotFoundError`.
2. Wrap it in `try/except FileNotFoundError as e:` to handle the failure gracefully.
3. Replace `data = []` with whatever your default state should be (empty list, default dict, etc.).
4. Add `except json.JSONDecodeError as e:` to also handle corrupt JSON later.

### Exercise 8 — Set a breakpoint and inspect a variable in VS Code's debugger

**Step-by-step:**
1. Open `practice.py` in VS Code.
2. Click in the gutter (left of the line numbers) next to `print(requests[0])` inside `close_request` to set a red breakpoint.
3. Press `F5` → choose `Python File` → the debugger pauses on the breakpoint.
4. Hover over `request` in the editor — VS Code shows its current contents.
5. Open the **Run and Debug** side panel (`Ctrl+Shift+D`) to see the full **Variables** tree.
6. Step over with `F10`, step into with `F11`, continue with `F5`.

This is the single most valuable habit you'll build in Week 1. If you can pause a running program and read its state, you can debug anything.

---

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

#### Step 1 — Create one hardcoded request and print it

```python
# tracker.py
request = {
    "id": "REQ-001",
    "customer_name": "Acme Corp",
    "title": "Login system upgrade",
    "description": "Users report slow login times",
    "priority": "high",
    "status": "open",
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z",
}

print(request)
```

```bash
uv run python tracker.py
git add tracker.py
git commit -m "feat: print one hardcoded request"
```

#### Step 2 — Replace hardcoded data with user input

```python
def prompt_new_request() -> dict:
    return {
        "id": "REQ-001",  # placeholder for now
        "customer_name": input("Customer name: "),
        "title":          input("Title: "),
        "description":    input("Description: "),
        "priority":       input("Priority (low/medium/high): "),
        "status":         "open",
        "created_at":     "2025-01-15T10:30:00Z",
        "updated_at":     "2025-01-15T10:30:00Z",
    }

new = prompt_new_request()
print(new)
```

```bash
git commit -am "feat: capture new request via input()"
```

#### Step 3 — Store requests in a list for the current session

```python
requests: list[dict] = []

while True:
    choice = input("Add request? (y/n): ").lower()
    if choice != "y":
        break
    requests.append(prompt_new_request())

print(f"\nCaptured {len(requests)} request(s).")
for r in requests:
    print(r["id"], "-", r["title"])
```

#### Step 4 — Generate a unique ID

```python
import re
from pathlib import Path

DATA_FILE = Path("data/requests.json")
ID_PATTERN = re.compile(r"REQ-(\d+)")

def next_request_id(existing: list[dict]) -> str:
    """Find the highest numeric suffix and increment."""
    nums = []
    for r in existing:
        match = ID_PATTERN.match(r["id"])
        if match:
            nums.append(int(match.group(1)))
    next_num = (max(nums) if nums else 0) + 1
    return f"REQ-{next_num:03d}"

# usage inside prompt_new_request:
# "id": next_request_id(requests),
```

**Why this works:**
- Regex `r"REQ-(\d+)"` extracts the trailing number from each existing ID.
- `max(nums)` finds the highest used; `+1` reserves the next.
- `:03d` zero-pads to 3 digits, so we get `REQ-001`, `REQ-002`, …, `REQ-099`, `REQ-100`.

#### Step 5 — Add filtering by status and priority

```python
def list_requests(requests: list[dict], status: str | None = None,
                  priority: str | None = None) -> list[dict]:
    result = requests
    if status:
        result = [r for r in result if r["status"] == status]
    if priority:
        result = [r for r in result if r["priority"] == priority]
    return result

# Examples:
list_requests(requests)                              # all
list_requests(requests, status="open")               # open only
list_requests(requests, priority="high")             # high-priority only
list_requests(requests, status="open", priority="high")
```

#### Step 6 — Save the list to `data/requests.json` after every change

```python
import json
from pathlib import Path

DATA_FILE = Path("data/requests.json")

def save_requests(requests: list[dict]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w") as f:
        json.dump(requests, f, indent=2)

# Call after every add/update/close:
# save_requests(requests)
```

**Pitfall to know:** If your program crashes between in-memory change and `save_requests()`, you lose data. We'll fix this in Week 2 by separating repository logic.

#### Step 7 — Load existing data at startup

```python
def load_requests() -> list[dict]:
    try:
        with DATA_FILE.open() as f:
            return json.load(f)
    except FileNotFoundError:
        return []

requests = load_requests()
```

#### Step 8 — Handle missing file by starting with empty list

Already handled by the `except FileNotFoundError → return []` above. **Verify it works:** delete `data/requests.json`, run the program, confirm it starts empty without crashing.

#### Step 9 — Handle corrupt JSON with a helpful error message

```python
def load_requests() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    try:
        with DATA_FILE.open() as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: {DATA_FILE} is not valid JSON: {e}")
        print("Fix the file or delete it to start fresh.")
        raise SystemExit(1)
```

**Step-by-step:**
1. Run the program once to create a valid `requests.json`.
2. Open the file in VS Code and corrupt it: delete a quote, leave a trailing comma.
3. Re-run the program — confirm the helpful message fires.

#### Step 10 — Add confirmation before closing a request

```python
def close_request(requests: list[dict], request_id: str) -> bool:
    target = find_request(requests, request_id)
    if not target:
        print(f"No request with id {request_id}")
        return False
    if target["status"] == "closed":
        print(f"{request_id} is already closed.")
        return False
    confirm = input(f"Close {request_id} ({target['title']})? (y/n): ").lower()
    if confirm != "y":
        print("Cancelled.")
        return False
    target["status"] = "closed"
    target["updated_at"] = "2025-01-16T09:00:00Z"  # or datetime.now(UTC).isoformat()
    save_requests(requests)
    print(f"{request_id} closed.")
    return True
```

#### Step 11 — Split repeated behavior into functions

Your file should end up with roughly these functions, each small enough to explain in one sentence:

```python
def prompt_new_request(existing): ...
def next_request_id(existing): ...
def find_request(requests, request_id): ...
def list_requests(requests, status=None, priority=None): ...
def change_status(requests, request_id, new_status): ...
def close_request(requests, request_id): ...
def save_requests(requests): ...
def load_requests(): ...
def main(): ...
```

The numbered menu in `main()` should look like:

```python
def main() -> None:
    requests = load_requests()
    while True:
        print("\n1. Add  2. List  3. View  4. Change status  5. Close  6. Exit")
        choice = input("> ").strip()
        if choice == "1":
            requests.append(prompt_new_request(requests))
            save_requests(requests)
        elif choice == "2":
            for r in list_requests(requests):
                print(r["id"], r["priority"], r["status"], "-", r["title"])
        elif choice == "3":
            r = find_request(requests, input("ID: "))
            print(r if r else "Not found.")
        elif choice == "4":
            change_status(requests, input("ID: "), input("New status: "))
            save_requests(requests)
        elif choice == "5":
            close_request(requests, input("ID: "))
        elif choice == "6":
            break

if __name__ == "__main__":
    main()
```

#### Step 12 — Write a `README.md` with setup and usage instructions

```markdown
# Customer Request Tracker

Tiny CLI for tracking customer requests in a JSON file.

## Setup
    uv sync
    uv run python tracker.py

## Usage
Pick from the numbered menu. Data lives in `data/requests.json`.

## Tests
Manual tests are listed in the week README.
```

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

```python
def open_high_priority_by_customer(requests):
    filtered = [r for r in requests
                if r["status"] == "open" and r["priority"] == "high"]
    filtered.sort(key=lambda r: r["customer_name"])
    return filtered
```

Try writing it cold, then compare with your answer. The goal is to be able to write a filter + sort from memory.

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
