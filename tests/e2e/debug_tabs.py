"""
Debug script to identify tab selectors on Instructor Dashboard.
"""

import pytest
from playwright.sync_api import Page
import os


STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")
INSTRUCTOR_EMAIL = os.getenv("TEST_INSTRUCTOR_EMAIL", "grandmaster@lfa.com")
INSTRUCTOR_PASSWORD = os.getenv("TEST_INSTRUCTOR_PASSWORD", "grandmaster123")


@pytest.mark.e2e
def test_find_tabs_on_instructor_dashboard(page: Page):
    """Find all tabs on Instructor Dashboard."""
    print("\n🔍 Finding tabs on Instructor Dashboard...")

    # Login
    page.goto(STREAMLIT_URL)
    page.wait_for_timeout(2000)

    page.fill("input[aria-label='Email']", INSTRUCTOR_EMAIL)
    page.fill("input[aria-label='Password']", INSTRUCTOR_PASSWORD)
    page.click("button:has-text('Login')")
    page.wait_for_timeout(3000)

    # Instructor is already on Instructor Dashboard after login (no need to click)
    page.wait_for_timeout(3000)

    # Take screenshot
    page.screenshot(path="docs/screenshots/debug_instructor_dashboard.png")
    print("📸 Screenshot saved: debug_instructor_dashboard.png")

    # Look for tabs - Streamlit uses specific data-testid for tabs
    tabs = page.locator("[data-testid='stTabs']")
    print(f"\n📋 Found {tabs.count()} tab containers")

    if tabs.count() > 0:
        # Get all buttons inside tabs (Streamlit renders tabs as buttons)
        tab_buttons = tabs.first.locator("button")
        print(f"Found {tab_buttons.count()} tab buttons")

        for i in range(tab_buttons.count()):
            btn = tab_buttons.nth(i)
            text = btn.text_content() or ""
            data_baseweb = btn.get_attribute("data-baseweb") or ""
            role = btn.get_attribute("role") or ""
            aria_selected = btn.get_attribute("aria-selected") or ""

            print(f"\nTab {i}:")
            print(f"  - text: '{text}'")
            print(f"  - data-baseweb: '{data_baseweb}'")
            print(f"  - role: '{role}'")
            print(f"  - aria-selected: '{aria_selected}'")

    # Try to find "Check-in" text
    print("\n\n🔍 Looking for 'Check-in' text:")
    checkin_elements = page.locator("text=/check.*in/i")
    print(f"Found {checkin_elements.count()} elements containing 'check' and 'in'")

    for i in range(min(5, checkin_elements.count())):
        elem = checkin_elements.nth(i)
        print(f"  - '{elem.text_content()}'")

    # Try clicking the 4th tab (index 3 = "✅ Check-in & Groups")
    print("\n\n🧪 Trying to click 4th tab (Check-in & Groups)...")
    try:
        if tab_buttons.count() >= 4:
            print(f"Clicking tab 3 (4th tab): '{tab_buttons.nth(3).text_content()}'")
            tab_buttons.nth(3).click()
            page.wait_for_timeout(2000)

            page.screenshot(path="docs/screenshots/debug_after_checkin_tab_click.png")
            print("📸 Screenshot saved: debug_after_checkin_tab_click.png")

            # Now look for sub-tabs
            sub_tabs = page.locator("[data-testid='stTabs']").nth(1)
            if sub_tabs.count() > 0:
                print("\n✅ Found sub-tabs!")
                sub_tab_buttons = sub_tabs.locator("button")
                print(f"Found {sub_tab_buttons.count()} sub-tab buttons:")

                for i in range(sub_tab_buttons.count()):
                    btn = sub_tab_buttons.nth(i)
                    print(f"  Sub-tab {i}: '{btn.text_content()}'")
            else:
                print("\n❌ No sub-tabs found")
    except Exception as e:
        print(f"❌ Failed to click tab: {e}")

    print("\n✅ Tab debug complete")
