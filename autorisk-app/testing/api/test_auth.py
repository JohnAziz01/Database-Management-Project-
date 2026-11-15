"""
API tests: authentication (POST /api/auth/login, GET /api/auth/me).

Each test follows Arrange -> Act -> Assert:
  Arrange: set up data / state       (fixtures usually do this)
  Act:     make exactly one request
  Assert:  check status code AND body (a 200 with the wrong data is still a bug)
"""
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from support import ADMIN_EMAIL, ADMIN_PASSWORD, CUSTOMER_EMAIL, CUSTOMER_PASSWORD
from support.db import run_sql

pytestmark = [pytest.mark.api, pytest.mark.security]


def login(anon_client, email, password):
    return anon_client.post("/api/auth/login", json={"email": email, "password": password})


# ------------------------------------------------------------- happy paths
def test_admin_can_log_in(anon_client):
    r = login(anon_client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["account_type"] == "Admin"
    assert body["email"] == ADMIN_EMAIL
    assert len(body["access_token"]) > 20


def test_customer_can_log_in(anon_client):
    r = login(anon_client, CUSTOMER_EMAIL, CUSTOMER_PASSWORD)
    assert r.status_code == 200
    assert r.json()["account_type"] == "Customer"


def test_login_records_last_login_time(anon_client):
    login(anon_client, ADMIN_EMAIL, ADMIN_PASSWORD)
    [(last_login,)] = run_sql("SELECT last_login_at FROM account WHERE email = %s", (ADMIN_EMAIL,))
    assert last_login is not None


def test_me_returns_the_logged_in_account(anon_client, admin_headers):
    r = anon_client.get("/api/auth/me", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["email"] == ADMIN_EMAIL


# ------------------------------------------------------------ negative paths
def test_wrong_password_is_rejected(anon_client):
    r = login(anon_client, ADMIN_EMAIL, "wrong-password")
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid email or password"


def test_unknown_email_gives_same_message_as_wrong_password(anon_client):
    # Same message for both cases, so an attacker can't use the login form
    # to find out which emails have accounts ("user enumeration").
    unknown = login(anon_client, "nobody@example.com", "whatever")
    wrong_pw = login(anon_client, ADMIN_EMAIL, "whatever")
    assert unknown.status_code == wrong_pw.status_code == 401
    assert unknown.json() == wrong_pw.json()


def test_password_is_case_sensitive(anon_client):
    assert login(anon_client, ADMIN_EMAIL, ADMIN_PASSWORD.upper()).status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": "x"},
        {"email": ADMIN_EMAIL},                 # missing password
        {"password": ADMIN_PASSWORD},           # missing email
        {},
    ],
    ids=["bad-email-format", "no-password", "no-email", "empty-body"],
)
def test_malformed_login_requests_get_422(anon_client, payload):
    assert anon_client.post("/api/auth/login", json=payload).status_code == 422


def test_disabled_account_cannot_log_in(anon_client):
    run_sql("UPDATE account SET is_active = false WHERE email = %s", (ADMIN_EMAIL,))
    r = login(anon_client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert r.status_code == 403


def test_sql_injection_in_login_is_rejected(anon_client):
    r = login(anon_client, "admin@autorisk.demo' OR '1'='1", "' OR '1'='1")
    assert r.status_code in (401, 422)


# --------------------------------------------------------------- tokens
def test_me_without_token_is_401(anon_client):
    assert anon_client.get("/api/auth/me").status_code == 401


def test_me_with_garbage_token_is_401(anon_client):
    r = anon_client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert r.status_code == 401


def test_expired_token_is_rejected(anon_client):
    from app.auth import JWT_ALGORITHM, JWT_SECRET

    expired = jwt.encode(
        {"sub": "1", "email": ADMIN_EMAIL, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    r = anon_client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401


def test_token_signed_with_another_secret_is_rejected(anon_client):
    forged = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "attacker-secret",
        algorithm="HS256",
    )
    r = anon_client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


def test_token_stops_working_when_account_is_disabled(anon_client, admin_headers):
    run_sql("UPDATE account SET is_active = false WHERE email = %s", (ADMIN_EMAIL,))
    assert anon_client.get("/api/auth/me", headers=admin_headers).status_code == 401


# ---------------------------------------------------- throttling (BUG-017)
def test_repeated_failed_logins_are_throttled(anon_client):
    statuses = [login(anon_client, ADMIN_EMAIL, f"guess-{i}").status_code for i in range(6)]
    assert statuses == [401] * 5 + [429]   # 5 wrong guesses allowed, the 6th is blocked


def test_throttled_account_rejects_even_the_right_password(anon_client):
    for i in range(5):
        login(anon_client, ADMIN_EMAIL, f"guess-{i}")
    # Otherwise an attacker could keep guessing and simply ignore the 429s.
    assert login(anon_client, ADMIN_EMAIL, ADMIN_PASSWORD).status_code == 429


def test_throttling_is_per_email(anon_client):
    for i in range(5):
        login(anon_client, ADMIN_EMAIL, f"guess-{i}")
    assert login(anon_client, CUSTOMER_EMAIL, CUSTOMER_PASSWORD).status_code == 200


def test_successful_login_resets_the_failure_count(anon_client):
    for i in range(4):
        login(anon_client, ADMIN_EMAIL, f"guess-{i}")
    assert login(anon_client, ADMIN_EMAIL, ADMIN_PASSWORD).status_code == 200
    for i in range(4):  # 4 more mistakes are allowed again
        assert login(anon_client, ADMIN_EMAIL, f"again-{i}").status_code == 401


def test_login_email_is_case_insensitive(anon_client):
    assert login(anon_client, ADMIN_EMAIL.upper(), ADMIN_PASSWORD).status_code == 200
