"""
End-to-End Test: Competitive Instructor Hiring Workflow
Tests all 8 validation steps for PATHWAY B (Job Posting)
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
DIEGO_EMAIL = "diego.rodriguez@lfa.com"
DIEGO_PASSWORD = "testpass123"
GRANDMASTER_EMAIL = "grandmaster@lfa.com"
GRANDMASTER_PASSWORD = "testpass123"

def login(email, password):
    """Login and get access token"""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"❌ Login failed: {response.text}")
        return None

def test_application_without_availability():
    """TEST 1: Diego applies WITHOUT availability → should be REJECTED"""
    print("\n" + "="*80)
    print("TEST 1: Application WITHOUT Availability")
    print("="*80)

    token = login(DIEGO_EMAIL, DIEGO_PASSWORD)
    if not token:
        return

    # Try to apply to position ID 1
    response = requests.post(
        f"{BASE_URL}/instructor-management/applications/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "position_id": 1,
            "application_message": "I am interested in this position and ready to teach!"
        }
    )

    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    if response.status_code == 403:
        print("\n✅ VALIDATION PASSED: Application rejected due to missing availability")
    else:
        print("\n❌ VALIDATION FAILED: Should have been rejected with 403")

def create_diego_availability():
    """STEP 2: Create availability record for Diego"""
    print("\n" + "="*80)
    print("STEP 2: Creating Availability Record for Diego")
    print("="*80)

    import psycopg2
    conn = psycopg2.connect(
        dbname="lfa_intern_system",
        user="postgres",
        password="postgres",
        host="localhost"
    )
    cur = conn.cursor()

    # Insert availability record
    cur.execute("""
        INSERT INTO instructor_specialization_availability
        (instructor_id, specialization_type, time_period_code, year, location_city, is_available)
        VALUES (2951, 'LFA_PLAYER_YOUTH', 'Q1', 2026, 'Budaörs', true)
        RETURNING id
    """)

    avail_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    print(f"✅ Created availability record ID: {avail_id}")

def test_application_with_availability():
    """TEST 2: Diego applies WITH availability → should SUCCEED"""
    print("\n" + "="*80)
    print("TEST 2: Application WITH Availability")
    print("="*80)

    token = login(DIEGO_EMAIL, DIEGO_PASSWORD)
    if not token:
        return

    # Try to apply to position ID 1
    response = requests.post(
        f"{BASE_URL}/instructor-management/applications/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "position_id": 1,
            "application_message": "I am interested in this position and ready to teach!"
        }
    )

    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    if response.status_code == 201:
        print("\n✅ APPLICATION SUCCESSFUL: Diego's application submitted")
        return response.json()["id"]
    else:
        print(f"\n❌ APPLICATION FAILED: {response.json()}")
        return None

def test_master_views_applications():
    """TEST 3: Grandmaster views applications"""
    print("\n" + "="*80)
    print("TEST 3: Master Views Applications")
    print("="*80)

    token = login(GRANDMASTER_EMAIL, GRANDMASTER_PASSWORD)
    if not token:
        return

    # Get applications for position
    response = requests.get(
        f"{BASE_URL}/instructor-management/applications/position/1",
        headers={"Authorization": f"Bearer {token}"}
    )

    print(f"\nStatus Code: {response.status_code}")
    if response.status_code == 200:
        applications = response.json()
        print(f"Found {len(applications.get('applications', []))} application(s)")
        for app in applications.get('applications', []):
            print(f"  - Applicant: {app.get('applicant_name')}")
            print(f"    Status: {app.get('status')}")
            print(f"    Message: {app.get('application_message')[:50]}...")

def test_duplicate_application():
    """TEST 4: Diego tries to apply AGAIN → should be REJECTED"""
    print("\n" + "="*80)
    print("TEST 4: Duplicate Application")
    print("="*80)

    token = login(DIEGO_EMAIL, DIEGO_PASSWORD)
    if not token:
        return

    response = requests.post(
        f"{BASE_URL}/instructor-management/applications/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "position_id": 1,
            "application_message": "Applying again!"
        }
    )

    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    if response.status_code == 400 and "already applied" in response.text:
        print("\n✅ VALIDATION PASSED: Duplicate application rejected")
    else:
        print("\n❌ VALIDATION FAILED: Should have rejected duplicate")

def run_all_tests():
    """Run complete test suite"""
    print("\n" + "#"*80)
    print("# COMPETITIVE HIRING WORKFLOW - END-TO-END TEST")
    print("#"*80)

    # Test 1: Application without availability (should fail)
    test_application_without_availability()

    # Step 2: Create availability for Diego
    create_diego_availability()

    # Test 2: Application with availability (should succeed)
    app_id = test_application_with_availability()

    if app_id:
        # Test 3: Master views applications
        test_master_views_applications()

        # Test 4: Duplicate application (should fail)
        test_duplicate_application()

    print("\n" + "#"*80)
    print("# TEST SUITE COMPLETE")
    print("#"*80)

if __name__ == "__main__":
    run_all_tests()
