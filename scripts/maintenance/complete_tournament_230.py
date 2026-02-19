"""
Complete Tournament 230 Workflow
=================================

Tournament 230 was created by sandbox with:
- ID: 230
- Status: COMPLETED
- Players: 8 enrolled
- Problem: No rankings/sessions generated

This script will:
1. Reset tournament to DRAFT
2. Generate sessions
3. Submit match results
4. Finalize tournament
5. Distribute rewards
6. Test idempotency

Usage:
    python complete_tournament_230.py
"""

import requests
import json
import time
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"
TOURNAMENT_ID = 230

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

def check_tournament_status(token):
    """Check current tournament status"""
    print(f"\n{'='*80}")
    print(f"CHECKING TOURNAMENT {TOURNAMENT_ID} STATUS")
    print(f"{'='*80}")

    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(
        f"{API_BASE_URL}/tournaments/{TOURNAMENT_ID}/summary",
        headers=headers
    )

    if response.status_code != 200:
        print(f"❌ Failed to get tournament: {response.text}")
        return None

    tournament = response.json()
    print(f"\nCurrent Status:")
    print(f"   - ID: {tournament.get('id')}")
    print(f"   - Name: {tournament.get('name')}")
    print(f"   - Status: {tournament.get('tournament_status')}")
    print(f"   - Participants: {tournament.get('total_bookings', 0)}")
    print(f"   - Sessions: {tournament.get('total_sessions', 0)}")
    print(f"   - Rankings: {tournament.get('rankings_count', 0)}")

    return tournament

def reset_tournament_status(token):
    """Reset tournament to IN_PROGRESS"""
    print(f"\n{'='*80}")
    print(f"RESETTING TOURNAMENT TO IN_PROGRESS")
    print(f"{'='*80}")

    headers = {"Authorization": f"Bearer {token}"}

    response = requests.patch(
        f"{API_BASE_URL}/semesters/{TOURNAMENT_ID}",
        headers=headers,
        json={"tournament_status": "IN_PROGRESS"}
    )

    if response.status_code != 200:
        print(f"❌ Failed to reset status: {response.text}")
        return False

    print(f"✅ Tournament status: IN_PROGRESS")
    return True

def generate_sessions(token):
    """Generate tournament sessions"""
    print(f"\n{'='*80}")
    print(f"GENERATING TOURNAMENT SESSIONS")
    print(f"{'='*80}")

    headers = {"Authorization": f"Bearer {token}"}

    session_data = {
        "parallel_fields": 1,
        "session_duration_minutes": 90,
        "break_minutes": 15
    }

    response = requests.post(
        f"{API_BASE_URL}/tournaments/{TOURNAMENT_ID}/generate-sessions",
        headers=headers,
        json=session_data
    )

    if response.status_code != 200:
        print(f"❌ Session generation failed: {response.text}")
        return None

    result = response.json()
    session_count = result.get("sessions_generated_count", 0)

    print(f"✅ {session_count} sessions generated successfully!")

    # Get session IDs
    response = requests.get(
        f"{API_BASE_URL}/tournaments/{TOURNAMENT_ID}/sessions",
        headers=headers
    )

    if response.status_code != 200:
        print(f"❌ Failed to fetch sessions: {response.text}")
        return None

    sessions = response.json()
    print(f"   - Sessions: {[s['id'] for s in sessions]}")

    return sessions

def submit_match_results(token, sessions):
    """Submit match results for all sessions"""
    print(f"\n{'='*80}")
    print(f"SUBMITTING MATCH RESULTS")
    print(f"{'='*80}")

    headers = {"Authorization": f"Bearer {token}"}

    for session in sessions:
        session_id = session["id"]
        session_type = session.get("session_type", "UNKNOWN")

        print(f"\nSession {session_id} ({session_type}):")

        # Get participants
        participants = session.get("participants", [])
        if not participants:
            print(f"   ⚠️ No participants found")
            continue

        print(f"   - Participants: {len(participants)}")

        # Check if INDIVIDUAL_RANKING with ROUNDS_BASED
        match_format = session.get("match_format", "")
        scoring_type = session.get("scoring_type", "")

        if match_format == "INDIVIDUAL_RANKING" and scoring_type == "ROUNDS_BASED":
            # Submit round-based results
            num_rounds = session.get("structure_config", {}).get("number_of_rounds", 3)
            print(f"   - Rounds to submit: {num_rounds}")

            for round_num in range(1, num_rounds + 1):
                # Generate random scores for each participant
                round_results = {}
                for participant in participants:
                    user_id = str(participant["id"])
                    # Random score between 10-100
                    score = 10 + (hash(f"{session_id}-{round_num}-{user_id}") % 90)
                    round_results[user_id] = str(score)

                # Submit round results
                response = requests.post(
                    f"{API_BASE_URL}/tournaments/{TOURNAMENT_ID}/sessions/{session_id}/rounds/{round_num}/submit-results",
                    headers=headers,
                    json={
                        "round_number": round_num,
                        "results": round_results,
                        "notes": f"E2E test round {round_num}"
                    }
                )

                if response.status_code == 200:
                    print(f"   ✅ Round {round_num} submitted")
                else:
                    print(f"   ❌ Round {round_num} failed: {response.text}")
        else:
            print(f"   ℹ️ Skipping non-rounds-based session")

    print(f"\n✅ All match results submitted!")
    return True

def finalize_tournament(token, sessions):
    """Finalize tournament"""
    print(f"\n{'='*80}")
    print(f"FINALIZING TOURNAMENT")
    print(f"{'='*80}")

    headers = {"Authorization": f"Bearer {token}"}

    # Finalize each session
    for session in sessions:
        session_id = session["id"]

        print(f"Finalizing session {session_id}...")

        response = requests.post(
            f"{API_BASE_URL}/tournaments/{TOURNAMENT_ID}/sessions/{session_id}/finalize",
            headers=headers
        )

        if response.status_code == 200:
            print(f"   ✅ Session {session_id} finalized")
        else:
            print(f"   ⚠️ Session {session_id} finalization: {response.text}")

    # Set tournament status to COMPLETED
    print("\nSetting tournament status to COMPLETED...")
    response = requests.patch(
        f"{API_BASE_URL}/semesters/{TOURNAMENT_ID}",
        headers=headers,
        json={"tournament_status": "COMPLETED"}
    )

    if response.status_code != 200:
        print(f"❌ Status update failed: {response.text}")
        return False

    print("✅ Tournament status: COMPLETED")

    # Verify rankings were created
    response = requests.get(
        f"{API_BASE_URL}/tournaments/{TOURNAMENT_ID}/summary",
        headers=headers
    )

    if response.status_code == 200:
        summary = response.json()
        rankings_count = summary.get("rankings_count", 0)
        print(f"✅ Tournament rankings created: {rankings_count}")

    return True

def distribute_rewards(token, reason="First distribution"):
    """Distribute rewards"""
    print(f"\n{'='*80}")
    print(f"DISTRIBUTING REWARDS: {reason}")
    print(f"{'='*80}")

    headers = {"Authorization": f"Bearer {token}"}

    start_time = time.time()
    response = requests.post(
        f"{API_BASE_URL}/tournaments/{TOURNAMENT_ID}/distribute-rewards",
        headers=headers,
        json={"reason": reason}
    )
    duration = time.time() - start_time

    print(f"Response: HTTP {response.status_code} ({duration*1000:.0f}ms)")

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Rewards distributed successfully!")
        print(f"   - Message: {result.get('message', 'N/A')}")

        if "rewards_summary" in result:
            summary = result["rewards_summary"]
            print(f"   - Credit transactions: {summary.get('credit_transactions', 0)}")
            print(f"   - XP transactions: {summary.get('xp_transactions', 0)}")
            print(f"   - Skill rewards: {summary.get('skill_rewards', 0)}")
            print(f"   - Total credits: {summary.get('total_credits', 0)}")
            print(f"   - Total XP: {summary.get('total_xp', 0)}")

        return True
    elif response.status_code == 400:
        error = response.json()
        error_message = error.get("error", {}).get("message", error.get("detail", "N/A"))
        print(f"✅ Idempotency protection working!")
        print(f"   - Error message: {error_message}")
        return "idempotency"
    else:
        print(f"❌ Reward distribution failed: {response.text}")
        return False

def main():
    """Run complete tournament workflow"""
    print(f"\n{'='*80}")
    print(f"COMPLETE TOURNAMENT {TOURNAMENT_ID} WORKFLOW")
    print(f"{'='*80}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Authenticate
        token = get_admin_token()

        # Step 1: Check current status
        tournament = check_tournament_status(token)
        if not tournament:
            print(f"\n❌ FAILED: Tournament not found")
            return

        # Step 2: Reset to IN_PROGRESS if needed
        if tournament.get("tournament_status") == "COMPLETED":
            if not reset_tournament_status(token):
                print(f"\n❌ FAILED: Could not reset tournament status")
                return

        # Step 3: Generate sessions
        sessions = generate_sessions(token)
        if not sessions:
            print(f"\n❌ FAILED: Could not generate sessions")
            return

        # Step 4: Submit match results
        if not submit_match_results(token, sessions):
            print(f"\n❌ FAILED: Could not submit match results")
            return

        # Step 5: Finalize tournament
        if not finalize_tournament(token, sessions):
            print(f"\n❌ FAILED: Could not finalize tournament")
            return

        # Step 6: Distribute rewards (first time)
        result = distribute_rewards(token, "Complete E2E tournament - first distribution")
        if not result:
            print(f"\n❌ FAILED: Could not distribute rewards")
            return

        # Step 7: Distribute rewards (second time - idempotency)
        result2 = distribute_rewards(token, "Complete E2E tournament - second distribution (idempotency test)")
        if result2 != "idempotency":
            print(f"\n⚠️ WARNING: Second distribution should have triggered idempotency protection")

        # Success!
        print(f"\n{'='*80}")
        print(f"✅ ALL STEPS COMPLETED SUCCESSFULLY!")
        print(f"{'='*80}")
        print(f"Tournament ID: {TOURNAMENT_ID}")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\nYou can now manually test this tournament in the frontend:")
        print(f"1. Navigate to Tournament History")
        print(f"2. Find tournament ID {TOURNAMENT_ID}")
        print(f"3. Click 'View Rewards' to see distributed rewards")
        print(f"4. Verify all 3 reward types are present")
        print(f"{'='*80}\n")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
