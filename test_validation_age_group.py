#!/usr/bin/env python3
"""
Test age group validation
Maria (Level 4 = Youth Head Coach) tries to teach PRO age group → should FAIL
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
        return None

def create_assignment(token, assignment_data):
    """Create assignment via API"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BASE_URL}/api/v1/instructor-management/assignments",
        json=assignment_data,
        headers=headers
    )
    print(f"\n{'='*60}")
    print(f"Response: {response.status_code}")
    print(f"{'='*60}")

    if response.status_code in [200, 201]:
        print("\n✅ SUCCESS:")
        print(json.dumps(response.json(), indent=2))
        return True
    else:
        print(f"\n❌ VALIDATION BLOCKED (Expected):")
        print(json.dumps(response.json(), indent=2))
        return False

def main():
    print("\n" + "="*60)
    print("AGE GROUP VALIDATION TEST")
    print("="*60)
    print("Maria García: Level 4 = Youth Head Coach")
    print("Can teach: PRE + YOUTH")
    print("Cannot teach: AMATEUR, PRO")
    print("="*60)

    token = login("marco.bellini@lfa.com", "admin123")
    if not token:
        return

    # TEST 1: Valid age group (YOUTH)
    print("\n[TEST 1] Assigning Maria to YOUTH (should SUCCEED)")
    valid_data = {
        "location_id": 1,
        "instructor_id": 2955,
        "specialization_type": "LFA_COACH",
        "age_group": "Youth Football Coach",
        "year": 2025,
        "time_period_start": "2025-01",
        "time_period_end": "2025-06",
        "is_master": False
    }

    result1 = create_assignment(token, valid_data)

    # Delete assignment if created
    if result1:
        print("\n[Cleanup] Deleting assignment...")
        requests.delete(
            f"{BASE_URL}/api/v1/instructor-management/assignments/4",
            headers={"Authorization": f"Bearer {token}"}
        )

    # TEST 2: Invalid age group (PRO)
    print("\n[TEST 2] Assigning Maria to PRO (should FAIL)")
    invalid_data = {
        "location_id": 1,
        "instructor_id": 2955,
        "specialization_type": "LFA_COACH",
        "age_group": "Pro Football Coach",  # Maria can't teach PRO!
        "year": 2025,
        "time_period_start": "2025-07",
        "time_period_end": "2025-12",
        "is_master": False
    }

    result2 = create_assignment(token, invalid_data)

    print("\n" + "="*60)
    print("VALIDATION TEST SUMMARY")
    print("="*60)
    print(f"✅ Test 1 (YOUTH - valid): {'PASSED' if result1 else 'FAILED'}")
    print(f"✅ Test 2 (PRO - invalid): {'PASSED (correctly blocked)' if not result2 else 'FAILED (should have blocked)'}")

if __name__ == "__main__":
    main()
