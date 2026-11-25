"""
Aggregate/reporting-style endpoints that power the Dashboard and Reports
pages. These run real SQL aggregate queries (COUNT, SUM, AVG) against
Postgres via SQLAlchemy's query builder — this is the "SQL aggregate
queries" the reports.html demo banner mentions.

Fixes after testing (see testing/docs/BUG_REPORTS.md):
  BUG-001/002  company-wide totals are for admins only
  BUG-013      "total claims paid" only counts payments whose status is Paid
  BUG-022      ?limit= must be 1..100 (a negative value used to crash with 500)

/portfolio covers EVERY policy, including the expired historical policies
imported from the freMTPL2 data handoff (data-handoff/), which the
"active only" summary cards above leave out.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from .. import models
from ..auth import require_admin
from ..database import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"], dependencies=[Depends(require_admin)])


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    active_policies = (
        db.query(func.count(models.Policy.policy_id))
        .filter(models.Policy.status == "Active")
        .scalar()
    )
    total_premium = (
        db.query(func.coalesce(func.sum(models.Policy.total_premium), 0))
        .filter(models.Policy.status == "Active")
        .scalar()
    )
    open_claims = (
        db.query(func.count(models.Claim.claim_id))
        .filter(models.Claim.status.in_(["Open", "Pending"]))
        .scalar()
    )
    total_paid = (
        db.query(func.coalesce(func.sum(models.ClaimPayment.amount), 0))
        .filter(models.ClaimPayment.status == "Paid")  # BUG-013
        .scalar()
    )
    policyholder_count = db.query(func.count(models.Policyholder.policyholder_id)).scalar()

    return {
        "active_policies": active_policies,
        "total_premium_written": float(total_premium),
        "open_claims": open_claims,
        "total_claims_paid": float(total_paid),
        "policyholders": policyholder_count,
    }


@router.get("/recent-claims")
def recent_claims(db: Session = Depends(get_db), limit: int = Query(5, ge=1, le=100)):  # BUG-022
    rows = (
        db.query(models.Claim)
        .order_by(models.Claim.claim_date.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "claim_id": c.claim_id,
            "policy_id": c.policy_id,
            "claim_date": c.claim_date,
            "status": c.status,
            "fault_percentage": float(c.fault_percentage),
        }
        for c in rows
    ]


# One row per policy with its claim count and Paid amount, pre-aggregated so
# joining claims and payments can't double-count a policy's premium.
_POLICY_FACTS = """
    WITH paid AS (
        SELECT c.policy_id,
               COUNT(DISTINCT c.claim_id)                                AS claims,
               COALESCE(SUM(cp.amount) FILTER (WHERE cp.status = 'Paid'), 0) AS paid
        FROM claim c
        LEFT JOIN claim_payment cp ON cp.claim_id = c.claim_id
        GROUP BY c.policy_id
    )
    SELECT p.policy_id, p.start_date, p.total_premium, ph.region_id,
           COALESCE(paid.claims, 0) AS claims, COALESCE(paid.paid, 0) AS paid
    FROM policy p
    JOIN policyholder ph ON ph.policyholder_id = p.policyholder_id
    LEFT JOIN paid ON paid.policy_id = p.policy_id
"""


def _ratio(num, den):
    return round(float(num) / float(den), 4) if den else None


@router.get("/portfolio")
def portfolio(db: Session = Depends(get_db)):
    """Whole-book view: totals, by region, and by policy start year."""
    totals = db.execute(text(f"""
        SELECT COUNT(*), COALESCE(SUM(total_premium), 0), COALESCE(SUM(claims), 0), COALESCE(SUM(paid), 0)
        FROM ({_POLICY_FACTS}) f
    """)).one()
    by_region = db.execute(text(f"""
        SELECT r.name, COUNT(*), SUM(f.total_premium), SUM(f.claims), SUM(f.paid)
        FROM ({_POLICY_FACTS}) f
        LEFT JOIN region r ON r.region_id = f.region_id
        GROUP BY r.name
        ORDER BY SUM(f.paid) DESC, r.name
    """)).all()
    by_year = db.execute(text(f"""
        SELECT EXTRACT(YEAR FROM f.start_date)::int, COUNT(*), SUM(f.total_premium), SUM(f.claims), SUM(f.paid)
        FROM ({_POLICY_FACTS}) f
        GROUP BY 1
        ORDER BY 1
    """)).all()

    def row(name_key, r):
        return {
            name_key: r[0] if r[0] is not None else "Unknown",
            "policies": r[1],
            "premium": float(r[2] or 0),
            "claims": int(r[3] or 0),
            "paid": float(r[4] or 0),
            "loss_ratio": _ratio(r[4] or 0, r[2] or 0),
        }

    policies, premium, claims, paid = totals
    return {
        "totals": {
            "policies": policies,
            "premium": float(premium),
            "claims": int(claims),
            "paid": float(paid),
            "loss_ratio": _ratio(paid, premium),          # paid / premium
            "claim_frequency": _ratio(claims, policies),  # claims per policy
            "average_claim": round(float(paid) / int(claims), 2) if claims else None,
        },
        "by_region": [row("region", r) for r in by_region],
        "by_year": [row("year", r) for r in by_year],
    }
