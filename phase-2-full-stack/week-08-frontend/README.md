# Week 8: Minimal Frontend

## Outcome

Build a **modest but real** frontend for the tracker API. Choose **React + TypeScript** (matches your JS background) or **server-rendered HTML with FastAPI + Jinja2** (faster to ship). Either way you will call your Week 5–7 API, render lists, handle forms, and display loading and error states.

By the end of this week you will be able to:

- Pick the simplest frontend that meets the requirement
- Call the FastAPI API with proper auth headers
- Render lists and detail views with loading and error states
- Submit forms that update server state
- Explain when to use React vs. server-rendered templates

## Setup Checklist

Pick a path. The recommended path for FDEs is **React + TypeScript** because you already know JavaScript.

### Path A — React + TypeScript

- [ ] `npm create vite@latest tracker-ui -- --template react-ts`
- [ ] `cd tracker-ui && npm install`
- [ ] `npm install react-router-dom axios`
- [ ] `npm install -D vitest @testing-library/react jsdom`
- [ ] Confirm `npm run dev` opens the dev server

### Path B — FastAPI + Jinja2 (server-rendered)

- [ ] `uv add jinja2 python-multipart`
- [ ] Create `src/request_tracker/web.py`
- [ ] Confirm `uv run uvicorn request_tracker.web:app --reload`

## Learning Path (60–90 minutes)

**Best approach:** Read existing API docs (`/docs` from Week 5) and build one page end-to-end before adding routing or styling.

### Learn in this order (React path)

1. **Vite** — project init, dev server, hot reload
2. **TypeScript with React** — `useState`, `useEffect`, types for props
3. **Fetch with `fetch` or `axios`** — auth header, error handling
4. **Routing** with `react-router-dom`
5. **Forms** — controlled inputs, submit, reset
6. **Loading and error states** — skeletons, banners
7. **Test a component** with `vitest` and `react-testing-library`

### Learn in this order (Jinja path)

1. **Jinja2 templates** — `{% for %}`, `{{ variable }}`, layout inheritance
2. **Form handling** — `Form` data, `request.form`
3. **HTMX for partial updates** (optional, very effective)
4. **Sessions/cookies** for auth
5. **Tailwind or plain CSS** — keep it minimal

### Free Resources

- [React TypeScript cheatsheet](https://react-typescript-cheatsheet.netlify.app/)
- [Vite getting started](https://vitejs.dev/guide/)
- [Jinja2 template designer docs](https://jinja.palletsprojects.com/en/stable/templates/)
- [HTMX in 100 seconds (video)](https://www.youtube.com/watch?v=r-GSj4dLmR4)

## Micro-Exercises (45–60 minutes)

### React + TypeScript

1. Render a list from a hardcoded array
2. Add `useState` to track an input value
3. Fetch `/requests` and `console.log` the result
4. Show a loading spinner while fetching
5. Show an error message on a 4xx/5xx response
6. Wire a form to `POST /requests`
7. Add `react-router-dom` routes for `/`, `/requests`, `/requests/:id`
8. Add a logout button that clears the stored token

### FastAPI + Jinja2

1. Render a hardcoded list in a template
2. Add a Jinja layout with `{% block content %}`
3. Read form data with `request.form`
4. Submit a form that calls `POST /requests` server-side
5. Show a flash message after create/update
6. Log in via a form and store the JWT in a session cookie
7. Display a 404 page on missing ID
8. Add a simple CSS file (one rule per component)

## Main Lab: Tracker Dashboard (4–5 hours)

### Required Pages

| Route                 | Purpose                                         |
|-----------------------|-------------------------------------------------|
| `/login`              | Username + password form, stores JWT in memory  |
| `/` or `/dashboard`   | Counts: open, in_progress, closed, high-priority |
| `/requests`           | Paginated list, filter by status & priority      |
| `/requests/new`       | Form to create a request                        |
| `/requests/:id`       | Detail view with status controls                |

### React Component Sketch

```
src/
├── api.ts                # typed fetch wrappers
├── auth.ts               # token storage, getCurrentUser
├── App.tsx               # router + auth gate
├── pages/
│   ├── Login.tsx
│   ├── Dashboard.tsx
│   ├── RequestList.tsx
│   ├── RequestNew.tsx
│   └── RequestDetail.tsx
├── components/
│   ├── Layout.tsx
│   ├── StatusBadge.tsx
│   └── ErrorBanner.tsx
└── main.tsx
```

### Jinja Template Sketch

```
src/request_tracker/
├── web.py                # FastAPI app with HTML routes
├── templates/
│   ├── base.html         # layout
│   ├── login.html
│   ├── dashboard.html
│   ├── request_list.html
│   ├── request_new.html
│   └── request_detail.html
└── static/
    └── app.css
```

### Build Steps

#### React path

1. Scaffold with Vite
2. Create typed `api.ts` wrappers for each endpoint
3. Implement `Login` and store the JWT
4. Build `Dashboard` with summary counts
5. Build `RequestList` with filters
6. Build `RequestNew` form
7. Build `RequestDetail` with status controls
8. Add an `ErrorBanner` and loading skeletons
9. Add a Playwright/Vitest happy-path test
10. Document `npm run dev` in the README

#### Jinja path

1. Add a `web.py` module with HTML routes
2. Create `base.html` layout with a nav bar
3. Implement `GET /login` and `POST /login`
4. Implement `GET /` dashboard
5. Implement `GET /requests` list with filters
6. Implement `GET /requests/new` and `POST /requests/new`
7. Implement `GET /requests/{id}` with status actions
8. Add `app.css` for minimal styling
9. Add a flash-message helper
10. Document `uv run uvicorn request_tracker.web:app --reload`

## Step-by-Step Walkthrough

The walkthrough below follows the **React + TypeScript** path. The Jinja equivalent is noted at the end of each step.

### Exercise 1 — Render a list from a hardcoded array

```tsx
// src/components/RequestList.tsx
type RequestSummary = {
  id: string;
  title: string;
  priority: "low" | "medium" | "high";
  status: "open" | "in_progress" | "closed";
};

export function RequestList({ items }: { items: RequestSummary[] }) {
  return (
    <ul className="request-list">
      {items.map((r) => (
        <li key={r.id}>
          <span className="id">{r.id}</span>
          <span className="title">{r.title}</span>
          <span className={`badge badge-${r.priority}`}>{r.priority}</span>
          <span className={`badge badge-${r.status}`}>{r.status}</span>
        </li>
      ))}
    </ul>
  );
}
```

**Step-by-step:**
1. Define the `RequestSummary` *type* first — your IDE will help you write code that conforms.
2. The `key` is required for stable list rendering.
3. Class names like `badge-high` make styling trivial in `app.css`.

### Exercise 2 — `useState` to track an input value

```tsx
// src/pages/Login.tsx
import { useState } from "react";

export function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  return (
    <form onSubmit={(e) => e.preventDefault()}>
      <label>
        Username
        <input value={username} onChange={(e) => setUsername(e.target.value)} />
      </label>
      <label>
        Password
        <input type="password"
               value={password}
               onChange={(e) => setPassword(e.target.value)} />
      </label>
      <button type="submit">Sign in</button>
    </form>
  );
}
```

**Step-by-step:**
1. The input is *controlled* — its value always comes from state.
2. `onChange` writes the new value back to state. This is the canonical React pattern.
3. `type="password"` masks the input in the browser.

### Exercise 3 — Fetch `/requests` and log the result

```tsx
// src/api.ts
import type { RequestSummary } from "./components/RequestList";

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export async function listRequests(token: string): Promise<RequestSummary[]> {
  const r = await fetch(`${BASE}/requests`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(`listRequests: ${r.status}`);
  return r.json();
}
```

```tsx
// usage
useEffect(() => {
  listRequests(token).then(setItems).catch(console.error);
}, [token]);
```

**Step-by-step:**
1. `import.meta.env.VITE_*` is Vite's way to read build-time config.
2. Throw on non-2xx — let the caller decide how to render the error.
3. The `Authorization: Bearer *** header is exactly what your Week 7 dependency expects.

### Exercise 4 — Show a loading spinner while fetching

```tsx
// src/components/Spinner.tsx
export function Spinner() {
  return <div role="status" aria-label="Loading" className="spinner" />;
}

// in a page
{loading ? <Spinner /> : <RequestList items={items} />}
```

**Step-by-step:**
1. `role="status"` lets screen readers announce the loading state.
2. The CSS for `.spinner` is one `animation: spin 1s linear infinite;` away.
3. Don't gate the *whole* page on a single request — load sections independently.

### Exercise 5 — Show an error message on 4xx/5xx

```tsx
// src/components/ErrorBanner.tsx
export function ErrorBanner({ error, onRetry }:
    { error: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="error-banner">
      <span>{error}</span>
      {onRetry && <button onClick={onRetry}>Retry</button>}
    </div>
  );
}
```

**Step-by-step:**
1. `role="alert"` makes screen readers announce the error immediately.
2. A *retry* button is a small thing that turns a frustrating UX into a tolerable one.
3. Don't show the raw stack trace — the user doesn't care; the developer can read console.

### Exercise 6 — Wire a form to `POST /requests`

```tsx
// src/pages/RequestNew.tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createRequest } from "../api";

export function RequestNew({ token }: { token: string }) {
  const nav = useNavigate();
  const [form, setForm] = useState({
    customer_name: "", title: "", description: "", priority: "low" as const,
  });
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const r = await createRequest(token, form);
      nav(`/requests/${r.id}`);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <form onSubmit={submit}>
      <input value={form.customer_name}
             onChange={(e) => setForm({ ...form, customer_name: e.target.value })} />
      {/* ...title, description, priority... */}
      <button type="submit">Create</button>
      {error && <div role="alert">{error}</div>}
    </form>
  );
}
```

**Step-by-step:**
1. `useNavigate` is the imperative way to redirect after a successful create.
2. Spreading `{ ...form, customer_name: e.target.value }` keeps the other fields intact.
3. The form is *uncontrolled-ish* in spirit (single source of truth in state) — this is the React way.

### Exercise 7 — Add `react-router-dom` routes

```tsx
// src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { RequestList } from "./pages/RequestList";
import { RequestDetail } from "./pages/RequestDetail";

export function App() {
  const token = localStorage.getItem("token");
  if (!token) return <Login />;

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard token={token} />} />
        <Route path="/requests" element={<RequestList token={token} />} />
        <Route path="/requests/:id" element={<RequestDetail token={token} />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  );
}
```

**Step-by-step:**
1. The auth gate is a single line — fail closed if there's no token.
2. `<Navigate to="/" />` is the redirect component; use it inside `<Route>`.
3. `localStorage.getItem("token")` is fine for a dev build; production should use httpOnly cookies (Week 20).

### Exercise 8 — Logout button that clears the token

```tsx
// src/components/Layout.tsx
import { useNavigate } from "react-router-dom";

export function Layout({ children }: { children: React.ReactNode }) {
  const nav = useNavigate();
  return (
    <div>
      <header>
        <button onClick={() => { localStorage.removeItem("token"); nav("/"); }}>
          Log out
        </button>
      </header>
      <main>{children}</main>
    </div>
  );
}
```

**Step-by-step:**
1. Removing the token + navigating to `/` is enough — the auth gate takes over.
2. In a real app, also call a `/auth/logout` endpoint to invalidate the token server-side.
3. Confirm `localStorage.removeItem` actually removes the key (`getItem` returns `null`).

---

### Step 1 — Scaffold with Vite

```bash
npm create vite@latest tracker-ui -- --template react-ts
cd tracker-ui
npm install
npm install react-router-dom
npm run dev
```

### Step 2 — Create typed `api.ts` wrappers

Already started in Exercise 3. Add the rest:

```ts
export async function createRequest(token: string, body: NewRequest) {
  const r = await fetch(`${BASE}/requests`, {
    method: "POST",
    headers: { "content-type": "application/json",
               Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`createRequest: ${r.status}`);
  return r.json();
}

export async function changeStatus(token: string, id: string, newStatus: string) {
  const r = await fetch(`${BASE}/requests/${id}/status`, {
    method: "PATCH",
    headers: { "content-type": "application/json",
               Authorization: `Bearer ${token}` },
    body: JSON.stringify({ new_status: newStatus }),
  });
  if (!r.ok) throw new Error(`changeStatus: ${r.status}`);
  return r.json();
}
```

### Step 3 — Implement `Login` and store the JWT

```tsx
// pages/Login.tsx (key parts)
const r = await fetch(`${BASE}/auth/login`, {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ username, password }),
});
if (!r.ok) { setError("bad credentials"); return; }
const { access_token } = await r.json();
localStorage.setItem("token", access_token);
nav("/");
```

### Step 4 — Build `Dashboard` with summary counts

```tsx
// pages/Dashboard.tsx
import { useEffect, useState } from "react";
import { listRequests } from "../api";

export function Dashboard({ token }: { token: string }) {
  const [counts, setCounts] = useState({ open: 0, in_progress: 0, closed: 0 });
  useEffect(() => {
    listRequests(token, { limit: 1000 }).then((rows) => {
      setCounts({
        open: rows.filter((r) => r.status === "open").length,
        in_progress: rows.filter((r) => r.status === "in_progress").length,
        closed: rows.filter((r) => r.status === "closed").length,
      });
    });
  }, [token]);

  return (
    <div className="dashboard">
      <Stat label="Open"        value={counts.open} />
      <Stat label="In progress" value={counts.in_progress} />
      <Stat label="Closed"      value={counts.closed} />
    </div>
  );
}
```

### Step 5 — Build `RequestList` with filters

```tsx
// pages/RequestList.tsx
const [status, setStatus] = useState<string>("");
useEffect(() => {
  listRequests(token, { status_filter: status || undefined })
    .then(setItems).catch(setError);
}, [token, status]);
```

### Step 6 — Build `RequestNew` form

Already in Exercise 6.

### Step 7 — Build `RequestDetail` with status controls

```tsx
// pages/RequestDetail.tsx
async function close() {
  await changeStatus(token, id!, "closed");
  refresh();
}
```

### Step 8 — Add `ErrorBanner` and loading skeletons

Already in Exercises 4 and 5. Add a `<Skeleton />` for each row during load.

### Step 9 — Add a Vitest happy-path test

```ts
// src/__tests__/RequestList.test.tsx
import { render, screen } from "@testing-library/react";
import { RequestList } from "../components/RequestList";

test("renders all items", () => {
  render(<RequestList items={[
    { id: "REQ-001", title: "Login", priority: "high", status: "open" },
  ]} />);
  expect(screen.getByText("REQ-001")).toBeInTheDocument();
  expect(screen.getByText("high")).toBeInTheDocument();
});
```

### Step 10 — Document `npm run dev` in the README

```markdown
## Run the UI

    cd tracker-ui
    npm install
    npm run dev

Visit http://localhost:5173.
The dev server proxies `/api` to http://localhost:8000 (configure in `vite.config.ts`).
```

#### Jinja Path Equivalents (abbreviated)

1. `web.py` exposes HTML routes; the API routes stay as-is.
2. `templates/base.html` is the layout; other templates extend it.
3. `templates/login.html` posts to `POST /login`; the server calls the API and sets a session cookie.
4. `templates/request_list.html` loops over `requests` and shows a status badge.
5. `templates/request_detail.html` shows the request and a form for `POST /requests/{id}/close`.
6. `static/app.css` provides a single style block.
7. Use `request.session` to hold the JWT instead of `localStorage`.

---

## Acceptance Criteria

- [ ] Login page works against the real `/auth/login` endpoint
- [ ] Dashboard shows real counts from the API
- [ ] Request list filters by status and priority
- [ ] Create form posts to the API and redirects to the new request
- [ ] Detail view can change status (engineer/admin) or close (customer)
- [ ] Loading states appear while fetching
- [ ] Error banner appears on 4xx/5xx with a retry option
- [ ] Logout clears the token and returns to the login page
- [ ] At least 5 meaningful commits

## AI-Off Check

**Without examples**, add a "Last 7 days" line chart to the dashboard. Either pull the data from a new endpoint you add to the API, or compute it client-side from `/requests`. Decide which is right and justify it.

## Reflection Questions

1. Why did you choose React + TypeScript over Jinja (or vice versa)? What would change your mind?
2. Where should the auth token live? `localStorage`? A cookie? In memory? What are the tradeoffs?
3. When does a frontend need a state library (Redux, Zustand)? When is `useState` enough?
4. What's the most expensive API call from the UI? How could you cache or batch it?

---

**Next:** Move to Week 9 when all acceptance criteria pass and you can demo the full login → create → close flow end-to-end.
