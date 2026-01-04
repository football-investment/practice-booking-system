"""
Debug script to identify correct Streamlit UI selectors.

Run with: PYTHONPATH=. pytest tests/e2e/debug_login.py -v --headed --slowmo 1000

This will open a browser window in slow motion so you can see what's happening.
"""

import pytest
from playwright.sync_api import Page
import os


STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")
INSTRUCTOR_EMAIL = os.getenv("TEST_INSTRUCTOR_EMAIL", "instructor@lfa.com")
INSTRUCTOR_PASSWORD = os.getenv("TEST_INSTRUCTOR_PASSWORD", "instructor123")


@pytest.mark.e2e
def test_debug_login_selectors(page: Page):
    """
    Debug test to find correct login selectors.

    This test will:
    1. Navigate to Streamlit app
    2. Take screenshot of login page
    3. Print all available input fields
    4. Attempt login with various selector strategies
    """
    print(f"\n🔍 Navigating to {STREAMLIT_URL}")
    page.goto(STREAMLIT_URL)

    # Wait for page load
    page.wait_for_timeout(3000)

    # Take screenshot of login page
    page.screenshot(path="docs/screenshots/debug_login_page.png")
    print("📸 Screenshot saved: docs/screenshots/debug_login_page.png")

    # Print page title
    print(f"📄 Page title: {page.title()}")

    # Check for "Login" text
    if page.locator("text=Login").count() > 0:
        print("✅ Found 'Login' text on page")
    else:
        print("❌ No 'Login' text found")

    # Count all input fields
    text_inputs = page.locator("input[type='text'], input[type='email'], input[type='password'], input")
    print(f"📝 Found {text_inputs.count()} input fields")

    # Try to identify email/password fields
    for i in range(text_inputs.count()):
        input_elem = text_inputs.nth(i)
        placeholder = input_elem.get_attribute("placeholder") or ""
        input_type = input_elem.get_attribute("type") or ""
        aria_label = input_elem.get_attribute("aria-label") or ""
        data_testid = input_elem.get_attribute("data-testid") or ""

        print(f"\nInput {i}:")
        print(f"  - type: {input_type}")
        print(f"  - placeholder: {placeholder}")
        print(f"  - aria-label: {aria_label}")
        print(f"  - data-testid: {data_testid}")

    # Count buttons
    buttons = page.locator("button")
    print(f"\n🔘 Found {buttons.count()} buttons")

    for i in range(min(5, buttons.count())):  # Print first 5 buttons
        btn = buttons.nth(i)
        text = btn.text_content() or ""
        aria_label = btn.get_attribute("aria-label") or ""
        data_testid = btn.get_attribute("data-testid") or ""

        print(f"\nButton {i}:")
        print(f"  - text: {text}")
        print(f"  - aria-label: {aria_label}")
        print(f"  - data-testid: {data_testid}")

    # Try Strategy 1: data-testid
    print("\n\n🧪 STRATEGY 1: Using data-testid")
    try:
        email_inputs = page.locator("[data-testid='stTextInput']")
        print(f"Found {email_inputs.count()} elements with stTextInput testid")

        if email_inputs.count() >= 2:
            print("✅ Strategy 1 might work (found 2+ stTextInput fields)")

            # Try filling
            email_inputs.nth(0).fill(INSTRUCTOR_EMAIL)
            page.wait_for_timeout(500)
            email_inputs.nth(1).fill(INSTRUCTOR_PASSWORD)
            page.wait_for_timeout(500)

            page.screenshot(path="docs/screenshots/debug_login_filled_strategy1.png")
            print("📸 Screenshot saved: debug_login_filled_strategy1.png")

            # Try to click login button
            login_buttons = page.locator("button:has-text('Login'), button:has-text('Log In'), button:has-text('Sign In')")
            if login_buttons.count() > 0:
                print(f"Found {login_buttons.count()} login buttons")
                login_buttons.first.click()

                # Wait and see what happens
                page.wait_for_timeout(3000)
                page.screenshot(path="docs/screenshots/debug_login_after_click.png")
                print("📸 Screenshot saved: debug_login_after_click.png")

                # Check for success
                if "Dashboard" in page.content() or "Instructor" in page.content():
                    print("✅ ✅ ✅ LOGIN SUCCESSFUL with Strategy 1!")
                else:
                    print("❌ Login may have failed - no Dashboard text found")
            else:
                print("❌ No login button found")
        else:
            print("❌ Strategy 1 won't work (need 2 stTextInput fields)")
    except Exception as e:
        print(f"❌ Strategy 1 failed: {e}")

    # Try Strategy 2: placeholder text
    print("\n\n🧪 STRATEGY 2: Using placeholder text")
    try:
        page.reload()
        page.wait_for_timeout(2000)

        email_field = page.locator("input[placeholder*='mail'], input[placeholder*='Email']")
        password_field = page.locator("input[type='password'], input[placeholder*='assword']")

        print(f"Found {email_field.count()} email fields")
        print(f"Found {password_field.count()} password fields")

        if email_field.count() > 0 and password_field.count() > 0:
            print("✅ Strategy 2 might work")

            email_field.first.fill(INSTRUCTOR_EMAIL)
            page.wait_for_timeout(500)
            password_field.first.fill(INSTRUCTOR_PASSWORD)
            page.wait_for_timeout(500)

            page.screenshot(path="docs/screenshots/debug_login_filled_strategy2.png")
            print("📸 Screenshot saved: debug_login_filled_strategy2.png")

            # Click login
            login_buttons = page.locator("button:has-text('Login'), button:has-text('Log In')")
            if login_buttons.count() > 0:
                login_buttons.first.click()
                page.wait_for_timeout(3000)

                if "Dashboard" in page.content():
                    print("✅ ✅ ✅ LOGIN SUCCESSFUL with Strategy 2!")
                else:
                    print("❌ Login may have failed")
        else:
            print("❌ Strategy 2 won't work")
    except Exception as e:
        print(f"❌ Strategy 2 failed: {e}")

    # Print final page content (first 500 chars)
    print("\n\n📄 Final page content (first 500 chars):")
    print(page.content()[:500])

    print("\n\n✅ Debug test complete. Check screenshots in docs/screenshots/")


@pytest.mark.e2e
def test_find_dashboard_selectors(page: Page):
    """
    After successful login, identify dashboard selectors.

    This helps find what text/elements to wait for after login.
    """
    print("\n🔍 Attempting login to find dashboard selectors...")

    page.goto(STREAMLIT_URL)
    page.wait_for_timeout(2000)

    # Use aria-label strategy (most reliable)
    try:
        page.fill("input[aria-label='Email']", INSTRUCTOR_EMAIL)
        page.fill("input[aria-label='Password']", INSTRUCTOR_PASSWORD)

        login_btn = page.locator("button:has-text('Login')")
        if login_btn.count() > 0:
            login_btn.first.click()
            page.wait_for_timeout(3000)

            # Take screenshot of dashboard
            page.screenshot(path="docs/screenshots/debug_dashboard.png")
            print("📸 Screenshot saved: debug_dashboard.png")

            # Look for common dashboard elements
            if page.locator("text=Dashboard").count() > 0:
                print("✅ Found 'Dashboard' text")

            if page.locator("text=Instructor").count() > 0:
                print("✅ Found 'Instructor' text")

            if page.locator("text=Tournament").count() > 0:
                print("✅ Found 'Tournament' text")

            if page.locator("text=Session").count() > 0:
                print("✅ Found 'Session' text")

            # Print all h1, h2, h3 headings
            headings = page.locator("h1, h2, h3")
            print(f"\n📋 Found {headings.count()} headings:")
            for i in range(min(10, headings.count())):
                print(f"  - {headings.nth(i).text_content()}")

            # Look for sidebar navigation
            sidebar = page.locator("[data-testid='stSidebar']")
            if sidebar.count() > 0:
                print("\n✅ Found sidebar")
                print(f"Sidebar content preview: {sidebar.text_content()[:200]}")

            print("\n✅ Dashboard debug complete")
    except Exception as e:
        print(f"❌ Login failed: {e}")
