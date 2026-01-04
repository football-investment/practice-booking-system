"""Debug script to examine Streamlit date_input widget structure"""

import pytest
from playwright.sync_api import Page
import os
from datetime import datetime

STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")

@pytest.mark.e2e
def test_debug_date_picker(page: Page):
    """Open registration form and examine date input widget"""

    print("\n🔍 DEBUG: Date Input Widget Structure")

    # Step 1: Navigate to home page
    page.goto(STREAMLIT_URL)
    page.wait_for_timeout(2000)
    print("  1️⃣ Opened home page")

    # Step 2: Click Register button
    register_btn = page.locator("button:has-text('Register with Invitation Code')")
    register_btn.click()
    page.wait_for_timeout(2000)
    print("  2️⃣ Registration form opened")

    # Step 3: Take screenshot of empty form
    page.screenshot(path="docs/screenshots/debug_date_picker_form.png")
    print("  📸 Screenshot saved: docs/screenshots/debug_date_picker_form.png")

    # Step 4: Try to locate date input with different selectors
    print("\n  🔍 Testing different selectors:")

    selectors = [
        "input[aria-label='Date of Birth *']",
        "input[type='date']",
        "[data-baseweb='input']",
        "input[aria-label*='Date of Birth']",
        "div[data-testid*='stDateInput']",
        "[data-testid='stDateInput']",
    ]

    for selector in selectors:
        try:
            element = page.locator(selector).first
            is_visible = element.is_visible(timeout=1000)
            print(f"    ✅ Found: {selector} (visible: {is_visible})")
        except:
            print(f"    ❌ Not found: {selector}")

    # Step 5: Print all input elements
    print("\n  📋 All input elements on page:")
    inputs = page.locator("input").all()
    for i, inp in enumerate(inputs):
        try:
            aria_label = inp.get_attribute("aria-label", timeout=500)
            input_type = inp.get_attribute("type", timeout=500)
            visible = inp.is_visible()
            print(f"    {i}: aria-label='{aria_label}' type='{input_type}' visible={visible}")
        except:
            print(f"    {i}: (could not get attributes)")

    # Step 6: Fill other fields first to see if date input appears
    print("\n  3️⃣ Filling other fields...")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    page.locator("input[aria-label='Your Name *']").fill(f"Test User {timestamp}")
    print("    ✅ Filled name")

    page.locator("input[aria-label='Your Email *']").fill(f"test{timestamp}@example.com")
    print("    ✅ Filled email")

    page.locator("input[aria-label='Your Password *']").fill("test1234")
    print("    ✅ Filled password")

    page.wait_for_timeout(1000)

    # Step 7: Take screenshot after filling fields
    page.screenshot(path="docs/screenshots/debug_date_picker_after_fill.png")
    print("  📸 Screenshot saved: docs/screenshots/debug_date_picker_after_fill.png")

    # Step 8: Try to interact with date input
    print("\n  4️⃣ Attempting date input interaction...")

    try:
        # Try clicking on date input area
        date_label = page.locator("text=Date of Birth *")
        date_label.scroll_into_view_if_needed()
        print("    ✅ Scrolled to date input")

        # Take screenshot focused on date input
        page.screenshot(path="docs/screenshots/debug_date_picker_focused.png")
        print("  📸 Screenshot saved: docs/screenshots/debug_date_picker_focused.png")

    except Exception as e:
        print(f"    ❌ Error: {e}")

    # Keep browser open for manual inspection
    print("\n  ⏸️  Pausing for 30 seconds - inspect the browser manually")
    page.wait_for_timeout(30000)

    print("\n✅ Debug session complete")
