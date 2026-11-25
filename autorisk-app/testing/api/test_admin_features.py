"""
API tests: the four admin features -- rate tables, risk analysis, reports
and accounts.

Seed data used below: regions 2/3/4 (Region A/B/C) each have a current
rate for all 4 coverages from 2026-01-01 (12 rows); 3 policies (premiums
610.50 / 705.00 / 890.25, bonus-malus 0.90 / 1.15 / 1.00); 2 claims, of
which claim 1 has a 2,400.00 Paid payment; accounts admin@ (Administrator)
and jordan.reyes@ (customer of policyholder 1).
"""
from datetime import timedelta

import pytest

from app.clock import today
from support import ADMIN_EMAIL, ADMIN_PASSWORD, CUSTOMER_EMAIL, CUSTOMER_PASSWORD

pytestmark = pytest.mark.api


def login(anon_client, email, password):
    return anon_client.post("/api/auth/login", json={"email": email, "password": password})


def headers_for(anon_client, email, password):
    r = login(anon_client, email, password)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def new_rate(**overrides):
    return {
        "region_id": 2, "coverage_id": 1, "effective_date": (today() + timedelta(days=1)).isoformat(),
        "base_rate": 500.00, "age_factor_young": 1.70, "age_factor_senior": 1.10,
        "vehicle_power_factor": 1.05, "bonus_malus_step": 1.00, **overrides,
    }


QUOTE = {
    "date_of_birth": "1980-01-01", "license_issue_date": "2000-01-01", "bonus_malus_coefficient": 0.90,
    "vehicle_manufacture_year": 2022, "vehicle_power_kw": 138, "region_id": 2, "coverage_id": 1,
}


@pytest.fixture
def analyst_headers(client, anon_client):
    r = client.post("/api/accounts", json={
        "email": "ana.lyst@autorisk.demo", "password": "analyst123", "account_type": "Admin", "admin_role": "Analyst",
    })
    assert r.status_code == 201, r.text
    return headers_for(anon_client, "ana.lyst@autorisk.demo", "analyst123")


# ================================================================ rate tables
def test_rate_tables_list_current_versions_with_names(client):
    rows = client.get("/api/rate-tables", params={"status": "Current"}).json()
    assert len(rows) == 12
    a_liability = next(r for r in rows if r["region_id"] == 2 and r["coverage_id"] == 1)
    assert (a_liability["region_name"], a_liability["coverage_name"], a_liability["base_rate"]) == ("Region A", "Liability", 450.0)


def test_rate_tables_filter_by_region(client):
    assert len(client.get("/api/rate-tables", params={"region_id": 2}).json()) == 4


def test_future_version_is_scheduled_and_closes_the_current_one(client):
    r = client.post("/api/rate-tables", json=new_rate())
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "Scheduled"
    versions = client.get("/api/rate-tables", params={"region_id": 2, "coverage_id": 1}).json()
    old = next(v for v in versions if v["base_rate"] == 450.0)
    assert old["expiry_date"] == new_rate()["effective_date"]   # closed exactly when the new one starts
    assert old["status"] == "Current"                            # ...but still in force today
    assert client.post("/api/quote", json=QUOTE).json()["base_rate"] == 450.0


def test_version_effective_today_reprices_quotes_immediately(client):
    r = client.post("/api/rate-tables", json=new_rate(effective_date=today().isoformat()))
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "Current"
    assert client.post("/api/quote", json=QUOTE).json()["base_rate"] == 500.0
    statuses = {v["base_rate"]: v["status"] for v in client.get("/api/rate-tables", params={"region_id": 2, "coverage_id": 1}).json()}
    assert statuses == {450.0: "Expired", 500.0: "Current"}


def test_two_versions_cannot_start_on_the_same_day(client):
    assert client.post("/api/rate-tables", json=new_rate()).status_code == 201
    r = client.post("/api/rate-tables", json=new_rate(base_rate=600))
    assert r.status_code == 409


@pytest.mark.parametrize("field, value", [
    ("effective_date", "2020-01-01"),   # backdating would re-price past quotes
    ("base_rate", 0),
    ("age_factor_young", 9),
    ("region_id", 999),
    ("coverage_id", 999),
])
def test_invalid_rate_version_is_422(client, field, value):
    assert client.post("/api/rate-tables", json=new_rate(**{field: value})).status_code == 422


def test_analyst_can_view_rates_but_not_publish(client, analyst_headers):
    assert client.get("/api/rate-tables", headers=analyst_headers).status_code == 200
    assert client.post("/api/rate-tables", json=new_rate(), headers=analyst_headers).status_code == 403


# ================================================================ risk analysis
@pytest.mark.parametrize("dimension", ["driver_age", "experience", "vehicle_power", "vehicle_age", "bonus_malus", "region", "risk_tier"])
def test_every_dimension_accounts_for_every_policy(client, dimension):
    body = client.get("/api/risk/analysis", params={"dimension": dimension}).json()
    assert body["overall"]["policies"] == 3
    assert sum(s["policies"] for s in body["segments"]) == 3
    assert sum(s["paid"] for s in body["segments"]) == pytest.approx(2400.0)


def test_risk_overall_metrics(client):
    o = client.get("/api/risk/analysis").json()["overall"]
    assert (o["claims"], o["paid"], o["premium"]) == (2, 2400.0, 2205.75)
    assert o["claim_frequency"] == round(2 / 3, 4)
    assert o["average_severity"] == 1200.0
    assert o["loss_ratio"] == round(2400 / 2205.75, 4)


def test_bonus_malus_segments(client):
    segs = {s["segment"]: s["policies"] for s in client.get("/api/risk/analysis", params={"dimension": "bonus_malus"}).json()["segments"]}
    assert segs == {"Bonus (< 1.00)": 1, "Neutral (1.00)": 1, "Malus 1.01–1.50": 1}


def test_unknown_risk_dimension_is_422(client):
    assert client.get("/api/risk/analysis", params={"dimension": "1; DROP TABLE policy"}).status_code == 422


# ================================================================ reports
def test_report_catalog(client):
    keys = [r["key"] for r in client.get("/api/reports").json()]
    assert keys == ["claims-register", "payments-ledger", "policy-register", "region-summary", "coverage-mix"]


def test_claims_register_includes_amount_paid(client):
    body = client.get("/api/reports/claims-register").json()
    assert body["total_rows"] == 2
    row = dict(zip(body["columns"], next(r for r in body["rows"] if r[0] == 1)))
    assert row["amount_paid"] == 2400.0 and row["policyholder"] == "Jordan Reyes"


def test_report_date_filter(client):
    body = client.get("/api/reports/policy-register", params={"date_from": "2026-01-01"}).json()
    assert body["total_rows"] == 2   # the 2025 policy is excluded


def test_region_summary_premium_adds_up(client):
    body = client.get("/api/reports/region-summary").json()
    premium = body["columns"].index("premium")
    assert sum(r[premium] for r in body["rows"]) == pytest.approx(2205.75)


def test_report_csv_download(client):
    r = client.get("/api/reports/policy-register/csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("policy_id,status,start_date") and len(lines) == 4


def test_report_bad_inputs(client):
    assert client.get("/api/reports/nope").status_code == 404
    assert client.get("/api/reports/policy-register", params={"date_from": "2026-12-01", "date_to": "2026-01-01"}).status_code == 422


# ================================================================ accounts
def test_accounts_list_never_exposes_password_hashes(client):
    r = client.get("/api/accounts")
    assert r.status_code == 200 and len(r.json()) == 2
    assert "password" not in r.text and "$2b$" not in r.text


def test_create_staff_account_and_sign_in(client, anon_client):
    r = client.post("/api/accounts", json={
        "email": "New.Manager@AutoRisk.demo", "password": "manager123", "account_type": "Admin", "admin_role": "Manager",
    })
    assert r.status_code == 201, r.text
    assert r.json()["email"] == "new.manager@autorisk.demo"   # stored in lower case
    me = login(anon_client, "new.manager@autorisk.demo", "manager123").json()
    assert me["admin_role"] == "Manager"


def test_create_customer_account_for_policyholder(client):
    r = client.post("/api/accounts", json={
        "email": "casey@example.com", "password": "casey1234", "account_type": "Customer", "policyholder_id": 2,
    })
    assert r.status_code == 201 and r.json()["policyholder_name"] == "Casey Nguyen"


@pytest.mark.parametrize("payload, status", [
    ({"email": "x@example.com", "password": "password1", "account_type": "Customer", "policyholder_id": 1}, 409),  # already has one
    ({"email": "ADMIN@autorisk.demo", "password": "password1", "account_type": "Admin", "admin_role": "Analyst"}, 409),  # email taken
    ({"email": "x@example.com", "password": "password1", "account_type": "Customer"}, 422),                         # no policyholder
    ({"email": "x@example.com", "password": "password1", "account_type": "Admin"}, 422),                            # no role
    ({"email": "x@example.com", "password": "password1", "account_type": "Admin", "admin_role": "Analyst", "policyholder_id": 2}, 422),
    ({"email": "x@example.com", "password": "short", "account_type": "Admin", "admin_role": "Analyst"}, 422),
    ({"email": "x@example.com", "password": "password1", "account_type": "Customer", "policyholder_id": 999}, 422),
])
def test_invalid_account_requests(client, payload, status):
    assert client.post("/api/accounts", json=payload).status_code == status


def test_disabled_account_is_locked_out_immediately(client, anon_client, customer_headers):
    assert client.patch("/api/accounts/2", json={"is_active": False}).status_code == 200
    assert login(anon_client, CUSTOMER_EMAIL, CUSTOMER_PASSWORD).status_code == 403
    assert anon_client.get("/api/policies", headers=customer_headers).status_code == 401   # old token rejected too
    assert client.patch("/api/accounts/2", json={"is_active": True}).status_code == 200
    assert login(anon_client, CUSTOMER_EMAIL, CUSTOMER_PASSWORD).status_code == 200


def test_admin_cannot_lock_themself_out(client):
    assert client.patch("/api/accounts/1", json={"is_active": False}).status_code == 409
    assert client.patch("/api/accounts/1", json={"admin_role": "Analyst"}).status_code == 409


def test_role_change_only_for_staff(client):
    assert client.patch("/api/accounts/2", json={"admin_role": "Manager"}).status_code == 422


def test_reset_password(client, anon_client):
    assert client.post("/api/accounts/2/reset-password", json={"new_password": "brandnew99"}).status_code == 204
    assert login(anon_client, CUSTOMER_EMAIL, CUSTOMER_PASSWORD).status_code == 401
    assert login(anon_client, CUSTOMER_EMAIL, "brandnew99").status_code == 200
    assert client.post("/api/accounts/999/reset-password", json={"new_password": "brandnew99"}).status_code == 404


def test_analyst_is_read_only_on_accounts(client, analyst_headers):
    assert client.get("/api/accounts", headers=analyst_headers).status_code == 200
    assert client.patch("/api/accounts/2", json={"is_active": False}, headers=analyst_headers).status_code == 403
    assert client.post("/api/accounts/2/reset-password", json={"new_password": "brandnew99"}, headers=analyst_headers).status_code == 403


# ================================================================ access control
@pytest.mark.parametrize("path", ["/api/rate-tables", "/api/risk/analysis", "/api/reports", "/api/reports/policy-register/csv", "/api/accounts"])
def test_admin_features_are_closed_to_customers_and_visitors(anon_client, customer_headers, path):
    assert anon_client.get(path).status_code == 401
    assert anon_client.get(path, headers=customer_headers).status_code == 403


def test_login_and_me_report_staff_role(anon_client, admin_headers):
    assert login(anon_client, ADMIN_EMAIL, ADMIN_PASSWORD).json()["admin_role"] == "Administrator"
    assert anon_client.get("/api/auth/me", headers=admin_headers).json()["admin_role"] == "Administrator"
