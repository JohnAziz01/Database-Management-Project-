"""
Root pytest configuration: runs before any test module is imported.

1. Loads testing/.env.test.
2. Points the backend at the TEST database by setting DATABASE_URL before
   app.database is imported (the backend's load_dotenv() never overrides a
   variable that is already set).
3. Puts backend/ on sys.path so tests can `from app.main import app`.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

TESTING_DIR = Path(__file__).resolve().parent
APP_ROOT = TESTING_DIR.parent

load_dotenv(TESTING_DIR / ".env.test")
# Without a test DB, point the backend at a URL that cannot connect, so no
# test can ever reach the real database by accident.
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", "postgresql+psycopg2://no-test-db-configured@127.0.0.1:1/none"
)

sys.path.insert(0, str(APP_ROOT / "backend"))
