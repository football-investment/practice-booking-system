"""
End-to-End tests for Regular Session Check-in UI using Playwright.

Tests that regular sessions show ALL 4 attendance buttons
(Present, Absent, Late, Excused), in contrast to tournament sessions
which only show 2 buttons.

These tests validate the differentiation between regular and tournament workflows.
"""

import pytest
import os
from playwright.sync_api import Page, expect
# TODO: Fix missing imports - these don't exist in tests.e2e.conftest
# from tests.e2e.conftest import (
#     STREAMLIT_URL,
#     navigate_to_session_checkin,
#     take_screenshot
# )

STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")

# Skip entire module until helper functions are fixed
pytestmark = pytest.mark.skip(reason="Missing helper functions: navigate_to_session_checkin, take_screenshot not found in conftest")


# ============================================================================
# Regular Session: 4-Button Rule E2E Tests
# ============================================================================

@pytest.mark.e2e
@pytest.mark.ui
class TestRegularSessionCheckinE2E:
    """
    E2E tests for regular session check-in UI.

    **PREREQUISITES:**
    Before running these tests, ensure:
    1. Streamlit app is running at http://localhost:8501
    2. Database has a regular semester created
    3. Regular session exists with 2+ enrolled students
    4. Instructor user exists and is assigned to session
    5. Test credentials match environment variables
    """

    def test_regular_session_shows_all_4_attendance_buttons(self, instructor_page: Page):
        """
        Regular sessions show ALL 4 attendance buttons.

        This is the OPPOSITE of tournament sessions (which show only 2).

        Flow:
        1. Login as instructor
        2. Navigate to Session Check-in (regular)
        3. Select regular session
        4. Go to Step 2: Mark Attendance
        5. Verify ALL 4 buttons (Present, Absent, Late, Excused)

        Expected Result:
        - ✅ Present buttons visible
        - ✅ Absent buttons visible
        - ✅ Late buttons visible
        - ✅ Excused buttons visible
        """
        page = instructor_page

        # Navigate to regular session check-in
        navigate_to_session_checkin(page)

        # Wait for session list to load
        page.wait_for_selector("text=Session, text=Check-in", timeout=10000)

        # Select first regular session
        try:
            page.click("button:has-text('▶️ Start'), button:has-text('Select')", timeout=5000)
        except:
            # Alternative selector
            page.click("[data-testid='session-card']:first-child")

        # Wait for Step 2 (Attendance marking)
        page.wait_for_selector("text=Mark Attendance, text=Step 2", timeout=10000)

        # Take screenshot
        take_screenshot(page, "regular_session_attendance_page_e2e")

        # Get number of students
        num_students = page.locator("button:has-text('Present')").count()

        if num_students == 0:
            pytest.skip("No students enrolled in session - test cannot run")

        # Assert ALL 4 buttons per student
        present_count = page.locator("button:has-text('✅ Present'), button:has-text('Present')").count()
        absent_count = page.locator("button:has-text('❌ Absent'), button:has-text('Absent')").count()
        late_count = page.locator("button:has-text('⏰ Late'), button:has-text('Late')").count()
        excused_count = page.locator("button:has-text('🎫 Excused'), button:has-text('Excused')").count()

        assert present_count == num_students, \
            f"Expected {num_students} Present buttons, found {present_count}"

        assert absent_count == num_students, \
            f"Expected {num_students} Absent buttons, found {absent_count}"

        assert late_count == num_students, \
            f"Expected {num_students} Late buttons, found {late_count}"

        assert excused_count == num_students, \
            f"Expected {num_students} Excused buttons, found {excused_count}"

        # Take final screenshot showing 4-button layout
        take_screenshot(page, "regular_session_4_buttons_verified_e2e")

    def test_regular_session_shows_all_5_metrics(self, instructor_page: Page):
        """
        Regular session attendance summary shows ALL 5 metrics.

        Expected metrics:
        - ✅ Present
        - ❌ Absent
        - ⏰ Late
        - 🎫 Excused
        - ⏳ Pending
        """
        page = instructor_page

        navigate_to_session_checkin(page)
        page.wait_for_selector("text=Session", timeout=10000)

        # Select session
        try:
            page.click("button:has-text('▶️ Start'), button:has-text('Select')", timeout=5000)
        except:
            page.click("[data-testid='session-card']:first-child")

        page.wait_for_selector("text=Mark Attendance", timeout=10000)

        # Check for metric presence
        page_text = page.content()

        # Should contain all 5 metrics
        assert "Present" in page_text, "Should show Present metric"
        assert "Absent" in page_text, "Should show Absent metric"
        assert "Late" in page_text, "Should show Late metric"
        assert "Excused" in page_text, "Should show Excused metric"
        assert "Pending" in page_text or "pending" in page_text, "Should show Pending metric"

    def test_regular_session_late_button_works(self, instructor_page: Page):
        """
        E2E test: Clicking Late button marks student as late.

        This functionality should ONLY work in regular sessions,
        NOT in tournament sessions.
        """
        page = instructor_page

        navigate_to_session_checkin(page)
        page.wait_for_selector("text=Session", timeout=10000)

        # Select session
        try:
            page.click("button:has-text('▶️ Start')", timeout=5000)
        except:
            page.click("[data-testid='session-card']:first-child")

        page.wait_for_selector("text=Mark Attendance", timeout=10000)

        # Click first Late button
        late_buttons = page.locator("button:has-text('⏰ Late'), button:has-text('Late')")

        if late_buttons.count() == 0:
            pytest.skip("No Late buttons found - cannot test")

        late_buttons.first.click()

        # Wait for Streamlit rerun
        page.wait_for_timeout(1000)

        # Verify Late metric increased (if metrics are visible)
        # This is a basic smoke test - full assertion depends on resettable state

    def test_regular_session_excused_button_works(self, instructor_page: Page):
        """
        E2E test: Clicking Excused button marks student as excused.

        This functionality should ONLY work in regular sessions.
        """
        page = instructor_page

        navigate_to_session_checkin(page)
        page.wait_for_selector("text=Session", timeout=10000)

        # Select session
        try:
            page.click("button:has-text('▶️ Start')", timeout=5000)
        except:
            page.click("[data-testid='session-card']:first-child")

        page.wait_for_selector("text=Mark Attendance", timeout=10000)

        # Click first Excused button
        excused_buttons = page.locator("button:has-text('🎫 Excused'), button:has-text('Excused')")

        if excused_buttons.count() == 0:
            pytest.skip("No Excused buttons found - cannot test")

        excused_buttons.first.click()

        # Wait for Streamlit rerun
        page.wait_for_timeout(1000)


# ============================================================================
# Comparison Test: Regular vs Tournament
# ============================================================================

@pytest.mark.e2e
@pytest.mark.ui
class TestRegularVsTournamentComparison:
    """
    E2E tests comparing regular and tournament UIs.

    These tests validate that the two workflows are visually distinct.
    """

    def test_button_count_difference(self, instructor_page: Page):
        """
        Compare button counts: Regular (4) vs Tournament (2).

        This test navigates to both UIs and compares button counts.
        """
        page = instructor_page

        # === TEST 1: Regular Session (4 buttons) ===
        navigate_to_session_checkin(page)
        page.wait_for_selector("text=Session", timeout=10000)

        try:
            page.click("button:has-text('▶️ Start')", timeout=5000)
        except:
            page.click("[data-testid='session-card']:first-child")

        page.wait_for_selector("text=Mark Attendance", timeout=10000)

        # Count buttons
        regular_late_count = page.locator("button:has-text('Late')").count()
        regular_excused_count = page.locator("button:has-text('Excused')").count()

        # Regular should have Late and Excused buttons
        assert regular_late_count > 0, "Regular sessions should have Late buttons"
        assert regular_excused_count > 0, "Regular sessions should have Excused buttons"

        # Take screenshot
        take_screenshot(page, "regular_vs_tournament_regular_4_buttons")

        # === TEST 2: Tournament Session (2 buttons) ===
        # Navigate to tournament check-in
        from tests.e2e.conftest import navigate_to_tournament_checkin

        navigate_to_tournament_checkin(page)
        page.wait_for_selector("text=Tournament", timeout=10000)

        try:
            page.click("button:has-text('Select ➡️')", timeout=5000)
        except:
            pytest.skip("No tournament session available for comparison test")

        page.wait_for_selector("text=Mark Attendance", timeout=10000)

        # Count buttons
        tournament_late_count = page.locator("button:has-text('Late')").count()
        tournament_excused_count = page.locator("button:has-text('Excused')").count()

        # Tournament should NOT have Late or Excused buttons
        assert tournament_late_count == 0, \
            f"❌ CRITICAL: Tournament should have NO Late buttons, found {tournament_late_count}"

        assert tournament_excused_count == 0, \
            f"❌ CRITICAL: Tournament should have NO Excused buttons, found {tournament_excused_count}"

        # Take screenshot
        take_screenshot(page, "regular_vs_tournament_tournament_2_buttons")


# ============================================================================
# Regular Session Branding Tests
# ============================================================================

@pytest.mark.e2e
@pytest.mark.ui
class TestRegularSessionUIBranding:
    """Test regular session UI branding (NOT tournament)."""

    def test_regular_session_does_not_show_tournament_branding(self, instructor_page: Page):
        """Regular session check-in should NOT show tournament branding."""
        page = instructor_page

        navigate_to_session_checkin(page)
        page.wait_for_selector("text=Session", timeout=10000)

        # Check page text
        page_text = page.text_content("body")

        # Should NOT prominently feature "Tournament" in header
        # (Some references in docs/sidebar are OK)
        main_heading = page.locator("h1, h2, h3").first.text_content() if page.locator("h1, h2, h3").count() > 0 else ""

        assert "Tournament" not in main_heading, \
            "Regular session page should NOT have 'Tournament' in main heading"
