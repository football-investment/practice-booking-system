"""
Instructor Dashboard — Tab 6: Inbox
=====================================

Phase 3 extraction Step 3.2.
Delegates entirely to the universal inbox component.

Public API:
    render_inbox_tab(token, user)
"""

from __future__ import annotations

from typing import Dict, Any

from components.instructor.tournament_applications import render_my_applications_tab


def render_inbox_tab(token: str, user: Dict[str, Any]) -> None:
    """Render the 'Inbox' tab content.

    Args:
        token: Bearer JWT for the authenticated instructor.
        user:  Session user dict.
    """
    render_my_applications_tab(token, user)
