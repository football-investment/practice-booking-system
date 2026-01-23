"""
Tournament API Helper Functions
Handles tournament browsing and enrollment API calls
"""
import requests
from typing import Tuple, Optional, List, Dict, Any
from config import API_BASE_URL, API_TIMEOUT


def get_available_tournaments(
    token: str,
    age_group: Optional[str] = None,
    location_id: Optional[int] = None,
    campus_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Tuple[bool, Optional[str], List[Dict[str, Any]]]:
    """
    Get available tournaments for current player

    Args:
        token: Authentication token
        age_group: Filter by age category (optional)
        location_id: Filter by location city (optional)
        campus_id: Filter by campus venue (optional)
        start_date: Filter tournaments starting after this date (ISO format)
        end_date: Filter tournaments ending before this date (ISO format)

    Returns:
        Tuple of (success, error_message, tournaments_list)
        - success: True if API call succeeded
        - error_message: Error message if failed, None if succeeded
        - tournaments_list: List of tournament dicts with details
    """
    params = {}
    if age_group and age_group != "All":
        params['age_group'] = age_group
    if location_id:
        params['location_id'] = location_id
    if campus_id:
        params['campus_id'] = campus_id
    if start_date:
        params['start_date'] = start_date
    if end_date:
        params['end_date'] = end_date

    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/tournaments/available",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_msg = error_data.get('detail', response.text)
            return False, error_msg, []
    except requests.exceptions.Timeout:
        return False, "Request timed out. Please try again.", []
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to server. Please check your connection.", []
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", []


def enroll_in_tournament(
    token: str,
    tournament_id: int
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Enroll current player in a tournament

    Args:
        token: Authentication token
        tournament_id: ID of tournament to enroll in

    Returns:
        Tuple of (success, error_message, enrollment_data)
        - success: True if enrollment succeeded
        - error_message: Error message if failed, None if succeeded
        - enrollment_data: Enrollment details dict including:
          - enrollment: SemesterEnrollment object
          - tournament: Tournament details
          - conflicts: List of conflict warnings
          - warnings: List of warning messages
          - credits_remaining: Credits left after enrollment
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/enroll",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_msg = error_data.get('detail', response.text)
            return False, error_msg, {}
    except requests.exceptions.Timeout:
        return False, "Request timed out. Please try again.", {}
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to server. Please check your connection.", {}
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", {}


def update_session_game_type(
    token: str,
    session_id: int,
    game_type: str
) -> Tuple[bool, Optional[str]]:
    """
    Update game_type for a tournament session

    Args:
        token: API authentication token
        session_id: Session ID to update
        game_type: Game type (e.g., "Group Stage", "Semifinal", "Final")

    Returns:
        Tuple of (success, error_message)
        - success: True if update succeeded
        - error_message: Error message if failed, None if succeeded
    """
    try:
        response = requests.patch(
            f"{API_BASE_URL}/api/v1/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"game_type": game_type},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_msg = error_data.get('detail', response.text)
            return False, error_msg
    except requests.exceptions.Timeout:
        return False, "Request timed out. Please try again."
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to server. Please check your connection."
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def update_tournament(
    token: str,
    tournament_id: int,
    update_data: Dict[str, Any]
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Update tournament (semester) details

    ✅ NEW BEHAVIOR (2026-01-23):
    - ALL updates (including tournament_status) now use PATCH /tournaments/{id} endpoint
    - Admin can change tournament_status freely (bypasses state machine validation)
    - No longer uses /tournaments/{id}/status endpoint (that has strict validation)

    Args:
        token: API authentication token
        tournament_id: Tournament (semester) ID to update
        update_data: Dictionary with fields to update (e.g., start_date, end_date, status)

    Returns:
        Tuple of (success, error_message, updated_tournament)
        - success: True if update succeeded
        - error_message: Error message if failed, None if succeeded
        - updated_tournament: Updated tournament data if success
    """
    try:
        # ✅ NEW: Use PATCH /tournaments/{id} for ALL updates (including tournament_status)
        # This bypasses state machine validation and allows admin full control
        response = requests.patch(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}",
            headers={"Authorization": f"Bearer {token}"},
            json=update_data,
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            result = response.json()
            return True, None, result
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_msg = error_data.get('detail', response.text)
            return False, error_msg, None
    except requests.exceptions.Timeout:
        return False, "Request timed out. Please try again.", None
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to server. Please check your connection.", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


def get_reward_policies(token: str) -> Tuple[bool, Optional[str], List[Dict[str, Any]]]:
    """
    Get list of available reward policies (Admin only)

    Args:
        token: API authentication token

    Returns:
        Tuple of (success, error_message, policies_list)
        - success: True if API call succeeded
        - error_message: Error message if failed, None if succeeded
        - policies_list: List of reward policy dicts with metadata
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/tournaments/reward-policies",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            return True, None, data.get('policies', [])
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_msg = error_data.get('detail', response.text)
            return False, error_msg, []
    except requests.exceptions.Timeout:
        return False, "Request timed out. Please try again.", []
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to server. Please check your connection.", []
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", []


def get_reward_policy_details(
    token: str,
    policy_name: str
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Get details of a specific reward policy (Admin only)

    Args:
        token: API authentication token
        policy_name: Name of the reward policy (e.g., "default")

    Returns:
        Tuple of (success, error_message, policy_details)
        - success: True if API call succeeded
        - error_message: Error message if failed, None if succeeded
        - policy_details: Policy details dict with placement/participation rewards
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/tournaments/reward-policies/{policy_name}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_msg = error_data.get('detail', response.text)
            return False, error_msg, {}
    except requests.exceptions.Timeout:
        return False, "Request timed out. Please try again.", {}
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to server. Please check your connection.", {}
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", {}


def distribute_tournament_rewards(
    token: str,
    tournament_id: int
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Distribute rewards to tournament participants based on rankings (Admin only)

    Args:
        token: API authentication token
        tournament_id: Tournament ID to distribute rewards for

    Returns:
        Tuple of (success, error_message, distribution_stats)
        - success: True if distribution succeeded
        - error_message: Error message if failed, None if succeeded
        - distribution_stats: Stats dict with total_participants, xp_distributed, credits_distributed
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/distribute-rewards",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_msg = error_data.get('detail', response.text)
            return False, error_msg, {}
    except requests.exceptions.Timeout:
        return False, "Request timed out. Please try again.", {}
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to server. Please check your connection.", {}
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", {}


def get_tournament_enrollment_count(
    token: str,
    tournament_id: int
) -> int:
    """
    Get active enrollment count for a tournament

    Args:
        token: API authentication token
        tournament_id: Tournament (semester) ID

    Returns:
        Number of active enrollments (approved, is_active=True)
        Returns 0 if API call fails
    """
    try:
        url = f"{API_BASE_URL}/api/v1/semester-enrollments/semesters/{tournament_id}/enrollments"
        print(f"🔍 DEBUG: Fetching enrollments from: {url}")

        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        print(f"🔍 DEBUG: Response status: {response.status_code}")

        if response.status_code == 200:
            # API returns a list directly, not a dict with 'enrollments' key
            enrollments = response.json()
            print(f"🔍 DEBUG: Total enrollments: {len(enrollments)}")

            # Count only APPROVED and is_active enrollments
            # Note: API returns lowercase "approved", not "APPROVED"
            active_count = sum(
                1 for e in enrollments
                if e.get('request_status', '').upper() == 'APPROVED' and e.get('is_active') is True
            )
            print(f"🔍 DEBUG: Active approved count: {active_count}")
            return active_count
        else:
            print(f"⚠️ Failed to fetch enrollment count for tournament {tournament_id}: {response.status_code}")
            print(f"⚠️ Response body: {response.text[:200]}")
            return 0
    except Exception as e:
        print(f"⚠️ Error fetching enrollment count: {e}")
        return 0


# ============================================================================
# 🎯 TOURNAMENT TYPE & SESSION GENERATION HELPERS (PHASE 2)
# ============================================================================

def get_tournament_types(token: str) -> Tuple[bool, Optional[str], List[Dict[str, Any]]]:
    """
    Get list of available tournament types (Admin only)

    Args:
        token: API authentication token

    Returns:
        Tuple of (success, error_message, tournament_types_list)
        - success: True if API call succeeded
        - error_message: Error message if failed, None if succeeded
        - tournament_types_list: List of tournament type dicts with:
          - id, code, display_name, min_players, max_players, requires_power_of_two, config
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/tournament-types/",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_msg = error_data.get('detail', response.text)
            return False, error_msg, []
    except requests.exceptions.Timeout:
        return False, "Request timed out. Please try again.", []
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to server. Please check your connection.", []
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", []


def estimate_tournament_duration(
    token: str,
    tournament_type_id: int,
    player_count: int,
    parallel_fields: int = 1
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Estimate tournament duration based on tournament type and player count

    Args:
        token: API authentication token
        tournament_type_id: Tournament type ID
        player_count: Expected number of players
        parallel_fields: Number of fields available for parallel matches

    Returns:
        Tuple of (success, error_message, estimate_data)
        - success: True if API call succeeded
        - error_message: Error message if failed, None if succeeded
        - estimate_data: Dict with:
          - total_matches: int
          - total_rounds: int
          - estimated_duration_minutes: int
          - estimated_duration_days: float
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tournament-types/{tournament_type_id}/estimate",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "player_count": player_count,
                "parallel_fields": parallel_fields
            },
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_msg = error_data.get('detail', response.text)
            return False, error_msg, {}
    except requests.exceptions.Timeout:
        return False, "Request timed out. Please try again.", {}
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to server. Please check your connection.", {}
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", {}


def preview_tournament_sessions(
    token: str,
    tournament_id: int,
    parallel_fields: int = 1,
    session_duration_minutes: int = 90,
    break_minutes: int = 15
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Preview tournament sessions WITHOUT creating them in database

    Args:
        token: API authentication token
        tournament_id: Tournament (semester) ID
        parallel_fields: Number of fields available for parallel matches
        session_duration_minutes: Duration of each session
        break_minutes: Break time between sessions

    Returns:
        Tuple of (success, error_message, preview_data)
        - success: True if preview succeeded
        - error_message: Error message if failed, None if succeeded
        - preview_data: Dict with:
          - tournament_id, tournament_name, tournament_type_code
          - player_count, sessions (list of session previews)
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/preview-sessions",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "parallel_fields": parallel_fields,
                "session_duration_minutes": session_duration_minutes,
                "break_minutes": break_minutes
            },
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_msg = error_data.get('detail', response.text)
            return False, error_msg, {}
    except requests.exceptions.Timeout:
        return False, "Request timed out. Please try again.", {}
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to server. Please check your connection.", {}
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", {}


def generate_tournament_sessions(
    token: str,
    tournament_id: int,
    parallel_fields: int = 1,
    session_duration_minutes: int = 90,
    break_minutes: int = 15
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Generate tournament sessions based on tournament type and enrolled player count

    CRITICAL: Sessions can ONLY be generated when tournament_status = "IN_PROGRESS"

    Args:
        token: API authentication token
        tournament_id: Tournament (semester) ID
        parallel_fields: Number of fields available for parallel matches
        session_duration_minutes: Duration of each session
        break_minutes: Break time between sessions

    Returns:
        Tuple of (success, error_message, generation_data)
        - success: True if generation succeeded
        - error_message: Error message if failed, None if succeeded
        - generation_data: Dict with:
          - tournament_id, tournament_name, sessions_created, sessions_generated_at
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/generate-sessions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "parallel_fields": parallel_fields,
                "session_duration_minutes": session_duration_minutes,
                "break_minutes": break_minutes
            },
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_msg = error_data.get('detail', response.text)
            return False, error_msg, {}
    except requests.exceptions.Timeout:
        return False, "Request timed out. Please try again.", {}
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to server. Please check your connection.", {}
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", {}


def finalize_group_stage(
    token: str,
    tournament_id: int
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Finalize group stage and calculate final standings

    This endpoint:
    - Validates all group stage matches are completed
    - Calculates final group standings
    - Saves snapshot to database
    - Determines qualified participants for knockout stage

    Args:
        token: API authentication token
        tournament_id: Tournament (semester) ID

    Returns:
        Tuple of (success, error_message, finalization_data)
        - success: True if finalization succeeded
        - error_message: Error message if failed, None if succeeded
        - finalization_data: Dict with group_standings and qualified_participants
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/finalize-group-stage",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_msg = error_data.get('detail', response.text)
            return False, error_msg, {}
    except requests.exceptions.Timeout:
        return False, "Request timed out. Please try again.", {}
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to server. Please check your connection.", {}
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", {}


def delete_generated_sessions(
    token: str,
    tournament_id: int
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Delete all auto-generated sessions for a tournament (RESET functionality)

    Args:
        token: API authentication token
        tournament_id: Tournament (semester) ID

    Returns:
        Tuple of (success, error_message, deletion_data)
        - success: True if deletion succeeded
        - error_message: Error message if failed, None if succeeded
        - deletion_data: Dict with sessions_deleted count
    """
    try:
        response = requests.delete(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/sessions",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_msg = error_data.get('detail', response.text)
            return False, error_msg, {}
    except requests.exceptions.Timeout:
        return False, "Request timed out. Please try again.", {}
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to server. Please check your connection.", {}
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", {}
