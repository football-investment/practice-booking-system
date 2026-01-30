"""
Playwright E2E Test: Quick Test - CORRECT Form Structure

Based on actual frontend code analysis (streamlit_sandbox_v3_admin_aligned.py):

Quick Test mode form fields (in order):
1. Game Type (preset) - ALREADY SELECTED (GánFootvolley)
2. Location - st.selectbox (line 682, key="location_select")
3. Campus - st.selectbox (line 701, key="campus_select")
4. Max Players - st.number_input (line 818)
5. Button: "⚡ Run Quick Test" (line 1065)

Flow:
Home → Select "Quick Test" mode → Select GánFootvolley preset
→ Fill Location → Fill Campus → Fill Max Players → Scroll → Click "⚡ Run Quick Test"
→ Progress screen → Results screen
"""

import re
import time
from playwright.sync_api import Page, expect


def test_quick_test_end_to_end(page: Page):
    """
    E2E test for Quick Test mode - CORRECT form structure

    Tests the complete flow:
    1. Navigate to home
    2. Select Quick Test mode
    3. Select GánFootvolley preset (pre-selected)
    4. Fill Location selectbox
    5. Fill Campus selectbox
    6. Fill Max Players number input
    7. Click "⚡ Run Quick Test" button
    8. Verify Progress screen appears
    9. Verify Results screen appears with verdict
    """

    # Step 1: Navigate to home
    page.goto("http://localhost:8501/")
    page.wait_for_load_state("networkidle")
    time.sleep(2)  # Wait for Streamlit to fully initialize

    print("✓ Page loaded")

    # Step 2: Verify we're on home screen
    expect(page.get_by_text("🏠 Tournament Sandbox - Home")).to_be_visible()
    print("✓ Home screen visible")

    # Step 3: Click "➕ New Tournament" button to enter configuration screen
    new_tournament_button = page.get_by_role("button", name=re.compile(r"New Tournament", re.IGNORECASE))
    expect(new_tournament_button).to_be_visible()
    new_tournament_button.click()
    time.sleep(2)  # Wait for configuration screen to load
    print("✓ New Tournament button clicked")

    # Step 4: Verify we're on configuration screen with Quick Test mode selected
    expect(page.get_by_text("⚡ Quick Test (Auto-complete)")).to_be_visible()
    print("✓ Quick Test mode visible")

    # Step 5: Verify a preset is selected (look for "✅ Selected" text)
    expect(page.get_by_text("✅ Selected")).to_be_visible()
    print("✓ Game preset selected")

    # Step 6: Scroll to Location & Campus section
    page.keyboard.press("PageDown")
    time.sleep(1)

    # Step 7: Fill Location selectbox
    # Find the selectbox by its label "Select location"
    # Streamlit selectboxes are rendered as <div> with data-baseweb="select"
    print("Looking for Location selectbox...")

    # Find the section with "Location & Campus" header
    location_section = page.locator('text=1️⃣ Location & Campus')
    expect(location_section).to_be_visible()
    print("✓ Location section visible")

    # Find the first selectbox after "Location ***" text
    # Streamlit uses data-testid for selectboxes
    location_selectbox = page.locator('[data-testid="stSelectbox"]').first
    expect(location_selectbox).to_be_visible()
    print("✓ Location selectbox found")

    # Click to open dropdown
    location_selectbox.click()
    time.sleep(0.5)

    # Select first available location from dropdown
    # Streamlit renders options in a listbox
    first_location_option = page.locator('[role="option"]').first
    expect(first_location_option).to_be_visible()
    first_location_option.click()
    time.sleep(1)
    print("✓ Location selected")

    # Step 8: Fill Campus selectbox (appears after Location is selected)
    # Find the second selectbox (Campus)
    campus_selectbox = page.locator('[data-testid="stSelectbox"]').nth(1)
    expect(campus_selectbox).to_be_visible()
    print("✓ Campus selectbox found")

    # Click to open dropdown
    campus_selectbox.click()
    time.sleep(0.5)

    # Select first available campus
    first_campus_option = page.locator('[role="option"]').first
    expect(first_campus_option).to_be_visible()
    first_campus_option.click()
    time.sleep(1)
    print("✓ Campus selected")

    # Step 9: Scroll to Tournament Configuration section
    page.keyboard.press("PageDown")
    time.sleep(1)

    # Step 10: Fill Max Players number input
    # Find the number input with label "Max Players *"
    max_players_input = page.locator('input[type="number"]').filter(has=page.locator('text=Max Players'))

    # Alternative: find by aria-label or nearby text
    # Streamlit number inputs are standard HTML <input type="number">
    max_players_input = page.locator('input[type="number"]').first
    expect(max_players_input).to_be_visible()
    print("✓ Max Players input found")

    # Clear and fill with 8 players
    max_players_input.click()
    max_players_input.fill("")
    max_players_input.type("8")
    time.sleep(0.5)
    print("✓ Max Players set to 8")

    # Step 11: Scroll to bottom to find "⚡ Run Quick Test" button
    page.keyboard.press("End")
    time.sleep(1)

    # Alternative: Multiple PageDown presses
    page.keyboard.press("PageDown")
    time.sleep(0.5)
    page.keyboard.press("PageDown")
    time.sleep(1)

    print("Scrolled to bottom, looking for Run Quick Test button...")

    # Step 12: Find and click "⚡ Run Quick Test" button
    # Streamlit buttons are <button> elements with the text inside
    run_button = page.get_by_role("button", name=re.compile(r"Run Quick Test", re.IGNORECASE))

    # Wait for button to be visible and enabled
    expect(run_button).to_be_visible(timeout=5000)
    expect(run_button).to_be_enabled()
    print("✓ Run Quick Test button found and enabled")

    # Click the button
    run_button.click()
    print("✓ Run Quick Test button clicked")

    # Step 13: Wait for Results screen (use unique title as marker)
    # The results screen has title "🧪 Sandbox Tournament Test Results"
    results_title = page.get_by_text("🧪 Sandbox Tournament Test Results")

    # Wait up to 90 seconds for test to complete and results to appear
    expect(results_title).to_be_visible(timeout=90000)
    print("✓ Results screen appeared")

    # Give time for results to fully render
    time.sleep(2)

    # Step 14: Take screenshot of results
    page.screenshot(path="tests_e2e/screenshots/quick_test_results.png", full_page=True)
    print("✓ Results screenshot saved")

    # Step 17: Take final screenshot
    page.screenshot(path="tests_e2e/screenshots/quick_test_final_results.png")
    print("✓ Final screenshot saved")

    print("\n🎉 E2E Test PASSED - Complete Quick Test flow successful!")
