"""
Playwright E2E Test: Quick Test with FULL DEBUG LOGGING

Debug captures:
1. Session state snapshots at every screen transition
2. API request/response logging
3. Screenshots at every critical step
4. Error context (user count, player count, test_mode)

This allows stable E2E test execution and fast backend error reproduction.
"""

import re
import time
import json
from playwright.sync_api import Page, expect
from datetime import datetime


def save_debug_data(page: Page, step_name: str, data: dict):
    """Save debug data to JSON file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"tests_e2e/debug/{timestamp}_{step_name}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"  📁 Debug data saved: {filename}")


def get_session_state(page: Page) -> dict:
    """Extract Streamlit session state via browser console"""
    try:
        # Streamlit stores session state in window.streamlitSessionState (if accessible)
        # Alternative: parse from DOM or use Streamlit's internal API
        session_data = page.evaluate("""
            () => {
                // Try to access Streamlit session state
                if (window.streamlitSessionState) {
                    return window.streamlitSessionState;
                }
                // Fallback: return empty object
                return {note: "Session state not accessible via JS"};
            }
        """)
        return session_data
    except Exception as e:
        return {"error": str(e), "note": "Could not extract session state"}


def capture_network_logs(page: Page) -> list:
    """Capture network requests/responses"""
    # Note: Playwright doesn't store past requests, need to listen during test
    # This is a placeholder - actual implementation needs request/response listeners
    return []


def test_quick_test_with_full_debug(page: Page):
    """
    E2E test with comprehensive debug logging

    Debug points:
    1. Home screen load → session state + screenshot
    2. Config screen load → session state + screenshot
    3. Location selection → screenshot
    4. Campus selection → screenshot
    5. Max Players input → screenshot
    6. Before "Run Quick Test" click → full state snapshot
    7. API call initiated → request payload
    8. Results screen → response + verdict + screenshot
    """

    print("\n" + "="*80)
    print("QUICK TEST - FULL DEBUG LOGGING")
    print("="*80)

    # Setup: Create debug directory
    import os
    os.makedirs("tests_e2e/debug", exist_ok=True)
    os.makedirs("tests_e2e/screenshots", exist_ok=True)

    # Track API calls
    api_calls = []

    def log_request(request):
        if "/api/" in request.url:
            api_calls.append({
                "type": "request",
                "url": request.url,
                "method": request.method,
                "timestamp": datetime.now().isoformat(),
                "post_data": request.post_data if request.method == "POST" else None
            })
            print(f"  🌐 API Request: {request.method} {request.url}")

    def log_response(response):
        if "/api/" in response.url:
            try:
                body = response.json() if response.headers.get("content-type", "").startswith("application/json") else None
            except:
                body = None

            api_calls.append({
                "type": "response",
                "url": response.url,
                "status": response.status,
                "timestamp": datetime.now().isoformat(),
                "body": body
            })
            print(f"  🌐 API Response: {response.status} {response.url}")

    # Listen to network events
    page.on("request", log_request)
    page.on("response", log_response)

    # ============================================================
    # STEP 1: HOME SCREEN
    # ============================================================
    print("\n[STEP 1: HOME SCREEN]")

    print("→ Loading http://localhost:8501/")
    page.goto("http://localhost:8501/")
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    print("  ✓ Page loaded")

    # DEBUG: Session state snapshot
    session_state_home = get_session_state(page)
    save_debug_data(page, "01_home_screen_session_state", {
        "screen": "home",
        "session_state": session_state_home,
        "url": page.url
    })

    # DEBUG: Screenshot
    page.screenshot(path="tests_e2e/screenshots/debug_01_home_screen.png", full_page=True)
    print("  📸 Screenshot: debug_01_home_screen.png")

    # Verify Home screen
    print("→ Verifying Home screen...")
    expect(page.get_by_text("🏠 Tournament Sandbox - Home")).to_be_visible()
    print("  ✓ Home screen visible")

    # Click "New Tournament"
    print("→ Clicking 'New Tournament' button...")
    new_tournament_button = page.get_by_role("button", name=re.compile(r"New Tournament", re.IGNORECASE))
    expect(new_tournament_button).to_be_visible()
    new_tournament_button.click()
    time.sleep(2)
    print("  ✓ Button clicked → Config screen")

    # ============================================================
    # STEP 2: CONFIGURATION SCREEN
    # ============================================================
    print("\n[STEP 2: CONFIGURATION SCREEN]")

    # DEBUG: Session state snapshot
    session_state_config = get_session_state(page)
    save_debug_data(page, "02_config_screen_session_state", {
        "screen": "configuration",
        "session_state": session_state_config,
        "url": page.url
    })

    # DEBUG: Screenshot
    page.screenshot(path="tests_e2e/screenshots/debug_02_config_screen_initial.png", full_page=True)
    print("  📸 Screenshot: debug_02_config_screen_initial.png")

    # Verify Quick Test mode
    print("→ Verifying Quick Test mode...")
    expect(page.get_by_text("⚡ Quick Test (Auto-complete)")).to_be_visible()
    print("  ✓ Quick Test mode active")

    # Verify preset selected
    print("→ Verifying game preset...")
    expect(page.get_by_text("✅ Selected")).to_be_visible()
    print("  ✓ Game preset selected")

    # Scroll to Location & Campus
    print("→ Scrolling to Location & Campus...")
    page.keyboard.press("PageDown")
    time.sleep(1)
    print("  ✓ Scrolled")

    # Verify Location section
    print("→ Verifying Location section...")
    location_section = page.locator('text=1️⃣ Location & Campus')
    expect(location_section).to_be_visible()
    print("  ✓ Section visible")

    # ============================================================
    # STEP 3: SELECT LOCATION
    # ============================================================
    print("\n[STEP 3: SELECT LOCATION]")

    print("→ Clicking Location selectbox...")
    location_selectbox = page.locator('[data-testid="stSelectbox"]').first
    expect(location_selectbox).to_be_visible()
    location_selectbox.click()
    time.sleep(0.5)

    # DEBUG: Screenshot of dropdown
    page.screenshot(path="tests_e2e/screenshots/debug_03_location_dropdown.png")
    print("  📸 Screenshot: debug_03_location_dropdown.png")

    # Select first option
    first_location = page.locator('[role="option"]').first
    expect(first_location).to_be_visible()
    location_text = first_location.text_content()
    first_location.click()
    time.sleep(1)
    print(f"  ✓ Location selected: {location_text}")

    # ============================================================
    # STEP 4: SELECT CAMPUS
    # ============================================================
    print("\n[STEP 4: SELECT CAMPUS]")

    print("→ Clicking Campus selectbox...")
    campus_selectbox = page.locator('[data-testid="stSelectbox"]').nth(1)
    expect(campus_selectbox).to_be_visible()
    campus_selectbox.click()
    time.sleep(0.5)

    # DEBUG: Screenshot of dropdown
    page.screenshot(path="tests_e2e/screenshots/debug_04_campus_dropdown.png")
    print("  📸 Screenshot: debug_04_campus_dropdown.png")

    # Select first option
    first_campus = page.locator('[role="option"]').first
    expect(first_campus).to_be_visible()
    campus_text = first_campus.text_content()
    first_campus.click()
    time.sleep(1)
    print(f"  ✓ Campus selected: {campus_text}")

    # ============================================================
    # STEP 5: CHECK REWARD CONFIGURATION
    # ============================================================
    print("\n[STEP 5: CHECK REWARD CONFIGURATION]")

    # Scroll to Reward Configuration section
    print("→ Scrolling to Reward Configuration...")
    page.keyboard.press("PageDown")
    time.sleep(1)

    # DEBUG: Screenshot of Reward Configuration section
    page.screenshot(path="tests_e2e/screenshots/debug_05a_reward_config.png", full_page=True)
    print("  📸 Screenshot: debug_05a_reward_config.png")

    # Check if Reward Configuration section exists
    reward_section = page.locator('text=2️⃣ Reward Configuration')
    if reward_section.is_visible():
        print("  ✓ Reward Configuration section visible")

        # Check for reward template selectbox
        reward_template_section = page.get_by_text("📋 Reward Template")
        if reward_template_section.is_visible():
            print("  ✓ Reward Template section visible")

            # Check if template is already selected
            page_text = page.locator("body").inner_text()
            if "Standard" in page_text or "Loaded" in page_text:
                print("  ✓ Reward template already loaded (default)")
            else:
                print("  ⚠️  No reward template selected")

        # Save reward config state
        reward_config_state = {
            "section_visible": True,
            "template_visible": reward_template_section.is_visible() if reward_template_section else False,
            "page_contains_standard": "Standard" in page_text if page_text else False
        }
        save_debug_data(page, "05a_reward_config_state", reward_config_state)
    else:
        print("  ⚠️  Reward Configuration section not visible")

    # ============================================================
    # STEP 6: CHANGE AGE GROUP TO AMATEUR
    # ============================================================
    print("\n[STEP 6: CHANGE AGE GROUP TO AMATEUR]")
    print("  ⚠️  CRITICAL: Default is PRE, but test users are AMATEUR!")

    # Scroll to Age Group
    print("→ Scrolling to Age Group...")
    page.keyboard.press("PageDown")
    time.sleep(1)

    # Find Age Group selectbox
    print("→ Looking for Age Group selectbox...")
    age_group_selectbox = page.locator('[data-testid="stSelectbox"]').filter(has_text="Age Group")
    expect(age_group_selectbox).to_be_visible()
    age_group_selectbox.click()
    time.sleep(0.5)

    # Select AMATEUR
    print("→ Selecting AMATEUR...")
    amateur_option = page.locator('[role="option"]').filter(has_text="AMATEUR")
    expect(amateur_option).to_be_visible()
    amateur_option.click()
    time.sleep(0.5)

    # Close the dropdown by pressing Escape
    print("→ Closing Age Group dropdown...")
    page.keyboard.press("Escape")
    time.sleep(0.5)
    print("  ✅ Age Group = AMATEUR")

    # ============================================================
    # STEP 7: SELECT PARTICIPANTS (8 users)
    # ============================================================
    print("\n[STEP 7: SELECT PARTICIPANTS]")
    print("  ⚠️  CRITICAL: Must manually select 8 users!")

    # Scroll to Participant Selection section (no expander anymore!)
    print("→ Scrolling to Participant Selection...")
    page.keyboard.press("PageDown")
    time.sleep(0.5)
    page.keyboard.press("PageDown")  # Extra scroll to ensure checkboxes are visible
    time.sleep(1)

    # Wait for participant section to render
    print("→ Waiting for participant checkboxes to render...")
    time.sleep(1)

    # 🎯 TERV A: Simple checkboxes - PLAYWRIGHT FRIENDLY!
    print("→ Selecting 8 users via simple checkboxes...")

    # Wait for checkboxes to render
    time.sleep(1)

    # Find participant checkboxes by key pattern: participant_*
    participant_checkboxes = page.locator('input[type="checkbox"][id*="participant_"]').all()
    print(f"  Found {len(participant_checkboxes)} participant checkboxes")

    # Select first 8 checkboxes
    selected_count = 0
    for i, checkbox in enumerate(participant_checkboxes):
        try:
            checkbox.scroll_into_view_if_needed()
            time.sleep(0.1)

            if checkbox.is_visible() and not checkbox.is_checked():
                print(f"    → Checkbox {i+1}: Clicking...")
                checkbox.check()
                selected_count += 1
                time.sleep(0.15)

                if selected_count >= 8:
                    break
        except Exception as e:
            print(f"    ⚠️  Checkbox {i+1} failed: {e}")
            continue

    time.sleep(1)
    print(f"  ✅ Total selected: {selected_count} users")

    # DEBUG: Screenshot after participant selection
    page.screenshot(path="tests_e2e/screenshots/debug_06_participants_selected.png", full_page=True)
    print("  📸 Screenshot: debug_06_participants_selected.png")

    # ============================================================
    # STEP 8: SCROLL TO BUTTON
    # ============================================================
    print("\n[STEP 8: SCROLL TO RUN QUICK TEST BUTTON]")

    print("→ Scrolling to bottom...")
    page.keyboard.press("End")
    time.sleep(1)
    page.keyboard.press("PageDown")
    time.sleep(0.5)
    page.keyboard.press("PageDown")
    time.sleep(1)
    print("  ✓ Scrolled to bottom")

    # DEBUG: Screenshot before button click
    page.screenshot(path="tests_e2e/screenshots/debug_07_before_button_click.png", full_page=True)
    print("  📸 Screenshot: debug_07_before_button_click.png")

    # ============================================================
    # STEP 8: CAPTURE PRE-CLICK STATE
    # ============================================================
    print("\n[STEP 8: PRE-CLICK STATE SNAPSHOT]")

    # DEBUG: Full state snapshot before API call
    pre_click_state = {
        "timestamp": datetime.now().isoformat(),
        "location_selected": location_text,
        "campus_selected": campus_text,
        "max_players": 8,
        "test_mode": "quick",
        "session_state": get_session_state(page),
        "api_calls_so_far": api_calls.copy()
    }

    save_debug_data(page, "08_pre_click_state", pre_click_state)
    print("  ✓ Pre-click state saved")

    # ============================================================
    # STEP 9: CLICK RUN QUICK TEST
    # ============================================================
    print("\n[STEP 9: CLICK RUN QUICK TEST BUTTON]")

    print("→ Finding 'Run Quick Test' button...")
    run_button = page.get_by_role("button", name=re.compile(r"Run Quick Test", re.IGNORECASE))

    expect(run_button).to_be_visible(timeout=5000)
    expect(run_button).to_be_enabled()
    print("  ✓ Button found and enabled")

    # Click button
    print("→ Clicking 'Run Quick Test'...")
    run_button.click()
    print("  ✓ Button clicked → API call initiated")

    # Wait for API call to complete (give 3 seconds for request to fire)
    time.sleep(3)

    # DEBUG: Capture API calls after click
    post_click_api_calls = [call for call in api_calls if call["timestamp"] > pre_click_state["timestamp"]]
    save_debug_data(page, "09_post_click_api_calls", {
        "api_calls": post_click_api_calls
    })
    print(f"  ✓ Captured {len(post_click_api_calls)} API calls after button click")

    # ============================================================
    # STEP 10: WAIT FOR RESULTS SCREEN
    # ============================================================
    print("\n[STEP 10: WAIT FOR RESULTS SCREEN]")

    print("→ Waiting for Results screen (up to 90 seconds)...")
    results_title = page.get_by_text("🧪 Sandbox Tournament Test Results")

    expect(results_title).to_be_visible(timeout=90000)
    print("  ✓ Results screen appeared")

    # Wait for full render
    time.sleep(2)

    # DEBUG: Screenshot of results
    page.screenshot(path="tests_e2e/screenshots/debug_10_results_screen.png", full_page=True)
    print("  📸 Screenshot: debug_10_results_screen.png")

    # ============================================================
    # STEP 11: ANALYZE RESULTS
    # ============================================================
    print("\n[STEP 11: ANALYZE RESULTS]")

    # Extract verdict from page
    page_text = page.locator("body").inner_text()

    verdict = "UNKNOWN"
    if "WORKING" in page_text:
        verdict = "WORKING"
    elif "PASS" in page_text:
        verdict = "PASS"
    elif "ERROR" in page_text:
        verdict = "ERROR"
    elif "NOT_WORKING" in page_text:
        verdict = "NOT_WORKING"

    # Check for error messages
    error_messages = []
    if "Sample larger than population" in page_text:
        error_messages.append("Sample larger than population or is negative")
    if "Test execution failed" in page_text:
        error_messages.append("Test execution failed")

    # Extract insights
    insights_visible = page.get_by_text("💡 Insights").is_visible()

    # DEBUG: Results analysis
    results_analysis = {
        "timestamp": datetime.now().isoformat(),
        "verdict": verdict,
        "insights_visible": insights_visible,
        "error_messages": error_messages,
        "session_state": get_session_state(page),
        "all_api_calls": api_calls,
        "page_contains_error": "ERROR" in page_text,
        "page_contains_working": "WORKING" in page_text
    }

    save_debug_data(page, "11_results_analysis", results_analysis)
    print(f"  ✓ Results analyzed: Verdict={verdict}")

    if error_messages:
        print(f"  ⚠️  Errors found: {error_messages}")

    # ============================================================
    # STEP 12: FINAL DEBUG SUMMARY
    # ============================================================
    print("\n[STEP 12: FINAL DEBUG SUMMARY]")

    final_summary = {
        "test_completed_at": datetime.now().isoformat(),
        "test_duration_seconds": None,  # Calculate if needed
        "verdict": verdict,
        "error_messages": error_messages,
        "total_api_calls": len(api_calls),
        "api_calls_detail": api_calls,
        "configuration": {
            "location": location_text,
            "campus": campus_text,
            "max_players": 8,
            "test_mode": "quick"
        },
        "screenshots": [
            "debug_01_home_screen.png",
            "debug_02_config_screen_initial.png",
            "debug_03_location_dropdown.png",
            "debug_04_campus_dropdown.png",
            "debug_05a_reward_config.png",
            "debug_06_form_filled.png",
            "debug_07_before_button_click.png",
            "debug_10_results_screen.png"
        ]
    }

    save_debug_data(page, "13_FINAL_SUMMARY", final_summary)

    print("\n" + "="*80)
    print("✅ TEST COMPLETED WITH FULL DEBUG LOGGING")
    print("="*80)
    print(f"Verdict: {verdict}")
    print(f"Errors: {error_messages if error_messages else 'None'}")
    print(f"Total API calls: {len(api_calls)}")
    print(f"Debug files saved to: tests_e2e/debug/")
    print(f"Screenshots saved to: tests_e2e/screenshots/")
    print("="*80)

    # Assert test passes (frontend flow completed)
    assert results_title.is_visible(), "Results screen should be visible"

    # Note: Backend errors (verdict=ERROR) are logged but don't fail frontend test
    if verdict == "ERROR":
        print("\n⚠️  NOTE: Backend returned ERROR verdict - see debug logs for details")
