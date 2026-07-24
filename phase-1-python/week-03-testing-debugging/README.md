# Week 3: Automated Testing and Debugging

## Outcome

Create a trustworthy test suite for the layered tracker and learn to diagnose failures systematically.

## Learning Path (60–90 minutes)

**Best approach:** Testing is learned by watching a test catch a real defect.

For every important rule:
1. Write the expected behavior in plain English
2. Write a **failing** test
3. Confirm it fails for the right reason
4. Implement the smallest fix
5. Refactor while the test stays green

Do not chase coverage percentages. Examine what behavior is actually covered.

### Learn in this order

1. **Arrange, Act, Assert** — the three-phase test pattern
2. **Unit vs. integration tests** — when to use each
3. **pytest discovery and assertions**
4. **Fixtures and temporary paths** (`tmp_path`, `@pytest.fixture`)
5. **Parametrization** — test multiple inputs
6. **Mocks and when NOT to mock** — real vs. fake objects
7. **Regression tests** — tests that catch re-introduced bugs
8. **VS Code test explorer and debugger**
9. **Logging levels and stack traces**

### Free Resources

- [pytest getting started](https://docs.pytest.org/en/stable/getting-started.html)
- [pytest fixtures](https://docs.pytest.org/en/stable/explanation/fixtures.html)
- [pytest parametrization](https://docs.pytest.org/en/stable/how-to/parametrize.html)
- [VS Code Python testing](https://code.visualstudio.com/docs/python/testing)
- [VS Code Python debugging](https://code.visualstudio.com/docs/python/debugging)
- [Python logging HOWTO](https://docs.python.org/3/howto/logging.html)

## Micro-Exercises (45–60 minutes)

1. Test a pure `calculate_sla_hours(priority)` function (parametrize all 3 priorities)
2. Use `tmp_path` to test writing and reading a file
3. Create three request fixtures in `conftest.py`
4. Create a regression test for corrupt JSON handling
5. Mock a clock so timestamps are predictable
6. Debug a deliberately failing test with a breakpoint
7. Add one intentional bug and prove a test catches it

## Main Lab: Test and Harden the Tracker (4–5 hours)

### Test File Structure

Create these test files:

```
tests/
├── conftest.py              # shared fixtures
├── test_models.py
├── test_service.py
├── test_json_repository.py
└── test_csv_import.py
```

### Required Tests

**Models** (test/models.py):
- [ ] Blank title rejected
- [ ] Invalid priority rejected
- [ ] Default status is `open`

**Service** (test_service.py):
- [ ] Allowed and forbidden status transitions
- [ ] Closing requires resolution note
- [ ] Unknown request produces a domain error
- [ ] Update changes `updated_at`, not `created_at`

**Repository** (test_json_repository.py):
- [ ] Empty repository
- [ ] Save/load round trip
- [ ] Missing file (starts empty)
- [ ] Corrupt file (helpful error message)
- [ ] Duplicate ID detection

**CSV** (test_csv_import.py):
- [ ] All valid rows import
- [ ] Mix of valid and invalid rows
- [ ] Missing required headers
- [ ] Extra columns handled gracefully
- [ ] Empty file

### Build Steps

1. Add pytest to `pyproject.toml` (`uv add --dev pytest`)
2. Write 3 simple model tests
3. Create shared fixtures in `conftest.py`
4. Write service tests *before* changing service code
5. Add repository integration tests using `tmp_path`
6. Parametrize all status transitions
7. Replace global time calls with injected clock if needed
8. Add structured logging to repository/service boundaries
9. Introduce one deliberate defect and prove a test catches it
10. Configure one command that runs lint, type checks, and tests

### Acceptance Criteria

- [ ] Tests run from a clean clone
- [ ] No test depends on real user files
- [ ] Tests are deterministic (same result every run)
- [ ] All status-transition combinations covered
- [ ] A deliberately introduced defect causes test failure
- [ ] Logs add diagnostic value without printing sensitive data
- [ ] README explains how to run quality checks
- [ ] At least 5 meaningful commits

## AI-Off Check

**Without looking at examples**, write the failing tests for this new rule: "High-priority requests cannot be closed without an owner assignment." Then implement the rule.

## Reflection Questions

1. Which tests describe actual business value?
2. Which test is too tightly coupled to implementation?
3. What's the difference between a fake repository and a mocked repository?
4. When did the debugger reveal more than a print statement?

---

**Next:** Move to Week 4 when all tests pass and acceptance criteria are met.
