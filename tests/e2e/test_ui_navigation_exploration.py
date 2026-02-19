"""
UI Navigation Exploration Test

Simple test to explore UI structure and find correct selectors
for the full business workflow test.
"""

import pytest
import time
from playwright.sync_api import Page

STREAMLIT_URL = "http://localhost:8501"
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"

FIRST_TEAM_PLAYER = "p3t1k3@f1rstteamfc.hu"
PLAYER_PASSWORD = "TestPass123!"


def login_user(page: Page, email: str, password: str):
    """Login user through Streamlit UI"""
    print(f"     → Logging in as: {email}")

    page.goto(STREAMLIT_URL)
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    email_input = page.locator('input[aria-label="Email"]')
    email_input.fill(email)
    time.sleep(0.5)

    password_input = page.locator('input[type="password"]')
    password_input.fill(password)
    time.sleep(0.5)

    login_button = page.locator('button:has-text("🔐 Login")')
    login_button.click()

    page.wait_for_load_state("networkidle")
    time.sleep(3)

    print(f"     ✅ Logged in successfully")


@pytest.mark.e2e
def test_ui_navigation_exploration(page: Page):
    """
    Explore UI navigation to find selectors for:
    - Tournaments tab
    - Tournament creation
    - Player dashboard
    - Tournament enrollment
    """

    print("\n" + "="*80)
    print("UI NAVIGATION EXPLORATION")
    print("="*80 + "\n")

    # ====================================================================
    # STEP 1: Admin login and navigate to Tournaments tab
    # ====================================================================
    print("STEP 1: Admin navigates to Tournaments tab")
    print("-" * 80)

    login_user(page, ADMIN_EMAIL, ADMIN_PASSWORD)

    # Should be on Admin Dashboard
    page.screenshot(path="tests/e2e/screenshots/admin_dashboard.png")
    print("📸 Screenshot: admin_dashboard.png")

    # Find and click Tournaments tab
    # Try different selectors
    print("\nSearching for Tournaments tab...")

    # Method 1: Try by text
    tournaments_tab = page.locator('button:has-text("Tournaments")')
    if tournaments_tab.count() > 0:
        print(f"✅ Found Tournaments tab by text (count: {tournaments_tab.count()})")
        tournaments_tab.first.click()
        time.sleep(2)
        page.screenshot(path="tests/e2e/screenshots/tournaments_tab.png")
        print("📸 Screenshot: tournaments_tab.png")
    else:
        print("❌ Tournaments tab not found by text")

    # Wait to see the page
    time.sleep(2)

    # ====================================================================
    # STEP 2: Navigate to Create Tournament sub-tab
    # ====================================================================
    print("\nSTEP 2: Navigate to Create Tournament")
    print("-" * 80)

    # Find "Create Tournament" tab
    create_tab = page.locator('button:has-text("Create Tournament")')
    if create_tab.count() > 0:
        print(f"✅ Found Create Tournament tab (count: {create_tab.count()})")
        create_tab.first.click()
        time.sleep(2)
        page.screenshot(path="tests/e2e/screenshots/create_tournament_form.png")
        print("📸 Screenshot: create_tournament_form.png")
    else:
        print("❌ Create Tournament tab not found")

    time.sleep(2)

    # ====================================================================
    # STEP 3: Logout and login as player
    # ====================================================================
    print("\nSTEP 3: Logout and login as First Team player")
    print("-" * 80)

    # Find logout button
    logout_button = page.locator('button:has-text("Logout")')
    if logout_button.count() > 0:
        print("✅ Found Logout button")
        logout_button.first.click()
        time.sleep(2)
    else:
        print("❌ Logout button not found - navigating to home instead")
        page.goto(STREAMLIT_URL)
        time.sleep(2)

    # Login as player
    login_user(page, FIRST_TEAM_PLAYER, PLAYER_PASSWORD)

    # Take screenshot of player dashboard
    page.screenshot(path="tests/e2e/screenshots/player_dashboard.png")
    print("📸 Screenshot: player_dashboard.png")

    # Wait to see the page
    time.sleep(3)

    print("\n" + "="*80)
    print("✅ NAVIGATION EXPLORATION COMPLETE")
    print("="*80 + "\n")
    print("Check screenshots in tests/e2e/screenshots/")
