"""
Tournament Workflow Steps Module

Contains all 6 instructor workflow steps for tournament management.
Each step uses the component library for consistent UX and E2E testing.
"""

import streamlit as st
import requests
from typing import Dict
from streamlit_components.core import api_client, APIError
from streamlit_components.layouts import Card, SingleColumnForm
from streamlit_components.feedback import Loading, Success, Error
from sandbox_helpers import render_mini_leaderboard, fetch_tournament_sessions

API_BASE_URL = "http://localhost:8000/api/v1"


def render_step_create_tournament(config: Dict):
    """
    Step 1: Create tournament with configuration

    This step:
    - Displays tournament configuration
    - Creates tournament via API
    - Enrolls participants
    - Generates sessions
    - Moves to next step
    """
    st.markdown("### 1. Create Tournament")

    card = Card(title="Tournament Configuration", card_id="config_preview")
    with card.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tournament Type", config.get('tournament_type', 'N/A'), data_testid="metric_tournament_type")
        with col2:
            st.metric("Max Players", config.get('max_players', 0), data_testid="metric_max_players")
        with col3:
            st.metric("Skills", len(config.get('skills_to_test', [])), data_testid="metric_skills_count")

        with st.expander("Full Configuration"):
            st.json(config)
    card.close_container()

    st.markdown("---")

    if st.button(
        "Create Tournament",
        type="primary",
        use_container_width=True,
        key="btn_create_tournament_step1",
        data_testid="btn_create_tournament"
    ):
        with Loading.spinner("Creating tournament..."):
            try:
                # Build API payload
                api_payload = {
                    "tournament_type": config["tournament_type"],
                    "skills_to_test": config["skills_to_test"],
                    "player_count": config["max_players"],
                    "test_config": {
                        "performance_variation": config.get("performance_variation", "MEDIUM"),
                        "ranking_distribution": config.get("ranking_distribution", "NORMAL"),
                        "game_preset_id": config.get("game_preset_id"),
                        "game_config_overrides": None
                    }
                }

                # Create tournament
                result = api_client.post("/sandbox/run-test", data=api_payload)

                tournament_id = result.get('tournament', {}).get('id')
                st.session_state.tournament_id = tournament_id
                st.session_state.tournament_result = result

                Success.message(f"Tournament created! ID: {tournament_id}")

                # Update tournament name
                try:
                    user_tournament_name = config.get('tournament_name', 'LFA Tournament')
                    api_client.patch(f"/semesters/{tournament_id}", data={"name": user_tournament_name})
                    Success.toast(f"Tournament name set to: {user_tournament_name}")
                except APIError:
                    pass

                # Reset status to IN_PROGRESS
                try:
                    api_client.patch(f"/semesters/{tournament_id}", data={"tournament_status": "IN_PROGRESS"})
                    Success.toast("Status set to IN_PROGRESS")
                except APIError as e:
                    Error.message(f"Status reset failed: {e.message}")

                # Generate sessions
                try:
                    session_data = api_client.post(
                        f"/tournaments/{tournament_id}/generate-sessions",
                        data={"parallel_fields": 1, "session_duration_minutes": 90, "break_minutes": 15}
                    )
                    sessions_count = session_data.get('sessions_generated_count', 0)
                    Success.message(f"{sessions_count} sessions auto-generated!")

                    # Move to next step
                    st.session_state.workflow_step = 2
                    st.rerun()

                except APIError as e:
                    Error.message(f"Session generation failed: {e.message}")

            except APIError as e:
                Error.api_error(e, show_details=True)


def render_step_manage_sessions():
    """
    Step 2: Manage tournament sessions (matches/brackets)

    This step:
    - Displays generated sessions
    - Allows viewing/editing sessions
    - Confirms sessions are ready
    - Moves to next step
    """
    st.markdown("### 2. Manage Sessions")

    tournament_id = st.session_state.get('tournament_id')
    if not tournament_id:
        Error.message("No tournament ID found. Please create a tournament first.")
        return

    card = Card(title="Tournament Sessions", card_id="sessions_list")
    with card.container():
        sessions = fetch_tournament_sessions(tournament_id)

        if sessions:
            st.success(f"Found {len(sessions)} sessions")

            # Display sessions
            for idx, session in enumerate(sessions, 1):
                with st.expander(f"Session {idx}: {session.get('session_type', 'N/A')}"):
                    st.json(session)
        else:
            st.info("No sessions found. Generate sessions first.")

    card.close_container()

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Back to Step 1",
            key="btn_back_to_step1",
            data_testid="btn_back_step2"
        ):
            st.session_state.workflow_step = 1
            st.rerun()

    with col2:
        if st.button(
            "Continue to Attendance",
            type="primary",
            use_container_width=True,
            key="btn_continue_to_step3",
            data_testid="btn_continue_step3"
        ):
            st.session_state.workflow_step = 3
            st.rerun()


def render_step_track_attendance():
    """
    Step 3: Track participant attendance

    This step:
    - Shows participants
    - Allows marking attendance
    - Moves to next step
    """
    st.markdown("### 3. Track Attendance")

    tournament_id = st.session_state.get('tournament_id')
    if not tournament_id:
        Error.message("No tournament ID found")
        return

    card = Card(title="Mark Attendance", card_id="attendance_tracker")
    with card.container():
        st.info("Attendance tracking functionality")
        st.markdown("All participants are automatically enrolled in sandbox mode.")
    card.close_container()

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Back to Sessions",
            key="btn_back_to_step2",
            data_testid="btn_back_step3"
        ):
            st.session_state.workflow_step = 2
            st.rerun()

    with col2:
        if st.button(
            "Continue to Results",
            type="primary",
            use_container_width=True,
            key="btn_continue_to_step4",
            data_testid="btn_continue_step4"
        ):
            st.session_state.workflow_step = 4
            st.rerun()


def render_step_enter_results():
    """
    Step 4: Enter match results

    This step:
    - Shows matches needing results
    - Allows entering scores
    - Updates leaderboard
    - Moves to next step
    """
    st.markdown("### 4. Enter Results")

    tournament_id = st.session_state.get('tournament_id')
    if not tournament_id:
        Error.message("No tournament ID found")
        return

    card = Card(title="Match Results", card_id="results_entry")
    with card.container():
        sessions = fetch_tournament_sessions(tournament_id)

        st.info(f"Found {len(sessions)} sessions/matches")
        st.markdown("**Results Entry:**")
        st.markdown("In sandbox mode, results are auto-generated. In production, instructors enter scores here.")
    card.close_container()

    # Show live leaderboard
    st.markdown("---")
    render_mini_leaderboard(tournament_id, title="Live Standings")

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Back to Attendance",
            key="btn_back_to_step3",
            data_testid="btn_back_step4"
        ):
            st.session_state.workflow_step = 3
            st.rerun()

    with col2:
        if st.button(
            "View Final Leaderboard",
            type="primary",
            use_container_width=True,
            key="btn_continue_to_step5",
            data_testid="btn_continue_step5"
        ):
            st.session_state.workflow_step = 5
            st.rerun()


def render_step_view_leaderboard():
    """
    Step 5: View final leaderboard

    This step:
    - Shows final standings
    - Displays statistics
    - Moves to rewards step
    """
    st.markdown("### 5. View Final Leaderboard")

    tournament_id = st.session_state.get('tournament_id')
    if not tournament_id:
        Error.message("No tournament ID found")
        return

    render_mini_leaderboard(tournament_id, title="Final Tournament Standings")

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Back to Results",
            key="btn_back_to_step4",
            data_testid="btn_back_step5"
        ):
            st.session_state.workflow_step = 4
            st.rerun()

    with col2:
        if st.button(
            "Distribute Rewards",
            type="primary",
            use_container_width=True,
            key="btn_continue_to_step6",
            data_testid="btn_continue_step6"
        ):
            st.session_state.workflow_step = 6
            st.rerun()


def render_step_distribute_rewards():
    """
    Step 6: Distribute rewards

    This step:
    - Shows reward configuration
    - Distributes badges/points
    - Completes tournament
    - Shows success message
    """
    st.markdown("### 6. Distribute Rewards")

    tournament_id = st.session_state.get('tournament_id')
    if not tournament_id:
        Error.message("No tournament ID found")
        return

    card = Card(title="Reward Distribution", card_id="rewards_panel")
    with card.container():
        st.info("Rewards Configuration")
        st.markdown("**Badges and skill points will be distributed to participants based on their performance.**")

        if st.button(
            "Distribute All Rewards",
            type="primary",
            use_container_width=True,
            key="btn_distribute_rewards",
            data_testid="btn_distribute_rewards"
        ):
            with Loading.spinner("Distributing rewards..."):
                try:
                    # Distribute rewards via API
                    result = api_client.post(f"/tournaments/{tournament_id}/distribute-rewards")
                    Success.message("Rewards distributed successfully!")

                    # Mark tournament as completed
                    api_client.patch(f"/semesters/{tournament_id}", data={"tournament_status": "COMPLETED"})
                    Success.toast("Tournament completed!")

                    st.balloons()

                except APIError as e:
                    Error.api_error(e, show_details=True)

    card.close_container()

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Back to Leaderboard",
            key="btn_back_to_step5",
            data_testid="btn_back_step6"
        ):
            st.session_state.workflow_step = 5
            st.rerun()

    with col2:
        if st.button(
            "View in History",
            type="primary",
            use_container_width=True,
            key="btn_view_history",
            data_testid="btn_view_history"
        ):
            st.session_state.screen = "history"
            st.rerun()


def render_step_tournament_history():
    """
    DEPRECATED: This step is now replaced by the main history screen.
    Keeping for compatibility with old code.
    """
    st.warning("This function is deprecated. Use render_history_screen() instead.")
    st.session_state.screen = "history"
    st.rerun()
