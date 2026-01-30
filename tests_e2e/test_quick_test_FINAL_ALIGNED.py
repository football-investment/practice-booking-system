"""
Playwright E2E Test: Quick Test - 1:1 Frontend Flow Alignment

Based on exact frontend click-flow:
Home → Config → Location → Campus → Max Players → Run Quick Test → Results

This test follows the EXACT sequence a human would use.
"""

import re
import time
from playwright.sync_api import Page, expect


def test_quick_test_exact_frontend_flow(page: Page):
    """
    E2E test following EXACT frontend flow sequence

    Flow:
    1. Home screen → Click "➕ New Tournament"
    2. Config screen → Verify Quick Test selected
    3. Config screen → Verify GānFootvolley preset selected
    4. Scroll → Location & Campus section
    5. Select Location → "Vienna Academy"
    6. Select Campus → "Vienna Main Campus" (enabled after Location)
    7. Scroll → Tournament Configuration section
    8. Set Max Players → 8
    9. Scroll → Bottom (End key)
    10. Click "⚡ Run Quick Test"
    11. Wait → Results screen appears
    """

    print("\n" + "="*80)
    print("QUICK TEST - EXACT FRONTEND FLOW")
    print("="*80)

    # ============================================================
    # SCREEN 1: HOME
    # ============================================================
    print("\n[SCREEN 1: HOME]")

    # Step 1: Navigate to home
    print("→ Loading http://localhost:8501/")
    page.goto("http://localhost:8501/")
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    print("  ✓ Page loaded")

    # Step 2: Verify Home screen elements
    print("→ Verifying Home screen...")
    expect(page.get_by_text("🏠 Tournament Sandbox - Home")).to_be_visible()
    print("  ✓ Home screen visible")

    # Step 3: Click "➕ New Tournament" button
    print("→ Clicking '➕ New Tournament' button...")
    new_tournament_button = page.get_by_role("button", name=re.compile(r"New Tournament", re.IGNORECASE))
    expect(new_tournament_button).to_be_visible()
    new_tournament_button.click()
    time.sleep(2)  # Wait for screen transition
    print("  ✓ Button clicked → navigating to Config screen")

    # ============================================================
    # SCREEN 2: CONFIGURATION
    # ============================================================
    print("\n[SCREEN 2: CONFIGURATION]")

    # Step 4: Verify Quick Test mode is selected (default)
    print("→ Verifying Quick Test mode selected...")
    expect(page.get_by_text("⚡ Quick Test (Auto-complete)")).to_be_visible()
    print("  ✓ Quick Test mode active")

    # Step 5: Verify GānFootvolley preset is selected (default)
    print("→ Verifying game preset selected...")
    expect(page.get_by_text("✅ Selected")).to_be_visible()
    print("  ✓ Game preset selected")

    # Step 6: Scroll to Location & Campus section
    print("→ Scrolling to Location & Campus section...")
    page.keyboard.press("PageDown")
    time.sleep(1)
    print("  ✓ Scrolled")

    # Step 7: Verify Location & Campus section visible
    print("→ Verifying Location & Campus section...")
    location_section = page.locator('text=1️⃣ Location & Campus')
    expect(location_section).to_be_visible()
    print("  ✓ Section visible")

    # Step 8: Select Location
    print("→ Selecting Location...")
    location_selectbox = page.locator('[data-testid="stSelectbox"]').first
    expect(location_selectbox).to_be_visible()
    location_selectbox.click()
    time.sleep(0.5)

    # Select first location option
    first_location = page.locator('[role="option"]').first
    expect(first_location).to_be_visible()
    first_location.click()
    time.sleep(1)
    print("  ✓ Location selected (first option)")

    # Step 9: Select Campus (NOW enabled after Location selection)
    print("→ Selecting Campus...")
    campus_selectbox = page.locator('[data-testid="stSelectbox"]').nth(1)
    expect(campus_selectbox).to_be_visible()
    campus_selectbox.click()
    time.sleep(0.5)

    # Select first campus option
    first_campus = page.locator('[role="option"]').first
    expect(first_campus).to_be_visible()
    first_campus.click()
    time.sleep(1)
    print("  ✓ Campus selected (first option)")

    # Step 10: Scroll to Tournament Configuration section
    print("→ Scrolling to Tournament Configuration section...")
    page.keyboard.press("PageDown")
    time.sleep(1)
    print("  ✓ Scrolled")

    # Step 11: Set Max Players to 8
    print("→ Setting Max Players to 8...")
    max_players_input = page.locator('input[type="number"]').first
    expect(max_players_input).to_be_visible()

    # Clear and enter 8
    max_players_input.click()
    max_players_input.fill("")
    max_players_input.type("8")
    time.sleep(0.5)
    print("  ✓ Max Players = 8")

    # Step 12: Scroll to bottom (End key)
    print("→ Scrolling to bottom...")
    page.keyboard.press("End")
    time.sleep(1)

    # Additional scrolls to ensure button is visible
    page.keyboard.press("PageDown")
    time.sleep(0.5)
    page.keyboard.press("PageDown")
    time.sleep(1)
    print("  ✓ Scrolled to bottom")

    # Step 13: Find "⚡ Run Quick Test" button
    print("→ Finding 'Run Quick Test' button...")
    run_button = page.get_by_role("button", name=re.compile(r"Run Quick Test", re.IGNORECASE))

    expect(run_button).to_be_visible(timeout=5000)
    expect(run_button).to_be_enabled()
    print("  ✓ Button found and enabled")

    # Step 14: Click "⚡ Run Quick Test"
    print("→ Clicking 'Run Quick Test' button...")
    run_button.click()
    print("  ✓ Button clicked → API call initiated")

    # ============================================================
    # SCREEN 3: PROGRESS (Transitional)
    # ============================================================
    print("\n[SCREEN 3: PROGRESS]")
    print("→ Waiting for backend processing...")
    print("  (Screen may transition quickly to Results)")

    # ============================================================
    # SCREEN 4: RESULTS
    # ============================================================
    print("\n[SCREEN 4: RESULTS]")

    # Step 15: Wait for Results screen
    print("→ Waiting for Results screen...")
    results_title = page.get_by_text("🧪 Sandbox Tournament Test Results")

    expect(results_title).to_be_visible(timeout=90000)
    print("  ✓ Results screen appeared")

    # Wait for full render
    time.sleep(2)

    # Step 16: Take screenshot
    print("→ Taking screenshot...")
    page.screenshot(path="tests_e2e/screenshots/quick_test_final_aligned.png", full_page=True)
    print("  ✓ Screenshot saved")

    # Step 17: Verify Results content exists
    print("→ Verifying Results content...")

    # Check for Insights section (always present)
    insights_section = page.get_by_text("💡 Insights")
    expect(insights_section).to_be_visible()
    print("  ✓ Insights section visible")

    # Check for Export Options
    export_section = page.get_by_text("📤 Export Options")
    expect(export_section).to_be_visible()
    print("  ✓ Export Options visible")

    print("\n" + "="*80)
    print("✅ TEST PASSED - Complete frontend flow executed successfully")
    print("="*80)
    print("\nNext step: Check Results screen for WORKING vs ERROR verdict")
    print("If ERROR appears, backend debugging required (not frontend issue)")
