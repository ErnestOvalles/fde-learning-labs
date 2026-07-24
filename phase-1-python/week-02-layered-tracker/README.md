# Week 2: Data Models, Validation, and Clean Structure

## Outcome

Refactor Week 1's tracker into a **layered, typed application** using Pydantic models, repositories, services, and a CLI.

## Learning Path (60–90 minutes)

**Best approach:** Refactor your working Week 1 code. Feel which problems each abstraction solves rather than learning OOP as a vocabulary exercise.

### Learn in this order

1. **Type hints and unions** — str | int, Optional[T]
2. **Dataclasses vs. Pydantic** — which to use and why
3. **Classes, constructors, instance methods, composition**
4. **Enums** — RequestStatus, Priority
5. **Validation** — Pydantic validators and field constraints
6. **Custom exceptions** — domain-specific error types
7. **Dependency direction** — how to structure layers
8. **Repository pattern** — separate data access from business logic
9. **Service layer** — where business rules live
10. **CSV reading/writing** — multi-format persistence
11. **Ruff and mypy** — automated formatting and type checking

### Free Resources

- [Python typing documentation](https://docs.python.org/3/library/typing.html)
- [Python classes tutorial](https://docs.python.org/3/tutorial/classes.html)
- [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/)
- [Pydantic validators](https://docs.pydantic.dev/latest/concepts/validators/)
- [Ruff tutorial](https://docs.astral.sh/ruff/tutorial/)
- [mypy getting started](https://mypy.readthedocs.io/en/stable/getting_started.html)

## Micro-Exercises (45–60 minutes)

1. Model a request using `dataclass`
2. Model the same request with Pydantic
3. Pass invalid priority to both; compare behavior
4. Create `RequestStatus` and `Priority` enums
5. Write a validator that rejects blank titles
6. Export two request instances to CSV
7. Run Ruff against deliberately poorly formatted code
8. Add a type error and confirm mypy finds it

## Main Lab: Layered Request Tracker (4–5 hours)

### Target Structure

```
week-02-layered-tracker/
├── pyproject.toml
├── README.md
├── src/
│   └── request_tracker/
│       ├── __init__.py
│       ├── cli.py          # input() and print() only
│       ├── models.py       # Pydantic models, enums, validation
│       ├── exceptions.py   # domain-specific errors
│       ├── repositories.py # load, save, find, list
│       └── services.py     # business rules
├── data/
└── tests/
    └── (covered in Week 3)
```

### Responsibilities

- **`models.py`:** validated data shapes, enums
- **`repositories.py`:** load, save, find, list data
- **`services.py`:** business rules and transitions
- **`cli.py`:** input/output only — no file or business logic
- **`exceptions.py`:** custom error types

### Build Steps

1. Copy Week 1 into a new folder
2. Introduce enums (`RequestStatus`, `Priority`) without changing behavior
3. Replace dictionaries with `CustomerRequest` Pydantic model
4. Create `JsonRequestRepository` with load/save methods
5. Move status-transition rules to `RequestService`
6. Keep `input()` and `print()` only in `cli.py`
7. Add rule: closed requests cannot move back to in-progress
8. Add rule: closing requires a resolution note
9. Add CSV export with `csv.DictWriter`
10. Add CSV import with row-level validation errors
11. Report valid and rejected row counts
12. Configure Ruff and mypy in `pyproject.toml`

### Acceptance Criteria

- [ ] Invalid models cannot be created
- [ ] CLI imports no modules from `repositories.py` or `models.py` directly (only `services.py`)
- [ ] Repository contains no `input()` or `print()`
- [ ] Service contains no JSON or CSV code
- [ ] Importing 10 rows with 2 invalid rows imports 8 and reports 2 errors
- [ ] `ruff check .` passes
- [ ] `mypy src/` passes on application code
- [ ] Week 1 behavior still works
- [ ] At least 5 meaningful commits

## AI-Off Check

**Without looking at your code**, draw the dependency direction among CLI, service, repository, and model. Then add a new business rule (e.g., "high-priority requests must have a description > 20 characters") without placing any logic in the CLI.

## Reflection Questions

1. Why use Pydantic rather than plain dictionaries?
2. Which logic belongs in the model vs. the service?
3. What would you change if storage moved from JSON to a database?
4. Did any abstraction make the code harder without providing value?

---

**Tip:** Commit after each step. Your git history should tell the story of the refactor.

**Next:** Move to Week 3 when all acceptance criteria pass.
