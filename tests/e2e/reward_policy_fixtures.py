"""
Reward Policy E2E Test Fixtures

Creates multi-user test environment for reward policy testing:
- 1 admin
- 5 players (different age groups)
- Tournament with multiple games/sessions
- Rankings and results
"""

import requests
import pytest
from typing import Dict, Any, List, Generator
from datetime import datetime, timedelta
import os


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


# ============================================================================
# Multi-User Creation Helpers
# ============================================================================

def create_admin_token() -> str:
    """Get admin authentication token."""
    response = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"email": "admin@lfa.com", "password": "admin123"}
    )
    response.raise_for_status()
    return response.json()["access_token"]


def create_player_users(token: str, count: int = 5, age_group: str = "AMATEUR") -> List[Dict[str, Any]]:
    """
    Create multiple player users with different characteristics.

    Args:
        token: Admin auth token
        count: Number of players (default 5)
        age_group: Age group for tournament (PRE, YOUTH, AMATEUR, PRO)

    Returns:
        List of player dicts with email, password, id, initial_xp, initial_credits
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    players = []

    for i in range(count):
        player_data = {
            "email": f"tournament_player_{timestamp}_{i}@test.com",
            "name": f"Tournament Player {i+1}",
            "password": "TestPass123!",
            "role": "student",  # ✅ FIXED: lowercase role value
            "date_of_birth": "2000-01-01T00:00:00",  # ✅ FIXED: ISO datetime format
            "specialization": "LFA_FOOTBALL_PLAYER"
        }

        response = requests.post(
            f"{API_BASE_URL}/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
            json=player_data
        )
        response.raise_for_status()

        user = response.json()
        user["password"] = player_data["password"]

        # Get current XP and credits for validation later
        user_detail_response = requests.get(
            f"{API_BASE_URL}/api/v1/users/{user['id']}",
            headers={"Authorization": f"Bearer {token}"}
        )
        user_detail = user_detail_response.json()
        user["initial_xp"] = user_detail.get("total_xp", 0)
        user["initial_credits"] = user_detail.get("credit_balance", 0)

        # ✅ CRITICAL FIX: Directly insert license via database
        # Bypass API complexity and create license + user_license records directly
        import psycopg2
        conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
        cur = conn.cursor()

        # 1. Activate user and give 1000 credits
        cur.execute(
            "UPDATE users SET is_active = true, credit_balance = 1000 WHERE id = %s",
            (user['id'],)
        )

        # 2. Insert user_licenses record (required for enrollment validation)
        cur.execute(
            """
            INSERT INTO user_licenses (user_id, specialization_type, current_level, max_achieved_level, started_at)
            VALUES (%s, 'LFA_FOOTBALL_PLAYER', 1, 1, NOW())
            RETURNING id
            """,
            (user['id'],)
        )
        license_id = cur.fetchone()[0]
        user["license_id"] = license_id

        conn.commit()
        cur.close()
        conn.close()
        user["initial_credits"] = 1000

        players.append(user)

    return players


def create_tournament_via_api(
    token: str,
    name: str,
    reward_policy_name: str = "default",
    age_group: str = "AMATEUR"
) -> Dict[str, Any]:
    """
    Create tournament with reward policy via API.

    Uses the POST /api/v1/tournaments/generate endpoint.
    """
    import random

    # Try multiple dates to avoid conflicts
    for attempt in range(10):
        today = datetime.now().date()
        # Use far future date with random offset
        future_days = random.randint(100, 365)  # 100-365 days in future
        future_date = today + timedelta(days=future_days)

        tournament_data = {
            "date": future_date.isoformat(),
            "name": name,
            "specialization_type": "LFA_FOOTBALL_PLAYER",
            "age_group": age_group,
            "reward_policy_name": reward_policy_name,
            "sessions": [
                {"time": "10:00", "title": "Morning Game", "duration_minutes": 90, "capacity": 20},
                {"time": "14:00", "title": "Afternoon Game", "duration_minutes": 90, "capacity": 20},
                {"time": "18:00", "title": "Evening Finals", "duration_minutes": 90, "capacity": 16}
            ],
            "campus_id": 1,  # Assume campus 1 exists
            "location_id": 1,  # Assume location 1 exists
            "auto_book_students": False
        }

        response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/generate",
            headers={"Authorization": f"Bearer {token}"},
            json=tournament_data
        )

        if response.status_code == 201 or response.status_code == 200:
            return response.json()
        elif response.status_code == 409:
            # Conflict - try next date
            continue
        else:
            response.raise_for_status()

    # If all attempts failed, raise the last error
    response.raise_for_status()
    return {}


def enroll_players_in_tournament(
    token: str,
    tournament_id: int,
    player_ids: List[int]
) -> List[Dict[str, Any]]:
    """Enroll multiple players in tournament."""
    enrollments = []

    for player_id in player_ids:
        # Get player token
        player_response = requests.get(
            f"{API_BASE_URL}/api/v1/users/{player_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        player = player_response.json()

        # Login as player to get their token
        login_response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={"email": player["email"], "password": "TestPass123!"}
        )
        player_token = login_response.json()["access_token"]

        # Enroll in tournament
        enroll_response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/enroll",
            headers={"Authorization": f"Bearer {player_token}"}
        )
        enroll_response.raise_for_status()
        enrollments.append(enroll_response.json())

    return enrollments


def set_tournament_rankings(
    token: str,
    tournament_id: int,
    rankings: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Set final tournament rankings via direct database insertion.

    Args:
        rankings: List of {"user_id": int, "placement": str, "points": int, "wins": int, "draws": int, "losses": int}
                  placement values: "1ST", "2ND", "3RD", "PARTICIPANT"
    """
    import psycopg2
    conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
    cur = conn.cursor()

    # Map placement to rank number
    placement_to_rank = {"1ST": 1, "2ND": 2, "3RD": 3, "PARTICIPANT": 4}

    for ranking in rankings:
        rank = placement_to_rank.get(ranking["placement"], 999)
        cur.execute(
            """
            INSERT INTO tournament_rankings (tournament_id, user_id, participant_type, rank, points, wins, draws, losses)
            VALUES (%s, %s, 'INDIVIDUAL', %s, %s, %s, %s, %s)
            """,
            (
                tournament_id,
                ranking["user_id"],
                rank,
                ranking["points"],
                ranking["wins"],
                ranking["draws"],
                ranking["losses"]
            )
        )

    conn.commit()
    cur.close()
    conn.close()

    return {"message": "Rankings set successfully", "count": len(rankings)}


def mark_tournament_completed(token: str, tournament_id: int):
    """Mark tournament as COMPLETED."""
    response = requests.patch(
        f"{API_BASE_URL}/api/v1/semesters/{tournament_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "COMPLETED"}
    )
    response.raise_for_status()
    return response.json()


def distribute_rewards(token: str, tournament_id: int) -> Dict[str, Any]:
    """Trigger reward distribution."""
    response = requests.post(
        f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/distribute-rewards",
        headers={"Authorization": f"Bearer {token}"}
    )
    response.raise_for_status()
    return response.json()


def get_user_current_stats(token: str, user_id: int) -> Dict[str, Any]:
    """Get user's current XP and credits."""
    response = requests.get(
        f"{API_BASE_URL}/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    response.raise_for_status()
    user = response.json()
    return {
        "user_id": user_id,
        "email": user["email"],
        "total_xp": user.get("total_xp", 0),
        "credit_balance": user.get("credit_balance", 0)
    }


def cleanup_user(token: str, user_id: int):
    """Delete test user."""
    try:
        requests.delete(
            f"{API_BASE_URL}/api/v1/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
    except Exception as e:
        print(f"Warning: Failed to cleanup user {user_id}: {e}")


def cleanup_tournament(token: str, tournament_id: int):
    """Delete tournament (cascades to sessions, bookings, rankings)."""
    try:
        requests.delete(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
    except Exception as e:
        print(f"Warning: Failed to cleanup tournament {tournament_id}: {e}")


# ============================================================================
# Pytest Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def reward_policy_admin_token() -> Generator[str, None, None]:
    """Admin token for reward policy tests."""
    token = create_admin_token()
    yield token


@pytest.fixture(scope="function")
def reward_policy_players(reward_policy_admin_token: str) -> Generator[List[Dict[str, Any]], None, None]:
    """
    Create 5 test players for reward policy testing.

    Returns:
        List of 5 players with email, password, id, initial_xp, initial_credits
    """
    players = create_player_users(reward_policy_admin_token, count=5, age_group="AMATEUR")
    yield players

    # Cleanup
    for player in players:
        cleanup_user(reward_policy_admin_token, player["id"])


@pytest.fixture(scope="function")
def reward_policy_tournament_complete(
    reward_policy_admin_token: str,
    reward_policy_players: List[Dict[str, Any]]
) -> Generator[Dict[str, Any], None, None]:
    """
    ⚠️ SIMPLIFIED TOURNAMENT FIXTURE (NOT PRODUCTION-REPRESENTATIVE)

    Creates a tournament in COMPLETED state with rankings for reward distribution testing.

    WARNING: This fixture bypasses the full production tournament lifecycle:

    MISSING STEPS (Production Requirements):
    ❌ Instructor assignment (master_instructor_id remains NULL)
    ❌ Session attendance tracking (no attendance records created)
    ❌ Instructor-submitted rankings (rankings inserted via direct SQL)

    ACTUAL FLOW IN THIS FIXTURE:
    1. Admin creates tournament → status: SEEKING_INSTRUCTOR
    2. ⚠️ Manual PATCH to change status → READY_FOR_ENROLLMENT (bypasses instructor)
    3. Players enroll in tournament
    4. ⚠️ Direct SQL insertion of rankings (bypasses attendance/session workflow)
    5. Mark tournament as COMPLETED
    6. Ready for reward distribution testing

    PRODUCTION FLOW (Should Be):
    1. Admin creates tournament → status: SEEKING_INSTRUCTOR
    2. Instructor accepts assignment → status: READY_FOR_ENROLLMENT
    3. Players enroll in tournament
    4. Instructor marks attendance for each session
    5. Instructor submits rankings based on session results
    6. Tournament marked as COMPLETED
    7. Admin distributes rewards

    USE CASE: Testing reward distribution backend logic ONLY.
    NOT SUITABLE FOR: Full tournament lifecycle E2E testing.

    Returns:
        {
            "tournament_id": int,
            "tournament": dict (with tournament details),
            "players": list (5 players with license_id),
            "rankings": list (rankings: 1ST, 2ND, 3RD, 2x PARTICIPANT)
        }

    TODO: Implement reward_policy_tournament_complete_with_instructor() fixture
          for production-representative testing once instructor workflow is implemented.
    """
    # Use microsecond-level timestamp to ensure uniqueness
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")

    # Create tournament
    tournament_result = create_tournament_via_api(
        reward_policy_admin_token,
        name=f"Reward Test Tournament {timestamp}",
        reward_policy_name="default",
        age_group="AMATEUR"
    )
    tournament_id = tournament_result["tournament_id"]

    # ✅ CRITICAL FIX: Change tournament status to READY_FOR_ENROLLMENT
    status_response = requests.patch(
        f"{API_BASE_URL}/api/v1/semesters/{tournament_id}",
        headers={"Authorization": f"Bearer {reward_policy_admin_token}"},
        json={"status": "READY_FOR_ENROLLMENT"}
    )
    status_response.raise_for_status()

    # Enroll all players
    player_ids = [p["id"] for p in reward_policy_players]
    enrollments = enroll_players_in_tournament(
        reward_policy_admin_token,
        tournament_id,
        player_ids
    )

    # Set rankings: 1ST, 2ND, 3RD, PARTICIPANT, PARTICIPANT
    rankings = [
        {"user_id": reward_policy_players[0]["id"], "placement": "1ST", "points": 15, "wins": 5, "draws": 0, "losses": 0},
        {"user_id": reward_policy_players[1]["id"], "placement": "2ND", "points": 12, "wins": 4, "draws": 0, "losses": 1},
        {"user_id": reward_policy_players[2]["id"], "placement": "3RD", "points": 9, "wins": 3, "draws": 0, "losses": 2},
        {"user_id": reward_policy_players[3]["id"], "placement": "PARTICIPANT", "points": 3, "wins": 1, "draws": 0, "losses": 4},
        {"user_id": reward_policy_players[4]["id"], "placement": "PARTICIPANT", "points": 0, "wins": 0, "draws": 0, "losses": 5}
    ]
    set_tournament_rankings(reward_policy_admin_token, tournament_id, rankings)

    # Mark as COMPLETED
    mark_tournament_completed(reward_policy_admin_token, tournament_id)

    test_data = {
        "tournament_id": tournament_id,
        "tournament": tournament_result,
        "players": reward_policy_players,
        "rankings": rankings
    }

    yield test_data

    # Cleanup
    cleanup_tournament(reward_policy_admin_token, tournament_id)
