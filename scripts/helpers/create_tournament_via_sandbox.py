"""
Create Complete Tournament via Sandbox Endpoint
================================================

Uses the /sandbox/run-test endpoint to create a complete tournament
with all steps already completed.

Usage:
    python create_tournament_via_sandbox.py
"""

import requests
import json
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"

# Test data
PLAYER_IDS = [4, 5, 6, 7, 13, 14, 15, 16]  # 8 existing players

def get_admin_token():
    """Authenticate and get admin token"""
    print("\n🔑 Authenticating as admin...")
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    print(f"✅ Admin authenticated")
    return token

def create_tournament_via_sandbox(token):
    """Create complete tournament using sandbox endpoint"""
    print("\n" + "="*80)
    print("CREATING COMPLETE TOURNAMENT VIA SANDBOX")
    print("="*80)

    headers = {"Authorization": f"Bearer {token}"}

    tournament_config = {
        "tournament_type": "league",  # league, knockout, or hybrid
        "skills_to_test": ["ball_control", "passing", "dribbling", "finishing"],  # 1-20 skills
        "player_count": len(PLAYER_IDS),  # 4-16 players
        "test_config": {
            "use_synthetic_players": False,  # Use real players, not synthetic
            "real_player_ids": PLAYER_IDS,  # Actual player IDs to use
            "tournament_code": f"E2E-SANDBOX-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "tournament_name": f"E2E Sandbox Tournament - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "use_game_presets": True,
            "game_type": "technical",
            "difficulty_level": "advanced"
        }
    }

    print(f"\nCalling /sandbox/run-test with config:")
    print(json.dumps(tournament_config, indent=2))

    response = requests.post(
        f"{API_BASE_URL}/sandbox/run-test",
        headers=headers,
        json=tournament_config
    )

    print(f"\nResponse: HTTP {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        tournament_code = result.get("tournament_code")
        tournament_id = result.get("tournament_id")

        print(f"\n✅ Tournament created successfully!")
        print(f"   - Tournament Code: {tournament_code}")
        print(f"   - Tournament ID: {tournament_id}")
        print(f"   - Players enrolled: {len(PLAYER_IDS)}")

        # Print full response for debugging
        print(f"\nFull Response:")
        print(json.dumps(result, indent=2))

        return tournament_id
    else:
        print(f"❌ Tournament creation failed: {response.text}")
        return None

def main():
    """Run complete tournament creation via sandbox"""
    print("\n" + "="*80)
    print("COMPLETE TOURNAMENT CREATION VIA SANDBOX")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Authenticate
        token = get_admin_token()

        # Create tournament via sandbox
        tournament_id = create_tournament_via_sandbox(token)

        if tournament_id:
            print("\n" + "="*80)
            print("✅ TOURNAMENT CREATED SUCCESSFULLY!")
            print("="*80)
            print(f"Tournament ID: {tournament_id}")
            print(f"\nNext steps:")
            print(f"1. Navigate to Tournament History in frontend")
            print(f"2. Find tournament ID {tournament_id}")
            print(f"3. Click 'Resume Workflow' to continue")
            print(f"4. Complete remaining steps: session generation, results, finalization, reward distribution")
            print("="*80 + "\n")
        else:
            print("\n❌ FAILED: Could not create tournament via sandbox")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
