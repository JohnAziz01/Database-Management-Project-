from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import customer_scope, get_current_account
from ..database import get_db

# BUG-001/002: login required; customers only see their own policies.
router = APIRouter(prefix="/api/policies", tags=["policies"], dependencies=[Depends(get_current_account)])


@router.get("", response_model=List[schemas.PolicyOut])
def list_policies(
    status_filter: Optional[str] = None,
    own_id: Optional[int] = Depends(customer_scope),
    db: Session = Depends(get_db),
):
    query = db.query(models.Policy)
    if own_id is not None:
        query = query.filter(models.Policy.policyholder_id == own_id)
    if status_filter:
        query = query.filter(models.Policy.status == status_filter)
    return query.order_by(models.Policy.policy_id).all()
