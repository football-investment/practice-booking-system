"""
Session Management - ENVIRONMENT-AWARE VERSION
- PRODUCTION: Uses ONLY Streamlit session_state (secure, no URL params)
- DEVELOPMENT/TEST: Uses URL query params for E2E test compatibility

Includes token expiration validation to prevent stale session usage
"""

import streamlit as st
import json
from typing import Dict, Any, Optional
from config import SESSION_TOKEN_KEY, SESSION_USER_KEY, SESSION_ROLE_KEY, ENVIRONMENT
from utils.token_validator import is_token_expired


def restore_session_from_url():
    """
    Restore session from URL query params (DEVELOPMENT/TEST ONLY)

    In production: No-op (secure, session_state only)
    In development/test: Restores from URL for E2E test compatibility
    """
    # Production: secure mode (no URL params)
    if ENVIRONMENT == "production":
        return SESSION_TOKEN_KEY in st.session_state

    # Development/Test: allow URL params for E2E tests

    if SESSION_TOKEN_KEY in st.query_params:
        token = st.query_params[SESSION_TOKEN_KEY]
        user_json = st.query_params.get(SESSION_USER_KEY, "{}")

        try:
            user = json.loads(user_json)

            # Restore to session_state
            st.session_state[SESSION_TOKEN_KEY] = token
            st.session_state[SESSION_USER_KEY] = user
            st.session_state[SESSION_ROLE_KEY] = user.get('role', 'student')

            return True
        except Exception:
            return False

    return SESSION_TOKEN_KEY in st.session_state


def save_session_to_url(token: str, user: Dict[str, Any]):
    """
    Save session to URL query params (DEVELOPMENT/TEST ONLY)

    In production: No-op (secure, session_state only)
    In development/test: Saves to URL for E2E test compatibility

    Session persistence relies on Streamlit's built-in session_state
    which survives page navigation within the same browser session.
    """
    # Production: secure mode (no URL params)
    if ENVIRONMENT == "production":
        return

    # Development/Test: save to URL params for E2E tests
    st.query_params[SESSION_TOKEN_KEY] = token
    st.query_params[SESSION_USER_KEY] = json.dumps(user)


def clear_session():
    """Clear session from session_state"""
    # Clear session_state (in-memory only)
    st.session_state.clear()

    # Clear any legacy query params if they exist
    try:
        if 'session_token' in st.query_params:
            del st.query_params['session_token']
        if 'session_user' in st.query_params:
            del st.query_params['session_user']
    except:
        pass


def validate_session() -> bool:
    """
    Validate current session and check token expiration

    Returns:
        True if session is valid, False otherwise

    Side effects:
        - Clears session and shows warning if token is expired
        - Redirects to login page if session invalid
    """
    # Check if session exists
    if SESSION_TOKEN_KEY not in st.session_state:
        return False

    token = st.session_state.get(SESSION_TOKEN_KEY)

    # Validate token expiration
    if is_token_expired(token):
        # Clear expired session
        clear_session()

        # Show warning
        st.warning("⚠️ Your session has expired. Please log in again.")
        st.stop()

        return False

    return True


def require_authentication():
    """
    Require valid authentication for current page
    Redirects to login if not authenticated or token expired

    Usage:
        # At top of protected pages
        require_authentication()
    """
    if not validate_session():
        st.switch_page("🏠_Home.py")
