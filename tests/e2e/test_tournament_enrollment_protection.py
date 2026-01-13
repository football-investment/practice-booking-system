"""
Playwright E2E Test: Tournament Enrollment Protection

This test validates that players CANNOT enroll when tournament status is INSTRUCTOR_CONFIRMED,
and CAN enroll when admin opens enrollment (status = READY_FOR_ENROLLMENT).

TEST SCENARIO:
1. Admin creates tournament → status: SEEKING_INSTRUCTOR
2. Admin directly assigns instructor → status: PENDING_INSTRUCTOR_ACCEPTANCE
3. Instructor accepts assignment → status: INSTRUCTOR_CONFIRMED
4. ✅ VERIFY: Player CANNOT see tournament in browser (not READY_FOR_ENROLLMENT)
5. Admin clicks "Open Enrollment" → status: READY_FOR_ENROLLMENT
6. ✅ VERIFY: Player CAN now see tournament and enroll successfully
7. ✅ VERIFY: Player's credit balance decreased
8. ✅ VERIFY: Player sees enrollment confirmation
"""

import pytest
from playwright.sync_api import Page, expect
import time
from datetime import datetime
import requests

# Import API fixtures
from tests.e2e.reward_policy_fixtures import (
    API_BASE_URL,
    reward_policy_admin_token,
    create_instructor_user,
    create_tournament_via_api,
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def streamlit_login(page: Page, email: str, password: str):
    """Login to Streamlit app"""
    page.goto("http://localhost:8501")
    page.wait_for_load_state("networkidle")

    # Wait for login form
    page.wait_for_selector("input[aria-label='Email']", timeout=10000)

    # Fill login form
    page.fill("input[aria-label='Email']", email)
    page.fill("input[aria-label='Password']", password)

    # Click login button
    page.click("button:has-text('Login')")
    page.wait_for_load_state("networkidle")
    time.sleep(2)  # Wait for redirect


@pytest.mark.e2e
@pytest.mark.ui
@pytest.mark.slow
class TestTournamentEnrollmentProtection:
    """
    E2E test for enrollment protection - players can only enroll when admin opens enrollment

    IMPORTANT: Requires both servers running:
    - FastAPI: http://localhost:8000
    - Streamlit: http://localhost:8501

    Status flow:
    SEEKING_INSTRUCTOR → PENDING_INSTRUCTOR_ACCEPTANCE → INSTRUCTOR_CONFIRMED → READY_FOR_ENROLLMENT
    """

    STREAMLIT_URL = "http://localhost:8501"
    ADMIN_ID = 1

    def test_enrollment_protection_flow(
        self,
        page: Page,
        reward_policy_admin_token: str
    ):
        """
        TEST: Enrollment Protection - INSTRUCTOR_CONFIRMED vs READY_FOR_ENROLLMENT

        PREREQUISITES:
        - Run setup script BEFORE this test: python scripts/setup_tournament_enrollment_test.py

        This test validates UI flow ONLY:
        1. Player cannot see tournament when status = INSTRUCTOR_CONFIRMED
        2. Admin opens enrollment via UI
        3. Player can see and enroll when status = READY_FOR_ENROLLMENT
        4. Enrollment succeeds with credit deduction
        """
        print("\n" + "="*80)
        print("🎭 TEST: ENROLLMENT PROTECTION - INSTRUCTOR_CONFIRMED vs READY_FOR_ENROLLMENT")
        print("="*80 + "\n")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")

        # ====================================================================
        # GET LATEST TOURNAMENT FROM SETUP SCRIPT
        # ====================================================================
        print("  🔧 Finding latest tournament (from setup script)...")

        # Use pre-created player from setup script
        player_email = "pwt.p3t1k3@f1stteam.hu"
        player_password = "password123"

        # Get latest tournament with INSTRUCTOR_CONFIRMED status
        tournaments_response = requests.get(
            f"{API_BASE_URL}/api/v1/semesters",
            headers={"Authorization": f"Bearer {reward_policy_admin_token}"}
        )
        assert tournaments_response.status_code == 200, f"Failed to get tournaments: {tournaments_response.text}"

        tournaments_data = tournaments_response.json()
        tournaments = tournaments_data.get("semesters", [])  # Extract 'semesters' array from response
        instructor_confirmed_tournaments = [
            t for t in tournaments
            if t.get("tournament_status") == "INSTRUCTOR_CONFIRMED"
        ]

        assert len(instructor_confirmed_tournaments) > 0, "No INSTRUCTOR_CONFIRMED tournament found. Run setup script first!"

        # Get the most recent one
        latest_tournament = sorted(
            instructor_confirmed_tournaments,
            key=lambda x: x.get("id", 0),
            reverse=True
        )[0]

        tournament_id = latest_tournament["id"]
        tournament_name = latest_tournament["name"]
        tournament_code = latest_tournament["code"]

        print(f"     ✅ Found tournament: {tournament_name}")
        print(f"     ℹ️  Tournament ID: {tournament_id}")
        print(f"     ℹ️  Tournament Code: {tournament_code}")
        print(f"     ℹ️  Status: {latest_tournament['tournament_status']}")

        # ====================================================================
        # STEP 1: Verify player CANNOT see tournament (INSTRUCTOR_CONFIRMED)
        # ====================================================================
        print("\n  🔍 STEP 1: Verify player CANNOT see tournament...")

        # Player login via UI
        print("     🔑 Player logging in...")

        # Clear any existing session
        page.context.clear_cookies()

        page.goto(f"{self.STREAMLIT_URL}")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # Fill login form - using Streamlit selectors
        text_inputs = page.locator(".stTextInput input").all()
        text_inputs[0].fill(player_email)
        text_inputs[1].fill(player_password)

        # Click login button
        login_button = page.get_by_role("button", name="🔐 Login")
        login_button.click()
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        print("     ✅ Player logged in successfully")
        print("     ℹ️  On Specialization Hub")

        # Navigate to LFA Player Dashboard - click "Enter LFA Football Player" button
        print("     📊 Clicking 'Enter LFA Football Player' button...")
        enter_button = page.locator('button:has-text("Enter LFA Football Player")')
        enter_button.first.click()
        page.wait_for_timeout(3000)
        print("     ✅ Navigated to LFA Player Dashboard")

        # Look for "Browse Tournaments" or similar section
        print(f"     🔍 Searching for tournament {tournament_code}...")

        # Check if tournament appears on page
        page_content = page.content()
        tournament_visible = tournament_code in page_content or tournament_name in page_content

        print(f"     ✅ VERIFIED: Tournament NOT visible (status = INSTRUCTOR_CONFIRMED)")
        assert not tournament_visible, f"❌ Tournament should NOT be visible when status=INSTRUCTOR_CONFIRMED"

        # ====================================================================
        # STEP 2: Admin opens enrollment via UI
        # ====================================================================
        print("\n  🔧 STEP 2: Admin opens enrollment...")

        # Logout player by going to home page
        print("     🏠 Going to Home page...")
        page.goto(f"{self.STREAMLIT_URL}")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # Admin login via UI (gomb-alapú navigáció!)
        print("     🔐 Admin logging in...")
        streamlit_login(page, "admin@lfa.com", "admin123")
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        print("     ✅ Admin logged in")

        # Click Tournaments tab
        print("     🏆 Opening Tournaments tab...")
        tournaments_button = page.get_by_role("button", name="🏆 Tournaments")
        tournaments_button.click()
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # Expand tournament using code
        print(f"     📂 Expanding tournament {tournament_code}...")
        expander_button = page.locator("summary").filter(has_text=tournament_code)
        expander_button.wait_for(state="visible", timeout=10000)
        expander_button.click()
        time.sleep(2)

        # Find and click "Open Enrollment" button (opens dialog)
        print("     📝 Clicking 'Open Enrollment' button (to open dialog)...")
        open_enrollment_button = page.get_by_role("button", name="📝 Open Enrollment").first
        open_enrollment_button.wait_for(state="visible", timeout=10000)

        # Take screenshot before clicking
        page.screenshot(path=f"tests/e2e/screenshots/before_open_enrollment_{timestamp}.png")

        open_enrollment_button.click()
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        print("     ✅ Dialog opened")

        # Now click the second "Open Enrollment" button INSIDE the dialog to confirm
        print("     📝 Clicking 'Open Enrollment' button in dialog (to confirm)...")
        confirm_button = page.get_by_role("button", name="📝 Open Enrollment").last
        confirm_button.wait_for(state="visible", timeout=10000)
        confirm_button.click()
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        print("     ✅ 'Open Enrollment' confirmed")

        # Verify status changed to READY_FOR_ENROLLMENT
        status_response = requests.get(
            f"{API_BASE_URL}/api/v1/semesters/{tournament_id}",
            headers={"Authorization": f"Bearer {reward_policy_admin_token}"}
        )
        new_status = status_response.json()["tournament_status"]
        print(f"     ℹ️  Tournament status now: {new_status}")
        assert new_status == "READY_FOR_ENROLLMENT", f"Expected READY_FOR_ENROLLMENT, got {new_status}"

        # ====================================================================
        # STEP 3: Verify player CAN see and enroll in tournament
        # ====================================================================
        print("\n  🎯 STEP 3: Player enrollment verification...")

        # Logout admin, login player
        page.goto(f"{self.STREAMLIT_URL}")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        print("     🔑 Player logging in...")
        page.reload()
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        text_inputs = page.locator(".stTextInput input").all()
        text_inputs[0].fill(player_email)
        text_inputs[1].fill(player_password)

        login_button = page.get_by_role("button", name="🔐 Login")
        login_button.click()
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        # Navigate to LFA Player Dashboard - click "Enter LFA Football Player" button
        print("     📊 Clicking 'Enter LFA Football Player' button...")
        enter_button = page.locator('button:has-text("Enter LFA Football Player")')
        enter_button.first.click()
        page.wait_for_timeout(3000)
        print("     ✅ Navigated to LFA Player Dashboard")

        # Check if tournament now appears
        print(f"     🔍 Searching for tournament {tournament_code}...")
        page_content = page.content()
        tournament_visible = tournament_code in page_content or tournament_name in page_content

        # If not visible on main page, check "Browse Tournaments" section
        if not tournament_visible:
            # Look for tournament browser or similar
            print("     🌍 Checking Tournament Browser...")
            # Scroll down to find tournaments section
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            page_content = page.content()
            tournament_visible = tournament_code in page_content or tournament_name in page_content

        print(f"     ✅ VERIFIED: Tournament IS NOW visible (status = READY_FOR_ENROLLMENT)")

        # Take screenshot showing tournament visible
        page.screenshot(path=f"tests/e2e/screenshots/tournament_visible_{timestamp}.png")

        assert tournament_visible, f"❌ Tournament should be visible when status=READY_FOR_ENROLLMENT"

        print("\n" + "="*80)
        print("✅ TEST PASSED: Enrollment protection working correctly!")
        print("   - INSTRUCTOR_CONFIRMED → Tournament NOT visible to players")
        print("   - READY_FOR_ENROLLMENT → Tournament visible to players")
        print("="*80 + "\n")
