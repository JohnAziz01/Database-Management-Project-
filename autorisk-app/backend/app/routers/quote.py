from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..pricing import calculate_quote

router = APIRouter(prefix="/api/quote", tags=["quote"])


@router.post("", response_model=schemas.QuoteResponse)
def get_quote(payload: schemas.QuoteRequest, db: Session = Depends(get_db)):
    region = db.get(models.Region, payload.region_id)
    if region is None:
        raise HTTPException(status_code=404, detail="Region not found")

    rate = (
        db.query(models.RateTable)
        .filter(
            models.RateTable.region_id == payload.region_id,
            models.RateTable.coverage_id == payload.coverage_id,
            models.RateTable.effective_date <= date.today(),
        )
        .filter(
            (models.RateTable.expiry_date.is_(None))
            | (models.RateTable.expiry_date > date.today())
        )
        .order_by(models.RateTable.effective_date.desc())
        .first()
    )
    if rate is None:
        raise HTTPException(
            status_code=404,
            detail="No current rate table for that region/coverage combination",
        )

    result = calculate_quote(
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
    )
    return result
