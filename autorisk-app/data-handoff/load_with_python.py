"""
Run load.sql without psql -- for machines that don't have the PostgreSQL
client tools installed.

It executes load.sql statement by statement, unchanged, on ONE connection in
ONE transaction (the BEGIN/COMMIT in the file). The only translation is psql's
client-side `\\copy ... FROM 'file.csv'`, which becomes a server-side
`COPY ... FROM STDIN` fed from the CSV via psycopg2. Any error rolls the
whole import back, exactly like `psql -v ON_ERROR_STOP=1`.

Usage (from the autorisk-app folder):
    backend\\.venv\\Scripts\\python.exe data-handoff\\load_with_python.py data-handoff\\sample

The database is DATABASE_URL from backend\\.env (the one the app uses).
"""
import re
import sys
from pathlib import Path

import psycopg2

HERE = Path(__file__).resolve().parent
COPY_RE = re.compile(r"^\\copy\s+(.+?)\s+FROM\s+'([^']+)'\s+WITH\s+(\(.+\))\s*$", re.IGNORECASE)


def database_url() -> str:
    env = HERE.parent / "backend" / ".env"
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL="):
            url = line.split("=", 1)[1].strip().strip('"')
            return url.replace("postgresql+psycopg2://", "postgresql://", 1)
    sys.exit(f"DATABASE_URL not found in {env}")


def statements(sql: str):
    """load.sql separates every statement with a blank line."""
    for chunk in re.split(r"\n\s*\n", sql.replace("\r\n", "\n")):
        chunk = chunk.strip()
        if not chunk or chunk.startswith("\\set"):
            continue
        # The last chunk is "SELECT ...;\nCOMMIT;" -- split off the COMMIT.
        if chunk.endswith("COMMIT;") and chunk != "COMMIT;":
            yield chunk[: -len("COMMIT;")].strip()
            yield "COMMIT;"
        else:
            yield chunk


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    csv_dir = Path(sys.argv[1]).resolve()
    sql = (HERE / "load.sql").read_text(encoding="utf-8")

    conn = psycopg2.connect(database_url())
    conn.autocommit = True  # load.sql issues its own BEGIN / COMMIT
    cur = conn.cursor()
    try:
        for stmt in statements(sql):
            m = COPY_RE.match(stmt)
            if m:
                target, filename, options = m.groups()
                with open(csv_dir / filename, encoding="utf-8") as f:
                    cur.copy_expert(f"COPY {target} FROM STDIN WITH {options}", f)
                print(f"  copied {filename:<22} {cur.rowcount:>8} rows")
                continue
            cur.execute(stmt)
            if stmt.startswith("SELECT (SELECT count(*)"):
                policies, claims, paid = cur.fetchone()
                print(f"\nImported: {policies} policies, {claims} claims, payments total {paid}")
        print("Committed.")
    except Exception:
        if not conn.closed:
            cur.execute("ROLLBACK")
        print("\nImport FAILED -- rolled back, nothing was changed.", file=sys.stderr)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
