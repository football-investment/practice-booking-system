"""
Debug Script: Inspect Specialization Hub UI
Explores the actual UI to find correct button selectors for unlock and onboarding flows
"""

import time
from playwright.sync_api import sync_playwright

STREAMLIT_URL = "http://localhost:8501"
PLAYER_EMAIL = "k1sqx1@f1rstteamfc.hu"  # Player 3 - NO LICENSE YET!
PLAYER_PASSWORD = "TestPass123!"


def login_and_explore():
    """Login and explore Specialization Hub UI"""
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False, slow_mo=1000)
        page = browser.new_page()

        print("\n" + "="*80)
        print("SPECIALIZATION HUB UI EXPLORATION")
        print("="*80 + "\n")

        # Login
        print("STEP 1: Login")
        print("-" * 80)
        page.goto(STREAMLIT_URL)
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        email_input = page.locator('input[aria-label="Email"]')
        email_input.fill(PLAYER_EMAIL)
        time.sleep(0.5)

        password_input = page.locator('input[type="password"]')
        password_input.fill(PLAYER_PASSWORD)
        time.sleep(0.5)

        login_button = page.locator('button:has-text("🔐 Login")')
        login_button.click()

        page.wait_for_load_state("networkidle")
        time.sleep(3)

        print("✅ Logged in successfully\n")

        # Take screenshot of Student Hub
        page.screenshot(path="tests/e2e/screenshots/student_hub.png")
        print("📸 Screenshot: student_hub.png\n")

        # Navigate to Specialization Hub via direct URL (already the default page for students)
        print("STEP 2: Check if on Specialization Hub")
        print("-" * 80)

        # User should already be on Specialization Hub after login
        print("✅ Already on Specialization Hub (default student page)\n")

        # Take screenshot of Specialization Hub
        page.screenshot(path="tests/e2e/screenshots/specialization_hub_main.png")
        print("📸 Screenshot: specialization_hub_main.png\n")

        # Inspect all buttons on page
        print("STEP 3: Inspect all buttons on page")
        print("-" * 80)

        all_buttons = page.locator('button')
        button_count = all_buttons.count()
        print(f"Total buttons found: {button_count}\n")

        for i in range(min(button_count, 50)):  # Limit to first 50 buttons
            try:
                button = all_buttons.nth(i)
                text = button.inner_text(timeout=1000)
                if text and text.strip():
                    print(f"Button {i+1}: '{text}'")
            except:
                pass

        print("\n" + "-" * 80)
        print("STEP 4: Look for LFA Football Player section")
        print("-" * 80 + "\n")

        # Look for LFA Football Player text
        lfa_text = page.locator('text=/LFA.*Football.*Player/i')
        if lfa_text.count() > 0:
            print(f"✅ Found LFA Football Player text (count: {lfa_text.count()})")
        else:
            print("❌ LFA Football Player text not found")

        # Look for "Unlock" buttons
        unlock_buttons = page.locator('button:has-text("Unlock")')
        print(f"\n'Unlock' buttons found: {unlock_buttons.count()}")

        for i in range(unlock_buttons.count()):
            try:
                button = unlock_buttons.nth(i)
                text = button.inner_text(timeout=1000)
                print(f"  Unlock button {i+1}: '{text}'")
            except:
                pass

        # Look for buttons containing "100"
        credit_buttons = page.locator('button:has-text("100")')
        print(f"\nButtons containing '100': {credit_buttons.count()}")

        for i in range(credit_buttons.count()):
            try:
                button = credit_buttons.nth(i)
                text = button.inner_text(timeout=1000)
                print(f"  Button {i+1}: '{text}'")
            except:
                pass

        print("\n" + "-" * 80)
        print("STEP 5: Try clicking unlock button")
        print("-" * 80 + "\n")

        # Try finding and clicking unlock button - based on screenshot, it's "100 Credits"
        unlock_selectors = [
            'button:has-text("💰 100 Credits")',
            'button:has-text("100 Credits")',
            'button:has-text("🔓 Unlock Now")',
            'button:has-text("Unlock Now")',
            'button:has-text("Unlock")',
        ]

        unlock_clicked = False
        for selector in unlock_selectors:
            unlock_btn = page.locator(selector)
            if unlock_btn.count() > 0:
                print(f"✅ Found unlock button with: {selector}")
                print(f"   Count: {unlock_btn.count()}")

                # Get all matching buttons
                for i in range(unlock_btn.count()):
                    try:
                        button = unlock_btn.nth(i)
                        text = button.inner_text(timeout=1000)
                        print(f"   Button {i+1} text: '{text}'")

                        # Click the first one (LFA Football Player)
                        if i == 0 and not unlock_clicked:
                            button.click()
                            time.sleep(2)
                            unlock_clicked = True

                            page.screenshot(path="tests/e2e/screenshots/after_unlock_click.png")
                            print("\n📸 Screenshot: after_unlock_click.png\n")

                            # Look for confirmation dialog
                            confirm_buttons = page.locator('button:has-text("Confirm")')
                            cancel_buttons = page.locator('button:has-text("Cancel")')

                            print(f"'Confirm' buttons found: {confirm_buttons.count()}")
                            print(f"'Cancel' buttons found: {cancel_buttons.count()}")

                            if confirm_buttons.count() > 0:
                                for j in range(confirm_buttons.count()):
                                    try:
                                        button = confirm_buttons.nth(j)
                                        text = button.inner_text(timeout=1000)
                                        print(f"  Confirm button {j+1}: '{text}'")
                                    except:
                                        pass

                            if cancel_buttons.count() > 0:
                                for j in range(cancel_buttons.count()):
                                    try:
                                        button = cancel_buttons.nth(j)
                                        text = button.inner_text(timeout=1000)
                                        print(f"  Cancel button {j+1}: '{text}'")
                                    except:
                                        pass
                    except:
                        pass

                if unlock_clicked:
                    break

        # Wait to see the page
        print("\n" + "="*80)
        print("Waiting 30 seconds for manual inspection...")
        print("="*80 + "\n")
        time.sleep(30)

        browser.close()


if __name__ == "__main__":
    login_and_explore()
