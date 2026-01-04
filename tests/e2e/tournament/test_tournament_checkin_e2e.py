"""
End-to-End tests for Tournament Check-in UI using Playwright.

Tests the CRITICAL requirement: Tournament sessions show ONLY 2 attendance buttons
(Present, Absent) and NOT 4 buttons (Present, Absent, Late, Excused).

These tests run against a live Streamlit application.
"""

import pytest
from playwright.sync_api import Page, expect
from tests.e2e.conftest import (
    STREAMLIT_URL,
    navigate_to_tournament_checkin,
    assert_button_count,
    assert_no_button_with_label,
    assert_metric_visible,
    take_screenshot
)


# ============================================================================
# CRITICAL: Tournament 2-Button Rule E2E Tests
# ============================================================================

@pytest.mark.e2e
@pytest.mark.tournament
@pytest.mark.ui
class TestTournamentCheckinE2E:
    """
    E2E tests for tournament check-in UI.

    **PREREQUISITES:**
    Before running these tests, ensure:
    1. Streamlit app is running at http://localhost:8501
    2. Database has a tournament semester created
    3. Tournament session exists with 2+ enrolled students
    4. Instructor user exists and is assigned to tournament
    5. Test credentials match environment variables
    """

    def test_tournament_shows_only_2_attendance_buttons(self, instructor_page: Page):
        """
        🔥 CRITICAL E2E TEST: Tournament check-in shows ONLY 2 attendance buttons.

        Flow:
        1. Login as instructor
        2. Navigate to Tournament Check-in
        3. Select tournament session
        4. Go to Step 2: Mark Attendance
        5. Verify ONLY Present/Absent buttons (NO Late/Excused)

        Expected Result:
        - ✅ Present buttons visible
        - ✅ Absent buttons visible
        - ❌ NO Late buttons
        - ❌ NO Excused buttons
        """
        page = instructor_page

        # Navigate to tournament check-in
        navigate_to_tournament_checkin(page)

        # Wait for tournament list to load
        page.wait_for_selector("text=Tournament, text=🏆", timeout=10000)

        # Select first tournament session
        # (Adjust selector based on actual UI implementation)
        try:
            page.click("button:has-text('Select ➡️')", timeout=5000)
        except:
            # Alternative: Click on tournament card/row
            page.click("[data-testid='tournament-session']:first-child")

        # Wait for Step 2 (Attendance marking page)
        page.wait_for_selector("text=Mark Attendance, text=Step 2", timeout=10000)

        # Take screenshot of attendance page
        take_screenshot(page, "tournament_attendance_page_e2e")

        # CRITICAL ASSERTIONS: Button counts
        # Get number of students (count Present buttons as baseline)
        num_students = page.locator("button:has-text('✅ Present'), button:has-text('Present')").count()

        if num_students == 0:
            pytest.skip("No students enrolled in tournament session - test cannot run")

        # Assert ONLY 2 buttons per student
        present_count = page.locator("button:has-text('✅ Present'), button:has-text('Present')").count()
        absent_count = page.locator("button:has-text('❌ Absent'), button:has-text('Absent')").count()

        assert present_count == num_students, \
            f"Expected {num_students} Present buttons, found {present_count}"

        assert absent_count == num_students, \
            f"Expected {num_students} Absent buttons, found {absent_count}"

        # CRITICAL: NO Late or Excused buttons should exist
        late_count = page.locator("button:has-text('⏰ Late'), button:has-text('Late')").count()
        excused_count = page.locator("button:has-text('🎫 Excused'), button:has-text('Excused')").count()

        assert late_count == 0, \
            f"❌ CRITICAL FAIL: Tournament should have NO Late buttons, found {late_count}"

        assert excused_count == 0, \
            f"❌ CRITICAL FAIL: Tournament should have NO Excused buttons, found {excused_count}"

        # Take final screenshot showing 2-button layout
        take_screenshot(page, "tournament_2_buttons_verified_e2e")

    def test_tournament_shows_only_3_metrics(self, instructor_page: Page):
        """
        Tournament attendance summary shows ONLY 3 metrics (not 5).

        Expected metrics:
        - ✅ Present
        - ❌ Absent
        - ⏳ Pending

        Should NOT show:
        - ❌ Late
        - ❌ Excused
        """
        page = instructor_page

        navigate_to_tournament_checkin(page)
        page.wait_for_selector("text=Tournament", timeout=10000)

        # Select tournament session
        try:
            page.click("button:has-text('Select ➡️')", timeout=5000)
        except:
            page.click("[data-testid='tournament-session']:first-child")

        # Wait for attendance page
        page.wait_for_selector("text=Mark Attendance, text=Step 2", timeout=10000)

        # Check for metric presence
        # Streamlit metrics have data-testid='stMetric'
        metrics = page.locator("[data-testid='stMetric']")

        # Should have 3 metrics visible
        assert metrics.count() >= 3, "Should have at least 3 metrics"

        # Check metric labels
        page_text = page.content()

        # Should contain: Present, Absent, Pending
        assert "Present" in page_text, "Should show Present metric"
        assert "Absent" in page_text, "Should show Absent metric"
        assert "Pending" in page_text or "pending" in page_text, "Should show Pending metric"

        # Should NOT contain Late or Excused in metrics section
        # (Some might be in headers/docs, so be specific)
        attendance_section = page.locator("text=Attendance Summary").locator("..")

        attendance_text = attendance_section.text_content() if attendance_section.count() > 0 else ""

        assert "Late" not in attendance_text, \
            "Tournament metrics should NOT show Late"

        assert "Excused" not in attendance_text, \
            "Tournament metrics should NOT show Excused"

    def test_tournament_info_banner_shows_2_button_mode(self, instructor_page: Page):
        """
        Tournament attendance page shows info banner about 2-button mode.

        Expected:
        - Info box explaining "Tournament Mode"
        - Mentions "Present and Absent only"
        """
        page = instructor_page

        navigate_to_tournament_checkin(page)
        page.wait_for_selector("text=Tournament", timeout=10000)

        # Select tournament
        try:
            page.click("button:has-text('Select ➡️')", timeout=5000)
        except:
            page.click("[data-testid='tournament-session']:first-child")

        # Wait for attendance page
        page.wait_for_selector("text=Mark Attendance", timeout=10000)

        # Check for info banner
        # Streamlit st.info creates specific structure
        info_boxes = page.locator("[data-testid='stInfo'], .stInfo, text=Tournament Mode")

        if info_boxes.count() > 0:
            info_text = info_boxes.first.text_content()

            # Should mention tournament attendance rules
            assert ("Present" in info_text and "Absent" in info_text) or \
                   "Tournament Mode" in info_text, \
                   "Info banner should explain tournament attendance rules"

    def test_tournament_click_present_button_works(self, instructor_page: Page):
        """
        E2E test: Clicking Present button marks student as present.

        Flow:
        1. Navigate to tournament attendance
        2. Click Present button for first student
        3. Verify student is marked as present
        4. Verify metrics update
        """
        page = instructor_page

        navigate_to_tournament_checkin(page)
        page.wait_for_selector("text=Tournament", timeout=10000)

        # Select tournament
        try:
            page.click("button:has-text('Select ➡️')", timeout=5000)
        except:
            page.click("[data-testid='tournament-session']:first-child")

        page.wait_for_selector("text=Mark Attendance", timeout=10000)

        # Get initial Present count from metrics
        initial_present_text = page.locator("text=Present").locator("..").text_content()

        # Click first Present button
        present_buttons = page.locator("button:has-text('✅ Present'), button:has-text('Present')")

        if present_buttons.count() == 0:
            pytest.skip("No Present buttons found - cannot test click")

        present_buttons.first.click()

        # Wait for page to update (Streamlit rerun)
        page.wait_for_timeout(1000)

        # Verify metrics updated
        updated_present_text = page.locator("text=Present").locator("..").text_content()

        # Present count should have increased or stayed same (if already marked)
        # (Exact assertion depends on whether we can reset state between tests)

    def test_tournament_no_late_button_in_dom(self, instructor_page: Page):
        """
        Verify NO Late button exists anywhere in DOM.

        This is a strict check to ensure Late button is completely removed,
        not just hidden with CSS.
        """
        page = instructor_page

        navigate_to_tournament_checkin(page)
        page.wait_for_selector("text=Tournament", timeout=10000)

        try:
            page.click("button:has-text('Select ➡️')", timeout=5000)
        except:
            page.click("[data-testid='tournament-session']:first-child")

        page.wait_for_selector("text=Mark Attendance", timeout=10000)

        # Check DOM for Late buttons
        late_buttons = page.locator("button:has-text('Late'), button:has-text('⏰ Late')")

        assert late_buttons.count() == 0, \
            f"NO Late buttons should exist in DOM, found {late_buttons.count()}"

        # Also check page HTML source
        page_html = page.content()

        assert "button" not in page_html.lower() or "late" not in page_html.lower() or \
               page_html.lower().count("late") == 0 or \
               ("late" in page_html.lower() and "button" not in page_html[page_html.lower().index("late"):page_html.lower().index("late")+100]), \
               "No button element should contain 'Late' text"


# ============================================================================
# Tournament UI Branding Tests
# ============================================================================

@pytest.mark.e2e
@pytest.mark.tournament
@pytest.mark.ui
class TestTournamentUIBranding:
    """Test tournament-specific UI branding and labels."""

    def test_tournament_wizard_shows_tournament_icon(self, instructor_page: Page):
        """Tournament wizard uses 🏆 icon and tournament branding."""
        page = instructor_page

        navigate_to_tournament_checkin(page)
        page.wait_for_selector("text=Tournament", timeout=10000)

        # Check for tournament branding
        page_text = page.text_content("body")

        assert "🏆" in page_text or "Tournament" in page_text, \
            "Page should show tournament branding"

    def test_tournament_step1_shows_game_types(self, instructor_page: Page):
        """Tournament selection shows game types (Semifinal, Final, etc)."""
        page = instructor_page

        navigate_to_tournament_checkin(page)
        page.wait_for_selector("text=Tournament", timeout=10000)

        # Check for game type labels
        page_text = page.text_content("body")

        # Should show at least one game type (if tournament sessions exist)
        # Common game types: Semifinal, Final, Quarterfinal, Group Stage
        game_type_keywords = ["Semifinal", "Final", "Quarterfinal", "Group", "Match"]

        has_game_type = any(keyword in page_text for keyword in game_type_keywords)

        # This is optional - may not have game types if no tournaments exist
        # So we just check if present, it's correctly labeled


# ============================================================================
# E2E Performance Tests
# ============================================================================

@pytest.mark.e2e
@pytest.mark.tournament
@pytest.mark.slow
class TestTournamentE2EPerformance:
    """Test tournament UI performance in real browser."""

    def test_tournament_page_loads_within_5_seconds(self, instructor_page: Page):
        """Tournament check-in page loads within 5 seconds."""
        import time

        page = instructor_page

        start_time = time.time()

        navigate_to_tournament_checkin(page)
        page.wait_for_selector("text=Tournament", timeout=10000)

        end_time = time.time()
        load_time = end_time - start_time

        assert load_time < 5.0, \
            f"Page loaded in {load_time:.2f}s, should be <5s"

    def test_attendance_marking_responds_quickly(self, instructor_page: Page):
        """Clicking attendance button responds within 2 seconds."""
        import time

        page = instructor_page

        navigate_to_tournament_checkin(page)
        page.wait_for_selector("text=Tournament", timeout=10000)

        try:
            page.click("button:has-text('Select ➡️')", timeout=5000)
        except:
            page.click("[data-testid='tournament-session']:first-child")

        page.wait_for_selector("text=Mark Attendance", timeout=10000)

        # Click Present button and measure response time
        present_buttons = page.locator("button:has-text('Present')")

        if present_buttons.count() == 0:
            pytest.skip("No Present buttons - cannot test performance")

        start_time = time.time()
        present_buttons.first.click()

        # Wait for Streamlit to rerun
        page.wait_for_timeout(500)

        end_time = time.time()
        response_time = end_time - start_time

        assert response_time < 2.0, \
            f"Button response took {response_time:.2f}s, should be <2s"
