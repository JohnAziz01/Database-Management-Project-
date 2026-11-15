from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    auth.check_login_allowed(payload.email)  # BUG-017: 429 after too many failures
    account = (
        db.query(models.Account)
        .filter(func.lower(models.Account.email) == payload.email)  # email is lower-cased by the schema
        .first()
    )
    if account is None or not auth.verify_password(payload.password, account.password_hash):
        auth.record_failed_login(payload.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    auth.clear_failed_logins(payload.email)
    if not account.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    account.last_login_at = datetime.now(timezone.utc)
    db.commit()

    token = auth.create_access_token(account.account_id, account.email)
    return schemas.LoginResponse(
        access_token=token,
        account_id=account.account_id,
        email=account.email,
        account_type=account.account_type,
    )


@router.get("/me")
def me(current=Depends(auth.get_current_account)):
    return {
        "account_id": current.account_id,
        "email": current.email,
        "account_type": current.account_type,
    }
