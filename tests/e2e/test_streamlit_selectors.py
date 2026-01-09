"""
Test script to identify and validate Streamlit selectors for login and navigation.

This script tests various selector strategies to find the most reliable approach
for Playwright automation of the Streamlit UI.
"""

from playwright.sync_api import sync_playwright
import time

STREAMLIT_URL = "http://localhost:8501"

def test_streamlit_selectors():
    """
    Test different selector strategies for Streamlit components.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context()
        page = context.new_page()

        print("\n" + "="*80)
        print("🧪 TESTING STREAMLIT SELECTORS")
        print("="*80 + "\n")

        # Navigate to Streamlit
        page.goto(STREAMLIT_URL)
        page.wait_for_load_state("networkidle")
        print("✅ Page loaded\n")

        # ====================================================================
        # TEST 1: Find text inputs using data-testid
        # ====================================================================
        print("📝 TEST 1: Locating text inputs...")

        try:
            # Get all stTextInput containers
            text_input_containers = page.locator("[data-testid='stTextInput']").all()
            print(f"   Found {len(text_input_containers)} stTextInput containers")

            # For each container, find the actual input element
            for i, container in enumerate(text_input_containers):
                # Streamlit wraps actual inputs inside stTextInput divs
                actual_input = container.locator("input").first

                # Get input attributes
                input_type = actual_input.get_attribute("type")
                input_aria_label = actual_input.get_attribute("aria-label")
                input_placeholder = actual_input.get_attribute("placeholder")

                print(f"\n   Input {i+1}:")
                print(f"      Type: {input_type}")
                print(f"      Aria-label: {input_aria_label}")
                print(f"      Placeholder: {input_placeholder}")

        except Exception as e:
            print(f"   ❌ Failed: {e}")

        # ====================================================================
        # TEST 2: Find login button
        # ====================================================================
        print("\n\n🔘 TEST 2: Locating login button...")

        try:
            # Try to find button with text "Login"
            login_button = page.get_by_role("button", name="🔐 Login")
            if login_button.count() > 0:
                print(f"   ✅ Found login button using role + name")
                print(f"      Visible: {login_button.is_visible()}")
            else:
                print(f"   ⚠️ Login button not found with role + name")

        except Exception as e:
            print(f"   ❌ Failed: {e}")

        # ====================================================================
        # TEST 3: Try to fill login form
        # ====================================================================
        print("\n\n📋 TEST 3: Testing login form interaction...")

        try:
            # Strategy: Use stTextInput containers and locate input inside
            text_inputs = page.locator("[data-testid='stTextInput'] input").all()

            if len(text_inputs) >= 2:
                print(f"   Found {len(text_inputs)} input fields")

                # First input should be email
                email_input = text_inputs[0]
                email_input.fill("test@example.com")
                print(f"   ✅ Filled email field")

                # Second input should be password
                password_input = text_inputs[1]
                password_input.fill("test123")
                print(f"   ✅ Filled password field")

                time.sleep(1)

                # Click login button
                login_btn = page.get_by_role("button", name="🔐 Login")
                if login_btn.count() > 0:
                    print(f"   ⚠️ Login button found, but NOT clicking (test only)")
                    # login_btn.click()  # Don't actually click in test mode

            else:
                print(f"   ❌ Expected 2 inputs, found {len(text_inputs)}")

        except Exception as e:
            print(f"   ❌ Failed: {e}")

        # ====================================================================
        # TEST 4: Check for tabs/navigation
        # ====================================================================
        print("\n\n📑 TEST 4: Checking tab navigation...")

        try:
            # Streamlit tabs use data-baseweb="tab"
            tabs = page.locator("[data-baseweb='tab']").all()
            print(f"   Found {len(tabs)} tabs")

            for i, tab in enumerate(tabs[:5]):  # Show first 5
                tab_text = tab.inner_text()
                print(f"      Tab {i+1}: '{tab_text}'")

        except Exception as e:
            print(f"   ❌ Failed: {e}")

        # ====================================================================
        # SUMMARY
        # ====================================================================
        print("\n" + "="*80)
        print("📋 SELECTOR STRATEGY SUMMARY")
        print("="*80)
        print("\n✅ RECOMMENDED SELECTORS:")
        print("   - Text inputs: page.locator(\"[data-testid='stTextInput'] input\")")
        print("   - Buttons: page.get_by_role(\"button\", name=\"Button Text\")")
        print("   - Tabs: page.locator(\"[data-baseweb='tab']\")")
        print("\n💡 KEY INSIGHTS:")
        print("   - Streamlit wraps inputs in stTextInput containers")
        print("   - Use .locator('input') inside stTextInput to get actual input element")
        print("   - Button selectors work with get_by_role + emoji + text")
        print("\n")

        time.sleep(5)
        browser.close()

if __name__ == "__main__":
    test_streamlit_selectors()
