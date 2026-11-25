"""
/api/quote -- the pricing calculator.

Fixes after testing (see testing/docs/BUG_REPORTS.md):
  BUG-001  login required
  BUG-009  GET /api/quote/options lists only the region/coverage pairs that
           have a current rate table, so the form never offers a dead end
  BUG-010  impossible inputs are rejected in schemas.QuoteRequest (422)
  BUG-023  "today" comes from app.clock (UTC, same as the database)

Full Coverage: full_coverage=true prices every coverage in the catalog with
its own rate table and combines them (pricing.calculate_full_coverage_quote).
It is offered only in regions where every coverage has a current rate table.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import clock, models, schemas
from ..auth import get_current_account
from ..database import get_db
from ..pricing import calculate_full_coverage_quote, calculate_quote

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
    options = [
        schemas.QuoteOption(region_id=r[0], region_name=r[1], coverage_id=r[2], coverage_name=r[3])
        for r in rows
    ]

    # Full Coverage is offered where every coverage in the catalog is priced.
    all_coverages = {c for (c,) in db.query(models.Coverage.coverage_id).all()}
    priced: dict[int, set] = {}
    names: dict[int, str] = {}
    for region_id, region_name, coverage_id, _ in rows:
        priced.setdefault(region_id, set()).add(coverage_id)
        names[region_id] = region_name
    full = [
        schemas.QuoteOption(region_id=rid, region_name=names[rid], coverage_name="Full Coverage", full_coverage=True)
        for rid in sorted(priced, key=lambda rid: names[rid])
        if all_coverages and priced[rid] >= all_coverages
    ]
    return options + full


def _latest_rate(db: Session, region_id: int, coverage_id: int):
    return (
        _current_rates(db)
        .filter(
            models.RateTable.region_id == region_id,
            models.RateTable.coverage_id == coverage_id,
        )
        .order_by(models.RateTable.effective_date.desc())
        .first()
    )


def _price(payload: schemas.QuoteRequest, region: models.Region, rate: models.RateTable) -> dict:
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


@router.post("", response_model=schemas.QuoteResponse)
def get_quote(payload: schemas.QuoteRequest, db: Session = Depends(get_db)):
    region = db.get(models.Region, payload.region_id)
    if region is None:
        raise HTTPException(status_code=404, detail="Region not found")

    if payload.full_coverage:
        components = []
        for coverage in db.query(models.Coverage).order_by(models.Coverage.coverage_id).all():
            rate = _latest_rate(db, payload.region_id, coverage.coverage_id)
            if rate is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Full Coverage is not available in this region: no current rate table for {coverage.coverage_name}",
                )
            components.append({
                **_price(payload, region, rate),
                "coverage_id": coverage.coverage_id,
                "coverage_name": coverage.coverage_name,
            })
        return calculate_full_coverage_quote(components)

    rate = _latest_rate(db, payload.region_id, payload.coverage_id)
    if rate is None:
        raise HTTPException(
            status_code=404,
            detail="No current rate table for that region/coverage combination",
        )
    return _price(payload, region, rate)
