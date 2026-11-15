"""
Fixtures for API tests.

A *fixture* is a function pytest runs for you before a test, injecting its
return value when a test names it as a parameter. E.g. a test written as
`def test_x(client, admin_headers):` automatically gets a ready HTTP client
and a valid admin Authorization header.

These tests use FastAPI's TestClient: it calls the app in-process (no
server to start), but goes through the full HTTP stack (routing,
validation, auth, database), so it behaves like a real client.
"""
import pytest
from fastapi.testclient import TestClient

from support import ADMIN_EMAIL, ADMIN_PASSWORD, CUSTOMER_EMAIL, CUSTOMER_PASSWORD
from support.db import reset_database, get_test_database_url


@pytest.fixture(scope="session")
def app():
    get_test_database_url()  # fail fast (and safely) if the test DB isn't configured
    from app.main import app as fastapi_app  # imported late, after DATABASE_URL points at the test DB
    return fastapi_app


@pytest.fixture(scope="session")
def anon_client(app):
    """A client with NO login token: what an anonymous visitor (or attacker) sends."""
    # raise_server_exceptions=False: an unhandled server error comes back
    # as an HTTP 500 response (what a real client sees) instead of a Python
    # exception inside the test.
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="session")
def client(app):
    """A client logged in as the ADMIN. Most tests use this one.

    Since BUG-001 was fixed every data endpoint needs a token, so this client
    sends the admin's token on every request. A test can still override it
    per request, e.g. client.get(url, headers=customer_headers).
    """
    reset_database()
    with TestClient(app, raise_server_exceptions=False) as c:
        c.headers["Authorization"] = _login(c, ADMIN_EMAIL, ADMIN_PASSWORD)["Authorization"]
        yield c


@pytest.fixture(autouse=True)
def fresh_db(client):
    """autouse: runs before EVERY API test, so each starts from seed data."""
    from app.auth import reset_login_throttle

    reset_database()
    reset_login_throttle()  # failed-login counts (BUG-017) live in memory, not the DB


def _login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin_headers(anon_client):
    return _login(anon_client, ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture
def customer_headers(anon_client):
    return _login(anon_client, CUSTOMER_EMAIL, CUSTOMER_PASSWORD)


@pytest.fixture
def new_policyholder():
    """A valid policyholder payload; tests tweak one field to probe validation."""
    return {
        "first_name": "Taylor",
        "last_name": "Morgan",
        "date_of_birth": "1988-07-21",
        "license_number": "T5550001",
        "license_issue_date": "2006-08-01",
        "email": "taylor.morgan@example.com",
        "phone": "555-0199",
        "region_id": 2,
        "risk_tier": "Low",
    }
