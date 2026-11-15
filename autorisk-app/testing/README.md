# AutoRisk — Automated Testing

The test project for AutoRisk: automated test scripts, the test
documentation, and a log of every bug found.

## Quick start (Windows, from the `autorisk-app` folder)

```powershell
.\testing\run_tests.ps1 setup     # once: pytest, Playwright, Chromium
# start Docker Desktop, then:
.\testing\run_tests.ps1           # run everything + HTML report
```

Other ways to run:

| Command | What it runs | Needs |
|---|---|---|
| `.\testing\run_tests.ps1 unit` | pricing formula tests (<1 s) | nothing |
| `.\testing\run_tests.ps1 api` | backend API tests (~30 s) | Docker |
| `.\testing\run_tests.ps1 e2e` | browser tests (~1–2 min) | Docker, Node |
| `.\testing\run_tests.ps1 api -k quote` | only tests with "quote" in their name | |
| `.\testing\run_tests.ps1 api -m security` | only security tests | |
| `.\testing\run_tests.ps1 db-down` | stop/delete the test database | |

Afterwards, open **`testing\reports\report.html`**.

## Reading the results

| pytest says | Meaning | What to do |
|---|---|---|
| `PASSED` | works as expected | nothing |
| `XFAIL` | **known bug**, still present | see `docs/BUG_REPORTS.md` |
| `FAILED` | something that worked is broken, **or** a new bug | investigate (the test itself could also be wrong) |
| `XPASS(strict)` | a known bug was **fixed** | remove its `@known_bug` marker and close the bug |
| `ERROR` | the test couldn't even run (setup problem) | read the message; is Docker running? |

## Your real data is safe
- Tests use their **own** PostgreSQL in Docker (port **5544**, stored in RAM).
  They never use the Neon database in `backend/.env`.
- The suite **refuses to run** if the test DB URL equals the real one.
- The browser tests start their own backend and frontend on ports
  **8001 / 5174**, so your normal app on 8000 / 5173 is untouched.

## What's here

```
testing/
├── run_tests.ps1            one-command runner
├── docker-compose.test.yml  throwaway test Postgres
├── .env.test.example        test settings (copied to .env.test)
├── pytest.ini               markers, strict-xfail
├── conftest.py              points the backend at the test DB
├── support/                 shared helpers (DB reset, known_bug, UI helpers)
├── unit/                    test_pricing.py: the premium formula
├── api/                     auth, security, policyholders, claims, quote, dashboard
├── e2e/                     login/navigation, policyholders page, quote page
├── reports/                 HTML report + E2E server logs (generated)
└── docs/
    ├── TEST_PLAN.md         scope, levels, environment, pass criteria
    ├── TEST_CASES.md        every test case and its result
    ├── BUG_REPORTS.md       every bug: steps, expected, actual, severity
    ├── FIX_REPORT.md        how each bug was fixed (+ FIX_REPORT.html for presenting)
```

## Results at a glance
Testing found **23 bugs** (2 Critical, 3 High, 10 Medium, 8 Low), including
data endpoints that needed no login and quotes that could come out negative.
**All 23 are fixed**, and the suite (232 tests) passes. See
[docs/FIX_REPORT.md](docs/FIX_REPORT.md) for each fix and
[docs/BUG_REPORTS.md](docs/BUG_REPORTS.md) for the original reports.

## App change made for testability
`frontend/vite.config.js` reads an optional `API_PROXY_TARGET` environment
variable, so the E2E tests can point their own copy of the frontend at their
own backend. Without it, behaviour is unchanged (proxies to `localhost:8000`).
The E2E tests run the **production build** (`vite build` + `vite preview`).
