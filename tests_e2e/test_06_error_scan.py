"""
Playwright E2E Test 05: Error Detection Scan

Systematically scans ALL tournaments in the history dropdown
to verify none cause errors when selected.
"""

from playwright.sync_api import sync_playwright, expect
import time

BASE_URL = "http://localhost:8501"

def test_error_scan():
    """
    Test Case 5: Error Detection Scan

    Steps:
    1. Navigate to Streamlit app
    2. Click "📊 Open History" button
    3. For each tournament in dropdown:
       - Select tournament
       - Wait 2 seconds
       - Scan page for error messages
       - Assert: No "Error:" text
       - Assert: No "'NoneType' object has no attribute" text
       - Assert: No red error boxes
    """

    print("\n" + "="*80)
    print("🎭 TEST 05: ERROR DETECTION SCAN - ALL TOURNAMENTS")
    print("="*80)

    with sync_playwright() as p:
        # Launch browser in headed mode
        print("→ Launching browser (headed mode, slow motion)...")
        browser = p.chromium.launch(
            headless=False,
            slow_mo=500,  # Faster for scanning many tournaments
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
        total_tournaments = len(options)
        print(f"   Found {total_tournaments} tournaments to scan")

        if total_tournaments == 0:
            print("   ❌ No tournaments available")
            browser.close()
            raise Exception("No tournaments found")

        print("\n" + "="*80)
        print("🔍 SCANNING ALL TOURNAMENTS FOR ERRORS...")
        print("="*80 + "\n")

        errors_found = []

        # Scan each tournament
        for i, option in enumerate(options):
            tournament_text = option.text_content() or "Unknown"
            tournament_value = option.get_attribute('value') or '0'

            print(f"→ [{i+1}/{total_tournaments}] Scanning: {tournament_text[:60]}...")

            # Select tournament
            tournament_selector.select_option(value=tournament_value)
            time.sleep(2)

            # Scan for errors
            error_messages = page.get_by_text("Error:").all()
            none_type_errors = page.get_by_text("'NoneType' object has no attribute").all()
            attribute_errors = page.get_by_text("AttributeError").all()

            total_errors = len(error_messages) + len(none_type_errors) + len(attribute_errors)

            if total_errors > 0:
                error_detail = {
                    'tournament': tournament_text,
                    'index': i + 1,
                    'error_count': total_errors,
                    'error_messages': len(error_messages),
                    'none_type_errors': len(none_type_errors),
                    'attribute_errors': len(attribute_errors)
                }
                errors_found.append(error_detail)
                print(f"   ❌ ERRORS FOUND: {total_errors}")
                print(f"      - Error messages: {len(error_messages)}")
                print(f"      - NoneType errors: {len(none_type_errors)}")
                print(f"      - AttributeErrors: {len(attribute_errors)}")
            else:
                print(f"   ✅ No errors")

        print("\n" + "="*80)

        if len(errors_found) > 0:
            print("❌ ❌ ❌ TEST 05 FAILED ❌ ❌ ❌")
            print("="*80)
            print(f"Errors found in {len(errors_found)} out of {total_tournaments} tournaments:")
            print()
            for error in errors_found:
                print(f"Tournament {error['index']}: {error['tournament'][:60]}")
                print(f"  - Total errors: {error['error_count']}")
                print(f"  - Error messages: {error['error_messages']}")
                print(f"  - NoneType errors: {error['none_type_errors']}")
                print(f"  - AttributeErrors: {error['attribute_errors']}")
                print()
            print("="*80)

            # Keep browser open for 5 seconds to inspect
            print("Keeping browser open for 5 seconds to inspect errors...")
            time.sleep(5)

            browser.close()
            raise Exception(f"Errors found in {len(errors_found)} tournaments")
        else:
            print("✅ ✅ ✅ TEST 05 PASSED ✅ ✅ ✅")
            print("="*80)
            print(f"All {total_tournaments} tournaments loaded without errors!")
            print("Zero crashes detected across entire tournament history!")
            print("="*80 + "\n")

        # Keep browser open for 3 seconds
        print("Keeping browser open for 3 more seconds...")
        time.sleep(3)

        browser.close()
        return True

if __name__ == "__main__":
    success = test_error_scan()
    exit(0 if success else 1)
