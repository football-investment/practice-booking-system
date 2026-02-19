"""
Tournament Manager — Unified Admin & Instructor View
======================================================
Role-aware tournament management page:

  - ADMIN      : Full OPS Wizard (create) + live monitoring + result entry + finalization
  - INSTRUCTOR : Live monitoring + result entry only (no creation, no finalization)

Navigation:
  Admin:      Admin Dashboard → Tournament Manager
  Instructor: Instructor Dashboard → Tournament Manager
  Direct URL: /Tournament_Manager
"""

import sys
from pathlib import Path

# ── Robust sys.path setup ────────────────────────────────────────────────────
_app_root = str(Path(__file__).parent.parent.resolve())
sys.path = [
    p for p in sys.path
    if not (p.endswith(("/components", "/components/admin", "/components/admin/ops_wizard",
                        "/components/admin/tournament_card")))
]
if _app_root not in sys.path:
    sys.path.insert(0, _app_root)
import importlib
for _mod in [k for k in sys.modules if k.startswith("components")]:
    _m = sys.modules.get(_mod)
    if _m and getattr(_m, "__file__", None) is None:
        del sys.modules[_mod]
del importlib

import streamlit as st

from config import (
    PAGE_TITLE, PAGE_ICON, LAYOUT, CUSTOM_CSS,
    SESSION_TOKEN_KEY, SESSION_USER_KEY, SESSION_ROLE_KEY,
)
from session_manager import restore_session_from_url, clear_session

# ── Component loader (preserves package context for relative imports) ─────────

import importlib.util as _ilu
import types as _types


def _load_component(dotted_name: str, file_path: Path):
    """Load a component module preserving package context for relative imports."""
    parts = dotted_name.rsplit(".", 1)
    parent_pkg = parts[0] if len(parts) > 1 else None

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
render_tournament_manager = _mod.render_tournament_manager

_perms_mod = _load_component(
    "components.admin.tournament_manager_permissions",
    Path(__file__).parent.parent / "components" / "admin" / "tournament_manager_permissions.py",
)
get_permissions = _perms_mod.get_permissions
ALLOWED_ROLES = _perms_mod.ALLOWED_ROLES


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title=f"{PAGE_TITLE} - Tournament Manager",
    page_icon="🏆",
    layout=LAYOUT,
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ── Auth & role gate ──────────────────────────────────────────────────────────

if SESSION_TOKEN_KEY not in st.session_state:
    restore_session_from_url()

if SESSION_TOKEN_KEY not in st.session_state or SESSION_USER_KEY not in st.session_state:
    st.error("Not authenticated. Please login first.")
    st.markdown("[Go to Login](http://localhost:8505)")
    st.stop()

user = st.session_state[SESSION_USER_KEY]
role = (user.get("role") or st.session_state.get(SESSION_ROLE_KEY) or "").lower()

perms = get_permissions(role)
if perms is None:
    st.error(f"Access denied. This page requires one of: {', '.join(sorted(ALLOWED_ROLES))}.")
    st.stop()

token = st.session_state[SESSION_TOKEN_KEY]


# ── Sidebar navigation ────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(f"### Welcome, {user.get('name', perms.display_name)}!")
    st.caption(f"Role: **{perms.display_name}**")
    st.markdown("---")
    if st.button(f"← {perms.display_name} Dashboard", use_container_width=True):
        st.switch_page(perms.dashboard_back_page)
    if st.button("🚪 Logout", use_container_width=True):
        clear_session()
        st.switch_page("🏠_Home.py")
    st.markdown("---")


# ── Page header ───────────────────────────────────────────────────────────────

_icon = "📡" if perms.can_create else "🏆"
_subtitle = (
    "OPS Test Observability Platform — create, launch, and monitor test tournaments"
    if perms.can_create
    else "Live monitoring and result entry for your assigned tournaments"
)
st.title(f"{_icon} Tournament Manager")
st.caption(_subtitle)
st.divider()


# ── Main component ────────────────────────────────────────────────────────────

render_tournament_manager(token, perms)
