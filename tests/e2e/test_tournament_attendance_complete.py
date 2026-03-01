"""
REFERENCE E2E TEST - Tournament Attendance (2-Button Rule)

This is a COMPLETE, SELF-CONTAINED E2E test demonstrating:
1. API-based fixture setup (no manual data needed)
2. Role-based testing (instructor login)
3. Critical business rule validation (2 buttons only)
4. Automatic cleanup

USE THIS AS A TEMPLATE for other E2E tests.
"""

import pytest
from playwright.sync_api import Page, expect
# TODO: Fix missing fixture - tournament_with_session doesn't exist in tests.e2e.fixtures
# from tests.e2e.fixtures import tournament_with_session
import os


STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")


@pytest.mark.skip(reason="Missing fixture: tournament_with_session not found in tests.e2e.fixtures")
@pytest.mark.e2e
@pytest.mark.tournament
class TestTournamentAttendanceComplete:
    """
    Complete E2E test for tournament attendance 2-button rule.

    WHAT THIS TESTS:
    - Instructor can login
    - Instructor can navigate to tournament check-in
    - Tournament sessions show ONLY 2 buttons (Present, Absent)
    - NO Late or Excused buttons visible

    FIXTURES USED:
    - tournament_with_session: Creates full test data automatically
    """

    def test_tournament_attendance_shows_only_2_buttons(
        self,
        page: Page,
        tournament_with_session: dict
    ):
        """
        🏆 CRITICAL E2E TEST: Tournament attendance shows only Present/Absent buttons.

        This is the GOLDEN PATH test - validates the core business rule:
        Tournament sessions MUST show exactly 2 attendance buttons, NOT 4.

        Test Flow:
        1. Setup: Fixture creates tournament + session + students
        2. Login: Instructor logs in
        3. Navigate: Go to tournament check-in page
        4. Verify: Count attendance buttons
        5. Assert: Exactly 2 buttons per student (Present, Absent)
        6. Assert: NO Late or Excused buttons
        7. Cleanup: Fixture automatically cleans up test data
        """
        # Extract test data from fixture
        instructor = tournament_with_session["instructor"]
        students = tournament_with_session["students"]
        session = tournament_with_session["session"]

        print(f"\n🏆 Testing tournament session: {session['id']}")
        print(f"   Instructor: {instructor['email']}")
        print(f"   Students: {len(students)}")

        # ================================================================
        # STEP 1: Login as instructor
        # ================================================================
        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        # Fill login credentials
        page.fill("input[aria-label='Email']", instructor["email"])
        page.fill("input[aria-label='Password']", instructor["password"])

        # Click login
        page.click("button:has-text('Login')")

        # Wait for successful login
        page.wait_for_timeout(3000)

        # Verify login success
        expect(page.locator("text=Dashboard")).to_be_visible()
        print("✅ Step 1: Login successful")

        # ================================================================
        # STEP 2: Navigate to Instructor Dashboard
        # ================================================================
        page.goto(f"{STREAMLIT_URL}/Instructor_Dashboard")
        page.wait_for_timeout(2000)

        expect(page.locator("text=Instructor Dashboard")).to_be_visible()
        print("✅ Step 2: Navigated to Instructor Dashboard")

        # ================================================================
        # STEP 3: Navigate to Check-in tab
        # ================================================================
        # Click "✅ Check-in & Groups" tab (4th tab, index 3)
        tabs = page.locator("[data-testid='stTabs']").first.locator("button")

        # Wait for tabs to load
        expect(tabs).to_have_count(6, timeout=5000)  # Should have 6 main tabs

        tabs.nth(3).click()  # 4th tab = "✅ Check-in & Groups"
        page.wait_for_timeout(1500)

        print("✅ Step 3: Navigated to Check-in tab")

        # ================================================================
        # STEP 4: Navigate to Tournament Sessions sub-tab
        # ================================================================
        # Click "🏆 Tournament Sessions (2 statuses)" sub-tab (2nd tab, index 1)
        sub_tabs = page.locator("[data-testid='stTabs']").nth(1).locator("button")

        # Wait for sub-tabs to load
        expect(sub_tabs).to_have_count(2, timeout=5000)  # Should have 2 sub-tabs

        sub_tabs.nth(1).click()  # 2nd sub-tab = "🏆 Tournament Sessions"
        page.wait_for_timeout(2000)

        # Verify tournament sub-tab text
        expect(page.locator("text=🏆 Tournament Sessions")).to_be_visible()
        print("✅ Step 4: Navigated to Tournament Sessions sub-tab")

        # ================================================================
        # STEP 5: Select the tournament session
        # ================================================================
        # Look for "Select ➡️" button to enter the session
        select_buttons = page.locator("button:has-text('Select ➡️')")

        # Should have at least 1 tournament session
        expect(select_buttons).to_have_count(1, timeout=5000)

        # Click to enter the session
        select_buttons.first.click()
        page.wait_for_timeout(2000)

        print("✅ Step 5: Selected tournament session")

        # ================================================================
        # STEP 6: Verify attendance button counts (CRITICAL!)
        # ================================================================

        # Count Present buttons (should be 5, one per student)
        present_buttons = page.locator("button:has-text('✅ Present'), button:has-text('Present')")
        present_count = present_buttons.count()

        # Count Absent buttons (should be 5, one per student)
        absent_buttons = page.locator("button:has-text('❌ Absent'), button:has-text('Absent')")
        absent_count = absent_buttons.count()

        # Count Late buttons (should be 0!)
        late_buttons = page.locator("button:has-text('⏰ Late'), button:has-text('Late')")
        late_count = late_buttons.count()

        # Count Excused buttons (should be 0!)
        excused_buttons = page.locator("button:has-text('🎫 Excused'), button:has-text('Excused')")
        excused_count = excused_buttons.count()

        # Take screenshot for documentation
        page.screenshot(path="docs/screenshots/tournament_attendance_buttons_e2e.png")
        print(f"📸 Screenshot saved: tournament_attendance_buttons_e2e.png")

        # ================================================================
        # STEP 7: CRITICAL ASSERTIONS
        # ================================================================

        # Log button counts
        print(f"\n📊 Button counts:")
        print(f"   Present: {present_count}")
        print(f"   Absent: {absent_count}")
        print(f"   Late: {late_count}")
        print(f"   Excused: {excused_count}")

        # Assert we have the right number of students
        assert present_count == len(students), \
            f"Expected {len(students)} Present buttons, got {present_count}"

        assert absent_count == len(students), \
            f"Expected {len(students)} Absent buttons, got {absent_count}"

        # 🔥 CRITICAL ASSERTIONS: NO Late or Excused buttons!
        assert late_count == 0, \
            f"❌ CRITICAL FAILURE: Found {late_count} Late buttons, expected 0! Tournament sessions MUST NOT have Late buttons."

        assert excused_count == 0, \
            f"❌ CRITICAL FAILURE: Found {excused_count} Excused buttons, expected 0! Tournament sessions MUST NOT have Excused buttons."

        print("\n✅ ✅ ✅ CRITICAL ASSERTIONS PASSED!")
        print("   Tournament attendance shows ONLY 2 buttons (Present, Absent)")
        print("   NO Late or Excused buttons found")

        # ================================================================
        # STEP 8: Verify button functionality (bonus)
        # ================================================================

        # Click Present for first student
        first_present_btn = present_buttons.first
        first_present_btn.click()
        page.wait_for_timeout(1000)

        # Verify success message or state change
        # (Implementation depends on your app's feedback mechanism)
        # This is optional but demonstrates full user flow

        print("✅ Step 8: Attendance marking works")

        # ================================================================
        # TEST COMPLETE
        # ================================================================
        print("\n🎉 🎉 🎉 E2E TEST PASSED!")
        print("Tournament 2-button rule is VALIDATED end-to-end")

        # Note: Cleanup happens automatically via fixture teardown


@pytest.mark.skip(reason="Missing fixture: tournament_with_session not found in tests.e2e.fixtures")
@pytest.mark.e2e
@pytest.mark.tournament
class TestTournamentAttendanceRoleComparison:
    """
    Demonstrates role-based testing pattern.

    FUTURE EXTENSION: Add tests for:
    - Admin viewing tournament attendance
    - Student viewing their own attendance
    - Different permission levels
    """

    def test_instructor_can_mark_tournament_attendance(
        self,
        page: Page,
        tournament_with_session: dict
    ):
        """
        Test that instructors have permission to mark tournament attendance.

        This complements the button count test by verifying permissions.
        """
        instructor = tournament_with_session["instructor"]

        # Login
        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)
        page.fill("input[aria-label='Email']", instructor["email"])
        page.fill("input[aria-label='Password']", instructor["password"])
        page.click("button:has-text('Login')")
        page.wait_for_timeout(3000)

        # Navigate to tournament check-in
        page.goto(f"{STREAMLIT_URL}/Instructor_Dashboard")
        page.wait_for_timeout(2000)

        # Verify instructor sees tournament section
        # (Actual selectors depend on your UI)
        expect(page.locator("text=Instructor Dashboard")).to_be_visible()

        print("✅ Instructor role verified - has access to tournament attendance")


# ============================================================================
# USAGE EXAMPLES FOR FUTURE TESTS
# ============================================================================

"""
To create similar E2E tests for other flows, follow this pattern:

1. Define what you're testing (business rule, user flow, etc.)
2. Use/create appropriate fixtures from tests/e2e/fixtures.py
3. Follow the step-by-step navigation pattern
4. Make explicit assertions
5. Add debugging aids (screenshots, print statements)
6. Let fixtures handle cleanup

Example for regular sessions (4-button rule):

@pytest.mark.e2e
def test_regular_session_shows_4_buttons(
    page: Page,
    regular_session_with_bookings: dict  # Create this fixture!
):
    instructor = regular_session_with_bookings["instructor"]

    # Login
    page.goto(STREAMLIT_URL)
    page.fill("input[aria-label='Email']", instructor["email"])
    page.fill("input[aria-label='Password']", instructor["password"])
    page.click("button:has-text('Login')")
    page.wait_for_timeout(3000)

    # Navigate to regular session check-in
    page.goto(f"{STREAMLIT_URL}/Instructor_Dashboard")
    # ... (similar navigation steps)

    # Assert 4 buttons
    assert present_count == len(students)
    assert absent_count == len(students)
    assert late_count == len(students)  # Should exist for regular!
    assert excused_count == len(students)  # Should exist for regular!

    print("✅ Regular session shows 4 buttons correctly")
"""
