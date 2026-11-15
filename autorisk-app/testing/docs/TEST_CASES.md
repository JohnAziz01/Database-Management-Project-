# AutoRisk — Test Case Catalog

Each row is one test case, and the **Automated by** column names the test
function that runs it. Parametrized tests (one function, many inputs) are
listed once, with their inputs.

Result legend: ✅ pass · ✅ fixed (BUG-xxx) = this case found a bug, the bug was fixed, and the test now passes as a regression test (see [FIX_REPORT.md](FIX_REPORT.md))

## Authentication — `api/test_auth.py`
| ID | Case | Expected | Result | Automated by |
|---|---|---|---|---|
| TC-AUTH-01 | Admin logs in with valid credentials | 200, bearer token, type Admin | ✅ | `test_admin_can_log_in` |
| TC-AUTH-02 | Customer logs in | 200, type Customer | ✅ | `test_customer_can_log_in` |
| TC-AUTH-03 | Login records `last_login_at` in the DB | not null | ✅ | `test_login_records_last_login_time` |
| TC-AUTH-04 | `/me` with a valid token | 200, own email | ✅ | `test_me_returns_the_logged_in_account` |
| TC-AUTH-05 | Wrong password | 401 "Invalid email or password" | ✅ | `test_wrong_password_is_rejected` |
| TC-AUTH-06 | Unknown email gets the same response as a wrong password (no user enumeration) | identical 401 | ✅ | `test_unknown_email_gives_same_message_as_wrong_password` |
| TC-AUTH-07 | Password is case-sensitive | 401 | ✅ | `test_password_is_case_sensitive` |
| TC-AUTH-08 | Malformed body: bad email / no password / no email / empty | 422 | ✅ | `test_malformed_login_requests_get_422` |
| TC-AUTH-09 | Disabled account | 403 | ✅ | `test_disabled_account_cannot_log_in` |
| TC-AUTH-10 | SQL injection in login | 401/422 | ✅ | `test_sql_injection_in_login_is_rejected` |
| TC-AUTH-11 | `/me` without a token / with a garbage token | 401 | ✅ | `test_me_without_token_is_401`, `test_me_with_garbage_token_is_401` |
| TC-AUTH-12 | Expired token | 401 | ✅ | `test_expired_token_is_rejected` |
| TC-AUTH-13 | Token signed with a different secret (forged) | 401 | ✅ | `test_token_signed_with_another_secret_is_rejected` |
| TC-AUTH-14 | Token of an account disabled after login | 401 | ✅ | `test_token_stops_working_when_account_is_disabled` |
| TC-AUTH-15 | 10 failed logins in a row are throttled | 429/423 | ✅ fixed (BUG-017) | `test_repeated_failed_logins_are_throttled` |

## Security — `api/test_security.py`
| ID | Case | Expected | Result | Automated by |
|---|---|---|---|---|
| TC-SEC-01 | 11 data endpoints called with no token | 401 | ✅ fixed (BUG-001) | `test_endpoint_rejects_requests_without_a_token` |
| TC-SEC-02 | Customer lists policyholders | only their own record | ✅ fixed (BUG-002) | `test_customer_only_sees_their_own_policyholder_record` |
| TC-SEC-03 | Customer creates a policyholder | 403 | ✅ fixed (BUG-002) | `test_customer_cannot_create_policyholders` |
| TC-SEC-04 | Health and login stay public | 200 / 401 | ✅ | `test_public_endpoints_stay_public` |
| TC-SEC-05 | CORS allows the frontend origin | header present | ✅ | `test_cors_allows_the_frontend_origin` |
| TC-SEC-06 | CORS blocks other origins | header absent | ✅ | `test_cors_blocks_other_origins` |
| TC-SEC-07 | 500 errors don't leak stack traces | no "Traceback" | ✅ | `test_server_errors_do_not_leak_stack_traces` |
| TC-SEC-08 | No endpoint returns password hashes | absent | ✅ | `api/test_read_endpoints.py::test_no_endpoint_leaks_password_hashes` |
| TC-SEC-09 | SQL injection in search | 200 `[]` | ✅ | `api/test_policyholders.py::test_search_is_safe_from_sql_injection` |
| TC-SEC-10 | XSS: `<img onerror>` in a name renders as text | not executed | ✅ | `e2e/test_policyholders_ui.py::test_script_in_name_is_shown_as_text_not_run` |

## Policyholders — `api/test_policyholders.py`
| ID | Case | Expected | Result | Automated by |
|---|---|---|---|---|
| TC-PH-01 | List all, in id order | Jordan, Casey, Priya | ✅ | `test_lists_all_seeded_policyholders_in_id_order` |
| TC-PH-02 | Response fields | exact field set | ✅ | `test_response_has_expected_fields` |
| TC-PH-03 | Search by first name / last name (case-insensitive) / email / partial licence / no match | matching rows | ✅ | `test_search` (6 inputs) |
| TC-PH-04 | Filter by region; search + region combined | matching rows | ✅ | `test_filter_by_region`, `test_search_and_region_filter_combine` |
| TC-PH-05 | `%` searched literally | `[]` | ✅ fixed (BUG-014) | `test_percent_sign_is_searched_literally` |
| TC-PH-06 | Get by id / missing id / non-numeric id | 200 / 404 / 422 | ✅ | `test_get_one`, `test_get_missing_is_404`, `test_get_non_numeric_id_is_422` |
| TC-PH-07 | Create valid; row is in the DB | 201, count = 4 | ✅ | `test_create_returns_201_and_saves_the_row` |
| TC-PH-08 | Optional fields omitted | 201 | ✅ | `test_optional_fields_can_be_omitted` |
| TC-PH-09 | Each required field missing | 422 | ✅ | `test_missing_required_field_is_422` (6) |
| TC-PH-10 | Invalid email formats / impossible date (Feb 30) | 422 | ✅ | `test_invalid_email_is_422` (4), `test_invalid_date_is_422` |
| TC-PH-11 | Duplicate email | 409 | ✅ | `test_duplicate_email_is_409` |
| TC-PH-12 | Duplicate licence | 409 | ✅ fixed (BUG-003) | `test_duplicate_license_number_is_409` |
| TC-PH-13 | Duplicate email, different case | 409 | ✅ fixed (BUG-015) | `test_duplicate_email_with_different_case_is_409` |
| TC-PH-14 | Invalid risk tier | 422 | ✅ fixed (BUG-004) | `test_invalid_risk_tier_is_422` |
| TC-PH-15 | Unknown region id | 422 | ✅ fixed (BUG-005) | `test_unknown_region_is_422` |
| TC-PH-16 | Future DOB; licence before birth | 422 | ✅ fixed (BUG-007) | `test_future_date_of_birth_is_422`, `test_license_before_birth_is_422` |
| TC-PH-17 | Blank name; 51-char name | 422 | ✅ fixed (BUG-016) | `test_blank_first_name_is_422`, `test_too_long_first_name_is_422` |

## Claims — `api/test_claims.py`
| ID | Case | Expected | Result | Automated by |
|---|---|---|---|---|
| TC-CL-01 | List, newest id first | [2, 1] | ✅ | `test_lists_claims_newest_id_first` |
| TC-CL-02 | Filter by status Paid / Pending / Denied | [1] / [2] / [] | ✅ | `test_filter_by_status` |
| TC-CL-03 | Create; default status Open | 201 | ✅ | `test_create_claim` |
| TC-CL-04 | Fault % boundaries 0, 0.01, 99.99, 100 | 201 | ✅ | `test_fault_percentage_boundaries_accepted` |
| TC-CL-05 | Fault % -0.01, 100.01, 150 | 422 | ✅ fixed (BUG-006) | `test_fault_percentage_out_of_range_is_422` |
| TC-CL-06 | Unknown policy / missing claim type | 404 / 422 | ✅ | `test_claim_for_missing_policy_is_404`, `test_missing_claim_type_is_422` |
| TC-CL-07 | Claim after the policy ended; claim in the future | rejected | ✅ fixed (BUG-008) | `test_claim_outside_policy_period_is_rejected`, `test_future_claim_date_is_rejected` |
| TC-CL-08 | 31-char claim type | 422 | ✅ fixed (BUG-016) | `test_too_long_claim_type_is_422` |
| TC-CL-09 | Payments of claim 1 / claim 2 | 1 payment / [] | ✅ | `test_payments_for_claim`, `test_claim_without_payments_returns_empty_list` |
| TC-CL-10 | Payments of a non-existent claim | 404 | ✅ fixed (BUG-021) | `test_payments_for_missing_claim_is_404` |

## Quote — `api/test_quote.py`
| ID | Case | Expected | Result | Automated by |
|---|---|---|---|---|
| TC-QT-01 | Region A Liability, 138 kW, BM 0.90 | $491.16, Low | ✅ | `test_quote_matches_hand_calculation` |
| TC-QT-02 | Each region uses its own base rate | 450 / 380 / 520 | ✅ | `test_each_region_uses_its_own_rate_table` |
| TC-QT-03 | 20-year-old gets the young factor | 1.60 | ✅ | `test_young_driver_gets_region_young_factor` |
| TC-QT-04 | Expired rate table ignored; newest wins; future one not used yet | 404 / 999 / 450 | ✅ | `test_expired_rate_table_is_ignored`, `test_newest_rate_table_wins`, `test_future_rate_table_not_used_yet` |
| TC-QT-05 | Unknown region; region with no rate table | 404 | ✅ | `test_unknown_region_is_404`, `test_region_without_rate_table_is_404` |
| TC-QT-06 | Missing fields; text in a number field | 422 | ✅ | `test_missing_field_is_422` (4), `test_text_in_number_field_is_422` |
| TC-QT-07 | All 16 region × coverage pairs offered in the form | all quotable | ✅ fixed (BUG-009) | `test_every_region_and_coverage_offered_in_the_form_can_be_quoted` |
| TC-QT-08 | BM -1 / 0, power -500, year 3000, future DOB, licence before birth | 422 | ✅ fixed (BUG-010) | `test_impossible_input_is_422` (6) |
| TC-QT-09 | App and DB use the same time zone | equal offsets | ✅ fixed (BUG-023) | `test_app_and_database_use_the_same_time_zone` |

## Pricing formula — `unit/test_pricing.py`
| ID | Case | Result | Automated by |
|---|---|---|---|
| TC-PR-01 | Age: birthday today / tomorrow / yesterday; leap-day birthdays | ✅ | `TestAge` |
| TC-PR-02 | Age factor at 24, 25-tomorrow, 25, 40, 65-tomorrow, 65, 80 | ✅ | `TestAgeFactor` (7) |
| TC-PR-03 | Power bands 0, 50, 99, 100, 149, 150, 250 kW; more power never costs less | ✅ | `TestVehiclePowerFactor` |
| TC-PR-04 | Hand-calculated premium; young > standard; linear in BM; frequency cap 35%; pure premium = freq × severity | ✅ | `TestPremium` |
| TC-PR-05 | Risk level thresholds 1.39 / 1.40 / 2.49 / 2.50 × base | ✅ | `TestRiskLevel` |
| TC-PR-06 | Brand-new driver pays more than an experienced one | ✅ fixed (BUG-011) | `test_new_driver_pays_more_than_experienced_driver` |
| TC-PR-07 | Negative bonus-malus rejected | ✅ fixed (BUG-010) | `test_negative_bonus_malus_is_rejected` |

## Dashboard and lists — `api/test_read_endpoints.py`
| ID | Case | Result | Automated by |
|---|---|---|---|
| TC-RD-01 | Health; regions sorted + hierarchy; coverages sorted, Liability mandatory | ✅ | `test_health`, `test_regions_sorted_by_name`, `test_region_hierarchy`, `test_coverages_sorted_and_liability_mandatory` |
| TC-RD-02 | Policies list + filter; vehicles by owner | ✅ | `test_policies`, `test_policies_filter`, `test_vehicles_filter_by_owner` |
| TC-RD-03 | Dashboard summary matches hand-calculated seed totals | ✅ | `test_dashboard_summary_matches_seed_data` |
| TC-RD-04 | Open-claims count goes up after a new claim | ✅ | `test_dashboard_updates_after_new_claim` |
| TC-RD-05 | Recent claims sorted by date; `limit=1` | ✅ | `test_recent_claims_newest_date_first`, `test_recent_claims_limit` |
| TC-RD-06 | Pending payment not counted as paid | ✅ fixed (BUG-013) | `test_pending_payments_not_counted_as_paid` |
| TC-RD-07 | `limit=-1` | ✅ fixed (BUG-022) | `test_negative_limit_is_422` |

## End-to-end UI — `e2e/`
| ID | Case | Result | Automated by |
|---|---|---|---|
| TC-UI-01 | Login page renders; login goes to Dashboard; user email shown | ✅ | `test_login_page_renders`, `test_successful_login_shows_dashboard` |
| TC-UI-02 | Dashboard KPIs show live DB values | ✅ | `test_dashboard_shows_live_kpis` |
| TC-UI-03 | Wrong password shows the error and stays on /login | ✅ | `test_wrong_password_shows_error_and_stays_on_login` |
| TC-UI-04 | Protected page redirects to login, then returns there after login | ✅ | `test_protected_page_redirects_to_login`, `test_after_login_user_returns_to_the_page_they_wanted` |
| TC-UI-05 | Sign out; can't go back in; session survives reload | ✅ | `test_sign_out`, `test_session_survives_page_reload` |
| TC-UI-06 | Sidebar navigation to 6 pages | ✅ | `test_sidebar_navigation` (6) |
| TC-UI-07 | Readable error for an invalid email | ✅ fixed (BUG-018) | `test_invalid_email_on_login_shows_readable_error` |
| TC-UI-08 | Policyholders: list, live search, empty state, region filter | ✅ | `test_lists_seeded_policyholders`, `test_live_search`, `test_search_with_no_results_shows_empty_state`, `test_region_filter` |
| TC-UI-09 | Add policyholder; Cancel saves nothing; required fields block submit; duplicate email message | ✅ | `test_add_policyholder`, `test_add_form_cancel_saves_nothing`, `test_required_fields_block_submit`, `test_duplicate_email_shows_server_message` |
| TC-UI-10 | Duplicate licence gives a helpful message | ✅ fixed (BUG-003) | `test_duplicate_license_shows_helpful_message` |
| TC-UI-11 | Region filter kept after adding | ✅ fixed (BUG-019) | `test_region_filter_still_applied_after_adding` |
| TC-UI-12 | Form fields reachable by label | ✅ fixed (BUG-020) | `test_add_form_fields_are_reachable_by_label` |
| TC-UI-13 | Quote: empty state, premium $491.16, Region B $351.41, browser blocks BM 9 | ✅ | `e2e/test_quote_ui.py` |
| TC-UI-14 | Quote with Collision | ✅ fixed (BUG-009) | `test_collision_coverage_can_be_quoted` |

## Manual / exploratory checklist (not automated yet)
Good practice for you: try these by hand, and write up anything that breaks.
- [ ] Very small window (mobile width): does the sidebar and table layout still work?
- [ ] Keyboard only (Tab / Enter): can you log in and add a policyholder?
- [ ] Double-click "Save Policyholder" quickly: are two records created?
- [ ] Stop the backend while the Dashboard is open, then reload: is the error message friendly?
- [ ] Unicode names (`José`, `李`, emoji): saved and displayed correctly?
- [ ] The Claims, Vehicles, Policies, Coverage, and Regions pages: do they show the right seed data? (Only navigation is automated so far.)
