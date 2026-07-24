# Week 4: HTTP APIs, Async, and Resilience

## Outcome

Integrate an external HTTP API through a tested client with timeouts, retries, validation, and a local fake server.

## Learning Path (60–90 minutes)

**Best approach:** Learn HTTP by inspecting actual requests and responses.

1. Send a request
2. Inspect method, URL, headers, body, status, timing
3. Predict app behavior for each type of failure
4. Handle timeouts, retries, invalid responses

### Learn in this order

1. **HTTP fundamentals** — GET, POST, PUT, DELETE, status codes, headers
2. **JSON encoding/decoding** — request and response bodies
3. **httpx** — simple HTTP client for Python
4. **Error handling** — timeouts, connection errors, bad status
5. **Retry logic** — exponential backoff, jitter
6. **async/await** — syntax and basic patterns (not deep async knowledge)
7. **Mocking HTTP** — local fake server or library-level mocking
8. **Environment variables and secrets** — API keys, endpoints
9. **API client architecture** — testable, swappable integrations

### Free Resources

- [httpx documentation](https://www.python-httpx.org/)
- [Python async/await guide](https://docs.python.org/3/library/asyncio.html) (sections 18.5.1–18.5.3)
- [HTTP status codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)
- [pytest with async](https://docs.pytest.org/en/stable/how-to/fixtures.html#async-fixtures)

## Micro-Exercises (45–60 minutes)

1. Make a simple GET request with httpx; inspect the response object
2. Construct a POST request with JSON body
3. Handle a timeout error gracefully
4. Mock an HTTP endpoint using `pytest` and a fake response
5. Write a function with exponential backoff retry logic
6. Test the retry function without making real network calls
7. Load an API key from environment and validate it exists

## Main Lab: API Integration with Resilience (4–5 hours)

### Scenario

Integrate a public API (e.g., [JSONPlaceholder](https://jsonplaceholder.typicode.com/)) to enrich customer requests with external data (e.g., fetch company info by name).

### Requirements

1. Create an `ApiClient` class with:
   - Configurable base URL and timeout
   - Request/response logging
   - Error handling (timeouts, bad status, invalid JSON)
   - Retry logic with exponential backoff

2. Integrate the client into your tracker:
   - On request creation, fetch company info from a public API
   - Store the fetched data in the request
   - Handle API failures gracefully (no blocking)

3. Add configuration via environment variables:
   - `API_BASE_URL`
   - `API_TIMEOUT` (seconds)
   - `MAX_RETRIES`
   - `API_KEY` (if needed)

4. Write tests:
   - Mock API responses (use `pytest` fixtures)
   - Test retry logic
   - Test timeout handling
   - Test malformed API responses

5. Add a CLI command to verify the API connection

### Build Steps

1. Design the `ApiClient` interface
2. Implement basic GET request
3. Add error handling (timeouts, bad status)
4. Add retry logic with exponential backoff
5. Integrate into `RequestService`
6. Add environment variable loading with defaults
7. Mock API responses in tests using `pytest`
8. Write tests for happy path and error cases
9. Add integration test with a local fake server (optional)
10. Document API integration in README

### Acceptance Criteria

- [ ] ApiClient handles timeouts without crashing
- [ ] Failed requests retry up to N times with exponential backoff
- [ ] Tests mock API responses (no real network calls in tests)
- [ ] Invalid API responses fail gracefully
- [ ] Environment variables are read and validated
- [ ] No secrets are logged
- [ ] CLI validates API connection on startup
- [ ] All tests pass
- [ ] At least 5 meaningful commits

## AI-Off Check

**Without examples**, implement a circuit breaker pattern that prevents excessive API calls to a failing endpoint (e.g., fail fast after 3 consecutive errors for 60 seconds).

## Reflection Questions

1. Why separate the API client from the business logic?
2. What happens if the API times out during a request? How should the app respond?
3. Why mock API responses instead of calling the real API in tests?
4. When would you use async/await instead of synchronous httpx calls?

---

## Phase 1 Gate: Python Fundamentals

**You've completed Phase 1 when:**

- [ ] You can build a typed Python program from a blank folder
- [ ] You can test it, debug it, and explain it without consulting tutorials
- [ ] Your code is clean, layered, and doesn't mix concerns
- [ ] Your tests are meaningful and catch real defects
- [ ] Your git history tells the story of the work

**Next:** Move to Phase 2 (FastAPI and full-stack development).
