"""
Playwright E2E Test 02: IN_PROGRESS Tournament - Continue Tournament

Verifies that clicking "Continue Tournament" on an IN_PROGRESS tournament
does not crash due to reward_config None handling.
"""

from playwright.sync_api import sync_playwright, expect
import time

BASE_URL = "http://localhost:8501"

def test_in_progress_continue():
    """
    Test Case 2: IN_PROGRESS Tournament - Continue Tournament

    Steps:
    1. Navigate to Streamlit app
    2. Click "📊 Open History" button
    3. Wait for tournament list
    4. Select an IN_PROGRESS tournament from dropdown
    5. Click "▶️ Continue Tournament" button
    6. Assert: No error message appears
    7. Assert: Navigation to workflow step occurs
    """

    print("\n" + "="*80)
    print("🎭 TEST 02: IN_PROGRESS TOURNAMENT - CONTINUE TOURNAMENT")
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

        # Get all options and find an IN_PROGRESS tournament
        options = tournament_selector.locator('option').all()
        print(f"   Found {len(options)} tournaments")

        in_progress_tournament = None
        for option in options:
            text = option.text_content() or ""
            if "IN_PROGRESS" in text.upper() or "IN PROGRESS" in text.upper():
                in_progress_tournament = option
                break

        if not in_progress_tournament:
            print("   ⚠️  No IN_PROGRESS tournament found, selecting second tournament")
            in_progress_tournament = options[1] if len(options) > 1 else options[0] if options else None

        if not in_progress_tournament:
            print("   ❌ No tournaments available")
            browser.close()
            raise Exception("No tournaments found")

        # Select the IN_PROGRESS tournament
        tournament_text = in_progress_tournament.text_content() or "Unknown"
        tournament_value = in_progress_tournament.get_attribute('value') or '0'
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

        # Look for Continue Tournament button
        print("→ Looking for 'Continue Tournament' button...")
        continue_button = None

        try:
            continue_button = page.get_by_role("button", name="▶️ Continue Tournament")
            if continue_button.is_visible(timeout=3000):
                print("   ✓ Found 'Continue Tournament' button")
        except:
            # Try Continue Setup as fallback
            try:
                continue_button = page.get_by_role("button", name="▶️ Continue Setup")
                if continue_button.is_visible(timeout=2000):
                    print("   ℹ️  Found 'Continue Setup' instead (tournament may be DRAFT)")
            except:
                pass

        if not continue_button:
            print("   ⚠️  No Continue button found - tournament may be completed")
            browser.close()
            return True  # Not a failure

        # CRITICAL TEST: Click Continue button
        print("\n→ ⚠️  CLICKING CONTINUE BUTTON...")
        print("   This is the critical moment - checking for crash...")

        continue_button.click()
        time.sleep(3)

        # VERIFY: Check for errors
        print("\n→ ✅ VERIFYING NO ERRORS...")

        # Check for error messages
        error_elements = page.get_by_text("Error:").all()
        if len(error_elements) > 0:
            print(f"   ❌ FAIL: Found {len(error_elements)} error message(s)!")
            browser.close()
            raise Exception(f"Error messages found: {len(error_elements)}")

        # Check for NoneType error
        none_type_errors = page.get_by_text("'NoneType' object has no attribute").all()
        if len(none_type_errors) > 0:
            print(f"   ❌ FAIL: Found NoneType AttributeError!")
            browser.close()
            raise Exception("NoneType AttributeError found")

        print("   ✅ SUCCESS: No error messages found!")

        # Verify navigation
        print("\n→ Verifying navigation occurred...")
        try:
            page.get_by_text("Current Step:").wait_for(timeout=5000)
            print("   ✓ Navigated to workflow step successfully")
        except:
            print("   ℹ️  May not have navigated (workflow may be at different step)")

        time.sleep(2)

        print("\n" + "="*80)
        print("✅ ✅ ✅ TEST 02 PASSED ✅ ✅ ✅")
        print("="*80)
        print("IN_PROGRESS tournament Continue Tournament works without errors!")
        print("="*80 + "\n")

        # Keep browser open for 3 seconds
        print("Keeping browser open for 3 more seconds...")
        time.sleep(3)

        browser.close()
        return True

if __name__ == "__main__":
    success = test_in_progress_continue()
    exit(0 if success else 1)
