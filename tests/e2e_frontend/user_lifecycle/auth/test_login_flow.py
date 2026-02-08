"""
Simple login test to verify Streamlit UI login works
"""

import pytest
import time
from playwright.sync_api import Page

STREAMLIT_URL = "http://localhost:8501"
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"


@pytest.mark.e2e
def test_simple_admin_login(page: Page):
    """Test admin login through Streamlit UI"""

    print("\n🧪 Testing Admin Login...")

    # Navigate to login page
    page.goto(STREAMLIT_URL)
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    # Take screenshot before login
    page.screenshot(path="tests/e2e/screenshots/before_login.png")
    print("📸 Screenshot saved: before_login.png")

    # Fill login form
    email_input = page.locator('input[aria-label="Email"]')
    email_input.fill(ADMIN_EMAIL)
    time.sleep(0.5)

    password_input = page.locator('input[type="password"]')
    password_input.fill(ADMIN_PASSWORD)
    time.sleep(0.5)

    # Take screenshot with filled form
    page.screenshot(path="tests/e2e/screenshots/form_filled.png")
    print("📸 Screenshot saved: form_filled.png")

    # Click login button
    login_button = page.locator('button:has-text("🔐 Login")')
    login_button.click()

    # Wait for redirect
    page.wait_for_load_state("networkidle")
    time.sleep(3)

    # Take screenshot after login
    page.screenshot(path="tests/e2e/screenshots/after_login.png")
    print("📸 Screenshot saved: after_login.png")

    # Verify we're on Admin Dashboard
    print(f"Current URL: {page.url}")

    # Check if redirected to Admin Dashboard
    assert "Admin_Dashboard" in page.url or "admin" in page.url.lower(), \
        f"Expected to be on Admin Dashboard, but URL is: {page.url}"

    print("✅ Admin login successful!")
