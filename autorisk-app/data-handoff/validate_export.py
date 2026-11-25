"""Validate exports and team seed against an in-memory SQLite translation of the DDL."""
import argparse
import csv
from decimal import Decimal
from pathlib import Path
import re
import sqlite3
import zipfile

TABLES = ("region", "policyholder", "vehicle", "policy", "policy_coverage",
          "claim", "claim_payment", "rate_table")


def validate(archive, directory):
    with zipfile.ZipFile(archive) as repo:
        schema, seed = [
            repo.read(next(n for n in repo.namelist() if n.endswith(f"/db/{file}.sql"))).decode()
            for file in ("schema", "seed")
        ]
    db = sqlite3.connect(":memory:")
    db.execute("PRAGMA foreign_keys = ON")
    schema = re.sub(r"^DROP TABLE.*$", "", schema, flags=re.MULTILINE)
    schema = schema.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY").replace("DEFAULT now()", "DEFAULT CURRENT_TIMESTAMP")
    db.executescript(schema)
    db.executescript(seed)
    [(liability_id,)] = db.execute("SELECT coverage_id FROM coverage WHERE coverage_name = 'Liability'")
    counts = {}
    payment_total = Decimal(0)
    for table in TABLES:
        with (directory / f"{table}.csv").open(encoding="utf-8", newline="") as stream:
            reader = csv.reader(stream)
            columns = next(reader)
            if table in ("policy_coverage", "rate_table"):
                columns.append("coverage_id")
            placeholders = ", ".join("?" for _ in columns)
            insert = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
            count = 0
            for row in reader:
                assert int(row[0]) < 0
                if table in ("policy_coverage", "rate_table"):
                    row.append(liability_id)
                if table == "claim_payment":
                    amount = Decimal(row[3])
                    assert 0 < amount < 100_000_000 and amount == amount.quantize(Decimal(".01"))
                    payment_total += amount
                db.execute(insert, [None if x == "" else x for x in row])
                count += 1
            counts[table] = count
    assert counts["policyholder"] == counts["vehicle"] == counts["policy"] == counts["policy_coverage"]
    assert counts["claim"] == counts["claim_payment"]
    assert not db.execute("PRAGMA foreign_key_check").fetchall()
    for query in (
        "SELECT 1 FROM policy p JOIN vehicle v USING (vehicle_id) WHERE p.policy_id < 0 AND p.policyholder_id <> v.policyholder_id",
        "SELECT 1 FROM claim c JOIN policy p USING (policy_id) WHERE c.claim_id < 0 AND (claim_date < start_date OR claim_date >= end_date)",
        "SELECT 1 FROM claim_payment x JOIN claim c USING (claim_id) WHERE c.claim_id < 0 AND (payment_date < claim_date OR x.status <> 'Paid' OR c.status <> 'Paid')",
        "SELECT 1 FROM policy p JOIN policy_coverage pc USING (policy_id) WHERE p.policy_id < 0 AND p.total_premium <> pc.coverage_premium",
        "SELECT 1 FROM region r WHERE r.parent_region_id = -1 AND NOT EXISTS (SELECT 1 FROM rate_table t WHERE t.region_id = r.region_id AND t.coverage_id = ? AND t.effective_date <= '2026-11-15' AND (t.expiry_date IS NULL OR t.expiry_date > '2026-11-15'))",
    ):
        assert db.execute(query, (liability_id,) if "?" in query else ()).fetchone() is None
    assert db.execute("SELECT count(*) FROM policy WHERE status = 'Active'").fetchone() == (2,)
    assert db.execute("SELECT count(*) FROM account").fetchone() == (2,)
    print(f"{directory.name}: {counts}; imported payments {payment_total:,.2f}; checks passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("team_zip", type=Path)
    parser.add_argument("exports", type=Path, nargs="+")
    args = parser.parse_args()
    for directory in args.exports:
        validate(args.team_zip, directory)
