"""
/api/claims

Fixes after testing (see testing/docs/BUG_REPORTS.md):
  BUG-001/002  login required; customers only see / file claims on their own policies
  BUG-006      fault_percentage range is checked in schemas.py (422, not 500)
  BUG-008      claim date must fall inside the policy period and not be in the future
  BUG-021      payments for a claim that doesn't exist -> 404
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import customer_scope, get_current_account
from ..database import get_db

router = APIRouter(
    prefix="/api/claims",
    tags=["claims"],
    dependencies=[Depends(get_current_account)],
)


def _visible_claims(db: Session, own_id: Optional[int]):
    query = db.query(models.Claim)
    if own_id is not None:
        query = query.join(models.Policy).filter(models.Policy.policyholder_id == own_id)
    return query


@router.get("", response_model=List[schemas.ClaimOut])
def list_claims(
    status_filter: Optional[str] = None,
    own_id: Optional[int] = Depends(customer_scope),
    db: Session = Depends(get_db),
):
    query = _visible_claims(db, own_id)
    if status_filter:
        query = query.filter(models.Claim.status == status_filter)
    return query.order_by(models.Claim.claim_id.desc()).all()


@router.post("", response_model=schemas.ClaimOut, status_code=201)
def create_claim(
    payload: schemas.ClaimCreate,
    own_id: Optional[int] = Depends(customer_scope),
    db: Session = Depends(get_db),
):
    policy = db.get(models.Policy, payload.policy_id)
    if policy is None or (own_id is not None and policy.policyholder_id != own_id):
        raise HTTPException(status_code=404, detail="Policy not found")
    if not (policy.start_date <= payload.claim_date <= policy.end_date):  # BUG-008
        raise HTTPException(
            status_code=422,
            detail=f"Claim date must be within the policy period "
                   f"({policy.start_date} to {policy.end_date})",
        )
    claim = models.Claim(**payload.model_dump())
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


@router.get("/{claim_id}/payments", response_model=List[schemas.ClaimPaymentOut])
def list_claim_payments(
    claim_id: int,
    own_id: Optional[int] = Depends(customer_scope),
    db: Session = Depends(get_db),
):
    claim = _visible_claims(db, own_id).filter(models.Claim.claim_id == claim_id).first()
    if claim is None:  # BUG-021
        raise HTTPException(status_code=404, detail="Claim not found")
    return (
        db.query(models.ClaimPayment)
        .filter(models.ClaimPayment.claim_id == claim_id)
        .order_by(models.ClaimPayment.payment_seq)
        .all()
    )
