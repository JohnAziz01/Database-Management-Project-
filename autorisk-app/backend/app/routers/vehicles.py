from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])


@router.get("", response_model=List[schemas.VehicleOut])
def list_vehicles(policyholder_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.Vehicle)
    if policyholder_id:
        query = query.filter(models.Vehicle.policyholder_id == policyholder_id)
    return query.order_by(models.Vehicle.vehicle_id).all()
