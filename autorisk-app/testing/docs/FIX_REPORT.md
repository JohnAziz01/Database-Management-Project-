# AutoRisk — Bug Fix Report

CSCI-4560 Database Management Systems Project · 14 November 2026

## Summary

| | Before fixes | After fixes |
|---|---|---|
| Bugs open | 23 | **0** |
| Automated tests | 195 (148 pass, 47 reproduce known bugs) | **232 (all pass)** |
| Critical security holes | 2 | 0 |
| Different inputs that crashed the server (HTTP 500) | 7 | 0 |

Severity of the 23 bugs: **2 Critical · 3 High · 10 Medium · 8 Low**.

Every bug was first reproduced by an automated test, then fixed, and the
test was kept as a **regression test**: if the bug ever comes back, the
suite fails.

## How we tested

| Level | Tool | Tests | What it checks |
|---|---|---|---|
| Unit | pytest | 44 | the premium formula in `pricing.py` |
| API / integration | pytest + FastAPI TestClient + PostgreSQL 16 (Docker) | 153 | every endpoint: status codes, data, validation, security |
| End-to-end | pytest + Playwright (Chromium) | 35 | real user flows in the React UI |

The test database is a separate throwaway Postgres, reset to the seed data
before every test, so tests never touch the real (Neon) database.

## Bugs and fixes

### Critical

| ID | Problem (before) | Fix (after) | Where |
|---|---|---|---|
| BUG-001 | No endpoint except `/me` required a login: anyone could read every customer's personal data with a plain HTTP request | Every data router now has `dependencies=[Depends(get_current_account)]`: no token → 401 | `routers/*.py` |
| BUG-002 | A Customer account could read and create every customer's records | New `require_admin` and `customer_scope` dependencies. Customers see only their own policyholder record, vehicles, policies and claims; creating policyholders and the company dashboard are admin-only (403) | `auth.py`, `routers/*.py` |

### High

| ID | Problem (before) | Fix (after) | Where |
|---|---|---|---|
| BUG-003 | Duplicate licence number → **500** crash | Checked before insert → **409** with a clear message; `IntegrityError` safety net for races | `routers/policyholders.py` |
| BUG-009 | Quote form offered 16 region × coverage pairs; only 3 had prices | Added rate tables for the 3 missing coverages; new `GET /api/quote/options` lists only priceable pairs; the form's dropdowns use it | `seed.sql`, `routers/quote.py`, `Quote.jsx` |
| BUG-010 | Quote accepted a negative bonus-malus and returned a **negative premium** (−$545.74) | Range checks in `QuoteRequest` (422) and `ValueError` guards inside `calculate_quote()` | `schemas.py`, `pricing.py` |

### Medium

| ID | Problem (before) | Fix (after) | Where |
|---|---|---|---|
| BUG-004 | Invalid risk tier → 500 | `Literal["Low","Medium","High"]` → 422 | `schemas.py` |
| BUG-005 | Unknown region id → 500 | Region checked first → 422 | `routers/policyholders.py` |
| BUG-006 | Fault % outside 0–100 → 500 | `Field(ge=0, le=100)` → 422 | `schemas.py` |
| BUG-007 | Future birth dates and licences issued before birth accepted | Date validators → 422 | `schemas.py` |
| BUG-008 | Claims accepted after the policy ended, or dated in the future | Claim date must be inside the policy period and not in the future → 422 | `schemas.py`, `routers/claims.py` |
| BUG-011 | Driving experience ignored by pricing | New experience factor: < 2 years licensed +20 %, < 5 years +10 % | `pricing.py` |
| BUG-013 | "Total Claims Paid" counted Pending payments | Sum filtered to `status = 'Paid'` | `routers/dashboard.py` |
| BUG-017 | Unlimited password guessing | 5 failed logins per email in 15 minutes → 429 | `auth.py`, `routers/auth.py` |
| BUG-018 | Validation errors displayed as "[object Object]" | `formatDetail()` turns FastAPI's error list into readable text | `frontend/src/api/client.js` |
| BUG-024 | Hard-coded fallback JWT secret; UI stayed "logged in" with a dead token | App refuses to start without `JWT_SECRET`; any 401 signs the user out and returns to the login page | `auth.py`, `client.js` |

### Low

| ID | Problem (before) | Fix (after) | Where |
|---|---|---|---|
| BUG-014 | `%` / `_` in search matched everything | LIKE wildcards escaped | `routers/policyholders.py` |
| BUG-015 | `JORDAN.REYES@…` treated as a different email | Emails stored and compared in lower case; login is case-insensitive too | `schemas.py`, routers |
| BUG-016 | Blank names accepted; too-long text → 500 | `StringConstraints(strip_whitespace, min_length=1, max_length=column size)` | `schemas.py` |
| BUG-019 | Region filter lost after adding a policyholder | Refresh re-uses the search **and** region filters | `Policyholders.jsx` |
| BUG-020 | Form labels not linked to inputs (accessibility) | `htmlFor` / `id` on all 16 fields | `Policyholders.jsx`, `Quote.jsx` |
| BUG-021 | Payments of a non-existent claim → 200 `[]` | → 404 "Claim not found" | `routers/claims.py` |
| BUG-022 | `?limit=-1` → 500 | `Query(ge=1, le=100)` → 422 | `routers/dashboard.py` |
| BUG-023 | App used local time for "today", the database used UTC (different days after 6 pm) | New `app/clock.py`; the whole app uses UTC "today" like Postgres | `clock.py`, `pricing.py`, `quote.py`, `schemas.py` |

## Problems we hit while fixing (and what they taught us)

| What happened | Cause | Fix |
|---|---|---|
| 2 unit tests failed after the BUG-010 fix | They priced a 0 kW car, which the fix made invalid on purpose | Updated the tests. When a requirement changes, its tests must change too |
| Browser tests passed in some runs and failed in others (flaky) | 1: a test's last API request was still running while the next test reset the database → Postgres **deadlock** | Reset with one `TRUNCATE` instead of dropping tables, and retry on deadlock |
| Still flaky: whole runs collapsed with "connection refused" | 2: the Node.js runtime crashed natively (exit code 0xC0000409) about 2 runs in 10. The build output sat in the OneDrive-synced folder | Built into the system temp folder, started Node directly in its own process group, and restart automatically if it ever dies. Result: 0 crashes in the next runs |

**Lesson:** a failing test does not always mean the app is wrong. We
investigated every unexpected failure (logs, screenshots, exit codes)
before deciding whether to fix the app, the test, or the environment.

## Known limitations (deliberate)

- **Login token in `localStorage`.** Acceptable for a class project. A production app would use an HttpOnly cookie.
- **Login throttling is kept in memory.** Fine for one server; several servers would need a shared store (Redis or the DB).
- **Vehicle age is validated but not priced.** Whether new or old cars should cost more is a business decision for the team.
- **Customers see "Admin access required" on the Dashboard.** The KPIs are company-wide; a customer dashboard is future work.
- **The Neon database still has the old rate tables.** The new rows are in `db/seed.sql`. `run.ps1 reset-db` applies them, but it **wipes all data**; alternatively, run just the new `INSERT INTO rate_table …` block.

## How to verify

```powershell
.\testing\run_tests.ps1     # all tests + HTML report in testing\reports\report.html
```
