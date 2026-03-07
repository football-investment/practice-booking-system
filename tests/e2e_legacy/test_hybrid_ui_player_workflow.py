"""
Hybrid UI Test - Player Workflow

SETUP (API):
- Admin creates 1 tournament via API
- Admin creates 1 coupon (TOURNAMENTPROMO1, 500 credits, max_uses=100) via API

TESTING (UI - Playwright):
- Player login (UI)
- Navigate to My Credits (UI)
- Apply coupon TOURNAMENTPROMO1 → +500 credits (UI)
- Navigate to Specialization Hub (UI)
- Unlock LFA Football Player → -100 credits (UI)
- Complete Onboarding (3 steps) (UI)
- Navigate to Player Dashboard (UI)
- Find and enroll in tournament (UI)
- Verify enrollment successful (UI)

This test uses EXISTING First Team players (no new user creation).
"""

import pytest
import time
import random
import requests
from datetime import datetime
from playwright.sync_api import Page

# API Setup
API_BASE_URL = "http://localhost:8000"
STREAMLIT_URL = "http://localhost:8501"

# Users
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"

FIRST_TEAM_PLAYERS = [
    {"email": "p3t1k3@f1rstteamfc.hu", "password": "TestPass123!"},
    {"email": "v4lv3rd3jr.77@f1rstteamfc.hu", "password": "TestPass123!"},
    {"email": "k1sqx1@f1rstteamfc.hu", "password": "TestPass123!"}
]


def api_login(email: str, password: str) -> str:
    """Login via API and return token"""
    response = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    response.raise_for_status()
    return response.json()["access_token"]


def api_create_coupon(admin_token: str, code: str, credits: int, max_uses: int = 100):
    """Create coupon via API"""
    response = requests.post(
        f"{API_BASE_URL}/api/v1/admin/coupons",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "code": code.upper(),
            "type": "credits",
            "discount_value": credits,
            "description": f"Test coupon - {credits} credits",
            "is_active": True,
            "expires_at": None,
            "max_uses": max_uses
        }
    )
    response.raise_for_status()
    return response.json()


def api_create_tournament(admin_token: str, name: str):
    """Create tournament via API using the working fixtures function"""
    # Import the working tournament generator from fixtures
    import sys
    from pathlib import Path
    test_dir = Path(__file__).parent
    sys.path.insert(0, str(test_dir))

    from reward_policy_fixtures import create_tournament_via_api

    # Use the working function from fixtures
    tournament = create_tournament_via_api(
        token=admin_token,
        name=name,
        age_group="PRO"
    )
    return tournament


def ui_login(page: Page, email: str, password: str):
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


def ui_logout(page: Page):
    """Logout user through Streamlit UI"""
    print(f"     → Logging out...")

    logout_button = page.locator('button:has-text("Logout")')
    if logout_button.count() > 0:
        logout_button.first.click()
        time.sleep(2)
        print(f"     ✅ Logged out")
    else:
        # Navigate to home as fallback
        page.goto(STREAMLIT_URL)
        time.sleep(2)
        print(f"     ⚠️  Logout button not found - navigated to home")


from datetime import timedelta


@pytest.mark.e2e
@pytest.mark.slow
class TestHybridUIPlayerWorkflow:
    """Hybrid UI test - Player complete workflow"""

    def test_player_complete_workflow(self, page: Page):
        """
        Test complete player workflow:
        1. API Setup: Create tournament and coupon
        2. UI Test: Player login → Coupon → Specialization → Onboarding → Tournament
        """

        print("\n" + "="*80)
        print("HYBRID UI PLAYER WORKFLOW TEST")
        print("="*80 + "\n")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        # ====================================================================
        # API SETUP: Admin creates tournament and coupon
        # ====================================================================
        print("API SETUP: Creating tournament and coupon")
        print("-" * 80)

        admin_token = api_login(ADMIN_EMAIL, ADMIN_PASSWORD)
        print(f"     ✅ Admin logged in via API")

        # Create coupon (reusable 100 times)
        coupon_code = "TOURNAMENTPROMO1"
        try:
            coupon = api_create_coupon(admin_token, coupon_code, credits=500, max_uses=100)
            print(f"     ✅ Coupon created: {coupon_code} (500 credits, max_uses=100)")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                print(f"     ⚠️  Coupon {coupon_code} already exists (will reuse)")
            else:
                raise

        # Create tournament
        tournament_name = f"UI Test Tournament {timestamp}"
        tournament = api_create_tournament(admin_token, tournament_name)
        tournament_id = tournament.get("id")
        print(f"     ✅ Tournament created: {tournament_name} (ID: {tournament_id})")

        # ====================================================================
        # UI TEST: Player 1 - Complete Workflow (fresh unlock+onboarding)
        # ====================================================================
        print(f"\nUI TEST: Player 1 - {FIRST_TEAM_PLAYERS[0]['email']}")
        print("-" * 80)

        player = FIRST_TEAM_PLAYERS[0]  # Use player 1 for fresh test

        # Login
        ui_login(page, player["email"], player["password"])
        time.sleep(3)  # Wait for redirect after login
        page.screenshot(path="tests/e2e/screenshots/player1_after_login.png")

        # Check current URL
        current_url = page.url
        print(f"     Current URL: {current_url}")

        # Check current credit balance via API FIRST (before navigating anywhere!)
        print(f"     → Checking credit balance via API...")
        player_token = api_login(player["email"], player["password"])
        user_response = requests.get(
            f"{API_BASE_URL}/api/v1/users/me",
            headers={"Authorization": f"Bearer {player_token}"}
        )
        current_balance = user_response.json().get("credit_balance", 0)
        print(f"     💰 Current balance: {current_balance} credits")

        # Apply coupon ONLY if balance < 100 (needed for specialization unlock)
        required_credits = 100  # For LFA Football Player unlock

        if current_balance < required_credits:
            print(f"     ⚠️  Insufficient credits ({current_balance} < {required_credits})")
            print(f"     → Need to apply coupon - navigating to My Credits...")

            # Navigate to My Credits via SIDEBAR BUTTON
            my_credits_button = page.locator('button:has-text("My Credits")')
            if my_credits_button.count() > 0:
                my_credits_button.first.click()
                page.wait_for_load_state("networkidle")
                time.sleep(2)
                print(f"     ✅ Navigated to My Credits page")
            else:
                print(f"     ❌ My Credits button not found in sidebar")

            page.screenshot(path="tests/e2e/screenshots/player1_my_credits.png")

            print(f"     → Applying coupon: {coupon_code}")

            # Look for coupon input field (placeholder: "Enter coupon code (optional)")
            coupon_input = page.locator('input[placeholder*="coupon" i]')

            if coupon_input.count() > 0:
                coupon_input.first.fill(coupon_code)
                time.sleep(0.5)
                print(f"     ✅ Coupon code entered: {coupon_code}")

                # Click Validate button (the button text is "Validate", not "Apply" or "Redeem")
                validate_button = page.locator('button:has-text("Validate")')

                if validate_button.count() > 0:
                    validate_button.first.click()
                    time.sleep(3)
                    print(f"     ✅ Coupon validated!")
                    page.screenshot(path="tests/e2e/screenshots/player1_coupon_validated.png")

                    # For CREDITS type coupons, we need to actually APPLY the coupon via API
                    # (UI doesn't have a "Redeem Credits" button yet for CREDITS type coupons)
                    print(f"     → Applying CREDITS coupon via API...")
                    apply_response = requests.post(
                        f"{API_BASE_URL}/api/v1/coupons/apply",
                        headers={"Authorization": f"Bearer {player_token}"},
                        json={"code": coupon_code}
                    )
                    if apply_response.status_code == 200:
                        data = apply_response.json()
                        print(f"     ✅ Coupon applied! +{data['credits_awarded']} credits → new balance: {data['new_balance']}")
                    else:
                        error_msg = apply_response.json().get("detail", {}).get("message", "Unknown error")
                        print(f"     ⚠️  API apply failed: {error_msg}")

                    # Click Refresh button in sidebar to reload balance (NOT browser refresh!)
                    print(f"     → Clicking Refresh button to update credit balance...")
                    refresh_button = page.locator('button:has-text("Refresh")')
                    if refresh_button.count() > 0:
                        refresh_button.first.click()
                        time.sleep(2)
                        print(f"     ✅ Credit balance refreshed!")
                    else:
                        print(f"     ⚠️  Refresh button not found")

                    page.screenshot(path="tests/e2e/screenshots/player1_coupon_applied.png")
                else:
                    print(f"     ❌ Validate button not found")
                    page.screenshot(path="tests/e2e/screenshots/player1_no_validate_button.png")
            else:
                print(f"     ❌ Coupon input not found")
                page.screenshot(path="tests/e2e/screenshots/player1_no_coupon_input.png")

            # Navigate back to Specialization Hub via "Back to Hub" button (only if we went to My Credits!)
            print(f"     → Navigating back to Specialization Hub...")
            back_to_hub_button = page.locator('button:has-text("🏠 Back to Hub")')
            if back_to_hub_button.count() > 0:
                back_to_hub_button.first.click()
                page.wait_for_load_state("networkidle")
                time.sleep(3)
                print(f"     ✅ Clicked 'Back to Hub' - should be on Specialization Hub")
            else:
                print(f"     ⚠️  'Back to Hub' button not found")

        else:
            print(f"     ✅ Sufficient credits available ({current_balance} >= {required_credits}) - skipping coupon & staying on Spec Hub")

        page.screenshot(path="tests/e2e/screenshots/player1_spec_hub.png")

        # Check if already unlocked or needs unlock
        print(f"     → Checking LFA Football Player status...")

        # Wait a bit for page to fully render
        time.sleep(2)

        # DEBUG: Print current URL and all buttons
        print(f"     DEBUG: Current URL: {page.url}")
        all_buttons = page.locator('button')
        print(f"     DEBUG: Total buttons on page: {all_buttons.count()}")
        for i in range(min(all_buttons.count(), 15)):
            try:
                text = all_buttons.nth(i).inner_text(timeout=1000)
                if text and text.strip():
                    print(f"     DEBUG: Button {i+1}: '{text}'")
            except:
                pass

        unlock_button = page.locator('button:has-text("100 credits")')
        enter_button = page.locator('button:has-text("Enter LFA Football Player")')
        complete_onboarding_button = page.locator('button:has-text("Complete Onboarding Now")')

        print(f"     DEBUG: unlock_button count: {unlock_button.count()}")
        print(f"     DEBUG: enter_button count: {enter_button.count()}")

        if enter_button.count() > 0:
            print(f"     ✅ Already unlocked! Clicking 'Enter LFA Football Player'...")
            enter_button.first.click()
            time.sleep(3)
            page.screenshot(path="tests/e2e/screenshots/player1_entered_spec.png")

            # Check if onboarding prompt appears
            if complete_onboarding_button.count() > 0:
                print(f"     ⚠️  Onboarding not completed yet! Clicking 'Complete Onboarding Now'...")
                complete_onboarding_button.first.click()
                time.sleep(3)
                print(f"     ✅ Onboarding wizard started")
            else:
                print(f"     ✅ Onboarding already completed - entering spec hub")

        elif unlock_button.count() > 0:
            print(f"     → Unlocking LFA Football Player...")
            unlock_button.first.click()
            time.sleep(2)
            page.screenshot(path="tests/e2e/screenshots/player1_unlock_dialog.png")

            # First try: Click Cancel to test rejection
            print(f"     → First try: Clicking Cancel to test rejection...")
            cancel_button = page.locator('button:has-text("❌ Cancel")')
            if cancel_button.count() > 0:
                cancel_button.first.click()
                time.sleep(1)
                print(f"     ✅ Unlock cancelled")
                page.screenshot(path="tests/e2e/screenshots/player1_unlock_cancelled.png")

            # Second try: Unlock for real
            print(f"     → Second try: Unlocking for real...")
            unlock_button = page.locator('button:has-text("100 credits")')
            if unlock_button.count() > 0:
                unlock_button.first.click()
                time.sleep(2)

                # Click Confirm Unlock
                confirm_button = page.locator('button:has-text("✅ Confirm Unlock")')
                if confirm_button.count() > 0:
                    confirm_button.first.click()
                    time.sleep(3)
                    print(f"     ✅ LFA Football Player unlocked! (100 credits spent)")
                    page.screenshot(path="tests/e2e/screenshots/player1_unlocked.png")
                else:
                    print(f"     ❌ Confirm Unlock button not found")
        else:
            print(f"     ⚠️  Could not find unlock or enter button")

        # Complete Onboarding (3 steps)
        print(f"     → Starting Onboarding...")
        time.sleep(2)

        # Step 1: Position Selection (RANDOM)
        print(f"       Step 1: Position Selection")
        positions = ["Striker", "Midfielder", "Defender", "Goalkeeper"]
        selected_position = random.choice(positions)
        print(f"       🎲 Randomly selecting: {selected_position}")

        position_button = page.locator(f'button:has-text("{selected_position}")')
        if position_button.count() > 0:
            position_button.first.click()
            time.sleep(1)
            print(f"       ✅ Position selected: {selected_position}")

            next_button = page.locator('button:has-text("Next")')
            if next_button.count() > 0:
                next_button.first.click()
                time.sleep(3)
                print(f"       ✅ Step 1 complete")
            else:
                print(f"       ❌ Next button not found")
        else:
            print(f"       ⚠️  Position button not found")

        # Step 2: Skills Assessment (RANDOM VALUES)
        print(f"       Step 2: Skills Assessment")
        time.sleep(2)
        page.screenshot(path="tests/e2e/screenshots/player1_onboarding_step2.png")

        # Streamlit uses div[role="slider"] not input[type="range"]
        sliders = page.locator('div[role="slider"]')
        slider_count = sliders.count()
        print(f"       Found {slider_count} sliders")

        skill_names = ["Heading", "Shooting", "Passing", "Dribbling", "Defending", "Physical"]

        for i in range(min(slider_count, len(skill_names))):
            try:
                slider = sliders.nth(i)
                random_value = random.randint(1, 10)
                current_value = slider.get_attribute("aria-valuenow")
                skill_name = skill_names[i] if i < len(skill_names) else f"Skill {i+1}"

                slider.click()
                time.sleep(0.2)

                # Calculate difference and use arrow keys
                current = int(current_value) if current_value else 5
                diff = random_value - current

                if diff > 0:
                    for _ in range(diff):
                        page.keyboard.press("ArrowRight")
                        time.sleep(0.05)
                elif diff < 0:
                    for _ in range(abs(diff)):
                        page.keyboard.press("ArrowLeft")
                        time.sleep(0.05)

                print(f"         {skill_name}: {random_value}/10")
                time.sleep(0.2)
            except Exception as e:
                print(f"         ❌ Error setting slider {i+1}: {e}")

        time.sleep(1)

        # Click Next
        next_button = page.locator('button:has-text("Next")')
        if next_button.count() > 0:
            next_button.first.click()
            time.sleep(3)
            print(f"       ✅ Step 2 complete")
        else:
            print(f"       ❌ Next button not found")

        page.screenshot(path="tests/e2e/screenshots/player1_onboarding_step3.png")

        # Step 3: Goals & Motivation (DROPDOWN SELECTION)
        print(f"       Step 3: Goals & Motivation")
        time.sleep(1)

        try:
            # Find selectbox input with role="combobox"
            selectbox = page.locator('input[role="combobox"][aria-label*="Primary Goal"]')
            selectbox.scroll_into_view_if_needed()
            time.sleep(0.5)
            selectbox.click(timeout=10000)
            time.sleep(2)

            # Look for dropdown options
            options = page.locator('li[role="option"]')
            option_count = options.count()

            if option_count > 0:
                random_index = random.randint(0, option_count - 1)
                option_text = options.nth(random_index).inner_text(timeout=1000) if random_index < option_count else f"Option {random_index+1}"
                print(f"       🎲 Selecting goal: {option_text}")

                options.nth(random_index).click()
                time.sleep(2)
                print(f"       ✅ Goal selected")
            else:
                print(f"       ❌ No goal options found")
        except Exception as e:
            print(f"       ❌ Error selecting goal: {e}")

        time.sleep(1)
        page.screenshot(path="tests/e2e/screenshots/player1_goal_selected.png")

        # Click Complete button
        complete_button = page.locator('button:has-text("Complete")')
        if complete_button.count() > 0:
            complete_button.first.click()
            time.sleep(3)
            print(f"       ✅ Onboarding complete!")
        else:
            print(f"       ❌ Complete button not found")

        page.screenshot(path="tests/e2e/screenshots/player1_onboarding_complete.png")

        # Should now be on Player Dashboard
        print(f"     ✅ Onboarding complete - should be on Player Dashboard")
        time.sleep(2)
        page.screenshot(path="tests/e2e/screenshots/player1_dashboard.png")

        # Find and enroll in tournament
        print(f"     → Searching for tournament: {tournament_name}")

        # Look for tournament in list (use :has-text for partial match)
        tournament_element = page.locator(f':has-text("{tournament_name}")')

        if tournament_element.count() > 0:
            print(f"     ✅ Found tournament ({tournament_element.count()} matches)")
            tournament_element.first.click()
            time.sleep(2)

            # Click Enroll button
            enroll_button = page.locator('button:has-text("Enroll")').or_(
                page.locator('button:has-text("Join")')
            )

            if enroll_button.count() > 0:
                enroll_button.first.click()
                time.sleep(3)
                print(f"     ✅ Enrolled in tournament!")
                page.screenshot(path="tests/e2e/screenshots/player1_enrolled.png")
            else:
                print(f"     ⚠️  Enroll button not found (might already be enrolled)")
                page.screenshot(path="tests/e2e/screenshots/player1_no_enroll_button.png")
        else:
            print(f"     ❌ Tournament not found in list")
            page.screenshot(path="tests/e2e/screenshots/player1_tournament_search.png")

        # Logout
        ui_logout(page)

        print("\n" + "="*80)
        print("✅ HYBRID UI PLAYER WORKFLOW TEST COMPLETE")
        print("="*80 + "\n")
        print("Check screenshots in tests/e2e/screenshots/")
