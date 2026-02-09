"""
Manual test script for streamlit_sandbox_MINIMAL.py
Tests the API endpoints used by the minimal sandbox
"""

import requests
from datetime import date

API_BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"

def test_minimal_sandbox_flow():
    print("=" * 60)
    print("🧪 Testing MINIMAL Sandbox Flow")
    print("=" * 60)

    # 1. Login
    print("\n1️⃣ Testing login...")
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.status_code}"
    token = response.json()["access_token"]
    print("   ✅ Login successful")

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Fetch locations
    print("\n2️⃣ Testing locations fetch...")
    response = requests.get(f"{API_BASE_URL}/admin/locations", headers=headers)
    assert response.status_code == 200, f"Locations fetch failed: {response.status_code}"
    locations = response.json()
    assert len(locations) > 0, "No locations found"
    print(f"   ✅ Found {len(locations)} locations")
    print(f"   Example: {locations[0]['name']} ({locations[0]['city']})")

    # 3. Fetch campuses for first location
    print("\n3️⃣ Testing campuses fetch...")
    location_id = locations[0]['id']
    response = requests.get(f"{API_BASE_URL}/admin/locations/{location_id}/campuses", headers=headers)
    assert response.status_code == 200, f"Campuses fetch failed: {response.status_code}"
    campuses = response.json()
    assert len(campuses) > 0, "No campuses found"
    print(f"   ✅ Found {len(campuses)} campuses for location {location_id}")
    print(f"   Example: {campuses[0]['name']}")
    campus_id = campuses[0]['id']

    # 4. Fetch users
    print("\n4️⃣ Testing users fetch...")
    response = requests.get(f"{API_BASE_URL}/sandbox/users?limit=50", headers=headers)
    assert response.status_code == 200, f"Users fetch failed: {response.status_code}"
    users = response.json()
    assert len(users) > 0, "No users found"
    print(f"   ✅ Found {len(users)} users")

    # Get test players (filter for test.player emails)
    test_players = [u for u in users if 'test.player' in u.get('email', '')]
    print(f"   Found {len(test_players)} test players")

    # If no test players, use first available users
    if len(test_players) == 0:
        print("   No test.player users found, using first available users")
        test_players = users[:7]

    selected_user_ids = [u['id'] for u in test_players[:7]]  # Select first 7
    print(f"   Selected user IDs: {selected_user_ids}")

    # 5. Create tournament
    print("\n5️⃣ Testing tournament creation...")
    tournament_config = {
        "tournament_type": "league",
        "name": f"Minimal Sandbox Test {date.today().isoformat()}",
        "tournament_date": date.today().isoformat(),
        "age_group": "AMATEUR",
        "campus_id": campus_id,
        "location_id": location_id,
        "format": "HEAD_TO_HEAD",
        "assignment_type": "OPEN_ASSIGNMENT",
        "max_players": len(selected_user_ids),
        "price_credits": 0,
        "skills_to_test": ["passing", "shooting"]
    }

    response = requests.post(
        f"{API_BASE_URL}/tournaments",
        headers=headers,
        json=tournament_config
    )
    assert response.status_code == 200, f"Tournament creation failed: {response.status_code} - {response.text}"
    tournament_id = response.json()["id"]
    print(f"   ✅ Tournament created with ID: {tournament_id}")

    # 6. Enroll users
    print("\n6️⃣ Testing user enrollment...")
    enrolled_count = 0
    for user_id in selected_user_ids:
        response = requests.post(
            f"{API_BASE_URL}/tournaments/{tournament_id}/enroll",
            headers=headers,
            json={"user_id": user_id}
        )
        if response.status_code == 200:
            enrolled_count += 1
    print(f"   ✅ Enrolled {enrolled_count}/{len(selected_user_ids)} users")

    # 7. Get sessions
    print("\n7️⃣ Testing sessions fetch...")
    response = requests.get(
        f"{API_BASE_URL}/tournaments/{tournament_id}/sessions",
        headers=headers
    )
    assert response.status_code == 200, f"Sessions fetch failed: {response.status_code}"
    sessions = response.json()
    print(f"   ✅ Found {len(sessions)} sessions")

    if sessions:
        session_id = sessions[0]['id']
        print(f"   First session ID: {session_id}")

        # 8. Test marking attendance
        print("\n8️⃣ Testing attendance marking...")
        response = requests.post(
            f"{API_BASE_URL}/sessions/{session_id}/attendance",
            headers=headers,
            json={"user_id": selected_user_ids[0], "status": "PRESENT"}
        )
        if response.status_code == 200:
            print(f"   ✅ Attendance marked for user {selected_user_ids[0]}")
        else:
            print(f"   ⚠️  Attendance marking status: {response.status_code}")

        # 9. Test entering result
        print("\n9️⃣ Testing result entry...")
        if len(selected_user_ids) >= 2:
            response = requests.post(
                f"{API_BASE_URL}/sessions/{session_id}/result",
                headers=headers,
                json={
                    "winner_id": selected_user_ids[0],
                    "loser_id": selected_user_ids[1],
                    "score": "3-1"
                }
            )
            if response.status_code == 200:
                print(f"   ✅ Result entered successfully")
            else:
                print(f"   ⚠️  Result entry status: {response.status_code}")

    # 10. Get leaderboard
    print("\n🔟 Testing leaderboard fetch...")
    response = requests.get(
        f"{API_BASE_URL}/tournaments/{tournament_id}/leaderboard",
        headers=headers
    )
    if response.status_code == 200:
        leaderboard = response.json()
        print(f"   ✅ Leaderboard retrieved: {len(leaderboard)} entries")
        if leaderboard:
            print(f"   Top entry: User {leaderboard[0].get('user_id')} - {leaderboard[0].get('total_points', 0)} pts")
    else:
        print(f"   ⚠️  Leaderboard status: {response.status_code}")

    # 11. Distribute rewards
    print("\n1️⃣1️⃣ Testing reward distribution...")
    response = requests.post(
        f"{API_BASE_URL}/tournaments/{tournament_id}/rewards/distribute",
        headers=headers
    )
    if response.status_code == 200:
        print(f"   ✅ Rewards distributed successfully")
    else:
        print(f"   ⚠️  Reward distribution status: {response.status_code}")

    print("\n" + "=" * 60)
    print("✅ ALL MINIMAL SANDBOX API TESTS COMPLETED")
    print("=" * 60)
    print(f"\n📋 Summary:")
    print(f"   - Location ID: {location_id}")
    print(f"   - Campus ID: {campus_id}")
    print(f"   - Tournament ID: {tournament_id}")
    print(f"   - Users enrolled: {enrolled_count}")
    print(f"   - Sessions created: {len(sessions)}")
    print(f"\n🎯 The minimal sandbox can now be tested at:")
    print(f"   http://localhost:8502")

if __name__ == "__main__":
    try:
        test_minimal_sandbox_flow()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
