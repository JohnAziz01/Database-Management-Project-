"""
API tests: /api/claims (list, filter, create) and /api/claims/{id}/payments.

Seed data: claim 1 (policy 1, Paid, 1 payment of 2400.00),
           claim 2 (policy 2, Pending, no payments).
Policy 3 is Expired, covering 2025-09-01 .. 2026-09-01.
"""
from datetime import date, timedelta

import pytest

from app.clock import today

from support.db import run_sql

pytestmark = pytest.mark.api

URL = "/api/claims"


@pytest.fixture
def new_claim():
    return {
        "policy_id": 1,
        "claim_date": "2026-07-01",
        "claim_type": "Collision",
        "description": "Scraped a pillar in a car park",
        "fault_percentage": 100,
    }


def test_lists_claims_newest_id_first(client):
    r = client.get(URL)
    assert r.status_code == 200
    assert [c["claim_id"] for c in r.json()] == [2, 1]


@pytest.mark.parametrize("status, expected_ids", [("Paid", [1]), ("Pending", [2]), ("Denied", [])])
def test_filter_by_status(client, status, expected_ids):
    r = client.get(URL, params={"status_filter": status})
    assert [c["claim_id"] for c in r.json()] == expected_ids


def test_create_claim(client, new_claim):
    r = client.post(URL, json=new_claim)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "Open"          # default status
    assert body["fault_percentage"] == 100
    assert run_sql("SELECT count(*) FROM claim")[0][0] == 3


@pytest.mark.parametrize("fault", [0, 0.01, 99.99, 100])
def test_fault_percentage_boundaries_accepted(client, new_claim, fault):
    new_claim["fault_percentage"] = fault
    assert client.post(URL, json=new_claim).status_code == 201


def test_claim_for_missing_policy_is_404(client, new_claim):
    new_claim["policy_id"] = 999
    r = client.post(URL, json=new_claim)
    assert r.status_code == 404
    assert r.json()["detail"] == "Policy not found"


def test_missing_claim_type_is_422(client, new_claim):
    del new_claim["claim_type"]
    assert client.post(URL, json=new_claim).status_code == 422


def test_payments_for_claim(client):
    r = client.get(f"{URL}/1/payments")
    assert r.status_code == 200
    [payment] = r.json()
    assert payment["amount"] == 2400.00
    assert payment["payment_seq"] == 1


def test_claim_without_payments_returns_empty_list(client):
    assert client.get(f"{URL}/2/payments").json() == []


# ------------------------------------------------- regression tests for fixed bugs
# Regression test for BUG-006 (fixed): fault_percentage outside 0-100 crashes with 500 instead of 422
@pytest.mark.parametrize("fault", [-0.01, 100.01, 150])
def test_fault_percentage_out_of_range_is_422(client, new_claim, fault):
    new_claim["fault_percentage"] = fault
    assert client.post(URL, json=new_claim).status_code == 422


# Regression test for BUG-008 (fixed): claim dated after the policy ended is accepted
def test_claim_outside_policy_period_is_rejected(client, new_claim):
    new_claim.update(policy_id=3, claim_date="2026-10-01")  # policy 3 ended 2026-09-01
    assert client.post(URL, json=new_claim).status_code in (400, 422)


# Regression test for BUG-008 (fixed): claim dated in the future is accepted
def test_future_claim_date_is_rejected(client, new_claim):
    new_claim["claim_date"] = (today() + timedelta(days=30)).isoformat()
    assert client.post(URL, json=new_claim).status_code in (400, 422)


# Regression test for BUG-016 (fixed): claim_type longer than the DB column crashes with 500
def test_too_long_claim_type_is_422(client, new_claim):
    new_claim["claim_type"] = "X" * 31  # column is VARCHAR(30)
    assert client.post(URL, json=new_claim).status_code == 422


# Regression test for BUG-021 (fixed): payments for a non-existent claim return 200 [] instead of 404
def test_payments_for_missing_claim_is_404(client):
    assert client.get(f"{URL}/999/payments").status_code == 404
