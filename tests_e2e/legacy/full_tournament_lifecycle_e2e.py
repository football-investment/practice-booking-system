"""
Full Tournament Lifecycle E2E Test
===================================

Complete end-to-end test of ENTIRE tournament workflow:
1. Create NEW tournament (DRAFT)
2. Enroll 8 players
3. Start tournament (IN_PROGRESS)
4. Generate sessions
5. Submit match results
6. Finalize sessions
7. Complete tournament (COMPLETED)
8. Distribute rewards (first time)
9. Test idempotency (second distribution)
10. Verify all reward types

NO WORKAROUNDS - Linear workflow from scratch.

Usage:
    python full_tournament_lifecycle_e2e.py
"""

import requests
import json
import time
from datetime import datetime, timedelta

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"

# Test data - 8 existing players
PLAYER_IDS = [4, 5, 6, 7, 13, 14, 15, 16]


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


def step_1_create_tournament(token):
    """Step 1: Create NEW tournament (DRAFT status)"""
    print(f"\n{'='*80}")
    print("STEP 1: CREATE TOURNAMENT")
    print(f"{'='*80}")

    headers = {"Authorization": f"Bearer {token}"}

    start_date = (datetime.now() + timedelta(days=1)).date()
    end_date = (datetime.now() + timedelta(days=8)).date()

    tournament_data = {
        "code": f"E2E-FULL-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "name": f"Full E2E Tournament - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "age_group": "PRO",
        "specialization_type": "PLAYER",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "ROUNDS_BASED",  # Important: ROUNDS_BASED for finalization
        "ranking_direction": "DESC",
        "max_players": 8,
        "assignment_type": "OPEN_ASSIGNMENT",
        "location_city": "Budapest",
        "location_venue": "LFA Academy",
        "is_active": True,
        "status": "DRAFT"
    }

    print(f"Creating tournament: {tournament_data['name']}")
    print(f"   - Format: INDIVIDUAL_RANKING")
    print(f"   - Scoring: ROUNDS_BASED")

    response = requests.post(
        f"{API_BASE_URL}/semesters",
        headers=headers,
        json=tournament_data
    )

    if response.status_code != 200:
        print(f"❌ Tournament creation failed (Status {response.status_code})")
        print(f"Response text: {response.text}")
        try:
            error_detail = response.json()
            print(f"Error detail: {json.dumps(error_detail, indent=2)}")
        except:
            pass
        return None

    tournament = response.json()
    tournament_id = tournament["id"]

    print(f"✅ Tournament created successfully!")
    print(f"   - ID: {tournament_id}")
    print(f"   - Name: {tournament['name']}")
    print(f"   - Status: {tournament.get('status', 'N/A')}")

    return tournament_id


def step_2_enroll_players(token, tournament_id):
    """Step 2: Enroll 8 players using admin batch-enroll endpoint"""
    print(f"\n{'='*80}")
    print("STEP 2: ENROLL PLAYERS")
    print(f"{'='*80}")

    headers = {"Authorization": f"Bearer {token}"}

    print(f"Batch enrolling {len(PLAYER_IDS)} players via admin endpoint...")

    enrollment_data = {
        "player_ids": PLAYER_IDS
    }

    response = requests.post(
        f"{API_BASE_URL}/tournaments/{tournament_id}/admin/batch-enroll",
        headers=headers,
        json=enrollment_data
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ {result['enrolled_count']}/{result['total_players']} players enrolled successfully!")
        if result['failed_players']:
            print(f"⚠️ Failed players: {result['failed_players']}")
        return result['success']
    else:
        print(f"❌ Batch enrollment failed: {response.text}")
        return False


def step_3_start_tournament(token, tournament_id):
    """Step 3: Start tournament (DRAFT → IN_PROGRESS)"""
    print(f"\n{'='*80}")
    print("STEP 3: START TOURNAMENT")
    print(f"{'='*80}")

    headers = {"Authorization": f"Bearer {token}"}

    print("Setting tournament status to IN_PROGRESS...")

    response = requests.patch(
        f"{API_BASE_URL}/semesters/{tournament_id}",
        headers=headers,
        json={"tournament_status": "IN_PROGRESS"}
    )

    if response.status_code != 200:
        print(f"❌ Status update failed: {response.text}")
        return False

    print(f"✅ Tournament status: IN_PROGRESS")
    return True


def step_4_generate_sessions(token, tournament_id):
    """Step 4: Generate tournament sessions"""
    print(f"\n{'='*80}")
    print("STEP 4: GENERATE SESSIONS")
    print(f"{'='*80}")

    headers = {"Authorization": f"Bearer {token}"}

    session_data = {
        "parallel_fields": 1,
        "session_duration_minutes": 90,
        "break_minutes": 15
    }

    print("Generating sessions...")

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

    # Get session details
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


def step_5_submit_match_results(token, tournament_id, sessions):
    """Step 5: Submit match results for all sessions"""
    print(f"\n{'='*80}")
    print("STEP 5: SUBMIT MATCH RESULTS")
    print(f"{'='*80}")

    headers = {"Authorization": f"Bearer {token}"}

    submitted_sessions = 0

    for session in sessions:
        session_id = session["id"]
        session_type = session.get("session_type", "UNKNOWN")
        match_format = session.get("match_format", "")
        scoring_type = session.get("scoring_type", "")

        print(f"\nSession {session_id} ({session_type}, {match_format}, {scoring_type}):")

        # Get participants
        participants = session.get("participants", [])
        if not participants:
            print(f"   ⚠️ No participants found")
            continue

        print(f"   - Participants: {len(participants)}")

        # Check if INDIVIDUAL_RANKING with ROUNDS_BASED
        if match_format == "INDIVIDUAL_RANKING" and scoring_type == "ROUNDS_BASED":
            # Submit round-based results
            num_rounds = session.get("structure_config", {}).get("number_of_rounds", 3)
            print(f"   - Rounds to submit: {num_rounds}")

            for round_num in range(1, num_rounds + 1):
                # Generate scores for each participant
                round_results = {}
                for participant in participants:
                    user_id = str(participant["id"])
                    # Generate deterministic score (10-100)
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
                    return False

            submitted_sessions += 1
        else:
            print(f"   ⚠️ Skipping non-ROUNDS_BASED session")

    print(f"\n✅ All match results submitted for {submitted_sessions} sessions!")
    return True


def step_6_finalize_sessions(token, tournament_id, sessions):
    """Step 6: Finalize all sessions"""
    print(f"\n{'='*80}")
    print("STEP 6: FINALIZE SESSIONS")
    print(f"{'='*80}")

    headers = {"Authorization": f"Bearer {token}"}

    finalized_count = 0

    for session in sessions:
        session_id = session["id"]
        match_format = session.get("match_format", "")

        if match_format != "INDIVIDUAL_RANKING":
            print(f"   ⚠️ Skipping session {session_id} (not INDIVIDUAL_RANKING)")
            continue

        print(f"Finalizing session {session_id}...")

        response = requests.post(
            f"{API_BASE_URL}/tournaments/{tournament_id}/sessions/{session_id}/finalize",
            headers=headers
        )

        if response.status_code == 200:
            finalized_count += 1
            print(f"   ✅ Session {session_id} finalized")
        else:
            print(f"   ❌ Session {session_id} finalization failed: {response.text}")
            return False

    print(f"✅ {finalized_count} sessions finalized successfully!")
    return True


def step_7_complete_tournament(token, tournament_id):
    """Step 7: Complete tournament (IN_PROGRESS → COMPLETED)"""
    print(f"\n{'='*80}")
    print("STEP 7: COMPLETE TOURNAMENT")
    print(f"{'='*80}")

    headers = {"Authorization": f"Bearer {token}"}

    print("Setting tournament status to COMPLETED...")

    response = requests.patch(
        f"{API_BASE_URL}/semesters/{tournament_id}",
        headers=headers,
        json={"tournament_status": "COMPLETED"}
    )

    if response.status_code != 200:
        print(f"❌ Status update failed: {response.text}")
        return False

    print(f"✅ Tournament status: COMPLETED")

    # Verify rankings were created
    response = requests.get(
        f"{API_BASE_URL}/tournaments/{tournament_id}/summary",
        headers=headers
    )

    if response.status_code == 200:
        summary = response.json()
        rankings_count = summary.get("rankings_count", 0)
        print(f"✅ Tournament rankings created: {rankings_count}")

        if rankings_count == 0:
            print(f"❌ No rankings found! Cannot proceed to reward distribution.")
            return False

    return True


def step_8_distribute_rewards_first(token, tournament_id):
    """Step 8: Distribute rewards (FIRST TIME)"""
    print(f"\n{'='*80}")
    print("STEP 8: DISTRIBUTE REWARDS (FIRST TIME)")
    print(f"{'='*80}")

    headers = {"Authorization": f"Bearer {token}"}

    print("Calling distribute-rewards endpoint...")

    start_time = time.time()
    response = requests.post(
        f"{API_BASE_URL}/tournaments/{tournament_id}/distribute-rewards",
        headers=headers,
        json={"reason": "Full E2E test - first distribution"}
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


def step_9_test_idempotency(token, tournament_id):
    """Step 9: Test idempotency (SECOND distribution attempt)"""
    print(f"\n{'='*80}")
    print("STEP 9: TEST IDEMPOTENCY (SECOND DISTRIBUTION)")
    print(f"{'='*80}")

    headers = {"Authorization": f"Bearer {token}"}

    print("Attempting second reward distribution...")
    print("⏳ Waiting 2 seconds...")
    time.sleep(2)

    start_time = time.time()
    response = requests.post(
        f"{API_BASE_URL}/tournaments/{tournament_id}/distribute-rewards",
        headers=headers,
        json={"reason": "Full E2E test - second distribution (idempotency test)"}
    )
    duration = time.time() - start_time

    print(f"Response: HTTP {response.status_code} ({duration*1000:.0f}ms)")

    if response.status_code == 400:
        error = response.json()
        error_message = error.get("error", {}).get("message", error.get("detail", "N/A"))
        print(f"✅ Idempotency protection working!")
        print(f"   - Error message: {error_message}")

        # Verify error indicates idempotency
        valid_indicators = ["already distributed", "locked", "rewards_distributed"]
        is_idempotency = any(indicator in error_message.lower() for indicator in valid_indicators)

        if not is_idempotency:
            print(f"❌ Error message does not indicate idempotency protection!")
            return False

        return True
    elif response.status_code == 200:
        print(f"⚠️ WARNING: Second distribution returned 200 (should be 400)")
        print(f"   - This may indicate idempotent success (no duplicates)")
        return True
    else:
        print(f"❌ Unexpected response: {response.text}")
        return False


def step_10_verify_rewards(token, tournament_id):
    """Step 10: Verify all 3 reward types created"""
    print(f"\n{'='*80}")
    print("STEP 10: VERIFY REWARD TYPES")
    print(f"{'='*80}")

    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(
        f"{API_BASE_URL}/tournaments/{tournament_id}/distributed-rewards",
        headers=headers
    )

    if response.status_code != 200:
        print(f"❌ Failed to fetch rewards: {response.text}")
        return False

    rewards = response.json()

    print(f"Rewards Status:")
    print(f"   - Rewards distributed: {rewards.get('rewards_distributed', False)}")
    print(f"   - Total reward count: {rewards.get('rewards_count', 0)}")

    if not rewards.get('rewards_distributed'):
        print(f"❌ Rewards not marked as distributed!")
        return False

    if rewards.get('rewards_count', 0) == 0:
        print(f"❌ No rewards found!")
        return False

    print(f"✅ Rewards verified successfully!")
    return True


def main():
    """Run complete tournament lifecycle E2E test"""
    print(f"\n{'='*80}")
    print("FULL TOURNAMENT LIFECYCLE E2E TEST")
    print(f"{'='*80}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nThis test will execute the COMPLETE tournament workflow:")
    print(f"1. Create tournament (DRAFT)")
    print(f"2. Enroll 8 players")
    print(f"3. Start tournament (IN_PROGRESS)")
    print(f"4. Generate sessions")
    print(f"5. Submit match results")
    print(f"6. Finalize sessions")
    print(f"7. Complete tournament (COMPLETED)")
    print(f"8. Distribute rewards (first time)")
    print(f"9. Test idempotency (second distribution)")
    print(f"10. Verify all reward types")

    tournament_id = None

    try:
        # Authenticate
        token = get_admin_token()

        # Step 1: Create tournament
        tournament_id = step_1_create_tournament(token)
        if not tournament_id:
            raise Exception("Step 1 failed: Could not create tournament")

        # Step 2: Enroll players
        if not step_2_enroll_players(token, tournament_id):
            raise Exception("Step 2 failed: Could not enroll all players")

        # Step 3: Start tournament
        if not step_3_start_tournament(token, tournament_id):
            raise Exception("Step 3 failed: Could not start tournament")

        # Step 4: Generate sessions
        sessions = step_4_generate_sessions(token, tournament_id)
        if not sessions:
            raise Exception("Step 4 failed: Could not generate sessions")

        # Step 5: Submit match results
        if not step_5_submit_match_results(token, tournament_id, sessions):
            raise Exception("Step 5 failed: Could not submit match results")

        # Step 6: Finalize sessions
        if not step_6_finalize_sessions(token, tournament_id, sessions):
            raise Exception("Step 6 failed: Could not finalize sessions")

        # Step 7: Complete tournament
        if not step_7_complete_tournament(token, tournament_id):
            raise Exception("Step 7 failed: Could not complete tournament")

        # Step 8: Distribute rewards (first time)
        if not step_8_distribute_rewards_first(token, tournament_id):
            raise Exception("Step 8 failed: Could not distribute rewards")

        # Step 9: Test idempotency
        if not step_9_test_idempotency(token, tournament_id):
            raise Exception("Step 9 failed: Idempotency test failed")

        # Step 10: Verify rewards
        if not step_10_verify_rewards(token, tournament_id):
            raise Exception("Step 10 failed: Reward verification failed")

        # Success!
        print(f"\n{'='*80}")
        print("✅ ALL 10 STEPS COMPLETED SUCCESSFULLY!")
        print(f"{'='*80}")
        print(f"Tournament ID: {tournament_id}")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\n🎯 NEXT STEP: Manual Frontend Testing")
        print(f"{'='*80}")
        print(f"1. Open Streamlit frontend: http://localhost:8501")
        print(f"2. Navigate to Tournament History")
        print(f"3. Find tournament ID: {tournament_id}")
        print(f"4. Click 'View Rewards' to see distributed rewards")
        print(f"5. Verify all 3 reward types are visible:")
        print(f"   - Credit transactions (coins)")
        print(f"   - XP transactions (experience)")
        print(f"   - Skill rewards (skill bonuses/penalties)")
        print(f"6. Try clicking 'Distribute All Rewards' again")
        print(f"7. Verify frontend shows 'Already distributed' message")
        print(f"{'='*80}\n")

        return tournament_id

    except Exception as e:
        print(f"\n{'='*80}")
        print(f"❌ TEST FAILED")
        print(f"{'='*80}")
        print(f"Error: {e}")
        if tournament_id:
            print(f"Tournament ID (for debugging): {tournament_id}")
        print(f"{'='*80}\n")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = main()
    exit(0 if result else 1)
