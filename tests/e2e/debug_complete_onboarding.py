"""
Debug Script: Complete Onboarding Flow with Skills and Goals
Explores all 3 steps including slider manipulation and goal selection
"""

import time
import random
from playwright.sync_api import sync_playwright

STREAMLIT_URL = "http://localhost:8501"
PLAYER_EMAIL = "v4lv3rd3jr.77@f1rstteamfc.hu"
PLAYER_PASSWORD = "TestPass123!"


def complete_onboarding():
    """Complete full onboarding to see all steps"""
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False, slow_mo=1000)
        page = browser.new_page()

        print("\n" + "="*80)
        print("COMPLETE ONBOARDING FLOW")
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
        print("✅ Logged in\n")

        # Check if already unlocked or needs unlock
        unlock_button = page.locator('button:has-text("100 credits")')
        enter_button = page.locator('button:has-text("Enter LFA Football Player")')
        complete_onboarding_button = page.locator('button:has-text("Complete Onboarding Now")')

        if enter_button.count() > 0:
            print("✅ Already unlocked! Clicking 'Enter LFA Football Player'...")
            enter_button.first.click()
            time.sleep(3)
            print("✅ Entered LFA Football Player hub\n")

            # Check if onboarding prompt appears
            if complete_onboarding_button.count() > 0:
                print("⚠️ Onboarding not completed yet! Clicking 'Complete Onboarding Now'...")
                complete_onboarding_button.first.click()
                time.sleep(3)
                print("✅ Onboarding wizard started\n")

        elif unlock_button.count() > 0:
            print("Unlocking...")
            unlock_button.first.click()
            time.sleep(2)

            confirm_button = page.locator('button:has-text("✅ Confirm Unlock")')
            if confirm_button.count() > 0:
                confirm_button.first.click()
                time.sleep(3)
                print("✅ Unlocked - onboarding should start automatically\n")

        # Step 1: Position Selection (RANDOM)
        print("ONBOARDING STEP 1: Position Selection")
        print("-" * 80)

        # Random position selection
        positions = ["Striker", "Midfielder", "Defender", "Goalkeeper"]
        selected_position = random.choice(positions)

        print(f"🎲 Randomly selecting position: {selected_position}")

        position_button = page.locator(f'button:has-text("{selected_position}")')
        if position_button.count() > 0:
            print(f"✅ Clicking {selected_position}...")
            position_button.first.click()
            time.sleep(2)

            next_button = page.locator('button:has-text("Next")')
            if next_button.count() > 0:
                print("✅ Clicking Next...")
                next_button.first.click()
                time.sleep(3)

        # Step 2: Skills Assessment (RANDOM SKILL VALUES)
        print("ONBOARDING STEP 2: Skills Assessment")
        print("-" * 80)

        # Wait for page to load
        time.sleep(2)

        page.screenshot(path="tests/e2e/screenshots/debug_step2_skills.png")
        print("📸 Screenshot: debug_step2_skills.png\n")

        # Look for sliders - Streamlit uses div[role="slider"] not input[type="range"]
        sliders = page.locator('div[role="slider"]')
        slider_count = sliders.count()
        print(f"Found {slider_count} sliders\n")

        skill_names = ["Heading", "Shooting", "Passing", "Dribbling", "Defending", "Physical"]

        # Set each slider to RANDOM value (1-10)
        for i in range(min(slider_count, len(skill_names))):
            try:
                slider = sliders.nth(i)
                random_value = random.randint(1, 10)

                # Get current value
                current_value = slider.get_attribute("aria-valuenow")
                skill_name = skill_names[i] if i < len(skill_names) else f"Skill {i+1}"

                print(f"  {skill_name}: current={current_value}, setting to {random_value}...")

                # Streamlit sliders: click and use keyboard arrows to set value
                # Or we can use ArrowRight/ArrowLeft keys
                slider.click()
                time.sleep(0.2)

                # Calculate difference and use arrow keys
                current = int(current_value) if current_value else 5
                diff = random_value - current

                if diff > 0:
                    # Press ArrowRight 'diff' times
                    for _ in range(diff):
                        page.keyboard.press("ArrowRight")
                        time.sleep(0.05)
                elif diff < 0:
                    # Press ArrowLeft 'abs(diff)' times
                    for _ in range(abs(diff)):
                        page.keyboard.press("ArrowLeft")
                        time.sleep(0.05)

                print(f"  ✅ {skill_name}: {random_value}/10")
                time.sleep(0.2)

            except Exception as e:
                print(f"  ❌ Error setting slider {i+1}: {e}")

        time.sleep(2)
        page.screenshot(path="tests/e2e/screenshots/debug_step2_skills_set.png")
        print("\n📸 Screenshot: debug_step2_skills_set.png\n")

        # Click Next to go to Step 3
        next_button = page.locator('button:has-text("Next")')
        if next_button.count() > 0:
            print("✅ Clicking Next to Step 3...")
            next_button.first.click()
            time.sleep(3)

        page.screenshot(path="tests/e2e/screenshots/debug_step3_goals.png")
        print("📸 Screenshot: debug_step3_goals.png\n")

        # Step 3: Goals & Motivation (RANDOM GOAL SELECTION)
        print("ONBOARDING STEP 3: Goals & Motivation")
        print("-" * 80)

        # Look for dropdown/selectbox with "Select your primary goal..."
        print("Looking for goal selection dropdown...\n")

        # Wait a bit for page to stabilize
        time.sleep(1)

        # Streamlit selectbox - find the clickable dropdown
        # The selectbox is an input with role="combobox"
        try:
            print("Clicking on selectbox...")

            # Find the input element with role="combobox" for Primary Goal
            selectbox = page.locator('input[role="combobox"][aria-label*="Primary Goal"]')
            selectbox.scroll_into_view_if_needed()
            time.sleep(0.5)

            # Click on it to open dropdown
            selectbox.click(timeout=10000)
            time.sleep(2)

            print("✅ Selectbox clicked, looking for options...")

            # Look for dropdown options (Streamlit creates a listbox with options)
            options = page.locator('li[role="option"]')
            option_count = options.count()

            print(f"Found {option_count} goal options:\n")

            # List all options
            option_texts = []
            for i in range(option_count):
                try:
                    text = options.nth(i).inner_text(timeout=1000)
                    option_texts.append(text)
                    print(f"  {i+1}. {text}")
                except:
                    pass

            # Select random option (skip first if it's placeholder)
            if option_count > 0:
                random_index = random.randint(0, option_count - 1)
                selected_goal = option_texts[random_index] if random_index < len(option_texts) else f"Option {random_index + 1}"

                print(f"\n🎲 Randomly selecting goal: {selected_goal}")

                options.nth(random_index).click()
                time.sleep(2)
                print("✅ Goal selected\n")
            else:
                print("❌ No options found in dropdown")

        except Exception as e:
            print(f"❌ Error with goal selection: {e}")

        page.screenshot(path="tests/e2e/screenshots/debug_step3_goal_selected.png")
        print("📸 Screenshot: debug_step3_goal_selected.png\n")

        # Click "Complete" button to finish onboarding
        print("-" * 80)
        print("Completing onboarding...")
        print("-" * 80 + "\n")

        complete_button = page.locator('button:has-text("Complete")')
        if complete_button.count() > 0:
            print("✅ Found Complete button - clicking...")
            complete_button.first.click()
            time.sleep(3)
            print("✅ Onboarding completed!\n")

            page.screenshot(path="tests/e2e/screenshots/debug_onboarding_complete.png")
            print("📸 Screenshot: debug_onboarding_complete.png\n")
        else:
            print("❌ Complete button not found")

        # Wait for inspection
        print("\n" + "="*80)
        print("Waiting 30 seconds for manual inspection...")
        print("="*80 + "\n")
        time.sleep(30)

        browser.close()


if __name__ == "__main__":
    complete_onboarding()
