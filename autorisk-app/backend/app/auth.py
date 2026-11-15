"""
Minimal auth helpers: password hashing + JWT (JSON Web Token) issuing.

Flow: POST /api/auth/login with email+password -> we verify the hash ->
we hand back a signed token -> React stores it (in memory / localStorage)
and sends it as `Authorization: Bearer <token>` on future requests ->
`get_current_account` below decodes it to know who's asking.

Security fixes after testing (see testing/docs/BUG_REPORTS.md):
  BUG-024  no hard-coded fallback secret: the app refuses to start without one
  BUG-017  repeated failed logins for one email are throttled (HTTP 429)
  BUG-002  require_admin / customer_scope enforce what each role may see
"""
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from . import models
from .database import get_db

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    # BUG-024: a default secret written in the source code would let anyone
    # who has read the code forge an admin token.
    raise RuntimeError("JWT_SECRET is not set. Add it to backend/.env (see .env.example).")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(account_id: int, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(account_id), "email": email, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# Login throttling (BUG-017)
# After MAX_FAILED_LOGINS wrong passwords for one email within the window,
# further attempts get 429 until the window passes. Kept in memory: fine for
# a single-server class project (a real deployment would use Redis or the DB).
# ---------------------------------------------------------------------------
MAX_FAILED_LOGINS = 5
FAILED_LOGIN_WINDOW_SECONDS = 15 * 60
_failed_logins: dict[str, deque] = defaultdict(deque)
_failed_lock = threading.Lock()


def _recent_failures(email: str) -> deque:
    attempts = _failed_logins[email]
    cutoff = time.monotonic() - FAILED_LOGIN_WINDOW_SECONDS
    while attempts and attempts[0] < cutoff:
        attempts.popleft()
    return attempts


def check_login_allowed(email: str) -> None:
    with _failed_lock:
        if len(_recent_failures(email)) >= MAX_FAILED_LOGINS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed sign-in attempts. Try again in 15 minutes.",
            )


def record_failed_login(email: str) -> None:
    with _failed_lock:
        _recent_failures(email).append(time.monotonic())


def clear_failed_logins(email: str) -> None:
    with _failed_lock:
        _failed_logins.pop(email, None)


def reset_login_throttle() -> None:
    """Forget all failed attempts (used by the automated tests between tests)."""
    with _failed_lock:
        _failed_logins.clear()


# ---------------------------------------------------------------------------
# Who is asking? (authentication)
# ---------------------------------------------------------------------------
def get_current_account(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.Account:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise unauthorized
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        account_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise unauthorized

    account = db.get(models.Account, account_id)
    if account is None or not account.is_active:
        raise unauthorized
    return account


# ---------------------------------------------------------------------------
# What may they do? (authorization, BUG-002)
#   Admin    -> everything
#   Customer -> only their own policyholder record, vehicles, policies, claims
# ---------------------------------------------------------------------------
def require_admin(account: models.Account = Depends(get_current_account)) -> models.Account:
    if account.account_type != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return account


def customer_scope(account: models.Account = Depends(get_current_account)) -> Optional[int]:
    """None for admins (no restriction); the customer's own policyholder_id otherwise."""
    return None if account.account_type == "Admin" else account.policyholder_id
