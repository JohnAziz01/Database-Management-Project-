from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/claims", tags=["claims"])


@router.get("", response_model=List[schemas.ClaimOut])
def list_claims(status_filter: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Claim)
    if status_filter:
        query = query.filter(models.Claim.status == status_filter)
    return query.order_by(models.Claim.claim_id.desc()).all()


@router.post("", response_model=schemas.ClaimOut, status_code=201)
def create_claim(payload: schemas.ClaimCreate, db: Session = Depends(get_db)):
    policy = db.get(models.Policy, payload.policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    claim = models.Claim(**payload.model_dump())
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


@router.get("/{claim_id}/payments", response_model=List[schemas.ClaimPaymentOut])
def list_claim_payments(claim_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.ClaimPayment)
        .filter(models.ClaimPayment.claim_id == claim_id)
        .order_by(models.ClaimPayment.payment_seq)
        .all()
    )
