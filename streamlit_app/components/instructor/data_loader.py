"""
Instructor Dashboard — Shared Data Loader
==========================================

Phase 3 contract file.  Defines the DashboardData dataclass that will be the
single shared state object passed to all tab-rendering functions once
Instructor_Dashboard.py is modularised (ARCHITECTURE.md §Phase 3, Step 3.4).

Current status (pre-extraction):
    - DashboardData is defined here as the authoritative contract.
    - load_dashboard_data() is a stub — not yet called by the monolith.
    - Extraction order: data_loader is Step 3.4 (after low-risk tabs 3.1–3.3).

Usage (target — post-Phase 3):
    from components.instructor.data_loader import load_dashboard_data

    data = load_dashboard_data(token)
    render_today_tab(data)
    render_jobs_tab(token, user, data)
    ...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# DashboardData — authoritative contract
# ---------------------------------------------------------------------------

@dataclass
class DashboardData:
    """
    Immutable snapshot of all data needed by the Instructor Dashboard tabs.

    Populated once per page load by load_dashboard_data(); passed to each
    tab-rendering function.  Tabs must NOT mutate this object — any write-back
    (e.g. recording attendance) goes through direct API calls.

    Fields mirror the data-prep block in Instructor_Dashboard.py (lines ~163–214).
    """

    # ── Raw API responses ────────────────────────────────────────────────────

    all_sessions: List[Dict] = field(default_factory=list)
    """All sessions returned by GET /api/v1/sessions (instructor filter applied)."""

    all_semesters: List[Dict] = field(default_factory=list)
    """All semesters / master-led seasons from GET /api/v1/semesters."""

    # ── Derived groupings ────────────────────────────────────────────────────

    seasons_sessions: List[Dict] = field(default_factory=list)
    """Sessions belonging to season semesters (code does NOT start with 'TOURN-')."""

    tournament_sessions: List[Dict] = field(default_factory=list)
    """Sessions belonging to tournament semesters (code starts with 'TOURN-')."""

    seasons_by_semester: Dict[int, List[Dict]] = field(default_factory=dict)
    """seasons_sessions grouped by semester_id.  Used by tab2_jobs."""

    tournaments_by_semester: Dict[int, List[Dict]] = field(default_factory=dict)
    """tournament_sessions grouped by semester_id.  Used by tab3_tournaments."""

    # ── Time-filtered views ──────────────────────────────────────────────────

    upcoming_sessions: List[Dict] = field(default_factory=list)
    """Sessions whose date_start is in [today, today+7 days].  Sorted ascending."""

    todays_sessions: List[Dict] = field(default_factory=list)
    """Subset of upcoming_sessions where date_start.date() == today."""

    # ── Metadata ─────────────────────────────────────────────────────────────

    load_error: Optional[str] = None
    """Non-None when the primary session fetch failed; tab UX should surface this."""

    fetched_at: Optional[datetime] = None
    """Timestamp of the data fetch.  Useful for staleness checks."""


# ---------------------------------------------------------------------------
# load_dashboard_data — stub (Phase 3 Step 3.4)
# ---------------------------------------------------------------------------

def load_dashboard_data(token: str) -> DashboardData:
    """
    Fetch and pre-process all data needed by the Instructor Dashboard.

    STUB: This function is not yet called by the monolith.  It will replace
    the inline data-prep block in Instructor_Dashboard.py at Phase 3 Step 3.4.

    Implementation notes:
    - Uses api_helpers.get_sessions() and get_semesters() (existing helpers).
    - Replicates the grouping logic from Instructor_Dashboard.py lines ~179–214.
    - Returns a DashboardData with load_error set if the session fetch fails,
      so callers can render an appropriate error without st.stop().

    Args:
        token: Bearer JWT for the authenticated instructor.

    Returns:
        DashboardData populated from the API responses.
    """
    # Import here to avoid circular import when the module is loaded at package init
    from collections import defaultdict

    try:
        from api_helpers import get_sessions, get_semesters
    except ImportError:
        # Allow the module to be imported in test contexts without the full app path
        return DashboardData(load_error="api_helpers not available in this context")

    # ── Fetch ────────────────────────────────────────────────────────────────
    success, all_sessions = get_sessions(token, size=100, specialization_filter=True)
    if not success:
        return DashboardData(load_error="Failed to load sessions. Please refresh the page.")

    semester_success, all_semesters = get_semesters(token)
    if not semester_success:
        all_semesters = []

    # ── Partition ────────────────────────────────────────────────────────────
    seasons_sessions = [
        s for s in all_sessions
        if not s.get("semester", {}).get("code", "").startswith("TOURN-")
    ]
    tournament_sessions = [
        s for s in all_sessions
        if s.get("semester", {}).get("code", "").startswith("TOURN-")
    ]

    seasons_by_semester: Dict[int, List[Dict]] = defaultdict(list)
    for s in seasons_sessions:
        sid = s.get("semester_id")
        if sid:
            seasons_by_semester[sid].append(s)

    tournaments_by_semester: Dict[int, List[Dict]] = defaultdict(list)
    for t in tournament_sessions:
        sid = t.get("semester_id")
        if sid:
            tournaments_by_semester[sid].append(t)

    # ── Time windows ─────────────────────────────────────────────────────────
    today    = datetime.now().date()
    next_week = today + timedelta(days=7)

    upcoming_sessions = []
    for s in all_sessions:
        ds = s.get("date_start")
        if ds:
            try:
                session_date = datetime.fromisoformat(
                    ds.replace("Z", "+00:00")
                ).date()
                if today <= session_date <= next_week:
                    upcoming_sessions.append(s)
            except (ValueError, AttributeError):
                pass

    upcoming_sessions.sort(key=lambda x: x.get("date_start", ""))

    todays_sessions = [
        s for s in upcoming_sessions
        if datetime.fromisoformat(
            s["date_start"].replace("Z", "+00:00")
        ).date() == today
    ]

    return DashboardData(
        all_sessions=all_sessions,
        all_semesters=all_semesters,
        seasons_sessions=seasons_sessions,
        tournament_sessions=tournament_sessions,
        seasons_by_semester=dict(seasons_by_semester),
        tournaments_by_semester=dict(tournaments_by_semester),
        upcoming_sessions=upcoming_sessions,
        todays_sessions=todays_sessions,
        fetched_at=datetime.now(),
    )
