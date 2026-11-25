"""
/api/rate-tables -- versioned pricing factors per region + coverage.

Rates are never edited in place. Publishing a new rate creates a new
VERSION: the version in force is closed (expiry_date = the new version's
effective_date) and the new row starts on its effective date. Issued
policies keep the premium copied into policy_coverage, so a rate change
can never re-price an existing contract (snapshot pricing).

  GET  /api/rate-tables   any admin (Analysts too)
  POST /api/rate-tables   Administrator or Manager only
"""
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import clock, models, schemas
from ..auth import require_admin, require_manager
from ..database import get_db

router = APIRouter(prefix="/api/rate-tables", tags=["rate tables"], dependencies=[Depends(require_admin)])


def _status(rate: models.RateTable) -> str:
    today = clock.today()
    if rate.effective_date > today:
        return "Scheduled"
    if rate.expiry_date is not None and rate.expiry_date <= today:
        return "Expired"
    return "Current"


def _out(rate, region_name, coverage_name) -> schemas.RateTableOut:
    return schemas.RateTableOut(
        rate_table_id=rate.rate_table_id,
        region_id=rate.region_id,
        region_name=region_name,
        coverage_id=rate.coverage_id,
        coverage_name=coverage_name,
        effective_date=rate.effective_date,
        expiry_date=rate.expiry_date,
        base_rate=float(rate.base_rate),
        age_factor_young=float(rate.age_factor_young),
        age_factor_senior=float(rate.age_factor_senior),
        vehicle_power_factor=float(rate.vehicle_power_factor),
        bonus_malus_step=float(rate.bonus_malus_step),
        status=_status(rate),
    )


@router.get("", response_model=List[schemas.RateTableOut])
def list_rate_tables(
    region_id: Optional[int] = None,
    coverage_id: Optional[int] = None,
    status: Optional[Literal["Current", "Scheduled", "Expired"]] = None,
    db: Session = Depends(get_db),
):
    query = (
        db.query(models.RateTable, models.Region.name, models.Coverage.coverage_name)
        .join(models.Region, models.Region.region_id == models.RateTable.region_id)
        .join(models.Coverage, models.Coverage.coverage_id == models.RateTable.coverage_id)
    )
    if region_id:
        query = query.filter(models.RateTable.region_id == region_id)
    if coverage_id:
        query = query.filter(models.RateTable.coverage_id == coverage_id)
    rows = query.order_by(
        models.Region.name, models.Coverage.coverage_name, models.RateTable.effective_date.desc()
    ).all()
    result = [_out(rate, region_name, coverage_name) for rate, region_name, coverage_name in rows]
    if status:
        result = [r for r in result if r.status == status]
    return result


@router.post("", response_model=schemas.RateTableOut, status_code=201)
def publish_rate_version(
    payload: schemas.RateTableCreate,
    db: Session = Depends(get_db),
    _: models.Account = Depends(require_manager),
):
    region = db.get(models.Region, payload.region_id)
    if region is None:
        raise HTTPException(status_code=422, detail="Unknown region")
    coverage = db.get(models.Coverage, payload.coverage_id)
    if coverage is None:
        raise HTTPException(status_code=422, detail="Unknown coverage")

    versions = (
        db.query(models.RateTable)
        .filter(
            models.RateTable.region_id == payload.region_id,
            models.RateTable.coverage_id == payload.coverage_id,
        )
        .with_for_update()  # two admins publishing at once can't both close the same row
        .all()
    )
    # A version already starting on/after this date would overlap the new one.
    clash = [v for v in versions if v.effective_date >= payload.effective_date]
    if clash:
        raise HTTPException(
            status_code=409,
            detail=f"A rate version already starts on {max(v.effective_date for v in clash)}; "
                   "choose a later effective date",
        )
    # Close the version that would still be open on the new effective date.
    for v in versions:
        if v.expiry_date is None or v.expiry_date > payload.effective_date:
            v.expiry_date = payload.effective_date

    rate = models.RateTable(**payload.model_dump())
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return _out(rate, region.name, coverage.coverage_name)
