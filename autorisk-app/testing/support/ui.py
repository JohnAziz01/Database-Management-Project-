"""Page helpers shared by the E2E browser tests."""
from support import ADMIN_EMAIL, ADMIN_PASSWORD


def login_as(page, base_url, email=ADMIN_EMAIL, password=ADMIN_PASSWORD):
    page.goto(f"{base_url}/login")
    page.locator("#login-email").fill(email)
    page.locator("#login-password").fill(password)
    page.get_by_role("button", name="Sign in").click()
    page.wait_for_url("**/dashboard")


def field(page, label):
    """Find an input/select by the text of the label above it.

    The app's labels are not linked to their inputs (BUG-020), so the
    normal page.get_by_label() doesn't work; this finds the .form-group
    containing that label text instead.
    """
    # `page` may be the whole Page or a Locator (e.g. a modal). The `has=`
    # locator is evaluated *inside* each .form-group, so it must be a plain
    # root locator built from the Page, not from the modal.
    root = getattr(page, "page", page)
    label_loc = root.locator("label", has_text=label)
    return page.locator(".form-group", has=label_loc).locator("input, select").first
