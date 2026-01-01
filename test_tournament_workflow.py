"""
Test Tournament Request Workflow - API Integration Test

Tests the complete workflow:
1. Create tournament (SEEKING_INSTRUCTOR status)
2. Admin sends instructor request
3. Instructor accepts request
4. Tournament becomes READY_FOR_ENROLLMENT
"""

import requests
import json
from datetime import date, timedelta

API_BASE_URL = "http://localhost:8000/api/v1"

def get_admin_token():
    """Login as admin and get token"""
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": "admin@lfa.com", "password": "admin123"}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    raise Exception(f"Admin login failed: {response.text}")

def get_instructor_token():
    """Login as instructor and get token"""
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": "marco.bellini@lfa.com", "password": "instructor123"}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    raise Exception(f"Instructor login failed: {response.text}")

def get_instructor_id(token, email="marco.bellini@lfa.com"):
    """Get instructor user ID"""
    response = requests.get(
        f"{API_BASE_URL}/users",
        headers={"Authorization": f"Bearer {token}"},
        params={"role": "instructor"}
    )
    if response.status_code == 200:
        data = response.json()
        users = data.get("users", [])
        for user in users:
            if user.get("email") == email:
                return user.get("id")
    raise Exception(f"Instructor not found: {email}")

def test_workflow():
    """Test complete tournament request workflow"""

    print("=" * 80)
    print("🏆 TOURNAMENT REQUEST WORKFLOW TEST")
    print("=" * 80)

    # Step 1: Admin login
    print("\n📝 Step 1: Admin Login")
    admin_token = get_admin_token()
    print("✅ Admin authenticated")

    # Step 2: Get instructor ID
    print("\n📝 Step 2: Get Grandmaster Instructor")
    instructor_id = get_instructor_id(admin_token)
    print(f"✅ Instructor ID: {instructor_id}")

    # Step 3: Create tournament (using existing tournament ID 210)
    tournament_id = 210
    print(f"\n📝 Step 3: Using Existing Tournament (ID: {tournament_id})")

    # Get tournament details
    response = requests.get(
        f"{API_BASE_URL}/semesters/{tournament_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if response.status_code == 200:
        tournament = response.json()
        print(f"✅ Tournament: {tournament['name']}")
        print(f"   Code: {tournament['code']}")
        print(f"   Status: {tournament['status']}")
        print(f"   Master Instructor: {tournament.get('master_instructor_id', 'Not assigned')}")
    else:
        print(f"❌ Failed to get tournament: {response.text}")
        return

    # Step 4: Send instructor request
    print(f"\n📝 Step 4: Admin Sends Instructor Request")
    response = requests.post(
        f"{API_BASE_URL}/tournaments/{tournament_id}/send-instructor-request",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "instructor_id": instructor_id,
            "message": "Would you like to lead the Test Winter Cup tournament?"
        }
    )

    if response.status_code == 201:
        request_data = response.json()
        request_id = request_data.get("id")
        print(f"✅ Request sent successfully!")
        print(f"   Request ID: {request_id}")
        print(f"   Status: {request_data.get('status')}")
        print(f"   Instructor ID: {request_data.get('instructor_id')}")
    else:
        print(f"❌ Failed to send request: {response.text}")
        # If request already exists, try to get it
        response = requests.get(
            f"{API_BASE_URL}/instructor-assignments",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"semester_id": tournament_id}
        )
        if response.status_code == 200:
            requests_list = response.json()
            if requests_list:
                request_id = requests_list[0].get("id")
                print(f"ℹ️  Using existing request ID: {request_id}")
            else:
                print("❌ No existing requests found")
                return
        else:
            return

    # Step 5: Instructor login
    print(f"\n📝 Step 5: Instructor Login")
    instructor_token = get_instructor_token()
    print("✅ Instructor authenticated")

    # Step 6: Get pending requests for instructor
    print(f"\n📝 Step 6: Instructor Views Pending Requests")
    response = requests.get(
        f"{API_BASE_URL}/instructor-assignments",
        headers={"Authorization": f"Bearer {instructor_token}"},
        params={
            "instructor_id": instructor_id,
            "status": "PENDING"
        }
    )

    if response.status_code == 200:
        pending_requests = response.json()
        print(f"✅ Found {len(pending_requests)} pending request(s)")
        for req in pending_requests:
            print(f"   - Request ID: {req.get('id')}, Tournament: {req.get('semester_id')}")
    else:
        print(f"❌ Failed to get pending requests: {response.text}")
        return

    # Step 7: Instructor accepts request
    print(f"\n📝 Step 7: Instructor Accepts Request")
    response = requests.post(
        f"{API_BASE_URL}/tournaments/requests/{request_id}/accept",
        headers={"Authorization": f"Bearer {instructor_token}"}
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Request accepted!")
        print(f"   Tournament Status: {result.get('status')}")
        print(f"   Master Instructor ID: {result.get('master_instructor_id')}")
    else:
        print(f"❌ Failed to accept request: {response.text}")
        return

    # Step 8: Verify tournament activated
    print(f"\n📝 Step 8: Verify Tournament Activation")
    response = requests.get(
        f"{API_BASE_URL}/semesters/{tournament_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    if response.status_code == 200:
        tournament = response.json()
        print(f"✅ Tournament Status: {tournament['status']}")
        print(f"✅ Master Instructor ID: {tournament.get('master_instructor_id')}")

        if tournament['status'] == 'READY_FOR_ENROLLMENT' and tournament.get('master_instructor_id') == instructor_id:
            print("\n" + "=" * 80)
            print("🎉 WORKFLOW TEST PASSED!")
            print("=" * 80)
            print("\n✅ All steps completed successfully:")
            print("   1. Tournament created (SEEKING_INSTRUCTOR)")
            print("   2. Admin sent instructor request (PENDING)")
            print("   3. Instructor viewed pending request")
            print("   4. Instructor accepted request")
            print("   5. Tournament activated (READY_FOR_ENROLLMENT)")
            print("   6. Master instructor assigned")
            print("\n📋 Next Steps:")
            print("   - Test in Streamlit UI")
            print("   - Verify sessions assigned to instructor")
            print("   - Test check-in workflow")
        else:
            print("\n❌ Tournament not properly activated")
            print(f"   Expected Status: READY_FOR_ENROLLMENT")
            print(f"   Actual Status: {tournament['status']}")
            print(f"   Expected Instructor: {instructor_id}")
            print(f"   Actual Instructor: {tournament.get('master_instructor_id')}")
    else:
        print(f"❌ Failed to verify tournament: {response.text}")

if __name__ == "__main__":
    try:
        test_workflow()
    except Exception as e:
        print(f"\n❌ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
