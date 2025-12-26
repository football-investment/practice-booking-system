"""
Position Management Module

Provides API wrapper functions for position operations:
- Position posting and management (Master Instructors)
- Job board browsing (All Instructors)
- Position status updates and closure
"""

import requests
from typing import Optional, List, Dict, Any
from config import API_BASE_URL


def get_api_url() -> str:
    """Get base API URL from config"""
    return f"{API_BASE_URL}/api/v1"


def get_headers(token: str) -> dict:
    """Build authorization headers"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


# ============================================================================
# Position Posting (Master Instructors)
# ============================================================================

def create_position(
    token: str,
    location_id: int,
    specialization_type: str,
    age_group: str,
    year: int,
    time_period_start: str,  # e.g., "M01", "Q1"
    time_period_end: str,    # e.g., "M06", "Q2"
    description: str,
    application_deadline: str,  # ISO format
    priority: int = 5
) -> Dict[str, Any]:
    """
    Master Instructor: Post a new position opening

    Returns: PositionResponse
    """
    url = f"{get_api_url()}/instructor-management/positions/"
    payload = {
        "location_id": location_id,
        "specialization_type": specialization_type,
        "age_group": age_group,
        "year": year,
        "time_period_start": time_period_start,
        "time_period_end": time_period_end,
        "description": description,
        "priority": priority,
        "application_deadline": application_deadline
    }
    response = requests.post(url, json=payload, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def get_all_positions(token: str, location_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Master Instructor: Get positions I posted

    Returns: PositionListResponse
    """
    url = f"{get_api_url()}/instructor-management/positions/my-positions"
    params = {}
    if location_id:
        params["location_id"] = location_id

    response = requests.get(url, params=params, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def get_position_by_id(token: str, location_id: int) -> List[Dict[str, Any]]:
    """
    Admin/Master Instructor: Get all positions for a specific location

    Returns: List of PositionResponse
    """
    url = f"{get_api_url()}/instructor-management/positions/my-positions"
    params = {"location_id": location_id}

    response = requests.get(url, params=params, headers=get_headers(token))
    response.raise_for_status()

    # Extract positions from response
    result = response.json()
    if isinstance(result, dict) and 'positions' in result:
        return result['positions']
    elif isinstance(result, list):
        return result
    else:
        return []


def get_job_board(
    token: str,
    location_id: Optional[int] = None,
    specialization: Optional[str] = None,
    age_group: Optional[str] = None,
    year: Optional[int] = None
) -> Dict[str, Any]:
    """
    All Instructors: View public job board

    Returns: JobBoardResponse with user_has_applied flags
    """
    url = f"{get_api_url()}/instructor-management/positions/job-board"
    params = {}
    if location_id:
        params["location_id"] = location_id
    if specialization:
        params["specialization"] = specialization
    if age_group:
        params["age_group"] = age_group
    if year:
        params["year"] = year

    response = requests.get(url, params=params, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def update_position(
    token: str,
    position_id: int,
    status: str  # "OPEN", "FILLED", "CLOSED", "CANCELLED"
) -> Dict[str, Any]:
    """
    Master Instructor: Update position status

    Returns: Updated PositionResponse
    """
    url = f"{get_api_url()}/instructor-management/positions/{position_id}"
    payload = {"status": status}
    response = requests.patch(url, json=payload, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def delete_position(token: str, position_id: int) -> None:
    """
    Master Instructor: Delete a position

    Typically should update status instead of delete (for audit trail).
    Delete only if position was posted in error.
    """
    url = f"{get_api_url()}/instructor-management/positions/{position_id}"
    response = requests.delete(url, headers=get_headers(token))
    response.raise_for_status()


def close_position(token: str, position_id: int) -> Dict[str, Any]:
    """
    Master Instructor: Close position (shorthand for update_position)

    Returns: Updated PositionResponse
    """
    return update_position(token, position_id, "CLOSED")
