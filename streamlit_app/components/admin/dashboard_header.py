"""
Admin Dashboard Header Component
Handles page configuration, authentication, header, and sidebar
"""

import streamlit as st
from pathlib import Path
import sys

# Setup imports
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from config import PAGE_TITLE, PAGE_ICON, LAYOUT, CUSTOM_CSS, SESSION_TOKEN_KEY, SESSION_USER_KEY, SESSION_ROLE_KEY
from session_manager import restore_session_from_url, clear_session


def render_dashboard_header():
    """
    Render dashboard header, authentication, and sidebar.
    Returns (token, user) tuple for authenticated admin user.
    """

    # Page configuration
    st.set_page_config(
        page_title=f"{PAGE_TITLE} - Admin Dashboard",
        page_icon=PAGE_ICON,
        layout=LAYOUT
    )

    # Apply CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # SIMPLIFIED SESSION PERSISTENCE: Restore from URL params
    if SESSION_TOKEN_KEY not in st.session_state:
        restore_session_from_url()

    # Check authentication
    if SESSION_TOKEN_KEY not in st.session_state or SESSION_USER_KEY not in st.session_state:
        st.error("❌ Not authenticated. Please login first.")
        st.info("💡 **How to login:** Go to Home page and use your credentials.")

        st.markdown("---")
        st.markdown("### Quick Access:")
        st.markdown("1. Click **'🔑 Go to Login'** button below")
        st.markdown("2. Enter your **email** and **password**")
        st.markdown("3. You'll be automatically redirected here")

        # CRITICAL FIX: Redirect to login page (Home is in root, not pages/)
        st.markdown("### 🔗 [Click here to go to Login Page](http://localhost:8505)")

        st.markdown("---")
        st.code("http://localhost:8505", language=None)
        st.caption("Copy-paste this URL to your browser if the link doesn't work")

        st.stop()

    # Check admin role
    user = st.session_state[SESSION_USER_KEY]
    if user.get('role') != 'admin':
        st.error("❌ Access denied. Admin role required.")
        st.stop()

    # Get token
    token = st.session_state[SESSION_TOKEN_KEY]

    # Header
    st.title("📊 Admin Dashboard")
    st.caption("LFA Education Center - Complete Admin Interface")

    # Sidebar
    with st.sidebar:
        st.markdown(f"### Welcome, {user.get('name', 'Admin')}!")
        st.caption(f"Role: **Admin**")
        st.caption(f"Email: {user.get('email', 'N/A')}")

        st.markdown("---")

        # REFRESH BUTTON - Keep session alive without re-login
        if st.button("🔄 Refresh Page", use_container_width=True, type="secondary"):
            st.rerun()

        if st.button("🚪 Logout", use_container_width=True):
            # Clear session (both session_state and query params)
            clear_session()
            st.switch_page("🏠_Home.py")

    # Initialize active_tab in session state if not present
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = 'overview'

    # Tab selection (MOVED BEFORE columns for full width)
    tab_col1, tab_col2, tab_col3, tab_col4, tab_col5, tab_col6, tab_col7 = st.columns(7)

    with tab_col1:
        if st.button("📊 Overview", use_container_width=True, type="primary" if st.session_state.active_tab == 'overview' else "secondary"):
            st.session_state.active_tab = 'overview'
            st.rerun()

    with tab_col2:
        if st.button("👥 Users", use_container_width=True, type="primary" if st.session_state.active_tab == 'users' else "secondary"):
            st.session_state.active_tab = 'users'
            st.rerun()

    with tab_col3:
        if st.button("📅 Sessions", use_container_width=True, type="primary" if st.session_state.active_tab == 'sessions' else "secondary"):
            st.session_state.active_tab = 'sessions'
            st.rerun()

    with tab_col4:
        if st.button("📍 Locations", use_container_width=True, type="primary" if st.session_state.active_tab == 'locations' else "secondary"):
            st.session_state.active_tab = 'locations'
            st.rerun()

    with tab_col5:
        if st.button("💳 Financial", use_container_width=True, type="primary" if st.session_state.active_tab == 'financial' else "secondary"):
            st.session_state.active_tab = 'financial'
            st.rerun()

    with tab_col6:
        if st.button("📅 Semesters", use_container_width=True, type="primary" if st.session_state.active_tab == 'semesters' else "secondary"):
            st.session_state.active_tab = 'semesters'
            st.rerun()

    with tab_col7:
        if st.button("🏆 Tournaments", use_container_width=True, type="primary" if st.session_state.active_tab == 'tournaments' else "secondary"):
            st.session_state.active_tab = 'tournaments'
            st.rerun()

    st.divider()

    return token, user
