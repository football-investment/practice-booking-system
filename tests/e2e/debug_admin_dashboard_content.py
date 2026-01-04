"""
Debug script to see what's on the Admin Dashboard page
"""

import pytest
from playwright.sync_api import Page
import os

STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"


@pytest.mark.e2e
def test_debug_admin_dashboard_content(page: Page):
    """See what content is on Admin Dashboard after login"""

    print("\n🔍 Debugging Admin Dashboard content...")

    # Login
    page.goto(STREAMLIT_URL)
    page.wait_for_timeout(2000)
    page.fill("input[aria-label='Email']", ADMIN_EMAIL)
    page.fill("input[aria-label='Password']", ADMIN_PASSWORD)
    page.click("button:has-text('Login')")
    page.wait_for_timeout(8000)  # Wait extra long

    print(f"📍 Current URL: {page.url}")

    # Take screenshot
    page.screenshot(path="docs/screenshots/debug_admin_content.png")

    # Print ALL text on page
    all_text = page.locator("body").inner_text()
    print(f"\n📄 ALL TEXT ON PAGE:")
    print("=" * 80)
    print(all_text[:2000])  # First 2000 chars
    print("=" * 80)

    # Print all buttons
    buttons = page.locator("button").all()
    print(f"\n🔘 ALL BUTTONS ({len(buttons)} total):")
    for i, btn in enumerate(buttons):
        try:
            text = btn.inner_text(timeout=500)
            visible = btn.is_visible()
            print(f"  {i}: '{text}' (visible: {visible})")
        except:
            print(f"  {i}: (could not get text)")

    # Check for error messages
    if "error" in all_text.lower() or "denied" in all_text.lower():
        print("\n⚠️ POSSIBLE ERROR ON PAGE!")

    print("\n✅ Debug complete")
