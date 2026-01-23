"""
Create E2E test tournament directly via API.

Bypasses unreliable Streamlit dropdown selectors by creating tournament
through backend API endpoints.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import requests


def create_test_tournament():
    """Create OPEN_ASSIGNMENT tournament for E2E tests."""

    print("\n" + "=" * 70)
    print("🏆 E2E TEST TOURNAMENT CREATION")
    print("=" * 70)

    api_base_url = "http://localhost:8000"

    # Step 1: Login as admin
    print("\n1️⃣  Logging in as admin...")
    login_response = requests.post(
        f"{api_base_url}/api/v1/auth/login",
        json={
            "email": "admin@lfa.com",
            "password": "admin123"
        }
    )

    if login_response.status_code != 200:
        print(f"❌ Failed to login as admin: {login_response.status_code}")
        print(f"   Response: {login_response.text}")
        return False

    admin_token = login_response.json()["access_token"]
    print("   ✅ Admin authenticated")

    headers = {"Authorization": f"Bearer {admin_token}"}

    # Step 2: Get instructor ID (Grandmaster)
    # Grandmaster is always created with ID=3 in reset_database_for_tests.py
    print("\n2️⃣  Using Grandmaster instructor...")
    instructor_id = 3
    print(f"   ✅ Grandmaster ID: {instructor_id}")

    # Step 3: Create tournament
    print("\n3️⃣  Creating E2E Test Tournament...")

    tournament_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    tournament_data = {
        "name": "E2E Test Tournament - OPEN_ASSIGNMENT",
        "tournament_date": tournament_date,
        "specialization_type": "LFA_FOOTBALL_PLAYER",
        "age_group": "YOUTH",
        "assignment_type": "OPEN_ASSIGNMENT",
        "max_players": 5,
        "price_credits": 500,
        "instructor_id": instructor_id,
        "description": "Automated E2E test tournament for player enrollment flow"
    }

    create_response = requests.post(
        f"{api_base_url}/api/v1/admin/tournaments",
        headers=headers,
        json=tournament_data
    )

    if create_response.status_code in [200, 201]:
        tournament = create_response.json()
        print(f"   ✅ Tournament created successfully!")
        print(f"      ID: {tournament.get('id')}")
        print(f"      Name: {tournament.get('name')}")
        print(f"      Status: {tournament.get('status')}")
        print(f"      Assignment Type: {tournament.get('assignment_type')}")
        print(f"      Max Players: {tournament.get('max_players')}")
        print(f"      Price: {tournament.get('price_credits')} credits")
        print(f"      Instructor ID: {tournament.get('instructor_id')}")
    else:
        print(f"   ❌ Failed to create tournament: {create_response.status_code}")
        print(f"      Response: {create_response.text}")
        return False

    print("\n" + "=" * 70)
    print("✅ TOURNAMENT CREATION COMPLETE")
    print("=" * 70)
    print()

    return True


if __name__ == "__main__":
    success = create_test_tournament()
    sys.exit(0 if success else 1)
