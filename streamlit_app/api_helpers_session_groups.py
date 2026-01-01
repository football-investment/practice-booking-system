"""
API Helpers for Session Group Assignment

Dynamic group creation at session start
"""

import requests
from config import API_BASE_URL
from typing import Tuple, List, Dict, Optional


def get_session_attendance(token: str, session_id: int) -> Tuple[bool, List[Dict]]:
    """
    Get attendance records for a session

    Returns: (success, attendance_list)
    """
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_BASE_URL}/attendance",
            headers=headers,
            params={"session_id": session_id}
        )

        if response.status_code == 200:
            data = response.json()
            # Handle different response formats
            if isinstance(data, list):
                return True, data
            elif isinstance(data, dict) and "attendances" in data:
                return True, data["attendances"]
            else:
                return True, []
        else:
            return False, []
    except Exception as e:
        print(f"Error fetching attendance: {e}")
        return False, []


def mark_student_attendance(token: str, session_id: int, user_id: int, status: str, booking_id: Optional[int] = None) -> Tuple[bool, str]:
    """
    Mark a student's attendance

    Args:
        token: Auth token
        session_id: Session ID
        user_id: Student user ID
        status: "present", "absent", "late", "excused"
        booking_id: Optional booking ID

    Returns: (success, message)
    """
    try:
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "session_id": session_id,
            "user_id": user_id,
            "status": status
        }

        if booking_id:
            data["booking_id"] = booking_id

        response = requests.post(
            f"{API_BASE_URL}/attendance",
            headers=headers,
            json=data
        )

        if response.status_code in [200, 201]:
            return True, "Attendance marked successfully"
        else:
            error = response.json().get("error", {}).get("message", "Unknown error")
            return False, error
    except Exception as e:
        return False, str(e)


def auto_assign_groups(token: str, session_id: int) -> Tuple[bool, Optional[Dict], str]:
    """
    Auto-assign students to groups based on attendance

    Returns: (success, group_data, message)
    """
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            f"{API_BASE_URL}/session-groups/auto-assign",
            headers=headers,
            json={"session_id": session_id}
        )

        if response.status_code == 200:
            data = response.json()
            return True, data, "Groups assigned successfully"
        else:
            error = response.json().get("error", {}).get("message", "Unknown error")
            return False, None, error
    except Exception as e:
        return False, None, str(e)


def get_session_groups(token: str, session_id: int) -> Tuple[bool, Optional[Dict]]:
    """
    Get group assignments for a session

    Returns: (success, group_data)
    """
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_BASE_URL}/session-groups/{session_id}",
            headers=headers
        )

        if response.status_code == 200:
            return True, response.json()
        else:
            return False, None
    except Exception as e:
        print(f"Error fetching groups: {e}")
        return False, None


def move_student_to_group(token: str, student_id: int, from_group_id: int, to_group_id: int) -> Tuple[bool, str]:
    """
    Move a student from one group to another

    Returns: (success, message)
    """
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            f"{API_BASE_URL}/session-groups/move-student",
            headers=headers,
            json={
                "student_id": student_id,
                "from_group_id": from_group_id,
                "to_group_id": to_group_id
            }
        )

        if response.status_code == 200:
            return True, "Student moved successfully"
        else:
            error = response.json().get("error", {}).get("message", "Unknown error")
            return False, error
    except Exception as e:
        return False, str(e)


def delete_session_groups(token: str, session_id: int) -> Tuple[bool, str]:
    """
    Delete all groups for a session (reset)

    Returns: (success, message)
    """
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.delete(
            f"{API_BASE_URL}/session-groups/{session_id}",
            headers=headers
        )

        if response.status_code == 204:
            return True, "Groups deleted successfully"
        else:
            error = response.json().get("error", {}).get("message", "Unknown error")
            return False, error
    except Exception as e:
        return False, str(e)


def get_session_bookings(token: str, session_id: int) -> Tuple[bool, List[Dict]]:
    """
    Get all bookings for a session

    Returns: (success, bookings_list)
    """
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_BASE_URL}/bookings",
            headers=headers,
            params={"session_id": session_id}
        )

        if response.status_code == 200:
            data = response.json()
            # Handle different response formats
            if isinstance(data, list):
                return True, data
            elif isinstance(data, dict) and "bookings" in data:
                return True, data["bookings"]
            else:
                return True, []
        else:
            return False, []
    except Exception as e:
        print(f"Error fetching bookings: {e}")
        return False, []
