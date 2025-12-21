"""
API Helper Functions for Invitation Code Management
Cookie-based authentication for web interface
"""

import requests
from typing import Tuple, Optional, List, Dict
from datetime import datetime, timedelta

API_BASE_URL = "http://localhost:8000"
API_TIMEOUT = 30


def get_invitation_codes(token: str) -> Tuple[bool, Optional[List[Dict]]]:
    """
    Get all invitation codes (Admin only)
    Returns: (success, codes_list)
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/admin/invitation-codes",
            cookies={"access_token": token},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, response.json()
        else:
            return False, None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching invitation codes: {e}")
        return False, None


def create_invitation_code(
    token: str,
    description: str,
    bonus_credits: int,
    expires_hours: Optional[int] = None,
    notes: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Create a new invitation code

    Args:
        token: Admin auth token
        description: Internal description (stored in invited_name)
        bonus_credits: Credits to give on registration
        expires_hours: Hours until expiration (None = never expires)
        notes: Optional admin notes

    Returns: (success, error_message, generated_code)
    """
    try:
        # Calculate expiration if specified
        expires_at = None
        if expires_hours and expires_hours > 0:
            expires_at = (datetime.now() + timedelta(hours=expires_hours)).isoformat()

        payload = {
            "invited_name": description,
            "invited_email": None,  # No email restriction - anyone can use
            "bonus_credits": bonus_credits,
            "expires_at": expires_at,
            "notes": notes
        }

        response = requests.post(
            f"{API_BASE_URL}/api/v1/admin/invitation-codes",
            cookies={"access_token": token},
            json=payload,
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            return True, None, data.get("code")
        else:
            # Better error handling
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg = error_data["error"].get("message", f"HTTP {response.status_code}")
                else:
                    error_msg = error_data.get("detail", f"HTTP {response.status_code}")
            except:
                error_msg = f"HTTP {response.status_code}: {response.text[:100]}"

            print(f"[ERROR] Create invitation failed: {error_msg}")
            print(f"[DEBUG] Response: {response.text[:200]}")
            return False, error_msg, None

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Request exception: {str(e)}")
        return False, str(e), None


def delete_invitation_code(token: str, code_id: int) -> Tuple[bool, Optional[str]]:
    """
    Delete an invitation code (only if not used)
    Returns: (success, error_message)
    """
    try:
        response = requests.delete(
            f"{API_BASE_URL}/api/v1/admin/invitation-codes/{code_id}",
            cookies={"access_token": token},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return True, None
        else:
            error_msg = response.json().get("detail", "Unknown error")
            return False, error_msg

    except requests.exceptions.RequestException as e:
        return False, str(e)
