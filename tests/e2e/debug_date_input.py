"""
Debug script to inspect Streamlit date_input HTML structure
"""
from playwright.sync_api import sync_playwright
import time

def debug_date_input():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False, slow_mo=1000)
        page = browser.new_page()

        # Clear cookies
        page.context.clear_cookies()

        # Go to home page
        page.goto("http://localhost:8501")
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        # Click "Register with Invitation Code"
        register_btn = page.locator("button:has-text('Register with Invitation Code')")
        register_btn.wait_for(timeout=10000)
        register_btn.click()
        time.sleep(3)

        # Fill first 6 fields
        print("Filling first 6 fields...")
        page.locator("input[placeholder='John']").fill("Test")
        time.sleep(500)
        page.locator("input[placeholder='Doe']").fill("User")
        time.sleep(500)
        page.locator("input[placeholder='Johnny']").fill("Testy")
        time.sleep(500)
        page.locator("input[placeholder='student@example.com']").fill("test@test.com")
        time.sleep(500)
        page.locator("input[type='password'][placeholder='Min 6 characters']").fill("password123")
        time.sleep(500)
        page.locator("input[placeholder='+36 20 123 4567']").fill("+36 20 123 4567")
        time.sleep(500)

        print("\n✅ First 6 fields filled!")
        print("\n🔍 Now inspecting ALL input elements on page:")

        # Get ALL inputs
        all_inputs = page.locator("input").all()
        print(f"\nTotal inputs found: {len(all_inputs)}")

        for i, inp in enumerate(all_inputs):
            try:
                tag = inp.evaluate("el => el.outerHTML")
                visible = inp.is_visible()
                print(f"\n[{i}] Visible: {visible}")
                print(f"    HTML: {tag[:200]}...")
            except Exception as e:
                print(f"\n[{i}] Error: {e}")

        print("\n\n🔍 Looking specifically for date-related inputs:")

        # Try different selectors
        selectors = [
            "input[type='date']",
            "input[type='text'][aria-label*='Date']",
            "input[data-testid*='date']",
            "input[data-testid='stDateInput']",
            "input[aria-label='Date of Birth *']",
            "[data-testid='stDateInput'] input",
            "div[data-testid='stDateInput'] input"
        ]

        for selector in selectors:
            try:
                elements = page.locator(selector).all()
                if elements:
                    print(f"\n✅ Found {len(elements)} with selector: {selector}")
                    for elem in elements:
                        print(f"   HTML: {elem.evaluate('el => el.outerHTML')[:150]}...")
                else:
                    print(f"\n❌ No elements for: {selector}")
            except Exception as e:
                print(f"\n❌ Error with {selector}: {e}")

        print("\n\n📸 Taking screenshot for manual inspection...")
        page.screenshot(path="tests/e2e/screenshots/debug_date_input.png")
        print("Screenshot saved: tests/e2e/screenshots/debug_date_input.png")

        input("\nPress Enter to close browser...")
        browser.close()

if __name__ == "__main__":
    debug_date_input()
