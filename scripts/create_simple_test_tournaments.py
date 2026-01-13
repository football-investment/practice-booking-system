"""
Create 3 Simple Test Tournaments for Testing Coach Level Requirements

Creates 3 APPLICATION_BASED tournaments to test coach level visibility and application logic:
1. PRE Tournament - Level 1+ can apply
2. YOUTH Tournament - Level 3+ can apply
3. AMATEUR Tournament - Level 5+ can apply
"""

import requests
import sys
from datetime import datetime, timedelta

API_BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"

# Tournament specifications
TOURNAMENTS = [
    {
        "name": "PRE Tournament - Level 1",
        "assignment_type": "APPLICATION_BASED",
        "max_players": 12,
        "enrollment_cost": 200,
        "age_group": "PRE",
        "games": [
            {
                "game_type": "LEAGUE_MATCH",
                "date": "2026-02-15",
                "start_time": "10:00",
                "end_time": "11:00",
                "capacity": 12
            }
        ]
    },
    {
        "name": "YOUTH Tournament - Level 3",
        "assignment_type": "APPLICATION_BASED",
        "max_players": 16,
        "enrollment_cost": 300,
        "age_group": "YOUTH",
        "games": [
            {
                "game_type": "GROUP_STAGE",
                "date": "2026-02-20",
                "start_time": "14:00",
                "end_time": "16:00",
                "capacity": 16
            }
        ]
    },
    {
        "name": "AMATEUR Tournament - Level 5",
        "assignment_type": "APPLICATION_BASED",
        "max_players": 20,
        "enrollment_cost": 400,
        "age_group": "AMATEUR",
        "games": [
            {
                "game_type": "KING_OF_THE_COURT",
                "date": "2026-02-25",
                "start_time": "09:00",
                "end_time": "11:00",
                "capacity": 20
            }
        ]
    }
]


def get_admin_token():
    """Get admin authentication token."""
    print(f"\n🔑 Authenticating as admin...")
    response = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )

    if response.status_code != 200:
        print(f"❌ Admin login failed: {response.status_code} {response.text}")
        sys.exit(1)

    token = response.json()["access_token"]
    print(f"✅ Admin authenticated")
    return token


def verify_location_and_campus(token):
    """Verify Budapest location and get first available campus."""
    print(f"\n📍 Verifying location and campus...")

    # Get locations
    response = requests.get(
        f"{API_BASE_URL}/api/v1/admin/locations",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code != 200:
        print(f"❌ Failed to get locations: {response.status_code}")
        sys.exit(1)

    locations = response.json()
    budapest = next((loc for loc in locations if loc["city"] == "Budapest"), None)

    if not budapest:
        print(f"❌ Budapest location not found")
        sys.exit(1)

    print(f"✅ Budapest location found (ID: {budapest['id']})")

    # Get campuses for Budapest
    response = requests.get(
        f"{API_BASE_URL}/api/v1/admin/locations/{budapest['id']}/campuses",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code != 200:
        print(f"❌ Failed to get campuses: {response.status_code}")
        sys.exit(1)

    campuses = response.json()

    if not campuses:
        print(f"❌ No campuses found for Budapest")
        sys.exit(1)

    # Use first available campus
    campus = campuses[0]
    print(f"✅ Campus found: {campus['name']} (ID: {campus['id']})")

    return budapest["id"], campus["id"]


def create_tournament(token, tournament_spec, location_id, campus_id):
    """Create a tournament with games using tournament generator."""
    print(f"\n🏆 Creating tournament: {tournament_spec['name']}...")
    print(f"   Assignment Type: {tournament_spec['assignment_type']}")
    print(f"   Max Players: {tournament_spec['max_players']}")
    print(f"   Cost: {tournament_spec['enrollment_cost']} credits")
    print(f"   Age Group: {tournament_spec['age_group']}")
    print(f"   Games: {len(tournament_spec['games'])}")

    # Get tournament date from first game
    tournament_date = tournament_spec["games"][0]["date"]

    # Build sessions list for tournament generator
    sessions = []
    for game_spec in tournament_spec["games"]:
        start_time_obj = datetime.strptime(game_spec["start_time"], "%H:%M")
        end_time_obj = datetime.strptime(game_spec["end_time"], "%H:%M")
        duration = (end_time_obj - start_time_obj).total_seconds() / 60

        sessions.append({
            "time": game_spec["start_time"],
            "title": game_spec["game_type"].replace("_", " ").title(),
            "duration_minutes": int(duration),
            "capacity": game_spec["capacity"],
            "credit_cost": 0,  # Tournament uses enrollment cost, not per-session
            "description": f"{game_spec['game_type']} game",
            "game_type": game_spec["game_type"]
        })

    # Create tournament using tournament generator endpoint
    tournament_payload = {
        "date": tournament_date,
        "name": tournament_spec["name"],
        "specialization_type": "LFA_FOOTBALL_PLAYER",
        "age_group": tournament_spec["age_group"],
        "campus_id": campus_id,
        "location_id": location_id,
        "sessions": sessions,
        "assignment_type": tournament_spec["assignment_type"],
        "max_players": tournament_spec["max_players"],
        "enrollment_cost": tournament_spec["enrollment_cost"],
        "auto_book_students": False,
        "reward_policy_name": "default"
    }

    response = requests.post(
        f"{API_BASE_URL}/api/v1/tournaments/generate",
        headers={"Authorization": f"Bearer {token}"},
        json=tournament_payload
    )

    if response.status_code not in [200, 201]:
        print(f"❌ Failed to create tournament: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

    result = response.json()

    # Extract tournament from response
    if "tournament" in result:
        tournament = result["tournament"]
    elif "semester" in result:
        tournament = result["semester"]
    else:
        tournament = result

    tournament_id = tournament.get("id") or tournament.get("tournament_id") or result.get("tournament_id")

    if tournament_id:
        print(f"✅ Tournament created (ID: {tournament_id})")
    else:
        print(f"✅ Tournament created")
    print(f"   Games created: {len(sessions)}")

    return tournament


def main():
    print("=" * 80)
    print("CREATE 3 SIMPLE TEST TOURNAMENTS (PRE, YOUTH, AMATEUR)")
    print("=" * 80)

    # Get admin token
    admin_token = get_admin_token()

    # Verify location and campus
    location_id, campus_id = verify_location_and_campus(admin_token)

    created_tournaments = []

    # Create each tournament
    for tournament_spec in TOURNAMENTS:
        tournament = create_tournament(admin_token, tournament_spec, location_id, campus_id)
        if tournament:
            created_tournaments.append(tournament)

    # Summary
    print("\n" + "=" * 80)
    print("✅ TOURNAMENT CREATION COMPLETE")
    print("=" * 80)

    print(f"\n📋 Created {len(created_tournaments)} tournaments\n")

    print("🎯 Testing scenario:")
    print("   1. PRE Tournament - Level 1+ instructors can apply")
    print("   2. YOUTH Tournament - Level 3+ instructors can apply (Level 1 sees but cannot apply)")
    print("   3. AMATEUR Tournament - Level 5+ instructors can apply (Level 1 sees but cannot apply)")
    print("\n   Level 1 instructor should:")
    print("   ✅ See all 3 tournaments")
    print("   ✅ Be able to apply to PRE tournament only")
    print("   ⚠️  See 'Level 3+ Required' on YOUTH tournament")
    print("   ⚠️  See 'Level 5+ Required' on AMATEUR tournament")
    print()


if __name__ == "__main__":
    main()
