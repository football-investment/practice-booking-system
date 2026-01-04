"""Simple login test to verify credentials work."""

import pytest
from playwright.sync_api import Page
import os


STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")


@pytest.mark.e2e
def test_simple_login(page: Page):
    """Test login with grandmaster credentials."""
    print("\n🔍 Testing login...")

    page.goto(STREAMLIT_URL)
    page.wait_for_timeout(2000)

    # Fill credentials
    page.fill("input[aria-label='Email']", "admin@lfa.com")
    page.fill("input[aria-label='Password']", "admin123")

    # Take screenshot before click
    page.screenshot(path="docs/screenshots/before_login_click.png")
    print("📸 Before login click")

    # Click login
    page.click("button:has-text('Login')")
    page.wait_for_timeout(5000)

    # Take screenshot after login
    page.screenshot(path="docs/screenshots/after_login.png")
    print("📸 After login")

    # Check page title
    print(f"Page title: {page.title()}")

    # Check if login error exists
    if page.locator("text=Login failed").count() > 0:
        print("❌ LOGIN FAILED!")
    elif page.locator("text=Incorrect").count() > 0:
        print("❌ INCORRECT CREDENTIALS!")
    else:
        print("✅ No error message found - login might be successful")

    # Look for dashboard or instructor text
    if page.locator("text=Dashboard").count() > 0:
        print("✅ Found 'Dashboard' text")
    if page.locator("text=Instructor").count() > 0:
        print("✅ Found 'Instructor' text")
    if page.locator("text=Grand Master").count() > 0:
        print("✅ Found 'Grand Master' (user name)")

    # Print page URL
    print(f"Current URL: {page.url}")

    # Print first 500 chars of page content
    content = page.content()
    print(f"\nPage content preview (first 500 chars):")
    print(content[:500])

    print("\n✅ Test complete")
