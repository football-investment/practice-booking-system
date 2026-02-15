"""
Tournament Monitor — Real-Time Admin View
==========================================
Standalone Streamlit page that renders live tournament status for admins.

Navigation: Admin Dashboard sidebar → Tournament Monitor
Direct URL: /Tournament_Monitor
"""

import sys
from pathlib import Path

# Ensure the streamlit_app directory is on the path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

import streamlit as st

from config import PAGE_TITLE, PAGE_ICON, LAYOUT, CUSTOM_CSS, SESSION_TOKEN_KEY, SESSION_USER_KEY
from session_manager import restore_session_from_url, clear_session

# Import directly from the module file to avoid __init__.py pulling in heavy
# dependencies (tournament_list → streamlit_components) that are not needed here.
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "tournament_monitor",
    Path(__file__).parent.parent / "components" / "admin" / "tournament_monitor.py",
)
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
render_tournament_monitor = _mod.render_tournament_monitor


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title=f"{PAGE_TITLE} - Tournament Monitor",
    page_icon="📡",
    layout=LAYOUT,
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ── Auth ──────────────────────────────────────────────────────────────────────

if SESSION_TOKEN_KEY not in st.session_state:
    restore_session_from_url()

if SESSION_TOKEN_KEY not in st.session_state or SESSION_USER_KEY not in st.session_state:
    st.error("Not authenticated. Please login first.")
    st.markdown("[Go to Login](http://localhost:8505)")
    st.stop()

user = st.session_state[SESSION_USER_KEY]
if user.get("role", "").lower() != "admin":
    st.error("Access denied. Admin role required.")
    st.stop()

token = st.session_state[SESSION_TOKEN_KEY]

# ── Sidebar navigation ────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(f"### Welcome, {user.get('name', 'Admin')}!")
    st.caption(f"Role: **Admin**")
    st.markdown("---")
    if st.button("← Admin Dashboard", use_container_width=True):
        st.switch_page("pages/Admin_Dashboard.py")
    if st.button("🚪 Logout", use_container_width=True):
        clear_session()
        st.switch_page("🏠_Home.py")
    st.markdown("---")

# ── Page header ───────────────────────────────────────────────────────────────

st.title("📡 Tournament Monitor")
st.caption("Real-time view of active tournaments across all campuses")

st.divider()

# ── Main component ────────────────────────────────────────────────────────────

render_tournament_monitor(token)
