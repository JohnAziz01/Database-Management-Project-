"""
/api/risk/analysis -- claim experience by rating factor.

For each segment of one dimension (driver age band, vehicle power band,
region, ...) it reports how many policies there are, how often they claim,
how much a claim costs, and the loss ratio (paid / premium). This is how
an actuary checks whether the pricing factors match reality: a segment
with a high loss ratio is under-priced.

The dimension comes from a fixed whitelist, each mapped to a SQL
expression written here -- user input never becomes SQL text.
"""
from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..database import get_db

router = APIRouter(prefix="/api/risk", tags=["risk analysis"], dependencies=[Depends(require_admin)])

# Ages and years are measured at the policy START date, which is what an
# insurer would have known when pricing the policy.
_AGE = "date_part('year', age(p.start_date, ph.date_of_birth))"
_EXPERIENCE = "date_part('year', age(p.start_date, ph.license_issue_date))"
_VEHICLE_AGE = "(EXTRACT(YEAR FROM p.start_date)::int - v.manufacture_year)"

# dimension -> (label, SQL expression returning "NN|segment label", description)
# The "NN|" prefix only fixes the display order and is stripped below.
DIMENSIONS = {
    "driver_age": ("Driver age", f"""CASE
        WHEN {_AGE} < 25 THEN '1|18–24' WHEN {_AGE} < 35 THEN '2|25–34' WHEN {_AGE} < 50 THEN '3|35–49'
        WHEN {_AGE} < 65 THEN '4|50–64' ELSE '5|65+' END""",
        "Age at policy start. Pricing applies a young-driver factor under 25 and a senior factor from 65."),
    "experience": ("Driving experience", f"""CASE
        WHEN {_EXPERIENCE} < 2 THEN '1|Under 2 years' WHEN {_EXPERIENCE} < 5 THEN '2|2–4 years'
        WHEN {_EXPERIENCE} < 10 THEN '3|5–9 years' ELSE '4|10+ years' END""",
        "Years licensed at policy start. Pricing adds +20 % under 2 years and +10 % under 5."),
    "vehicle_power": ("Vehicle power", """CASE
        WHEN v.engine_power_kw < 60 THEN '1|Under 60 kW' WHEN v.engine_power_kw < 100 THEN '2|60–99 kW'
        WHEN v.engine_power_kw < 150 THEN '3|100–149 kW' ELSE '4|150 kW+' END""",
        "Engine power. Pricing compounds the power factor for every 50 kW above 50."),
    "vehicle_age": ("Vehicle age", f"""CASE
        WHEN {_VEHICLE_AGE} <= 2 THEN '1|0–2 years' WHEN {_VEHICLE_AGE} <= 5 THEN '2|3–5 years'
        WHEN {_VEHICLE_AGE} <= 10 THEN '3|6–10 years' ELSE '4|11+ years' END""",
        "Vehicle age at policy start. Not priced yet: this view shows whether it should be."),
    "bonus_malus": ("Bonus-malus", """CASE
        WHEN p.bonus_malus_coefficient < 1.00 THEN '1|Bonus (< 1.00)'
        WHEN p.bonus_malus_coefficient = 1.00 THEN '2|Neutral (1.00)'
        WHEN p.bonus_malus_coefficient <= 1.50 THEN '3|Malus 1.01–1.50'
        ELSE '4|Malus > 1.50' END""",
        "Claims-history coefficient. Below 1.00 is a no-claims bonus; above 1.00 is a malus."),
    "region": ("Region", "'0|' || COALESCE(r.name, 'No region')",
        "Policyholder's region. Pricing multiplies by each region's base risk factor."),
    "risk_tier": ("Risk tier", """CASE ph.risk_tier
        WHEN 'Low' THEN '1|Low' WHEN 'Medium' THEN '2|Medium' WHEN 'High' THEN '3|High' ELSE '4|Unrated' END""",
        "Underwriter's tier on the policyholder record. Imported historical drivers are unrated."),
}

_SQL = """
WITH paid AS (
    SELECT c.policy_id,
           COUNT(DISTINCT c.claim_id) AS claims,
           COALESCE(SUM(cp.amount) FILTER (WHERE cp.status = 'Paid'), 0) AS paid
    FROM claim c LEFT JOIN claim_payment cp ON cp.claim_id = c.claim_id
    GROUP BY c.policy_id
)
SELECT {segment} AS segment,
       COUNT(*)                         AS policies,
       COALESCE(SUM(p.total_premium), 0) AS premium,
       COALESCE(SUM(paid.claims), 0)     AS claims,
       COALESCE(SUM(paid.paid), 0)       AS paid
FROM policy p
JOIN policyholder ph ON ph.policyholder_id = p.policyholder_id
JOIN vehicle v       ON v.vehicle_id = p.vehicle_id
LEFT JOIN region r   ON r.region_id = ph.region_id
LEFT JOIN paid       ON paid.policy_id = p.policy_id
GROUP BY 1
"""


def _metrics(policies, premium, claims, paid):
    policies, premium, claims, paid = int(policies), float(premium), int(claims), float(paid)
    return {
        "policies": policies,
        "premium": round(premium, 2),
        "claims": claims,
        "paid": round(paid, 2),
        "claim_frequency": round(claims / policies, 4) if policies else None,  # claims per policy
        "average_severity": round(paid / claims, 2) if claims else None,        # cost per claim
        "loss_ratio": round(paid / premium, 4) if premium else None,            # paid / premium
    }


@router.get("/dimensions")
def list_dimensions():
    return [{"key": k, "label": v[0], "description": v[2]} for k, v in DIMENSIONS.items()]


@router.get("/analysis")
def risk_analysis(
    dimension: Literal[tuple(DIMENSIONS)] = "driver_age",  # type: ignore[valid-type]
    db: Session = Depends(get_db),
):
    label, expression, description = DIMENSIONS[dimension]
    rows = db.execute(text(_SQL.format(segment=expression))).all()

    segments = []
    for key, *values in rows:
        order, name = key.split("|", 1)
        segments.append({"segment": name, "_order": order, **_metrics(*values)})
    if dimension == "region":
        segments.sort(key=lambda s: -(s["loss_ratio"] or 0))  # riskiest region first
    else:
        segments.sort(key=lambda s: s["_order"])
    for s in segments:
        del s["_order"]

    overall = _metrics(*(sum(r[i] for r in rows) for i in range(1, 5))) if rows else _metrics(0, 0, 0, 0)
    return {
        "dimension": dimension,
        "label": label,
        "description": description,
        "overall": overall,
        "segments": segments,
    }
