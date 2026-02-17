"""
Tournament Manager — Central Role Permissions
==============================================

Single source of truth for what each role can do in the Tournament Manager.

Design principle: role capabilities are declared here ONCE.
No inline `if role == "admin":` conditions should exist in rendering code —
all branching happens through a `TournamentManagerPermissions` instance.

Usage:
    from .tournament_manager_permissions import get_permissions, ALLOWED_ROLES

    perms = get_permissions(user_role)
    if perms is None:
        st.error("Access denied.")
        st.stop()

    render_tournament_manager(token, perms)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TournamentManagerPermissions:
    """Immutable capability set for a single role in the Tournament Manager."""

    role: str
    """Canonical lowercase role string (e.g. "admin", "instructor")."""

    can_create: bool
    """May use the OPS Wizard to launch new tournaments."""

    can_enter_results: bool
    """May submit manual match results."""

    can_finalize: bool
    """May trigger finalize-tournament and distribute-rewards API calls."""

    dashboard_back_page: str
    """st.switch_page() target for the '← Dashboard' sidebar button."""

    display_name: str
    """Human-readable label shown in the sidebar (e.g. "Admin", "Instructor")."""


# ── Role definitions ──────────────────────────────────────────────────────────

_ROLE_PERMISSIONS: dict[str, TournamentManagerPermissions] = {
    "admin": TournamentManagerPermissions(
        role="admin",
        can_create=True,
        can_enter_results=True,
        can_finalize=True,
        dashboard_back_page="pages/Admin_Dashboard.py",
        display_name="Admin",
    ),
    "instructor": TournamentManagerPermissions(
        role="instructor",
        can_create=False,
        can_enter_results=True,
        can_finalize=False,
        dashboard_back_page="pages/Instructor_Dashboard.py",
        display_name="Instructor",
    ),
}

ALLOWED_ROLES: frozenset = frozenset(_ROLE_PERMISSIONS)
"""Set of role strings that are permitted to access the Tournament Manager."""


def get_permissions(role: str) -> TournamentManagerPermissions | None:
    """Return the permission set for *role*, or None if the role is not allowed.

    Args:
        role: Raw role string from session state (case-insensitive).

    Returns:
        TournamentManagerPermissions if the role is permitted, None otherwise.
    """
    return _ROLE_PERMISSIONS.get(role.lower()) if role else None
