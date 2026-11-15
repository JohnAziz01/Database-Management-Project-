"""
Aggregate/reporting-style endpoints that power the Dashboard and Reports
pages. These run real SQL aggregate queries (COUNT, SUM, AVG) against
Postgres via SQLAlchemy's query builder — this is the "SQL aggregate
queries" the reports.html demo banner mentions.

Fixes after testing (see testing/docs/BUG_REPORTS.md):
  BUG-001/002  company-wide totals are for admins only
  BUG-013      "total claims paid" only counts payments whose status is Paid
  BUG-022      ?limit= must be 1..100 (a negative value used to crash with 500)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
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
