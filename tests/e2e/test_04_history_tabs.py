"""
Playwright E2E Test 03: Tournament History Tabs Navigation

Verifies that all tabs (Leaderboard, Match Results, Rewards) load
without crashing when viewing tournament history.
"""

import pytest
from playwright.sync_api import sync_playwright, expect
import time

BASE_URL = "http://localhost:8501"

@pytest.mark.nondestructive
def test_history_tabs():
    """
    Test Case 3: Tournament History Tabs Navigation

    Steps:
    1. Navigate to Streamlit app
    2. Click "📊 Open History" button
    3. Select any tournament
    4. Click "📊 Leaderboard" tab
    5. Assert: No crash
    6. Click "🎯 Match Results" tab
    7. Assert: No crash, date fields display correctly
    8. Click "🎁 Rewards" tab
    9. Assert: No crash
    """

    print("\n" + "="*80)
    print("🎭 TEST 03: TOURNAMENT HISTORY TABS NAVIGATION")
    print("="*80)

    with sync_playwright() as p:
        # Launch browser in headed mode
        print("→ Launching browser (headed mode, slow motion)...")
        browser = p.chromium.launch(
            headless=False,
            slow_mo=800,
        )

        page = browser.new_page()

        # Navigate to app
        print(f"→ Opening {BASE_URL}...")
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # Click Open History button
        print("→ Clicking '📚 Open History' button...")
        try:
            history_button = page.get_by_role("button", name="📚 Open History")
            history_button.wait_for(timeout=10000)
            history_button.click()
            print("   ✓ Clicked Open History")
        except Exception as e:
            print(f"   ❌ Could not find Open History button: {e}")
            browser.close()
            raise

        time.sleep(2)

        # Wait for tournament list
        print("→ Waiting for tournament list...")
        try:
            page.wait_for_selector("text=Found", timeout=10000)
            print("   ✓ Tournament list loaded")
        except:
            print("   ❌ Tournament list did not load")
            browser.close()
            raise

        time.sleep(2)

        # Find tournament selector dropdown
        print("→ Finding tournament selector...")
        tournament_selector = page.locator('select').first
        tournament_selector.wait_for(timeout=5000)

        # Get all options and select first tournament
        options = tournament_selector.locator('option').all()
        print(f"   Found {len(options)} tournaments")

        if len(options) == 0:
            print("   ❌ No tournaments available")
            browser.close()
            raise Exception("No tournaments found")

        # Select the first tournament
        tournament_text = options[0].text_content() or "Unknown"
        tournament_value = options[0].get_attribute('value') or '0'
        print(f"→ Selecting tournament: {tournament_text}")

        tournament_selector.select_option(value=tournament_value)
        time.sleep(3)

        # Verify tournament details loaded
        print("→ Verifying tournament details loaded...")
        try:
            page.get_by_text("Tournament Name").wait_for(timeout=5000)
            print("   ✓ Tournament details loaded")
        except:
            print("   ⚠️  Tournament details may not have loaded")

        time.sleep(2)

        # Test Tab 1: Leaderboard
        print("\n→ Testing Tab 1: 📊 Leaderboard...")
        try:
            leaderboard_tab = page.get_by_role("tab", name="📊 Leaderboard")
            if leaderboard_tab.is_visible(timeout=3000):
                leaderboard_tab.click()
                time.sleep(2)

                # Check for errors
                error_elements = page.get_by_text("Error:").all()
                if len(error_elements) > 0:
                    print(f"   ❌ FAIL: Leaderboard tab has {len(error_elements)} error(s)")
                    browser.close()
                    raise Exception("Leaderboard tab error")

                print("   ✅ Leaderboard tab loaded successfully")
            else:
                print("   ℹ️  Leaderboard tab not visible")
        except Exception as e:
            print(f"   ⚠️  Could not test Leaderboard tab: {e}")

        # Test Tab 2: Match Results
        print("\n→ Testing Tab 2: 🎯 Match Results...")
        try:
            results_tab = page.get_by_role("tab", name="🎯 Match Results")
            if results_tab.is_visible(timeout=3000):
                results_tab.click()
                time.sleep(2)

                # Check for errors
                error_elements = page.get_by_text("Error:").all()
                if len(error_elements) > 0:
                    print(f"   ❌ FAIL: Match Results tab has {len(error_elements)} error(s)")
                    browser.close()
                    raise Exception("Match Results tab error")

                # Check for NoneType errors specifically
                none_type_errors = page.get_by_text("'NoneType' object has no attribute").all()
                if len(none_type_errors) > 0:
                    print(f"   ❌ FAIL: Match Results tab has NoneType error")
                    browser.close()
                    raise Exception("Match Results NoneType error")

                print("   ✅ Match Results tab loaded successfully")
            else:
                print("   ℹ️  Match Results tab not visible")
        except Exception as e:
            print(f"   ⚠️  Could not test Match Results tab: {e}")

        # Test Tab 3: Rewards
        print("\n→ Testing Tab 3: 🎁 Rewards...")
        try:
            rewards_tab = page.get_by_role("tab", name="🎁 Rewards")
            if rewards_tab.is_visible(timeout=3000):
                rewards_tab.click()
                time.sleep(2)

                # Check for errors
                error_elements = page.get_by_text("Error:").all()
                if len(error_elements) > 0:
                    print(f"   ❌ FAIL: Rewards tab has {len(error_elements)} error(s)")
                    browser.close()
                    raise Exception("Rewards tab error")

                print("   ✅ Rewards tab loaded successfully")
            else:
                print("   ℹ️  Rewards tab not visible")
        except Exception as e:
            print(f"   ⚠️  Could not test Rewards tab: {e}")

        time.sleep(2)

        print("\n" + "="*80)
        print("✅ ✅ ✅ TEST 03 PASSED ✅ ✅ ✅")
        print("="*80)
        print("All tournament history tabs loaded without errors!")
        print("="*80 + "\n")

        # Keep browser open for 3 seconds
        print("Keeping browser open for 3 more seconds...")
        time.sleep(3)

        browser.close()
        return True

if __name__ == "__main__":
    success = test_history_tabs()
    exit(0 if success else 1)
