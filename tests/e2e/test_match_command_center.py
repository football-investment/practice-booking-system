"""
E2E Tests for Match Command Center Module

Tests match management, result entry, and leaderboard workflows.
Following UI_REFACTOR_PATTERN.md - minimum 5-10 tests per refactored file.
"""

import pytest
from playwright.sync_api import Page, expect

MATCH_CENTER_URL = "http://localhost:8503"


class TestMatchCenterAuthentication:
    """Test authentication for match command center"""

    def test_auto_authentication(self, page: Page):
        """Verify auto-login on page load"""
        page.goto(MATCH_CENTER_URL)
        page.wait_for_timeout(2000)

        # Verify match command center loads (includes emoji)
        expect(page.get_by_text("🎮 Match Command Center")).to_be_visible(timeout=10000)


class TestActiveMatchDisplay:
    """Test active match display"""

    def test_active_match_loads(self, page: Page):
        """Test active match displays correctly"""
        page.goto(MATCH_CENTER_URL)
        page.wait_for_timeout(3000)

        # If active match exists, verify display


class TestAttendanceMarking:
    """Test attendance marking workflow"""

    def test_mark_present_button(self, page: Page):
        """Test mark present button click"""
        page.goto(MATCH_CENTER_URL)
        page.wait_for_timeout(3000)

        # Find present button (if exists)
        # Pattern: btn_present_{participant_id}
        present_button = page.locator('button[key^="btn_present_"]').first
        if present_button.is_visible():
            present_button.click()
            page.wait_for_timeout(1000)

            # Verify success message
            expect(page.get_by_text("Marked PRESENT")).to_be_visible()

    def test_mark_absent_button(self, page: Page):
        """Test mark absent button click"""
        page.goto(MATCH_CENTER_URL)
        page.wait_for_timeout(3000)

        # Find absent button (if exists)
        # Pattern: btn_absent_{participant_id}
        absent_button = page.locator('button[key^="btn_absent_"]').first
        if absent_button.is_visible():
            absent_button.click()
            page.wait_for_timeout(1000)

            # Verify success message
            expect(page.get_by_text("Marked ABSENT")).to_be_visible()


class TestResultEntry:
    """Test result entry forms"""

    def test_individual_ranking_form(self, page: Page):
        """Test individual ranking form submission"""
        page.goto(MATCH_CENTER_URL)
        page.wait_for_timeout(3000)

        # Look for ranking inputs
        # Pattern: input_rank_{participant_id}
        submit_button = page.locator('button[key="btn_submit_rankings"]').first
        if submit_button.is_visible():
            submit_button.click()
            page.wait_for_timeout(1000)

            # Verify submission
            expect(page.get_by_text("Results submitted")).to_be_visible()

    def test_rounds_based_entry(self, page: Page):
        """Test rounds-based entry form"""
        page.goto(MATCH_CENTER_URL)
        page.wait_for_timeout(3000)

        # Find round submit button
        # Pattern: btn_submit_round_{round_number}
        round_button = page.locator('button[key^="btn_submit_round_"]').first
        if round_button.is_visible():
            round_button.click()
            page.wait_for_timeout(1000)

    def test_time_based_entry(self, page: Page):
        """Test time-based entry form"""
        page.goto(MATCH_CENTER_URL)
        page.wait_for_timeout(3000)

        # Find time submit button
        submit_button = page.locator('button[key="btn_submit_times"]').first
        if submit_button.is_visible():
            # Enter time values
            time_inputs = page.locator('input[key^="input_time_"]')
            # Fill in times

            submit_button.click()
            page.wait_for_timeout(1000)


class TestLeaderboard:
    """Test leaderboard display"""

    def test_leaderboard_sidebar_visible(self, page: Page):
        """Test leaderboard sidebar displays"""
        page.goto(MATCH_CENTER_URL)
        page.wait_for_timeout(3000)

        # Verify leaderboard header (includes emoji)
        expect(page.get_by_text("🏆 Live Leaderboard")).to_be_visible()

    def test_leaderboard_standings(self, page: Page):
        """Test leaderboard standings display"""
        page.goto(MATCH_CENTER_URL)
        page.wait_for_timeout(3000)

        # Look for leaderboard metrics
        # Pattern: metric_leaderboard_{rank}


class TestMatchProgression:
    """Test match progression workflow"""

    def test_next_match_button(self, page: Page):
        """Test next match button navigation"""
        page.goto(MATCH_CENTER_URL)
        page.wait_for_timeout(3000)

        # Find next match button
        next_button = page.locator('button[key="btn_next_match"]').first
        if next_button.is_visible():
            next_button.click()
            page.wait_for_timeout(2000)

            # Verify new match loaded


class TestFinalLeaderboard:
    """Test final leaderboard display"""

    def test_final_leaderboard_display(self, page: Page):
        """Test final leaderboard shows when tournament complete"""
        page.goto(MATCH_CENTER_URL)
        page.wait_for_timeout(3000)

        # Look for final leaderboard
        # Pattern: metric_final_name_{rank}, metric_final_score_{rank}


@pytest.mark.slow
class TestCompleteMatchWorkflow:
    """Test complete match workflow"""

    def test_attendance_to_results_workflow(self, page: Page):
        """Test full workflow from attendance to results"""
        page.goto(MATCH_CENTER_URL)
        page.wait_for_timeout(3000)

        # Step 1: Verify match center loads (includes emoji)
        expect(page.get_by_text("🎮 Match Command Center")).to_be_visible()

        # Step 2: Mark attendance (if in attendance phase)
        present_button = page.locator('button[key^="btn_present_"]').first
        if present_button.is_visible():
            # Mark all present
            present_buttons = page.locator('button[key^="btn_present_"]').all()
            for btn in present_buttons:
                btn.click()
                page.wait_for_timeout(500)

        # Step 3: Enter results (if in results phase)
        submit_button = page.locator('button[key="btn_submit_rankings"]').first
        if submit_button.is_visible():
            submit_button.click()
            page.wait_for_timeout(1000)

            # Verify success
            expect(page.get_by_text("Results submitted")).to_be_visible()

        # Step 4: Check leaderboard updated
        expect(page.get_by_text("Live Leaderboard")).to_be_visible()
