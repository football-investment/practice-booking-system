"""
Manual Backend API Test - Tournament Creation

This script tests the tournament creation API endpoint directly,
independent of any UI framework (Streamlit/Playwright).

Purpose: Validate that the refactored backend can create tournaments successfully.
"""

import requests
import json
from datetime import date, timedelta

def test_tournament_creation_api():
    """Test tournament creation via direct API calls"""

    print("\n" + "="*70)
    print("🔧 BACKEND API TEST: Tournament Creation")
    print("="*70 + "\n")

    # Step 1: Login as admin
    print("1. Logging in as admin...")
    login_payload = {
        "email": "admin@lfa.com",
        "password": "admin123"
    }

    login_response = requests.post(
        "http://localhost:8000/api/v1/auth/login",
        json=login_payload
    )

    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(f"   Response: {login_response.text}")
        return False

    token = login_response.json()["access_token"]
    print(f"✅ Logged in successfully")

    # Step 2: Get locations
    print("\n2. Fetching locations...")
    locations_response = requests.get(
        "http://localhost:8000/api/v1/admin/locations/",
        headers={"Authorization": f"Bearer {token}"}
    )

    if locations_response.status_code != 200:
        print(f"❌ Failed to fetch locations: {locations_response.status_code}")
        return False

    locations = locations_response.json()
    if not locations:
        print("❌ No locations found in database")
        return False

    location = locations[0]
    location_id = location["id"]
    print(f"✅ Found {len(locations)} locations")
    print(f"   Using: {location['name']} (ID: {location_id})")

    # Step 3: Get campuses
    print("\n3. Fetching campuses...")
    campuses_response = requests.get(
        "http://localhost:8000/api/v1/admin/campuses/",
        headers={"Authorization": f"Bearer {token}"}
    )

    if campuses_response.status_code != 200:
        print(f"❌ Failed to fetch campuses: {campuses_response.status_code}")
        return False

    all_campuses = campuses_response.json()

    # Filter by location_id
    campuses = [c for c in all_campuses if c.get('location_id') == location_id]

    if not campuses:
        print(f"❌ No campuses found for location {location_id}")
        print(f"   Total campuses in DB: {len(all_campuses)}")
        return False

    campus = campuses[0]
    campus_id = campus["id"]
    print(f"✅ Found {len(campuses)} campuses at location {location_id}")
    print(f"   Using: {campus['name']} (ID: {campus_id})")

    # Step 4: Create tournament
    print("\n4. Creating tournament...")
    tournament_date = (date.today() + timedelta(days=1)).isoformat()
    tournament_name = f"Backend API Test {date.today().isoformat()}"

    tournament_payload = {
        "date": tournament_date,
        "name": tournament_name,
        "specialization_type": "LFA_FOOTBALL_PLAYER",
        "campus_id": campus_id,
        "location_id": location_id,
        "age_group": "YOUTH",
        "sessions": [
            {
                "title": "Morning Session",
                "time": "09:00",
                "duration_minutes": 90,
                "capacity": 20
            },
            {
                "title": "Late Morning Session",
                "time": "11:00",
                "duration_minutes": 90,
                "capacity": 20
            }
        ],
        "auto_book_students": False
    }

    print(f"   Tournament: {tournament_name}")
    print(f"   Date: {tournament_date}")
    print(f"   Location ID: {location_id}")
    print(f"   Campus ID: {campus_id}")
    print(f"   Sessions: {len(tournament_payload['sessions'])}")

    create_response = requests.post(
        "http://localhost:8000/api/v1/tournaments/generate",
        headers={"Authorization": f"Bearer {token}"},
        json=tournament_payload
    )

    print(f"\n   POST /api/v1/tournaments/generate")
    print(f"   Status: {create_response.status_code}")

    if create_response.status_code != 201:
        print(f"\n❌ Tournament creation FAILED")
        print(f"   Status: {create_response.status_code}")
        print(f"   Response: {create_response.text}")
        return False

    tournament_data = create_response.json()
    tournament_id = tournament_data.get("tournament_id")

    print(f"\n✅ Tournament created successfully!")
    print(f"   ID: {tournament_id}")
    print(f"   Code: {tournament_data.get('code')}")
    print(f"   Sessions: {tournament_data.get('summary', {}).get('session_count')}")

    # Step 5: Verify in database (via API)
    print("\n5. Verifying tournament in database...")

    semesters_response = requests.get(
        "http://localhost:8000/api/v1/semesters/",
        headers={"Authorization": f"Bearer {token}"}
    )

    if semesters_response.status_code != 200:
        print(f"❌ Failed to fetch semesters: {semesters_response.status_code}")
        return False

    semesters_data = semesters_response.json()
    all_semesters = semesters_data.get("semesters", []) if isinstance(semesters_data, dict) else semesters_data

    # Find our tournament
    tournaments = [s for s in all_semesters if s.get("code", "").startswith("TOURN-")]
    our_tournament = next((t for t in tournaments if t.get("id") == tournament_id), None)

    if not our_tournament:
        print(f"❌ Tournament {tournament_id} NOT found in database!")
        print(f"   Found {len(tournaments)} tournaments total")
        return False

    print(f"✅ Tournament verified in database!")
    print(f"   ID: {our_tournament['id']}")
    print(f"   Name: {our_tournament['name']}")
    print(f"   Code: {our_tournament['code']}")
    print(f"   Status: {our_tournament['status']}")
    print(f"   Age Group: {our_tournament.get('age_group')}")

    # Validate data
    assert our_tournament["code"].startswith("TOURN-"), "Code should start with TOURN-"
    assert our_tournament["status"] == "SEEKING_INSTRUCTOR", f"Expected SEEKING_INSTRUCTOR, got {our_tournament['status']}"
    assert our_tournament["name"] == tournament_name, "Name mismatch"

    print("\n" + "="*70)
    print("✅✅✅ BACKEND API TEST: PASSED")
    print("="*70 + "\n")

    return True


if __name__ == "__main__":
    try:
        success = test_tournament_creation_api()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
