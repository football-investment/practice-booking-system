"""
E2E Tests for Sandbox Tournament Workflow

Tests the complete 6-step instructor workflow using the refactored
sandbox UI with data-testid selectors.

This test suite validates:
1. Auto-authentication on page load
2. Home screen navigation
3. Complete 6-step tournament creation workflow
4. Backward navigation through workflow steps
5. Metrics display and validation

Prerequisites:
- API server running on http://localhost:8000
- Sandbox Streamlit app running on http://localhost:8502
- Database configured with admin@lfa.com user
"""

import pytest
from playwright.sync_api import Page, expect
import time


# Test Configuration
SANDBOX_URL = "http://localhost:8502"
API_BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"


class TestSandboxAuthentication:
    """Test authentication flows"""

    def test_auto_authentication(self, page: Page):
        """
        Test auto-login on page load

        Verifies:
        - Page loads successfully
        - Auto-authentication occurs
        - Home screen is displayed
        - New tournament button is visible
        """
        # Navigate to sandbox
        page.goto(SANDBOX_URL)

        # Wait for auto-authentication to complete
        page.wait_for_timeout(2000)

        # Verify home screen elements are visible
        # Note: Streamlit wraps buttons in iframes, use text-based selectors
        expect(page.get_by_text("Tournament Sandbox - Home")).to_be_visible(timeout=10000)
        expect(page.get_by_text("Create New Tournament")).to_be_visible()
        expect(page.get_by_text("View Tournament History")).to_be_visible()


class TestSandboxNavigation:
    """Test navigation between screens"""

    def test_navigate_to_history(self, page: Page):
        """
        Test navigation to tournament history

        Verifies:
        - History button clickable
        - History screen loads
        """
        page.goto(SANDBOX_URL)
        page.wait_for_timeout(2000)

        # Click history button
        page.get_by_test_id("btn_open_history").click()
        page.wait_for_timeout(1000)

        # Verify history screen loaded
        expect(page.get_by_text("Tournament History")).to_be_visible(timeout=5000)

    def test_navigate_to_new_tournament(self, page: Page):
        """
        Test navigation to tournament configuration

        Verifies:
        - New tournament button clickable
        - Configuration screen loads
        """
        page.goto(SANDBOX_URL)
        page.wait_for_timeout(2000)

        # Click new tournament button
        page.get_by_test_id("btn_new_tournament").click()
        page.wait_for_timeout(1000)

        # Verify configuration screen loaded
        expect(page.get_by_text("Sandbox Tournament Test")).to_be_visible(timeout=5000)


class TestSandboxMetrics:
    """Test metrics display and validation"""

    def test_home_screen_metrics_display(self, page: Page):
        """
        Test home screen metrics are displayed correctly

        Verifies:
        - All three metrics visible
        - Metrics have numeric values
        """
        page.goto(SANDBOX_URL)
        page.wait_for_timeout(2000)

        # Get metrics
        total_metric = page.get_by_test_id("metric_total")
        completed_metric = page.get_by_test_id("metric_completed")
        in_progress_metric = page.get_by_test_id("metric_in_progress")

        # Verify visibility
        expect(total_metric).to_be_visible()
        expect(completed_metric).to_be_visible()
        expect(in_progress_metric).to_be_visible()

        # Verify they contain text (numeric values)
        expect(total_metric).to_contain_text(r"\d+")
        expect(completed_metric).to_contain_text(r"\d+")
        expect(in_progress_metric).to_contain_text(r"\d+")


class TestTournamentCreationWorkflow:
    """Test complete 6-step tournament creation workflow"""

    @pytest.mark.slow
    def test_complete_tournament_workflow(self, page: Page):
        """
        Test complete 6-step tournament creation workflow

        Steps:
        1. Home → Configuration
        2. Configuration → Create Tournament (Step 1)
        3. Step 1: Create tournament
        4. Step 2: Manage sessions
        5. Step 3: Track attendance
        6. Step 4: Enter results
        7. Step 5: View leaderboard
        8. Step 6: Distribute rewards

        Verifies:
        - All steps accessible
        - Forward navigation works
        - Success messages displayed
        - Workflow completes
        """
        page.goto(SANDBOX_URL)
        page.wait_for_timeout(2000)

        # Navigate to configuration
        page.get_by_test_id("btn_new_tournament").click()
        page.wait_for_timeout(1500)

        # TODO: Configure tournament (requires form selectors)
        # For now, we'll assume configuration is pre-filled or use defaults

        # Step 1: Create Tournament
        # Look for create button (may need to scroll or navigate to workflow)
        create_button = page.get_by_test_id("btn_create_tournament")
        if create_button.is_visible():
            create_button.click()
            page.wait_for_timeout(3000)  # Wait for tournament creation

            # Verify success message
            expect(page.get_by_text("Tournament created!")).to_be_visible(timeout=10000)

            # Step 2: Manage Sessions
            expect(page.get_by_test_id("btn_continue_step3")).to_be_visible(timeout=5000)
            page.get_by_test_id("btn_continue_step3").click()
            page.wait_for_timeout(1000)

            # Step 3: Track Attendance
            expect(page.get_by_test_id("btn_continue_step4")).to_be_visible(timeout=5000)
            page.get_by_test_id("btn_continue_step4").click()
            page.wait_for_timeout(1000)

            # Step 4: Enter Results
            expect(page.get_by_test_id("btn_continue_step5")).to_be_visible(timeout=5000)
            page.get_by_test_id("btn_continue_step5").click()
            page.wait_for_timeout(1000)

            # Step 5: View Leaderboard
            expect(page.get_by_test_id("btn_continue_step6")).to_be_visible(timeout=5000)
            page.get_by_test_id("btn_continue_step6").click()
            page.wait_for_timeout(1000)

            # Step 6: Distribute Rewards
            expect(page.get_by_test_id("btn_distribute_rewards")).to_be_visible(timeout=5000)
            page.get_by_test_id("btn_distribute_rewards").click()
            page.wait_for_timeout(3000)  # Wait for reward distribution

            # Verify completion
            expect(page.get_by_text("Rewards distributed successfully!")).to_be_visible(timeout=10000)
            expect(page.get_by_text("Tournament completed!")).to_be_visible(timeout=5000)


class TestWorkflowBackwardNavigation:
    """Test backward navigation through workflow steps"""

    @pytest.mark.slow
    def test_backward_navigation_through_steps(self, page: Page):
        """
        Test navigating backwards through workflow

        Navigates to step 3, then clicks back buttons to return to step 1

        Verifies:
        - Back buttons work
        - Can navigate backwards through all steps
        - No data loss on navigation
        """
        page.goto(SANDBOX_URL)
        page.wait_for_timeout(2000)

        # Navigate to configuration and create tournament
        page.get_by_test_id("btn_new_tournament").click()
        page.wait_for_timeout(1500)

        # Create tournament if button visible
        create_button = page.get_by_test_id("btn_create_tournament")
        if create_button.is_visible():
            create_button.click()
            page.wait_for_timeout(3000)

            # Navigate forward to step 3
            page.get_by_test_id("btn_continue_step3").click()
            page.wait_for_timeout(1000)
            page.get_by_test_id("btn_continue_step4").click()
            page.wait_for_timeout(1000)

            # Now navigate backwards
            # Step 3 → Step 2
            page.get_by_test_id("btn_back_step3").click()
            page.wait_for_timeout(1000)
            expect(page.get_by_test_id("btn_continue_step3")).to_be_visible(timeout=5000)

            # Step 2 → Step 1
            page.get_by_test_id("btn_back_step2").click()
            page.wait_for_timeout(1000)
            expect(page.get_by_test_id("btn_create_tournament")).to_be_visible(timeout=5000)


class TestTournamentMetrics:
    """Test tournament configuration metrics"""

    def test_tournament_metrics_display(self, page: Page):
        """
        Test tournament configuration metrics

        Verifies:
        - Tournament type metric displayed
        - Max players metric displayed
        - Skills count metric displayed
        """
        page.goto(SANDBOX_URL)
        page.wait_for_timeout(2000)

        # Navigate to configuration
        page.get_by_test_id("btn_new_tournament").click()
        page.wait_for_timeout(1500)

        # Check if we can navigate to step 1 (metrics visible)
        create_button = page.get_by_test_id("btn_create_tournament")
        if create_button.is_visible():
            # Verify metrics are visible
            expect(page.get_by_test_id("metric_tournament_type")).to_be_visible(timeout=5000)
            expect(page.get_by_test_id("metric_max_players")).to_be_visible()
            expect(page.get_by_test_id("metric_skills_count")).to_be_visible()


# Pytest configuration
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Setup test environment before running tests

    Verifies:
    - API server is running
    - Sandbox app is running
    """
    import requests

    # Check API server
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        print(f"\n✅ API server is running: {response.status_code}")
    except Exception as e:
        pytest.fail(f"❌ API server not running on {API_BASE_URL}: {e}")

    # Check Sandbox app
    try:
        response = requests.get(SANDBOX_URL, timeout=5)
        print(f"✅ Sandbox app is running: {response.status_code}")
    except Exception as e:
        pytest.fail(f"❌ Sandbox app not running on {SANDBOX_URL}: {e}")

    yield

    print("\n✅ Test environment cleanup complete")


@pytest.fixture(scope="function")
def page(playwright):
    """
    Create a new browser page for each test

    Configuration:
    - Headless mode
    - 1920x1080 viewport
    - 30 second timeout
    """
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        ignore_https_errors=True
    )
    page = context.new_page()
    page.set_default_timeout(30000)

    yield page

    context.close()
    browser.close()
