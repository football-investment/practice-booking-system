"""
Tournament List Module - Tournament listing and game management
Refactored following UI_REFACTOR_PATTERN.md
"""

import streamlit as st
from pathlib import Path
import sys
from typing import Dict

# Setup path
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from streamlit_components.core.api_client import api_client
from streamlit_components.core.auth import require_auth
from streamlit_components.layouts import Card, SingleColumnForm
from streamlit_components.feedback import Loading, Success, Error

from components.admin.tournament_list_helpers import (
    get_user_names_from_db,
    get_tournament_sessions_from_db,
    get_location_info,
    get_campus_info,
    get_all_tournaments,
    get_tournament_sessions,
    update_tournament,
    get_tournament_enrollment_count,
    generate_tournament_sessions,
    preview_tournament_sessions,
    delete_generated_sessions,
    save_tournament_reward_config
)
from components.admin.tournament_list_dialogs import (
    show_edit_tournament_dialog,
    show_generate_sessions_dialog,
    show_preview_sessions_dialog,
    show_delete_tournament_dialog,
    show_cancel_tournament_dialog,
    show_edit_reward_config_dialog,
    show_enrollment_viewer_modal,
    show_add_game_dialog,
    show_delete_game_dialog,
    show_reset_sessions_dialog,
    show_edit_schedule_dialog,
    show_edit_game_type_dialog
)


def render_tournament_list():
    """Display list of all tournaments"""
    st.subheader("📋 All Tournaments")

    with Loading.spinner("Loading tournaments..."):
        tournaments_data = get_all_tournaments()

    if not tournaments_data:
        st.info("No tournaments found")
        return

    # Filter for tournaments (TOURN- prefix)
    tournaments = [t for t in tournaments_data if t.get('code', '').startswith('TOURN-')]

    if not tournaments:
        st.info("No tournaments found")
        return

    # Render each tournament
    for tournament in tournaments:
        render_tournament_card(tournament)


def render_tournament_card(tournament: Dict):
    """Render individual tournament card"""
    tournament_id = tournament.get('id')
    tournament_name = tournament.get('name', 'Unknown')
    tournament_code = tournament.get('code', 'N/A')

    with st.expander(f"🏆 {tournament_name} ({tournament_code})"):
        # Action buttons
        render_tournament_actions(tournament)
        st.divider()

        # Tournament details
        col1, col2 = st.columns(2)

        with col1:
            render_tournament_status(tournament)

        with col2:
            render_tournament_metadata(tournament)

        st.divider()

        # Sessions section
        render_tournament_sessions_section(tournament)


def render_tournament_actions(tournament: Dict):
    """Render tournament action buttons"""
    tournament_id = tournament.get('id')
    tournament_status = tournament.get('tournament_status', 'N/A')

    btn_col1, btn_col2, btn_col3, btn_col4, btn_col5 = st.columns(5)

    with btn_col1:
        if st.button("✏️", key=f"btn_edit_tournament_{tournament_id}", help="Edit tournament"):
            st.session_state['edit_tournament_id'] = tournament_id
            st.session_state['edit_tournament_data'] = tournament
            show_edit_tournament_dialog()

    with btn_col2:
        enrollment_started = tournament_status in ['ENROLLMENT_OPEN', 'IN_PROGRESS', 'COMPLETED']
        if not enrollment_started:
            if st.button("⚙️", key=f"btn_edit_schedule_{tournament_id}", help="Edit match schedule"):
                st.session_state['edit_schedule_tournament_id'] = tournament_id
                st.session_state['edit_schedule_tournament_name'] = tournament.get('name', 'Unknown')
                show_edit_schedule_dialog()

    with btn_col3:
        reward_config = tournament.get('reward_config')
        button_label = "🎁" if reward_config else "➕"
        button_help = "Edit reward configuration" if reward_config else "Add reward configuration"
        if st.button(button_label, key=f"btn_reward_config_{tournament_id}", help=button_help):
            st.session_state['edit_reward_config_tournament_id'] = tournament_id
            st.session_state['edit_reward_config_tournament_name'] = tournament.get('name', 'Unknown')
            st.session_state['edit_reward_config_existing'] = reward_config
            st.rerun()

    with btn_col4:
        can_cancel = tournament_status not in ['COMPLETED', 'CANCELLED']
        if can_cancel:
            if st.button("❌", key=f"btn_cancel_tournament_{tournament_id}", help="Cancel tournament"):
                st.session_state['cancel_tournament_id'] = tournament_id
                st.session_state['cancel_tournament_name'] = tournament.get('name', 'Untitled')
                st.session_state['cancel_tournament_status'] = tournament_status
                show_cancel_tournament_dialog()

    with btn_col5:
        if st.button("🗑️", key=f"btn_delete_tournament_{tournament_id}", help="Delete tournament"):
            st.session_state['delete_tournament_id'] = tournament_id
            st.session_state['delete_tournament_name'] = tournament.get('name', 'Untitled')
            show_delete_tournament_dialog()


def render_tournament_status(tournament: Dict):
    """Render tournament status section"""
    st.write(f"**Status**: {tournament.get('status', 'N/A')}", key=f"metric_status_{tournament.get('id')}")

    tournament_status = tournament.get('tournament_status', 'N/A')
    assignment_type = tournament.get('assignment_type', 'UNKNOWN')

    if tournament_status == 'SEEKING_INSTRUCTOR':
        if assignment_type == 'APPLICATION_BASED':
            st.write(f"**Tournament Status**: 📝 {tournament_status}", key=f"metric_tournament_status_{tournament.get('id')}")
            st.caption("Instructors can apply")
        elif assignment_type == 'OPEN_ASSIGNMENT':
            st.write(f"**Tournament Status**: 🔒 {tournament_status}", key=f"metric_tournament_status_{tournament.get('id')}")
            st.caption("Admin will assign instructor")
    else:
        st.write(f"**Tournament Status**: {tournament_status}", key=f"metric_tournament_status_{tournament.get('id')}")

    st.write(f"**Dates**: {tournament.get('start_date', 'N/A')} to {tournament.get('end_date', 'N/A')}", key=f"metric_dates_{tournament.get('id')}")


def render_tournament_metadata(tournament: Dict):
    """Render tournament metadata section"""
    tournament_id = tournament.get('id')
    tournament_type_id = tournament.get('tournament_type_id')
    location_id = tournament.get('location_id')
    campus_id = tournament.get('campus_id')

    if tournament_type_id:
        st.write(f"**Tournament Type ID**: {tournament_type_id}", key=f"metric_type_{tournament_id}")

    if location_id:
        location_info = get_location_info(location_id)
        location_name = location_info.get('name', 'Unknown')
        st.write(f"**Location**: {location_name}", key=f"metric_location_{tournament_id}")

    if campus_id:
        campus_info = get_campus_info(campus_id)
        campus_name = campus_info.get('name', 'Unknown')
        st.write(f"**Campus**: {campus_name}", key=f"metric_campus_{tournament_id}")

    enrollment_count = get_tournament_enrollment_count(tournament_id)
    st.write(f"**Enrollments**: {enrollment_count}", key=f"metric_enrollments_{tournament_id}")


def render_tournament_sessions_section(tournament: Dict):
    """Render tournament sessions section"""
    tournament_id = tournament.get('id')
    tournament_status = tournament.get('tournament_status', 'N/A')

    st.markdown("### 🎮 Tournament Sessions")

    # Session generation buttons
    session_btn_col1, session_btn_col2, session_btn_col3, session_btn_col4 = st.columns(4)

    with session_btn_col1:
        can_generate = tournament_status == 'ENROLLMENT_CLOSED'
        if st.button("🎲 Generate Sessions", key=f"btn_generate_sessions_{tournament_id}", disabled=not can_generate):
            st.session_state['generate_sessions_tournament_id'] = tournament_id
            show_generate_sessions_dialog()

    with session_btn_col2:
        if st.button("👁️ Preview", key=f"btn_preview_sessions_{tournament_id}"):
            st.session_state['preview_sessions_tournament_id'] = tournament_id
            show_preview_sessions_dialog()

    with session_btn_col3:
        if st.button("🔄 Reset", key=f"btn_reset_sessions_{tournament_id}"):
            st.session_state['reset_sessions_tournament_id'] = tournament_id
            show_reset_sessions_dialog()

    with session_btn_col4:
        if st.button("➕ Add Game", key=f"btn_add_game_{tournament_id}"):
            st.session_state['add_game_tournament_id'] = tournament_id
            show_add_game_dialog()

    # Fetch and display sessions
    sessions = get_tournament_sessions_from_db(tournament_id)

    if not sessions:
        st.info("No sessions generated yet")
        return

    st.write(f"**Total Sessions**: {len(sessions)}", key=f"metric_total_sessions_{tournament_id}")

    # Display sessions
    for session in sessions:
        render_session_card(session, tournament_id)


def render_session_card(session: Dict, tournament_id: int):
    """Render individual session card"""
    session_id = session.get('id')
    session_title = session.get('title', 'Untitled')

    with st.expander(f"📋 {session_title} (ID: {session_id})"):
        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**Phase**: {session.get('tournament_phase', 'N/A')}")
            st.write(f"**Round**: {session.get('tournament_round', 'N/A')}")
            st.write(f"**Group**: {session.get('group_identifier', 'N/A')}")
            st.write(f"**Match Format**: {session.get('match_format', 'N/A')}")

        with col2:
            st.write(f"**Scoring Type**: {session.get('scoring_type', 'N/A')}")
            st.write(f"**Status**: {session.get('session_status', 'N/A')}")

            participant_ids = session.get('participant_user_ids', [])
            st.write(f"**Participants**: {len(participant_ids)}")

        # Session actions
        action_col1, action_col2 = st.columns(2)

        with action_col1:
            if st.button("✏️ Edit", key=f"btn_edit_game_{session_id}"):
                st.session_state['edit_game_id'] = session_id
                st.session_state['edit_game_data'] = session
                show_edit_game_type_dialog()

        with action_col2:
            if st.button("🗑️ Delete", key=f"btn_delete_game_{session_id}"):
                st.session_state['delete_game_id'] = session_id
                show_delete_game_dialog()


def main():
    """Main entry point"""
    st.title("🏆 Tournament List")

    # Authentication
    token = require_auth()
    if not token:
        st.warning("Please log in to access tournament management")
        return

    # Render tournament list
    render_tournament_list()


if __name__ == "__main__":
    main()
