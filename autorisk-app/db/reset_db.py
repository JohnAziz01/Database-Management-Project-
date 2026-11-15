"""
Rebuild the database from scratch: runs db/schema.sql then db/seed.sql
against the DATABASE_URL in backend/.env (works for Neon or local Postgres,
no psql needed).

WARNING: schema.sql DROPs every table first -- all existing data is lost.

Usually run through the launcher:  .\run.ps1 reset-db
"""
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "backend" / ".env")

url = os.getenv("DATABASE_URL")
if not url:
    sys.exit("DATABASE_URL is not set in backend/.env")

# SQLAlchemy-style URLs ("postgresql+psycopg2://") aren't understood by psycopg2.
url = url.replace("postgresql+psycopg2://", "postgresql://", 1)

conn = psycopg2.connect(url)
try:
    with conn, conn.cursor() as cur:
        for name in ("schema.sql", "seed.sql"):
            print(f"  running db/{name} ...")
            cur.execute((ROOT / "db" / name).read_text(encoding="utf-8"))
    print("  database reset complete.")
finally:
    conn.close()
