"""Simple debug script to see tabs after Admin login"""

import pytest
from playwright.sync_api import Page
import os

STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"

@pytest.mark.e2e
def test_debug_admin_tabs(page: Page):
    """Login and check what tabs appear"""

    print("\n🔍 DEBUG: Admin Dashboard Tabs")

    # Step 1: Login
    print("  1️⃣ Logging in...")
    page.goto(STREAMLIT_URL)
    page.wait_for_timeout(2000)

    page.fill("input[aria-label='Email']", ADMIN_EMAIL)
    page.fill("input[aria-label='Password']", ADMIN_PASSWORD)
    page.click("button:has-text('Login')")

    # Step 2: Wait for redirect
    print("  2️⃣ Waiting for redirect...")
    page.wait_for_timeout(8000)  # Wait longer

    # Step 3: Check URL
    url = page.url
    print(f"  📍 Current URL: {url}")

    # Step 4: Check if we need to navigate
    if "/Admin_Dashboard" not in url:
        print("  ⚠️ Not on Admin Dashboard, navigating...")
        page.goto(f"{STREAMLIT_URL}/Admin_Dashboard")
        page.wait_for_timeout(5000)

    # Step 5: Wait EVEN LONGER for tabs to render
    print("  3️⃣ Waiting for tabs to render (12 seconds)...")
    page.wait_for_timeout(12000)

    # Step 6: List ALL buttons
    print("\n  📋 ALL BUTTONS ON PAGE:")
    buttons = page.locator("button").all()
    for i, btn in enumerate(buttons):
        try:
            text = btn.inner_text(timeout=500)
            visible = btn.is_visible()
            print(f"    {i}: '{text}' (visible: {visible})")
        except:
            print(f"    {i}: (could not get text)")

    # Step 7: Take screenshot
    page.screenshot(path="docs/screenshots/debug_admin_tabs_simple.png")
    print(f"\n  📸 Screenshot saved: docs/screenshots/debug_admin_tabs_simple.png")

    # Keep browser open
    page.wait_for_timeout(5000)
