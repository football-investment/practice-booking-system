"""
Admin Dashboard - REFACTORED MODULAR ARCHITECTURE
Clean, reusable components for session, user, location, and financial management
"""

import sys
from pathlib import Path

# Add parent directory to path to import config and other modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

import streamlit as st
from components.admin import (
    render_dashboard_header,
    render_overview_tab,
    render_users_tab,
    render_sessions_tab,
    render_locations_tab,
    render_financial_tab,
    render_semesters_tab,
    render_tournaments_tab,
)


# ========================================
# MAIN APPLICATION
# ========================================

# Render header (handles auth check, sidebar, tab selector)
# Returns (token, user) for authenticated admin
token, user = render_dashboard_header()

# Create main layout with filter column
filter_col, main_col = st.columns([1, 3])

# Render active tab based on session state
if st.session_state.active_tab == 'overview':
    render_overview_tab(token, user)
elif st.session_state.active_tab == 'users':
    render_users_tab(token, user)
elif st.session_state.active_tab == 'sessions':
    render_sessions_tab(token, user)
elif st.session_state.active_tab == 'locations':
    render_locations_tab(token, user)
elif st.session_state.active_tab == 'financial':
    render_financial_tab(token, user)
elif st.session_state.active_tab == 'semesters':
    render_semesters_tab(token, user)
elif st.session_state.active_tab == 'tournaments':
    render_tournaments_tab(token, user)
else:
    st.error(f"Unknown tab: {st.session_state.active_tab}")
