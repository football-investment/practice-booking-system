"""
API Helper Functions for Enrollment Conflict and Schedule Management
Supports three-tier parallel enrollment system
"""

import requests
from typing import Tuple, Optional, Dict, List
from config import API_BASE_URL, API_TIMEOUT


def check_enrollment_conflicts(token: str, semester_id: int) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Check if enrolling in a semester would create conflicts.

    Returns:
        (success, error_message, conflict_data)

    conflict_data structure:
    {
        "semester": {...},
        "has_conflict": bool,
        "conflicts": [...],
        "warnings": [...],
        "can_enroll": true,
        "conflict_summary": {
            "total_conflicts": int,
            "blocking_conflicts": int,
            "warning_conflicts": int
        }
    }
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/enrollments/{semester_id}/check-conflicts",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            error_msg = f"HTTP {response.status_code}"
            try:
                error_data = response.json()
                error_msg = error_data.get('detail', error_msg)
            except:
                pass
            return False, error_msg, None

    except Exception as e:
        return False, str(e), None


def get_user_schedule(token: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Get complete schedule for current user across all enrollment types.

    Args:
        token: Auth token
        start_date: Start date (YYYY-MM-DD), defaults to today
        end_date: End date (YYYY-MM-DD), defaults to start_date + 90 days

    Returns:
        (success, error_message, schedule_data)

    schedule_data structure:
    {
        "enrollments": [
            {
                "enrollment_id": int,
                "semester_name": str,
                "enrollment_type": "TOURNAMENT" | "MINI_SEASON" | "ACADEMY_SEASON",
                "sessions": [...]
            }
        ],
        "total_sessions": int,
        "date_range": {...}
    }
    """
    try:
        params = {}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date

        response = requests.get(
            f"{API_BASE_URL}/api/v1/enrollments/my-schedule",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            error_msg = f"HTTP {response.status_code}"
            try:
                error_data = response.json()
                error_msg = error_data.get('detail', error_msg)
            except:
                pass
            return False, error_msg, None

    except Exception as e:
        return False, str(e), None


def validate_enrollment_request(token: str, semester_id: int) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Full validation for enrollment request.

    Returns:
        (success, error_message, validation_data)

    validation_data structure:
    {
        "semester": {...},
        "allowed": true,
        "conflicts": [...],
        "warnings": [...],
        "recommendations": [...],
        "summary": {
            "total_conflicts": int,
            "total_warnings": int,
            "has_blocking_conflicts": bool
        }
    }
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/enrollments/validate",
            headers={"Authorization": f"Bearer {token}"},
            params={"semester_id": semester_id},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            error_msg = f"HTTP {response.status_code}"
            try:
                error_data = response.json()
                error_msg = error_data.get('detail', error_msg)
            except:
                pass
            return False, error_msg, None

    except Exception as e:
        return False, str(e), None


def get_enrollments_by_type(enrollments: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Helper function to group enrollments by enrollment type.

    Args:
        enrollments: List of enrollment dictionaries from get_user_schedule

    Returns:
        {
            "TOURNAMENT": [...],
            "MINI_SEASON": [...],
            "ACADEMY_SEASON": [...]
        }
    """
    grouped = {
        "TOURNAMENT": [],
        "MINI_SEASON": [],
        "ACADEMY_SEASON": []
    }

    for enrollment in enrollments:
        enrollment_type = enrollment.get("enrollment_type", "OTHER")
        if enrollment_type in grouped:
            grouped[enrollment_type].append(enrollment)

    return grouped
