"""
Debug script to manually test coupon modal opening in Firefox headed mode
"""
from playwright.sync_api import sync_playwright
import time

def debug_coupon_modal():
    with sync_playwright() as p:
        # Launch Firefox in headed mode
        browser = p.firefox.launch(headless=False, slow_mo=1000)
        page = browser.new_page()

        print("1. Navigating to Streamlit home...")
        page.goto("http://localhost:8501")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        print("2. Filling login form...")
        page.fill("input[aria-label='Email']", "admin@lfa.com")
        page.fill("input[aria-label='Password']", "admin123")

        print("3. Clicking login button...")
        page.click("button:has-text('Login')")
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        print("4. Current URL:", page.url)

        print("5. Clicking Financial tab...")
        page.click("button:has-text('💳 Financial')")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        print("6. Looking for 'Create Coupon' button...")
        create_btn = page.locator("button:has-text('Create Coupon')")
        print(f"   Found: {create_btn.count()} buttons")

        if create_btn.count() > 0:
            print("7. Clicking 'Create Coupon' button...")
            create_btn.click()
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            print("8. Looking for 'Type *' label...")
            type_label = page.locator("label:has-text('Type *')")
            print(f"   Found: {type_label.count()} labels")

            print("9. Looking for selectbox...")
            selectboxes = page.locator("[data-baseweb='select']")
            print(f"   Found: {selectboxes.count()} selectboxes")

            if selectboxes.count() > 0:
                for i in range(selectboxes.count()):
                    sb = selectboxes.nth(i)
                    is_visible = sb.is_visible()
                    print(f"   Selectbox {i}: visible={is_visible}")

                # Click the visible selectbox
                print("\n   Clicking visible selectbox...")
                for i in range(selectboxes.count()):
                    sb = selectboxes.nth(i)
                    if sb.is_visible():
                        sb.click()
                        print(f"   Clicked selectbox {i}")
                        break

                time.sleep(1)

                # Check for dropdown menu
                print("\n   Looking for dropdown menu...")
                listbox = page.locator("[role='listbox']")
                print(f"   Found [role='listbox']: {listbox.count()}")

                menu = page.locator("[role='menu']")
                print(f"   Found [role='menu']: {menu.count()}")

                options = page.locator("[role='option']")
                print(f"   Found [role='option']: {options.count()}")

            print("\n10. Taking screenshot...")
            page.screenshot(path="tests/e2e/screenshots/debug_coupon_modal.png")
            print("    Saved to: tests/e2e/screenshots/debug_coupon_modal.png")

            print("\n11. Waiting 10 seconds for manual inspection...")
            time.sleep(10)
        else:
            print("ERROR: 'Create Coupon' button not found!")
            page.screenshot(path="tests/e2e/screenshots/debug_financial_tab.png")

        browser.close()

if __name__ == "__main__":
    debug_coupon_modal()
