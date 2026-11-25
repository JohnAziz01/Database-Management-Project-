"""
/api/reports -- standard business reports, previewed as JSON or downloaded as CSV.

  GET /api/reports                       the report catalog
  GET /api/reports/{key}                 JSON preview: columns, first `limit` rows, total row count
  GET /api/reports/{key}/csv             every row, as a CSV file download

Each report is a fixed SQL query written here. The optional date_from /
date_to filters are passed as bound parameters, never pasted into SQL.
"""
import csv
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import clock
from ..auth import require_admin
from ..database import get_db

router = APIRouter(prefix="/api/reports", tags=["reports"], dependencies=[Depends(require_admin)])

_PAID = """
    SELECT c.policy_id, COUNT(DISTINCT c.claim_id) AS claims,
           COALESCE(SUM(cp.amount) FILTER (WHERE cp.status = 'Paid'), 0) AS paid
    FROM claim c LEFT JOIN claim_payment cp ON cp.claim_id = c.claim_id
    GROUP BY c.policy_id
"""

# key -> title, description, date column the filters apply to, SQL (with {where})
REPORTS = {
    "claims-register": {
        "title": "Claims register",
        "description": "Every claim with its policyholder, region, status and the amount paid so far.",
        "date_column": "c.claim_date",
        "sql": """
            SELECT c.claim_id, c.claim_date, c.claim_type, c.status, c.fault_percentage,
                   c.policy_id, ph.first_name || ' ' || ph.last_name AS policyholder,
                   COALESCE(r.name, '') AS region,
                   COUNT(cp.payment_seq) AS payments,
                   COALESCE(SUM(cp.amount) FILTER (WHERE cp.status = 'Paid'), 0) AS amount_paid
            FROM claim c
            JOIN policy p        ON p.policy_id = c.policy_id
            JOIN policyholder ph ON ph.policyholder_id = p.policyholder_id
            LEFT JOIN region r   ON r.region_id = ph.region_id
            LEFT JOIN claim_payment cp ON cp.claim_id = c.claim_id
            {where}
            GROUP BY c.claim_id, ph.first_name, ph.last_name, r.name
            ORDER BY c.claim_date DESC, c.claim_id
        """,
    },
    "payments-ledger": {
        "title": "Payments ledger",
        "description": "Every claim payment and installment, with its method and status.",
        "date_column": "cp.payment_date",
        "sql": """
            SELECT cp.claim_id, cp.payment_seq, cp.payment_date, cp.amount, cp.payment_method,
                   cp.status, c.policy_id, c.claim_type
            FROM claim_payment cp
            JOIN claim c ON c.claim_id = cp.claim_id
            {where}
            ORDER BY cp.payment_date DESC, cp.claim_id, cp.payment_seq
        """,
    },
    "policy-register": {
        "title": "Policy register",
        "description": "Every policy with its holder, vehicle, region, term, status and premium.",
        "date_column": "p.start_date",
        "sql": """
            SELECT p.policy_id, p.status, p.start_date, p.end_date,
                   ph.first_name || ' ' || ph.last_name AS policyholder,
                   v.make || ' ' || v.model AS vehicle, v.engine_power_kw,
                   COALESCE(r.name, '') AS region,
                   p.bonus_malus_coefficient, p.total_premium
            FROM policy p
            JOIN policyholder ph ON ph.policyholder_id = p.policyholder_id
            JOIN vehicle v       ON v.vehicle_id = p.vehicle_id
            LEFT JOIN region r   ON r.region_id = ph.region_id
            {where}
            ORDER BY p.start_date DESC, p.policy_id
        """,
    },
    "region-summary": {
        "title": "Premium & claims by region",
        "description": "Policies, premium, claims, amount paid and loss ratio for each region.",
        "date_column": "p.start_date",
        "sql": f"""
            WITH paid AS ({_PAID})
            SELECT COALESCE(r.name, 'No region') AS region,
                   COUNT(*) AS policies,
                   SUM(p.total_premium) AS premium,
                   COALESCE(SUM(paid.claims), 0) AS claims,
                   COALESCE(SUM(paid.paid), 0) AS amount_paid,
                   ROUND(COALESCE(SUM(paid.paid), 0) / NULLIF(SUM(p.total_premium), 0), 4) AS loss_ratio
            FROM policy p
            JOIN policyholder ph ON ph.policyholder_id = p.policyholder_id
            LEFT JOIN region r   ON r.region_id = ph.region_id
            LEFT JOIN paid       ON paid.policy_id = p.policy_id
            {{where}}
            GROUP BY r.name
            ORDER BY amount_paid DESC, region
        """,
    },
    "coverage-mix": {
        "title": "Coverage mix",
        "description": "How many policies carry each coverage, with average limit, deductible and premium.",
        "date_column": "p.start_date",
        "sql": """
            SELECT cv.coverage_name,
                   COUNT(pc.policy_id) AS policies,
                   COALESCE(SUM(pc.coverage_premium), 0) AS total_premium,
                   ROUND(AVG(pc.coverage_premium), 2) AS avg_premium,
                   ROUND(AVG(pc.coverage_limit), 2) AS avg_limit,
                   ROUND(AVG(pc.deductible), 2) AS avg_deductible
            FROM coverage cv
            LEFT JOIN (
                SELECT pc.* FROM policy_coverage pc
                JOIN policy p ON p.policy_id = pc.policy_id
                {where}
            ) pc ON pc.coverage_id = cv.coverage_id
            GROUP BY cv.coverage_name
            ORDER BY policies DESC, cv.coverage_name
        """,
    },
}


def _query(key: str, date_from: Optional[date], date_to: Optional[date]):
    report = REPORTS.get(key)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must be on or before date_to")
    col, conditions, params = report["date_column"], [], {}
    if date_from:
        conditions.append(f"{col} >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conditions.append(f"{col} <= :date_to")
        params["date_to"] = date_to
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return report, report["sql"].format(where=where), params


def _cell(value):
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "is_finite"):  # Decimal
        return float(value)
    return value


@router.get("")
def list_reports():
    return [{"key": k, "title": r["title"], "description": r["description"]} for k, r in REPORTS.items()]


@router.get("/{key}")
def preview_report(
    key: str,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    report, sql, params = _query(key, date_from, date_to)
    total = db.execute(text(f"SELECT COUNT(*) FROM ({sql}) t"), params).scalar()
    result = db.execute(text(f"{sql} LIMIT :limit"), {**params, "limit": limit})
    return {
        "key": key,
        "title": report["title"],
        "description": report["description"],
        "columns": list(result.keys()),
        "rows": [[_cell(v) for v in row] for row in result],
        "total_rows": total,
    }


@router.get("/{key}/csv")
def download_report(
    key: str,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
):
    _, sql, params = _query(key, date_from, date_to)
    result = db.execute(text(sql), params)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(list(result.keys()))
    for row in result:
        writer.writerow([_cell(v) for v in row])
    filename = f"autorisk-{key}-{clock.today().isoformat()}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
