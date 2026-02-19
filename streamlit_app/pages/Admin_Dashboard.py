"""
Admin Dashboard - REFACTORED MODULAR ARCHITECTURE
Clean, reusable components for session, user, location, and financial management
"""

import sys
from pathlib import Path

# ── Robust sys.path setup ────────────────────────────────────────────────────
# streamlit_app/ is two levels above this file (pages/Admin_Dashboard.py)
_app_root = str(Path(__file__).parent.parent.resolve())
# Remove any stale entries that point INSIDE components/ (namespace package trap)
sys.path = [
    p for p in sys.path
    if not (p.endswith(("/components", "/components/admin", "/components/admin/ops_wizard",
                        "/components/admin/tournament_card")))
]
# Ensure streamlit_app/ is at the front exactly once
if _app_root not in sys.path:
    sys.path.insert(0, _app_root)
# Force-reload components.admin if it was cached as a namespace package
import importlib
for _mod in [k for k in sys.modules if k.startswith("components")]:
    _m = sys.modules.get(_mod)
    if _m and getattr(_m, "__file__", None) is None:
        del sys.modules[_mod]
del importlib

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
    render_system_events_tab,
    render_game_presets_tab,
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
elif st.session_state.active_tab == 'system_events':
    render_system_events_tab(token, user)
elif st.session_state.active_tab == 'game_presets':
    render_game_presets_tab(token, user)
else:
    st.error(f"Unknown tab: {st.session_state.active_tab}")
