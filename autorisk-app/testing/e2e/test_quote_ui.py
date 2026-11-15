"""E2E tests: the New Quote page."""
import pytest
from playwright.sync_api import expect

from support.ui import field

pytestmark = pytest.mark.e2e


@pytest.fixture
def quote_page(logged_in_page, base_url):
    page = logged_in_page
    page.goto(f"{base_url}/quote")
    # wait until the dropdowns have loaded their options from the API
    # "Select..." + Regions A, B, C (the form now only lists regions that
    # have a current rate table -- BUG-009 fix -- so "National" is gone)
    expect(field(page, "Region").locator("option")).to_have_count(4)
    return page


def fill_quote(page, region="Region A", coverage="Liability", **overrides):
    values = {
        "Date of Birth": "1980-01-01", "License Issue Date": "2000-01-01",
        "Bonus-Malus Coefficient": "0.90", "Vehicle Manufacture Year": "2022",
        "Vehicle Power (kW)": "138", **overrides,
    }
    for label, value in values.items():
        field(page, label).fill(value)
    field(page, "Region").select_option(label=region)
    field(page, "Coverage").select_option(label=coverage)
    page.get_by_role("button", name="Calculate Quote").click()


def test_empty_state_before_calculating(quote_page):
    expect(quote_page.get_by_text("Fill in the form and calculate a quote.")).to_be_visible()


def test_calculates_premium(quote_page):
    fill_quote(quote_page)
    # same hand-calculated value as the unit and API tests: 491.16
    expect(quote_page.locator(".result-value")).to_have_text("$491.16 / year")
    expect(quote_page.locator(".metric-row", has_text="Risk Level")).to_contain_text("Low")


def test_region_changes_the_price(quote_page):
    fill_quote(quote_page, region="Region B")
    # Region B has its OWN power factor (1.04, not Region A's 1.05):
    # 380 * 1.04^2 * 0.95 * 0.90 = 351.41
    # (The first draft of this test assumed 1.05 and expected 358.19 -- the
    # app was right and the test's "oracle" was wrong.)
    expect(quote_page.locator(".result-value")).to_have_text("$351.41 / year")


def test_out_of_range_bonus_malus_blocked_by_browser(quote_page):
    fill_quote(quote_page, **{"Bonus-Malus Coefficient": "9"})  # field max is 3.5
    expect(quote_page.get_by_text("Fill in the form and calculate a quote.")).to_be_visible()


# Regression test for BUG-009 (fixed): choosing Collision (the first coverage listed) always fails
def test_collision_coverage_can_be_quoted(quote_page):
    fill_quote(quote_page, coverage="Collision")
    # 320 * 1.06^2 (138 kW) * 1.10 * 0.90 = 355.96
    expect(quote_page.locator(".result-value")).to_have_text("$355.96 / year")


def test_coverage_list_follows_the_chosen_region(quote_page):
    coverage = field(quote_page, "Coverage")
    expect(coverage).to_be_disabled()           # until a region is chosen
    field(quote_page, "Region").select_option(label="Region B")
    expect(coverage).to_be_enabled()
    expect(coverage.locator("option")).to_have_count(5)  # "Select..." + 4 coverages
