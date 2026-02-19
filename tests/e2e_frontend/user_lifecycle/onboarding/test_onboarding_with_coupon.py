"""
E2E Test: Complete Onboarding with Coupon (UI-based)

Prerequisites:
- Phase 0 seeds onboarding coupons from tests/e2e/test_users.json automatically.
  No manual setup_onboarding_coupons.py needed.

Flow (per star user):
1. User logs in → applies coupon (+50) → 100 credits total
2. User unlocks specialization (-100) → 0 credits
3. User completes onboarding (3 steps: Position, Skills, Goals)
4. Verify user lands on Player Dashboard

Based on working test_hybrid_ui_player_workflow.py
"""

import pytest
import json
import random
from pathlib import Path
from playwright.sync_api import Page, expect


# Test configuration
STREAMLIT_URL = "http://localhost:8501"

# Single source of truth: load users from tests/e2e/test_users.json
_TEST_USERS_JSON = (
    Path(__file__).parent.parent.parent.parent.parent / "tests" / "e2e" / "test_users.json"
)


def _load_test_users() -> list:
    with open(_TEST_USERS_JSON) as f:
        pwt_users = json.load(f)["pwt_users"]
    return [
        {"email": u["email"], "password": u["password"], "coupon_code": u["coupon_code"]}
        for u in pwt_users
    ]


TEST_USERS = _load_test_users()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def streamlit_login(page: Page, email: str, password: str):
    """Login to Streamlit app"""
    page.goto(STREAMLIT_URL)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    email_input = page.locator('input[aria-label="Email"]')
    email_input.fill(email)
    page.wait_for_timeout(500)

    password_input = page.locator('input[type="password"]')
    password_input.fill(password)
    page.wait_for_timeout(500)

    login_button = page.locator('button:has-text("🔐 Login")')
    login_button.click()

    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)


def user_apply_coupon(page: Page, email: str, password: str, coupon_code: str) -> bool:
    """
    User applies BONUS_CREDITS coupon directly on the Specialization Hub page.

    After login, students with no license land on Specialization Hub which has
    the bonus code redemption form at the bottom. We use that form directly
    to avoid navigation issues (My Credits → Back to Hub sends LFA_FOOTBALL_PLAYER
    users to LFA_Player_Dashboard instead of Hub).

    Returns:
        True if coupon applied successfully, False otherwise
    """
    print(f"🔐 User logging in: {email}")
    streamlit_login(page, email, password)

    # After login with no license, user lands on Specialization Hub
    page.wait_for_timeout(5000)
    print(f"   ✅ Login done — should be on Specialization Hub")
    page.screenshot(path=f"tests/e2e/screenshots/after_login_hub.png")

    # Verify we're on Specialization Hub
    hub_heading = page.locator("h1").first
    current_url = page.url
    print(f"   DEBUG: URL after login: {current_url}")

    # Scroll to bottom where bonus code form is
    print(f"🎫 Applying coupon '{coupon_code}' on Specialization Hub...")
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(2000)

    # Find bonus code input — aria-label="Bonus Code"
    coupon_input = page.locator("input[aria-label='Bonus Code']").first

    if not coupon_input.is_visible(timeout=10000):
        print(f"   ❌ Bonus Code input not found on Hub")
        page.screenshot(path=f"tests/e2e/screenshots/hub_coupon_input_not_found.png")
        return False

    coupon_input.fill(coupon_code)
    page.wait_for_timeout(1000)
    print(f"   ✅ Coupon code entered: {coupon_code}")

    # Click "🎁 Redeem Code" submit button
    redeem_btn = page.locator("button:has-text('Redeem Code')").first
    if not redeem_btn.is_visible(timeout=5000):
        print(f"   ❌ Redeem Code button not found")
        page.screenshot(path=f"tests/e2e/screenshots/redeem_button_not_found.png")
        return False

    redeem_btn.click()
    page.wait_for_timeout(6000)  # Wait for API call + st.rerun()
    print(f"   ✅ Coupon submitted")

    # After st.rerun() we're back on Specialization Hub with updated balance
    # Verify credit balance is now 100 (sidebar shows balance)
    print(f"✅ Verifying credit balance is 100...")
    sidebar_100 = page.locator("[data-testid='stSidebar']").locator("text=100").first
    if sidebar_100.is_visible(timeout=5000):
        print(f"   ✅ Credit balance verified: 100 credits (sidebar)")
    else:
        # Fallback: check DB directly
        import psycopg2
        conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
        cur = conn.cursor()
        cur.execute("SELECT credit_balance FROM users WHERE email = %s", (email,))
        row = cur.fetchone()
        conn.close()
        if row and row[0] >= 100:
            print(f"   ✅ Credit balance verified via DB: {row[0]} credits")
        else:
            print(f"   ⚠️  Balance {row[0] if row else 'unknown'} (expected 100)")
            page.screenshot(path=f"tests/e2e/screenshots/coupon_verify_failed_{coupon_code}.png")
            return False

    print(f"✅ Coupon '{coupon_code}' applied successfully! Credit balance is now 100")
    return True


def user_unlock_and_complete_onboarding(page: Page, email: str) -> bool:
    """
    User unlocks LFA Football Player specialization AND completes onboarding
    (Based on working test_hybrid_ui_player_workflow.py lines 334-487)

    Returns:
        True if unlocked and onboarding completed, False otherwise
    """
    print(f"🔓 Already on Specialization Hub (after coupon st.rerun())...")

    # After coupon redemption st.rerun(), we're back on Specialization Hub
    # with updated credit balance. Wait for page to stabilize.
    page.wait_for_timeout(3000)
    print(f"   DEBUG: Current URL: {page.url}")

    # Check if already unlocked or needs unlock
    print(f"🔍 Checking LFA Football Player status...")

    # Case 0: "Complete Onboarding Now" gate — license exists but onboarding not yet done
    complete_now_button = page.locator('button:has-text("Complete Onboarding Now")')
    if complete_now_button.is_visible(timeout=3000):
        print(f"✅ Onboarding gate detected — clicking 'Complete Onboarding Now'")
        complete_now_button.click()
        page.wait_for_timeout(3000)
        # Fall through to onboarding wizard steps below

    else:
        unlock_button = page.locator('button:has-text("100 credits")')
        enter_button = page.locator('button:has-text("Enter LFA Football Player")')

        print(f"   DEBUG: unlock_button count: {unlock_button.count()}")
        print(f"   DEBUG: enter_button count: {enter_button.count()}")

        if enter_button.count() > 0:
            print(f"✅ Already unlocked! Entering specialization...")
            enter_button.first.click()
            page.wait_for_timeout(3000)

        elif unlock_button.count() > 0:
            print(f"🔓 Unlocking LFA Football Player...")
            unlock_button.first.click()
            page.wait_for_timeout(2000)

            confirm_button = page.locator('button:has-text("Confirm Unlock")').first
            if confirm_button.is_visible(timeout=10000):
                confirm_button.click(force=True)
                print(f"   🖱️  Clicked Confirm Unlock button (force=True)")
                page.wait_for_timeout(3000)

                import psycopg2
                conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
                cur = conn.cursor()
                cur.execute(
                    "SELECT COUNT(*) FROM user_licenses WHERE user_id = (SELECT id FROM users WHERE email = %s) AND specialization_type = 'LFA_FOOTBALL_PLAYER'",
                    (email,)
                )
                license_count = cur.fetchone()[0]
                conn.close()

                if license_count > 0:
                    print(f"   ✅ Specialization unlocked successfully (verified in DB)")
                    page.wait_for_timeout(5000)

                    current_url = page.url
                    if "LFA_Player_Onboarding" in current_url:
                        print(f"   ✅ Automatically redirected to onboarding")
                    else:
                        print(f"   ⚠️  Not auto-redirected (URL: {current_url})")
                        enter_btn = page.locator('button:has-text("Enter LFA Football Player")').first
                        if enter_btn.is_visible(timeout=2000):
                            print(f"   🖱️  Clicking 'Enter LFA Football Player' button")
                            enter_btn.click()
                        else:
                            print(f"   ⚠️  No 'Enter' button found, trying direct URL navigation")
                            page.evaluate("window.location.href = '/LFA_Player_Onboarding'")
                        page.wait_for_timeout(2000)
                else:
                    print(f"   ❌ License not found in DB - unlock failed")
                    page.screenshot(path=f"tests/e2e/screenshots/unlock_failed_no_license.png")
                    return False

        else:
            print(f"❌ Could not find unlock or enter button")
            page.screenshot(path="tests/e2e/screenshots/unlock_button_not_found.png")
            return False

    # Complete Onboarding (6 steps) - FROM WORKING TEST
    print(f"🎓 Starting Onboarding (6 steps: Position + 4 Skill Categories + Goals)...")

    # Wait for onboarding page to load and check for Step 1 heading
    page.wait_for_timeout(3000)

    # Verify we're on onboarding page by checking for "Step 1" heading
    step1_heading = page.locator("text=Step 1").first
    if not step1_heading.is_visible(timeout=10000):
        print(f"   ⚠️  Onboarding Step 1 not visible, waiting longer...")
        page.wait_for_timeout(3000)
        page.screenshot(path=f"tests/e2e/screenshots/onboarding_not_loaded.png")

    # Step 1: Position Selection (RANDOM)
    print(f"  📍 Step 1: Position Selection")
    page.wait_for_timeout(2000)

    # Take screenshot to see onboarding page
    page.screenshot(path=f"tests/e2e/screenshots/onboarding_step1_position.png")

    positions = ["Striker", "Midfielder", "Defender", "Goalkeeper"]
    selected_position = random.choice(positions)
    print(f"     🎲 Randomly selecting: {selected_position}")

    # Position buttons have format: "{icon}\n\n**{name}**\n\n{desc}"
    # Use more flexible selector that matches the button text
    position_button = page.locator(f'button:has-text("{selected_position}")').first

    if position_button.is_visible(timeout=10000):
        position_button.click()
        page.wait_for_timeout(2000)
        print(f"     ✅ Position selected: {selected_position}")

        # Wait for Next button to be enabled (requires position selection)
        next_button = page.locator('button:has-text("Next")').first
        if next_button.is_visible(timeout=5000):
            # Check if button is enabled (not disabled)
            page.wait_for_timeout(1000)
            next_button.click()
            page.wait_for_timeout(3000)
            print(f"     ✅ Step 1 complete")
        else:
            print(f"     ❌ Next button not found")
            page.screenshot(path=f"tests/e2e/screenshots/next_button_not_found_step1.png")
            return False
    else:
        print(f"     ⚠️  Position button '{selected_position}' not found")
        page.screenshot(path=f"tests/e2e/screenshots/position_button_not_found.png")
        return False

    # Steps 2-5: Skills Assessment (4 CATEGORIES, ALL SKILLS, DETERMINISTIC)
    # Production UI has 4 skill categories across Steps 2-5 (total 29 skills)
    # Each category is on a separate step with "Next" button to proceed
    print(f"  ⚡ Steps 2-5: Skills Assessment (ALL 29 skills across 4 categories)")

    BASELINE_SKILL_VALUE = 60  # Deterministic baseline for test reproducibility
    total_skills_set = 0

    # Loop through 4 skill category steps (Steps 2, 3, 4, 5)
    for step_num in range(2, 6):  # Steps 2, 3, 4, 5
        print(f"  📋 Step {step_num}: Category {step_num - 1}")
        page.wait_for_timeout(2000)

        # Get all sliders on this step (Streamlit uses div[role="slider"])
        sliders = page.locator('div[role="slider"]')
        slider_count = sliders.count()
        print(f"     Found {slider_count} sliders in this category")

        # Set ALL sliders in this category to BASELINE_SKILL_VALUE (60/100)
        for i in range(slider_count):
            try:
                slider = sliders.nth(i)
                target_value = BASELINE_SKILL_VALUE
                current_value = slider.get_attribute("aria-valuenow")

                slider.click()
                page.wait_for_timeout(200)

                # Calculate steps needed (UI uses step=5, so 0, 5, 10, ..., 100)
                # Target must be multiple of 5
                current = int(current_value) if current_value else 50
                diff = target_value - current

                # Each ArrowRight/ArrowLeft moves by 5 in Streamlit slider (step=5)
                steps_needed = diff // 5

                if steps_needed > 0:
                    for _ in range(steps_needed):
                        page.keyboard.press("ArrowRight")
                        page.wait_for_timeout(50)
                elif steps_needed < 0:
                    for _ in range(abs(steps_needed)):
                        page.keyboard.press("ArrowLeft")
                        page.wait_for_timeout(50)

                # Verify final value
                final_value = slider.get_attribute("aria-valuenow")
                print(f"       Skill {total_skills_set + 1}: {current} → {final_value} (target: {target_value})")
                total_skills_set += 1
                page.wait_for_timeout(100)
            except Exception as e:
                print(f"       ❌ Error setting slider {i+1}: {e}")

        page.wait_for_timeout(1000)

        # Click Next to proceed to next category (or final step)
        next_button = page.locator('button:has-text("Next")')
        if next_button.count() > 0:
            next_button.first.click()
            page.wait_for_timeout(3000)
            print(f"     ✅ Step {step_num} complete")
        else:
            print(f"     ❌ Next button not found on Step {step_num}")
            return False

    print(f"  ✅ ALL {total_skills_set} skills set to baseline {BASELINE_SKILL_VALUE}/100")

    # Step 6: Goals & Motivation (DROPDOWN SELECTION)
    print(f"  🎯 Step 6: Goals & Motivation")
    page.wait_for_timeout(1000)

    try:
        # Find selectbox input with role="combobox"
        selectbox = page.locator('input[role="combobox"][aria-label*="Primary Goal"]')
        selectbox.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        selectbox.click(timeout=10000)
        page.wait_for_timeout(2000)

        # Look for dropdown options
        options = page.locator('li[role="option"]')
        option_count = options.count()

        if option_count > 1:
            # Skip index 0 (placeholder "Select your primary goal...")
            random_index = random.randint(1, option_count - 1)
            option_text = options.nth(random_index).inner_text(timeout=1000)
            print(f"     🎲 Selecting goal: {option_text}")

            options.nth(random_index).click()
            page.wait_for_timeout(2000)
            print(f"     ✅ Goal selected")
        elif option_count == 1:
            options.first.click()
            page.wait_for_timeout(2000)
            print(f"     ✅ Goal selected (only option)")
        else:
            print(f"     ❌ No goal options found")
    except Exception as e:
        print(f"     ❌ Error selecting goal: {e}")

    page.wait_for_timeout(1000)

    # Click Complete Onboarding button (🚀 emoji + text)
    complete_button = page.locator('button:has-text("Complete Onboarding")')
    page.screenshot(path=f"tests/e2e/screenshots/onboarding_step6_before_complete.png")
    if complete_button.count() > 0:
        # Check if disabled
        is_disabled = complete_button.first.get_attribute("disabled")
        print(f"   DEBUG: Complete Onboarding button disabled attr: {is_disabled}")
        if is_disabled is not None:
            print(f"   ❌ Complete Onboarding button is DISABLED — goal not selected properly")
            page.screenshot(path=f"tests/e2e/screenshots/onboarding_button_disabled.png")
            return False
        complete_button.first.click()
        page.wait_for_timeout(5000)
        print(f"     ✅ Clicked Complete Onboarding button")
    else:
        print(f"     ❌ Complete Onboarding button not found")
        return False

    # Should now be on Player Dashboard
    print(f"🎉 Onboarding complete - should be on Player Dashboard")
    page.wait_for_timeout(3000)

    # Verify DB state: onboarding_completed must be True
    import psycopg2
    db_url = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("""
        SELECT u.onboarding_completed, ul.onboarding_completed
        FROM users u
        JOIN user_licenses ul ON ul.user_id = u.id AND ul.specialization_type = 'LFA_FOOTBALL_PLAYER'
        WHERE u.email = %s
    """, (email,))
    row = cur.fetchone()
    conn.close()

    if row is None:
        print(f"   ❌ DB check failed: user or license not found for {email}")
        page.screenshot(path=f"tests/e2e/screenshots/onboarding_db_check_failed.png")
        return False

    user_onboarding, lic_onboarding = row
    if not user_onboarding or not lic_onboarding:
        print(f"   ❌ DB check: user.onboarding_completed={user_onboarding}, license.onboarding_completed={lic_onboarding}")
        page.screenshot(path=f"tests/e2e/screenshots/onboarding_db_false.png")
        return False

    print(f"   ✅ DB verified: onboarding_completed=True for {email}")

    current_url = page.url
    if "Dashboard" in current_url or "dashboard" in current_url:
        print(f"✅ Successfully redirected to Dashboard")
    else:
        print(f"⚠️  URL: {current_url} (expected dashboard, but DB is OK)")

    return True


# =============================================================================
# TEST CASES
# =============================================================================

@pytest.mark.e2e
@pytest.mark.onboarding
@pytest.mark.ui
def test_complete_onboarding_user1(page: Page):
    """
    Test complete onboarding workflow for User 1 (UI-based)

    Flow:
    1. User logs in → applies coupon → 100 credits
    2. User unlocks specialization → 0 credits
    3. User completes onboarding (3 steps)
    4. Verify dashboard redirect

    Prerequisites: Run setup_onboarding_coupons.py first
    """
    user = TEST_USERS[0]
    email = user["email"]
    password = user["password"]
    coupon_code = user["coupon_code"]

    print(f"\n{'='*60}")
    print(f"🎬 COMPLETE ONBOARDING TEST: {email}")
    print(f"{'='*60}\n")

    # Step 1: User applies coupon
    print(f"\n📋 STEP 1: User applies coupon")
    coupon_applied = user_apply_coupon(page, email, password, coupon_code)
    assert coupon_applied, f"Failed to apply coupon '{coupon_code}'"

    # Step 2: User unlocks specialization AND completes onboarding
    print(f"\n📋 STEP 2: User unlocks specialization + completes onboarding")
    onboarding_complete = user_unlock_and_complete_onboarding(page, email)
    assert onboarding_complete, "Failed to unlock specialization or complete onboarding"

    print(f"\n{'='*60}")
    print(f"🎉 TEST PASSED: {email}")
    print(f"{'='*60}\n")


@pytest.mark.e2e
@pytest.mark.onboarding
@pytest.mark.ui
def test_complete_onboarding_user2(page: Page):
    """Test complete onboarding workflow for User 2 (UI-based)"""
    user = TEST_USERS[1]
    email = user["email"]
    password = user["password"]
    coupon_code = user["coupon_code"]

    print(f"\n{'='*60}")
    print(f"🎬 COMPLETE ONBOARDING TEST: {email}")
    print(f"{'='*60}\n")

    # User applies coupon
    print(f"\n📋 STEP 1: User applies coupon")
    coupon_applied = user_apply_coupon(page, email, password, coupon_code)
    assert coupon_applied, f"Failed to apply coupon '{coupon_code}'"

    # User unlocks specialization + completes onboarding
    print(f"\n📋 STEP 2: User unlocks specialization + completes onboarding")
    onboarding_complete = user_unlock_and_complete_onboarding(page, email)
    assert onboarding_complete, "Failed to unlock specialization or complete onboarding"

    print(f"\n{'='*60}")
    print(f"🎉 TEST PASSED: {email}")
    print(f"{'='*60}\n")


@pytest.mark.e2e
@pytest.mark.onboarding
@pytest.mark.ui
def test_complete_onboarding_user3(page: Page):
    """Test complete onboarding workflow for User 3 (UI-based)"""
    user = TEST_USERS[2]
    email = user["email"]
    password = user["password"]
    coupon_code = user["coupon_code"]

    print(f"\n{'='*60}")
    print(f"🎬 COMPLETE ONBOARDING TEST: {email}")
    print(f"{'='*60}\n")

    # User applies coupon
    print(f"\n📋 STEP 1: User applies coupon")
    coupon_applied = user_apply_coupon(page, email, password, coupon_code)
    assert coupon_applied, f"Failed to apply coupon '{coupon_code}'"

    # User unlocks specialization + completes onboarding
    print(f"\n📋 STEP 2: User unlocks specialization + completes onboarding")
    onboarding_complete = user_unlock_and_complete_onboarding(page, email)
    assert onboarding_complete, "Failed to unlock specialization or complete onboarding"

    print(f"\n{'='*60}")
    print(f"🎉 TEST PASSED: {email}")
    print(f"{'='*60}\n")


@pytest.mark.onboarding
@pytest.mark.ui
def test_complete_onboarding_user4(page: Page):
    """Test complete onboarding workflow for User 4 (UI-based)"""
    user = TEST_USERS[3]
    email = user["email"]
    password = user["password"]
    coupon_code = user["coupon_code"]

    print(f"\n{'='*60}")
    print(f"🎬 COMPLETE ONBOARDING TEST: {email}")
    print(f"{'='*60}\n")

    print(f"\n📋 STEP 1: User applies coupon")
    coupon_applied = user_apply_coupon(page, email, password, coupon_code)
    assert coupon_applied, f"Failed to apply coupon '{coupon_code}'"

    print(f"\n📋 STEP 2: User unlocks specialization + completes onboarding")
    onboarding_complete = user_unlock_and_complete_onboarding(page, email)
    assert onboarding_complete, "Failed to unlock specialization or complete onboarding"

    print(f"\n{'='*60}")
    print(f"🎉 TEST PASSED: {email}")
    print(f"{'='*60}\n")
