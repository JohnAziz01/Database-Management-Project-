"""
UNIT TESTS for backend/app/pricing.py

Unit = the smallest testable piece (one function), tested in isolation:
no database, no web server, no network. They run in milliseconds, so you
can run them on every save.

Techniques used here:
  * Equivalence partitioning - drivers fall into 3 age classes (young,
    standard, senior); one representative per class is enough.
  * Boundary value analysis - bugs hide at the edges, so we test exactly
    at, just below, and just above each boundary (age 25, age 65, 100 kW...).
  * Oracle - the "expected" value is worked out by hand from the formula,
    never copied from what the code currently returns.
"""
from datetime import date

import pytest

from app.pricing import _age, calculate_full_coverage_quote, calculate_quote

pytestmark = pytest.mark.unit

AS_OF = date(2026, 6, 15)  # fixed "today" so results never change over time

# Factors from seed.sql's Region A / Liability rate-table row.
RATE = dict(
    base_rate=450.00,
    age_factor_young=1.60,
    age_factor_senior=1.10,
    vehicle_power_factor_table=1.05,
    bonus_malus_step=1.00,
)


def quote(**overrides):
    """Valid standard-driver quote; each test overrides only what it probes."""
    args = dict(
        date_of_birth=date(1980, 1, 1),
        license_issue_date=date(2000, 1, 1),
        bonus_malus_coefficient=1.00,
        vehicle_manufacture_year=2022,
        vehicle_power_kw=60,
        region_base_risk_factor=1.00,
        as_of=AS_OF,
        **RATE,
    )
    args.update(overrides)
    return calculate_quote(**args)


def born_years_ago(years, days_offset=0):
    """Date of birth that makes the driver exactly `years` old on AS_OF.
    days_offset=+1 means the birthday is tomorrow (still one year younger)."""
    d = date(AS_OF.year - years, AS_OF.month, AS_OF.day)
    return date.fromordinal(d.toordinal() + days_offset)


# ---------------------------------------------------------------- _age()
class TestAge:
    def test_birthday_today_counts_the_new_year(self):
        assert _age(date(2000, 6, 15), AS_OF) == 26

    def test_birthday_tomorrow_not_counted_yet(self):
        assert _age(date(2000, 6, 16), AS_OF) == 25

    def test_birthday_was_yesterday(self):
        assert _age(date(2000, 6, 14), AS_OF) == 26

    @pytest.mark.parametrize(
        "as_of, expected",
        [(date(2025, 2, 28), 24), (date(2025, 3, 1), 25), (date(2028, 2, 29), 28)],
    )
    def test_leap_day_birthday(self, as_of, expected):
        # Born 29 Feb: in non-leap years the birthday "happens" on 1 March.
        assert _age(date(2000, 2, 29), as_of) == expected


# ---------------------------------------------------------- age factor
class TestAgeFactor:
    @pytest.mark.parametrize(
        "age, days_offset, expected_factor",
        [
            (24, 0, 1.60),   # young class
            (25, 1, 1.60),   # turns 25 tomorrow -> still 24 -> young (boundary-1)
            (25, 0, 1.00),   # exactly 25 today -> standard (boundary)
            (40, 0, 1.00),   # standard class representative
            (65, 1, 1.00),   # turns 65 tomorrow -> still 64 -> standard (boundary-1)
            (65, 0, 1.10),   # exactly 65 -> senior (boundary)
            (80, 0, 1.10),   # senior class representative
        ],
    )
    def test_age_classes_and_boundaries(self, age, days_offset, expected_factor):
        result = quote(date_of_birth=born_years_ago(age, days_offset))
        assert result["age_factor"] == expected_factor


# --------------------------------------------------- vehicle power factor
class TestVehiclePowerFactor:
    # Formula: table_factor ** (1 + max(kW - 50, 0) // 50)
    @pytest.mark.parametrize(
        "kw, exponent",
        # (started at 0 kW before the BUG-010 fix made 0 kW an invalid input)
        [(1, 1), (50, 1), (99, 1), (100, 2), (149, 2), (150, 3), (250, 5)],
    )
    def test_power_bands(self, kw, exponent):
        result = quote(vehicle_power_kw=kw)
        assert result["vehicle_power_factor"] == pytest.approx(1.05 ** exponent, abs=1e-4)

    def test_more_power_never_costs_less(self):
        premiums = [quote(vehicle_power_kw=kw)["estimated_premium"] for kw in range(10, 400, 10)]
        assert premiums == sorted(premiums)


# ----------------------------------------------------- whole-formula checks
class TestPremium:
    def test_hand_calculated_example(self):
        # 450 base * 1.00 age * 1.05^2 (138 kW) * 1.10 region * 0.90 bonus-malus
        # = 450 * 1.1025 * 1.10 * 0.90 = 491.16375 per year
        # x 6/12 for the 6-month term = 245.581875 -> 245.58
        result = quote(
            vehicle_power_kw=138, region_base_risk_factor=1.10, bonus_malus_coefficient=0.90
        )
        assert result["estimated_premium"] == 245.58
        assert result["term_months"] == 6

    def test_young_driver_pays_more_than_standard(self):
        young = quote(date_of_birth=born_years_ago(20))["estimated_premium"]
        standard = quote()["estimated_premium"]
        assert young > standard

    def test_premium_scales_linearly_with_bonus_malus(self):
        assert quote(bonus_malus_coefficient=2.0)["estimated_premium"] == pytest.approx(
            2 * quote(bonus_malus_coefficient=1.0)["estimated_premium"], abs=0.01
        )

    def test_frequency_capped_at_35_percent(self):
        result = quote(date_of_birth=born_years_ago(19), bonus_malus_coefficient=3.5)
        # annual frequency capped at 35 %, then x 6/12 for the term
        assert result["estimated_claim_frequency"] == 0.175

    def test_pure_premium_is_frequency_times_severity(self):
        r = quote(vehicle_power_kw=138)
        assert r["pure_premium"] == pytest.approx(
            r["estimated_claim_frequency"] * r["estimated_claim_severity"], abs=0.01
        )


class TestRiskLevel:
    # Low < 1.4 x base <= Medium < 2.5 x base <= High
    @pytest.mark.parametrize(
        "bonus_malus, expected",
        [(1.00, "Low"), (1.39, "Low"), (1.40, "Medium"), (2.49, "Medium"), (2.50, "High")],
    )
    def test_thresholds(self, bonus_malus, expected):
        # With every other factor forced to 1.0, premium = base * bonus_malus,
        # so the bonus-malus value IS the multiple of the base rate.
        # (Even 0-50 kW applies the power factor once, so neutralise it too --
        # forgetting that was a real bug in the first draft of this test.)
        result = quote(bonus_malus_coefficient=bonus_malus, vehicle_power_factor_table=1.00)
        assert result["risk_level"] == expected


# ------------------------------------- experience factor (added for BUG-011)
class TestExperienceFactor:
    # Full years holding a license: < 2 -> 1.20, < 5 -> 1.10, otherwise 1.00
    @pytest.mark.parametrize(
        "years, days_offset, expected",
        [
            (0, 0, 1.20),
            (2, 1, 1.20),   # 2nd license anniversary is tomorrow -> still 1 year (boundary-1)
            (2, 0, 1.10),   # exactly 2 years (boundary)
            (5, 1, 1.10),   # boundary-1
            (5, 0, 1.00),   # exactly 5 years (boundary)
            (26, 0, 1.00),
        ],
    )
    def test_experience_bands(self, years, days_offset, expected):
        result = quote(license_issue_date=born_years_ago(years, days_offset))
        assert result["experience_factor"] == expected


class TestInputValidation:
    # Added with the BUG-010 fix: impossible inputs raise ValueError.
    @pytest.mark.parametrize(
        "field, value",
        [
            ("bonus_malus_coefficient", 0),
            ("vehicle_power_kw", 0),
            ("vehicle_power_kw", -500),
            ("date_of_birth", date(2030, 1, 1)),
            ("license_issue_date", date(2030, 1, 1)),
        ],
    )
    def test_impossible_inputs_raise(self, field, value):
        with pytest.raises(ValueError):
            quote(**{field: value})


# --------------------------------------- regression tests for fixed bugs
class TestFixedPricingBugs:
    # Regression test for BUG-011 (fixed): driving experience (license_issue_date) does not affect price
    def test_new_driver_pays_more_than_experienced_driver(self):
        experienced = quote(license_issue_date=date(2000, 1, 1))["estimated_premium"]
        brand_new = quote(license_issue_date=date(2026, 6, 1))["estimated_premium"]
        assert brand_new > experienced

    # Regression test for BUG-010 (fixed): pricing accepts impossible inputs (negative bonus-malus -> negative premium)
    def test_negative_bonus_malus_is_rejected(self):
        try:
            result = quote(bonus_malus_coefficient=-1.0)
        except ValueError:
            return  # correct behaviour: the input was rejected
        assert False, f"accepted; premium = {result['estimated_premium']}"


# ------------------------------------------------------------- Full Coverage
def component(coverage_id, premium, base, freq, pure):
    return dict(
        coverage_id=coverage_id, coverage_name=f"C{coverage_id}",
        estimated_premium=premium, base_rate=base, estimated_claim_frequency=freq,
        pure_premium=pure, age_factor=1.0, vehicle_power_factor=1.05,
        experience_factor=1.0, region_factor=1.10, bonus_malus_adjustment=0.90,
    )


def test_full_coverage_premium_is_discounted_sum():
    q = calculate_full_coverage_quote([component(1, 500, 450, 0.1, 50), component(2, 300, 320, 0.2, 60)])
    assert q["subtotal_premium"] == 800
    assert q["estimated_premium"] == 720.00          # 800 * 0.90
    assert q["discount_amount"] == 80.00
    assert q["base_rate"] == 770


def test_full_coverage_frequency_is_chance_of_any_claim():
    q = calculate_full_coverage_quote([component(1, 500, 450, 0.1, 50), component(2, 300, 320, 0.2, 60)])
    assert q["estimated_claim_frequency"] == 0.28     # 1 - 0.9 * 0.8
    assert q["pure_premium"] == 110                   # expected losses add up
    assert q["estimated_claim_severity"] == round(110 / 0.28, 2)


def test_full_coverage_risk_level_ignores_discount():
    # 70 per 6 months = 140/yr = 1.4x the annual base -> Medium, even though
    # the discounted price works out below 1.4x
    q = calculate_full_coverage_quote([component(1, 70, 100, 0.1, 10)])
    assert q["estimated_premium"] < 70
    assert q["risk_level"] == "Medium"


def test_full_coverage_needs_components():
    with pytest.raises(ValueError):
        calculate_full_coverage_quote([])


# ------------------------------------------------------------- 6-month term
def test_term_premium_is_half_the_annual_rate():
    # all factors 1.0: annual premium = base rate 450, 6-month premium = 225
    r = quote(vehicle_power_factor_table=1.00, bonus_malus_coefficient=1.0)
    assert r["estimated_premium"] == 225.00


def test_risk_level_uses_annual_figures():
    # 6-month premium is 0.7x the annual base, but annually it's 1.4x -> Medium
    r = quote(vehicle_power_factor_table=1.00, bonus_malus_coefficient=1.40)
    assert r["estimated_premium"] == 315.00
    assert r["risk_level"] == "Medium"
