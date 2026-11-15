"""
/api/quote -- the pricing calculator.

Fixes after testing (see testing/docs/BUG_REPORTS.md):
  BUG-001  login required
  BUG-009  GET /api/quote/options lists only the region/coverage pairs that
           have a current rate table, so the form never offers a dead end
  BUG-010  impossible inputs are rejected in schemas.QuoteRequest (422)
  BUG-023  "today" comes from app.clock (UTC, same as the database)
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import clock, models, schemas
from ..auth import get_current_account
from ..database import get_db
from ..pricing import calculate_quote

router = APIRouter(prefix="/api/quote", tags=["quote"], dependencies=[Depends(get_current_account)])


def _current_rates(db: Session):
    today = clock.today()
    return db.query(models.RateTable).filter(
        models.RateTable.effective_date <= today,
        (models.RateTable.expiry_date.is_(None)) | (models.RateTable.expiry_date > today),
    )


@router.get("/options", response_model=List[schemas.QuoteOption])
def quote_options(db: Session = Depends(get_db)):
    """Region/coverage pairs that can actually be quoted today (BUG-009)."""
    rows = (
        _current_rates(db)
        .join(models.Region, models.Region.region_id == models.RateTable.region_id)
        .join(models.Coverage, models.Coverage.coverage_id == models.RateTable.coverage_id)
        .with_entities(
            models.Region.region_id, models.Region.name,
            models.Coverage.coverage_id, models.Coverage.coverage_name,
        )
        .distinct()
        .order_by(models.Region.name, models.Coverage.coverage_name)
        .all()
    )
    return [
        schemas.QuoteOption(region_id=r[0], region_name=r[1], coverage_id=r[2], coverage_name=r[3])
        for r in rows
    ]


@router.post("", response_model=schemas.QuoteResponse)
def get_quote(payload: schemas.QuoteRequest, db: Session = Depends(get_db)):
    region = db.get(models.Region, payload.region_id)
    if region is None:
        raise HTTPException(status_code=404, detail="Region not found")

    rate = (
        _current_rates(db)
        .filter(
            models.RateTable.region_id == payload.region_id,
            models.RateTable.coverage_id == payload.coverage_id,
        )
        .order_by(models.RateTable.effective_date.desc())
        .first()
    )
    if rate is None:
        raise HTTPException(
            status_code=404,
            detail="No current rate table for that region/coverage combination",
        )

    return calculate_quote(
        date_of_birth=payload.date_of_birth,
        license_issue_date=payload.license_issue_date,
        bonus_malus_coefficient=payload.bonus_malus_coefficient,
        vehicle_manufacture_year=payload.vehicle_manufacture_year,
        vehicle_power_kw=payload.vehicle_power_kw,
        region_base_risk_factor=float(region.base_risk_factor),
        base_rate=float(rate.base_rate),
        age_factor_young=float(rate.age_factor_young),
        age_factor_senior=float(rate.age_factor_senior),
        vehicle_power_factor_table=float(rate.vehicle_power_factor),
        bonus_malus_step=float(rate.bonus_malus_step),
        as_of=clock.today(),
    )
