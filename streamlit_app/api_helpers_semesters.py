"""
API Helper Functions for Semester Management
Extracted from unified_workflow_dashboard.py
"""

import requests
from typing import Tuple, Optional, List, Dict
from config import API_BASE_URL


# ============================================================================
# LOCATION MANAGEMENT APIs
# ============================================================================

def get_all_locations(token: str, include_inactive: bool = False) -> Tuple[bool, Optional[str], Optional[List[dict]]]:
    """
    Fetch all locations from the API

    Args:
        token: Admin authentication token
        include_inactive: Whether to include inactive locations

    Returns:
        Tuple of (success, error_message, locations_list)
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/admin/locations/",
            headers={"Authorization": f"Bearer {token}"},
            params={"include_inactive": include_inactive},
            timeout=30
        )

        if response.status_code == 200:
            locations = response.json()
            return True, None, locations
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            return False, error_msg, None

    except requests.exceptions.RequestException as e:
        return False, f"Network error: {str(e)}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


def create_location(token: str, location_data: dict) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Create a new location

    Args:
        token: Admin authentication token
        location_data: Dictionary with location fields

    Returns:
        Tuple of (success, error_message, created_location)
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/admin/locations/",
            headers={"Authorization": f"Bearer {token}"},
            json=location_data,
            timeout=30
        )

        if response.status_code in [200, 201]:
            location = response.json()
            return True, None, location
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            return False, error_msg, None

    except requests.exceptions.RequestException as e:
        return False, f"Network error: {str(e)}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


def update_location(token: str, location_id: int, update_data: dict) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Update a location

    Args:
        token: Admin authentication token
        location_id: ID of location to update
        update_data: Dictionary with fields to update

    Returns:
        Tuple of (success, error_message, updated_location)
    """
    try:
        response = requests.patch(
            f"{API_BASE_URL}/api/v1/admin/locations/{location_id}",
            headers={"Authorization": f"Bearer {token}"},
            json=update_data,
            timeout=30
        )

        if response.status_code == 200:
            location = response.json()
            return True, None, location
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            return False, error_msg, None

    except requests.exceptions.RequestException as e:
        return False, f"Network error: {str(e)}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


# ============================================================================
# SEMESTER GENERATION APIs
# ============================================================================

# ============================================================================
# 🚀 NEW: MODULAR LFA_PLAYER SEASON GENERATORS (Individual Period Selection)
# ============================================================================

def generate_lfa_player_pre_season(
    token: str,
    year: int,
    month: int,
    location_id: int,
    force_overwrite: bool = False
) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Generate a single LFA_PLAYER PRE monthly season

    Args:
        token: Admin authentication token
        year: Year (e.g., 2026)
        month: Month number (1-12)
        location_id: ID of location
        force_overwrite: Replace existing season if true

    Returns:
        Tuple of (success, error_message, result_data)
        result_data contains: {
            "success": bool,
            "message": str,  # e.g., "Successfully generated season M03 for 2025/LFA_PLAYER/PRE"
            "period": {
                "code": str,
                "name": str,
                "start_date": str,
                "end_date": str,
                "theme": str,
                "focus_description": str,
                "period_type": "season"
            }
        }
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/admin/periods/lfa-player/pre",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "year": year,
                "month": month,
                "location_id": location_id,
                "force_overwrite": force_overwrite
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return True, None, result
        else:
            error_msg = response.json().get("detail", f"HTTP {response.status_code}: {response.text}")
            return False, error_msg, None

    except requests.exceptions.RequestException as e:
        return False, f"Network error: {str(e)}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


def generate_lfa_player_youth_season(
    token: str,
    year: int,
    quarter: int,
    location_id: int,
    force_overwrite: bool = False
) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Generate a single LFA_PLAYER YOUTH quarterly season

    Args:
        token: Admin authentication token
        year: Year (e.g., 2026)
        quarter: Quarter number (1-4)
        location_id: ID of location
        force_overwrite: Replace existing season if true

    Returns:
        Tuple of (success, error_message, result_data)
        result_data contains: {
            "success": bool,
            "message": str,  # e.g., "Successfully generated season Q2 for 2025/LFA_PLAYER/YOUTH"
            "period": {...}
        }
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/admin/periods/lfa-player/youth",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "year": year,
                "quarter": quarter,
                "location_id": location_id,
                "force_overwrite": force_overwrite
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return True, None, result
        else:
            error_msg = response.json().get("detail", f"HTTP {response.status_code}: {response.text}")
            return False, error_msg, None

    except requests.exceptions.RequestException as e:
        return False, f"Network error: {str(e)}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


def generate_lfa_player_amateur_season(
    token: str,
    year: int,
    location_id: int,
    force_overwrite: bool = False
) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Generate annual season for LFA_PLAYER AMATEUR (Jul-Jun)

    Args:
        token: Admin authentication token
        year: Year (e.g., 2026)
        location_id: ID of location
        force_overwrite: Replace existing season if true

    Returns:
        Tuple of (success, error_message, result_data)
        result_data contains: {
            "success": bool,
            "message": str,  # e.g., "Successfully generated season for 2025/2026 LFA_PLAYER/AMATEUR"
            "period": {...}
        }
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/admin/periods/lfa-player/amateur",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "year": year,
                "location_id": location_id,
                "force_overwrite": force_overwrite
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return True, None, result
        else:
            error_msg = response.json().get("detail", f"HTTP {response.status_code}: {response.text}")
            return False, error_msg, None

    except requests.exceptions.RequestException as e:
        return False, f"Network error: {str(e)}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


def generate_lfa_player_pro_season(
    token: str,
    year: int,
    location_id: int,
    force_overwrite: bool = False
) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Generate annual season for LFA_PLAYER PRO (Jul-Jun)

    Args:
        token: Admin authentication token
        year: Year (e.g., 2026)
        location_id: ID of location
        force_overwrite: Replace existing season if true

    Returns:
        Tuple of (success, error_message, result_data)
        result_data contains: {
            "success": bool,
            "message": str,  # e.g., "Successfully generated season for 2025/LFA_PLAYER/PRO"
            "period": {...}
        }
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/admin/periods/lfa-player/pro",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "year": year,
                "location_id": location_id,
                "force_overwrite": force_overwrite
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return True, None, result
        else:
            error_msg = response.json().get("detail", f"HTTP {response.status_code}: {response.text}")
            return False, error_msg, None

    except requests.exceptions.RequestException as e:
        return False, f"Network error: {str(e)}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


# ============================================================================
# OLD BULK SEMESTER GENERATOR (⚠️ Still used for INTERNSHIP/COACH/GANCUJU)
# ============================================================================

def get_available_templates(token: str) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Fetch available semester templates from backend

    Args:
        token: Admin authentication token

    Returns:
        Tuple of (success, error_message, templates_data)
        templates_data contains: {"available_templates": [...]}
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/admin/semesters/available-templates",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            return True, None, data
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            return False, error_msg, None

    except requests.exceptions.RequestException as e:
        return False, f"Network error: {str(e)}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


def generate_semesters(token: str, year: int, specialization: str, age_group: str, location_id: int) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Generate semesters for a given year/specialization/age group at a location

    Args:
        token: Admin authentication token
        year: Year to generate for (e.g., 2026)
        specialization: Specialization type (e.g., "LFA_PLAYER")
        age_group: Age group (e.g., "PRE", "YOUTH")
        location_id: ID of location where semesters will be held

    Returns:
        Tuple of (success, error_message, result_data)
        result_data contains: {
            "message": str,
            "generated_count": int,
            "semesters": [...]
        }
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/admin/semesters/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "year": year,
                "specialization": specialization,
                "age_group": age_group,
                "location_id": location_id
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return True, None, result
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            return False, error_msg, None

    except requests.exceptions.RequestException as e:
        return False, f"Network error: {str(e)}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


# ============================================================================
# SEMESTER MANAGEMENT APIs
# ============================================================================

def get_all_semesters(token: str) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Fetch all semesters from the API

    Args:
        token: Admin authentication token

    Returns:
        Tuple of (success, error_message, semesters_data)
        semesters_data contains: {
            "semesters": [...],
            "total": int
        }
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/semesters/",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            return True, None, data
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            return False, error_msg, None

    except requests.exceptions.RequestException as e:
        return False, f"Network error: {str(e)}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


def update_semester(token: str, semester_id: int, update_data: dict) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Update a semester (e.g., toggle active/inactive)

    Args:
        token: Admin authentication token
        semester_id: ID of semester to update
        update_data: Dictionary with fields to update (e.g., {"is_active": True})

    Returns:
        Tuple of (success, error_message, updated_semester)
    """
    try:
        response = requests.patch(  # Use PATCH not PUT
            f"{API_BASE_URL}/api/v1/semesters/{semester_id}",
            headers={"Authorization": f"Bearer {token}"},
            json=update_data,
            timeout=30
        )

        if response.status_code == 200:
            semester = response.json()
            return True, None, semester
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            return False, error_msg, None

    except requests.exceptions.RequestException as e:
        return False, f"Network error: {str(e)}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


def delete_semester(token: str, semester_id: int) -> Tuple[bool, Optional[str]]:
    """
    Delete a semester (only if it has no sessions)

    Args:
        token: Admin authentication token
        semester_id: ID of semester to delete

    Returns:
        Tuple of (success, error_message)
    """
    try:
        response = requests.delete(
            f"{API_BASE_URL}/api/v1/semesters/{semester_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )

        if response.status_code == 200:
            return True, None
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            return False, error_msg

    except requests.exceptions.RequestException as e:
        return False, f"Network error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


# ============================================================================
# INSTRUCTOR ASSIGNMENT APIs (P1 - Not yet implemented in components)
# ============================================================================

def get_available_instructors(token: str, year: str, time_period: str) -> Tuple[bool, Optional[str], Optional[List[dict]]]:
    """
    Get available instructors for assignment

    Args:
        token: Admin authentication token
        year: Year to check availability
        time_period: Time period (e.g., "FALL", "SPRING")

    Returns:
        Tuple of (success, error_message, instructors_list)
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/instructor-assignments/available-instructors",
            headers={"Authorization": f"Bearer {token}"},
            params={"year": year, "time_period": time_period},
            timeout=30
        )

        if response.status_code == 200:
            instructors = response.json()
            return True, None, instructors
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            return False, error_msg, None

    except requests.exceptions.RequestException as e:
        return False, f"Network error: {str(e)}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None
