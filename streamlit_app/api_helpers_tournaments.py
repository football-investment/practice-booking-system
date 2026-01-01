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
        response = requests.patch(
            f"{API_BASE_URL}/api/v1/semesters/{tournament_id}",
            headers={"Authorization": f"Bearer {token}"},
            json=update_data,
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
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
