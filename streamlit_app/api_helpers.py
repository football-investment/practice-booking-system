"""
API Helper Functions
EXACT PATTERNS from unified_workflow_dashboard.py (WORKING!)
"""

import streamlit as st
import requests
from typing import Tuple, Optional, Union, List, Dict
from config import API_BASE_URL, API_TIMEOUT


def login_user(email: str, password: str) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Login user - returns (success, error_message, response_data)
    EXACT pattern from unified_workflow_dashboard.py
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={"email": email, "password": password},  # EXACT: "email" not "username"
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            # Backend returns errors in {"error": {"message": "..."}} format
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg = error_data['error'].get('message', f'HTTP {response.status_code}')
                else:
                    error_msg = error_data.get('detail', f'HTTP {response.status_code}')
            except:
                error_msg = f'HTTP {response.status_code}'
            return False, error_msg, None
    except Exception as e:
        return False, str(e), None


def get_current_user(token: str) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Get current user data
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            return False, f"HTTP {response.status_code}", None
    except Exception as e:
        return False, str(e), None


def get_users(token: str, limit: int = 100) -> Tuple[bool, list]:
    """
    Get users - EXACT pattern from working dashboard (Line 199)
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/users/?limit={limit}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            # EXACT pattern: data.get('users', []) if isinstance(data, dict) else data
            users = data.get('users', []) if isinstance(data, dict) else data
            return True, users
        else:
            # Return error details for debugging
            error_detail = f"HTTP {response.status_code}"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_detail = f"HTTP {response.status_code}: {error_data['error'].get('message', 'Unknown error')}"
            except:
                pass
            st.error(f"API Error: {error_detail}")
            return False, []
    except Exception as e:
        st.error(f"Connection Error: {str(e)}")
        return False, []


def get_sessions(token: str, size: int = 100, specialization_filter: bool = False) -> Tuple[bool, list]:
    """
    Get sessions - EXACT pattern from working dashboard (Line 2757-2778)
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/sessions/",  # ✅ Added trailing slash for refactored backend
            headers={"Authorization": f"Bearer {token}"},
            params={
                "size": size,
                "specialization_filter": specialization_filter
            },
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            sessions_data = response.json()

            # EXACT pattern: Handle SessionList response format
            if isinstance(sessions_data, dict) and 'sessions' in sessions_data:
                all_sessions = sessions_data['sessions']
            else:
                all_sessions = sessions_data if isinstance(sessions_data, list) else []

            return True, all_sessions
        else:
            return False, []
    except Exception as e:
        return False, []


def get_semesters(token: str) -> Tuple[bool, list]:
    """
    Get semesters - EXACT pattern from working dashboard (Line 2781-2794)
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/semesters/",  # ✅ Added trailing slash for refactored backend
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            semesters_data = response.json()

            # EXACT pattern: Handle SemesterList response format
            if isinstance(semesters_data, dict) and 'semesters' in semesters_data:
                all_semesters = semesters_data['semesters']
            else:
                all_semesters = semesters_data if isinstance(semesters_data, list) else []

            return True, all_semesters
        else:
            return False, []
    except Exception as e:
        return False, []


# ============================================================================
# SESSION CRUD OPERATIONS (NEW - for Admin Dashboard enhancement)
# ============================================================================

def update_session(token: str, session_id: int, data: dict) -> Tuple[bool, Optional[str], Optional[dict]]:
    """Update session data"""
    try:
        response = requests.put(
            f"{API_BASE_URL}/api/v1/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token}"},
            json=data,
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            error_msg = response.json().get('detail', f'HTTP {response.status_code}')
            return False, error_msg, None
    except Exception as e:
        return False, str(e), None


def delete_session(token: str, session_id: int) -> Tuple[bool, Optional[str]]:
    """Delete session"""
    try:
        response = requests.delete(
            f"{API_BASE_URL}/api/v1/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None
        else:
            error_msg = response.json().get('detail', f'HTTP {response.status_code}')
            return False, error_msg
    except Exception as e:
        return False, str(e)


# ============================================================================
# USER CRUD OPERATIONS (NEW - for Admin Dashboard enhancement)
# ============================================================================

def update_user(token: str, user_id: int, data: dict) -> Tuple[bool, Optional[str], Optional[dict]]:
    """Update user data"""
    try:
        response = requests.put(
            f"{API_BASE_URL}/api/v1/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
            json=data,
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            error_msg = response.json().get('detail', f'HTTP {response.status_code}')
            return False, error_msg, None
    except Exception as e:
        return False, str(e), None


def toggle_user_status(token: str, user_id: int, is_active: bool) -> Tuple[bool, Optional[str]]:
    """Activate/Deactivate user"""
    success, error, _ = update_user(token, user_id, {"is_active": is_active})
    return success, error


# ============================================================================
# LOCATION CRUD OPERATIONS (NEW - for Location Management)
# ============================================================================

def get_locations(token: str, include_inactive: bool = False) -> Tuple[bool, list]:
    """Get all locations"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/admin/locations/",
            headers={"Authorization": f"Bearer {token}"},
            params={"include_inactive": include_inactive},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            locations = response.json()
            return True, locations if isinstance(locations, list) else []
        else:
            return False, []
    except Exception as e:
        return False, []


def create_location(token: str, data: dict) -> Tuple[bool, Optional[str], Optional[dict]]:
    """Create new location"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/admin/locations/",
            headers={"Authorization": f"Bearer {token}"},
            json=data,
            timeout=API_TIMEOUT
        )

        if response.status_code == 201:
            return True, None, response.json()
        else:
            error_msg = response.json().get('detail', f'HTTP {response.status_code}')
            return False, error_msg, None
    except Exception as e:
        return False, str(e), None


def update_location(token: str, location_id: int, data: dict) -> Tuple[bool, Optional[str], Optional[dict]]:
    """Update location data"""
    try:
        response = requests.put(
            f"{API_BASE_URL}/api/v1/admin/locations/{location_id}",
            headers={"Authorization": f"Bearer {token}"},
            json=data,
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            error_msg = response.json().get('detail', f'HTTP {response.status_code}')
            return False, error_msg, None
    except Exception as e:
        return False, str(e), None


def delete_location(token: str, location_id: int) -> Tuple[bool, Optional[str]]:
    """Delete location (soft delete)"""
    try:
        response = requests.delete(
            f"{API_BASE_URL}/api/v1/admin/locations/{location_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 204:
            return True, None
        else:
            error_msg = response.json().get('detail', f'HTTP {response.status_code}')
            return False, error_msg
    except Exception as e:
        return False, str(e)


def toggle_location_status(token: str, location_id: int, is_active: bool) -> Tuple[bool, Optional[str]]:
    """Activate/Deactivate location"""
    success, error, _ = update_location(token, location_id, {"is_active": is_active})
    return success, error


# ========================================
# CAMPUS MANAGEMENT
# ========================================

def get_campuses_by_location(token: str, location_id: int, include_inactive: bool = False) -> Tuple[bool, Union[List[Dict], str]]:
    """Get all campuses for a specific location"""
    try:
        url = f"{API_BASE_URL}/api/v1/admin/locations/{location_id}/campuses"
        params = {"include_inactive": include_inactive}
        response = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=10)

        if response.status_code == 200:
            return True, response.json()
        else:
            error_msg = response.json().get("detail", "Failed to fetch campuses")
            return False, error_msg
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}"


def update_campus(token: str, campus_id: int, data: Dict) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """Update campus"""
    try:
        url = f"{API_BASE_URL}/api/v1/admin/campuses/{campus_id}"
        response = requests.put(url, json=data, headers={"Authorization": f"Bearer {token}"}, timeout=10)

        if response.status_code == 200:
            return True, None, response.json()
        else:
            error_msg = response.json().get("detail", "Failed to update campus")
            return False, error_msg, None
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}", None


def delete_campus(token: str, campus_id: int) -> Tuple[bool, Optional[str]]:
    """Delete campus (soft delete)"""
    try:
        url = f"{API_BASE_URL}/api/v1/admin/campuses/{campus_id}"
        response = requests.delete(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)

        if response.status_code == 204:
            return True, None
        else:
            error_msg = response.json().get("detail", "Failed to delete campus")
            return False, error_msg
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}"


def toggle_campus_status(token: str, campus_id: int, is_active: bool) -> Tuple[bool, Optional[str]]:
    """Activate/Deactivate campus"""
    success, error, _ = update_campus(token, campus_id, {"is_active": is_active})
    return success, error
