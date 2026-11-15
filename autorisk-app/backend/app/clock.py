"""
One clock for the whole app (fix for BUG-023).

Postgres (Neon and the test container) runs in UTC, so `created_at`,
`now()` and `CURRENT_DATE` are UTC. Python's date.today() uses the
*server's local* time zone instead, so in the evening (US time) the app and
the database disagreed about what day it was. Everything in the app that
needs "today" now calls clock.today(), which is UTC like the database.
"""
from datetime import date, datetime, timezone


def today() -> date:
    return datetime.now(timezone.utc).date()
