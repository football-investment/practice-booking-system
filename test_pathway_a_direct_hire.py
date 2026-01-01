#!/usr/bin/env python3
"""
Test PATHWAY A: Direct Hire by Master Instructor
Marco Bellini (master at Budapest) invites Maria García
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def login(email: str, password: str):
    """Login and get access token"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        print(f"✅ Logged in as {email}")
        return token
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None

def direct_hire_instructor(token, assignment_data):
    """Direct hire instructor via assignment API"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BASE_URL}/api/v1/instructor-management/assignments",
        json=assignment_data,
        headers=headers
    )
    print(f"\n{'='*60}")
    print(f"Direct Hire Response: {response.status_code}")
    print(f"{'='*60}")

    if response.status_code in [200, 201]:
        result = response.json()
        print("\n✅ SUCCESS - Assignment Created:")
        print(json.dumps(result, indent=2))
        return result
    else:
        print(f"\n❌ ERROR:")
        print(response.text)
        return None

def main():
    print("\n" + "="*60)
    print("PATHWAY A: DIRECT HIRE TEST")
    print("="*60)

    # Step 1: Login as Marco Bellini (master at Budapest)
    print("\n[1] Logging in as Marco Bellini (Master at Budapest)...")
    token = login("marco.bellini@lfa.com", "admin123")

    if not token:
        print("❌ Cannot proceed - login failed")
        return

    # Step 2: Direct hire Maria García
    print("\n[2] Marco invites Maria García as regular instructor...")
    assignment_data = {
        "location_id": 1,  # Budapest Central Campus
        "instructor_id": 2955,  # Maria García
        "specialization_type": "LFA_COACH",
        "age_group": "Youth Football Coach",
        "year": 2025,
        "time_period_start": "2025-01",
        "time_period_end": "2025-06",
        "is_master": False  # Regular instructor, not master
    }

    print(f"\nAssignment details:")
    print(json.dumps(assignment_data, indent=2))

    result = direct_hire_instructor(token, assignment_data)

    if result:
        print("\n" + "="*60)
        print("✅ PATHWAY A TEST SUCCESSFUL")
        print("="*60)
        print(f"Assignment created: {result.get('assignment_id')}")
        print(f"Instructor: {result.get('instructor_email')}")
        print(f"Validation passed: {result.get('validation_passed')}")
    else:
        print("\n" + "="*60)
        print("❌ PATHWAY A TEST FAILED")
        print("="*60)

if __name__ == "__main__":
    main()
