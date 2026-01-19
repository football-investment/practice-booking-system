"""
Session Management - SECURE VERSION
Uses ONLY Streamlit session_state (in-memory, server-side storage)
NO URL query params (security risk: token exposure in browser history/logs)

Includes token expiration validation to prevent stale session usage
"""

import streamlit as st
from typing import Dict, Any, Optional
from config import SESSION_TOKEN_KEY, SESSION_USER_KEY, SESSION_ROLE_KEY
from utils.token_validator import is_token_expired


def restore_session_from_url():
    """
    DEPRECATED - NO LONGER USED
    Previously restored session from URL query params (SECURITY RISK)
    Now a no-op for backward compatibility
    """
    # No-op: session_state is already in memory
    return SESSION_TOKEN_KEY in st.session_state


def save_session_to_url(token: str, user: Dict[str, Any]):
    """
    DEPRECATED - NO LONGER USED
    Previously saved session to URL query params (SECURITY RISK)
    Now a no-op for backward compatibility

    Session persistence relies on Streamlit's built-in session_state
    which survives page navigation within the same browser session.
    """
    # No-op: session_state already persists across page navigation
    pass


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
