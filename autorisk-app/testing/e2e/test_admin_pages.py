"""
E2E tests: the Rate Tables, Risk Analysis, Reports and Accounts pages.
"""
import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_rate_tables_lists_current_versions(logged_in_page, base_url):
    page = logged_in_page
    page.goto(f"{base_url}/rate-tables")
    rows = page.locator("table tbody tr")
    expect(rows).to_have_count(12)                 # 3 regions x 4 coverages, all current
    expect(rows.first).to_contain_text("Current")


def test_revise_publishes_a_scheduled_version(logged_in_page, base_url):
    page = logged_in_page
    page.goto(f"{base_url}/rate-tables")
    page.get_by_role("button", name="Revise").first.click()
    page.locator("#rt-base_rate").fill("475")
    page.get_by_role("button", name="Publish Version").click()
    expect(page.locator(".form-success")).to_contain_text("Published")
    page.get_by_label("Status").select_option("Scheduled")
    expect(page.locator("table tbody tr")).to_have_count(1)
    expect(page.locator("table tbody tr")).to_contain_text("$475.00")


def test_risk_analysis_switches_dimension(logged_in_page, base_url):
    page = logged_in_page
    page.goto(f"{base_url}/risk-analysis")
    expect(page.get_by_role("heading", name="Claim experience by driver age")).to_be_visible()
    page.get_by_role("tab", name="Bonus-malus").click()
    expect(page.get_by_role("heading", name="Claim experience by bonus-malus")).to_be_visible()
    expect(page.locator("table tbody")).to_contain_text("Bonus (< 1.00)")


def test_reports_preview_and_download(logged_in_page, base_url):
    page = logged_in_page
    page.goto(f"{base_url}/reports")
    page.get_by_role("button", name="Policy register").click()
    expect(page.locator(".report-view .subtitle")).to_contain_text("3 rows")
    with page.expect_download() as info:
        page.get_by_role("button", name="Download CSV").click()
    assert info.value.suggested_filename.startswith("autorisk-policy-register-")


def test_accounts_create_analyst(logged_in_page, base_url):
    page = logged_in_page
    page.goto(f"{base_url}/users")
    expect(page.locator("table tbody tr")).to_have_count(2)
    page.get_by_role("button", name="Add Account").click()
    page.locator("#acc-role").select_option("Analyst")
    page.locator("#acc-email").fill("new.analyst@autorisk.demo")
    page.locator("#acc-password").fill("analyst123")
    page.get_by_role("button", name="Create Account").click()
    expect(page.locator(".form-success")).to_contain_text("Created new.analyst@autorisk.demo")
    expect(page.locator("table tbody tr")).to_have_count(3)
