from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..auth import get_current_account
from ..database import get_db

# BUG-001: login required
router = APIRouter(prefix="/api/regions", tags=["regions"], dependencies=[Depends(get_current_account)])


@router.get("", response_model=List[schemas.RegionOut])
def list_regions(db: Session = Depends(get_db)):
    return db.query(models.Region).order_by(models.Region.name).all()
