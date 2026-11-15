from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..auth import get_current_account
from ..database import get_db

# BUG-001: login required
router = APIRouter(prefix="/api/coverages", tags=["coverages"], dependencies=[Depends(get_current_account)])


@router.get("", response_model=List[schemas.CoverageOut])
def list_coverages(db: Session = Depends(get_db)):
    return db.query(models.Coverage).order_by(models.Coverage.coverage_name).all()
