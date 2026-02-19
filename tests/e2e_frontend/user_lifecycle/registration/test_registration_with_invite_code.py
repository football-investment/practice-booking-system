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
from pathlib import Path

# =============================================================================
# SINGLE SOURCE OF TRUTH: test_users.json
# =============================================================================

import json

# Path to single source of truth JSON
_TEST_USERS_JSON = Path(__file__).parent.parent.parent.parent.parent / "tests" / "e2e" / "test_users.json"


def _load_pwt_users() -> list:
    """Load pwt user definitions from tests/e2e/test_users.json"""
    with open(_TEST_USERS_JSON) as f:
        return json.load(f)["pwt_users"]


def _write_back_user_ids(user_ids: dict):
    """
    Write registered user db_id values back to test_users.json.

    Args:
        user_ids: dict mapping email -> db_id, e.g. {"pwt.k1sqx1@f1rstteam.hu": 5}
    """
    with open(_TEST_USERS_JSON) as f:
        data = json.load(f)

    for user in data["pwt_users"]:
        if user["email"] in user_ids:
            user["db_id"] = user_ids[user["email"]]

    with open(_TEST_USERS_JSON, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"   ✅ Wrote {len(user_ids)} db_id(s) back to test_users.json")


# Verify users exist with CRITICAL fixed emails (pwt. prefix)
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
    page.wait_for_timeout(3000)  # Wait longer for new code to appear

    code_elements = page.locator("code").all()

    # Find ALL invitation codes and take the LAST one (most recent)
    invitation_codes_found = []
    for code_el in code_elements:
        try:
            code_value = code_el.inner_text(timeout=500)
            if code_value and code_value.startswith("INV-"):
                invitation_codes_found.append(code_value)
        except:
            pass

    if not invitation_codes_found:
        raise AssertionError("Could not capture generated invitation code from modal")

    # Use the LAST (most recent) code
    generated_code = invitation_codes_found[-1]
    print(f"✅ Captured invitation code: {generated_code}")

    # Close modal by pressing Escape
    page.keyboard.press("Escape")
    page.wait_for_timeout(2000)  # Wait for modal to fully close

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

    # Verify we landed on Specialization Hub by checking URL and visible page content
    # The URL should be /Specialization_Hub — this is the primary check
    # We also look for the main content area heading (not the sidebar nav item which may be hidden)
    hub_heading = page.locator("section[data-testid='stMain'] >> text=Specialization Hub").or_(
        page.locator("section[data-testid='stMain'] >> text=Choose Your Path")
    ).or_(
        page.locator("section[data-testid='stMain'] >> text=LFA Football Player")
    ).or_(
        page.locator("[data-testid='stAppViewContainer'] >> h1")
    ).first

    try:
        # Primary check: URL already shows /Specialization_Hub
        current_url = page.url
        if "Specialization_Hub" in current_url:
            print(f"✅ Specialization Hub loaded for user: {email} (URL confirmed)")
        else:
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
    Test D1: Admin creates invitation codes via UI — one per star user in test_users.json.

    Number of codes matches len(star_users) in test_users.json (currently 4).
    Each code: 50 bonus credits, 7-day expiry.
    Codes saved to tests/e2e/generated_invitation_codes.json for D2-D5.
    """
    pwt_users = _load_pwt_users()
    n = len(pwt_users)
    categories = [u.get("age_category", "AMATEUR") for u in pwt_users]
    invitation_codes = []

    for i, category in enumerate(categories, start=1):
        print(f"\n📝 Creating invitation code {i}/{n} ({category})...")

        click_generate_invitation_code_button(admin_page)

        fill_invitation_form(
            admin_page,
            description=f"E2E Test - PWT User {i} - {category}",
            bonus_credits=50,
            expires_hours=168
        )

        code = submit_invitation_form_and_capture_code(admin_page)
        invitation_codes.append(code)

        print(f"✅ Code {i}/{n} created: {code} (50 credits, {category})")
        admin_page.wait_for_timeout(1000)

    assert len(invitation_codes) == n
    assert len(set(invitation_codes)) == n

    with open("tests/e2e/generated_invitation_codes.json", "w") as f:
        json.dump(invitation_codes, f)

    print(f"\n✅✅✅ All {n} invitation codes created and saved!")
    print(f"Codes: {invitation_codes}")


# =============================================================================
# TEST GROUP 2: 3 Users Register with Invitation Codes
# =============================================================================

@pytest.mark.e2e
@pytest.mark.invitation_ui
def test_d2_first_user_registers_with_invitation(page: Page):
    """
    Test D2.1: First user registers with invitation code.
    User data loaded from tests/e2e/test_users.json (pwt_users[0]).
    """
    with open("tests/e2e/generated_invitation_codes.json", "r") as f:
        invitation_codes = json.load(f)

    assert len(invitation_codes) >= 1

    pwt_users = _load_pwt_users()
    user_data = pwt_users[0]

    register_new_user(page, user_data, invitation_codes[0])

    print(f"✅ First user registered: {user_data['email']}")


@pytest.mark.e2e
@pytest.mark.invitation_ui
def test_d3_second_user_registers_with_invitation(page: Page):
    """
    Test D2.2: Second user registers with invitation code.
    User data loaded from tests/e2e/test_users.json (pwt_users[1]).
    """
    with open("tests/e2e/generated_invitation_codes.json", "r") as f:
        invitation_codes = json.load(f)

    assert len(invitation_codes) >= 2

    pwt_users = _load_pwt_users()
    user_data = pwt_users[1]

    register_new_user(page, user_data, invitation_codes[1])

    print(f"✅ Second user registered: {user_data['email']}")


@pytest.mark.e2e
@pytest.mark.invitation_ui
def test_d4_third_user_registers_with_invitation(page: Page):
    """
    Test D2.3: Third user registers with invitation code.
    User data loaded from tests/e2e/test_users.json (pwt_users[2]).
    """
    with open("tests/e2e/generated_invitation_codes.json", "r") as f:
        invitation_codes = json.load(f)

    assert len(invitation_codes) >= 3

    pwt_users = _load_pwt_users()
    user_data = pwt_users[2]

    register_new_user(page, user_data, invitation_codes[2])

    print(f"✅ Third user registered: {user_data['email']}")


@pytest.mark.e2e
@pytest.mark.invitation_ui
def test_d5_fourth_user_registers_with_invitation(page: Page):
    """
    Test D2.4: Fourth user registers with invitation code.
    User data loaded from tests/e2e/test_users.json (pwt_users[3]).
    Required so Phase 4 sandbox tournament has minimum 4 participants.
    """
    with open("tests/e2e/generated_invitation_codes.json", "r") as f:
        invitation_codes = json.load(f)

    assert len(invitation_codes) >= 4

    pwt_users = _load_pwt_users()
    user_data = pwt_users[3]

    register_new_user(page, user_data, invitation_codes[3])

    print(f"✅ Fourth user registered: {user_data['email']}")


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
        email="pwt.k1sqx1@f1rstteam.hu",
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
        email="pwt.p3t1k3@f1rstteam.hu",
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
        email="pwt.v4lv3rd3jr@f1rstteam.hu",
        password="password123"
    )


# =============================================================================
# TEST GROUP 4: Database Verification (Hybrid API + E2E)
# =============================================================================

@pytest.mark.e2e
@pytest.mark.invitation_ui
def test_d8_verify_users_in_database():
    """
    Test D8: Verify all pwt users exist in database with correct data.

    Loads expected users from tests/e2e/test_users.json — automatically
    covers any number of pwt_users without hardcoding.

    CRITICAL REQUIREMENTS:
    - All pwt users created in DB with fixed emails
    - Each user has 50 bonus credits from invitation code
    - Invitation codes marked as used
    - db_ids written back to test_users.json for Phase 3 onboarding
    """
    import os
    import psycopg2
    import psycopg2.extras

    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
    )

    pwt_users = _load_pwt_users()
    today = date.today()
    id_map = {}

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        for defn in pwt_users:
            email = defn["email"]

            cursor.execute(
                "SELECT id, first_name, credit_balance, date_of_birth FROM users WHERE email = %s",
                (email,)
            )
            row = cursor.fetchone()
            assert row is not None, f"PWT user not found in DB: {email}"
            assert row["credit_balance"] == 50, f"{email} has {row['credit_balance']} credits, expected 50"
            assert row["first_name"] == defn["first_name"], f"{email} first_name mismatch"

            cursor.execute(
                "SELECT id, is_used, bonus_credits FROM invitation_codes WHERE used_by_user_id = %s",
                (row["id"],)
            )
            code_row = cursor.fetchone()
            assert code_row is not None, f"Invitation code not found for {email}"
            assert code_row["is_used"] is True
            assert code_row["bonus_credits"] == 50

            dob = row["date_of_birth"]
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

            id_map[email] = row["id"]
            print(f"   ✅ {email} — id={row['id']}, credits={row['credit_balance']}, age={age}")

    finally:
        cursor.close()
        conn.close()

    print(f"\n✅✅✅ All {len(pwt_users)} pwt users verified in database!")

    # Write db_ids back to test_users.json — enables Phase 3 onboarding to use correct ids
    _write_back_user_ids(id_map)
    print(f"✅ db_ids written to test_users.json: {id_map}")
