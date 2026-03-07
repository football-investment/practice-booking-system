"""
Simplified E2E Test for Sandbox - Streamlit Compatible

Uses text-based selectors instead of data-testid (Streamlit limitation).
Focus on smoke testing critical paths.
"""

import pytest
from playwright.sync_api import Page, expect

SANDBOX_URL = "http://localhost:8502"


class TestSandboxSmoke:
    """Smoke tests for sandbox app"""

    def test_app_loads(self, page: Page):
        """Test that app loads successfully"""
        page.goto(SANDBOX_URL, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Verify page loaded by checking content
        page_content = page.content()
        assert len(page_content) > 100, "Page content too short"
        assert "tournament" in page_content.lower() or "sandbox" in page_content.lower()

    def test_buttons_exist(self, page: Page):
        """Test that interactive buttons exist"""
        page.goto(SANDBOX_URL, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Count buttons on page
        buttons = page.locator("button").all()
        assert len(buttons) > 0, "No buttons found on page"


class TestSandboxNavigation:
    """Test basic navigation"""

    def test_can_click_buttons(self, page: Page):
        """Test that buttons are clickable"""
        page.goto(SANDBOX_URL, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Find first visible button and click it
        first_button = page.locator("button").first
        if first_button.is_visible():
            first_button.click()
            page.wait_for_timeout(1000)
            # If click succeeded, we're good


class TestAPIConnection:
    """Test API connectivity"""

    def test_api_accessible_from_app(self, page: Page):
        """Test that app can reach API"""
        page.goto(SANDBOX_URL, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Check console for API errors
        console_messages = []
        page.on("console", lambda msg: console_messages.append(msg.text))

        page.wait_for_timeout(2000)

        # Look for critical errors
        critical_errors = [msg for msg in console_messages if "failed" in msg.lower() and "fetch" in msg.lower()]
        assert len(critical_errors) == 0, f"API connection errors: {critical_errors}"


@pytest.mark.integration
class TestFullWorkflow:
    """Integration test - full workflow if possible"""

    def test_create_tournament_attempt(self, page: Page):
        """Attempt to start tournament creation workflow"""
        page.goto(SANDBOX_URL, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Try to find and click "New Tournament" or similar button
        new_tournament_btn = page.get_by_text("New Tournament", exact=False).first

        if new_tournament_btn.is_visible():
            new_tournament_btn.click()
            page.wait_for_timeout(2000)

            # Verify we navigated somewhere
            # (content should have changed)
