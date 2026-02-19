#!/usr/bin/env python3
"""
Test Credit Validation Fix
===========================
Tests the critical security fix for credit validation on specialization unlock endpoints.

Test Cases:
1. User with 10 credits attempts to unlock LFA Player (should FAIL with 402)
2. User with 150 credits attempts to unlock LFA Player (should SUCCEED with 201)
3. Verify credit balance is deducted correctly (150 - 100 = 50)
"""

import requests
import json
from typing import Tuple

API_BASE_URL = "http://localhost:8000"

def get_admin_token() -> str:
    """Get admin authentication token"""
    response = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"email": "admin@lfa.com", "password": "admin123"}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Admin login failed: {response.text}")

def get_user_from_db(user_id: int, admin_token: str) -> dict:
    """Get user details from database"""
    response = requests.get(
        f"{API_BASE_URL}/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get user {user_id}: {response.text}")

def get_user_token(email: str, password: str = "admin123") -> str:
    """Get user authentication token"""
    response = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"User login failed for {email}: {response.text}")

def test_insufficient_credits(user_id: int, user_email: str, admin_token: str) -> Tuple[bool, str]:
    """
    Test Case 1: User with 10 credits attempts to unlock specialization
    Expected: HTTP 402 Payment Required
    """
    print(f"\n{'='*80}")
    print(f"TEST 1: Insufficient Credits ({user_email})")
    print(f"{'='*80}")

    # Get user details
    user = get_user_from_db(user_id, admin_token)
    print(f"User ID: {user['id']}")
    print(f"Email: {user['email']}")
    print(f"Credit Balance: {user['credit_balance']} credits")

    # Login as user to get their token
    print(f"\nLogging in as {user_email}...")
    user_token = get_user_token(user_email)
    print("✅ User authenticated")

    # Attempt to create LFA Player license
    print(f"\nAttempting to unlock LFA Player specialization...")
    print(f"Required: 100 credits")
    print(f"Available: {user['credit_balance']} credits")

    response = requests.post(
        f"{API_BASE_URL}/api/v1/lfa-player/licenses",
        json={"age_group": "YOUTH"},
        headers={"Authorization": f"Bearer {user_token}"}
    )

    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Body: {json.dumps(response.json(), indent=2)}")

    if response.status_code == 402:
        print("\n✅ TEST PASSED: Request correctly rejected with 402 Payment Required")
        error_data = response.json()
        error_message = error_data.get("error", {}).get("message", error_data.get("detail", ""))
        if "Insufficient credits" in error_message:
            print(f"✅ Error message is clear: {error_message}")
            return True, "PASSED"
        else:
            print(f"⚠️  Error message unclear: {error_message}")
            return False, "FAILED - Error message unclear"
    else:
        print(f"\n❌ TEST FAILED: Expected 402, got {response.status_code}")
        print("❌ SECURITY VULNERABILITY: User was able to unlock specialization without sufficient credits!")
        return False, "FAILED - Security breach"

def test_sufficient_credits(user_id: int, user_email: str, admin_token: str) -> Tuple[bool, str]:
    """
    Test Case 2: User with 150 credits attempts to unlock specialization
    Expected: HTTP 201 Created, credit balance reduced to 50
    """
    print(f"\n{'='*80}")
    print(f"TEST 2: Sufficient Credits ({user_email})")
    print(f"{'='*80}")

    # Get user details BEFORE
    user_before = get_user_from_db(user_id, admin_token)
    print(f"User ID: {user_before['id']}")
    print(f"Email: {user_before['email']}")
    print(f"Credit Balance BEFORE: {user_before['credit_balance']} credits")

    # Login as user to get their token
    print(f"\nLogging in as {user_email}...")
    user_token = get_user_token(user_email)
    print("✅ User authenticated")

    # Attempt to create LFA Player license
    print(f"\nAttempting to unlock LFA Player specialization...")
    print(f"Required: 100 credits")
    print(f"Available: {user_before['credit_balance']} credits")

    response = requests.post(
        f"{API_BASE_URL}/api/v1/lfa-player/licenses",
        json={"age_group": "YOUTH"},
        headers={"Authorization": f"Bearer {user_token}"}
    )

    print(f"\nResponse Status: {response.status_code}")

    if response.status_code == 201:
        license_data = response.json()
        print(f"Response Body: {json.dumps(license_data, indent=2)}")
        print("\n✅ License created successfully")

        # Get user details AFTER to verify credit deduction
        user_after = get_user_from_db(user_id, admin_token)
        balance_after = user_after['credit_balance']
        expected_balance = user_before['credit_balance'] - 100

        print(f"\nCredit Balance AFTER: {balance_after} credits")
        print(f"Expected Balance: {expected_balance} credits")

        if balance_after == expected_balance:
            print(f"✅ Credits deducted correctly: {user_before['credit_balance']} - 100 = {balance_after}")
            return True, "PASSED"
        else:
            print(f"❌ Credit deduction FAILED: Expected {expected_balance}, got {balance_after}")
            return False, f"FAILED - Credit deduction incorrect"
    else:
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")
        print(f"\n❌ TEST FAILED: Expected 201, got {response.status_code}")
        return False, f"FAILED - Expected 201, got {response.status_code}"

def test_duplicate_license_prevention(user_id: int, user_email: str, admin_token: str) -> Tuple[bool, str]:
    """
    Test Case 3: User attempts to create second license (will fail due to insufficient credits)
    Expected: HTTP 402 Payment Required (user only has 50 credits after Test 2, needs 100)
    """
    print(f"\n{'='*80}")
    print(f"TEST 3: Second License Attempt with Insufficient Credits ({user_email})")
    print(f"{'='*80}")

    # Login as user to get their token
    print(f"Logging in as {user_email}...")
    user_token = get_user_token(user_email)
    print("✅ User authenticated")

    # Get current credit balance
    user = get_user_from_db(user_id, admin_token)
    print(f"\nCurrent Credit Balance: {user['credit_balance']} credits")
    print(f"Required: 100 credits")

    # User should already have a license from Test 2 and only 50 credits left
    print(f"\nAttempting to create SECOND LFA Player license...")

    response = requests.post(
        f"{API_BASE_URL}/api/v1/lfa-player/licenses",
        json={"age_group": "PRO"},
        headers={"Authorization": f"Bearer {user_token}"}
    )

    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Body: {json.dumps(response.json(), indent=2)}")

    if response.status_code == 402:
        error_data = response.json()
        error_message = error_data.get("error", {}).get("message", error_data.get("detail", ""))
        if "Insufficient credits" in error_message:
            print("\n✅ TEST PASSED: Second license correctly rejected due to insufficient credits")
            print(f"✅ Error message: {error_message}")

            # Verify credits were NOT deducted
            user_after = get_user_from_db(user_id, admin_token)
            if user_after['credit_balance'] == 50:  # Should still be 50 from Test 2
                print(f"✅ Credits NOT deducted for failed attempt: {user_after['credit_balance']} credits")
                return True, "PASSED"
            else:
                print(f"⚠️  Credit balance unexpected: {user_after['credit_balance']} (expected 50)")
                return False, "FAILED - Credits deducted on failed attempt"
        else:
            print(f"⚠️  Error message unclear: {error_message}")
            return False, "FAILED - Error message unclear"
    else:
        print(f"\n❌ TEST FAILED: Expected 402, got {response.status_code}")
        return False, f"FAILED - Expected 402, got {response.status_code}"

def main():
    """Run all test cases"""
    print("="*80)
    print("CREDIT VALIDATION FIX - TEST SUITE")
    print("="*80)
    print("Testing critical security fix for specialization unlock endpoints")
    print()

    try:
        # Get admin token
        print("Logging in as admin...")
        admin_token = get_admin_token()
        print("✅ Admin authenticated")

        # Test users from database (update IDs after fresh creation)
        LOW_CREDIT_USER_ID = 2943  # testlow@test.com (10 credits)
        HIGH_CREDIT_USER_ID = 2944  # testhigh@test.com (150 credits)

        results = []

        # Test 1: Insufficient credits (should FAIL with 402)
        passed, message = test_insufficient_credits(
            LOW_CREDIT_USER_ID,
            "testlow@test.com",
            admin_token
        )
        results.append(("Test 1: Insufficient Credits", passed, message))

        # Test 2: Sufficient credits (should SUCCEED with 201)
        passed, message = test_sufficient_credits(
            HIGH_CREDIT_USER_ID,
            "testhigh@test.com",
            admin_token
        )
        results.append(("Test 2: Sufficient Credits", passed, message))

        # Test 3: Duplicate license prevention
        passed, message = test_duplicate_license_prevention(
            HIGH_CREDIT_USER_ID,
            "testhigh@test.com",
            admin_token
        )
        results.append(("Test 3: Second License with Insufficient Credits", passed, message))

        # Print summary
        print(f"\n{'='*80}")
        print("TEST SUMMARY")
        print(f"{'='*80}")

        for test_name, passed, message in results:
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{status} - {test_name}: {message}")

        all_passed = all(passed for _, passed, _ in results)

        print(f"\n{'='*80}")
        if all_passed:
            print("🎉 ALL TESTS PASSED - Security fix verified!")
            print("✅ Credit validation is working correctly")
            print("✅ Specialization unlocking is secure")
        else:
            print("⚠️  SOME TESTS FAILED - Review results above")
            failed_count = sum(1 for _, passed, _ in results if not passed)
            print(f"❌ {failed_count}/{len(results)} tests failed")
        print(f"{'='*80}")

    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED WITH ERROR:")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
