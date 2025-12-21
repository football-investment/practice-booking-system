"""
Session Persistence - SIMPLIFIED VERSION
Uses Streamlit session_state + query params (no complex localStorage JS)
"""

import streamlit as st
import json
from typing import Dict, Any
from config import SESSION_TOKEN_KEY, SESSION_USER_KEY, SESSION_ROLE_KEY


def restore_session_from_url():
    """
    Restore session from URL query params
    This is called on every page load
    """
    query_params = st.query_params

    if 'session_token' in query_params and 'session_user' in query_params:
        try:
            token = query_params['session_token']
            user_json = query_params['session_user']

            # Parse user JSON
            user = json.loads(user_json) if isinstance(user_json, str) else user_json

            # Restore to session_state
            st.session_state[SESSION_TOKEN_KEY] = token
            st.session_state[SESSION_USER_KEY] = user
            st.session_state[SESSION_ROLE_KEY] = user.get('role', 'student')

            return True
        except Exception as e:
            return False

    return False


def save_session_to_url(token: str, user: Dict[str, Any]):
    """
    Save session to URL query params
    This persists the session across page refreshes
    """
    try:
        # Set query params
        st.query_params['session_token'] = token
        st.query_params['session_user'] = json.dumps(user)
    except Exception as e:
        pass


def clear_session():
    """Clear session from both session_state and query params"""
    # Clear session_state
    st.session_state.clear()

    # Clear query params
    try:
        st.query_params.clear()
    except:
        pass
