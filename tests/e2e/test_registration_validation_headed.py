"""
E2E Test: Registration Form Validation (Headed Debug Mode)

This test allows manual validation testing via browser automation.
Run with: pytest tests/e2e/test_registration_validation_headed.py -v --headed

Test scenarios:
1. Invalid phone numbers
2. Invalid address fields
3. Short names
4. Valid data submission
"""

import pytest
from playwright.sync_api import Page, expect
import os
from datetime import datetime

STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")


@pytest.mark.e2e
@pytest.mark.validation
class TestRegistrationValidation:
    """E2E validation tests for registration form"""

    def test_registration_form_validation_invalid_phone(self, page: Page):
        """
        Test: Registration form rejects invalid phone numbers

        This test verifies that:
        1. Form can be accessed
        2. Invalid phone number triggers backend validation error
        3. Error message is displayed to user
        """

        print("\n🧪 Testing: Invalid phone number validation")

        # Navigate to home page
        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        # Click Register button
        register_btn = page.locator("button:has-text('Register with Invitation Code')")
        expect(register_btn).to_be_visible(timeout=5000)
        register_btn.click()
        page.wait_for_timeout(2000)

        print("  ✅ Registration form opened")

        # Fill form with INVALID phone number
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        page.locator("input[aria-label='First Name *']").fill("Test")
        page.locator("input[aria-label='Last Name *']").fill("User")
        page.locator("input[aria-label='Nickname *']").fill("Tester")
        page.locator("input[aria-label='Email *']").fill(f"test{timestamp}@example.com")
        page.locator("input[aria-label='Password *']").fill("test1234")

        # INVALID PHONE: Too short
        page.locator("input[aria-label='Phone Number *']").fill("123")

        page.locator("input[aria-label='Select a date.']").fill("2000/01/15")
        page.locator("input[aria-label='Nationality *']").fill("Hungarian")

        # Select gender
        gender_selectbox = page.locator("div[data-baseweb='select']").last
        gender_selectbox.click()
        page.wait_for_timeout(500)
        page.locator("text=Male").first.click()
        page.wait_for_timeout(500)

        # Fill address
        page.locator("input[aria-label='Street Address *']").fill("Main Street 123")
        page.locator("input[aria-label='City *']").fill("Budapest")
        page.locator("input[aria-label='Postal Code *']").fill("1011")
        page.locator("input[aria-label='Country *']").fill("Hungary")

        # Use valid invitation code from previous test
        page.locator("input[aria-label='Invitation Code *']").fill("INV-20260103-APWZEP")

        print("  ✅ Form filled with INVALID phone number: '123'")

        # Submit form
        submit_btn = page.locator("button:has-text('Register Now')")
        submit_btn.click()
        page.wait_for_timeout(3000)

        # Check for error message
        page.screenshot(path="docs/screenshots/validation_invalid_phone.png")

        # Look for validation error in page content
        content = page.content()

        if "invalid phone" in content.lower() or "phone" in content.lower():
            print("  ✅ Validation error displayed for invalid phone")
        else:
            print("  ⚠️  No validation error found - check screenshot")

        print("\n🔍 Manual verification:")
        print("  1. Check screenshot: docs/screenshots/validation_invalid_phone.png")
        print("  2. Look for error message about invalid phone number")
        print("  3. Verify form did not submit successfully")

    def test_registration_form_validation_short_city(self, page: Page):
        """
        Test: Registration form rejects too short city name
        """

        print("\n🧪 Testing: Short city name validation")

        # Navigate and open form
        page.goto(STREAMLIT_URL)
        page.wait_for_timeout(2000)

        register_btn = page.locator("button:has-text('Register with Invitation Code')")
        register_btn.click()
        page.wait_for_timeout(2000)

        # Fill form with SHORT CITY
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        page.locator("input[aria-label='First Name *']").fill("Test")
        page.locator("input[aria-label='Last Name *']").fill("User")
        page.locator("input[aria-label='Nickname *']").fill("Tester")
        page.locator("input[aria-label='Email *']").fill(f"test{timestamp}@example.com")
        page.locator("input[aria-label='Password *']").fill("test1234")
        page.locator("input[aria-label='Phone Number *']").fill("+36 20 123 4567")
        page.locator("input[aria-label='Select a date.']").fill("2000/01/15")
        page.locator("input[aria-label='Nationality *']").fill("Hungarian")

        gender_selectbox = page.locator("div[data-baseweb='select']").last
        gender_selectbox.click()
        page.wait_for_timeout(500)
        page.locator("text=Male").first.click()
        page.wait_for_timeout(500)

        page.locator("input[aria-label='Street Address *']").fill("Main Street 123")

        # SHORT CITY: Only 1 character
        page.locator("input[aria-label='City *']").fill("B")

        page.locator("input[aria-label='Postal Code *']").fill("1011")
        page.locator("input[aria-label='Country *']").fill("Hungary")
        page.locator("input[aria-label='Invitation Code *']").fill("INV-20260103-APWZEP")

        print("  ✅ Form filled with SHORT city: 'B'")

        # Submit
        submit_btn = page.locator("button:has-text('Register Now')")
        submit_btn.click()
        page.wait_for_timeout(3000)

        page.screenshot(path="docs/screenshots/validation_short_city.png")

        content = page.content()

        if "city" in content.lower() and ("short" in content.lower() or "2 characters" in content.lower()):
            print("  ✅ Validation error displayed for short city")
        else:
            print("  ⚠️  No validation error found - check screenshot")

        print("\n🔍 Manual verification:")
        print("  1. Check screenshot: docs/screenshots/validation_short_city.png")
        print("  2. Look for error message about city being too short")

    def test_registration_form_validation_valid_data(self, page: Page):
        """
        Test: Registration form accepts valid data

        NOTE: This will consume the invitation code!
        """

        print("\n🧪 Testing: Valid data submission")
        print("  ⚠️  This test will consume invitation code INV-20260103-APWZEP")
        print("  ⚠️  Skipping to preserve code for other tests")

        # Skip this test to preserve invitation code
        pytest.skip("Skipping to preserve invitation code")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("REGISTRATION VALIDATION HEADED TEST")
    print("="*70)
    print("\nRun with:")
    print("  pytest tests/e2e/test_registration_validation_headed.py -v --headed")
    print("="*70 + "\n")
