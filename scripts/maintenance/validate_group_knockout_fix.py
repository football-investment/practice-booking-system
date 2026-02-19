"""
Validate Group+Knockout Finalization Fix

Tests the enrollment_snapshot setter bug fix without needing Playwright.
Creates a minimal 7-player tournament, completes group stage, and tests finalization.
"""

import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import random

# Database configuration
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
API_BASE_URL = "http://localhost:8000/api/v1"

# Test configuration
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"
TEST_PARTICIPANTS = [3, 4, 5, 14, 15, 16, 17]  # 7 players for edge case

def get_auth_token():
    """Authenticate and get JWT token"""
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    response.raise_for_status()
    return response.json()["access_token"]

def create_test_tournament(token):
    """Create a GROUP_KNOCKOUT tournament via sandbox API"""
    print("📝 Creating test tournament...")

    # Use sandbox endpoint to create tournament
    response = requests.post(
        f"{API_BASE_URL}/sandbox/test-tournament",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "tournament_name": "Group+Knockout Fix Validation",
            "age_group": "AMATEUR",
            "selected_user_ids": TEST_PARTICIPANTS,
            "scoring_mode": "HEAD_TO_HEAD",
            "tournament_format_code": "group_knockout",
            "enrollment_cost": 0,
        }
    )
    response.raise_for_status()
    result = response.json()
    tournament_id = result["tournament_id"]
    print(f"✅ Tournament created: ID {tournament_id}")
    return tournament_id

def get_group_sessions(tournament_id):
    """Get all group stage sessions"""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    query = text("""
        SELECT id, title, participant_user_ids, game_results
        FROM sessions
        WHERE semester_id = :tournament_id
            AND is_tournament_game = true
            AND tournament_phase = 'Group Stage'
        ORDER BY id
    """)

    result = db.execute(query, {"tournament_id": tournament_id})
    sessions = [dict(row._mapping) for row in result]
    db.close()
    return sessions

def submit_group_results(sessions, token):
    """Submit results for all group stage matches"""
    print(f"\n📊 Submitting results for {len(sessions)} group matches...")

    for i, session in enumerate(sessions, 1):
        if not session['participant_user_ids'] or len(session['participant_user_ids']) != 2:
            print(f"   ⚠️  Session {session['id']}: Invalid participants, skipping")
            continue

        p1, p2 = session['participant_user_ids']

        # Randomize scores (3-0 to 3-2 range)
        winner_score = 3
        loser_score = random.randint(0, 2)
        winner = random.choice([p1, p2])
        loser = p2 if winner == p1 else p1

        response = requests.patch(
            f"{API_BASE_URL}/sessions/{session['id']}/head-to-head-results",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "results": [
                    {"user_id": winner, "score": winner_score},
                    {"user_id": loser, "score": loser_score}
                ]
            }
        )

        if response.status_code == 200:
            print(f"   ✅ Match {i}/{len(sessions)}: {winner_score}-{loser_score} (Winner: User {winner})")
        else:
            print(f"   ❌ Match {i}: Failed ({response.status_code})")
            print(f"      Response: {response.text}")

    print(f"✅ All group stage results submitted")

def finalize_group_stage(tournament_id, token):
    """Call the finalize-group-stage endpoint"""
    print(f"\n🏁 Finalizing group stage for tournament {tournament_id}...")

    response = requests.post(
        f"{API_BASE_URL}/tournaments/{tournament_id}/finalize-group-stage",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Group stage finalized successfully!")
        print(f"   Qualified participants: {result.get('qualified_participants', [])}")
        print(f"   Knockout sessions updated: {result.get('knockout_sessions_updated', 0)}")
        print(f"   Snapshot saved: {result.get('snapshot_saved', False)}")
        return result
    else:
        print(f"❌ Finalization failed with status {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def verify_snapshot_saved(tournament_id):
    """Verify enrollment_snapshot was saved to database"""
    print(f"\n🔍 Verifying enrollment_snapshot in database...")

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    query = text("""
        SELECT enrollment_snapshot
        FROM tournament_configurations
        WHERE semester_id = :tournament_id
    """)

    result = db.execute(query, {"tournament_id": tournament_id})
    row = result.fetchone()
    db.close()

    if row and row[0]:
        snapshot = row[0]
        print(f"✅ Snapshot saved successfully!")
        print(f"   Phase: {snapshot.get('phase', 'N/A')}")
        print(f"   Total groups: {snapshot.get('total_groups', 0)}")
        print(f"   Total qualified: {snapshot.get('total_qualified', 0)}")
        return True
    else:
        print(f"❌ Snapshot NOT found in database!")
        return False

def get_knockout_sessions(tournament_id):
    """Get knockout sessions to verify they were populated"""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    query = text("""
        SELECT id, title, participant_user_ids, tournament_round
        FROM sessions
        WHERE semester_id = :tournament_id
            AND is_tournament_game = true
            AND tournament_phase = 'Knockout Stage'
        ORDER BY tournament_round, id
    """)

    result = db.execute(query, {"tournament_id": tournament_id})
    sessions = [dict(row._mapping) for row in result]
    db.close()
    return sessions

def main():
    print("=" * 70)
    print("GROUP+KNOCKOUT FINALIZATION FIX VALIDATION")
    print("=" * 70)

    try:
        # Authenticate
        print("\n🔐 Authenticating...")
        token = get_auth_token()
        print("✅ Authenticated successfully")

        # Create tournament
        tournament_id = create_test_tournament(token)

        # Get group sessions
        group_sessions = get_group_sessions(tournament_id)
        print(f"\n📋 Found {len(group_sessions)} group stage sessions")

        # Submit all group results
        submit_group_results(group_sessions, token)

        # Finalize group stage (THIS IS THE CRITICAL TEST)
        finalization_result = finalize_group_stage(tournament_id, token)

        if not finalization_result:
            print("\n" + "=" * 70)
            print("❌ VALIDATION FAILED: Finalization endpoint returned error")
            print("=" * 70)
            return False

        # Verify snapshot was saved
        snapshot_saved = verify_snapshot_saved(tournament_id)

        # Check knockout sessions were populated
        print(f"\n🥊 Checking knockout sessions...")
        knockout_sessions = get_knockout_sessions(tournament_id)
        print(f"   Found {len(knockout_sessions)} knockout sessions")

        populated_count = sum(1 for s in knockout_sessions if s['participant_user_ids'] and len(s['participant_user_ids']) == 2)
        print(f"   Populated: {populated_count}/{len(knockout_sessions)}")

        # Final verdict
        print("\n" + "=" * 70)
        if snapshot_saved and populated_count > 0:
            print("✅ VALIDATION PASSED: enrollment_snapshot bug is FIXED!")
            print("=" * 70)
            print(f"\nTournament ID: {tournament_id}")
            print(f"✅ Group stage finalized without errors")
            print(f"✅ Snapshot saved to database")
            print(f"✅ {populated_count} knockout sessions populated")
            return True
        else:
            print("❌ VALIDATION FAILED: Some checks did not pass")
            print("=" * 70)
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
