from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/regions", tags=["regions"])


@router.get("", response_model=List[schemas.RegionOut])
def list_regions(db: Session = Depends(get_db)):
    return db.query(models.Region).order_by(models.Region.name).all()
