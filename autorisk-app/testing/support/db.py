"""
Test-database helpers.

Every API and E2E test starts from the same known state: the tables are
emptied and db/seed.sql is re-loaded. That makes tests independent of each
other (test order never matters) and repeatable (running the suite twice
gives the same result).

The first reset in a test run also re-creates the tables from
db/schema.sql, so schema changes are always picked up.
"""
import os
import time
from pathlib import Path

import psycopg2
from psycopg2 import errors as pg_errors
from dotenv import dotenv_values

APP_ROOT = Path(__file__).resolve().parents[2]  # .../autorisk-app
DB_DIR = APP_ROOT / "db"
SCHEMA_SQL = (DB_DIR / "schema.sql").read_text(encoding="utf-8")
SEED_SQL = (DB_DIR / "seed.sql").read_text(encoding="utf-8")


def _plain_url(url: str) -> str:
    # SQLAlchemy URLs ("postgresql+psycopg2://") aren't understood by psycopg2.
    return url.replace("postgresql+psycopg2://", "postgresql://", 1)


def get_test_database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        raise RuntimeError(
            "TEST_DATABASE_URL is not set. Copy testing/.env.test.example to "
            "testing/.env.test (or just run testing/run_tests.ps1)."
        )
    real_url = dotenv_values(APP_ROOT / "backend" / ".env").get("DATABASE_URL")
    if real_url and _plain_url(real_url) == _plain_url(url):
        raise RuntimeError(
            "TEST_DATABASE_URL is the same database as backend/.env. The tests "
            "wipe their database, so they refuse to run against your real data."
        )
    return url


TABLES = [
    "claim_payment", "claim", "policy_coverage", "policy", "rate_table",
    "account", "vehicle", "policyholder", "coverage", "region",
]
_schema_created = False


def reset_database() -> None:
    """Empty every table and reload the seed data.

    Lesson learned (a flaky-test bug in this suite): a browser test can end
    while its last API request is still running on the server. Dropping
    tables under that request DEADLOCKED in about 1 run out of 4, the reset
    was cancelled, and the next tests started from the wrong data. So:
      * TRUNCATE instead of DROP + CREATE (one statement, fewer locks), and
      * on a deadlock / lock timeout, wait a moment and retry.
    """
    global _schema_created
    url = _plain_url(get_test_database_url())
    for attempt in range(1, 6):
        conn = psycopg2.connect(url)
        try:
            with conn, conn.cursor() as cur:
                cur.execute("SET lock_timeout = '5s'")
                if not _schema_created:
                    cur.execute(SCHEMA_SQL)
                else:
                    cur.execute(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE")
                cur.execute(SEED_SQL)
            _schema_created = True
            return
        except (pg_errors.DeadlockDetected, pg_errors.LockNotAvailable):
            if attempt == 5:
                raise
            time.sleep(0.5 * attempt)
        finally:
            conn.close()


def run_sql(sql: str, params=None):
    """Run one SQL statement against the test DB; return rows if it has any.

    Tests use this to set up states the API can't create yet (e.g. disabling
    an account) and to check what actually landed in the database.
    """
    conn = psycopg2.connect(_plain_url(get_test_database_url()))
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall() if cur.description else None
    finally:
        conn.close()
