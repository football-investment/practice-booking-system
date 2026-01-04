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
            "role": "STUDENT",
            "date_of_birth": "2000-01-01",
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
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)

    tournament_data = {
        "date": tomorrow.isoformat(),
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
    response.raise_for_status()
    return response.json()


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
    Set final tournament rankings.

    Args:
        rankings: List of {"user_id": int, "placement": str, "points": int, "wins": int, "draws": int, "losses": int}
                  placement values: "1ST", "2ND", "3RD", "PARTICIPANT"
    """
    response = requests.post(
        f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/rankings",
        headers={"Authorization": f"Bearer {token}"},
        json={"rankings": rankings}
    )
    response.raise_for_status()
    return response.json()


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
    Create complete tournament with:
    - 5 enrolled players
    - Rankings set (1ST, 2ND, 3RD, 2x PARTICIPANT)
    - Status COMPLETED
    - Ready for reward distribution

    Returns:
        {
            "tournament_id": int,
            "tournament": dict,
            "players": list,
            "rankings": list
        }
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # Create tournament
    tournament_result = create_tournament_via_api(
        reward_policy_admin_token,
        name=f"Reward Test Tournament {timestamp}",
        reward_policy_name="default",
        age_group="AMATEUR"
    )
    tournament_id = tournament_result["tournament_id"]

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
