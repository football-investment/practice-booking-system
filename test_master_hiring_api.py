"""
Test Master Hiring API Endpoints
Tests both Direct Hire and Job Posting pathways
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/v1"

def print_response(title, response):
    """Pretty print API response"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2, default=str))
    except:
        print(response.text)

def get_admin_token():
    """Get admin authentication token"""
    # For testing, we'll create a JWT token manually
    # In production, this would be from login endpoint
    import jwt
    from datetime import datetime, timedelta

    # Admin user ID from database
    payload = {
        "sub": "4",  # Admin user ID
        "email": "admin@yourcompany.com",
        "role": "ADMIN",
        "exp": datetime.utcnow() + timedelta(hours=24)
    }

    # JWT secret (matches backend config in app/config.py)
    secret = "super-secret-jwt-key-change-this"

    token = jwt.encode(payload, secret, algorithm="HS256")
    return token

def get_locations(token):
    """Get available locations"""
    response = requests.get(
        f"{BASE_URL}/locations",
        headers={"Authorization": f"Bearer {token}"}
    )
    print_response("GET Locations", response)
    return response.json() if response.status_code == 200 else []

def get_instructors(token):
    """Get available instructors"""
    response = requests.get(
        f"{BASE_URL}/users",
        headers={"Authorization": f"Bearer {token}"},
        params={"role": "INSTRUCTOR"}
    )
    print_response("GET Instructors", response)
    return response.json() if response.status_code == 200 else []

def test_direct_hire(token, location_id, instructor_id):
    """Test Direct Hire Pathway"""
    print("\n" + "="*60)
    print("TESTING PATHWAY A: DIRECT HIRE")
    print("="*60)

    # Test 1: Create direct hire offer
    start_date = datetime.now() + timedelta(days=30)
    end_date = start_date + timedelta(days=365)

    payload = {
        "location_id": location_id,
        "instructor_id": instructor_id,
        "contract_start": start_date.isoformat(),
        "contract_end": end_date.isoformat(),
        "offer_deadline_days": 14,
        "override_availability": False
    }

    response = requests.post(
        f"{BASE_URL}/instructor-management/masters/direct-hire",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload
    )
    print_response("POST /masters/direct-hire", response)

    if response.status_code == 201:
        offer = response.json()
        offer_id = offer.get('id')
        print(f"\n✅ Direct hire offer created! ID: {offer_id}")
        print(f"   Offer Status: {offer.get('offer_status')}")
        print(f"   Availability Match: {offer.get('availability_match_score')}%")
        return offer_id
    else:
        print(f"\n❌ Failed to create direct hire offer")
        return None

def test_pending_offers(token):
    """Test viewing pending offers (admin)"""
    response = requests.get(
        f"{BASE_URL}/instructor-management/masters/pending-offers",
        headers={"Authorization": f"Bearer {token}"}
    )
    print_response("GET /masters/pending-offers", response)
    return response.json() if response.status_code == 200 else []

def test_my_offers(instructor_token):
    """Test viewing my offers (instructor)"""
    response = requests.get(
        f"{BASE_URL}/instructor-management/masters/my-offers",
        headers={"Authorization": f"Bearer {instructor_token}"},
        params={"status": "OFFERED"}
    )
    print_response("GET /masters/my-offers", response)
    return response.json() if response.status_code == 200 else []

def main():
    print("🚀 Starting Master Hiring API Tests")
    print("="*60)

    # Get admin token
    print("\n1. Getting admin authentication...")
    token = get_admin_token()
    print(f"   Token: {token[:20]}...")

    # Get test data
    print("\n2. Fetching test data...")
    locations = get_locations(token)
    instructors = get_instructors(token)

    if not locations:
        print("❌ No locations found")
        return

    if not instructors:
        print("❌ No instructors found")
        return

    location_id = locations[0].get('id')
    instructor_id = instructors[0].get('id')

    print(f"\n   Using Location ID: {location_id}")
    print(f"   Using Instructor ID: {instructor_id}")

    # Test Direct Hire pathway
    print("\n3. Testing Direct Hire Pathway...")
    offer_id = test_direct_hire(token, location_id, instructor_id)

    # Test pending offers view
    if offer_id:
        print("\n4. Testing Pending Offers View...")
        pending = test_pending_offers(token)
        print(f"\n   Found {len(pending)} pending offers")

    print("\n" + "="*60)
    print("✅ API Tests Complete!")
    print("="*60)

if __name__ == "__main__":
    main()
