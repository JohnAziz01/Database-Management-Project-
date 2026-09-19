from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/coverages", tags=["coverages"])


@router.get("", response_model=List[schemas.CoverageOut])
def list_coverages(db: Session = Depends(get_db)):
    return db.query(models.Coverage).order_by(models.Coverage.coverage_name).all()
