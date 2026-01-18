"""
Tournament Helper Functions - API calls and utility functions for instructor tournaments
"""

import streamlit as st
import requests
from typing import Dict, List
from config import API_BASE_URL, API_TIMEOUT

def get_instructor_coach_level(token: str) -> int:
    """
    Get the instructor's highest LFA_COACH license level.

    This is a WORKAROUND: Since there's no /api/v1/user-licenses/me endpoint,
    we query the database directly using a SQL-like approach through the users endpoint.

    For now, we'll use a simpler approach: check the user's profile data
    which may include license information, or query the database directly.

    Returns:
        int: Highest coach level (1-8), or 0 if no LFA_COACH license found
    """
    try:
        # WORKAROUND: Query database directly since API endpoint doesn't exist
        # We'll need to implement this properly on the backend
        # For now, return a default based on user email for testing

        # Get current user info
        response = requests.get(
            f"{API_BASE_URL}/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            user_data = response.json()
            user_id = user_data.get('id')

            # Query database directly (temporary solution)
            import psycopg2
            conn = psycopg2.connect(
                host="localhost",
                database="lfa_intern_system",
                user="postgres",
                password="postgres",
                port=5432
            )
            cur = conn.cursor()

            # Get highest LFA_COACH license level
            cur.execute("""
                SELECT MAX(current_level)
                FROM user_licenses
                WHERE user_id = %s AND specialization_type = 'LFA_COACH'
            """, (user_id,))

            result = cur.fetchone()
            cur.close()
            conn.close()

            if result and result[0] is not None:
                level = int(result[0])
                print(f"✅ Coach level for user_id={user_id}: {level}")
                return level
            else:
                print(f"⚠️ No LFA_COACH license found for user_id={user_id}")

        print(f"⚠️ API call failed with status {response.status_code}")
        return 0
    except Exception as e:
        # Fallback: return 0 if any error occurs
        import traceback
        print(f"❌ ERROR getting coach level: {e}")
        print(f"❌ Traceback:\n{traceback.format_exc()}")
        return 0


def check_coach_level_sufficient(coach_level: int, age_group: str) -> bool:
    """
    Check if instructor's coach level is sufficient for tournament age group.

    Args:
        coach_level: Instructor's coach level (1-8)
        age_group: Tournament age group (e.g., 'PRE', 'YOUTH', 'AMATEUR', 'PRO')

    Returns:
        bool: True if level is sufficient, False otherwise
    """
    MINIMUM_COACH_LEVELS = {
        "PRE": 1,       # Level 1 (lowest)
        "YOUTH": 3,     # Level 3
        "AMATEUR": 5,   # Level 5
        "PRO": 7        # Level 7 (highest)
    }

    required_level = MINIMUM_COACH_LEVELS.get(age_group)

    # If age group not in mapping, allow (backward compatibility)
    if required_level is None:
        return True

    return coach_level >= required_level


def batch_get_application_statuses(token: str, tournament_ids: List[int]) -> Dict[int, Dict]:
    """
    Batch fetch application status for multiple tournaments.

    Args:
        token: Authentication token
        tournament_ids: List of tournament IDs to check

    Returns:
        Dictionary mapping tournament_id -> application data
        Example: {25: {"status": "PENDING", "id": 123}, 26: None}
    """
    application_map = {}

    # For each tournament, check if instructor has applied
    for tournament_id in tournament_ids:
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/my-application",
                headers={"Authorization": f"Bearer {token}"},
                timeout=API_TIMEOUT
            )
            if response.status_code == 200:
                application_map[tournament_id] = response.json()
            else:
                application_map[tournament_id] = None
        except:
            application_map[tournament_id] = None

    return application_map


def get_open_tournaments(token: str) -> List[Dict]:
    """
    Fetch tournaments with SEEKING_INSTRUCTOR status.

    Returns:
        List of tournament dictionaries
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/semesters",
            headers={"Authorization": f"Bearer {token}"},
            params={"size": 100},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            # API returns {"semesters": [...]} format
            all_semesters = data.get('semesters', data.get('items', []))

            # Filter for all tournaments with SEEKING_INSTRUCTOR status
            # Show both APPLICATION_BASED and OPEN_ASSIGNMENT
            # Apply button only shows for APPLICATION_BASED
            open_tournaments = [
                t for t in all_semesters
                if (t.get('code', '').startswith('TOURN-') and
                    t.get('status') == 'SEEKING_INSTRUCTOR')
            ]

            return open_tournaments
        else:
            return []
    except Exception as e:
        st.error(f"Error fetching tournaments: {str(e)}")
        return []


def get_my_applications(token: str) -> List[Dict]:
    """
    Fetch instructor's own tournament applications.

    Returns:
        List of application dictionaries with tournament details
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/tournaments/instructor/my-applications",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            return data.get('applications', [])
        else:
            return []
    except Exception as e:
        # Endpoint might not exist yet - return empty list
        return []


def apply_to_tournament(token: str, tournament_id: int, message: str) -> bool:
    """
    Submit an application to a tournament.

    Returns:
        True if successful, False otherwise
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/instructor-applications",
            headers={"Authorization": f"Bearer {token}"},
            json={"application_message": message},
            timeout=API_TIMEOUT
        )

        response.raise_for_status()
        return True
    except requests.exceptions.HTTPError as e:
        error_data = e.response.json() if e.response else {}
        error_message = error_data.get('error', {}).get('message', {})

        if error_message.get('error') == 'duplicate_application':
            st.error("⚠️ You have already applied to this tournament")
        elif error_message.get('error') == 'missing_coach_license':
            st.error("⚠️ You need an active LFA_COACH license to apply")
        else:
            st.error(f"Application failed: {str(e)}")
        return False
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        return False


def accept_assignment(token: str, tournament_id: int) -> bool:
    """
    Accept an approved instructor assignment.

    Returns:
        True if successful, False otherwise
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/instructor/accept",
            headers={"Authorization": f"Bearer {token}"},
            json={},  # Empty request body required by endpoint
            timeout=API_TIMEOUT
        )

        response.raise_for_status()
        return True
    except requests.exceptions.HTTPError as e:
        error_data = e.response.json() if e.response else {}
        st.error(f"Failed to accept assignment: {error_data.get('detail', str(e))}")
        return False
    except Exception as e:
        st.error(f"Accept error: {str(e)}")
        return False


# ============================================================================
# UI COMPONENTS
# ============================================================================
