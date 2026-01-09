"""
Debug script to inspect the Instructor Dashboard after login.
"""

from playwright.sync_api import sync_playwright
import time

STREAMLIT_URL = "http://localhost:8501"

def debug_instructor_dashboard():
    """Debug what tabs are visible on Instructor Dashboard."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        context = browser.new_context()
        page = context.new_page()

        print("\n" + "="*80)
        print("🐛 DEBUG: Instructor Dashboard Tabs")
        print("="*80 + "\n")

        # Navigate to Streamlit
        page.goto(STREAMLIT_URL)
        page.wait_for_load_state("networkidle")

        # Login as instructor
        print("📧 Logging in as instructor...")
        text_inputs = page.locator("[data-testid='stTextInput'] input").all()
        text_inputs[0].fill("instructor@test.com")
        text_inputs[1].fill("instructor123")

        login_button = page.get_by_role("button", name="🔐 Login")
        login_button.click()

        page.wait_for_load_state("networkidle", timeout=10000)
        time.sleep(3)

        # Navigate to Instructor Dashboard
        try:
            instructor_dashboard_link = page.locator("text=Instructor Dashboard").first
            instructor_dashboard_link.click()
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(3)
        except:
            page.goto(f"{STREAMLIT_URL}/Instructor_Dashboard")
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(3)

        print(f"✅ Current URL: {page.url}\n")

        # Check all tabs using data-baseweb="tab"
        print("🔍 Finding tabs using data-baseweb='tab'...")
        tabs = page.locator("[data-baseweb='tab']").all()
        print(f"Found {len(tabs)} tabs\n")

        for i, tab in enumerate(tabs):
            try:
                tab_text = tab.inner_text(timeout=2000)
                is_visible = tab.is_visible()
                print(f"  Tab {i+1}: '{tab_text}' (visible: {is_visible})")
            except:
                print(f"  Tab {i+1}: [Error reading text]")

        # Also check for buttons with role="button"
        print("\n🔍 Finding buttons with role='button'...")
        buttons = page.get_by_role("button").all()
        print(f"Found {len(buttons)} buttons\n")

        for i, btn in enumerate(buttons[:20]):  # Show first 20
            try:
                btn_text = btn.inner_text(timeout=1000)
                is_visible = btn.is_visible()
                print(f"  Button {i+1}: '{btn_text}' (visible: {is_visible})")
            except:
                pass

        print("\n⏸️  Browser will stay open for 60 seconds for inspection...")
        time.sleep(60)

        browser.close()

if __name__ == "__main__":
    debug_instructor_dashboard()
