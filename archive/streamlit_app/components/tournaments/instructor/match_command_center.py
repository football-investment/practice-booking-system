"""
Match Command Center - Tournament UI

Sequential, match-centric workflow for tournament management:
1. Show active match needing attention
2. 2-button attendance (Present/Absent only)
3. Result entry form (shared component — tournament_card/result_entry.py)
4. Auto-advance to next match
5. Live leaderboard sidebar (shared component — tournament_card/leaderboard.py)
"""

import logging
import streamlit as st
from pathlib import Path
import sys
from typing import Dict, Any, Optional

_log = logging.getLogger(__name__)

_KNOWN_MATCH_FORMATS = frozenset({"INDIVIDUAL_RANKING", "HEAD_TO_HEAD", "TEAM_MATCH"})

# Setup path
parent_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(parent_dir))

from streamlit_components.core.api_client import api_client
from streamlit_components.core.auth import AuthManager
from streamlit_components.layouts import Card
from streamlit_components.feedback import Loading, Success, Error

from components.tournaments.instructor.match_command_center_helpers import (
    get_active_match,
    get_tournament_rankings,
)
from components.admin.tournament_card.leaderboard import render_leaderboard as _render_shared_leaderboard
from components.admin.tournament_card.result_entry import render_manual_result_entry as _render_shared_result_entry
from config import SESSION_TOKEN_KEY as _SESSION_TOKEN_KEY
from components.tournaments.instructor.match_command_center_screens import render_attendance_step


def _match_to_session_dict(match: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt active_match inner object to the session dict expected by render_manual_result_entry.

    The /active-match endpoint envelope is unwrapped by get_active_match() before this is called.
    The inner active_match object uses different field names from the session dict format:

    active_match field   → session dict field
    ─────────────────────────────────────────────
    session_id           → id
    match_participants   → (used to build participant_user_ids / participant_names)
      └ user_id          → participant_user_ids element
      └ name             → participant_names element
    game_results         → result_submitted (non-None means submitted)
    match_format         → match_format          (same)
    scoring_type         → scoring_type          (same)
    structure_config     → structure_config      (same)
    rounds_data          → rounds_data           (same)
    tournament_phase     → tournament_phase      (same)
    tournament_round     → tournament_round      (same)
    """
    # match_participants is the authoritative list of participants for this specific match
    raw_participants = match.get("match_participants")
    participants = [p for p in (raw_participants or []) if isinstance(p, dict)]

    match_format = match.get("match_format") or ""
    if match_format and match_format not in _KNOWN_MATCH_FORMATS:
        _log.warning(
            "MCC._match_to_session_dict: unexpected match_format=%r for session_id=%s — "
            "render_manual_result_entry will silently skip this session",
            match_format,
            match.get("session_id"),
        )

    return {
        # active_match uses "session_id"; result_entry.py expects "id"
        "id": match.get("session_id"),
        # game_results is non-None once results have been recorded
        "result_submitted": match.get("game_results") is not None,
        "match_format": match_format,
        # participant dicts have "user_id" (not "id"); filter out any None ids
        "participant_user_ids": [
            p["user_id"] for p in participants if p.get("user_id") is not None
        ],
        "participant_names": [p.get("name") or "" for p in participants],
        "scoring_type": match.get("scoring_type") or "",
        "structure_config": match.get("structure_config") or {},
        "rounds_data": match.get("rounds_data") or {},
        "tournament_phase": match.get("tournament_phase") or "",
        "tournament_round": match.get("tournament_round"),
    }


def render_match_command_center(tournament_id: int):
    """Main match command center view"""
    st.title("🎮 Match Command Center")

    # Fetch active match
    with Loading.spinner("Loading active match..."):
        match = get_active_match(tournament_id)

    if not match:
        st.info("No active match found")
        render_final_leaderboard(tournament_id)
        return

    # Render match workflow
    render_match_workflow(tournament_id, match)

    # Sidebar: Live leaderboard
    with st.sidebar:
        render_leaderboard_sidebar(tournament_id)


def render_match_workflow(tournament_id: int, match: Dict[str, Any]):
    """Render match workflow steps"""
    match_status = match.get('status', 'PENDING')

    if match_status == 'PENDING':
        render_attendance_step(match)
    elif match_status == 'IN_PROGRESS':
        render_results_step(tournament_id, match)
    else:
        st.success("Match completed!")
        if st.button("Next Match", key="btn_next_match"):
            st.rerun()


def render_results_step(tournament_id: int, match: Dict[str, Any]):
    """Render results entry step.

    Delegates to tournament_card/result_entry.py (shared component).
    _match_to_session_dict() adapts the active_match inner dict → session dict format.
    """
    st.markdown("### 📝 Enter Results")
    token = st.session_state.get(_SESSION_TOKEN_KEY, "")
    session_dict = _match_to_session_dict(match)
    _render_shared_result_entry(token, tournament_id, [session_dict])


def render_leaderboard_sidebar(tournament_id: int):
    """Render live leaderboard in sidebar.

    Delegates to tournament_card/leaderboard.py (shared component).
    """
    st.markdown("### 🏆 Live Leaderboard")
    with Loading.spinner("Loading leaderboard..."):
        rankings = get_tournament_rankings(tournament_id)
    _render_shared_leaderboard(rankings)


def render_final_leaderboard(tournament_id: int):
    """Render final tournament leaderboard.

    Delegates to tournament_card/leaderboard.py (shared component).
    """
    st.markdown("## 🏆 Final Leaderboard")
    with Loading.spinner("Loading final standings..."):
        rankings = get_tournament_rankings(tournament_id)
    _render_shared_leaderboard(rankings)


def main():
    """Main entry point"""
    st.set_page_config(page_title="Match Command Center", layout="wide")

    if not AuthManager.is_authenticated():
        st.warning("Please log in to access match command center")
        return

    tournament_id = st.session_state.get('tournament_id')
    if not tournament_id:
        st.error("No tournament selected")
        return

    render_match_command_center(tournament_id)


if __name__ == "__main__":
    main()
