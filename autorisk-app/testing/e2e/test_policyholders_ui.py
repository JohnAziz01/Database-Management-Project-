"""E2E tests: the Policyholders page (live search, region filter, add form)."""
import pytest
from playwright.sync_api import expect

from support.db import run_sql
from support.ui import field

pytestmark = pytest.mark.e2e


@pytest.fixture
def ph_page(logged_in_page, base_url):
    page = logged_in_page
    page.goto(f"{base_url}/policyholders")
    expect(rows(page)).to_have_count(3)
    return page


def rows(page):
    return page.locator("table.data-table tbody tr")


def open_add_form_and_fill(page, **overrides):
    values = {
        "First Name": "Taylor", "Last Name": "Morgan", "Date of Birth": "1988-07-21",
        "License Number": "T5550001", "License Issue Date": "2006-08-01",
        "Email": "taylor.morgan@example.com", **overrides,
    }
    page.get_by_role("button", name="Add Policyholder").click()
    modal = page.locator(".modal-box")
    for label, value in values.items():
        field(modal, label).fill(value)
    return modal


def test_lists_seeded_policyholders(ph_page):
    expect(rows(ph_page).first).to_contain_text("PH-0001")
    expect(rows(ph_page).first).to_contain_text("Jordan Reyes")


def test_live_search(ph_page):
    ph_page.get_by_placeholder("Search name, email, or license…").fill("shah")
    expect(rows(ph_page)).to_have_count(1)
    expect(rows(ph_page)).to_contain_text("Priya Shah")


def test_search_with_no_results_shows_empty_state(ph_page):
    ph_page.get_by_placeholder("Search name, email, or license…").fill("zzzz")
    expect(ph_page.get_by_text("No policyholders match your filters.")).to_be_visible()


def test_region_filter(ph_page):
    ph_page.locator(".toolbar-filters select").select_option(label="Region B")
    expect(rows(ph_page)).to_have_count(1)
    expect(rows(ph_page)).to_contain_text("Casey Nguyen")


def test_add_policyholder(ph_page):
    modal = open_add_form_and_fill(ph_page)
    modal.get_by_role("button", name="Save Policyholder").click()
    expect(modal).to_be_hidden()
    expect(rows(ph_page)).to_have_count(4)
    expect(rows(ph_page).last).to_contain_text("Taylor Morgan")
    assert run_sql("SELECT count(*) FROM policyholder")[0][0] == 4


def test_add_form_cancel_saves_nothing(ph_page):
    modal = open_add_form_and_fill(ph_page)
    modal.get_by_role("button", name="Cancel").click()
    expect(modal).to_be_hidden()
    expect(rows(ph_page)).to_have_count(3)


def test_required_fields_block_submit(ph_page):
    ph_page.get_by_role("button", name="Add Policyholder").click()
    modal = ph_page.locator(".modal-box")
    modal.get_by_role("button", name="Save Policyholder").click()
    expect(modal).to_be_visible()  # browser's built-in "required" validation stops it
    assert run_sql("SELECT count(*) FROM policyholder")[0][0] == 3


def test_duplicate_email_shows_server_message(ph_page):
    modal = open_add_form_and_fill(ph_page, Email="jordan.reyes@example.com")
    modal.get_by_role("button", name="Save Policyholder").click()
    expect(modal.locator(".form-error")).to_have_text(
        "A policyholder with that email already exists"
    )


def test_script_in_name_is_shown_as_text_not_run(ph_page):
    # XSS check: if the app ran this, the page title would change.
    payload = "<img src=x onerror=\"document.title='HACKED'\">"
    modal = open_add_form_and_fill(ph_page, **{"First Name": payload})
    modal.get_by_role("button", name="Save Policyholder").click()
    expect(rows(ph_page).last).to_contain_text(payload)
    assert ph_page.title() != "HACKED"


# Regression test for BUG-003 (fixed): duplicate license number shows 'Internal Server Error'
def test_duplicate_license_shows_helpful_message(ph_page):
    modal = open_add_form_and_fill(ph_page, **{"License Number": "D1234567"})
    modal.get_by_role("button", name="Save Policyholder").click()
    expect(modal.locator(".form-error")).to_contain_text("license", ignore_case=True, timeout=3000)


# Regression test for BUG-019 (fixed): after adding a policyholder the list ignores the active region filter
def test_region_filter_still_applied_after_adding(ph_page):
    # Two traps the first drafts of this test fell into (each gave a false XPASS):
    #  1. The "Loading..." placeholder is ALSO a <tr>, so "1 row" was true while
    #     the page was still loading. Wait for actual content instead.
    #  2. The app closes the modal BEFORE re-fetching the list, so checking
    #     right after the click was too early. Wait for the network to go idle.
    ph_page.locator(".toolbar-filters select").select_option(label="Region B")
    expect(rows(ph_page)).to_have_count(1)
    expect(rows(ph_page)).to_contain_text("Casey Nguyen")   # filtered list really loaded
    modal = open_add_form_and_fill(ph_page)                 # new person is in no region
    modal.get_by_role("button", name="Save Policyholder").click()
    expect(modal).to_be_hidden()
    ph_page.wait_for_load_state("networkidle")              # the re-fetch has finished
    assert rows(ph_page).count() == 1, rows(ph_page).all_inner_texts()  # still only Region B


# Regression test for BUG-020 (fixed): form labels are not linked to their inputs (accessibility)
def test_add_form_fields_are_reachable_by_label(ph_page):
    ph_page.get_by_role("button", name="Add Policyholder").click()
    expect(ph_page.get_by_label("First Name")).to_be_visible(timeout=1000)
