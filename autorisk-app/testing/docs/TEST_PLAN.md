# AutoRisk — Test Plan

## 1. Purpose
Check that AutoRisk (React + FastAPI + PostgreSQL car-insurance app) works
correctly, safely rejects bad input, and protects customer data. Record
every defect found in [`BUG_REPORTS.md`](BUG_REPORTS.md).

## 2. Scope

**In scope (the features that are wired up):**

| Feature | Backend | Frontend page |
|---|---|---|
| Login / logout / sessions | `routers/auth.py`, `auth.py` | Login, Sidebar |
| Policyholders: list, search, filter, create | `routers/policyholders.py` | Policyholders |
| Claims: list, filter, create, payments | `routers/claims.py` | Claims |
| Quote calculator | `routers/quote.py`, `pricing.py` | New Quote |
| Dashboard KPIs and recent claims | `routers/dashboard.py` | Dashboard |
| Read-only lists | regions, coverages, policies, vehicles | matching pages |

**Out of scope:** Rate Tables, Risk Analysis, Reports, and Accounts (still
"Coming Soon" pages); performance/load testing; non-Chromium browsers;
the Neon production database.

## 3. Test levels (the "test pyramid")

```
        /\        E2E (Playwright)      35 tests    slow (~50 s)   whole system through a real browser
       /  \
      /----\      API / integration     153 tests   medium (~25 s)  backend + real Postgres, no browser
     /      \
    /--------\    Unit                  44 tests    fast (<1 s)     pricing formula alone
```

Most checks sit at the lowest level that can catch the problem. E2E tests
only cover what *only* a browser can show (navigation, forms, what is
rendered on screen).

| Level | Folder | Tool | What it proves |
|---|---|---|---|
| Unit | `unit/` | pytest | `pricing.py` math is right (age bands, power bands, risk levels) |
| API | `api/` | pytest + FastAPI TestClient | Endpoints return the right status codes and data, and enforce validation and security |
| E2E | `e2e/` | pytest + Playwright (Chromium) | A user can actually do the task in the UI |

## 4. Test types and techniques
- **Functional:** each feature does what it should (happy path).
- **Negative:** bad input is rejected cleanly with 4xx, never 500.
- **Boundary value analysis:** ages 24/25/64/65, power 99/100 kW, fault % 0/100/100.01.
- **Equivalence partitioning:** one representative per class (young / standard / senior).
- **Security:** missing/expired/forged tokens, role checks, SQL injection, XSS, CORS, error leakage.
- **Data integrity:** after a write, check the database directly, not just the response.
- **Regression:** the whole suite is re-run after every change; known-bug tests flip to XPASS when fixed.
- **Exploratory (manual):** clicking around with no script; anything found is written up as a new bug + test.

## 5. Test environment
| Item | Value |
|---|---|
| Database | PostgreSQL 16 in Docker (`docker-compose.test.yml`), port **5544**, wiped and re-seeded before **every** test |
| Backend under test | API tests: in-process TestClient. E2E: uvicorn on port **8001** |
| Frontend under test | Vite dev server on port **5174**, proxying `/api` to 8001 |
| Browser | Chromium (Playwright), headless by default |
| Test data | `db/seed.sql` (3 policyholders, 3 policies, 2 claims, 2 accounts) |

**Safety rule:** tests refuse to run if `TEST_DATABASE_URL` matches the
`DATABASE_URL` in `backend/.env`, and with no test DB configured the backend
is pointed at an address that cannot connect.

## 6. Entry and exit criteria
**Start testing when:** the app starts, `db/schema.sql` and `seed.sql` load cleanly, and the test DB container is healthy.

**A test run "passes" when:**
- 0 `FAILED` and 0 `ERROR`
- every `XFAIL` links to an open bug in `BUG_REPORTS.md`
- 0 `XPASS` (an XPASS means a bug was fixed: close it and remove its marker)

**Release-ready (beyond this class project) would need:** no open Critical or High bugs.

## 7. Risks
| Risk | Mitigation |
|---|---|
| Tests wipe real data | Separate DB on its own port, plus the safety check above |
| Flaky UI tests (timing) | Playwright auto-waiting `expect()`, never `sleep()`; wait for network responses when the UI updates asynchronously |
| Tests depend on the clock | Unit tests pass a fixed `as_of` date; API tests use one clock (see BUG-023) |
| Test itself is wrong | Expected values worked out by hand from the formula; every unexpected failure investigated before filing a bug (see FIX_REPORT.md, "Problems we hit while fixing") |

## 8. Deliverables
- Automated tests: `testing/unit`, `testing/api`, `testing/e2e`
- HTML report: `testing/reports/report.html` (from `run_tests.ps1`)
- [`TEST_CASES.md`](TEST_CASES.md): what is covered
- [`BUG_REPORTS.md`](BUG_REPORTS.md): what is broken
- [`FIX_REPORT.md`](FIX_REPORT.md): how each bug was fixed
