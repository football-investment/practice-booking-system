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

# Import directly from the module file.
# IMPORTANT: module name must be the full dotted path so that relative imports
# inside tournament_monitor.py (e.g. `from .tournament_card.leaderboard`) can
# resolve their parent package correctly.  Without this, Python's import system
# has no way to walk up the package hierarchy and the relative import fails with
# "attempted relative import with no known parent package".
import importlib.util as _ilu
import types as _types

def _load_component(dotted_name: str, file_path: Path):
    """Load a component module preserving package context for relative imports."""
    parts = dotted_name.rsplit(".", 1)
    parent_pkg = parts[0] if len(parts) > 1 else None

    # Ensure every ancestor package is present in sys.modules so that
    # relative imports inside the loaded module can walk upwards.
    if parent_pkg:
        pkg_parts = parent_pkg.split(".")
        for i in range(len(pkg_parts)):
            pkg_name = ".".join(pkg_parts[: i + 1])
            if pkg_name not in sys.modules:
                pkg_path = Path(__file__).parent.parent.joinpath(*pkg_parts[: i + 1])
                pkg_mod = _types.ModuleType(pkg_name)
                pkg_mod.__path__ = [str(pkg_path)]
                pkg_mod.__package__ = pkg_name
                sys.modules[pkg_name] = pkg_mod

    spec = _ilu.spec_from_file_location(dotted_name, file_path)
    mod = _ilu.module_from_spec(spec)
    mod.__package__ = parent_pkg or dotted_name
    sys.modules[dotted_name] = mod
    spec.loader.exec_module(mod)
    return mod

_mod = _load_component(
    "components.admin.tournament_monitor",
    Path(__file__).parent.parent / "components" / "admin" / "tournament_monitor.py",
)
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
