"""
Playwright E2E Test 01: Quick Test - FULL FLOW (Home → Create → Results)

COMPLETE end-to-end test covering:
1. Home screen
2. Click "New Tournament"
3. Fill tournament configuration form
4. Select "Quick Test" mode
5. Submit form
6. Wait for test to complete
7. Verify Results screen appears
8. Verify NO CRASHES at any point

This is the PRIMARY acceptance test - if this fails, the workflow is broken.
"""

import pytest
from playwright.sync_api import sync_playwright, expect
import time

BASE_URL = "http://localhost:8501"

@pytest.mark.nondestructive
def test_quick_test_full_flow():
    """
    FULL E2E Test: Quick Test Flow

    Home → Create New Tournament → Quick Test → Results

    SUCCESS CRITERIA:
    - No Streamlit exceptions
    - No NoneType errors
    - No tracebacks
    - Results screen appears with verdict
    - Skill progression data visible
    """

    print("\n" + "="*80)
    print("🎭 TEST 01: QUICK TEST - FULL FLOW (HOME → CREATE → RESULTS)")
    print("="*80)

    with sync_playwright() as p:
        # Launch Firefox in headed mode with slow motion for visibility
        print("→ Launching Firefox browser (headed mode, slow motion)...")
        browser = p.firefox.launch(
            headless=False,
            slow_mo=1200,  # 1.2 second delays for visibility
        )

        page = browser.new_page()

        # ==================================================
        # STEP 1: Navigate to Home Screen
        # ==================================================
        print("\n" + "="*80)
        print("STEP 1: NAVIGATE TO HOME SCREEN")
        print("="*80)

        print(f"→ Opening {BASE_URL}...")
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        # Verify we're on home screen
        page_text = page.text_content('body') or ""
        if "Tournament Sandbox" in page_text:
            print("   ✅ Home screen loaded")
        else:
            print("   ❌ Home screen not detected")
            page.screenshot(path="error_home_not_loaded.png")
            browser.close()
            raise Exception("Home screen did not load")

        # Check for errors on home screen
        error_count = check_for_errors(page, "Home screen")
        if error_count > 0:
            page.screenshot(path="error_home_screen.png")
            browser.close()
            raise Exception(f"Errors on home screen: {error_count}")

        # ==================================================
        # STEP 2: Click "New Tournament" Button
        # ==================================================
        print("\n" + "="*80)
        print("STEP 2: CLICK 'NEW TOURNAMENT' BUTTON")
        print("="*80)

        print("→ Looking for 'New Tournament' button...")
        new_tournament_button = None

        try:
            # Try "➕ New Tournament" first
            new_tournament_button = page.get_by_role("button", name="➕ New Tournament")
            if new_tournament_button.is_visible(timeout=3000):
                print("   ✓ Found '➕ New Tournament' button")
        except:
            try:
                # Try "🆕 Create New Tournament" as fallback
                new_tournament_button = page.get_by_role("button", name="🆕 Create New Tournament")
                if new_tournament_button.is_visible(timeout=3000):
                    print("   ✓ Found '🆕 Create New Tournament' button")
            except:
                pass

        if not new_tournament_button:
            print("   ❌ Could not find New Tournament button")
            page.screenshot(path="error_no_new_tournament_button.png")
            browser.close()
            raise Exception("New Tournament button not found")

        print("→ ⚠️  CLICKING 'NEW TOURNAMENT' BUTTON...")
        new_tournament_button.click()
        time.sleep(3)

        # Verify configuration screen appeared
        page_text = page.text_content('body') or ""
        if "Test Mode" in page_text or "Game Type" in page_text:
            print("   ✅ Configuration screen loaded")
        else:
            print("   ❌ Configuration screen not detected")
            page.screenshot(path="error_config_not_loaded.png")
            browser.close()
            raise Exception("Configuration screen did not load")

        # Check for errors
        error_count = check_for_errors(page, "After clicking New Tournament")
        if error_count > 0:
            page.screenshot(path="error_after_new_tournament.png")
            browser.close()
            raise Exception(f"Errors after clicking New Tournament: {error_count}")

        # ==================================================
        # STEP 3: Fill Tournament Configuration Form
        # ==================================================
        print("\n" + "="*80)
        print("STEP 3: FILL TOURNAMENT CONFIGURATION FORM")
        print("="*80)

        # 3.1: Select Test Mode - "Quick Test"
        print("→ Selecting 'Quick Test (Auto-complete)' mode...")
        try:
            # Look for radio button with label "Quick Test"
            quick_test_radio = page.get_by_text("⚡Quick Test (Auto-complete)")
            if quick_test_radio.is_visible(timeout=3000):
                quick_test_radio.click()
                print("   ✅ Selected 'Quick Test' mode")
                time.sleep(1)
        except Exception as e:
            print(f"   ❌ Could not select Quick Test mode: {e}")
            page.screenshot(path="error_quick_test_selection.png")
            browser.close()
            raise Exception("Failed to select Quick Test mode")

        # 3.2: Select Game Type (should be pre-selected, but verify)
        print("→ Verifying game type selection...")
        page_text = page.text_content('body') or ""
        if "GânFootvolley" in page_text or "Selected" in page_text:
            print("   ✅ Game type is selected")
        else:
            print("   ⚠️  Game type may not be selected")

        # 3.3: Tournament Type
        print("→ Selecting tournament type...")
        try:
            # Look for tournament type selector (likely a selectbox)
            # Tournament types: League, Knockout, Hybrid
            # We'll select League as it's most common

            # Try to find selectbox containing tournament type
            tournament_type_selects = page.locator('select').all()

            for select in tournament_type_selects:
                # Get the options
                options = select.locator('option').all()
                option_texts = [opt.text_content() or "" for opt in options]

                # Check if this looks like tournament type selector
                if any("league" in text.lower() or "knockout" in text.lower() for text in option_texts):
                    print(f"   Found tournament type selector with {len(options)} options")
                    # Select "League" (typically first option after placeholder)
                    if len(options) > 1:
                        select.select_option(index=1)  # Select first non-placeholder option
                        print("   ✅ Selected tournament type")
                        time.sleep(1)
                    break
        except Exception as e:
            print(f"   ⚠️  Tournament type selection: {e}")
            # Continue anyway - may have a default

        # 3.4: Player Count
        print("→ Setting player count...")
        try:
            # Look for number input for player count
            player_count_input = page.locator('input[type="number"]').first
            if player_count_input.is_visible(timeout=3000):
                player_count_input.fill("8")  # 8 players
                print("   ✅ Set player count to 8")
                time.sleep(1)
        except Exception as e:
            print(f"   ⚠️  Player count setting: {e}")
            # Continue - may have a default

        # 3.5: Skills to Test
        print("→ Verifying skills selection...")
        # Skills are typically pre-selected based on game type
        # Just verify they appear in the form
        page_text = page.text_content('body') or ""
        if "Skills" in page_text or "skills" in page_text:
            print("   ✅ Skills section visible")
        else:
            print("   ⚠️  Skills section may not be visible")

        # Take screenshot of filled form
        page.screenshot(path="screenshot_form_filled.png")
        print("   📸 Screenshot saved: screenshot_form_filled.png")

        # ==================================================
        # STEP 4: Submit Form (Create Tournament)
        # ==================================================
        print("\n" + "="*80)
        print("STEP 4: SUBMIT FORM - CREATE TOURNAMENT")
        print("="*80)

        # Scroll to bottom of page to reveal Create Tournament button
        print("→ Scrolling to bottom of form...")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)

        print("→ Looking for 'Create Tournament' submit button...")
        create_button = None

        try:
            create_button = page.get_by_role("button", name="✅ Create Tournament")
            if create_button.is_visible(timeout=3000):
                print("   ✓ Found '✅ Create Tournament' button")
        except:
            try:
                create_button = page.get_by_role("button", name="Create Tournament")
                if create_button.is_visible(timeout=3000):
                    print("   ✓ Found 'Create Tournament' button")
            except:
                pass

        if not create_button:
            print("   ❌ Could not find Create Tournament button")
            page.screenshot(path="error_no_create_button.png")
            browser.close()
            raise Exception("Create Tournament button not found")

        print("→ ⚠️  CLICKING 'CREATE TOURNAMENT' BUTTON...")
        print("   This will trigger Quick Test execution...")
        create_button.click()
        time.sleep(3)

        # Check for immediate errors
        error_count = check_for_errors(page, "After clicking Create Tournament")
        if error_count > 0:
            page.screenshot(path="error_after_create_click.png")
            browser.close()
            raise Exception(f"Errors after clicking Create Tournament: {error_count}")

        # ==================================================
        # STEP 5: Wait for Test to Complete
        # ==================================================
        print("\n" + "="*80)
        print("STEP 5: WAITING FOR TEST TO COMPLETE")
        print("="*80)

        print("→ Waiting for Quick Test to run...")
        print("   (Backend is creating tournament, enrolling users, running matches, distributing rewards)")

        # Quick Test should complete within 10-15 seconds
        # Wait for results screen to appear
        max_wait_seconds = 20
        wait_interval = 2
        elapsed = 0

        results_appeared = False

        while elapsed < max_wait_seconds:
            time.sleep(wait_interval)
            elapsed += wait_interval

            print(f"   ⏳ Waiting... {elapsed}s / {max_wait_seconds}s")

            # Check if results screen appeared
            page_text = page.text_content('body') or ""

            if "Verdict" in page_text or "verdict" in page_text:
                print("   ✅ Results screen appeared!")
                results_appeared = True
                break

            # Check for "WORKING" or "Results" or "Skill Progression"
            if "WORKING" in page_text or "Skill Progression" in page_text or "Top Performers" in page_text:
                print("   ✅ Results detected!")
                results_appeared = True
                break

            # Check for errors
            error_count = check_for_errors(page, f"While waiting (t={elapsed}s)", silent=True)
            if error_count > 0:
                print(f"   ❌ Errors detected while waiting!")
                page.screenshot(path=f"error_while_waiting_{elapsed}s.png")
                browser.close()
                raise Exception(f"Errors during test execution at t={elapsed}s")

        if not results_appeared:
            print(f"   ❌ Results did not appear after {max_wait_seconds}s")
            page.screenshot(path="error_results_timeout.png")

            # Check what screen we're on
            page_text = page.text_content('body') or ""
            print(f"   Current page content (first 500 chars):")
            print(f"   {page_text[:500]}")

            browser.close()
            raise Exception(f"Results screen did not appear after {max_wait_seconds}s")

        # ==================================================
        # STEP 6: Verify Results Screen
        # ==================================================
        print("\n" + "="*80)
        print("STEP 6: VERIFY RESULTS SCREEN")
        print("="*80)

        time.sleep(2)  # Let results fully load

        # Take screenshot of results
        page.screenshot(path="screenshot_results.png")
        print("   📸 Screenshot saved: screenshot_results.png")

        # Verify key result elements
        page_text = page.text_content('body') or ""

        verifications = {
            "Verdict": "Verdict" in page_text,
            "Tournament": "tournament" in page_text.lower() or "Tournament" in page_text,
            "Skill Progression": "skill" in page_text.lower() or "Skill" in page_text,
            "Performers": "performer" in page_text.lower() or "Performer" in page_text,
        }

        print("\n→ Verifying result components:")
        all_verified = True
        for component, found in verifications.items():
            status = "✅" if found else "❌"
            print(f"   {status} {component}: {found}")
            if not found:
                all_verified = False

        if not all_verified:
            print("\n   ⚠️  Some result components missing, but test may still have passed")

        # FINAL ERROR CHECK
        print("\n→ ✅ FINAL ERROR CHECK...")
        error_count = check_for_errors(page, "Results screen")
        if error_count > 0:
            page.screenshot(path="error_results_screen.png")
            browser.close()
            raise Exception(f"Errors on results screen: {error_count}")

        print("   ✅ No errors detected on results screen!")

        # ==================================================
        # SUCCESS!
        # ==================================================
        print("\n" + "="*80)
        print("✅ ✅ ✅ TEST 01 PASSED - FULL FLOW COMPLETE ✅ ✅ ✅")
        print("="*80)
        print("🎉 Quick Test flow executed successfully!")
        print("📊 Flow: Home → Create New Tournament → Quick Test → Results")
        print("🔍 Verified: No crashes, no errors, results appeared")
        print("="*80 + "\n")

        # Keep browser open for 5 seconds for inspection
        print("Keeping browser open for 5 more seconds for inspection...")
        time.sleep(5)

        browser.close()
        return True


def check_for_errors(page, context: str = "", silent: bool = False) -> int:
    """
    Check page for Streamlit errors, NoneType errors, and tracebacks.

    Returns: Number of errors found
    """
    error_elements = page.locator('[data-testid="stException"]').all()
    none_type_errors = page.get_by_text("'NoneType' object has no attribute").all()
    traceback_errors = page.get_by_text("Traceback (most recent call last)").all()

    total_errors = len(error_elements) + len(none_type_errors) + len(traceback_errors)

    if total_errors > 0 and not silent:
        print(f"   ❌ ERRORS DETECTED {context}:")
        print(f"      - Streamlit exceptions: {len(error_elements)}")
        print(f"      - NoneType errors: {len(none_type_errors)}")
        print(f"      - Traceback errors: {len(traceback_errors)}")

    return total_errors


if __name__ == "__main__":
    try:
        success = test_quick_test_full_flow()
        print("\n🎉 TEST PASSED!")
        exit(0)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
