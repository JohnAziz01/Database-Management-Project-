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

Policy term: quotes are for a 6-month term (POLICY_TERM_MONTHS). Rate tables
still hold ANNUAL base rates; the annual figure is scaled by TERM_FRACTION.
Risk level is judged on the annual figure, so a shorter term never makes a
driver look less risky.
"""
from datetime import date

from . import clock

# Surcharge for inexperienced drivers, by full years holding a license.
EXPERIENCE_FACTORS = [(2, 1.20), (5, 1.10)]  # < 2 years: +20 %, < 5 years: +10 %

# Length of one policy term. Rate tables are annual, so prices and expected
# claims are multiplied by TERM_FRACTION (6 / 12 = 0.5).
POLICY_TERM_MONTHS = 6
TERM_FRACTION = POLICY_TERM_MONTHS / 12


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

    annual_premium = (
        base_rate * age_factor * experience_factor * vehicle_power_factor
        * region_factor * bonus_malus_adjustment
    )
    estimated_premium = round(annual_premium * TERM_FRACTION, 2)

    # A simple, transparent frequency/severity breakdown for the UI —
    # not actuarially rigorous, just illustrative for the class project.
    # Frequency is expected claims per TERM (annual rate, capped, x term);
    # severity (cost of one claim) doesn't depend on the term length.
    annual_frequency = min(0.35, 0.08 * age_factor * bonus_malus_adjustment)
    estimated_claim_frequency = round(annual_frequency * TERM_FRACTION, 4)
    estimated_claim_severity = round(base_rate * 6 * vehicle_power_factor, 2)
    pure_premium = round(estimated_claim_frequency * estimated_claim_severity, 2)

    # Risk level uses ANNUAL figures (base_rate is annual), unaffected by term.
    if annual_premium >= base_rate * 2.5:
        risk_level = "High"
    elif annual_premium >= base_rate * 1.4:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return {
        "estimated_premium": estimated_premium,
        "term_months": POLICY_TERM_MONTHS,
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


# --------------------------------------------------------------------------
# Full Coverage = every coverage in the catalog bundled into one quote.
# Each component is priced with calculate_quote() using its own rate table,
# then the components are combined here and a bundle discount is applied.
# --------------------------------------------------------------------------
FULL_COVERAGE_DISCOUNT = 0.10  # 10 % off the sum of the individual premiums


def calculate_full_coverage_quote(components: list[dict], discount: float = FULL_COVERAGE_DISCOUNT) -> dict:
    """Combine per-coverage quotes into one Full Coverage quote.

    `components` is a list of dicts, each one a calculate_quote() result plus
    "coverage_id" and "coverage_name".

      premium    = sum(component premiums) * (1 - discount)
      frequency  = P(at least one claim in the term) = 1 - prod(1 - f_i)
                   (coverages assumed independent)
      pure       = sum(component pure premiums)   -- expected loss is not
                   reduced by a commercial discount
      severity   = pure / frequency, so pure = frequency * severity still holds
      risk level = undiscounted total, annualised, vs. the summed (annual)
                   base rates, using the same 2.5x / 1.4x thresholds as a
                   single coverage, so neither the discount nor the 6-month
                   term makes a risky driver look safer
    """
    if not components:
        raise ValueError("Full coverage needs at least one component coverage")
    if not 0 <= discount < 1:
        raise ValueError("discount must be in [0, 1)")

    subtotal = round(sum(c["estimated_premium"] for c in components), 2)
    estimated_premium = round(subtotal * (1 - discount), 2)
    discount_amount = round(subtotal - estimated_premium, 2)
    base_rate = round(sum(c["base_rate"] for c in components), 2)

    no_claim = 1.0
    for c in components:
        no_claim *= 1 - c["estimated_claim_frequency"]
    estimated_claim_frequency = round(1 - no_claim, 4)

    pure_premium = round(sum(c["pure_premium"] for c in components), 2)
    estimated_claim_severity = (
        round(pure_premium / estimated_claim_frequency, 2) if estimated_claim_frequency else 0.0
    )

    annual_subtotal = subtotal / TERM_FRACTION
    if annual_subtotal >= base_rate * 2.5:
        risk_level = "High"
    elif annual_subtotal >= base_rate * 1.4:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    first = components[0]
    return {
        "estimated_premium": estimated_premium,
        "term_months": POLICY_TERM_MONTHS,
        "risk_level": risk_level,
        "estimated_claim_frequency": estimated_claim_frequency,
        "estimated_claim_severity": estimated_claim_severity,
        "pure_premium": pure_premium,
        "base_rate": base_rate,
        # age and vehicle-power factors come from each coverage's own rate
        # table, so they differ per component -- see coverage_breakdown.
        "age_factor": None,
        "vehicle_power_factor": None,
        # these three don't depend on the rate table, so they're shared
        "experience_factor": first["experience_factor"],
        "region_factor": first["region_factor"],
        "bonus_malus_adjustment": first["bonus_malus_adjustment"],
        "full_coverage": True,
        "subtotal_premium": subtotal,
        "discount_rate": discount,
        "discount_amount": discount_amount,
        "coverage_breakdown": [
            {
                "coverage_id": c["coverage_id"],
                "coverage_name": c["coverage_name"],
                "base_rate": c["base_rate"],
                "age_factor": c["age_factor"],
                "vehicle_power_factor": c["vehicle_power_factor"],
                "estimated_premium": c["estimated_premium"],
            }
            for c in components
        ],
    }
