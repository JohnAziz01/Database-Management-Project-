"""
Security tests: authentication (are you logged in?) and authorization
(are you ALLOWED to do this?), plus CORS.

The frontend hides pages from logged-out users, but that is only cosmetic:
anyone can call the API directly with curl or Postman. So the API itself
must enforce access. These tests call the API exactly like an attacker
would -- with no token, or with a low-privilege customer token.

History: BUG-001 (no login required) and BUG-002 (customers could see
everyone's data) were found here and fixed; these tests now guard against
them coming back (regression tests).
"""
import pytest

pytestmark = [pytest.mark.api, pytest.mark.security]

# Every data endpoint the app exposes.
PROTECTED = [
    ("GET", "/api/policyholders"),
    ("GET", "/api/policyholders/1"),
    ("POST", "/api/policyholders"),
    ("GET", "/api/policies"),
    ("GET", "/api/vehicles"),
    ("GET", "/api/claims"),
    ("POST", "/api/claims"),
    ("GET", "/api/claims/1/payments"),
    ("GET", "/api/dashboard/summary"),
    ("GET", "/api/dashboard/recent-claims"),
    ("GET", "/api/regions"),
    ("GET", "/api/coverages"),
    ("GET", "/api/quote/options"),
    ("POST", "/api/quote"),
]


# ------------------------------------------------------- authentication
@pytest.mark.parametrize("method, path", PROTECTED, ids=[f"{m} {p}" for m, p in PROTECTED])
def test_endpoint_rejects_requests_without_a_token(anon_client, method, path):
    r = anon_client.request(method, path, json={})
    assert r.status_code == 401


def test_public_endpoints_stay_public(anon_client):
    # Login and health MUST work without a token, otherwise nobody can log in.
    assert anon_client.get("/api/health").status_code == 200
    assert anon_client.post("/api/auth/login", json={"email": "a@b.co", "password": "x"}).status_code == 401


# -------------------------------------------------------- authorization
# Seed data: the customer jordan.reyes@example.com is policyholder 1, owns
# vehicle 1 and policy 1, and policy 1 has claim 1.
def test_customer_only_sees_their_own_policyholder_record(client, customer_headers):
    r = client.get("/api/policyholders", headers=customer_headers)
    assert [p["policyholder_id"] for p in r.json()] == [1]


def test_customer_cannot_open_someone_elses_record(client, customer_headers):
    assert client.get("/api/policyholders/2", headers=customer_headers).status_code == 404
    assert client.get("/api/policyholders/1", headers=customer_headers).status_code == 200


def test_customer_cannot_create_policyholders(client, customer_headers, new_policyholder):
    r = client.post("/api/policyholders", json=new_policyholder, headers=customer_headers)
    assert r.status_code == 403


@pytest.mark.parametrize(
    "path, id_field, expected_ids",
    [
        ("/api/policies", "policy_id", [1]),
        ("/api/vehicles", "vehicle_id", [1]),
        ("/api/claims", "claim_id", [1]),
    ],
)
def test_customer_lists_only_their_own_data(client, customer_headers, path, id_field, expected_ids):
    r = client.get(path, headers=customer_headers)
    assert [row[id_field] for row in r.json()] == expected_ids


def test_customer_cannot_read_payments_of_other_customers_claims(client, customer_headers):
    assert client.get("/api/claims/2/payments", headers=customer_headers).status_code == 404
    assert client.get("/api/claims/1/payments", headers=customer_headers).status_code == 200


def test_customer_cannot_file_a_claim_on_someone_elses_policy(client, customer_headers):
    claim = {"policy_id": 2, "claim_date": "2026-07-01", "claim_type": "Theft", "fault_percentage": 0}
    assert client.post("/api/claims", json=claim, headers=customer_headers).status_code == 404


def test_customer_can_file_a_claim_on_their_own_policy(client, customer_headers):
    claim = {"policy_id": 1, "claim_date": "2026-07-01", "claim_type": "Glass", "fault_percentage": 0}
    assert client.post("/api/claims", json=claim, headers=customer_headers).status_code == 201


def test_company_dashboard_is_admin_only(client, customer_headers):
    r = client.get("/api/dashboard/summary", headers=customer_headers)
    assert r.status_code == 403
    assert r.json()["detail"] == "Admin access required"


def test_customer_can_still_get_a_quote(client, customer_headers):
    quote = {
        "date_of_birth": "1990-04-12", "license_issue_date": "2009-05-01",
        "bonus_malus_coefficient": 0.9, "vehicle_manufacture_year": 2022,
        "vehicle_power_kw": 138, "region_id": 2, "coverage_id": 1,
    }
    assert client.post("/api/quote", json=quote, headers=customer_headers).status_code == 200


# ------------------------------------------------------------ misc
def test_cors_allows_the_frontend_origin(anon_client):
    r = anon_client.options(
        "/api/health",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_blocks_other_origins(anon_client):
    r = anon_client.options(
        "/api/health",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in r.headers


def test_error_responses_do_not_leak_internals(client, new_policyholder):
    # This used to be a 500 crash (BUG-003). Whatever the error, the client
    # must never see stack traces or database driver messages.
    new_policyholder["license_number"] = "D1234567"
    r = client.post("/api/policyholders", json=new_policyholder)
    assert r.status_code == 409
    assert "Traceback" not in r.text
    assert "psycopg2" not in r.text
    assert "IntegrityError" not in r.text
