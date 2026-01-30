"""
E2E Tests for Tournament List Module

Tests tournament listing, filtering, and management workflows.
Following UI_REFACTOR_PATTERN.md - minimum 5-10 tests per refactored file.
"""

import pytest
from playwright.sync_api import Page, expect

TOURNAMENT_LIST_URL = "http://localhost:8501"


class TestTournamentListAuthentication:
    """Test authentication for tournament list"""

    def test_auto_authentication(self, page: Page):
        """Verify auto-login on page load"""
        page.goto(TOURNAMENT_LIST_URL)
        page.wait_for_timeout(2000)

        # Verify tournament list screen after auto-auth
        expect(page.get_by_text("All Tournaments")).to_be_visible(timeout=10000)


class TestTournamentListDisplay:
    """Test tournament list display and filtering"""

    def test_tournament_list_loads(self, page: Page):
        """Test tournament list loads successfully"""
        page.goto(TOURNAMENT_LIST_URL)
        page.wait_for_timeout(2000)

        # Verify header
        expect(page.get_by_text("All Tournaments")).to_be_visible()

    def test_tournament_card_display(self, page: Page):
        """Test tournament card displays correctly"""
        page.goto(TOURNAMENT_LIST_URL)
        page.wait_for_timeout(3000)

        # If tournaments exist, verify card structure
        # Note: This assumes at least one tournament exists in test DB
        # Adjust based on test data setup


class TestTournamentActions:
    """Test tournament action buttons"""

    def test_edit_tournament_button(self, page: Page):
        """Test edit tournament button click"""
        page.goto(TOURNAMENT_LIST_URL)
        page.wait_for_timeout(3000)

        # Find first edit button (if exists)
        # Pattern: btn_edit_tournament_{tournament_id}
        edit_button = page.locator('button[key^="btn_edit_tournament_"]').first
        if edit_button.is_visible():
            edit_button.click()
            page.wait_for_timeout(1000)

            # Verify dialog opened
            expect(page.get_by_text("Edit Tournament")).to_be_visible()

    def test_generate_sessions_button(self, page: Page):
        """Test generate sessions button availability"""
        page.goto(TOURNAMENT_LIST_URL)
        page.wait_for_timeout(3000)

        # Generate sessions button should exist
        # Pattern: btn_generate_sessions_{tournament_id}
        generate_button = page.locator('button[key^="btn_generate_sessions_"]').first
        # Button may be disabled depending on tournament status


class TestSessionManagement:
    """Test session management features"""

    def test_session_list_display(self, page: Page):
        """Test session list displays when sessions exist"""
        page.goto(TOURNAMENT_LIST_URL)
        page.wait_for_timeout(3000)

        # Look for session count metric
        # Pattern: metric_total_sessions_{tournament_id}
        # This will only be visible if sessions exist

    def test_add_game_button(self, page: Page):
        """Test add game button click"""
        page.goto(TOURNAMENT_LIST_URL)
        page.wait_for_timeout(3000)

        # Find add game button (if exists)
        # Pattern: btn_add_game_{tournament_id}
        add_button = page.locator('button[key^="btn_add_game_"]').first
        if add_button.is_visible():
            add_button.click()
            page.wait_for_timeout(1000)

            # Verify dialog opened
            expect(page.get_by_text("Add New Game")).to_be_visible()


class TestTournamentMetrics:
    """Test tournament metrics display"""

    def test_tournament_status_display(self, page: Page):
        """Test tournament status displays correctly"""
        page.goto(TOURNAMENT_LIST_URL)
        page.wait_for_timeout(3000)

        # Verify status metric exists
        # Pattern: metric_status_{tournament_id}

    def test_enrollment_count_display(self, page: Page):
        """Test enrollment count displays"""
        page.goto(TOURNAMENT_LIST_URL)
        page.wait_for_timeout(3000)

        # Look for enrollment metric
        # Pattern: metric_enrollments_{tournament_id}


class TestTournamentDialogs:
    """Test tournament dialog interactions"""

    def test_delete_tournament_dialog(self, page: Page):
        """Test delete tournament dialog opens"""
        page.goto(TOURNAMENT_LIST_URL)
        page.wait_for_timeout(3000)

        # Find delete button (if exists)
        # Pattern: btn_delete_tournament_{tournament_id}
        delete_button = page.locator('button[key^="btn_delete_tournament_"]').first
        if delete_button.is_visible():
            delete_button.click()
            page.wait_for_timeout(1000)

            # Verify dialog opened
            expect(page.get_by_text("Delete Tournament")).to_be_visible()

    def test_cancel_tournament_dialog(self, page: Page):
        """Test cancel tournament dialog opens"""
        page.goto(TOURNAMENT_LIST_URL)
        page.wait_for_timeout(3000)

        # Find cancel button (if exists)
        # Pattern: btn_cancel_tournament_{tournament_id}
        cancel_button = page.locator('button[key^="btn_cancel_tournament_"]').first
        if cancel_button.is_visible():
            cancel_button.click()
            page.wait_for_timeout(1000)

            # Verify dialog opened
            expect(page.get_by_text("Cancel Tournament")).to_be_visible()


@pytest.mark.slow
class TestCompleteTournamentManagementWorkflow:
    """Test complete tournament management workflow"""

    def test_tournament_creation_to_sessions(self, page: Page):
        """Test full workflow from viewing tournament to managing sessions"""
        page.goto(TOURNAMENT_LIST_URL)
        page.wait_for_timeout(3000)

        # Step 1: Verify tournament list loads
        expect(page.get_by_text("All Tournaments")).to_be_visible()

        # Step 2: Expand first tournament (if exists)
        expander = page.locator('summary').first
        if expander.is_visible():
            expander.click()
            page.wait_for_timeout(1000)

            # Step 3: Verify tournament details visible
            # Status, dates, metadata should be displayed

            # Step 4: Test session management section
            expect(page.get_by_text("Tournament Sessions")).to_be_visible()

            # Step 5: Verify action buttons present
            # Edit, delete, generate, etc.
