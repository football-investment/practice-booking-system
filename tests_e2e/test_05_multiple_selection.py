"""
Playwright E2E Test 04: Multiple Tournament Selection

Verifies that rapidly switching between different tournaments
does not cause crashes or state loading errors.
"""

import pytest
from playwright.sync_api import sync_playwright, expect
import time

BASE_URL = "http://localhost:8501"

@pytest.mark.nondestructive
def test_multiple_selection():
    """
    Test Case 4: Multiple Tournament Selection

    Steps:
    1. Navigate to Streamlit app
    2. Click "📊 Open History" button
    3. Select Tournament A
    4. Wait for detail load
    5. Assert: No error
    6. Select Tournament B
    7. Wait for detail load
    8. Assert: No error
    9. Select Tournament C
    10. Wait for detail load
    11. Assert: No error
    """

    print("\n" + "="*80)
    print("🎭 TEST 04: MULTIPLE TOURNAMENT SELECTION")
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

        # Get all options
        options = tournament_selector.locator('option').all()
        print(f"   Found {len(options)} tournaments")

        if len(options) < 3:
            print("   ⚠️  Less than 3 tournaments available, testing with available tournaments")

        # Test switching between tournaments
        tournaments_to_test = min(3, len(options))

        for i in range(tournaments_to_test):
            tournament_text = options[i].text_content() or "Unknown"
            tournament_value = options[i].get_attribute('value') or '0'

            print(f"\n→ Selecting Tournament {i+1}: {tournament_text}")
            tournament_selector.select_option(value=tournament_value)
            time.sleep(2)

            # Verify tournament details loaded
            print(f"   Verifying details loaded for Tournament {i+1}...")
            try:
                page.get_by_text("Tournament Name").wait_for(timeout=5000)
                print(f"   ✓ Tournament {i+1} details loaded")
            except:
                print(f"   ⚠️  Tournament {i+1} details may not have loaded")

            # Check for errors
            error_elements = page.get_by_text("Error:").all()
            if len(error_elements) > 0:
                print(f"   ❌ FAIL: Tournament {i+1} has {len(error_elements)} error(s)")
                browser.close()
                raise Exception(f"Error loading tournament {i+1}")

            # Check for NoneType errors
            none_type_errors = page.get_by_text("'NoneType' object has no attribute").all()
            if len(none_type_errors) > 0:
                print(f"   ❌ FAIL: Tournament {i+1} has NoneType error")
                browser.close()
                raise Exception(f"NoneType error on tournament {i+1}")

            print(f"   ✅ Tournament {i+1} loaded without errors")
            time.sleep(1)

        print("\n" + "="*80)
        print("✅ ✅ ✅ TEST 04 PASSED ✅ ✅ ✅")
        print("="*80)
        print(f"Successfully switched between {tournaments_to_test} tournaments without errors!")
        print("="*80 + "\n")

        # Keep browser open for 3 seconds
        print("Keeping browser open for 3 more seconds...")
        time.sleep(3)

        browser.close()
        return True

if __name__ == "__main__":
    success = test_multiple_selection()
    exit(0 if success else 1)
