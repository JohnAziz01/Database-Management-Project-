"""
/api/policyholders

Fixes after testing (see testing/docs/BUG_REPORTS.md):
  BUG-001/002  login required; customers only see their own record; only
               admins can create policyholders
  BUG-003      duplicate license number -> 409 (was a 500 crash)
  BUG-005      unknown region_id -> 422 (was a 500 crash)
  BUG-014      % and _ in the search box are matched literally
  BUG-015      duplicate-email check ignores upper/lower case
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import customer_scope, get_current_account, require_admin
from ..database import get_db

router = APIRouter(
    prefix="/api/policyholders",
    tags=["policyholders"],
    dependencies=[Depends(get_current_account)],  # BUG-001: no token -> 401
)


def _escape_like(text: str) -> str:
    """Make %, _ and the escape character match themselves in LIKE (BUG-014)."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("", response_model=List[schemas.PolicyholderOut])
def list_policyholders(
    q: Optional[str] = None,
    region_id: Optional[int] = None,
    own_id: Optional[int] = Depends(customer_scope),
    db: Session = Depends(get_db),
):
    """
    GET /api/policyholders?q=jordan&region_id=2
    `q` is optional free-text search across name/email/license,
    `region_id` optionally filters to one region — both map directly
    to the search box + region dropdown on the Policyholders page.
    """
    query = db.query(models.Policyholder)
    if own_id is not None:  # BUG-002: a customer only ever sees themself
        query = query.filter(models.Policyholder.policyholder_id == own_id)
    if q:
        like = f"%{_escape_like(q)}%"
        query = query.filter(
            or_(
                models.Policyholder.first_name.ilike(like, escape="\\"),
                models.Policyholder.last_name.ilike(like, escape="\\"),
                models.Policyholder.email.ilike(like, escape="\\"),
                models.Policyholder.license_number.ilike(like, escape="\\"),
            )
        )
    if region_id:
        query = query.filter(models.Policyholder.region_id == region_id)
    return query.order_by(models.Policyholder.policyholder_id).all()


@router.get("/{policyholder_id}", response_model=schemas.PolicyholderOut)
def get_policyholder(
    policyholder_id: int,
    own_id: Optional[int] = Depends(customer_scope),
    db: Session = Depends(get_db),
):
    ph = db.get(models.Policyholder, policyholder_id)
    # A customer asking for someone else gets the same 404 as a missing id,
    # so they can't even tell whether that record exists.
    if ph is None or (own_id is not None and ph.policyholder_id != own_id):
        raise HTTPException(status_code=404, detail="Policyholder not found")
    return ph


@router.post(
    "",
    response_model=schemas.PolicyholderOut,
    status_code=201,
    dependencies=[Depends(require_admin)],  # BUG-002: admins only
)
def create_policyholder(payload: schemas.PolicyholderCreate, db: Session = Depends(get_db)):
    # Emails arrive lower-cased (schemas.py); compare lower-cased too, in
    # case older rows were stored with capitals (BUG-015).
    if db.query(models.Policyholder).filter(func.lower(models.Policyholder.email) == payload.email).first():
        raise HTTPException(status_code=409, detail="A policyholder with that email already exists")
    if db.query(models.Policyholder).filter(models.Policyholder.license_number == payload.license_number).first():
        # BUG-003
        raise HTTPException(status_code=409, detail="A policyholder with that license number already exists")
    if payload.region_id is not None and db.get(models.Region, payload.region_id) is None:
        raise HTTPException(status_code=422, detail="Region not found")  # BUG-005

    ph = models.Policyholder(**payload.model_dump())
    db.add(ph)
    try:
        db.commit()
    except IntegrityError:
        # Safety net: if two requests race past the checks above, the DB's
        # UNIQUE constraint still catches it -- answer 409, never crash.
        db.rollback()
        raise HTTPException(status_code=409, detail="That email or license number is already in use")
    db.refresh(ph)
    return ph
