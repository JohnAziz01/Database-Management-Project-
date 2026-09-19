from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/policies", tags=["policies"])


@router.get("", response_model=List[schemas.PolicyOut])
def list_policies(status_filter: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Policy)
    if status_filter:
        query = query.filter(models.Policy.status == status_filter)
    return query.order_by(models.Policy.policy_id).all()
