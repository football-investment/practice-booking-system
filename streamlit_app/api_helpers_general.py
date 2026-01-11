"""
API Helper Functions
EXACT PATTERNS from unified_workflow_dashboard.py (WORKING!)
"""

import streamlit as st
import requests
import time
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
        # Build params dict - only include specialization_filter if False (to override backend default of True)
        params = {"size": size}
        if not specialization_filter:
            params["specialization_filter"] = "false"  # Pass as string "false" for FastAPI to parse

        response = requests.get(
            f"{API_BASE_URL}/api/v1/sessions/",  # ✅ Added trailing slash for refactored backend
            headers={"Authorization": f"Bearer {token}"},
            params=params,
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
        # Cache-busting: Add timestamp parameter to force fresh data
        cache_buster = int(time.time() * 1000)  # milliseconds timestamp

        response = requests.get(
            f"{API_BASE_URL}/api/v1/semesters/?_={cache_buster}",  # ✅ Cache-busting parameter
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
    """
    Update user profile (self-service)

    ✅ CORRECT: Uses PATCH /api/v1/users/me (not PUT /api/v1/users/{user_id})
    The user_id parameter is kept for backward compatibility but ignored.
    """
    try:
        response = requests.patch(  # ✅ CHANGED: PUT → PATCH
            f"{API_BASE_URL}/api/v1/users/me",  # ✅ CHANGED: /{user_id} → /me
            headers={"Authorization": f"Bearer {token}"},
            json=data,
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            try:
                error_msg = response.json().get('detail', f'HTTP {response.status_code}')
            except:
                error_msg = f'HTTP {response.status_code}'
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


def create_campus(token: str, location_id: int, data: Dict) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """Create new campus within a location"""
    try:
        url = f"{API_BASE_URL}/api/v1/admin/locations/{location_id}/campuses"
        response = requests.post(url, json=data, headers={"Authorization": f"Bearer {token}"}, timeout=10)

        if response.status_code == 201:
            return True, None, response.json()
        else:
            error_msg = response.json().get("detail", "Failed to create campus")
            return False, error_msg, None
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}", None


def toggle_campus_status(token: str, campus_id: int, is_active: bool) -> Tuple[bool, Optional[str]]:
    """Activate/Deactivate campus"""
    success, error, _ = update_campus(token, campus_id, {"is_active": is_active})
    return success, error


# ============================================================================
# SPECIALIZATION MANAGEMENT (FOR STUDENT HUB)
# ============================================================================

def unlock_specialization(token: str, specialization: str) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Unlock a specialization (costs 100 credits)

    Args:
        token: Authentication token
        specialization: Specialization type (e.g., "LFA_PLAYER", "INTERNSHIP", etc.)

    Returns:
        Tuple of (success, error_message, response_data)
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/specialization/unlock",
            headers={"Authorization": f"Bearer {token}"},
            data={"specialization": specialization},  # Form data, not JSON
            timeout=API_TIMEOUT
        )

        if response.status_code == 200 or response.status_code == 303:
            # Success - returns redirect, but we just need to know it worked
            return True, None, {"message": "Specialization unlocked successfully"}
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get('detail', f'HTTP {response.status_code}')
            except:
                error_msg = f'HTTP {response.status_code}'
            return False, error_msg, None
    except Exception as e:
        return False, str(e), None


def submit_lfa_player_onboarding(
    token: str,
    date_of_birth,  # ✅ NEW: date object or None
    position: str,
    skills: dict,
    goals: str,
    motivation: str
) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Submit LFA Player onboarding form

    Args:
        token: Authentication token
        date_of_birth: Date object (from st.date_input) - will be converted to ISO string
        position: STRIKER, MIDFIELDER, DEFENDER, GOALKEEPER
        skills: Dict with {heading, shooting, passing, dribbling, defending, physical}
        goals: Goals dropdown value
        motivation: Motivation text

    Returns:
        Tuple of (success, error_message, response_data)
    """
    try:
        # Prepare form data
        form_data = {
            "position": position,
            "skill_heading": skills['heading'],
            "skill_shooting": skills['shooting'],
            "skill_passing": skills['passing'],
            "skill_dribbling": skills['dribbling'],
            "skill_defending": skills['defending'],
            "skill_physical": skills['physical'],
            "goals": goals,
            "motivation": motivation
        }

        # ✅ NEW: Add date_of_birth if provided (convert to ISO string YYYY-MM-DD)
        if date_of_birth:
            form_data["date_of_birth"] = date_of_birth.isoformat()

        response = requests.post(
            f"{API_BASE_URL}/specialization/lfa-player/onboarding-submit",
            headers={"Authorization": f"Bearer {token}"},
            data=form_data,
            timeout=API_TIMEOUT,
            allow_redirects=False  # Don't follow redirects to /dashboard
        )

        if response.status_code in [200, 303]:
            return True, None, {"message": "Onboarding completed successfully"}
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get('detail', f'HTTP {response.status_code}')
            except:
                error_msg = f'HTTP {response.status_code}'
            return False, error_msg, None
    except Exception as e:
        return False, str(e), None


# ============================================================================
# PASSWORD RESET (ADMIN FUNCTION)
# ============================================================================

def reset_user_password(token: str, user_id: int, new_password: str) -> Tuple[bool, Optional[str]]:
    """
    Reset user password (Admin only)

    Args:
        token: Admin authentication token
        user_id: ID of user whose password to reset
        new_password: New password to set

    Returns:
        Tuple of (success, error_message)
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/users/{user_id}/reset-password",
            headers={"Authorization": f"Bearer {token}"},
            json={"new_password": new_password},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get('detail', f'HTTP {response.status_code}')
            except:
                error_msg = f'HTTP {response.status_code}'
            return False, error_msg
    except Exception as e:
        return False, str(e)


# ============================================================================
# CREDIT PURCHASE & INVOICE MANAGEMENT
# ============================================================================

def request_invoice(token: str, credit_amount: int, amount_eur: float, coupon_code: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Request invoice for credit purchase

    Args:
        token: Authentication token
        credit_amount: Number of credits to purchase
        amount_eur: Price in EUR
        coupon_code: Optional coupon code for discount

    Returns:
        Tuple of (success, error_message, response_data)
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/invoices/request",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "credit_amount": credit_amount,
                "amount_eur": amount_eur,
                "coupon_code": coupon_code  # ✅ Dynamic, not hardcoded None
            },
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get('detail', f'HTTP {response.status_code}')
            except:
                error_msg = f'HTTP {response.status_code}'
            return False, error_msg, None
    except Exception as e:
        return False, str(e), None


def list_pending_invoices(token: str, status: str = "pending") -> Tuple[bool, list]:
    """
    Get list of invoices (admin only)

    Args:
        token: Admin authentication token
        status: Invoice status filter (default: "pending")

    Returns:
        Tuple of (success, invoices_list)
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/invoices/list",
            headers={"Authorization": f"Bearer {token}"},
            params={"status": status, "limit": 50},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, response.json()
        else:
            return False, []
    except Exception as e:
        return False, []


def verify_invoice(token: str, invoice_id: int) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Verify invoice payment and add credits (admin only)

    Args:
        token: Admin authentication token
        invoice_id: ID of invoice to verify

    Returns:
        Tuple of (success, error_message, response_data)
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/invoices/{invoice_id}/verify",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None, response.json()
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get('detail', f'HTTP {response.status_code}')
            except:
                error_msg = f'HTTP {response.status_code}'
            return False, error_msg, None
    except Exception as e:
        return False, str(e), None


# ============================================================================
# STUDENT CREDIT & TRANSACTION MANAGEMENT
# ============================================================================

def get_credit_transactions(token: str, limit: int = 50, offset: int = 0) -> Tuple[bool, Optional[dict]]:
    """
    Get user's credit transaction history

    Args:
        token: Authentication token
        limit: Number of transactions to fetch (default 50, max 200)
        offset: Pagination offset (default 0)

    Returns:
        Tuple of (success, response_data)
        response_data includes: {transactions: [], total_count: int, credit_balance: int, ...}
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/users/me/credit-transactions",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": limit, "offset": offset},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, response.json()
        else:
            return False, None
    except Exception as e:
        return False, None


def get_my_invoices(token: str) -> Tuple[bool, Optional[list]]:
    """
    Get current user's invoice requests

    Args:
        token: Authentication token

    Returns:
        Tuple of (success, invoices_list)
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/invoices/my-invoices",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, response.json()
        else:
            return False, []
    except Exception as e:
        return False, []
