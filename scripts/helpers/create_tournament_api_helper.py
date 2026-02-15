"""
API-based tournament creation helper for E2E tests

Creates a Group+Knockout tournament directly via API, bypassing unreliable UI preset selection.
Includes enrollment and session generation for complete setup.
"""
import requests
from typing import Dict, Any, List

API_BASE = "http://localhost:8000/api/v1"


def login_as_admin(
    admin_email: str = "admin@lfa.com",
    admin_password: str = "admin123"
) -> str:
    """
    Login as admin and return access token.

    Args:
        admin_email: Admin user email
        admin_password: Admin user password

    Returns:
        Access token string

    Raises:
        requests.HTTPError: If login fails
    """
    login_resp = requests.post(f"{API_BASE}/auth/login", json={
        "email": admin_email,
        "password": admin_password
    })
    login_resp.raise_for_status()
    return login_resp.json()["access_token"]


def create_group_knockout_tournament_via_api(
    admin_email: str = "admin@lfa.com",
    admin_password: str = "admin123",
    tournament_name: str = "LFA Golden Path Test Tournament"
) -> Dict[str, Any]:
    """
    Create a Group+Knockout tournament via API.

    Args:
        admin_email: Admin user email
        admin_password: Admin user password
        tournament_name: Tournament name

    Returns:
        Dict with tournament_id, token, and other details

    Raises:
        requests.HTTPError: If API call fails
    """
    # Step 1: Login as admin
    token = login_as_admin(admin_email, admin_password)
    headers = {"Authorization": f"Bearer {token}"}

    # Step 2: Create tournament with group_knockout type
    tournament_data = {
        "name": tournament_name,
        "tournament_type": "group_knockout",  # Code from tournament_types table (ID=3)
        "age_group": "YOUTH",  # Required field
        "max_players": 7,  # Match preset: Group+Knockout (7 players)
        "skills_to_test": ["PASSING", "DRIBBLING"],  # Required field (minimum 1 skill)
        "reward_config": [  # Required field
            {"rank": 1, "xp_reward": 100, "credits_reward": 50},
            {"rank": 2, "xp_reward": 75, "credits_reward": 30},
            {"rank": 3, "xp_reward": 50, "credits_reward": 20}
        ],
        "enrollment_cost": 0,  # Free tournament for testing
        "game_preset_id": None  # Not using preset, creating custom tournament
    }

    response = requests.post(
        f"{API_BASE}/tournaments/create",
        json=tournament_data,
        headers=headers
    )
    response.raise_for_status()

    result = response.json()
    result["token"] = token  # Include token for subsequent API calls
    print(f"✅ Tournament created via API:")
    print(f"   ID: {result['tournament_id']}")
    print(f"   Name: {result['tournament_name']}")
    print(f"   Code: {result['tournament_code']}")
    print(f"   Type: {result['tournament_type']}")
    print(f"   Status: {result['tournament_status']}")

    return result


def get_eligible_users(token: str, limit: int = 10) -> List[int]:
    """
    Get list of eligible user IDs for tournament enrollment.

    Args:
        token: Admin access token
        limit: Maximum number of users to fetch

    Returns:
        List of user IDs

    Raises:
        requests.HTTPError: If API call fails
    """
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_BASE}/sandbox/users",  # Use sandbox endpoint which returns STUDENT users
        params={"limit": limit},
        headers=headers
    )
    response.raise_for_status()
    users = response.json()

    # Extract user IDs (sandbox endpoint returns list directly)
    if isinstance(users, list):
        user_ids = [u["id"] for u in users]
    else:
        user_ids = []

    print(f"✅ Found {len(user_ids)} eligible users: {user_ids[:10]}")
    return user_ids


def enroll_participants_via_api(
    tournament_id: int,
    token: str,
    participant_count: int = 7
) -> Dict[str, Any]:
    """
    Enroll participants in tournament via API.

    Args:
        tournament_id: Tournament ID
        token: Admin access token
        participant_count: Number of participants to enroll

    Returns:
        Dict with enrollment result

    Raises:
        requests.HTTPError: If API call fails
    """
    headers = {"Authorization": f"Bearer {token}"}

    # Get eligible users
    user_ids = get_eligible_users(token, limit=participant_count)

    if len(user_ids) < participant_count:
        raise ValueError(f"Not enough eligible users: found {len(user_ids)}, need {participant_count}")

    # Enroll users (use first N users)
    enrolled_users = user_ids[:participant_count]

    enrollment_data = {
        "player_ids": enrolled_users  # Correct parameter name
    }

    response = requests.post(
        f"{API_BASE}/tournaments/{tournament_id}/admin/batch-enroll",  # Correct endpoint
        json=enrollment_data,
        headers=headers
    )
    response.raise_for_status()

    result = response.json()
    print(f"✅ Enrolled {result.get('enrolled_count', len(enrolled_users))} participants via API")
    return result


def generate_sessions_via_api(
    tournament_id: int,
    token: str
) -> Dict[str, Any]:
    """
    Generate tournament sessions via API.

    Args:
        tournament_id: Tournament ID
        token: Admin access token

    Returns:
        Dict with session generation result

    Raises:
        requests.HTTPError: If API call fails
    """
    headers = {"Authorization": f"Bearer {token}"}

    # Request body with default parameters
    session_data = {
        "parallel_fields": 1,
        "session_duration_minutes": 90,
        "break_minutes": 15,
        "number_of_rounds": 1
    }

    response = requests.post(
        f"{API_BASE}/tournaments/{tournament_id}/generate-sessions",
        json=session_data,
        headers=headers
    )

    if response.status_code != 200:
        print(f"❌ Session generation failed with status {response.status_code}")
        print(f"   Response: {response.text}")
        response.raise_for_status()

    result = response.json()
    print(f"✅ Generated sessions via API:")
    print(f"   Total sessions: {result.get('sessions_generated_count', 'unknown')}")
    return result


def submit_match_result_via_api(
    tournament_id: int,
    session_id: int,
    token: str,
    player1_score: int = 2,
    player2_score: int = 1
) -> Dict[str, Any]:
    """
    Submit match result via API.

    Args:
        tournament_id: Tournament ID
        session_id: Session ID
        token: Admin access token
        player1_score: Player 1 score
        player2_score: Player 2 score

    Returns:
        Dict with result submission response

    Raises:
        requests.HTTPError: If API call fails
    """
    headers = {"Authorization": f"Bearer {token}"}

    # Request body matching SessionResultSubmitRequest schema
    result_data = {
        "scores": {
            "player1": player1_score,
            "player2": player2_score
        }
    }

    response = requests.post(
        f"{API_BASE}/tournaments/{tournament_id}/sessions/{session_id}/results",
        json=result_data,
        headers=headers
    )

    if response.status_code != 200:
        print(f"❌ Match result submission failed with status {response.status_code}")
        print(f"   Response: {response.text}")
        response.raise_for_status()

    return response.json()


def get_knockout_sessions_via_api(
    tournament_id: int,
    token: str
) -> List[Dict[str, Any]]:
    """
    Get knockout sessions for tournament via API.

    Args:
        tournament_id: Tournament ID
        token: Admin access token

    Returns:
        List of knockout session dicts

    Raises:
        requests.HTTPError: If API call fails
    """
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(
        f"{API_BASE}/tournaments/{tournament_id}/sessions",
        params={"phase": "KNOCKOUT"},
        headers=headers
    )
    response.raise_for_status()

    sessions = response.json()
    return [s for s in sessions if s.get("tournament_phase") == "KNOCKOUT"]


if __name__ == "__main__":
    # Test the helper function
    try:
        result = create_group_knockout_tournament_via_api()
        print(f"\n✅ SUCCESS: Tournament {result['tournament_id']} created")
    except requests.HTTPError as e:
        print(f"\n❌ ERROR: {e}")
        print(f"Response: {e.response.text}")
