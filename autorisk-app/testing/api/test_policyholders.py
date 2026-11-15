"""
API tests: /api/policyholders (list + search + filter, get one, create).

Seed data has 3 policyholders:
  1 Jordan Reyes  (Region A, id 2)   jordan.reyes@example.com  D1234567
  2 Casey Nguyen  (Region B, id 3)   casey.nguyen@example.com  D7654321
  3 Priya Shah    (Region C, id 4)   priya.shah@example.com    D9988776
"""
import pytest

from support.db import run_sql

pytestmark = pytest.mark.api

URL = "/api/policyholders"


def names(response):
    return [p["first_name"] for p in response.json()]


# ------------------------------------------------------------- listing
def test_lists_all_seeded_policyholders_in_id_order(client):
    r = client.get(URL)
    assert r.status_code == 200
    assert names(r) == ["Jordan", "Casey", "Priya"]


def test_response_has_expected_fields(client):
    ph = client.get(URL).json()[0]
    assert set(ph) == {
        "policyholder_id", "first_name", "last_name", "date_of_birth", "license_number",
        "license_issue_date", "email", "phone", "region_id", "risk_tier", "created_at",
    }


@pytest.mark.parametrize(
    "q, expected",
    [
        ("jordan", ["Jordan"]),             # first name
        ("SHAH", ["Priya"]),                # last name, case-insensitive
        ("casey.nguyen@", ["Casey"]),       # email
        ("D99887", ["Priya"]),              # license number, partial
        ("example.com", ["Jordan", "Casey", "Priya"]),
        ("zzz-no-match", []),
    ],
)
def test_search(client, q, expected):
    assert names(client.get(URL, params={"q": q})) == expected


def test_filter_by_region(client):
    assert names(client.get(URL, params={"region_id": 3})) == ["Casey"]


def test_search_and_region_filter_combine(client):
    assert names(client.get(URL, params={"q": "example.com", "region_id": 4})) == ["Priya"]


def test_search_is_safe_from_sql_injection(client):
    r = client.get(URL, params={"q": "' OR 1=1 --"})
    assert r.status_code == 200
    assert r.json() == []


# Regression test for BUG-014 (fixed): LIKE wildcards % and _ in the search box are not escaped
def test_percent_sign_is_searched_literally(client):
    assert client.get(URL, params={"q": "%"}).json() == []


# ------------------------------------------------------------- get by id
def test_get_one(client):
    r = client.get(f"{URL}/2")
    assert r.status_code == 200
    assert r.json()["email"] == "casey.nguyen@example.com"


def test_get_missing_is_404(client):
    r = client.get(f"{URL}/9999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Policyholder not found"


def test_get_non_numeric_id_is_422(client):
    assert client.get(f"{URL}/abc").status_code == 422


# ------------------------------------------------------------- create
def test_create_returns_201_and_saves_the_row(client, new_policyholder):
    r = client.post(URL, json=new_policyholder)
    assert r.status_code == 201
    created = r.json()
    assert created["policyholder_id"] == 4
    assert created["email"] == new_policyholder["email"]
    # Don't trust the response alone -- check it really reached the database.
    assert run_sql("SELECT count(*) FROM policyholder")[0][0] == 4
    assert client.get(f"{URL}/4").status_code == 200


def test_optional_fields_can_be_omitted(client, new_policyholder):
    for field in ("phone", "region_id", "risk_tier"):
        del new_policyholder[field]
    assert client.post(URL, json=new_policyholder).status_code == 201


@pytest.mark.parametrize(
    "field", ["first_name", "last_name", "date_of_birth", "license_number", "license_issue_date", "email"]
)
def test_missing_required_field_is_422(client, new_policyholder, field):
    del new_policyholder[field]
    assert client.post(URL, json=new_policyholder).status_code == 422


@pytest.mark.parametrize("bad_email", ["plainaddress", "@example.com", "a@b", "a b@example.com"])
def test_invalid_email_is_422(client, new_policyholder, bad_email):
    new_policyholder["email"] = bad_email
    assert client.post(URL, json=new_policyholder).status_code == 422


def test_invalid_date_is_422(client, new_policyholder):
    new_policyholder["date_of_birth"] = "1990-02-30"
    assert client.post(URL, json=new_policyholder).status_code == 422


def test_duplicate_email_is_409(client, new_policyholder):
    new_policyholder["email"] = "jordan.reyes@example.com"
    r = client.post(URL, json=new_policyholder)
    assert r.status_code == 409


# ---- regression tests for fixed bugs ----
# Regression test for BUG-003 (fixed): duplicate license number crashes with 500 instead of 409
def test_duplicate_license_number_is_409(client, new_policyholder):
    new_policyholder["license_number"] = "D1234567"  # Jordan's
    assert client.post(URL, json=new_policyholder).status_code == 409


# Regression test for BUG-015 (fixed): duplicate-email check is case-sensitive
def test_duplicate_email_with_different_case_is_409(client, new_policyholder):
    new_policyholder["email"] = "JORDAN.REYES@example.com"
    assert client.post(URL, json=new_policyholder).status_code == 409


# Regression test for BUG-004 (fixed): invalid risk_tier crashes with 500 instead of 422
def test_invalid_risk_tier_is_422(client, new_policyholder):
    new_policyholder["risk_tier"] = "Extreme"
    assert client.post(URL, json=new_policyholder).status_code == 422


# Regression test for BUG-005 (fixed): non-existent region_id crashes with 500 instead of 422
def test_unknown_region_is_422(client, new_policyholder):
    new_policyholder["region_id"] = 999
    assert client.post(URL, json=new_policyholder).status_code == 422


# Regression test for BUG-007 (fixed): date of birth in the future is accepted
def test_future_date_of_birth_is_422(client, new_policyholder):
    new_policyholder["date_of_birth"] = "2090-01-01"
    assert client.post(URL, json=new_policyholder).status_code == 422


# Regression test for BUG-007 (fixed): license issued before the driver was born is accepted
def test_license_before_birth_is_422(client, new_policyholder):
    new_policyholder["license_issue_date"] = "1950-01-01"
    assert client.post(URL, json=new_policyholder).status_code == 422


# Regression test for BUG-016 (fixed): blank names are accepted
def test_blank_first_name_is_422(client, new_policyholder):
    new_policyholder["first_name"] = "   "
    assert client.post(URL, json=new_policyholder).status_code == 422


# Regression test for BUG-016 (fixed): text longer than the DB column crashes with 500 instead of 422
def test_too_long_first_name_is_422(client, new_policyholder):
    new_policyholder["first_name"] = "A" * 51  # column is VARCHAR(50)
    assert client.post(URL, json=new_policyholder).status_code == 422
