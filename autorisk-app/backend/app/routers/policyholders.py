from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/policyholders", tags=["policyholders"])


@router.get("", response_model=List[schemas.PolicyholderOut])
def list_policyholders(
    q: Optional[str] = None,
    region_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    GET /api/policyholders?q=jordan&region_id=2
    `q` is optional free-text search across name/email/license,
    `region_id` optionally filters to one region — both map directly
    to the search box + region dropdown on the Policyholders page.
    """
    query = db.query(models.Policyholder)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                models.Policyholder.first_name.ilike(like),
                models.Policyholder.last_name.ilike(like),
                models.Policyholder.email.ilike(like),
                models.Policyholder.license_number.ilike(like),
            )
        )
    if region_id:
        query = query.filter(models.Policyholder.region_id == region_id)
    return query.order_by(models.Policyholder.policyholder_id).all()


@router.get("/{policyholder_id}", response_model=schemas.PolicyholderOut)
def get_policyholder(policyholder_id: int, db: Session = Depends(get_db)):
    ph = db.get(models.Policyholder, policyholder_id)
    if ph is None:
        raise HTTPException(status_code=404, detail="Policyholder not found")
    return ph


@router.post("", response_model=schemas.PolicyholderOut, status_code=201)
def create_policyholder(payload: schemas.PolicyholderCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Policyholder).filter(models.Policyholder.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="A policyholder with that email already exists")

    ph = models.Policyholder(**payload.model_dump())
    db.add(ph)
    db.commit()
    db.refresh(ph)
    return ph
