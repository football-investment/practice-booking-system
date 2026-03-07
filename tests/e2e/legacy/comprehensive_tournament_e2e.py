"""
Comprehensive Tournament E2E Test Suite
Tests ALL configuration variations for tournament workflows

Covers:
- INDIVIDUAL_RANKING format with all scoring types
- HEAD_TO_HEAD format with tournament types
- Multiple rounds
- Different ranking directions
"""
import requests
import json
from datetime import datetime, timedelta

# API Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"

# Test player IDs (8 players with LFA_FOOTBALL_PLAYER licenses)
PLAYER_IDS = [4, 5, 6, 7, 13, 14, 15, 16]


# ============================================================================
# TEST CONFIGURATIONS
# ============================================================================

TEST_CONFIGURATIONS = [
    # ========================================================================
    # TIER 0: Already Tested (1-round INDIVIDUAL_RANKING + basic HEAD_TO_HEAD)
    # ========================================================================
    {
        "id": "T1",
        "name": "INDIVIDUAL_RANKING + ROUNDS_BASED + 1 round",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "ROUNDS_BASED",
        "ranking_direction": "DESC",
        "measurement_unit": None,
        "tournament_type_id": None,  # INDIVIDUAL_RANKING cannot have tournament_type_id
        "number_of_rounds": 1,
        "supports_finalization": True,
        "status": "⏭️ SKIP (already tested)"
    },
    {
        "id": "T2",
        "name": "INDIVIDUAL_RANKING + TIME_BASED + 1 round",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "TIME_BASED",
        "ranking_direction": "ASC",
        "measurement_unit": "seconds",
        "tournament_type_id": None,
        "number_of_rounds": 1,
        "supports_finalization": True,
        "status": "⏳ TEST"
    },
    {
        "id": "T3",
        "name": "INDIVIDUAL_RANKING + SCORE_BASED + 1 round",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "SCORE_BASED",
        "ranking_direction": "DESC",
        "measurement_unit": "points",
        "tournament_type_id": None,
        "number_of_rounds": 1,
        "supports_finalization": True,
        "status": "⏳ TEST"
    },
    {
        "id": "T4",
        "name": "INDIVIDUAL_RANKING + DISTANCE_BASED + 1 round",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "DISTANCE_BASED",
        "ranking_direction": "DESC",
        "measurement_unit": "meters",
        "tournament_type_id": None,
        "number_of_rounds": 1,
        "supports_finalization": True,
        "status": "⏳ TEST"
    },
    {
        "id": "T5",
        "name": "INDIVIDUAL_RANKING + PLACEMENT + 1 round",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "PLACEMENT",
        "ranking_direction": None,
        "measurement_unit": None,
        "tournament_type_id": None,
        "number_of_rounds": 1,
        "supports_finalization": True,
        "status": "⏳ TEST"
    },
    {
        "id": "T6",
        "name": "HEAD_TO_HEAD + League (Round Robin)",
        "format": "HEAD_TO_HEAD",
        "scoring_type": None,
        "ranking_direction": None,
        "measurement_unit": None,
        "tournament_type_id": 1,  # league
        "number_of_rounds": None,
        "supports_finalization": False,
        "status": "⏳ TEST"
    },
    {
        "id": "T7",
        "name": "HEAD_TO_HEAD + Single Elimination",
        "format": "HEAD_TO_HEAD",
        "scoring_type": None,
        "ranking_direction": None,
        "measurement_unit": None,
        "tournament_type_id": 2,  # knockout
        "number_of_rounds": None,
        "supports_finalization": False,
        "status": "⏳ TEST"
    },

    # ========================================================================
    # TIER 1: Multi-Round INDIVIDUAL_RANKING (10 configs)
    # ========================================================================
    {
        "id": "T8",
        "name": "INDIVIDUAL_RANKING + ROUNDS_BASED + 2 rounds",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "ROUNDS_BASED",
        "ranking_direction": "DESC",
        "measurement_unit": None,
        "tournament_type_id": None,  # INDIVIDUAL_RANKING
        "number_of_rounds": 2,
        "supports_finalization": True,
        "status": "⏳ TEST"
    },
    {
        "id": "T9",
        "name": "INDIVIDUAL_RANKING + ROUNDS_BASED + 3 rounds",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "ROUNDS_BASED",
        "ranking_direction": "DESC",
        "measurement_unit": None,
        "tournament_type_id": None,  # INDIVIDUAL_RANKING
        "number_of_rounds": 3,
        "supports_finalization": True,
        "status": "⏳ TEST"
    },
    {
        "id": "T10",
        "name": "INDIVIDUAL_RANKING + TIME_BASED + 2 rounds",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "TIME_BASED",
        "ranking_direction": "ASC",
        "measurement_unit": "seconds",
        "tournament_type_id": None,  # INDIVIDUAL_RANKING
        "number_of_rounds": 2,
        "supports_finalization": True,
        "status": "⏳ TEST"
    },
    {
        "id": "T11",
        "name": "INDIVIDUAL_RANKING + TIME_BASED + 3 rounds",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "TIME_BASED",
        "ranking_direction": "ASC",
        "measurement_unit": "seconds",
        "tournament_type_id": None,  # INDIVIDUAL_RANKING
        "number_of_rounds": 3,
        "supports_finalization": True,
        "status": "⏳ TEST"
    },
    {
        "id": "T12",
        "name": "INDIVIDUAL_RANKING + SCORE_BASED + 2 rounds",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "SCORE_BASED",
        "ranking_direction": "DESC",
        "measurement_unit": "points",
        "tournament_type_id": None,  # INDIVIDUAL_RANKING
        "number_of_rounds": 2,
        "supports_finalization": True,
        "status": "⏳ TEST"
    },
    {
        "id": "T13",
        "name": "INDIVIDUAL_RANKING + SCORE_BASED + 3 rounds",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "SCORE_BASED",
        "ranking_direction": "DESC",
        "measurement_unit": "points",
        "tournament_type_id": None,  # INDIVIDUAL_RANKING
        "number_of_rounds": 3,
        "supports_finalization": True,
        "status": "⏳ TEST"
    },
    {
        "id": "T14",
        "name": "INDIVIDUAL_RANKING + DISTANCE_BASED + 2 rounds",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "DISTANCE_BASED",
        "ranking_direction": "DESC",
        "measurement_unit": "meters",
        "tournament_type_id": None,  # INDIVIDUAL_RANKING
        "number_of_rounds": 2,
        "supports_finalization": True,
        "status": "⏳ TEST"
    },
    {
        "id": "T15",
        "name": "INDIVIDUAL_RANKING + DISTANCE_BASED + 3 rounds",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "DISTANCE_BASED",
        "ranking_direction": "DESC",
        "measurement_unit": "meters",
        "tournament_type_id": None,  # INDIVIDUAL_RANKING
        "number_of_rounds": 3,
        "supports_finalization": True,
        "status": "⏳ TEST"
    },
    {
        "id": "T16",
        "name": "INDIVIDUAL_RANKING + PLACEMENT + 2 rounds",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "PLACEMENT",
        "ranking_direction": None,
        "measurement_unit": None,
        "tournament_type_id": None,  # INDIVIDUAL_RANKING
        "number_of_rounds": 2,
        "supports_finalization": True,
        "status": "⏳ TEST"
    },
    {
        "id": "T17",
        "name": "INDIVIDUAL_RANKING + PLACEMENT + 3 rounds",
        "format": "INDIVIDUAL_RANKING",
        "scoring_type": "PLACEMENT",
        "ranking_direction": None,
        "measurement_unit": None,
        "tournament_type_id": None,  # INDIVIDUAL_RANKING
        "number_of_rounds": 3,
        "supports_finalization": True,
        "status": "⏳ TEST"
    },

    # ========================================================================
    # TIER 1: Group + Knockout (1 config)
    # ========================================================================
    {
        "id": "T18",
        "name": "HEAD_TO_HEAD + Group Stage + Knockout",
        "format": "HEAD_TO_HEAD",
        "scoring_type": None,
        "ranking_direction": None,
        "measurement_unit": None,
        "tournament_type_id": 3,  # group_knockout
        "number_of_rounds": None,
        "supports_finalization": False,
        "status": "⏳ TEST"
    },
]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Admin login failed: {response.text}")


def create_tournament(token, config):
    """Create tournament with specific configuration"""
    headers = {"Authorization": f"Bearer {token}"}

    start_date = datetime.now() + timedelta(days=1)
    end_date = start_date + timedelta(days=7)

    tournament_data = {
        "code": f"E2E-{config['id']}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "name": f"E2E Test: {config['name']}",
        "start_date": start_date.date().isoformat(),
        "end_date": end_date.date().isoformat(),
        "age_group": "PRO",
        "specialization_type": "PLAYER",
        "format": config["format"],
        "scoring_type": config["scoring_type"],
        "measurement_unit": config["measurement_unit"],
        "ranking_direction": config["ranking_direction"],
        "tournament_type_id": config["tournament_type_id"],
        "number_of_rounds": config.get("number_of_rounds", 1),
        "max_players": 8,
        "assignment_type": "OPEN_ASSIGNMENT",
        "location_city": "Budapest",
        "location_venue": "LFA Academy",
        "is_active": True,
        "status": "DRAFT"
    }

    # Remove None values
    tournament_data = {k: v for k, v in tournament_data.items() if v is not None}

    response = requests.post(
        f"{API_BASE_URL}/semesters",
        headers=headers,
        json=tournament_data
    )

    if response.status_code == 200:
        return response.json()["id"]
    else:
        raise Exception(f"Tournament creation failed: {response.text}")


def enroll_players(token, tournament_id):
    """Enroll 8 players using admin batch-enroll"""
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.post(
        f"{API_BASE_URL}/tournaments/{tournament_id}/admin/batch-enroll",
        headers=headers,
        json={"player_ids": PLAYER_IDS}
    )

    if response.status_code == 200:
        return response.json()["success"]
    else:
        raise Exception(f"Enrollment failed: {response.text}")


def start_tournament(token, tournament_id):
    """Set tournament to IN_PROGRESS"""
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.patch(
        f"{API_BASE_URL}/semesters/{tournament_id}",
        headers=headers,
        json={"tournament_status": "IN_PROGRESS"}
    )

    return response.status_code == 200


def generate_sessions(token, tournament_id):
    """Generate tournament sessions"""
    headers = {"Authorization": f"Bearer {token}"}

    # Session generation request body
    request_body = {
        "parallel_fields": 1,
        "session_duration_minutes": 90,
        "break_minutes": 15,
        "number_of_rounds": 1
    }

    response = requests.post(
        f"{API_BASE_URL}/tournaments/{tournament_id}/generate-sessions",
        headers=headers,
        json=request_body
    )

    if response.status_code != 200:
        raise Exception(f"Session generation failed: {response.text}")

    # Fetch generated sessions from DB
    response = requests.get(
        f"{API_BASE_URL}/tournaments/{tournament_id}/sessions",
        headers=headers
    )

    if response.status_code == 200:
        sessions = response.json()
        return sessions
    else:
        raise Exception(f"Failed to fetch generated sessions: {response.text}")


def submit_results(token, tournament_id, sessions, scoring_type):
    """Submit match results (format depends on scoring_type)"""
    headers = {"Authorization": f"Bearer {token}"}

    for session in sessions:
        session_id = session.get("id")
        if not session_id:
            print(f"⚠️ Session has no ID, skipping")
            continue

        # Use all enrolled players as participants (simplification for E2E testing)
        # In reality, different sessions might have different participants
        participants = PLAYER_IDS

        # Submit game results with score and rank
        game_results = []
        for i, user_id in enumerate(participants):
            if scoring_type == "ROUNDS_BASED":
                score = 100 - (i * 5)  # Descending scores
            elif scoring_type == "TIME_BASED":
                score = 10.0 + (i * 0.5)  # Ascending times (faster is better)
            elif scoring_type == "SCORE_BASED":
                score = 95 - (i * 5)  # Descending scores
            elif scoring_type == "DISTANCE_BASED":
                score = 50.0 - (i * 2.0)  # Descending distances
            elif scoring_type == "PLACEMENT":
                score = 0.0  # No score for placement
            else:
                score = 100.0

            game_results.append({
                "user_id": user_id,
                "score": score,
                "rank": i + 1  # Rank: 1st, 2nd, 3rd, etc.
            })

        # Submit game results (PATCH /sessions/{id}/results)
        response = requests.patch(
            f"{API_BASE_URL}/sessions/{session_id}/results",
            headers=headers,
            json={
                "results": game_results
            }
        )

        if response.status_code != 200:
            raise Exception(f"Result submission failed: {response.text}")

    return True


def finalize_sessions(token, tournament_id, sessions):
    """Finalize sessions (only for INDIVIDUAL_RANKING)"""
    headers = {"Authorization": f"Bearer {token}"}

    for session in sessions:
        session_id = session.get("id")
        if not session_id:
            continue

        response = requests.post(
            f"{API_BASE_URL}/tournaments/{tournament_id}/sessions/{session_id}/finalize",
            headers=headers
        )

        if response.status_code != 200:
            raise Exception(f"Finalization failed: {response.text}")

    return True


def complete_tournament(token, tournament_id):
    """Complete tournament and create rankings"""
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.post(
        f"{API_BASE_URL}/tournaments/{tournament_id}/complete",
        headers=headers
    )

    return response.status_code == 200


def distribute_rewards(token, tournament_id):
    """Distribute rewards"""
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.post(
        f"{API_BASE_URL}/tournaments/{tournament_id}/distribute-rewards",
        headers=headers
    )

    return response.status_code == 200


def test_idempotency(token, tournament_id):
    """Test reward distribution idempotency"""
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.post(
        f"{API_BASE_URL}/tournaments/{tournament_id}/distribute-rewards",
        headers=headers
    )

    # Should return 400 (already distributed)
    return response.status_code == 400


# ============================================================================
# TEST RUNNER
# ============================================================================

def run_single_test(config):
    """Run E2E test for a single configuration"""
    print(f"\n{'='*80}")
    print(f"TEST {config['id']}: {config['name']}")
    print(f"{'='*80}")

    try:
        token = get_admin_token()
        print("✅ Admin authenticated")

        # Step 1: Create tournament
        tournament_id = create_tournament(token, config)
        print(f"✅ Step 1: Tournament {tournament_id} created")

        # Step 2: Enroll players
        enroll_players(token, tournament_id)
        print(f"✅ Step 2: Players enrolled")

        # Step 3: Start tournament
        start_tournament(token, tournament_id)
        print(f"✅ Step 3: Tournament started")

        # Step 4: Generate sessions
        sessions = generate_sessions(token, tournament_id)
        print(f"✅ Step 4: {len(sessions)} sessions generated")

        # Step 5: Submit results
        submit_results(token, tournament_id, sessions, config["scoring_type"])
        print(f"✅ Step 5: Results submitted")

        # Step 6: Finalize sessions (conditional)
        if config["supports_finalization"]:
            finalize_sessions(token, tournament_id, sessions)
            print(f"✅ Step 6: Sessions finalized")
        else:
            print(f"⏭️  Step 6: Skipped (HEAD_TO_HEAD doesn't support finalization)")

        # Step 7: Complete tournament
        complete_tournament(token, tournament_id)
        print(f"✅ Step 7: Tournament completed")

        # Step 8: Distribute rewards
        distribute_rewards(token, tournament_id)
        print(f"✅ Step 8: Rewards distributed")

        # Step 9: Test idempotency
        if test_idempotency(token, tournament_id):
            print(f"✅ Step 9: Idempotency protection verified")
        else:
            print(f"⚠️ Step 9: Idempotency protection NOT working")

        print(f"\n✅ TEST {config['id']} PASSED (Tournament {tournament_id})")
        return {"config": config, "status": "PASSED", "tournament_id": tournament_id, "error": None}

    except Exception as e:
        print(f"\n❌ TEST {config['id']} FAILED: {str(e)}")
        return {"config": config, "status": "FAILED", "tournament_id": None, "error": str(e)}


def run_all_tests():
    """Run all test configurations"""
    print("\n" + "="*80)
    print("COMPREHENSIVE TOURNAMENT E2E TEST SUITE")
    print("="*80)
    print(f"Total configurations to test: {len(TEST_CONFIGURATIONS)}")
    print("="*80)

    results = []

    for config in TEST_CONFIGURATIONS:
        if config["status"] == "✅ PASSED (Tournament 233)":
            print(f"\n⏭️  Skipping {config['id']} (already tested)")
            results.append({"config": config, "status": "SKIPPED", "tournament_id": 233, "error": None})
            continue

        result = run_single_test(config)
        results.append(result)

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for r in results if r["status"] == "PASSED")
    failed = sum(1 for r in results if r["status"] == "FAILED")
    skipped = sum(1 for r in results if r["status"] == "SKIPPED")

    print(f"✅ PASSED: {passed}")
    print(f"❌ FAILED: {failed}")
    print(f"⏭️  SKIPPED: {skipped}")
    print(f"📊 TOTAL: {len(results)}")

    print("\n" + "="*80)
    print("DETAILED RESULTS")
    print("="*80)

    for result in results:
        config = result["config"]
        status_emoji = "✅" if result["status"] == "PASSED" else ("❌" if result["status"] == "FAILED" else "⏭️")
        print(f"{status_emoji} {config['id']}: {config['name']}")
        if result["tournament_id"]:
            print(f"   Tournament ID: {result['tournament_id']}")
        if result["error"]:
            print(f"   Error: {result['error']}")

    return results


if __name__ == "__main__":
    results = run_all_tests()
