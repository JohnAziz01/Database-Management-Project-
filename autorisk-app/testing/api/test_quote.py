"""
API tests: POST /api/quote -- the pricing calculator.

The unit tests (unit/test_pricing.py) already prove the formula. These
tests prove the *integration*: that the endpoint finds the right
rate-table row in Postgres and passes the right numbers into the formula.

Seed rate tables exist for all 4 coverages in Regions A/B/C (region ids
2/3/4). The "National" region (id 1) has no rate table on purpose: it's a
parent region, not somewhere a driver lives. (Before the BUG-009 fix only
Liability had rate tables.)
"""
from datetime import date

from app.clock import today

import pytest

from support.db import run_sql

pytestmark = pytest.mark.api

URL = "/api/quote"


@pytest.fixture
def payload():
    return {
        "date_of_birth": "1980-01-01",
        "license_issue_date": "2000-01-01",
        "bonus_malus_coefficient": 0.90,
        "vehicle_manufacture_year": 2022,
        "vehicle_power_kw": 138,
        "region_id": 2,       # Region A: base 450, region factor 1.10
        "coverage_id": 1,     # Liability
    }


def years_ago(n):
    t = today()
    return t.replace(year=t.year - n).isoformat() if not (t.month == 2 and t.day == 29) \
        else t.replace(year=t.year - n, day=28).isoformat()


def test_quote_matches_hand_calculation(client, payload):
    # 450 * 1.00 (age) * 1.05^2 (138 kW) * 1.10 (Region A) * 0.90 = 491.16
    r = client.post(URL, json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["estimated_premium"] == 491.16
    assert body["base_rate"] == 450.0
    assert body["region_factor"] == 1.10
    assert body["risk_level"] == "Low"


@pytest.mark.parametrize("region_id, base_rate", [(2, 450.0), (3, 380.0), (4, 520.0)])
def test_each_region_uses_its_own_rate_table(client, payload, region_id, base_rate):
    payload["region_id"] = region_id
    assert client.post(URL, json=payload).json()["base_rate"] == base_rate


def test_young_driver_gets_region_young_factor(client, payload):
    payload["date_of_birth"] = years_ago(20)
    payload["license_issue_date"] = years_ago(3)  # must be after birth (BUG-007/010 fix)
    assert client.post(URL, json=payload).json()["age_factor"] == 1.60


@pytest.mark.parametrize("licensed_years, factor", [(1, 1.20), (2, 1.10), (4, 1.10), (5, 1.00), (26, 1.00)])
def test_new_drivers_pay_experience_surcharge(client, payload, licensed_years, factor):
    # BUG-011 fix: driving experience now affects the price
    payload["license_issue_date"] = years_ago(licensed_years)
    body = client.post(URL, json=payload).json()
    assert body["experience_factor"] == factor
    assert body["estimated_premium"] == pytest.approx(491.16 * factor, abs=0.02)


def test_expired_rate_table_is_ignored(client, payload):
    run_sql("UPDATE rate_table SET expiry_date = effective_date + 1 WHERE region_id = 2")
    assert client.post(URL, json=payload).status_code == 404


# NOTE: the first draft of these tests used SQL's CURRENT_DATE while the app
# used Python's local date.today(); in the evening (US time) those are
# different days, so the test only failed after 6 pm -- a classic flaky
# test that exposed BUG-023. Now the app and the tests both use app.clock.
def test_newest_rate_table_wins(client, payload):
    run_sql(
        "INSERT INTO rate_table (region_id, coverage_id, effective_date, base_rate) "
        "VALUES (2, 1, %s, 999.00)",
        (today(),),
    )
    assert client.post(URL, json=payload).json()["base_rate"] == 999.0


def test_future_rate_table_not_used_yet(client, payload):
    run_sql(
        "INSERT INTO rate_table (region_id, coverage_id, effective_date, base_rate) "
        "VALUES (2, 1, %s, 999.00)",
        (date.fromordinal(today().toordinal() + 30),),
    )
    assert client.post(URL, json=payload).json()["base_rate"] == 450.0


# Regression test for BUG-023 (fixed): app's 'today' (server local time) disagrees with the database's (UTC)
def test_app_and_database_agree_on_todays_date(client):
    # The app's clock (app.clock.today) is UTC, like the database, so they
    # agree at every hour of the day -- including the evening, when the old
    # local-time date.today() was already one day behind.
    [(db_today,)] = run_sql("SELECT CURRENT_DATE")
    assert db_today == today()


def test_unknown_region_is_404(client, payload):
    payload["region_id"] = 999
    r = client.post(URL, json=payload)
    assert r.status_code == 404
    assert r.json()["detail"] == "Region not found"


def test_region_without_rate_table_is_404(client, payload):
    payload["region_id"] = 1  # "National"
    assert client.post(URL, json=payload).status_code == 404


@pytest.mark.parametrize("field", ["date_of_birth", "region_id", "coverage_id", "vehicle_power_kw"])
def test_missing_field_is_422(client, payload, field):
    del payload[field]
    assert client.post(URL, json=payload).status_code == 422


def test_text_in_number_field_is_422(client, payload):
    payload["vehicle_power_kw"] = "lots"
    assert client.post(URL, json=payload).status_code == 422


# ------------------------------------------------- regression tests for fixed bugs
# Regression test for BUG-009 (fixed): the Quote form offered region/coverage pairs that have no rate table
def test_every_option_offered_in_the_form_can_be_quoted(client, payload):
    # The form now builds its dropdowns from /api/quote/options.
    options = client.get(f"{URL}/options").json()
    assert len(options) == 12  # 3 regions x 4 coverages
    failures = []
    for o in options:
        payload.update(region_id=o["region_id"], coverage_id=o["coverage_id"])
        if client.post(URL, json=payload).status_code != 200:
            failures.append((o["region_name"], o["coverage_name"]))
    assert failures == []


def test_options_leave_out_regions_without_rate_tables(client):
    names = {o["region_name"] for o in client.get(f"{URL}/options").json()}
    assert names == {"Region A", "Region B", "Region C"}  # no "National"


def test_options_leave_out_expired_rate_tables(client):
    run_sql("UPDATE rate_table SET expiry_date = effective_date + 1 WHERE coverage_id = 2")
    coverages = {o["coverage_name"] for o in client.get(f"{URL}/options").json()}
    assert "Collision" not in coverages


# Regression test for BUG-010 (fixed): impossible quote inputs are accepted
@pytest.mark.parametrize(
    "field, value",
    [
        ("bonus_malus_coefficient", -1),     # gives a NEGATIVE premium
        ("bonus_malus_coefficient", 0),      # gives a $0 premium
        ("vehicle_power_kw", -500),
        ("vehicle_manufacture_year", 3000),
        ("date_of_birth", "2090-01-01"),
        ("license_issue_date", "1970-01-01"),  # before the driver was born
    ],
)
def test_impossible_input_is_422(client, payload, field, value):
    payload[field] = value
    assert client.post(URL, json=payload).status_code == 422
