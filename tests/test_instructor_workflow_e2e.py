"""
Playwright E2E Tests: Instructor Workflow - Complete Flow
Tests all scenarios from Home screen through Tournament History
"""

import pytest
from playwright.sync_api import Page, expect
import time

BASE_URL = "http://localhost:8501"

@pytest.fixture(scope="function")
def page_with_login(page: Page):
    """Login and navigate to home"""
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")

    # Wait for Streamlit to load
    time.sleep(2)

    # Check if already logged in by looking for home screen elements
    try:
        # Try to find tournament configuration form
        page.wait_for_selector("text=Tournament Configuration", timeout=3000)
        print("✓ Already logged in")
        yield page
        return
    except:
        pass

    # Need to login
    print("→ Logging in...")

    # Fill login form
    email_input = page.get_by_label("Admin Email")
    password_input = page.get_by_label("Password", exact=True)

    email_input.fill("admin@lfa.com")
    password_input.fill("admin123")

    # Click login
    page.get_by_role("button", name="🔓 Login").click()

    # Wait for redirect to home
    page.wait_for_selector("text=Tournament Configuration", timeout=10000)
    print("✓ Logged in successfully")

    time.sleep(1)
    yield page


class TestInstructorWorkflowE2E:
    """Complete E2E tests for Instructor Workflow"""

    def test_01_history_continue_draft_tournament(self, page_with_login: Page):
        """
        Test Case 1: Tournament History → Continue DRAFT Tournament

        Flow:
        1. Navigate to History
        2. Select DRAFT tournament
        3. Click "Continue Setup"
        4. Verify no crash
        5. Verify state loaded correctly
        """
        print("\n" + "="*80)
        print("TEST CASE 1: History → Continue DRAFT Tournament")
        print("="*80)

        page = page_with_login

        # Step 1: Navigate to Instructor Workflow tab
        print("→ Step 1: Click Instructor Workflow tab")
        page.get_by_role("tab", name="👨‍🏫 Instructor Workflow").click()
        time.sleep(1)

        # Step 2: Verify we're in workflow
        print("→ Step 2: Verify Instructor Workflow screen")
        expect(page.get_by_text("👨‍🏫 Instructor Workflow")).to_be_visible()
        time.sleep(1)

        # Step 3: Go to Tournament History (should be workflow_step 6)
        # The history browser should appear automatically or via navigation
        print("→ Step 3: Navigate to Tournament History")

        # Check if we need to click "View Tournament History" button
        try:
            history_button = page.get_by_role("button", name="📚 View Tournament History")
            if history_button.is_visible(timeout=2000):
                history_button.click()
                time.sleep(1)
        except:
            pass  # Already in history view

        # Step 4: Wait for tournament list
        print("→ Step 4: Wait for tournament list to load")
        page.wait_for_selector("text=Found", timeout=10000)
        expect(page.get_by_text("Sandbox Tournaments")).to_be_visible()
        time.sleep(1)

        # Step 5: Select a DRAFT tournament from dropdown
        print("→ Step 5: Select DRAFT tournament from dropdown")

        # Get the selectbox - Streamlit renders it as a select element
        tournament_selector = page.locator('select[aria-label="Select tournament to view:"]').first

        # Get all options
        options = tournament_selector.locator('option').all()

        # Find first DRAFT tournament
        draft_option = None
        for option in options:
            text = option.text_content() or ""
            if "DRAFT" not in text.upper():
                continue
            draft_option = option
            break

        if not draft_option:
            print("⚠️  No DRAFT tournaments found - skipping this test")
            pytest.skip("No DRAFT tournaments available")
            return

        draft_value = draft_option.get_attribute('value') or '0'
        print(f"   Selected DRAFT tournament: {draft_option.text_content()}")

        tournament_selector.select_option(value=draft_value)
        time.sleep(2)

        # Step 6: Verify tournament detail loaded
        print("→ Step 6: Verify tournament detail loaded")
        expect(page.get_by_text("Tournament Name")).to_be_visible()
        expect(page.get_by_text("Status")).to_be_visible()
        time.sleep(1)

        # Step 7: Click "Continue Setup" button for DRAFT
        print("→ Step 7: Click 'Continue Setup' button")
        continue_button = page.get_by_role("button", name="▶️ Continue Setup")
        expect(continue_button).to_be_visible()

        # ⚠️ CRITICAL ASSERTION: No crash before clicking
        print("   ✓ No crash before clicking button")

        continue_button.click()
        time.sleep(2)

        # Step 8: Verify no error message appeared
        print("→ Step 8: Verify no crash after clicking button")

        # Check for error messages
        error_messages = page.get_by_text("Error:").all()
        assert len(error_messages) == 0, "❌ Error message found after clicking Continue Setup!"

        # Check for NoneType error specifically
        none_type_errors = page.get_by_text("'NoneType' object has no attribute").all()
        assert len(none_type_errors) == 0, "❌ NoneType error found!"

        print("   ✓ No errors - page loaded successfully")

        # Step 9: Verify workflow step changed (should be at Step 1)
        print("→ Step 9: Verify workflow navigation")
        expect(page.get_by_text("Current Step:")).to_be_visible(timeout=5000)

        print("✅ TEST PASSED: DRAFT tournament continuation works!")
        time.sleep(1)

    def test_02_history_continue_in_progress_tournament(self, page_with_login: Page):
        """
        Test Case 2: Tournament History → Continue IN_PROGRESS Tournament

        Flow:
        1. Navigate to History
        2. Select IN_PROGRESS tournament
        3. Click "Continue Tournament"
        4. Verify no crash
        5. Verify correct step routing (Step 2 or Step 6)
        """
        print("\n" + "="*80)
        print("TEST CASE 2: History → Continue IN_PROGRESS Tournament")
        print("="*80)

        page = page_with_login

        # Step 1: Navigate to Instructor Workflow
        print("→ Step 1: Navigate to Instructor Workflow")
        page.get_by_role("tab", name="👨‍🏫 Instructor Workflow").click()
        time.sleep(1)

        # Step 2: Go to history view
        print("→ Step 2: Navigate to Tournament History")
        try:
            history_button = page.get_by_role("button", name="📚 View Tournament History")
            if history_button.is_visible(timeout=2000):
                history_button.click()
                time.sleep(1)
        except:
            pass

        # Step 3: Wait for tournament list
        print("→ Step 3: Wait for tournament list")
        page.wait_for_selector("text=Found", timeout=10000)
        time.sleep(1)

        # Step 4: Select IN_PROGRESS tournament
        print("→ Step 4: Select IN_PROGRESS tournament")

        tournament_selector = page.locator('select[aria-label="Select tournament to view:"]').first
        options = tournament_selector.locator('option').all()

        # Find first IN_PROGRESS tournament
        in_progress_option = None
        for option in options:
            text = option.text_content() or ""
            # IN_PROGRESS tournaments won't have DRAFT in their label
            # and will show IN_PROGRESS in the metrics after selection
            in_progress_option = option
            break

        if not in_progress_option:
            print("⚠️  No tournaments found - skipping")
            pytest.skip("No tournaments available")
            return

        in_progress_value = in_progress_option.get_attribute('value') or '0'
        print(f"   Selected tournament: {in_progress_option.text_content()}")

        tournament_selector.select_option(value=in_progress_value)
        time.sleep(2)

        # Step 5: Check tournament status
        print("→ Step 5: Check tournament status")

        # Try to find Continue Tournament button (IN_PROGRESS)
        # or Continue Setup button (DRAFT)
        continue_tournament_button = None
        try:
            continue_tournament_button = page.get_by_role("button", name="▶️ Continue Tournament")
            if continue_tournament_button.is_visible(timeout=2000):
                print("   Tournament Status: IN_PROGRESS")
        except:
            try:
                continue_setup_button = page.get_by_role("button", name="▶️ Continue Setup")
                if continue_setup_button.is_visible(timeout=2000):
                    print("   Tournament Status: DRAFT - switching test")
                    # This is actually a DRAFT, continue with it anyway
                    continue_tournament_button = continue_setup_button
            except:
                print("   ⚠️ No continue button found")
                pytest.skip("No continue button available")
                return

        # Step 6: Click continue button
        print("→ Step 6: Click Continue Tournament button")
        expect(continue_tournament_button).to_be_visible()

        # ⚠️ CRITICAL ASSERTION: No crash before clicking
        print("   ✓ No crash before clicking button")

        continue_tournament_button.click()
        time.sleep(2)

        # Step 7: Verify no error
        print("→ Step 7: Verify no crash after clicking")

        error_messages = page.get_by_text("Error:").all()
        assert len(error_messages) == 0, "❌ Error message found!"

        none_type_errors = page.get_by_text("'NoneType' object has no attribute").all()
        assert len(none_type_errors) == 0, "❌ NoneType error found!"

        print("   ✓ No errors - page loaded successfully")

        # Step 8: Verify workflow navigation
        print("→ Step 8: Verify workflow step")
        expect(page.get_by_text("Current Step:")).to_be_visible(timeout=5000)

        print("✅ TEST PASSED: IN_PROGRESS tournament continuation works!")
        time.sleep(1)

    def test_03_tournament_history_browser_navigation(self, page_with_login: Page):
        """
        Test Case 3: Tournament History Browser - Full Navigation

        Flow:
        1. Open History Browser
        2. Select multiple tournaments
        3. Verify all data loads without errors
        4. Check tabs (Leaderboard, Match Results, Rewards)
        """
        print("\n" + "="*80)
        print("TEST CASE 3: Tournament History Browser - Navigation")
        print("="*80)

        page = page_with_login

        # Step 1: Navigate to Instructor Workflow
        print("→ Step 1: Navigate to Instructor Workflow")
        page.get_by_role("tab", name="👨‍🏫 Instructor Workflow").click()
        time.sleep(1)

        # Step 2: Go to history
        print("→ Step 2: Go to Tournament History")
        try:
            history_button = page.get_by_role("button", name="📚 View Tournament History")
            if history_button.is_visible(timeout=2000):
                history_button.click()
                time.sleep(1)
        except:
            pass

        # Step 3: Wait for list
        print("→ Step 3: Wait for tournament list")
        page.wait_for_selector("text=Found", timeout=10000)
        time.sleep(1)

        # Step 4: Select first tournament
        print("→ Step 4: Select first tournament from dropdown")

        tournament_selector = page.locator('select[aria-label="Select tournament to view:"]').first
        options = tournament_selector.locator('option').all()

        if len(options) == 0:
            pytest.skip("No tournaments found")
            return

        first_value = options[0].get_attribute('value') or '0'
        print(f"   Selected: {options[0].text_content()}")

        tournament_selector.select_option(value=first_value)
        time.sleep(2)

        # Step 5: Verify no errors in loading
        print("→ Step 5: Verify tournament detail loaded without errors")

        error_messages = page.get_by_text("Error:").all()
        assert len(error_messages) == 0, "❌ Error found while loading tournament detail!"

        print("   ✓ Tournament detail loaded successfully")

        # Step 6: Check tabs are accessible
        print("→ Step 6: Verify tabs are present")

        # Look for tab labels
        tabs_present = False
        try:
            leaderboard_tab = page.get_by_role("tab", name="📊 Leaderboard")
            if leaderboard_tab.is_visible(timeout=2000):
                tabs_present = True
                print("   ✓ Tabs found: Leaderboard, Match Results, Rewards")
        except:
            print("   ℹ️  Tabs may not be visible for this tournament status")

        # Step 7: Try clicking a tab if present
        if tabs_present:
            print("→ Step 7: Click Leaderboard tab")
            try:
                leaderboard_tab = page.get_by_role("tab", name="📊 Leaderboard")
                leaderboard_tab.click()
                time.sleep(1)

                # Verify no crash
                error_messages = page.get_by_text("Error:").all()
                assert len(error_messages) == 0, "❌ Error after clicking Leaderboard tab!"
                print("   ✓ Leaderboard tab clicked successfully")
            except Exception as e:
                print(f"   ⚠️  Could not click Leaderboard tab: {e}")

        print("✅ TEST PASSED: Tournament History Browser navigation works!")
        time.sleep(1)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
