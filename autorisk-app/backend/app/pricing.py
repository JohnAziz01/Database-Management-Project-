"""
Pricing / quote calculation logic.

This is a plain Python function with no FastAPI or SQLAlchemy imports —
that's deliberate. Keeping "business logic" separate from "web framework
glue" makes it trivial to unit test (call the function directly with fake
numbers) and reuse (the /quote endpoint calls it, and later you could call
it again from a nightly re-rating job, a CLI script, etc.).

The formula mirrors the "Pricing Factors" panel in quote.html:
  base_rate * age_factor * experience_factor * vehicle_power_factor
            * region_factor * bonus_malus

Changes after testing (see testing/docs/BUG_REPORTS.md):
  BUG-010  impossible inputs raise ValueError instead of giving a negative price
  BUG-011  driving experience (years since license_issue_date) now affects price
"""
from datetime import date

from . import clock

# Surcharge for inexperienced drivers, by full years holding a license.
EXPERIENCE_FACTORS = [(2, 1.20), (5, 1.10)]  # < 2 years: +20 %, < 5 years: +10 %


def _age(born: date, as_of: date) -> int:
    years = as_of.year - born.year
    if (as_of.month, as_of.day) < (born.month, born.day):
        years -= 1
    return years


def calculate_quote(
    *,
    date_of_birth: date,
    license_issue_date: date,
    bonus_malus_coefficient: float,
    vehicle_manufacture_year: int,
    vehicle_power_kw: int,
    region_base_risk_factor: float,
    base_rate: float,
    age_factor_young: float,
    age_factor_senior: float,
    vehicle_power_factor_table: float,
    bonus_malus_step: float,
    as_of: date | None = None,
) -> dict:
    as_of = as_of or clock.today()

    # BUG-010: refuse inputs that can't describe a real driver or car, so a
    # caller can never get a negative or zero premium out of this function.
    if bonus_malus_coefficient <= 0:
        raise ValueError("bonus_malus_coefficient must be greater than 0")
    if vehicle_power_kw <= 0:
        raise ValueError("vehicle_power_kw must be greater than 0")
    if date_of_birth > as_of:
        raise ValueError("date_of_birth cannot be in the future")
    if license_issue_date > as_of:
        raise ValueError("license_issue_date cannot be in the future")

    age = _age(date_of_birth, as_of)

    # Age factor: young/inexperienced and senior drivers carry a surcharge.
    if age < 25:
        age_factor = age_factor_young
    elif age >= 65:
        age_factor = age_factor_senior
    else:
        age_factor = 1.00

    # Experience factor (BUG-011): new drivers carry a surcharge.
    years_licensed = _age(license_issue_date, as_of)
    experience_factor = 1.00
    for max_years, factor in EXPERIENCE_FACTORS:
        if years_licensed < max_years:
            experience_factor = factor
            break

    # Vehicle power factor scales with engine power in 50kW bands.
    power_bands = max(vehicle_power_kw - 50, 0) // 50
    vehicle_power_factor = round(vehicle_power_factor_table ** (1 + power_bands), 4)

    region_factor = region_base_risk_factor
    bonus_malus_adjustment = bonus_malus_coefficient * bonus_malus_step

    estimated_premium = round(
        base_rate * age_factor * experience_factor * vehicle_power_factor
        * region_factor * bonus_malus_adjustment,
        2,
    )

    # A simple, transparent frequency/severity breakdown for the UI —
    # not actuarially rigorous, just illustrative for the class project.
    estimated_claim_frequency = round(min(0.35, 0.08 * age_factor * bonus_malus_adjustment), 4)
    estimated_claim_severity = round(base_rate * 6 * vehicle_power_factor, 2)
    pure_premium = round(estimated_claim_frequency * estimated_claim_severity, 2)

    if estimated_premium >= base_rate * 2.5:
        risk_level = "High"
    elif estimated_premium >= base_rate * 1.4:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return {
        "estimated_premium": estimated_premium,
        "risk_level": risk_level,
        "estimated_claim_frequency": estimated_claim_frequency,
        "estimated_claim_severity": estimated_claim_severity,
        "pure_premium": pure_premium,
        "base_rate": base_rate,
        "age_factor": age_factor,
        "experience_factor": experience_factor,
        "vehicle_power_factor": vehicle_power_factor,
        "region_factor": region_factor,
        "bonus_malus_adjustment": bonus_malus_adjustment,
    }
