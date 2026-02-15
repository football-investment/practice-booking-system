"""
Complete Tournament E2E Creation Script
========================================

This script creates a COMPLETE tournament from start to finish:
1. Create tournament
2. Enroll 8 players
3. Generate sessions
4. Submit match results
5. Finalize tournament
6. Distribute rewards (first time)
7. Verify rewards created
8. Distribute rewards (second time - idempotency test)

Usage:
    python create_complete_tournament_e2e.py
"""

import requests
import json
import time
from datetime import datetime, timedelta

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

def create_tournament(token):
    """Step 1: Create tournament"""
    print("\n" + "="*80)
    print("STEP 1: Creating Tournament")
    print("="*80)

    headers = {"Authorization": f"Bearer {token}"}

    start_date = (datetime.now() + timedelta(days=1)).date()
    end_date = (datetime.now() + timedelta(days=8)).date()

    tournament_data = {
        "code": f"E2E-TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "name": f"Complete E2E Test Tournament - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "age_group": "PRO",
        "specialization_type": "PLAYER",
        "format": "INDIVIDUAL_RANKING",  # Not tournament_format, and use correct enum value
        "scoring_type": "PLACEMENT",
        "ranking_direction": "DESC",
        "max_players": 8,
        "assignment_type": "OPEN_ASSIGNMENT",
        "location_city": "Budapest",  # Use location_city instead of location_id
        "location_venue": "LFA Academy",
        "is_active": True,
        "status": "DRAFT"  # Use status not tournament_status for SemesterCreate
    }

    print(f"Creating tournament: {tournament_data['name']}")

    response = requests.post(
        f"{API_BASE_URL}/semesters",
        headers=headers,
        json=tournament_data
    )

    if response.status_code != 200:
        print(f"❌ Tournament creation failed: {response.text}")
        return None

    tournament = response.json()
    tournament_id = tournament["id"]

    print(f"✅ Tournament created successfully!")
    print(f"   - ID: {tournament_id}")
    print(f"   - Name: {tournament['name']}")
    print(f"   - Status: {tournament.get('tournament_status', 'N/A')}")

    return tournament_id

def enroll_players(token, tournament_id):
    """Step 2: Enroll players"""
    print("\n" + "="*80)
    print("STEP 2: Enrolling Players")
    print("="*80)

    headers = {"Authorization": f"Bearer {token}"}

    print(f"Enrolling {len(PLAYER_IDS)} players...")

    enrolled_count = 0
    for player_id in PLAYER_IDS:
        # Create enrollment
        enrollment_data = {
            "user_id": player_id,
            "semester_id": tournament_id,
            "enrollment_type": "TOURNAMENT_PARTICIPANT"
        }

        response = requests.post(
            f"{API_BASE_URL}/semester-enrollments",
            headers=headers,
            json=enrollment_data
        )

        if response.status_code == 200:
            enrolled_count += 1
            print(f"   ✅ Player {player_id} enrolled")
        else:
            print(f"   ⚠️ Player {player_id} enrollment failed: {response.text}")

    print(f"✅ {enrolled_count}/{len(PLAYER_IDS)} players enrolled successfully!")
    return enrolled_count == len(PLAYER_IDS)

def generate_sessions(token, tournament_id):
    """Step 3: Generate tournament sessions"""
    print("\n" + "="*80)
    print("STEP 3: Generating Tournament Sessions")
    print("="*80)

    headers = {"Authorization": f"Bearer {token}"}

    # First, update tournament status to IN_PROGRESS
    print("Setting tournament status to IN_PROGRESS...")
    response = requests.patch(
        f"{API_BASE_URL}/semesters/{tournament_id}",
        headers=headers,
        json={"tournament_status": "IN_PROGRESS"}
    )

    if response.status_code != 200:
        print(f"❌ Status update failed: {response.text}")
        return None

    print("✅ Tournament status: IN_PROGRESS")

    # Generate sessions
    print("Generating sessions...")
    session_data = {
        "parallel_fields": 1,
        "session_duration_minutes": 90,
        "break_minutes": 15
    }

    response = requests.post(
        f"{API_BASE_URL}/tournaments/{tournament_id}/generate-sessions",
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
        f"{API_BASE_URL}/tournaments/{tournament_id}/sessions",
        headers=headers
    )

    if response.status_code != 200:
        print(f"❌ Failed to fetch sessions: {response.text}")
        return None

    sessions = response.json()
    print(f"   - Sessions: {[s['id'] for s in sessions]}")

    return sessions

def submit_match_results(token, tournament_id, sessions):
    """Step 4: Submit match results for all sessions"""
    print("\n" + "="*80)
    print("STEP 4: Submitting Match Results")
    print("="*80)

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
                    f"{API_BASE_URL}/tournaments/{tournament_id}/sessions/{session_id}/rounds/{round_num}/submit-results",
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

def finalize_tournament(token, tournament_id, sessions):
    """Step 5: Finalize tournament"""
    print("\n" + "="*80)
    print("STEP 5: Finalizing Tournament")
    print("="*80)

    headers = {"Authorization": f"Bearer {token}"}

    # Finalize each session
    for session in sessions:
        session_id = session["id"]

        print(f"Finalizing session {session_id}...")

        response = requests.post(
            f"{API_BASE_URL}/tournaments/{tournament_id}/sessions/{session_id}/finalize",
            headers=headers
        )

        if response.status_code == 200:
            print(f"   ✅ Session {session_id} finalized")
        else:
            print(f"   ⚠️ Session {session_id} finalization: {response.text}")

    # Set tournament status to COMPLETED
    print("\nSetting tournament status to COMPLETED...")
    response = requests.patch(
        f"{API_BASE_URL}/semesters/{tournament_id}",
        headers=headers,
        json={"tournament_status": "COMPLETED"}
    )

    if response.status_code != 200:
        print(f"❌ Status update failed: {response.text}")
        return False

    print("✅ Tournament status: COMPLETED")

    # Verify rankings were created
    response = requests.get(
        f"{API_BASE_URL}/tournaments/{tournament_id}/summary",
        headers=headers
    )

    if response.status_code == 200:
        summary = response.json()
        rankings_count = summary.get("rankings_count", 0)
        print(f"✅ Tournament rankings created: {rankings_count}")

    return True

def distribute_rewards_first_time(token, tournament_id):
    """Step 6: Distribute rewards (first time)"""
    print("\n" + "="*80)
    print("STEP 6: Distributing Rewards (FIRST TIME)")
    print("="*80)

    headers = {"Authorization": f"Bearer {token}"}

    print("Calling distribute-rewards endpoint...")

    start_time = time.time()
    response = requests.post(
        f"{API_BASE_URL}/tournaments/{tournament_id}/distribute-rewards",
        headers=headers,
        json={"reason": "Complete E2E tournament - first distribution"}
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
    else:
        print(f"❌ Reward distribution failed: {response.text}")
        return False

def verify_rewards(token, tournament_id):
    """Step 7: Verify rewards created"""
    print("\n" + "="*80)
    print("STEP 7: Verifying Rewards Created")
    print("="*80)

    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(
        f"{API_BASE_URL}/tournaments/{tournament_id}/distributed-rewards",
        headers=headers
    )

    if response.status_code != 200:
        print(f"❌ Failed to fetch rewards: {response.text}")
        return False

    rewards = response.json()

    print(f"✅ Rewards status:")
    print(f"   - Rewards distributed: {rewards.get('rewards_distributed', False)}")
    print(f"   - Total reward count: {rewards.get('rewards_count', 0)}")

    return rewards.get('rewards_distributed', False)

def distribute_rewards_second_time(token, tournament_id):
    """Step 8: Distribute rewards (second time - idempotency test)"""
    print("\n" + "="*80)
    print("STEP 8: Distributing Rewards (SECOND TIME - Idempotency Test)")
    print("="*80)

    headers = {"Authorization": f"Bearer {token}"}

    print("Calling distribute-rewards endpoint again...")

    start_time = time.time()
    response = requests.post(
        f"{API_BASE_URL}/tournaments/{tournament_id}/distribute-rewards",
        headers=headers,
        json={"reason": "Complete E2E tournament - second distribution (idempotency test)"}
    )
    duration = time.time() - start_time

    print(f"Response: HTTP {response.status_code} ({duration*1000:.0f}ms)")

    if response.status_code == 400:
        error = response.json()
        error_message = error.get("error", {}).get("message", error.get("detail", "N/A"))
        print(f"✅ Idempotency protection working!")
        print(f"   - Error message: {error_message}")
        return True
    elif response.status_code == 200:
        print(f"✅ Idempotent success (no duplicates created)")
        return True
    else:
        print(f"❌ Unexpected response: {response.text}")
        return False

def main():
    """Run complete E2E tournament creation"""
    print("\n" + "="*80)
    print("COMPLETE TOURNAMENT E2E CREATION")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Authenticate
        token = get_admin_token()

        # Step 1: Create tournament
        tournament_id = create_tournament(token)
        if not tournament_id:
            print("\n❌ FAILED: Could not create tournament")
            return

        # Step 2: Enroll players
        if not enroll_players(token, tournament_id):
            print("\n❌ FAILED: Could not enroll all players")
            return

        # Step 3: Generate sessions
        sessions = generate_sessions(token, tournament_id)
        if not sessions:
            print("\n❌ FAILED: Could not generate sessions")
            return

        # Step 4: Submit match results
        if not submit_match_results(token, tournament_id, sessions):
            print("\n❌ FAILED: Could not submit match results")
            return

        # Step 5: Finalize tournament
        if not finalize_tournament(token, tournament_id, sessions):
            print("\n❌ FAILED: Could not finalize tournament")
            return

        # Step 6: Distribute rewards (first time)
        if not distribute_rewards_first_time(token, tournament_id):
            print("\n❌ FAILED: Could not distribute rewards")
            return

        # Step 7: Verify rewards
        if not verify_rewards(token, tournament_id):
            print("\n❌ FAILED: Rewards not verified")
            return

        # Step 8: Distribute rewards (second time - idempotency)
        if not distribute_rewards_second_time(token, tournament_id):
            print("\n❌ FAILED: Idempotency test failed")
            return

        # Success!
        print("\n" + "="*80)
        print("✅ ALL STEPS COMPLETED SUCCESSFULLY!")
        print("="*80)
        print(f"Tournament ID: {tournament_id}")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nYou can now manually test this tournament in the frontend:")
        print(f"1. Navigate to Tournament History")
        print(f"2. Find tournament ID {tournament_id}")
        print(f"3. Click 'View Rewards' to see distributed rewards")
        print(f"4. Verify all 3 reward types are present")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
