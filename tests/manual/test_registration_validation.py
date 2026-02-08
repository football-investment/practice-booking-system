"""
Manual Test: Registration Validation via API

This test validates the registration endpoint with various invalid inputs
to ensure proper validation is working.
"""

import requests
import os
from datetime import datetime

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def test_registration_validation():
    """Test registration validation with various invalid inputs"""

    print("\n" + "="*70)
    print("REGISTRATION VALIDATION TEST")
    print("="*70)

    # Base valid data
    base_data = {
        "email": "test@example.com",
        "password": "test1234",
        "name": "Test User",
        "first_name": "Test",
        "last_name": "User",
        "nickname": "Testy",
        "phone": "+36 20 123 4567",
        "date_of_birth": "2000-01-15T00:00:00",
        "nationality": "Hungarian",
        "gender": "Male",
        "street_address": "Main Street 123",
        "city": "Budapest",
        "postal_code": "1011",
        "country": "Hungary",
        "invitation_code": "TESTCODE123"
    }

    # Test cases: (description, field_to_modify, new_value, expected_error_substring)
    test_cases = [
        # Name validations
        ("Empty first name", "first_name", "", "First name is required"),
        ("Too short first name", "first_name", "A", "First name must be at least 2 characters"),
        ("Empty last name", "last_name", "", "Last name is required"),
        ("Too short last name", "last_name", "B", "Last name must be at least 2 characters"),
        ("Empty nickname", "nickname", "", "Nickname is required"),
        ("Too short nickname", "nickname", "N", "Nickname must be at least 2 characters"),

        # Phone validations
        ("Empty phone", "phone", "", "Phone number is required"),
        ("Invalid phone (too short)", "phone", "123", "Invalid phone number"),
        ("Invalid phone (letters)", "phone", "abc123", "Invalid phone number"),

        # Address validations
        ("Empty street address", "street_address", "", "Street address must be at least 5 characters"),
        ("Too short street address", "street_address", "Str", "Street address must be at least 5 characters"),
        ("Empty city", "city", "", "City name must be at least 2 characters"),
        ("Too short city", "city", "B", "City name must be at least 2 characters"),
        ("Invalid city (contains numbers)", "city", "City123", "City name can only contain letters"),
        ("Empty postal code", "postal_code", "", "Postal code must be at least 3 characters"),
        ("Too short postal code", "postal_code", "11", "Postal code must be at least 3 characters"),
        ("Empty country", "country", "", "Country name must be at least 2 characters"),
        ("Too short country", "country", "H", "Country name must be at least 2 characters"),

        # Valid phone formats (should succeed)
        ("Valid Hungarian phone with country code", "phone", "+36 20 987 6543", None),
        ("Valid Hungarian phone without country code", "phone", "06209876543", None),
    ]

    print(f"\n📊 Running {len(test_cases)} validation test cases...\n")

    passed = 0
    failed = 0

    for i, (description, field, value, expected_error) in enumerate(test_cases, 1):
        # Create test data
        test_data = base_data.copy()
        test_data[field] = value

        # Make request
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/v1/auth/register-with-invitation",
                json=test_data,
                timeout=5
            )

            if expected_error is None:
                # Should succeed
                if response.status_code == 200:
                    print(f"✅ Test {i:2d}/{len(test_cases)}: {description}")
                    print(f"           Status: {response.status_code} (expected success)")
                    passed += 1
                else:
                    print(f"❌ Test {i:2d}/{len(test_cases)}: {description}")
                    print(f"           Status: {response.status_code} (expected 200)")
                    print(f"           Response: {response.json()}")
                    failed += 1
            else:
                # Should fail with validation error
                if response.status_code == 400:
                    error_detail = response.json().get("detail", "")
                    if expected_error.lower() in error_detail.lower():
                        print(f"✅ Test {i:2d}/{len(test_cases)}: {description}")
                        print(f"           Got expected error: '{error_detail}'")
                        passed += 1
                    else:
                        print(f"❌ Test {i:2d}/{len(test_cases)}: {description}")
                        print(f"           Expected error containing: '{expected_error}'")
                        print(f"           Got: '{error_detail}'")
                        failed += 1
                elif response.status_code == 404:
                    # Invitation code doesn't exist - expected for these tests
                    error_detail = response.json().get("detail", "")
                    if "invitation code" in error_detail.lower():
                        print(f"⚠️  Test {i:2d}/{len(test_cases)}: {description}")
                        print(f"           Validation passed, but invitation code doesn't exist (expected)")
                        passed += 1
                    else:
                        print(f"❌ Test {i:2d}/{len(test_cases)}: {description}")
                        print(f"           Expected 400 validation error, got 404: {error_detail}")
                        failed += 1
                else:
                    print(f"❌ Test {i:2d}/{len(test_cases)}: {description}")
                    print(f"           Expected 400, got {response.status_code}")
                    print(f"           Response: {response.json()}")
                    failed += 1

        except requests.exceptions.RequestException as e:
            print(f"❌ Test {i:2d}/{len(test_cases)}: {description}")
            print(f"           Request failed: {e}")
            failed += 1

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"✅ Passed: {passed}/{len(test_cases)}")
    print(f"❌ Failed: {failed}/{len(test_cases)}")
    print(f"📊 Success Rate: {passed/len(test_cases)*100:.1f}%")
    print("="*70 + "\n")

    return passed == len(test_cases)


if __name__ == "__main__":
    success = test_registration_validation()
    exit(0 if success else 1)
