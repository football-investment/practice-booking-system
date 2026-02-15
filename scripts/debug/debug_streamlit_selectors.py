"""
DEBUG SCRIPT: Analyze Streamlit DOM structure for Playwright selectors

This script opens the Streamlit app and inspects the actual DOM structure
to find reliable selectors for selectbox elements.

Run: python debug_streamlit_selectors.py
"""
from playwright.sync_api import sync_playwright
import time

STREAMLIT_URL = "http://localhost:8501"

def debug_streamlit_form():
    """Open Streamlit app and inspect form elements"""
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False, slow_mo=1000)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        print("🔍 Opening Streamlit app...")
        page.goto(STREAMLIT_URL)
        time.sleep(3)

        print("\n📋 Waiting for app to load...")
        page.wait_for_selector("[data-testid='stAppViewContainer']", timeout=15000)
        time.sleep(2)

        # Click "New Tournament" button
        print("\n🖱️  Clicking 'New Tournament' button...")
        new_tournament_btn = page.get_by_text("New Tournament", exact=True)
        new_tournament_btn.click()
        time.sleep(3)

        print("\n✅ Form opened! Now analyzing elements...\n")

        # ====================================================================
        # ANALYZE TEXT INPUTS
        # ====================================================================
        print("="*80)
        print("📝 TEXT INPUT ANALYSIS")
        print("="*80)

        text_inputs = page.locator('input[type="text"]').all()
        print(f"Found {len(text_inputs)} text inputs\n")

        for i, input_elem in enumerate(text_inputs):
            try:
                parent = input_elem.locator('xpath=ancestor::div[@data-testid]').first
                testid = parent.get_attribute('data-testid') if parent.count() > 0 else "N/A"
                label = input_elem.get_attribute('aria-label') or "N/A"
                placeholder = input_elem.get_attribute('placeholder') or "N/A"

                print(f"Input {i+1}:")
                print(f"  - data-testid: {testid}")
                print(f"  - aria-label: {label}")
                print(f"  - placeholder: {placeholder}\n")
            except Exception as e:
                print(f"Input {i+1}: Error - {e}\n")

        # ====================================================================
        # ANALYZE SELECTBOXES
        # ====================================================================
        print("="*80)
        print("📦 SELECTBOX ANALYSIS")
        print("="*80)

        # Try different selectors
        selectors_to_try = [
            ('[data-baseweb="select"]', "BaseWeb Select"),
            ('[data-testid*="selectbox"]', "Testid Selectbox"),
            ('[data-testid="stSelectbox"]', "stSelectbox"),
            ('div[role="combobox"]', "Role Combobox"),
        ]

        for selector, name in selectors_to_try:
            elements = page.locator(selector).all()
            print(f"\n{name} ('{selector}'): Found {len(elements)} elements")

            if len(elements) > 0:
                for i, elem in enumerate(elements[:5]):  # First 5 only
                    try:
                        # Get parent with label
                        parent_label = elem.locator('xpath=ancestor::div[contains(@class, "stSelectbox")]').first
                        label_elem = parent_label.locator('label').first if parent_label.count() > 0 else None
                        label_text = label_elem.inner_text() if label_elem and label_elem.count() > 0 else "N/A"

                        # Get current value
                        value_elem = elem.locator('[id*="value"]').first
                        current_value = value_elem.inner_text() if value_elem.count() > 0 else "N/A"

                        print(f"  Selectbox {i+1}:")
                        print(f"    - Label: {label_text}")
                        print(f"    - Current value: {current_value}")
                    except Exception as e:
                        print(f"  Selectbox {i+1}: Error - {e}")

        # ====================================================================
        # ANALYZE NUMBER INPUTS
        # ====================================================================
        print("\n" + "="*80)
        print("🔢 NUMBER INPUT ANALYSIS")
        print("="*80)

        number_inputs = page.locator('input[type="number"]').all()
        print(f"Found {len(number_inputs)} number inputs\n")

        for i, input_elem in enumerate(number_inputs):
            try:
                parent = input_elem.locator('xpath=ancestor::div[@data-testid]').first
                testid = parent.get_attribute('data-testid') if parent.count() > 0 else "N/A"
                label = input_elem.get_attribute('aria-label') or "N/A"

                print(f"Number Input {i+1}:")
                print(f"  - data-testid: {testid}")
                print(f"  - aria-label: {label}\n")
            except Exception as e:
                print(f"Number Input {i+1}: Error - {e}\n")

        # ====================================================================
        # FULL PAGE SNAPSHOT
        # ====================================================================
        print("="*80)
        print("📸 TAKING SCREENSHOT")
        print("="*80)

        page.screenshot(path="debug_streamlit_form.png", full_page=True)
        print("✅ Screenshot saved: debug_streamlit_form.png")

        # Keep browser open for manual inspection
        print("\n" + "="*80)
        print("⏸️  BROWSER PAUSED FOR MANUAL INSPECTION")
        print("="*80)
        print("Press ENTER in terminal to close browser...")
        input()

        browser.close()

if __name__ == "__main__":
    print("🚀 Starting Streamlit DOM Analysis Tool")
    print("="*80)
    print("IMPORTANT: Make sure Streamlit app is running on http://localhost:8501")
    print("="*80)
    print()

    try:
        debug_streamlit_form()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nMake sure:")
        print("1. Streamlit app is running (streamlit run streamlit_sandbox_v3_admin_aligned.py)")
        print("2. PostgreSQL database is running")
        print("3. FastAPI backend is running")
