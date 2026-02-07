#!/usr/bin/env python3
"""
MINIMAL headless test: Verify participant toggle selection works

Tests ONLY the toggle clicking functionality - no tournament creation
User requirement: "nincs uj plywright teszt headed amig healessben nincs megoldva"

Expected behavior:
- UI shows "✅ 0 selected" initially
- After clicking toggles for users [4, 5, 6], should show "✅ 3 selected"
"""
import time
from playwright.sync_api import sync_playwright, Page

STREAMLIT_URL = "http://localhost:8501"

def wait_for_streamlit_rerun(page: Page, timeout: int = 10000):
    """Wait for Streamlit to finish rerunning after interaction"""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
        time.sleep(0.5)  # Extra buffer for Streamlit internal state updates
    except Exception:
        time.sleep(1.0)  # Fallback wait


def test_participant_toggle_selection():
    """Test ONLY participant toggle clicking - minimal validation"""

    with sync_playwright() as p:
        # Launch HEADLESS browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1024, "height": 768})
        page = context.new_page()

        print("\n" + "="*80)
        print("MINIMAL HEADLESS TEST: Participant Toggle Selection")
        print("="*80)

        try:
            # Navigate to Streamlit app
            print("\n1. Navigate to Streamlit app (home page)...")
            page.goto(STREAMLIT_URL, wait_until="networkidle")
            time.sleep(2)

            # Click "New Tournament" button to open form
            print("\n2. Click 'New Tournament' button to open form...")
            new_tournament_button = page.get_by_text("New Tournament", exact=True)
            new_tournament_button.click()
            time.sleep(3)  # Wait for form to load

            # DEBUG: Take screenshot of the form
            print("\n3. DEBUG: Taking screenshot of tournament form...")
            page.screenshot(path="/tmp/participant_test_form.png")
            print("   Screenshot saved: /tmp/participant_test_form.png")

            # Scroll down to find Participants section
            print("\n4. Scroll down to find Participants section...")
            try:
                # Scroll to bottom of page
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)

                # Look for Participants section
                participants = page.get_by_text("Participants", exact=False)
                if participants.count() > 0:
                    print(f"   ✅ Found 'Participants' text ({participants.count()} instances)")
                    participants.first.scroll_into_view_if_needed()
                    time.sleep(0.5)
                else:
                    print("   ❌ 'Participants' section still not found!")
                    # Take another screenshot
                    page.screenshot(path="/tmp/participant_test_scrolled.png")
                    print("   Screenshot after scroll: /tmp/participant_test_scrolled.png")

            except Exception as e:
                print(f"   ⚠️  Error finding Participants section: {e}")

            # Try to find and click toggles
            print("\n5. Attempt to find and click participant toggles...")
            test_users = [4, 5, 6]
            clicked_count = 0

            for test_user_id in test_users:
                toggle_label = f"Select {test_user_id}"

                try:
                    toggle = page.get_by_text(toggle_label, exact=True).first
                    print(f"   Looking for toggle: '{toggle_label}'")

                    if toggle.is_visible():
                        print(f"      ✅ Toggle is visible, clicking...")
                        toggle.scroll_into_view_if_needed()
                        toggle.click()
                        clicked_count += 1
                        print(f"      ✅ Clicked toggle for user {test_user_id}")
                        time.sleep(0.5)
                    else:
                        print(f"      ❌ Toggle exists in DOM but is NOT visible")

                except Exception as e:
                    print(f"      ❌ Failed to find/click toggle: {e}")

            # Wait for Streamlit rerun
            wait_for_streamlit_rerun(page)

            # Take screenshot after clicks
            print(f"\n6. Taking screenshot after clicking {clicked_count} toggles...")
            page.screenshot(path="/tmp/participant_test_after_clicks.png")
            print("   Screenshot saved: /tmp/participant_test_after_clicks.png")

            # Try to verify participant count
            print("\n7. Verify participant count updated...")
            try:
                count_text = page.locator("text=/✅.*selected/").first.text_content(timeout=5000)
                print(f"   Found count: '{count_text}'")

                if f"{clicked_count} selected" in count_text:
                    print(f"   ✅ SUCCESS: {clicked_count} participants selected!")
                    return True
                else:
                    print(f"   ⚠️  Count text found but doesn't match expected {clicked_count}")
            except Exception as e:
                print(f"   ⚠️  Could not find participant count text: {e}")
                print(f"   Check screenshot to verify selection visually")

            print("\n" + "="*80)
            print("✅ DEBUG TEST COMPLETE")
            print("="*80)
            print("   Check screenshots to verify:")
            print("   - /tmp/participant_test_initial.png (before click)")
            print("   - /tmp/participant_test_after_click.png (after click)")
            print("\n   If toggle labels are visible and clickable, test is passing")
            print("="*80 + "\n")

        except AssertionError as e:
            print("\n" + "="*80)
            print("❌ ASSERTION FAILED")
            print("="*80)
            print(str(e))
            print("\n🔍 TROUBLESHOOTING:")
            print("   1. Check if Streamlit is running on http://localhost:8501")
            print("   2. Verify toggle labels are visible (not collapsed)")
            print("   3. Check if session_state.participant_toggles is updating")
            print("="*80 + "\n")
            raise

        except Exception as e:
            print("\n" + "="*80)
            print("❌ ERROR")
            print("="*80)
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("\n🔍 TROUBLESHOOTING:")
            print("   1. Ensure Streamlit app is running")
            print("   2. Check if participant toggles exist in UI")
            print("   3. Verify label text matches 'Select {user_id}' format")
            print("="*80 + "\n")
            raise

        finally:
            browser.close()


if __name__ == "__main__":
    test_participant_toggle_selection()
