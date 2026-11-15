# AutoRisk — Bug Reports

Every issue found while testing AutoRisk. Each one was **reproduced by an
automated test** before it was fixed.

> **Status (2026-11-14): all 23 bugs are fixed.** How each one was fixed,
> and the before/after test results, are in [FIX_REPORT.md](FIX_REPORT.md).
> The tests that reproduced them now pass and stay in the suite as
> **regression tests** (marked `# Regression test for BUG-xxx`), so if a
> bug ever comes back, the suite fails.
>
> The steps / expected / actual below describe the app **before** the fixes.

For a NEW bug: write a test for it and mark it `@known_bug("BUG-0XX", "...")`
(from `support`). It shows as `XFAIL` until fixed; once the fix lands, the
test passes, pytest reports `XPASS(strict)` as a failure, and that tells you
to remove the marker and close the bug here.

**Environment:** Windows 11, Python 3.13, FastAPI 0.115, React 18 + Vite 5,
PostgreSQL 16 (test container), seed data from `db/seed.sql`.

## Severity scale

| Severity | Meaning |
|---|---|
| **Critical** | Security hole or data exposure; must fix before anyone real uses the app |
| **High** | Core feature broken or wrong data saved, with no workaround |
| **Medium** | Feature works but gives wrong/confusing results, or crashes on bad input |
| **Low** | Cosmetic, minor inconsistency, or rare edge case |

## Summary

| ID | Title | Severity | Area | Found by | Status |
|---|---|---|---|---|---|
| BUG-001 | Data endpoints don't require login | Critical | Security | `api/test_security.py` | **Fixed** |
| BUG-002 | No role checks: customers can read and change all data | Critical | Security | `api/test_security.py` | **Fixed** |
| BUG-003 | Duplicate license number crashes with 500 | High | Policyholders | `api/test_policyholders.py`, E2E | **Fixed** |
| BUG-004 | Invalid risk tier crashes with 500 | Medium | Policyholders | `api/test_policyholders.py` | **Fixed** |
| BUG-005 | Unknown region id crashes with 500 | Medium | Policyholders | `api/test_policyholders.py` | **Fixed** |
| BUG-006 | Fault % outside 0–100 crashes with 500 | Medium | Claims | `api/test_claims.py` | **Fixed** |
| BUG-007 | Impossible dates accepted for policyholders | Medium | Policyholders | `api/test_policyholders.py` | **Fixed** |
| BUG-008 | Claims accepted outside the policy period / in the future | Medium | Claims | `api/test_claims.py` | **Fixed** |
| BUG-009 | Quote form offers 16 region/coverage pairs; only 3 work | High | Quote | `api/test_quote.py`, E2E | **Fixed** |
| BUG-010 | Quote accepts impossible inputs (negative premium possible) | High | Quote / Pricing | `api/test_quote.py`, unit | **Fixed** |
| BUG-011 | Driving experience and car age are ignored by pricing | Medium | Pricing | `unit/test_pricing.py` | **Fixed** |
| BUG-013 | "Total Claims Paid" includes unpaid (Pending) payments | Medium | Dashboard | `api/test_read_endpoints.py` | **Fixed** |
| BUG-014 | `%` and `_` in search act as wildcards | Low | Policyholders | `api/test_policyholders.py` | **Fixed** |
| BUG-015 | Duplicate-email check is case-sensitive | Low | Policyholders | `api/test_policyholders.py` | **Fixed** |
| BUG-016 | Blank names accepted; over-long text crashes with 500 | Low | Validation | `api/test_policyholders.py`, `api/test_claims.py` | **Fixed** |
| BUG-017 | No rate limiting on login (password guessing) | Medium | Security | `api/test_auth.py` | **Fixed** |
| BUG-018 | Validation errors shown as "[object Object]" | Medium | Frontend | E2E | **Fixed** |
| BUG-019 | Region filter lost after adding a policyholder | Low | Frontend | E2E | **Fixed** |
| BUG-020 | Form labels not linked to inputs (accessibility) | Low | Frontend | E2E | **Fixed** |
| BUG-021 | Payments for a non-existent claim return 200 `[]` | Low | Claims | `api/test_claims.py` | **Fixed** |
| BUG-022 | Negative `?limit=` crashes recent-claims with 500 | Low | Dashboard | `api/test_read_endpoints.py` | **Fixed** |
| BUG-023 | App and database disagree on what "today" is | Low | Dates | `api/test_quote.py` | **Fixed** |
| BUG-024 | Hard-coded JWT secret fallback; token in localStorage | Medium | Security | Code review | **Fixed** |

(BUG-012 was merged into BUG-010 because they turned out to be the same problem.)

---

## Critical

### BUG-001 — Data endpoints don't require login
- **Severity:** Critical · **Area:** Security (authentication)
- **Steps:** With no `Authorization` header, call `GET /api/policyholders`
  (or `/api/claims`, `/api/policies`, `/api/vehicles`, `/api/dashboard/summary`,
  `POST /api/quote`, `POST /api/policyholders`, `POST /api/claims`).
- **Expected:** `401 Unauthorized`.
- **Actual:** `200 OK` with the full data. Anyone who can reach the API can
  read every customer's name, date of birth, licence number, email, and
  phone, and can create records. The React login screen only *hides* pages;
  it doesn't protect the data.
- **Cause:** Only `/api/auth/me` uses `Depends(auth.get_current_account)`.
- **Suggested fix:** Add `dependencies=[Depends(get_current_account)]` to every
  data router (`APIRouter(..., dependencies=[...])`) in `backend/app/routers/*.py`.
- **Test:** `api/test_security.py::test_endpoint_rejects_requests_without_a_token` (11 cases)

### BUG-002 — No role checks: customers can read and change all data
- **Severity:** Critical · **Area:** Security (authorization)
- **Steps:** Log in as `jordan.reyes@example.com` / `demo1234` (a Customer),
  then call `GET /api/policyholders` with that token.
- **Expected:** Only Jordan's own record (policyholder 1). Creating
  policyholders should be `403 Forbidden`.
- **Actual:** All policyholders come back, and the customer can create new ones.
- **Note:** Fixing BUG-001 won't fix this; it also needs an `account_type` / `admin_role` check.
- **Tests:** `api/test_security.py::test_customer_only_sees_their_own_policyholder_record`,
  `test_customer_cannot_create_policyholders`

## High

### BUG-003 — Duplicate license number crashes with 500
- **Steps:** `POST /api/policyholders` with a new email but `license_number: "D1234567"` (Jordan's).
- **Expected:** `409 Conflict`, "A policyholder with that license number already exists".
- **Actual:** `500 Internal Server Error`. In the UI the modal just says "Internal Server Error".
- **Cause:** The code checks for a duplicate email before inserting but not a
  duplicate licence, so the database's UNIQUE constraint raises an
  `IntegrityError` that nothing catches.
- **Tests:** `api/test_policyholders.py::test_duplicate_license_number_is_409`,
  `e2e/test_policyholders_ui.py::test_duplicate_license_shows_helpful_message`

### BUG-009 — Quote form offers 16 region/coverage pairs; only 3 work
- **Steps:** On New Quote, pick any coverage except **Liability** (e.g.
  **Collision**, which is listed first), or pick the **National** region.
- **Expected:** A premium, or those options left out of the dropdown.
- **Actual:** "No current rate table for that region/coverage combination".
  Only Liability in Regions A, B and C has a rate table, so 13 of the 16
  combinations the form offers always fail.
- **Suggested fix:** Either add rate tables to `seed.sql`, or have the form
  only offer combinations that have a current rate table.
- **Tests:** `api/test_quote.py::test_every_region_and_coverage_offered_in_the_form_can_be_quoted`,
  `e2e/test_quote_ui.py::test_collision_coverage_can_be_quoted`

### BUG-010 — Quote accepts impossible inputs
- **Steps:** `POST /api/quote` with `bonus_malus_coefficient: -1`.
- **Expected:** `422` validation error.
- **Actual:** `200` with **`estimated_premium: -545.74`**, a negative price.
  These were also accepted:

  | Input | Result |
  |---|---|
  | `bonus_malus_coefficient: 0` | $0.00 premium |
  | `vehicle_power_kw: -500` | 200 OK |
  | `vehicle_manufacture_year: 3000` | 200 OK |
  | `date_of_birth: 2090-01-01` | 200 OK, driver priced as "young" (negative age) |
  | licence issued before the driver was born | 200 OK |

- **Note:** The HTML form has `min/max` on Bonus-Malus, but that only stops
  people using the browser form; the API accepts anything.
- **Suggested fix:** Add Pydantic constraints in `schemas.QuoteRequest`, for example
  `Field(gt=0, le=3.5)` and `Field(ge=0, le=1000)`, plus a validator for date
  order.
- **Tests:** `api/test_quote.py::test_impossible_input_is_422` (6 cases),
  `unit/test_pricing.py::TestKnownPricingBugs::test_negative_bonus_malus_is_rejected`

## Medium

### BUG-004 — Invalid risk tier crashes with 500
- `POST /api/policyholders` with `risk_tier: "Extreme"` → **500** (expected 422).
  The database CHECK constraint rejects it, but the API doesn't validate it first.
  Fix: `risk_tier: Optional[Literal["Low","Medium","High"]]`.
- Test: `api/test_policyholders.py::test_invalid_risk_tier_is_422`

### BUG-005 — Unknown region id crashes with 500
- `POST /api/policyholders` with `region_id: 999` → **500** (foreign-key violation). Expected 422.
- Test: `api/test_policyholders.py::test_unknown_region_is_422`

### BUG-006 — Fault % outside 0–100 crashes with 500
- `POST /api/claims` with `fault_percentage: 150` (also `-0.01`, `100.01`) → **500**. Expected 422.
  Fix: `fault_percentage: float = Field(0, ge=0, le=100)`.
- Test: `api/test_claims.py::test_fault_percentage_out_of_range_is_422` (3 cases)

### BUG-007 — Impossible dates accepted for policyholders
- A date of birth of `2090-01-01` → **201 Created**.
- A licence issue date of `1950-01-01` for someone born in 1988 → **201 Created**.
- Expected: 422 for both.
- Tests: `test_future_date_of_birth_is_422`, `test_license_before_birth_is_422`

### BUG-008 — Claims accepted outside the policy period or in the future
- A claim dated `2026-10-01` on policy 3 (which ended `2026-09-01`) → **201**.
- A claim dated 30 days in the future → **201**.
- Expected: 400/422; you can't claim on a policy that wasn't active that day.
- Tests: `api/test_claims.py::test_claim_outside_policy_period_is_rejected`, `test_future_claim_date_is_rejected`

### BUG-011 — Driving experience and car age are ignored by pricing
- `license_issue_date` and `vehicle_manufacture_year` are required on the
  quote form but `pricing.calculate_quote()` never uses them. Someone who
  got their licence last month pays the same as a driver with 26 years'
  experience. This is a requirements/design gap: the form asks for data
  that has no effect on the result.
- Test: `unit/test_pricing.py::TestKnownPricingBugs::test_new_driver_pays_more_than_experienced_driver`

### BUG-013 — "Total Claims Paid" includes unpaid (Pending) payments
- **Steps:** Add a `claim_payment` row with `status = 'Pending'`, amount 500.
- **Expected:** The Total Claims Paid KPI stays at $2400.00.
- **Actual:** It shows $2900.00, because `dashboard_summary` sums every payment
  regardless of status.
- Test: `api/test_read_endpoints.py::test_pending_payments_not_counted_as_paid`

### BUG-017 — No rate limiting on login
- 10 wrong passwords in a row all return 401, with no lockout, delay, or 429.
  An attacker can keep guessing passwords indefinitely.
- Test: `api/test_auth.py::test_repeated_failed_logins_are_throttled`

### BUG-018 — Validation errors shown as "[object Object]"
- **Steps:** On the login page, type `not-an-email` as the email and click Sign in.
- **Expected:** A readable message such as "Enter a valid email address".
- **Actual:** The red error box shows **`[object Object]`**.
- **Cause:** On a 422, FastAPI sends `detail` as a *list* of error objects.
  `frontend/src/api/client.js` does `new Error(body.detail)`, which turns the
  list into the text "[object Object]". This affects every form.
- **Fix:** If `detail` is an array, join each item's `msg`.
- Test: `e2e/test_login_and_navigation.py::test_invalid_email_on_login_shows_readable_error`

### BUG-024 — Hard-coded JWT secret fallback; token stored in localStorage *(found by code review)*
- `backend/app/auth.py`: if `JWT_SECRET` is missing, the app quietly uses
  `"dev-only-secret-change-me"`. That value is in the source code, so anyone
  could forge an admin token. The app should refuse to start without the variable.
- `frontend/src/context/AuthContext.jsx` keeps the token in `localStorage`, which
  any injected script can read. (Acceptable for a class project; note it as a known risk.)
- The frontend never checks whether the token has expired. After 8 hours the
  user still *looks* logged in. (Today this has no visible effect only because
  of BUG-001.)
- No automated test; this was found by reading the code (static review).

## Low

| ID | Steps | Expected | Actual | Test |
|---|---|---|---|---|
| BUG-014 | Search policyholders for `%` | No results (nobody's name contains %) | Every policyholder | `test_percent_sign_is_searched_literally` |
| BUG-015 | Create a policyholder with email `JORDAN.REYES@example.com` | 409 duplicate | 201; two records for the same person | `test_duplicate_email_with_different_case_is_409` |
| BUG-016 | First name `"   "` / first name of 51 chars / claim type of 31 chars | 422 | 201 for blank; **500** for too long | `test_blank_first_name_is_422`, `test_too_long_first_name_is_422`, `test_too_long_claim_type_is_422` |
| BUG-019 | Filter Policyholders by Region B, then add a policyholder | List still filtered to Region B | List shows everyone; the filter still says "Region B" | `e2e/...::test_region_filter_still_applied_after_adding` |
| BUG-020 | Inspect the Add Policyholder and Quote forms | `<label for=...>` linked to each input | Labels not linked; screen readers can't name the fields, and clicking a label doesn't focus its input | `e2e/...::test_add_form_fields_are_reachable_by_label` |
| BUG-021 | `GET /api/claims/999/payments` | 404 Claim not found | 200 `[]` | `test_payments_for_missing_claim_is_404` |
| BUG-022 | `GET /api/dashboard/recent-claims?limit=-1` | 422 | **500** | `test_negative_limit_is_422` |
| BUG-023 | Compare `date.today()` in the app with `CURRENT_DATE` in Postgres after 6 pm US Central | Same day | App says Nov 11, database says Nov 12. The app uses the server's local clock for ages/rate tables; the DB stamps `created_at` in UTC | `test_app_and_database_use_the_same_time_zone` |

---

## How to report a new bug

Copy this template, give it the next number, and add a row to the summary table.

```markdown
### BUG-0XX — <short title saying what's wrong>
- **Severity:** Critical / High / Medium / Low · **Area:** <page or endpoint>
- **Steps:** 1. ... 2. ... 3. ...   (exact enough that someone else gets the same result)
- **Expected:** <what should happen, and why: spec, common sense, DB constraint...>
- **Actual:** <what happened: status code, message, screenshot>
- **Test:** <path::test_name> marked @known_bug("BUG-0XX", "...")
```

Then write the automated test that reproduces it (the tests in `api/` and `e2e/` are good templates).
