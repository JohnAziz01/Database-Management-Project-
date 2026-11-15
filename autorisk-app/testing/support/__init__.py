"""Shared helpers for the AutoRisk test suite."""
import pytest


def known_bug(bug_id: str, summary: str):
    """Mark a test as documenting an open bug from docs/BUG_REPORTS.md.

    The test asserts the CORRECT behaviour, so today it fails and pytest
    reports it as "xfail" (expected failure) instead of breaking the run.
    Because xfail_strict is on, once someone fixes the bug the test passes,
    pytest reports XPASS as a failure, and that reminds you to remove this
    marker and close the bug.

    raises=AssertionError: only a failed *assertion* counts as "the bug is
    still there". If the test crashes for some other reason (server didn't
    start, typo in a selector...) it is reported as a real error instead of
    being silently swallowed as an expected failure.
    """
    return pytest.mark.xfail(reason=f"{bug_id}: {summary}", strict=True, raises=AssertionError)


# Seed data facts (from db/seed.sql) that many tests rely on.
ADMIN_EMAIL = "admin@autorisk.demo"
ADMIN_PASSWORD = "admin123"
CUSTOMER_EMAIL = "jordan.reyes@example.com"
CUSTOMER_PASSWORD = "demo1234"
