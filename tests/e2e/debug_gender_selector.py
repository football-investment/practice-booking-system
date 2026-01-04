"""Debug script to examine Gender selectbox interaction"""

import pytest
from playwright.sync_api import Page
import os
from datetime import datetime

STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")

@pytest.mark.e2e
def test_debug_gender_selector(page: Page):
    """Open registration form and examine Gender selectbox"""

    print("\n🔍 DEBUG: Gender Selectbox Interaction")

    # Step 1: Navigate and open registration form
    page.goto(STREAMLIT_URL)
    page.wait_for_timeout(2000)

    register_btn = page.locator("button:has-text('Register with Invitation Code')")
    register_btn.click()
    page.wait_for_timeout(2000)
    print("  1️⃣ Registration form opened")

    # Step 2: Fill other fields first
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    page.locator("input[aria-label='Your Name *']").fill(f"Test User {timestamp}")
    page.locator("input[aria-label='Your Email *']").fill(f"test{timestamp}@example.com")
    page.locator("input[aria-label='Choose Password *']").fill("test1234")
    page.locator("input[aria-label='Select a date.']").fill("2000/01/15")
    page.locator("input[aria-label='Nationality *']").fill("Hungarian")
    print("  2️⃣ Filled other fields")

    page.wait_for_timeout(1000)

    # Step 3: Examine Gender selectbox
    print("\n  🔍 Examining Gender selectbox:")

    # Try different selectors for the selectbox
    selectors = [
        "div[data-baseweb='select']",
        "[data-testid='stSelectbox']",
        "input[aria-label='Gender *']",
        "div:has-text('Gender *')",
    ]

    for selector in selectors:
        try:
            element = page.locator(selector).first
            is_visible = element.is_visible(timeout=1000)
            print(f"    ✅ Found: {selector} (visible: {is_visible})")
        except:
            print(f"    ❌ Not found: {selector}")

    # Step 4: Try to interact with Gender selectbox
    print("\n  3️⃣ Attempting to select Gender...")

    try:
        # Method 1: Click on the selectbox by data-baseweb
        print("    Method 1: Click selectbox by data-baseweb...")
        gender_selectbox = page.locator("div[data-baseweb='select']").last  # Use last because there might be multiple
        gender_selectbox.scroll_into_view_if_needed()
        page.wait_for_timeout(500)

        # Take screenshot before clicking
        page.screenshot(path="docs/screenshots/debug_gender_before_click.png")
        print("      📸 Screenshot before click: debug_gender_before_click.png")

        gender_selectbox.click()
        page.wait_for_timeout(1000)

        # Take screenshot after clicking (dropdown should be open)
        page.screenshot(path="docs/screenshots/debug_gender_after_click.png")
        print("      📸 Screenshot after click: debug_gender_after_click.png")

        # Try to find and click "Male" option
        print("    Trying to select 'Male' option...")

        # List all visible options
        print("    Visible elements containing 'Male':")
        male_options = page.locator("text=Male").all()
        for i, opt in enumerate(male_options):
            try:
                visible = opt.is_visible()
                text = opt.inner_text(timeout=500)
                print(f"      {i}: '{text}' (visible: {visible})")
            except:
                print(f"      {i}: (could not get info)")

        # Try clicking Male option
        if male_options:
            # Click the first visible "Male" option
            for opt in male_options:
                if opt.is_visible():
                    opt.click()
                    print("      ✅ Clicked 'Male' option")
                    break

        page.wait_for_timeout(1000)

        # Take screenshot after selection
        page.screenshot(path="docs/screenshots/debug_gender_after_select.png")
        print("      📸 Screenshot after selection: debug_gender_after_select.png")

    except Exception as e:
        print(f"    ❌ Error: {e}")
        page.screenshot(path="docs/screenshots/debug_gender_error.png")

    # Step 5: Check if Gender was selected
    print("\n  4️⃣ Checking if Gender field has value...")
    try:
        # Check the selectbox for selected value
        gender_value = page.locator("div[data-baseweb='select']").last.inner_text(timeout=1000)
        print(f"    Gender value: '{gender_value}'")
    except Exception as e:
        print(f"    ❌ Could not get gender value: {e}")

    # Keep browser open for manual inspection
    print("\n  ⏸️  Pausing for 20 seconds - inspect the browser manually")
    page.wait_for_timeout(20000)

    print("\n✅ Debug session complete")
