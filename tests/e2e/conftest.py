"""
Playwright E2E test fixtures and helpers.

Provides:
- Browser configuration
- Authentication helpers
- Test data fixtures
- Page object models
"""

import pytest
from playwright.sync_api import Page, expect
from typing import Generator
import os


# ============================================================================
# Configuration
# ============================================================================

# Streamlit app URL (default: localhost:8501)
STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")

# Test credentials (from environment or defaults)
ADMIN_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "admin@lfa.com")
ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "admin123")

# Use admin credentials for E2E tests (admin can access all dashboards)
INSTRUCTOR_EMAIL = os.getenv("TEST_INSTRUCTOR_EMAIL", "admin@lfa.com")
INSTRUCTOR_PASSWORD = os.getenv("TEST_INSTRUCTOR_PASSWORD", "admin123")

STUDENT_EMAIL = os.getenv("TEST_STUDENT_EMAIL", "student@lfa.com")
STUDENT_PASSWORD = os.getenv("TEST_STUDENT_PASSWORD", "student123")


# ============================================================================
# Pytest-Playwright Configuration
# ============================================================================

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """
    Configure browser context for all tests.

    Sets viewport size, timezone, and other browser options.
    """
    return {
        **browser_context_args,
        "viewport": {
            "width": 1920,
            "height": 1080,
        },
        "locale": "en-US",
        "timezone_id": "America/New_York",
    }


@pytest.fixture(scope="function")
def context(context):
    """
    Provide isolated browser context for each test.

    Tracing is configured via pytest-playwright plugin.
    """
    yield context


# ============================================================================
# Authentication Helpers
# ============================================================================

def login_as_instructor(page: Page) -> None:
    """
    Login to Streamlit app as instructor user.

    Args:
        page: Playwright Page object

    Note:
        Assumes login form has fields with st.text_input keys:
        - 'email' or 'Email'
        - 'password' or 'Password'
        And a login button with text 'Login' or 'Log In'
    """
    page.goto(STREAMLIT_URL)

    # Wait for app to load
    page.wait_for_selector("text=Login", timeout=10000)

    # Fill login form using aria-label (most reliable)
    # Based on debug test: Email has aria-label="Email", Password has aria-label="Password"
    page.fill("input[aria-label='Email']", INSTRUCTOR_EMAIL)
    page.fill("input[aria-label='Password']", INSTRUCTOR_PASSWORD)

    # Click login button (has text "🔐 Login")
    page.click("button:has-text('Login')")

    # Wait for successful login - look for any dashboard indicator
    # Try multiple possible selectors
    try:
        page.wait_for_selector("text=Dashboard", timeout=10000)
    except:
        try:
            page.wait_for_selector("text=Admin", timeout=5000)
        except:
            # If neither found, just wait a bit for page to load
            page.wait_for_timeout(3000)

    # Wait for sidebar to be fully loaded
    page.wait_for_timeout(2000)


def login_as_admin(page: Page) -> None:
    """Login to Streamlit app as admin user."""
    page.goto(STREAMLIT_URL)
    page.wait_for_selector("text=Login", timeout=10000)

    # Fill login form using aria-label
    page.fill("input[aria-label='Email']", ADMIN_EMAIL)
    page.fill("input[aria-label='Password']", ADMIN_PASSWORD)

    # Click login button
    page.click("button:has-text('Login')")

    # Wait for successful login
    try:
        page.wait_for_selector("text=Dashboard", timeout=10000)
    except:
        try:
            page.wait_for_selector("text=Admin", timeout=5000)
        except:
            page.wait_for_timeout(3000)


def login_as_student(page: Page) -> None:
    """Login to Streamlit app as student user."""
    page.goto(STREAMLIT_URL)
    page.wait_for_selector("text=Login", timeout=10000)

    # Fill login form using aria-label
    page.fill("input[aria-label='Email']", STUDENT_EMAIL)
    page.fill("input[aria-label='Password']", STUDENT_PASSWORD)

    # Click login button
    page.click("button:has-text('Login')")

    # Wait for successful login
    try:
        page.wait_for_selector("text=Dashboard", timeout=10000)
    except:
        try:
            page.wait_for_selector("text=Student", timeout=5000)
        except:
            page.wait_for_timeout(3000)


# ============================================================================
# Authenticated Page Fixtures
# ============================================================================

@pytest.fixture
def instructor_page(page: Page) -> Generator[Page, None, None]:
    """
    Provide authenticated instructor page.

    Usage:
        def test_something(instructor_page):
            instructor_page.goto(STREAMLIT_URL + "/some-page")
            # Already logged in as instructor
    """
    login_as_instructor(page)
    yield page


@pytest.fixture
def admin_page(page: Page) -> Generator[Page, None, None]:
    """Provide authenticated admin page."""
    login_as_admin(page)
    yield page


@pytest.fixture
def student_page(page: Page) -> Generator[Page, None, None]:
    """Provide authenticated student page."""
    login_as_student(page)
    yield page


# ============================================================================
# Navigation Helpers
# ============================================================================

def navigate_to_tournament_checkin(page: Page) -> None:
    """
    Navigate to Tournament Check-in page.

    Args:
        page: Authenticated page (logged in as admin)

    Navigation path:
        1. Click "Instructor Dashboard" in sidebar
        2. Click "✅ Check-in & Groups" tab (4th tab, index 3)
        3. Click "🏆 Tournament Sessions (2 statuses)" sub-tab
    """
    # Step 1: Navigate to Instructor Dashboard
    # Use direct URL navigation (more reliable than clicking sidebar link)
    page.goto(f"{STREAMLIT_URL}/Instructor_Dashboard")
    page.wait_for_timeout(2000)

    # Step 2: Click "✅ Check-in & Groups" main tab
    # Use tab button selector - Streamlit renders tabs as buttons
    # Click the 4th tab (index 3)
    tabs = page.locator("[data-testid='stTabs']").first.locator("button")
    if tabs.count() >= 4:
        tabs.nth(3).click()  # 4th tab = "✅ Check-in & Groups"
    else:
        # Fallback: try clicking by text
        page.click("text=Check-in")

    page.wait_for_timeout(1500)

    # Step 3: Click "🏆 Tournament Sessions (2 statuses)" sub-tab
    # This is the 2nd sub-tab (index 1)
    sub_tabs = page.locator("[data-testid='stTabs']").nth(1).locator("button")
    if sub_tabs.count() >= 2:
        sub_tabs.nth(1).click()  # 2nd sub-tab = "🏆 Tournament Sessions"
    else:
        # Fallback: try clicking by text
        page.click("text=Tournament Sessions")

    page.wait_for_timeout(2000)


def navigate_to_session_checkin(page: Page) -> None:
    """
    Navigate to Regular Session Check-in page.

    Args:
        page: Authenticated page (logged in as admin)

    Navigation path:
        1. Click "Instructor Dashboard" in sidebar
        2. Click "✅ Check-in & Groups" tab (4th tab, index 3)
        3. Click "✅ Regular Sessions (4 statuses)" sub-tab (1st sub-tab, index 0)
    """
    # Step 1: Navigate to Instructor Dashboard
    # Use direct URL navigation (more reliable than clicking sidebar link)
    page.goto(f"{STREAMLIT_URL}/Instructor_Dashboard")
    page.wait_for_timeout(2000)

    # Step 2: Click "✅ Check-in & Groups" main tab
    # Click the 4th tab (index 3)
    tabs = page.locator("[data-testid='stTabs']").first.locator("button")
    if tabs.count() >= 4:
        tabs.nth(3).click()  # 4th tab = "✅ Check-in & Groups"
    else:
        # Fallback: try clicking by text
        page.click("text=Check-in")

    page.wait_for_timeout(1500)

    # Step 3: Click "✅ Regular Sessions (4 statuses)" sub-tab
    # This is the 1st sub-tab (index 0) - DEFAULT, might already be selected
    sub_tabs = page.locator("[data-testid='stTabs']").nth(1).locator("button")
    if sub_tabs.count() >= 1:
        sub_tabs.nth(0).click()  # 1st sub-tab = "✅ Regular Sessions"
    else:
        # Fallback: try clicking by text
        page.click("text=Regular Sessions")

    page.wait_for_timeout(2000)


# ============================================================================
# Assertion Helpers
# ============================================================================

def assert_button_count(page: Page, label_substring: str, expected_count: int) -> None:
    """
    Assert that a specific number of buttons with label exist.

    Args:
        page: Playwright Page
        label_substring: Button label to search for (e.g., "Present", "Absent")
        expected_count: Expected number of buttons

    Example:
        assert_button_count(page, "Present", 2)
        # Asserts 2 buttons with "Present" in label
    """
    selector = f"button:has-text('{label_substring}')"
    actual_count = page.locator(selector).count()

    assert actual_count == expected_count, \
        f"Expected {expected_count} '{label_substring}' buttons, found {actual_count}"


def assert_no_button_with_label(page: Page, label_substring: str) -> None:
    """
    Assert that NO buttons with given label exist.

    Args:
        page: Playwright Page
        label_substring: Button label that should NOT exist
    """
    selector = f"button:has-text('{label_substring}')"
    actual_count = page.locator(selector).count()

    assert actual_count == 0, \
        f"Expected NO '{label_substring}' buttons, but found {actual_count}"


def assert_metric_visible(page: Page, label: str) -> None:
    """
    Assert that a metric with given label is visible.

    Args:
        page: Playwright Page
        label: Metric label (e.g., "Present", "Absent")
    """
    # Streamlit metrics have specific structure
    selector = f"[data-testid='stMetric']:has-text('{label}')"

    expect(page.locator(selector)).to_be_visible()


# ============================================================================
# Screenshot Helpers
# ============================================================================

def take_screenshot(page: Page, name: str) -> None:
    """
    Take screenshot and save to tests/screenshots/ folder.

    Args:
        page: Playwright Page
        name: Screenshot filename (without extension)
    """
    import pathlib

    screenshot_dir = pathlib.Path(__file__).parent.parent.parent / "docs" / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    screenshot_path = screenshot_dir / f"{name}.png"
    page.screenshot(path=str(screenshot_path), full_page=True)

    print(f"Screenshot saved: {screenshot_path}")
