"""
Pricing / quote calculation logic.

This is a plain Python function with no FastAPI or SQLAlchemy imports —
that's deliberate. Keeping "business logic" separate from "web framework
glue" makes it trivial to unit test (call the function directly with fake
numbers) and reuse (the /quote endpoint calls it, and later you could call
it again from a nightly re-rating job, a CLI script, etc.).

The formula mirrors the "Pricing Factors" panel in quote.html:
  base_rate * age_factor * vehicle_power_factor * region_factor * bonus_malus
"""
from datetime import date


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
    as_of = as_of or date.today()
    age = _age(date_of_birth, as_of)

    # Age factor: young/inexperienced and senior drivers carry a surcharge.
    if age < 25:
        age_factor = age_factor_young
    elif age >= 65:
        age_factor = age_factor_senior
    else:
        age_factor = 1.00

    # Vehicle power factor scales with engine power in 50kW bands.
    power_bands = max(vehicle_power_kw - 50, 0) // 50
    vehicle_power_factor = round(vehicle_power_factor_table ** (1 + power_bands), 4)

    region_factor = region_base_risk_factor
    bonus_malus_adjustment = bonus_malus_coefficient * bonus_malus_step

    estimated_premium = round(
        base_rate * age_factor * vehicle_power_factor * region_factor * bonus_malus_adjustment,
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
        "vehicle_power_factor": vehicle_power_factor,
        "region_factor": region_factor,
        "bonus_malus_adjustment": bonus_malus_adjustment,
    }
