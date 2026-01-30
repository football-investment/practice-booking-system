"""
Match Command Center - Tournament UI
Refactored following UI_REFACTOR_PATTERN.md

Sequential, match-centric workflow for tournament management:
1. Show active match needing attention
2. 2-button attendance (Present/Absent only)
3. Result entry form (rank-based)
4. Auto-advance to next match
5. Live leaderboard sidebar
"""

import streamlit as st
from pathlib import Path
import sys
from typing import Dict, Any, Optional

# Setup path
parent_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(parent_dir))

from streamlit_components.core.api_client import api_client
from streamlit_components.core.auth import AuthManager
from streamlit_components.layouts import Card
from streamlit_components.feedback import Loading, Success, Error

from components.tournaments.instructor.match_command_center_helpers import (
    get_active_match,
    get_leaderboard
)
from components.tournaments.instructor.match_command_center_screens import (
    render_attendance_step,
    render_individual_ranking_form,
    render_rounds_based_entry,
    render_measured_value_entry,
    render_placement_based_entry,
    render_head_to_head_form,
    render_team_match_form,
    render_time_based_form,
    render_knockout_bracket,
    render_group_results_table
)


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
    """Render results entry step based on match format"""
    st.markdown("### 📝 Enter Results")

    match_format = match.get('match_format', 'INDIVIDUAL_RANKING')
    scoring_type = match.get('scoring_type', 'RANK_BASED')

    # Individual ranking
    if match_format == 'INDIVIDUAL_RANKING':
        if scoring_type == 'RANK_BASED':
            render_individual_ranking_form(match)
        elif scoring_type == 'ROUNDS_BASED':
            num_rounds = match.get('structure_config', {}).get('num_rounds', 3)
            render_rounds_based_entry(match, num_rounds)
        elif scoring_type == 'MEASURED_VALUE':
            metric_name = match.get('structure_config', {}).get('metric_name', 'Distance')
            metric_unit = match.get('structure_config', {}).get('metric_unit', 'meters')
            render_measured_value_entry(match, metric_name, metric_unit)
        elif scoring_type == 'PLACEMENT_BASED':
            render_placement_based_entry(match)
        elif scoring_type == 'TIME_BASED':
            render_time_based_form(match)
        else:
            st.error(f"Unknown scoring type: {scoring_type}")

    # Head-to-head
    elif match_format == 'HEAD_TO_HEAD':
        render_head_to_head_form(match)

    # Team match
    elif match_format == 'TEAM_MATCH':
        render_team_match_form(match)

    else:
        st.error(f"Unknown match format: {match_format}")


def render_leaderboard_sidebar(tournament_id: int):
    """Render live leaderboard in sidebar"""
    st.markdown("### 🏆 Live Leaderboard")

    with Loading.spinner("Loading leaderboard..."):
        leaderboard_data = get_leaderboard(tournament_id)

    if not leaderboard_data:
        st.info("No leaderboard data yet")
        return

    tournament_phase = leaderboard_data.get('tournament_phase', 'GROUP')

    if tournament_phase == 'KNOCKOUT':
        render_knockout_bracket(leaderboard_data)
    elif tournament_phase == 'GROUP':
        group_standings = leaderboard_data.get('group_standings', {})
        render_group_results_table(group_standings)
    else:
        # Individual rankings
        standings = leaderboard_data.get('standings', [])
        for i, entry in enumerate(standings, 1):
            st.write(f"{i}. {entry.get('name')} - {entry.get('score', 0)} pts",
                     key=f"metric_leaderboard_{i}")


def render_final_leaderboard(tournament_id: int):
    """Render final tournament leaderboard"""
    st.markdown("## 🏆 Final Leaderboard")

    card = Card(title="Tournament Complete", card_id="final_leaderboard")
    with card.container():
        with Loading.spinner("Loading final standings..."):
            leaderboard_data = get_leaderboard(tournament_id)

        if not leaderboard_data:
            st.info("No leaderboard data available")
            return

        standings = leaderboard_data.get('standings', [])

        for i, entry in enumerate(standings, 1):
            col1, col2, col3 = st.columns([1, 3, 2])

            with col1:
                if i == 1:
                    st.write("🥇")
                elif i == 2:
                    st.write("🥈")
                elif i == 3:
                    st.write("🥉")
                else:
                    st.write(f"{i}.")

            with col2:
                st.write(entry.get('name', 'Unknown'), key=f"metric_final_name_{i}")

            with col3:
                st.write(f"{entry.get('score', 0)} pts", key=f"metric_final_score_{i}")
    card.close_container()


def main():
    """Main entry point"""
    st.set_page_config(page_title="Match Command Center", layout="wide")

    # Authentication
    if not AuthManager.is_authenticated():
        st.warning("Please log in to access match command center")
        return

    # Get tournament ID from session state or URL params
    tournament_id = st.session_state.get('tournament_id')

    if not tournament_id:
        st.error("No tournament selected")
        return

    # Render command center
    render_match_command_center(tournament_id)


if __name__ == "__main__":
    main()
