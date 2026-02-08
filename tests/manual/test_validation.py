"""
Manual Test: Phone Number and Address Validation

This script tests the validation utilities to ensure they work correctly.
"""

import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.validators import validate_phone_number, validate_address, validate_name


def test_phone_validation():
    """Test phone number validation"""
    print("\n" + "="*60)
    print("PHONE NUMBER VALIDATION TESTS")
    print("="*60)

    test_cases = [
        # Valid cases
        ("+36 20 123 4567", True, "Valid Hungarian mobile with country code"),
        ("06201234567", True, "Valid Hungarian mobile without country code"),
        ("+1 555 123 4567", True, "Valid US phone number"),
        ("+44 20 7946 0958", True, "Valid UK phone number"),

        # Invalid cases
        ("", False, "Empty string"),
        ("123", False, "Too short"),
        ("abc123", False, "Contains letters"),
        ("999999999999999", False, "Too long/invalid"),
    ]

    for phone, expected_valid, description in test_cases:
        is_valid, formatted, error = validate_phone_number(phone)
        status = "✅ PASS" if is_valid == expected_valid else "❌ FAIL"
        print(f"\n{status} - {description}")
        print(f"  Input: '{phone}'")
        print(f"  Valid: {is_valid} (expected: {expected_valid})")
        if is_valid:
            print(f"  Formatted: {formatted}")
        else:
            print(f"  Error: {error}")


def test_address_validation():
    """Test address validation"""
    print("\n" + "="*60)
    print("ADDRESS VALIDATION TESTS")
    print("="*60)

    test_cases = [
        # Valid cases
        ("Main Street 123", "Budapest", "1011", "Hungary", True, "Valid Hungarian address"),
        ("123 Main St", "New York", "10001", "USA", True, "Valid US address"),
        ("Baker Street 221B", "London", "NW1 6XE", "United Kingdom", True, "Valid UK address"),

        # Invalid cases - street address
        ("", "Budapest", "1011", "Hungary", False, "Empty street address"),
        ("Str", "Budapest", "1011", "Hungary", False, "Street address too short"),

        # Invalid cases - city
        ("Main Street 123", "", "1011", "Hungary", False, "Empty city"),
        ("Main Street 123", "B", "1011", "Hungary", False, "City too short"),
        ("Main Street 123", "City123", "1011", "Hungary", False, "City contains numbers"),

        # Invalid cases - postal code
        ("Main Street 123", "Budapest", "", "Hungary", False, "Empty postal code"),
        ("Main Street 123", "Budapest", "11", "Hungary", False, "Postal code too short"),

        # Invalid cases - country
        ("Main Street 123", "Budapest", "1011", "", False, "Empty country"),
        ("Main Street 123", "Budapest", "1011", "H", False, "Country too short"),
    ]

    for street, city, postal, country, expected_valid, description in test_cases:
        is_valid, error = validate_address(street, city, postal, country)
        status = "✅ PASS" if is_valid == expected_valid else "❌ FAIL"
        print(f"\n{status} - {description}")
        print(f"  Street: '{street}'")
        print(f"  City: '{city}'")
        print(f"  Postal: '{postal}'")
        print(f"  Country: '{country}'")
        print(f"  Valid: {is_valid} (expected: {expected_valid})")
        if not is_valid:
            print(f"  Error: {error}")


def test_name_validation():
    """Test name validation"""
    print("\n" + "="*60)
    print("NAME VALIDATION TESTS")
    print("="*60)

    test_cases = [
        # Valid cases
        ("John", True, "Valid first name"),
        ("Doe", True, "Valid last name"),
        ("O'Brien", True, "Name with apostrophe"),
        ("Jean-Claude", True, "Name with hyphen"),

        # Invalid cases
        ("", False, "Empty name"),
        ("J", False, "Name too short"),
        ("123", False, "No letters in name"),
    ]

    for name, expected_valid, description in test_cases:
        is_valid, error = validate_name(name, "Name")
        status = "✅ PASS" if is_valid == expected_valid else "❌ FAIL"
        print(f"\n{status} - {description}")
        print(f"  Input: '{name}'")
        print(f"  Valid: {is_valid} (expected: {expected_valid})")
        if not is_valid:
            print(f"  Error: {error}")


if __name__ == "__main__":
    print("\n🧪 VALIDATION UTILITIES TEST SUITE")
    test_phone_validation()
    test_address_validation()
    test_name_validation()
    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETED")
    print("="*60 + "\n")
