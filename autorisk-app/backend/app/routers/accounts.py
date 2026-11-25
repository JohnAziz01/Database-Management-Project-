"""
/api/accounts -- login accounts for customers and staff.

  GET   /api/accounts                     any admin (Analysts too)
  POST  /api/accounts                     Administrator / Manager
  PATCH /api/accounts/{id}                enable/disable, change staff role
  POST  /api/accounts/{id}/reset-password set a new password

Password hashes are never returned. Guards keep the system usable: you
cannot disable or demote your own account, and the last active
Administrator/Manager cannot be disabled or demoted.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import MANAGE_ROLES, hash_password, require_admin, require_manager
from ..database import get_db

router = APIRouter(prefix="/api/accounts", tags=["accounts"], dependencies=[Depends(require_admin)])


def _out(a: models.Account) -> schemas.AccountOut:
    ph = a.policyholder
    return schemas.AccountOut(
        account_id=a.account_id,
        email=a.email,
        account_type=a.account_type,
        admin_role=a.admin_role,
        policyholder_id=a.policyholder_id,
        policyholder_name=f"{ph.first_name} {ph.last_name}" if ph else None,
        is_active=a.is_active,
        created_at=a.created_at,
        last_login_at=a.last_login_at,
    )


def _get(db: Session, account_id: int) -> models.Account:
    account = db.get(models.Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


def _other_active_managers(db: Session, account_id: int) -> int:
    return (
        db.query(func.count(models.Account.account_id))
        .filter(
            models.Account.account_type == "Admin",
            models.Account.admin_role.in_(MANAGE_ROLES),
            models.Account.is_active.is_(True),
            models.Account.account_id != account_id,
        )
        .scalar()
    )


@router.get("", response_model=List[schemas.AccountOut])
def list_accounts(db: Session = Depends(get_db)):
    accounts = db.query(models.Account).order_by(models.Account.account_type, models.Account.email).all()
    return [_out(a) for a in accounts]


@router.post("", response_model=schemas.AccountOut, status_code=201)
def create_account(
    payload: schemas.AccountCreate,
    db: Session = Depends(get_db),
    _: models.Account = Depends(require_manager),
):
    if db.query(models.Account).filter(func.lower(models.Account.email) == payload.email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    if payload.account_type == "Customer":
        if db.get(models.Policyholder, payload.policyholder_id) is None:
            raise HTTPException(status_code=422, detail="Unknown policyholder")
        if db.query(models.Account).filter(models.Account.policyholder_id == payload.policyholder_id).first():
            raise HTTPException(status_code=409, detail="This policyholder already has an account")

    account = models.Account(
        email=payload.email,
        password_hash=hash_password(payload.password),
        account_type=payload.account_type,
        admin_role=payload.admin_role,
        policyholder_id=payload.policyholder_id,
        is_active=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return _out(account)


@router.patch("/{account_id}", response_model=schemas.AccountOut)
def update_account(
    account_id: int,
    payload: schemas.AccountUpdate,
    db: Session = Depends(get_db),
    me: models.Account = Depends(require_manager),
):
    account = _get(db, account_id)
    is_manager = account.account_type == "Admin" and account.admin_role in MANAGE_ROLES and account.is_active

    if payload.admin_role is not None:
        if account.account_type != "Admin":
            raise HTTPException(status_code=422, detail="Only staff accounts have a role")
        demoting = payload.admin_role not in MANAGE_ROLES
        if demoting and account.account_id == me.account_id:
            raise HTTPException(status_code=409, detail="You cannot remove your own management role")
        if demoting and is_manager and _other_active_managers(db, account_id) == 0:
            raise HTTPException(status_code=409, detail="At least one active Administrator or Manager must remain")
        account.admin_role = payload.admin_role

    if payload.is_active is False:
        if account.account_id == me.account_id:
            raise HTTPException(status_code=409, detail="You cannot disable your own account")
        if is_manager and _other_active_managers(db, account_id) == 0:
            raise HTTPException(status_code=409, detail="At least one active Administrator or Manager must remain")
    if payload.is_active is not None:
        account.is_active = payload.is_active

    db.commit()
    db.refresh(account)
    return _out(account)


@router.post("/{account_id}/reset-password", status_code=204)
def reset_password(
    account_id: int,
    payload: schemas.PasswordReset,
    db: Session = Depends(get_db),
    _: models.Account = Depends(require_manager),
):
    account = _get(db, account_id)
    account.password_hash = hash_password(payload.new_password)
    db.commit()
