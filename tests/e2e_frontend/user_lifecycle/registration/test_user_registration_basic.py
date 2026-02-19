"""
E2E Test: User Registration with Invitation Code

This test validates the user registration flow:
1. Create invitation code via API (fixture)
2. User navigates to registration form
3. User fills registration form with invitation code
4. User submits registration
5. Verify: Registration successful

Part of Sprint 1.2 - User Activation
"""

import pytest
from playwright.sync_api import Page, expect
import os
import requests
from datetime import datetime, timedelta

STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Admin credentials for API calls
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="function")
def invitation_code():
    """
    Dynamically creates a fresh invitation code via DB insert.
    Ensures test isolation - no hardcoded dependencies.
    """
    import psycopg2
    from datetime import datetime, timedelta
    import random
    import string

    # Generate unique code
    timestamp = datetime.now().strftime("%Y%m%d")
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    code = f"INV-{timestamp}-{random_suffix}"

    # Insert directly into DB (bypass API for speed)
    conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
    cur = conn.cursor()

    # Get admin user ID (assume admin@lfa.com exists)
    cur.execute("SELECT id FROM users WHERE email = 'admin@lfa.com' LIMIT 1")
    admin_id = cur.fetchone()[0] if cur.rowcount > 0 else None

    # Insert invitation code
    cur.execute("""
        INSERT INTO invitation_codes
        (code, invited_name, invited_email, bonus_credits, is_used, created_by_admin_id, created_at, expires_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        code,
        "E2E Test User",
        None,  # email not required
        50,    # bonus credits
        False, # not used
        admin_id,
        datetime.now(),
        datetime.now() + timedelta(days=30)  # valid for 30 days
    ))
    conn.commit()
    conn.close()

    print(f"\n📧 Generated fresh invitation code: {code}")

    yield code

    # Cleanup after test (optional - helps keep DB clean)
    conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
    cur = conn.cursor()
    cur.execute("DELETE FROM invitation_codes WHERE code = %s", (code,))
    conn.commit()
    conn.close()


@pytest.mark.e2e
@pytest.mark.registration
class TestUserRegistration:
    """E2E tests for user registration with invitation code"""

    def test_user_can_register_with_invitation_code(self, page: Page, invitation_code: str):
        """
        E2E: User registers with invitation code via UI.

        Flow:
        1. Navigate to registration page
        2. Fill registration form
        3. Submit with invitation code
        4. Verify: Success message and redirect to Hub
        """

        print("\n👤 Testing: User registration with invitation code")
        print(f"  📧 Using invitation code: {invitation_code}")

        # ================================================================
        # STEP 1: Navigate to Home Page
        # ================================================================
        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)
        print("  1. Opened home page")

        # ================================================================
        # STEP 2: Click "Register with Invitation Code" Button
        # ================================================================
        print("  2. Clicking 'Register with Invitation Code' button...")

        register_btn = page.locator("button:has-text('Register with Invitation Code')")
        expect(register_btn).to_be_visible(timeout=5000)
        register_btn.click()
        page.wait_for_timeout(2000)  # Wait for form to appear

        print("  ✅ Registration form displayed")

        # ================================================================
        # STEP 3: Fill Registration Form (ALL NEW FIELDS)
        # ================================================================
        print("  3. Filling registration form with ALL required fields...")

        # Generate unique test user data
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        test_email = f"testuser{timestamp}@example.com"
        test_first_name = "Test"
        test_last_name = f"User{timestamp}"
        test_nickname = f"Tester{timestamp}"

        # === PERSONAL INFORMATION ===
        print("     📝 Personal Information...")

        first_name_input = page.locator("input[aria-label='First Name *']")
        first_name_input.fill(test_first_name)
        print(f"        ✅ First Name: {test_first_name}")

        last_name_input = page.locator("input[aria-label='Last Name *']")
        last_name_input.fill(test_last_name)
        print(f"        ✅ Last Name: {test_last_name}")

        nickname_input = page.locator("input[aria-label='Nickname *']")
        nickname_input.fill(test_nickname)
        print(f"        ✅ Nickname: {test_nickname}")

        email_input = page.locator("input[aria-label='Email *']")
        email_input.fill(test_email)
        print(f"        ✅ Email: {test_email}")

        password_input = page.locator("input[aria-label='Password *']")
        password_input.fill("test1234")
        print("        ✅ Password: ********")

        phone_input = page.locator("input[aria-label='Phone Number *']")
        phone_input.fill("+36 20 123 4567")
        print("        ✅ Phone: +36 20 123 4567")

        # === DEMOGRAPHICS ===
        print("     👤 Demographics...")

        # Date of Birth - Streamlit date_input uses aria-label "Select a date."
        dob_input = page.locator("input[aria-label='Select a date.']")
        dob_input.fill("2000/01/15")  # Format: YYYY/MM/DD
        print("        ✅ Date of Birth: 2000/01/15")

        nationality_input = page.locator("input[aria-label='Nationality *']")
        nationality_input.fill("Hungarian")
        print("        ✅ Nationality: Hungarian")

        # Gender - selectbox (Streamlit renders as data-baseweb='select')
        # Use .last to get the Gender selectbox (there may be multiple selectboxes on page)
        gender_selectbox = page.locator("div[data-baseweb='select']").last
        gender_selectbox.click()
        page.wait_for_timeout(500)
        # Click the "Male" option from dropdown - find first visible one
        male_option = page.locator("text=Male").first
        male_option.click()
        print("        ✅ Gender: Male")
        page.wait_for_timeout(500)

        # === ADDRESS ===
        print("     🏠 Address...")

        street_input = page.locator("input[aria-label='Street Address *']")
        street_input.fill("Main Street 123")
        print("        ✅ Street Address: Main Street 123")

        city_input = page.locator("input[aria-label='City *']")
        city_input.fill("Budapest")
        print("        ✅ City: Budapest")

        postal_input = page.locator("input[aria-label='Postal Code *']")
        postal_input.fill("1011")
        print("        ✅ Postal Code: 1011")

        country_input = page.locator("input[aria-label='Country *']")
        country_input.fill("Hungary")
        print("        ✅ Country: Hungary")

        # === INVITATION ===
        print("     🎟️  Invitation...")

        code_input = page.locator("input[aria-label='Invitation Code *']")
        code_input.fill(invitation_code)
        print(f"        ✅ Invitation Code: {invitation_code}")

        print("  ✅ All fields filled successfully!")

        # Take screenshot of filled form
        page.screenshot(path="docs/screenshots/e2e_registration_form_filled.png")

        # ================================================================
        # STEP 4: Submit Registration
        # ================================================================
        print("  4. Submitting registration...")

        submit_btn = page.locator("button:has-text('Register Now')")
        expect(submit_btn).to_be_visible(timeout=3000)
        submit_btn.click()

        # Wait for registration to complete
        page.wait_for_timeout(5000)

        print("  ✅ Clicked 'Register Now' button")

        # ================================================================
        # STEP 5: Verify Registration Success
        # ================================================================
        print("  5. Verifying registration success...")

        # After successful registration, Streamlit app redirects back to login page
        # Check if we're back on the login page (indicated by Login button and title)
        try:
            # Wait a bit for redirect to complete
            page.wait_for_timeout(3000)

            # Take screenshot of result page
            page.screenshot(path="docs/screenshots/e2e_registration_result.png")

            # Check if we're back on the login page (success indicator)
            login_button = page.locator("button:has-text('🔐 Login')").first
            login_title = page.locator("text=🔐 Login").first

            if login_button.is_visible() and login_title.is_visible():
                print("  ✅ Redirected back to Login page (registration successful)")
            else:
                # Check for error message
                content = page.content()
                if "registration failed" in content.lower() or "error" in content.lower():
                    print("  ❌ Registration failed - check screenshot")
                    raise AssertionError("Registration failed - see screenshot for details")
                else:
                    print("  ⚠️ Unexpected page state - check screenshot")
                    raise AssertionError("Could not verify registration success")

        except AssertionError:
            raise
        except Exception as e:
            print(f"  ⚠️ Error during verification: {e}")
            page.screenshot(path="docs/screenshots/e2e_registration_error.png")
            raise AssertionError("Could not verify registration success")

        print("\n✅ ✅ ✅ TEST PASSED: User can register with invitation code")
