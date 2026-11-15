from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import customer_scope, get_current_account
from ..database import get_db

# BUG-001/002: login required; customers only see their own vehicles.
router = APIRouter(prefix="/api/vehicles", tags=["vehicles"], dependencies=[Depends(get_current_account)])


@router.get("", response_model=List[schemas.VehicleOut])
def list_vehicles(
    policyholder_id: Optional[int] = None,
    own_id: Optional[int] = Depends(customer_scope),
    db: Session = Depends(get_db),
):
    query = db.query(models.Vehicle)
    if own_id is not None:
        query = query.filter(models.Vehicle.policyholder_id == own_id)
    if policyholder_id:
        query = query.filter(models.Vehicle.policyholder_id == policyholder_id)
    return query.order_by(models.Vehicle.vehicle_id).all()
