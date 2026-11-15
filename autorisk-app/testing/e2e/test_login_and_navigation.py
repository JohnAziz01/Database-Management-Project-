"""
E2E tests: signing in, signing out, route guards, and the dashboard.

Playwright basics used here:
  page.goto(url)                    open a page
  page.locator(css) / get_by_role   find elements (prefer roles & visible text:
                                    that's how users find things too)
  expect(locator).to_have_text(...) assertions that WAIT and retry until the
                                    UI catches up (up to 5 s) -- never use
                                    time.sleep() in UI tests.
"""
import pytest
from playwright.sync_api import expect

from support.ui import login_as

pytestmark = pytest.mark.e2e


def kpi(page, label):
    return page.locator(".kpi-card", has_text=label).locator(".kpi-value")


def test_login_page_renders(page, base_url):
    page.goto(f"{base_url}/login")
    expect(page.get_by_role("heading", name="Sign in")).to_be_visible()
    expect(page.locator("#login-email")).to_be_visible()


def test_successful_login_shows_dashboard(page, base_url):
    login_as(page, base_url)
    expect(page.get_by_role("heading", name="Executive Dashboard")).to_be_visible()
    expect(page.locator(".sidebar-user")).to_have_text("admin@autorisk.demo")


def test_dashboard_shows_live_kpis(logged_in_page):
    page = logged_in_page
    expect(kpi(page, "Active Policies")).to_have_text("2")
    expect(kpi(page, "Total Premium Written")).to_have_text("$1315.50")
    expect(kpi(page, "Open Claims")).to_have_text("1")
    expect(kpi(page, "Policyholders")).to_have_text("3")


def test_wrong_password_shows_error_and_stays_on_login(page, base_url):
    page.goto(f"{base_url}/login")
    page.locator("#login-email").fill("admin@autorisk.demo")
    page.locator("#login-password").fill("wrong")
    page.get_by_role("button", name="Sign in").click()
    expect(page.locator(".form-error")).to_have_text("Invalid email or password")
    expect(page).to_have_url(f"{base_url}/login")


def test_protected_page_redirects_to_login(page, base_url):
    page.goto(f"{base_url}/claims")
    expect(page).to_have_url(f"{base_url}/login")


def test_after_login_user_returns_to_the_page_they_wanted(page, base_url):
    page.goto(f"{base_url}/claims")           # bounced to /login
    page.locator("#login-email").fill("admin@autorisk.demo")
    page.locator("#login-password").fill("admin123")
    page.get_by_role("button", name="Sign in").click()
    expect(page).to_have_url(f"{base_url}/claims")


def test_sign_out(logged_in_page, base_url):
    page = logged_in_page
    page.get_by_role("button", name="Sign out").click()
    expect(page).to_have_url(f"{base_url}/login")
    page.goto(f"{base_url}/dashboard")         # can't go back in after signing out
    expect(page).to_have_url(f"{base_url}/login")


def test_session_survives_page_reload(logged_in_page):
    logged_in_page.reload()
    expect(logged_in_page.get_by_role("heading", name="Executive Dashboard")).to_be_visible()


@pytest.mark.parametrize(
    "link, heading",
    [("Policies", "Policies"), ("Vehicles", "Vehicles"), ("Claims", "Claims"),
     ("Coverage", "Coverage"), ("Regions", "Regions"), ("New Quote", "New Insurance Quote")],
)
def test_sidebar_navigation(logged_in_page, link, heading):
    page = logged_in_page
    page.locator("nav").get_by_role("link", name=link, exact=True).click()
    expect(page.locator(".app-topbar h1")).to_have_text(heading)


# Regression test for BUG-018 (fixed): server validation errors are shown to the user as '[object Object]'
def test_invalid_email_on_login_shows_readable_error(page, base_url):
    page.goto(f"{base_url}/login")
    page.locator("#login-email").fill("not-an-email")
    page.locator("#login-password").fill("x")
    page.get_by_role("button", name="Sign in").click()
    error = page.locator(".form-error")
    expect(error).to_be_visible()
    expect(error).not_to_contain_text("[object Object]", timeout=1000)
    expect(error).to_contain_text("valid email")


def test_expired_session_sends_user_back_to_login(logged_in_page, base_url):
    # BUG-024 fix: if the saved token stops working, the app signs the user
    # out instead of showing pages that can't load any data.
    page = logged_in_page
    page.evaluate("localStorage.setItem('autorisk_token', 'expired.or.forged')")
    page.goto(f"{base_url}/policyholders")
    expect(page).to_have_url(f"{base_url}/login")


def test_customer_sees_only_their_own_policyholder_record(page, base_url):
    # BUG-002 fix, seen from the UI
    login_as(page, base_url, "jordan.reyes@example.com", "demo1234")
    page.goto(f"{base_url}/policyholders")
    rows = page.locator("table.data-table tbody tr")
    expect(rows.first).to_contain_text("Jordan Reyes")
    expect(rows).to_have_count(1)
