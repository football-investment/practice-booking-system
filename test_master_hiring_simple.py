"""
Simplified Test for Master Hiring API Endpoints
Direct testing of new master hiring functionality
"""
import requests
import json
from datetime import datetime, timedelta, timezone
import jwt

BASE_URL = "http://localhost:8000/api/v1"
SECRET_KEY = "super-secret-jwt-key-change-this"

# Test data from database
LOCATION_ID = 1  # Budapest
INSTRUCTOR_ID = 2949  # Marco Bellini
ADMIN_ID = 4

def create_jwt_token(user_id: int, email: str, role: str):
    """Create a valid JWT token for testing"""
    payload = {
        "sub": email,  # Backend expects email in 'sub' field
        "email": email,
        "role": role,
        "type": "access",  # Required by verify_token
        "exp": datetime.now(timezone.utc) + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def test_direct_hire_offer():
    """Test creating a direct hire offer"""
    print("\n" + "="*70)
    print("TEST 1: Create Direct Hire Offer")
    print("="*70)

    # Create admin token
    admin_token = create_jwt_token(ADMIN_ID, "admin@yourcompany.com", "ADMIN")

    # Create offer payload
    start_date = (datetime.now() + timedelta(days=30)).isoformat()
    end_date = (datetime.now() + timedelta(days=395)).isoformat()

    payload = {
        "location_id": LOCATION_ID,
        "instructor_id": INSTRUCTOR_ID,
        "contract_start": start_date,
        "contract_end": end_date,
        "offer_deadline_days": 14,
        "override_availability": True  # Override any availability issues for testing
    }

    print(f"\nSending direct hire offer:")
    print(f"  Location ID: {LOCATION_ID} (Budapest)")
    print(f"  Instructor ID: {INSTRUCTOR_ID} (Marco Bellini)")
    print(f"  Contract: {start_date[:10]} to {end_date[:10]}")
    print(f"  Deadline: 14 days")

    response = requests.post(
        f"{BASE_URL}/instructor-management/masters/direct-hire",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=payload
    )

    print(f"\n Response Status: {response.status_code}")
    print(f"\nResponse Body:")
    try:
        data = response.json()
        print(json.dumps(data, indent=2, default=str))

        if response.status_code == 201:
            print(f"\n✅ SUCCESS! Offer created with ID: {data.get('id')}")
            print(f"   Offer Status: {data.get('offer_status')}")
            print(f"   Active: {data.get('is_active')}")
            print(f"   Availability Match: {data.get('availability_match_score')}%")
            return data.get('id')
        else:
            print(f"\n❌ FAILED: {data.get('error', {}).get('message', 'Unknown error')}")
            return None
    except Exception as e:
        print(f"Error parsing response: {e}")
        print(response.text)
        return None

def test_get_pending_offers():
    """Test getting all pending offers (admin view)"""
    print("\n" + "="*70)
    print("TEST 2: Get Pending Offers (Admin)")
    print("="*70)

    admin_token = create_jwt_token(ADMIN_ID, "admin@yourcompany.com", "ADMIN")

    response = requests.get(
        f"{BASE_URL}/instructor-management/masters/pending-offers",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    print(f"\nResponse Status: {response.status_code}")
    try:
        data = response.json()
        print(f"\nResponse Body:")
        print(json.dumps(data, indent=2, default=str))

        if response.status_code == 200:
            print(f"\n✅ SUCCESS! Found {len(data)} pending offers")
            return data
        else:
            print(f"\n❌ FAILED: {data.get('error', {}).get('message', 'Unknown error')}")
            return []
    except Exception as e:
        print(f"Error: {e}")
        print(response.text)
        return []

def test_get_my_offers():
    """Test getting instructor's own offers"""
    print("\n" + "="*70)
    print("TEST 3: Get My Offers (Instructor)")
    print("="*70)

    instructor_token = create_jwt_token(INSTRUCTOR_ID, "marco.bellini@lfa.com", "INSTRUCTOR")

    response = requests.get(
        f"{BASE_URL}/instructor-management/masters/my-offers",
        headers={"Authorization": f"Bearer {instructor_token}"},
        params={"status": "OFFERED"}
    )

    print(f"\nResponse Status: {response.status_code}")
    try:
        data = response.json()
        print(f"\nResponse Body:")
        print(json.dumps(data, indent=2, default=str))

        if response.status_code == 200:
            print(f"\n✅ SUCCESS! Instructor has {len(data)} pending offers")
            return data
        else:
            print(f"\n❌ FAILED: {data.get('error', {}).get('message', 'Unknown error')}")
            return []
    except Exception as e:
        print(f"Error: {e}")
        print(response.text)
        return []

def test_accept_offer(offer_id: int):
    """Test instructor accepting an offer"""
    print("\n" + "="*70)
    print(f"TEST 4: Accept Offer (Instructor) - Offer ID: {offer_id}")
    print("="*70)

    instructor_token = create_jwt_token(INSTRUCTOR_ID, "marco.bellini@lfa.com", "INSTRUCTOR")

    payload = {"action": "ACCEPT"}

    response = requests.patch(
        f"{BASE_URL}/instructor-management/masters/offers/{offer_id}/respond",
        headers={"Authorization": f"Bearer {instructor_token}"},
        json=payload
    )

    print(f"\nResponse Status: {response.status_code}")
    try:
        data = response.json()
        print(f"\nResponse Body:")
        print(json.dumps(data, indent=2, default=str))

        if response.status_code == 200:
            print(f"\n✅ SUCCESS! Offer accepted!")
            print(f"   Status: {data.get('offer_status')}")
            print(f"   Active: {data.get('is_active')}")
            print(f"   Accepted At: {data.get('accepted_at')}")
            return True
        else:
            print(f"\n❌ FAILED: {data.get('error', {}).get('message', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        print(response.text)
        return False

def main():
    print("\n" + "="*70)
    print("🚀 MASTER HIRING API TESTS")
    print("="*70)
    print("\nTesting hybrid master instructor hiring system...")
    print("PATHWAY A: Direct Hire Workflow")

    # Test 1: Create direct hire offer
    offer_id = test_direct_hire_offer()

    if offer_id:
        # Test 2: View pending offers (admin)
        test_get_pending_offers()

        # Test 3: View my offers (instructor)
        test_get_my_offers()

        # Test 4: Accept offer (instructor)
        test_accept_offer(offer_id)

        # Test 5: Verify offer is no longer pending
        print("\n" + "="*70)
        print("TEST 5: Verify Offer Accepted (Check Pending List)")
        print("="*70)
        pending = test_get_pending_offers()
        if not any(o.get('id') == offer_id for o in pending):
            print(f"\n✅ SUCCESS! Offer {offer_id} no longer in pending list")
        else:
            print(f"\n❌ WARNING: Offer {offer_id} still in pending list")

    print("\n" + "="*70)
    print("✅ ALL TESTS COMPLETE!")
    print("="*70)

if __name__ == "__main__":
    main()
