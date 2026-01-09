"""
Interactive Playwright script to inspect Streamlit DOM structure.

This script opens a browser window and allows manual inspection of the
Streamlit UI to identify the correct selectors for automated testing.

Usage:
    python tests/e2e/inspect_streamlit_dom.py
"""

from playwright.sync_api import sync_playwright
import time

STREAMLIT_URL = "http://localhost:8501"

def inspect_streamlit_ui():
    """
    Open Streamlit UI in headed mode for manual inspection.
    Prints useful selector information.
    """
    with sync_playwright() as p:
        # Launch browser in headed mode (visible)
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        context = browser.new_context()
        page = context.new_page()

        print("\n" + "="*80)
        print("🔍 STREAMLIT DOM INSPECTOR")
        print("="*80 + "\n")

        # Navigate to Streamlit
        print(f"📍 Navigating to {STREAMLIT_URL}...")
        page.goto(STREAMLIT_URL)
        page.wait_for_load_state("networkidle")

        print("✅ Page loaded\n")

        # Try to find common Streamlit elements
        print("🔍 Searching for Streamlit elements...\n")

        # Check for text inputs
        text_inputs = page.locator("input[type='text']").all()
        print(f"📝 Found {len(text_inputs)} text inputs")

        # Check for data-testid attributes (Streamlit often uses these)
        testid_elements = page.locator("[data-testid]").all()
        print(f"🎯 Found {len(testid_elements)} elements with data-testid")

        if testid_elements:
            print("\n📋 First 10 data-testid values:")
            for i, elem in enumerate(testid_elements[:10]):
                testid = elem.get_attribute("data-testid")
                print(f"   {i+1}. {testid}")

        # Check for buttons
        buttons = page.locator("button").all()
        print(f"\n🔘 Found {len(buttons)} buttons")

        if buttons:
            print("\n📋 First 10 button texts:")
            for i, btn in enumerate(buttons[:10]):
                try:
                    text = btn.inner_text(timeout=1000)
                    print(f"   {i+1}. '{text}'")
                except:
                    print(f"   {i+1}. [No text]")

        # Check for stTextInput (Streamlit's text input wrapper)
        st_text_inputs = page.locator("[data-testid='stTextInput']").all()
        print(f"\n📝 Found {len(st_text_inputs)} Streamlit text inputs")

        # Check for forms
        forms = page.locator("form").all()
        print(f"\n📋 Found {len(forms)} forms")

        print("\n" + "="*80)
        print("🔍 MANUAL INSPECTION MODE")
        print("="*80)
        print("\n👁️  Browser window is now open for manual inspection.")
        print("💡 Use browser DevTools (F12) to inspect elements.")
        print("⏸️  This script will wait for 120 seconds before closing.")
        print("\n🔎 Look for these selector patterns in DevTools:")
        print("   - data-testid attributes")
        print("   - data-baseweb attributes")
        print("   - aria-label attributes")
        print("   - Streamlit-specific class names (st-*)")
        print("\n")

        # Wait for manual inspection
        time.sleep(120)

        print("\n✅ Inspection complete. Closing browser...")
        browser.close()

if __name__ == "__main__":
    inspect_streamlit_ui()
