"""
API tests: the read-only list endpoints and the dashboard aggregates.

The dashboard numbers are checked against values worked out by hand from
db/seed.sql, so they act as a test of the SQL aggregate queries.
"""
import pytest

from support.db import run_sql

pytestmark = pytest.mark.api


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_regions_sorted_by_name(client):
    assert [r["name"] for r in client.get("/api/regions").json()] == [
        "National", "Region A", "Region B", "Region C",
    ]


def test_region_hierarchy(client):
    regions = {r["name"]: r for r in client.get("/api/regions").json()}
    assert regions["National"]["parent_region_id"] is None
    assert regions["Region A"]["parent_region_id"] == regions["National"]["region_id"]


def test_coverages_sorted_and_liability_mandatory(client):
    cov = client.get("/api/coverages").json()
    assert [c["coverage_name"] for c in cov] == [
        "Collision", "Comprehensive", "Liability", "Uninsured Motorist",
    ]
    assert [c["coverage_name"] for c in cov if c["is_mandatory"]] == ["Liability"]


def test_policies(client):
    policies = client.get("/api/policies").json()
    assert [p["status"] for p in policies] == ["Active", "Active", "Expired"]


def test_policies_filter(client):
    r = client.get("/api/policies", params={"status_filter": "Active"})
    assert [p["policy_id"] for p in r.json()] == [1, 2]


def test_vehicles_filter_by_owner(client):
    [vehicle] = client.get("/api/vehicles", params={"policyholder_id": 1}).json()
    assert (vehicle["make"], vehicle["model"]) == ("Toyota", "Camry")


def test_no_endpoint_leaks_password_hashes(client):
    for path in ["/api/policyholders", "/api/policies", "/api/claims", "/api/vehicles"]:
        assert "password" not in client.get(path).text.lower()


# ------------------------------------------------------------- dashboard
def test_dashboard_summary_matches_seed_data(client):
    assert client.get("/api/dashboard/summary").json() == {
        "active_policies": 2,               # policies 1 and 2
        "total_premium_written": 1315.50,   # 610.50 + 705.00 (expired policy excluded)
        "open_claims": 1,                   # claim 2 is Pending; claim 1 is Paid
        "total_claims_paid": 2400.00,
        "policyholders": 3,
    }


def test_dashboard_updates_after_new_claim(client):
    client.post("/api/claims", json={
        "policy_id": 1, "claim_date": "2026-07-01", "claim_type": "Glass", "fault_percentage": 0,
    })
    assert client.get("/api/dashboard/summary").json()["open_claims"] == 2


def test_recent_claims_newest_date_first(client):
    claims = client.get("/api/dashboard/recent-claims").json()
    assert [c["claim_date"] for c in claims] == ["2026-06-02", "2026-05-14"]


def test_recent_claims_limit(client):
    assert len(client.get("/api/dashboard/recent-claims", params={"limit": 1}).json()) == 1


# Regression test for BUG-013 (fixed): 'Total claims paid' also counts payments that are still Pending
def test_pending_payments_not_counted_as_paid(client):
    run_sql(
        "INSERT INTO claim_payment (claim_id, payment_seq, payment_date, amount, payment_method, status) "
        "VALUES (2, 1, '2026-06-10', 500.00, 'Cheque', 'Pending')"
    )
    assert client.get("/api/dashboard/summary").json()["total_claims_paid"] == 2400.00


# Regression test for BUG-022 (fixed): negative ?limit= crashes recent-claims with 500 instead of 422
def test_negative_limit_is_422(client):
    assert client.get("/api/dashboard/recent-claims", params={"limit": -1}).status_code == 422
