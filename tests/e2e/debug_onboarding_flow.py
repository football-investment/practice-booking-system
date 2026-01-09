"""
Debug Script: Explore Onboarding Flow
Clicks confirm unlock and explores the 3-step onboarding wizard
"""

import time
from playwright.sync_api import sync_playwright

STREAMLIT_URL = "http://localhost:8501"
PLAYER_EMAIL = "v4lv3rd3jr.77@f1rstteamfc.hu"
PLAYER_PASSWORD = "TestPass123!"


def login_and_explore_onboarding():
    """Login, unlock specialization, and explore onboarding flow"""
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False, slow_mo=1000)
        page = browser.new_page()

        print("\n" + "="*80)
        print("ONBOARDING FLOW EXPLORATION")
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

        # Unlock LFA Football Player
        print("STEP 2: Unlock LFA Football Player")
        print("-" * 80)

        unlock_button = page.locator('button:has-text("100 credits")')
        if unlock_button.count() > 0:
            print("✅ Found unlock button")
            unlock_button.first.click()
            time.sleep(2)

            page.screenshot(path="tests/e2e/screenshots/onboarding_unlock_dialog.png")
            print("📸 Screenshot: onboarding_unlock_dialog.png\n")

            # Click Confirm Unlock
            confirm_button = page.locator('button:has-text("✅ Confirm Unlock")')
            if confirm_button.count() > 0:
                print("✅ Found Confirm Unlock button - clicking...")
                confirm_button.first.click()
                time.sleep(3)
                print("✅ Unlock confirmed!\n")

                page.screenshot(path="tests/e2e/screenshots/onboarding_after_unlock.png")
                print("📸 Screenshot: onboarding_after_unlock.png\n")
            else:
                print("❌ Confirm Unlock button not found\n")
        else:
            print("⚠️  Already unlocked - skipping unlock step\n")

        # Explore onboarding screens
        print("STEP 3: Explore Onboarding Wizard")
        print("-" * 80 + "\n")

        # Wait for onboarding to appear
        time.sleep(3)

        # Look for onboarding-related text
        onboarding_texts = [
            'text=/position/i',
            'text=/skill/i',
            'text=/goal/i',
            'text=/onboard/i',
            'text=/welcome/i',
        ]

        for text_selector in onboarding_texts:
            text = page.locator(text_selector)
            if text.count() > 0:
                print(f"✅ Found text matching: {text_selector}")

        # Look for all buttons on page
        print("\n📋 All buttons on page:")
        all_buttons = page.locator('button')
        button_count = all_buttons.count()
        print(f"Total buttons: {button_count}\n")

        for i in range(min(button_count, 50)):
            try:
                button = all_buttons.nth(i)
                text = button.inner_text(timeout=1000)
                if text and text.strip():
                    print(f"  Button {i+1}: '{text}'")
            except:
                pass

        # Take screenshot
        page.screenshot(path="tests/e2e/screenshots/onboarding_step1.png")
        print("\n📸 Screenshot: onboarding_step1.png\n")

        # Look for position buttons
        print("-" * 80)
        print("STEP 4: Look for Position Selection Buttons")
        print("-" * 80 + "\n")

        position_selectors = [
            'button:has-text("GK")',
            'button:has-text("DEF")',
            'button:has-text("MID")',
            'button:has-text("FWD")',
            'button:has-text("STRIKER")',
            'button:has-text("GOALKEEPER")',
            'button:has-text("DEFENDER")',
            'button:has-text("MIDFIELDER")',
        ]

        for selector in position_selectors:
            btn = page.locator(selector)
            if btn.count() > 0:
                print(f"✅ Found position button: {selector} (count: {btn.count()})")
                for i in range(btn.count()):
                    try:
                        text = btn.nth(i).inner_text(timeout=1000)
                        print(f"   Button {i+1} text: '{text}'")
                    except:
                        pass

        # Try clicking MID button
        print("\n-" * 80)
        print("STEP 5: Try clicking MID position")
        print("-" * 80 + "\n")

        mid_button = page.locator('button:has-text("MID")')
        if mid_button.count() > 0:
            print("✅ Found MID button - clicking...")
            mid_button.first.click()
            time.sleep(2)

            page.screenshot(path="tests/e2e/screenshots/onboarding_step2.png")
            print("📸 Screenshot: onboarding_step2.png\n")

            # Look for "Next" button
            next_button = page.locator('button:has-text("Next")')
            if next_button.count() > 0:
                print("✅ Found Next button - clicking...")
                next_button.first.click()
                time.sleep(2)

                page.screenshot(path="tests/e2e/screenshots/onboarding_step3.png")
                print("📸 Screenshot: onboarding_step3.png\n")
        else:
            print("❌ MID button not found")

        # Wait for manual inspection
        print("\n" + "="*80)
        print("Waiting 30 seconds for manual inspection...")
        print("="*80 + "\n")
        time.sleep(30)

        browser.close()


if __name__ == "__main__":
    login_and_explore_onboarding()
