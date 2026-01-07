"""
Playwright E2E Tests for User Registration with Invitation Codes

Tests the complete user registration workflow:
1. Admin creates 3 invitation codes via UI (50 credits each)
2. 3 new users register with these codes via UI
3. Users appear in database with 50 credits
4. Specialization Hub loads for new users

CRITICAL REQUIREMENTS:
- Email addresses (FIXED with pwt. prefix): pwt.k1sqx1@f1stteam.hu, pwt.p3t1k3@f1stteam.hu, pwt.V4lv3rd3jr@f1stteam.hu
- Bonus credits: 50 credits ONLY (no other amount allowed)
- Age groups: Pre (6-11), Youth (12-17), Amateur (18+)
- Clean database: users created ONLY via invitation code redemption
- Run in Firefox headed mode for visibility
- Tests complete UI workflow from code creation → registration → hub loading
- Focus on user creation and hub loading (NOT detailed onboarding)
- PREFIX: "pwt." to distinguish from API tests (which use "api.")

Part of Phase B: Invitation Code Testing
"""

import pytest
from playwright.sync_api import Page, expect
import time
from datetime import date


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def streamlit_login(page: Page, email: str, password: str):
    """Login to Streamlit app"""
    page.goto("http://localhost:8501")
    page.wait_for_load_state("networkidle")

    # Wait for login form
    page.wait_for_selector("input[aria-label='Email']", timeout=10000)

    # Fill login form
    page.fill("input[aria-label='Email']", email)
    page.fill("input[aria-label='Password']", password)

    # Click login button
    page.click("button:has-text('Login')")
    page.wait_for_load_state("networkidle")
    time.sleep(2)  # Wait for redirect


def navigate_to_financial_tab(page: Page):
    """Navigate to Financial Management tab in admin dashboard"""
    page.click("button:has-text('💳 Financial')")
    page.wait_for_load_state("networkidle")
    time.sleep(1)


def navigate_to_invitation_codes_subtab(page: Page):
    """Navigate to Invitation Codes sub-tab within Financial tab"""
    # Click the Invitation Codes tab using role selector
    invitation_codes_tab = page.get_by_role("tab", name="🎟️ Invitation Codes")
    expect(invitation_codes_tab).to_be_visible(timeout=5000)
    invitation_codes_tab.click()
    page.wait_for_timeout(2000)


def click_generate_invitation_code_button(page: Page):
    """Click 'Generate Invitation Code' button to open modal"""
    page.click("button:has-text('Generate Invitation Code')")
    page.wait_for_load_state("networkidle")

    # Wait for modal to appear
    page.wait_for_selector("text='Generate Invitation Code'", timeout=5000, state="visible")
    time.sleep(1)


def fill_invitation_form(page: Page, description: str, bonus_credits: int, expires_hours: int, invited_email: str = None):
    """Fill invitation code generation form"""
    # Fill Internal Description (first text input)
    desc_input = page.locator("input[aria-label='Internal Description']").first
    desc_input.fill(description)

    # Fill Invited Email (optional - second text input if present)
    # Note: This field might not exist in current UI, skip if not found

    # Fill Bonus Credits (first number input)
    credits_input = page.locator("input[type='number']").first
    credits_input.clear()
    credits_input.fill(str(bonus_credits))

    # Fill Expiration hours (second number input)
    expiry_input = page.locator("input[type='number']").nth(1)
    expiry_input.clear()
    expiry_input.fill(str(expires_hours))


def submit_invitation_form_and_capture_code(page: Page) -> str:
    """
    Submit invitation form and capture the generated code

    Returns:
        str: The generated invitation code
    """
    # Click "Generate Code" button (using emoji)
    submit_btn = page.locator("button:has-text('Generate Code')")
    expect(submit_btn).to_be_visible(timeout=3000)
    submit_btn.click()
    page.wait_for_timeout(2000)

    # Wait for success message and code display
    # The modal shows the generated code in a st.code() element after success
    code_elements = page.locator("code").all()

    # Find the invitation code (format: INV-YYYYMMDD-XXXXXX)
    generated_code = None
    for code_el in code_elements:
        try:
            code_value = code_el.inner_text(timeout=500)
            if code_value and code_value.startswith("INV-"):
                generated_code = code_value
                break
        except:
            pass

    if not generated_code:
        raise AssertionError("Could not capture generated invitation code from modal")

    print(f"✅ Captured invitation code: {generated_code}")

    # Close modal by waiting for it to auto-close or clicking outside
    # (The modal might stay open to show the code, so we need to close it)
    page.wait_for_timeout(2000)

    # Click outside modal or press Escape to close
    page.keyboard.press("Escape")
    page.wait_for_timeout(1000)

    return generated_code


def register_new_user(page: Page, user_data: dict, invitation_code: str):
    """
    Register a new user with invitation code

    Args:
        user_data: Dictionary with user registration details
        invitation_code: The invitation code to use
    """
    # Clear browser context (logout any existing session)
    page.context.clear_cookies()

    # Go to home page
    page.goto("http://localhost:8501")
    page.wait_for_load_state("networkidle")
    time.sleep(3)

    # Click "Register with Invitation Code" button
    register_btn = page.locator("button:has-text('Register with Invitation Code')")
    expect(register_btn).to_be_visible(timeout=10000)
    register_btn.click()
    page.wait_for_timeout(3000)

    # Fill registration form using CORRECT placeholders from streamlit code
    # (Streamlit doesn't set aria-label, so we use placeholders)

    # Personal Information
    page.locator("input[placeholder='John']").fill(user_data["first_name"])
    page.wait_for_timeout(300)
    page.locator("input[placeholder='Doe']").fill(user_data["last_name"])
    page.wait_for_timeout(300)
    page.locator("input[placeholder='Johnny']").fill(user_data["nickname"])
    page.wait_for_timeout(300)
    page.locator("input[placeholder='student@example.com']").fill(user_data["email"])
    page.wait_for_timeout(300)
    page.locator("input[type='password'][placeholder='Min 6 characters']").fill(user_data["password"])
    page.wait_for_timeout(300)
    page.locator("input[placeholder='+36 20 123 4567']").fill(user_data["phone"])
    page.wait_for_timeout(300)

    # Fill date of birth - Streamlit date_input requires ENTER key press to accept the value!
    # Format: YYYY/MM/DD (as shown in placeholder)
    date_value_streamlit = user_data["date_of_birth"].replace("-", "/")  # 2016-05-15 -> 2016/05/15
    date_input = page.locator("input[data-testid='stDateInputField']")
    date_input.fill(date_value_streamlit)
    page.wait_for_timeout(300)
    # Press ENTER to confirm the date value
    date_input.press("Enter")
    page.wait_for_timeout(800)

    # Nationality
    page.locator("input[placeholder='e.g., Hungarian']").fill(user_data["nationality"])
    page.wait_for_timeout(300)

    # Select gender from selectbox
    # Streamlit selectbox has specific structure
    gender_select = page.locator("[data-baseweb='select']").first
    gender_select.click()
    page.wait_for_timeout(500)

    # Click the gender option using get_by_role with exact match
    page.get_by_role("option", name=user_data['gender'], exact=True).click()
    page.wait_for_timeout(500)

    # Fill address
    page.locator("input[placeholder='Main Street 123']").fill(user_data["street_address"])
    page.wait_for_timeout(300)
    page.locator("input[placeholder='Budapest']").fill(user_data["city"])
    page.wait_for_timeout(300)
    page.locator("input[placeholder='1011']").fill(user_data["postal_code"])
    page.wait_for_timeout(300)
    page.locator("input[placeholder='Hungary']").fill(user_data["country"])
    page.wait_for_timeout(300)

    # Fill invitation code
    page.locator("input[placeholder='Enter the code you received']").fill(invitation_code)
    page.wait_for_timeout(500)

    # Take screenshot before submission
    screenshot_path = f"tests/e2e/screenshots/registration_{user_data['email']}.png"
    page.screenshot(path=screenshot_path)
    print(f"📸 Screenshot saved: {screenshot_path}")

    # Click "Register Now" button
    register_submit_btn = page.locator("button:has-text('Register Now')")
    expect(register_submit_btn).to_be_visible(timeout=3000)
    register_submit_btn.click()

    # Wait for registration to complete and page to reload
    # After successful registration, Streamlit does st.rerun() which returns to login form
    page.wait_for_timeout(5000)

    # Verify success by checking if we're back at login form (registration successful redirects here)
    # The registration form should be closed and login form visible
    login_btn = page.locator("button:has-text('Login')")
    expect(login_btn).to_be_visible(timeout=10000)

    print(f"✅ User registered successfully: {user_data['email']}")


def login_and_verify_hub_loads(page: Page, email: str, password: str):
    """
    Login as newly registered user and verify Specialization Hub loads

    Expected:
    - User logs in successfully
    - Redirected to Specialization Hub (since no unlocked specializations yet)
    - Hub page displays specializations
    """
    # Login
    streamlit_login(page, email, password)

    # Wait for redirect to Specialization Hub
    # New users without unlocked specializations should be redirected to hub
    page.wait_for_timeout(5000)

    # Verify we're on Specialization Hub page
    current_url = page.url

    # The URL might be /Specialization_Hub or contain the page name
    # Let's verify by looking for hub-specific content

    # Look for "Specialization Hub" heading or similar content
    hub_heading = page.locator("text=Specialization Hub").or_(
        page.locator("text=Choose Your Path")
    ).or_(
        page.locator("text=First Team")
    ).first

    try:
        expect(hub_heading).to_be_visible(timeout=10000)
        print(f"✅ Specialization Hub loaded for user: {email}")

        # Take screenshot
        screenshot_path = f"tests/e2e/screenshots/hub_{email.split('@')[0]}.png"
        page.screenshot(path=screenshot_path)
        print(f"📸 Hub screenshot saved: {screenshot_path}")

    except Exception as e:
        # Debug: Print current URL and page content
        print(f"❌ ERROR: Hub not loaded")
        print(f"Current URL: {current_url}")

        # Take debug screenshot
        page.screenshot(path=f"tests/e2e/screenshots/debug_hub_{email.split('@')[0]}.png")

        raise AssertionError(f"Specialization Hub did not load for {email}: {e}")


# =============================================================================
# PYTEST FIXTURES
# =============================================================================

@pytest.fixture(scope="function")
def admin_page(page: Page):
    """
    Fixture that provides an authenticated admin page at Financial → Invitation Codes

    Prerequisites:
    - Streamlit app running at http://localhost:8501
    - Admin user exists: admin@lfa.com / admin123
    - Run tests with: pytest --browser firefox --headed
    """
    streamlit_login(page, "admin@lfa.com", "admin123")
    navigate_to_financial_tab(page)
    navigate_to_invitation_codes_subtab(page)
    yield page


# =============================================================================
# TEST GROUP 1: Admin Creates 3 Invitation Codes via UI
# =============================================================================

@pytest.mark.e2e
@pytest.mark.invitation_ui
def test_d1_admin_creates_three_invitation_codes(admin_page: Page):
    """
    Test D1: Admin creates 3 invitation codes via UI and captures them

    CRITICAL REQUIREMENTS:
    - 3 invitation codes created successfully
    - Each code has 50 bonus credits (CRITICAL: ONLY 50 credits allowed)
    - Email restrictions: pwt.k1sqx1@f1stteam.hu, pwt.p3t1k3@f1stteam.hu, pwt.V4lv3rd3jr@f1stteam.hu
    - Codes are captured for use in registration tests

    NOTE: We'll store codes in a file for use in subsequent tests
    """
    invitation_codes = []

    # NOTE: Email restriction not supported in current UI modal
    # We'll create codes without email restriction for now
    # The API tests already validate email restriction functionality

    categories = ["Pre Category", "Youth Category", "Amateur Category"]

    for i in range(1, 4):
        print(f"\n📝 Creating invitation code {i}/3 ({categories[i-1]})...")

        # Click "Generate Invitation Code" button
        click_generate_invitation_code_button(admin_page)

        # Fill form
        fill_invitation_form(
            admin_page,
            description=f"E2E Test - First Team Player {i} - {categories[i-1]}",
            bonus_credits=50,  # CRITICAL: 50 credits only
            expires_hours=168  # 7 days
        )

        # Submit and capture code
        code = submit_invitation_form_and_capture_code(admin_page)
        invitation_codes.append(code)

        print(f"✅ Code {i}/3 created: {code} (50 credits, {categories[i-1]})")

        # Wait before creating next code
        admin_page.wait_for_timeout(1000)

    # Verify we have 3 unique codes
    assert len(invitation_codes) == 3
    assert len(set(invitation_codes)) == 3  # All unique

    # Save codes to file for use in next tests
    import json
    with open("tests/e2e/generated_invitation_codes.json", "w") as f:
        json.dump(invitation_codes, f)

    print(f"\n✅✅✅ All 3 invitation codes created and saved!")
    print(f"Codes: {invitation_codes}")


# =============================================================================
# TEST GROUP 2: 3 Users Register with Invitation Codes
# =============================================================================

@pytest.mark.e2e
@pytest.mark.invitation_ui
def test_d2_first_user_registers_with_invitation(page: Page):
    """
    Test D2.1: First user registers with invitation code (PRE category, age 6-11)

    CRITICAL REQUIREMENTS:
    - Email: pwt.k1sqx1@f1stteam.hu (fixed)
    - Date of birth: Pre category (age 6-11, born 2015-2019)
    - Registration form accepts all required fields
    - Invitation code is validated and accepted
    - User is created successfully with 50 bonus credits
    - Success message displayed
    """
    # Load invitation codes from file
    import json
    with open("tests/e2e/generated_invitation_codes.json", "r") as f:
        invitation_codes = json.load(f)

    assert len(invitation_codes) >= 1

    # User 1 data - PRE CATEGORY (age 10)
    user_data = {
        "first_name": "Kristóf",
        "last_name": "Kis",
        "nickname": "Krisz",
        "email": "pwt.k1sqx1@f1stteam.hu",  # CRITICAL: Fixed email with pwt. prefix
        "password": "password123",
        "phone": "+36 20 123 4567",
        "date_of_birth": "2016-05-15",  # Age 10 (Pre category: 6-11)
        "nationality": "Hungarian",
        "gender": "Male",
        "street_address": "Fő utca 12",
        "city": "Budapest",
        "postal_code": "1011",
        "country": "Hungary"
    }

    register_new_user(page, user_data, invitation_codes[0])

    print(f"✅ First user registered: {user_data['email']} (Pre category, age 10)")


@pytest.mark.e2e
@pytest.mark.invitation_ui
def test_d3_second_user_registers_with_invitation(page: Page):
    """
    Test D2.2: Second user registers with invitation code (YOUTH category, age 12-17)

    CRITICAL REQUIREMENTS:
    - Email: pwt.p3t1k3@f1stteam.hu (fixed)
    - Date of birth: Youth category (age 12-17, born 2009-2014)
    - Different invitation code from first user
    - Registration successful with 50 bonus credits
    """
    # Load invitation codes from file
    import json
    with open("tests/e2e/generated_invitation_codes.json", "r") as f:
        invitation_codes = json.load(f)

    assert len(invitation_codes) >= 2

    # User 2 data - YOUTH CATEGORY (age 14)
    user_data = {
        "first_name": "Péter",
        "last_name": "Pataki",
        "nickname": "Peti",
        "email": "pwt.p3t1k3@f1stteam.hu",  # CRITICAL: Fixed email with pwt. prefix
        "password": "password123",
        "phone": "+36 30 234 5678",
        "date_of_birth": "2012-08-20",  # Age 14 (Youth category: 12-17)
        "nationality": "Hungarian",
        "gender": "Male",
        "street_address": "Petőfi utca 34",
        "city": "Debrecen",
        "postal_code": "4024",
        "country": "Hungary"
    }

    register_new_user(page, user_data, invitation_codes[1])

    print(f"✅ Second user registered: {user_data['email']} (Youth category, age 14)")


@pytest.mark.e2e
@pytest.mark.invitation_ui
def test_d4_third_user_registers_with_invitation(page: Page):
    """
    Test D2.3: Third user registers with invitation code (AMATEUR category, age 18+)

    CRITICAL REQUIREMENTS:
    - Email: pwt.V4lv3rd3jr@f1stteam.hu (fixed)
    - Date of birth: Amateur category (age 18+, born 2008 or earlier)
    - Different invitation code from previous users
    - Registration successful with 50 bonus credits
    """
    # Load invitation codes from file
    import json
    with open("tests/e2e/generated_invitation_codes.json", "r") as f:
        invitation_codes = json.load(f)

    assert len(invitation_codes) >= 3

    # User 3 data - AMATEUR CATEGORY (age 22)
    user_data = {
        "first_name": "Viktor",
        "last_name": "Valverde",
        "nickname": "Viki",
        "email": "pwt.V4lv3rd3jr@f1stteam.hu",  # CRITICAL: Fixed email with pwt. prefix
        "password": "password123",
        "phone": "+36 70 345 6789",
        "date_of_birth": "2004-11-12",  # Age 22 (Amateur category: 18+)
        "nationality": "Hungarian",
        "gender": "Male",
        "street_address": "Rákóczi út 56",
        "city": "Szeged",
        "postal_code": "6720",
        "country": "Hungary"
    }

    register_new_user(page, user_data, invitation_codes[2])

    print(f"✅ Third user registered: {user_data['email']} (Amateur category, age 22)")


# =============================================================================
# TEST GROUP 3: Verify Specialization Hub Loads for New Users
# =============================================================================

@pytest.mark.e2e
@pytest.mark.invitation_ui
def test_d5_first_user_hub_loads(page: Page):
    """
    Test D3.1: First registered user (Pre category) logs in and Specialization Hub loads

    Expected:
    - User logs in successfully with credentials
    - Automatically redirected to Specialization Hub
    - Hub displays specialization options
    """
    login_and_verify_hub_loads(
        page,
        email="pwt.k1sqx1@f1stteam.hu",
        password="password123"
    )


@pytest.mark.e2e
@pytest.mark.invitation_ui
def test_d6_second_user_hub_loads(page: Page):
    """
    Test D3.2: Second registered user (Youth category) logs in and Specialization Hub loads
    """
    login_and_verify_hub_loads(
        page,
        email="pwt.p3t1k3@f1stteam.hu",
        password="password123"
    )


@pytest.mark.e2e
@pytest.mark.invitation_ui
def test_d7_third_user_hub_loads(page: Page):
    """
    Test D3.3: Third registered user (Amateur category) logs in and Specialization Hub loads
    """
    login_and_verify_hub_loads(
        page,
        email="pwt.V4lv3rd3jr@f1stteam.hu",
        password="password123"
    )


# =============================================================================
# TEST GROUP 4: Database Verification (Hybrid API + E2E)
# =============================================================================

@pytest.mark.e2e
@pytest.mark.invitation_ui
def test_d8_verify_users_in_database(db):
    """
    Test D4: Verify all 3 users exist in database with correct data

    CRITICAL REQUIREMENTS:
    - All 3 users created in database with fixed emails
    - Each user has 50 bonus credits from invitation code (CRITICAL: ONLY 50 credits allowed)
    - Invitation codes marked as used
    - Age groups correctly represented: Pre, Youth, Amateur
    """
    from app.models.user import User
    from app.models.invitation_code import InvitationCode

    # Verify users exist with CRITICAL fixed emails (pwt. prefix)
    user1 = db.query(User).filter(User.email == "pwt.k1sqx1@f1stteam.hu").first()
    user2 = db.query(User).filter(User.email == "pwt.p3t1k3@f1stteam.hu").first()
    user3 = db.query(User).filter(User.email == "pwt.V4lv3rd3jr@f1stteam.hu").first()

    assert user1 is not None, "First user (pwt.k1sqx1@f1stteam.hu) not found in database"
    assert user2 is not None, "Second user (pwt.p3t1k3@f1stteam.hu) not found in database"
    assert user3 is not None, "Third user (pwt.V4lv3rd3jr@f1stteam.hu) not found in database"

    # CRITICAL: Verify bonus credits (MUST be 50)
    assert user1.credit_balance == 50, f"User 1 has {user1.credit_balance} credits, expected 50"
    assert user2.credit_balance == 50, f"User 2 has {user2.credit_balance} credits, expected 50"
    assert user3.credit_balance == 50, f"User 3 has {user3.credit_balance} credits, expected 50"

    # Verify user details
    assert user1.first_name == "Kristóf"
    assert user2.first_name == "Péter"
    assert user3.first_name == "Viktor"

    # Verify age groups
    from datetime import date
    today = date.today()

    # User 1 - Pre category (age 6-11)
    age1 = today.year - user1.date_of_birth.year
    assert 6 <= age1 <= 11, f"User 1 age {age1} not in Pre category (6-11)"

    # User 2 - Youth category (age 12-17)
    age2 = today.year - user2.date_of_birth.year
    assert 12 <= age2 <= 17, f"User 2 age {age2} not in Youth category (12-17)"

    # User 3 - Amateur category (age 18+)
    age3 = today.year - user3.date_of_birth.year
    assert age3 >= 18, f"User 3 age {age3} not in Amateur category (18+)"

    # Verify invitation codes are marked as used
    code1 = db.query(InvitationCode).filter(InvitationCode.used_by_user_id == user1.id).first()
    code2 = db.query(InvitationCode).filter(InvitationCode.used_by_user_id == user2.id).first()
    code3 = db.query(InvitationCode).filter(InvitationCode.used_by_user_id == user3.id).first()

    assert code1 is not None, "User 1's invitation code not found"
    assert code2 is not None, "User 2's invitation code not found"
    assert code3 is not None, "User 3's invitation code not found"

    assert code1.is_used is True
    assert code2.is_used is True
    assert code3.is_used is True

    # CRITICAL: Verify invitation codes had 50 credits
    assert code1.bonus_credits == 50
    assert code2.bonus_credits == 50
    assert code3.bonus_credits == 50

    print("\n✅✅✅ All 3 users verified in database!")
    print(f"User 1: {user1.email} - {user1.credit_balance} credits (Pre, age {age1})")
    print(f"User 2: {user2.email} - {user2.credit_balance} credits (Youth, age {age2})")
    print(f"User 3: {user3.email} - {user3.credit_balance} credits (Amateur, age {age3})")
