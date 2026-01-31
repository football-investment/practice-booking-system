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

    # Tournament Configuration Preview Card
    card = Card(title="Tournament Configuration Preview", card_id="config_preview")
    with card.container():
        # Section 1: Basic Info
        st.markdown("#### 📋 Basic Information")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tournament Name", config.get('tournament_name', 'N/A'))
        with col2:
            st.metric("Age Group", config.get('age_group', 'N/A'))
        with col3:
            st.metric("Max Players", config.get('max_players', 0))

        st.markdown("---")

        # Section 2: Format & Structure
        st.markdown("#### 🏆 Format & Structure")
        tournament_format = config.get('tournament_format', 'N/A')
        scoring_mode = config.get('scoring_mode', 'N/A')

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tournament Format", tournament_format.title())

        with col2:
            st.metric("Scoring Mode", scoring_mode.replace('_', ' ').title())

        with col3:
            if scoring_mode == "INDIVIDUAL":
                # Show number of rounds
                num_rounds = config.get('number_of_rounds', 'N/A')
                st.metric("Number of Rounds", num_rounds)

        # Additional INDIVIDUAL scoring details
        if scoring_mode == "INDIVIDUAL":
            col1, col2, col3 = st.columns(3)
            with col1:
                scoring_type = config.get('scoring_type', 'N/A')
                st.metric("Scoring Type", scoring_type.replace('_', ' ').title())
            with col2:
                ranking_dir = config.get('ranking_direction', 'N/A')
                st.metric("Ranking Direction", ranking_dir)
            with col3:
                measurement = config.get('measurement_unit', 'N/A')
                st.metric("Measurement Unit", measurement if measurement else "—")

        st.markdown("---")

        # Section 3: Schedule & Location
        st.markdown("#### 📅 Schedule & Location")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Start Date", config.get('start_date', 'N/A'))
        with col2:
            st.metric("End Date", config.get('end_date', 'N/A'))
        with col3:
            st.metric("Location ID", config.get('location_id', 'N/A'))
        with col4:
            st.metric("Campus ID", config.get('campus_id', 'N/A'))

        st.markdown("---")

        # Section 4: Game Configuration
        st.markdown("#### ⚽ Game Configuration")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Game Preset ID", config.get('game_preset_id', 'N/A'))
            st.metric("Performance Variation", config.get('performance_variation', 'N/A'))
        with col2:
            skills = config.get('skills_to_test', [])
            st.metric("Skills Tested", len(skills))
            if skills:
                st.caption(", ".join(skills[:5]) + ("..." if len(skills) > 5 else ""))

        st.markdown("---")

        # Section 5: Participants
        st.markdown("#### 👥 Participants")
        selected_users = config.get('selected_users', [])
        st.metric("Selected Users", len(selected_users))
        if selected_users:
            st.caption(f"User IDs: {', '.join(map(str, selected_users[:10]))}" + ("..." if len(selected_users) > 10 else ""))

        st.markdown("---")

        # Section 6: Rewards
        st.markdown("#### 🏅 Rewards")
        rewards = config.get('rewards', {})
        col1, col2, col3 = st.columns(3)
        with col1:
            first = rewards.get('first_place', {})
            st.metric("🥇 1st Place", f"{first.get('xp', 0)} XP + {first.get('credits', 0)} Credits")
        with col2:
            second = rewards.get('second_place', {})
            st.metric("🥈 2nd Place", f"{second.get('xp', 0)} XP + {second.get('credits', 0)} Credits")
        with col3:
            third = rewards.get('third_place', {})
            st.metric("🥉 3rd Place", f"{third.get('xp', 0)} XP + {third.get('credits', 0)} Credits")

        col1, col2 = st.columns(2)
        with col1:
            participation = rewards.get('participation', {})
            st.metric("Participation XP", participation.get('xp', 0))
        with col2:
            st.metric("Session Base XP", rewards.get('session_base_xp', 0))

        # Collapsible Full JSON
        with st.expander("🔍 Full Configuration (JSON)"):
            st.json(config)
    card.close_container()

    st.markdown("---")

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button(
            "← Back to Configuration",
            use_container_width=True,
            key="btn_back_to_config"
        ):
            st.session_state.screen = "configuration"
            st.session_state.workflow_step = 1
            st.rerun()

    with col2:
        create_clicked = st.button(
            "Create Tournament",
            type="primary",
            use_container_width=True,
            key="btn_create_tournament_step1"
        )

    if create_clicked:
        with Loading.spinner("Creating tournament..."):
            try:
                # Use sandbox/run-test to create AND auto-enroll participants
                # This endpoint handles tournament creation + enrollment automatically
                selected_users = config.get("selected_users", [])
                player_count = len(selected_users) if selected_users else config.get("max_players", 8)

                api_payload = {
                    "tournament_type": config["tournament_format"],
                    "skills_to_test": config["skills_to_test"],
                    "player_count": player_count,
                    "test_config": {
                        "performance_variation": config.get("performance_variation", "MEDIUM"),
                        "ranking_distribution": config.get("ranking_distribution", "NORMAL"),
                        "game_preset_id": config.get("game_preset_id"),
                        "game_config_overrides": {
                            "scoring_mode": config["scoring_mode"],
                            "individual_config": {
                                "number_of_rounds": config.get("number_of_rounds"),
                                "scoring_type": config.get("scoring_type"),
                                "ranking_direction": config.get("ranking_direction"),
                                "measurement_unit": config.get("measurement_unit")
                            } if config["scoring_mode"] == "INDIVIDUAL" else None
                        }
                    }
                }

                # Create tournament via sandbox/run-test (auto-enrolls users)
                result = api_client.post("/api/v1/sandbox/run-test", data=api_payload)

                tournament_id = result.get('tournament', {}).get('id')
                st.session_state.tournament_id = tournament_id
                st.session_state.tournament_result = result

                Success.message(f"Tournament created! ID: {tournament_id}")

                # Update tournament name
                try:
                    user_tournament_name = config.get('tournament_name', 'LFA Tournament')
                    api_client.patch(f"/api/v1/semesters/{tournament_id}", data={"name": user_tournament_name})
                    Success.toast(f"Tournament name set to: {user_tournament_name}")
                except APIError:
                    pass

                # Reset status to IN_PROGRESS (required for session generation)
                # NOTE: sandbox/run-test sets status to COMPLETED after enrolling users.
                # We need IN_PROGRESS status to allow session generation.
                # The enrollments are already saved in tournament_participations table.
                try:
                    api_client.patch(f"/api/v1/semesters/{tournament_id}", data={"tournament_status": "IN_PROGRESS"})
                    Success.toast("✅ Status set to IN_PROGRESS")
                except APIError as e:
                    Error.message(f"Status reset failed: {e.message}")

                # Generate sessions
                try:
                    session_data = api_client.post(
                        f"/api/v1/tournaments/{tournament_id}/generate-sessions",
                        data={"parallel_fields": 1, "session_duration_minutes": 90, "break_minutes": 15}
                    )
                    sessions_count = session_data.get('sessions_generated_count', 0)
                    Success.message(f"✅ {sessions_count} sessions auto-generated!")

                    # Move to next step
                    st.session_state.workflow_step = 2
                    st.rerun()

                except APIError as e:
                    # Session generation failed - show detailed error
                    error_msg = str(e.message) if hasattr(e, 'message') else str(e)
                    Error.message(f"❌ Session generation failed: {error_msg}")

                    # Debug: Check enrollment count
                    st.warning("⚠️ Debugging enrollment status...")
                    st.info(f"Tournament ID: {tournament_id}")

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
            key="btn_back_to_step1"
        ):
            st.session_state.workflow_step = 1
            st.rerun()

    with col2:
        if st.button(
            "Continue to Attendance",
            type="primary",
            use_container_width=True,
            key="btn_continue_to_step3"
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
            key="btn_back_to_step2"
        ):
            st.session_state.workflow_step = 2
            st.rerun()

    with col2:
        if st.button(
            "Continue to Results",
            type="primary",
            use_container_width=True,
            key="btn_continue_to_step4"
        ):
            st.session_state.workflow_step = 4
            st.rerun()


def render_step_enter_results():
    """
    Step 4: Enter match results

    This step:
    - Shows matches/sessions needing results
    - Allows instructor to manually enter round-by-round scores (INDIVIDUAL tournaments)
    - Allows instructor to manually enter match scores (HEAD_TO_HEAD tournaments)
    - Updates leaderboard ONLY after results are submitted
    - Moves to next step

    **Sandbox Mode**: Full production UI with optional auto-fill toggle for testing
    """
    st.markdown("### 4. Enter Results")

    tournament_id = st.session_state.get('tournament_id')
    if not tournament_id:
        Error.message("No tournament ID found")
        return

    # 🎯 Sandbox auto-fill toggle (optional testing tool)
    sandbox_autofill = st.toggle(
        "Sandbox Auto-Fill (for quick testing)",
        value=False,
        key="toggle_sandbox_autofill",
        help="Enable to auto-generate results. Disable for manual instructor entry (production UX testing)."
    )

    # Fetch sessions
    sessions = fetch_tournament_sessions(tournament_id)

    if not sessions:
        st.info("No sessions found. Please generate sessions first (Step 2).")
        return

    st.info(f"Found {len(sessions)} session(s)/match(es)")

    # 🎯 Check if ANY rounds have been submitted
    any_results_submitted = False
    for session in sessions:
        rounds_data = session.get('rounds_data', {})
        if rounds_data and rounds_data.get('completed_rounds', 0) > 0:
            any_results_submitted = True
            break

    if sandbox_autofill:
        # Sandbox auto-fill mode
        st.warning("⚠️ Sandbox Auto-Fill ENABLED: Results are auto-generated. This bypasses instructor workflow!")
        st.markdown("**To test production UX**: Disable auto-fill and enter scores manually below.")
    else:
        # Production manual entry mode
        st.success("✅ Manual Entry Mode: Full production instructor UX")

    st.markdown("---")

    # 🎯 PRODUCTION UI INTEGRATION: Render round-based entry for each session
    for session in sessions:
        match_format = session.get('match_format', 'INDIVIDUAL_RANKING')
        scoring_type = session.get('scoring_type', 'RANK_BASED')

        card = Card(
            title=f"Session: {session.get('title', 'Untitled')} (ID: {session.get('id')})",
            card_id=f"session_{session.get('id')}"
        )
        with card.container():
            st.markdown(f"**Format**: {match_format} | **Scoring**: {scoring_type}")

            if match_format == 'INDIVIDUAL_RANKING' and scoring_type == 'ROUNDS_BASED':
                # 🎯 Inline round-based UI (step-by-step, production logic)
                num_rounds = session.get('structure_config', {}).get('number_of_rounds', 3)
                scoring_method = session.get('structure_config', {}).get('scoring_method', 'SCORE_BASED')
                session_id = session.get('id')

                # Get rounds_data to determine current round
                rounds_data = session.get('rounds_data', {})
                completed_rounds = rounds_data.get('completed_rounds', 0)
                total_rounds = rounds_data.get('total_rounds', num_rounds)

                # Determine current round (next incomplete round)
                current_round = completed_rounds + 1

                # If all rounds completed, show completion message
                if current_round > total_rounds:
                    st.success(f"✅ All {total_rounds} rounds completed!")
                    st.info("You can now finalize the session to calculate final rankings.")
                else:
                    # Progress indicator
                    st.markdown(f"#### 🎯 Round {current_round} of {total_rounds}")
                    st.progress(completed_rounds / total_rounds)

                    participants = session.get('participants', [])

                    if not participants:
                        st.warning("No participants found for this session")
                    else:
                        # Single card for current round only
                        round_card = Card(title=f"Round {current_round}", card_id=f"round_{current_round}_{session_id}")
                        with round_card.container():
                            # 🎯 ATTENDANCE TRACKING (per round)
                            st.markdown(f"#### 📋 Attendance")
                            st.markdown("Mark who is present for this round:")

                            # Initialize attendance state for this round
                            attendance_key = f"round_{current_round}_attendance_{session_id}"
                            if attendance_key not in st.session_state:
                                st.session_state[attendance_key] = {
                                    str(p['id']): p.get('is_present', False)
                                    for p in participants
                                }

                            # Attendance checkboxes
                            for participant in participants:
                                user_id_str = str(participant['id'])
                                is_present = st.checkbox(
                                    f"✅ {participant['name']} ({participant['email']})",
                                    value=st.session_state[attendance_key].get(user_id_str, False),
                                    key=f"attendance_round{current_round}_{user_id_str}_{session_id}"
                                )
                                st.session_state[attendance_key][user_id_str] = is_present

                            st.markdown("---")

                            # 🎯 SCORE ENTRY (only for present participants)
                            st.markdown(f"#### 🎯 Results")

                            round_results = {}  # Backend expects Dict[user_id_str, value_str]

                            for participant in participants:
                                user_id_str = str(participant['id'])

                                # Only show input if participant is marked as present
                                if not st.session_state[attendance_key].get(user_id_str, False):
                                    st.text(f"⏭️ {participant['name']} - Not present (skipped)")
                                    continue

                                if scoring_method == 'TIME_BASED':
                                    # Time input
                                    time_value = st.number_input(
                                        f"⏱️ {participant['name']} - Time (seconds)",
                                        min_value=0.0,
                                        step=0.01,
                                        format="%.2f",
                                        key=f"sandbox_round{current_round}_time_{user_id_str}_{session_id}"
                                    )
                                    round_results[user_id_str] = f"{time_value:.2f}s"
                                else:
                                    # Score/distance input
                                    score_value = st.number_input(
                                        f"📊 {participant['name']} - Score",
                                        min_value=0,
                                        key=f"sandbox_round{current_round}_score_{user_id_str}_{session_id}"
                                    )
                                    round_results[user_id_str] = str(score_value)

                            if st.button(
                                f"Submit Round {current_round}",
                                type="primary",
                                key=f"btn_sandbox_submit_round_{current_round}_{session_id}"
                            ):
                                # Validate that at least one participant is present
                                if not any(st.session_state[attendance_key].values()):
                                    Error.message("Please mark at least one participant as present")
                                else:
                                    with Loading.spinner(f"Submitting round {current_round}..."):
                                        try:
                                            # Submit via API
                                            api_client.post(
                                                f"/api/v1/tournaments/{tournament_id}/sessions/{session_id}/rounds/{current_round}/submit-results",
                                                data={
                                                    "round_number": current_round,
                                                    "results": round_results,
                                                    "notes": None
                                                }
                                            )
                                            Success.message(f"Round {current_round} results submitted!")
                                            # Clear attendance state for this round after successful submission
                                            if attendance_key in st.session_state:
                                                del st.session_state[attendance_key]
                                            st.rerun()  # Refresh to show next round
                                        except APIError as e:
                                            Error.message(f"Failed to submit round results: {e.message}")

                        round_card.close_container()

                # Show completed rounds summary
                if completed_rounds > 0:
                    st.markdown("---")
                    st.markdown(f"### ✅ Completed Rounds: {completed_rounds}/{total_rounds}")

                    round_results_data = rounds_data.get('round_results', {})
                    for round_num in range(1, completed_rounds + 1):
                        if str(round_num) in round_results_data:
                            with st.expander(f"Round {round_num} Results"):
                                results = round_results_data[str(round_num)]
                                for user_id, value in results.items():
                                    # Find participant name
                                    participant = next((p for p in participants if str(p['id']) == user_id), None)
                                    name = participant.get('name', f'User {user_id}') if participant else f'User {user_id}'
                                    st.text(f"{name}: {value}")

            elif match_format == 'INDIVIDUAL_RANKING':
                # Other INDIVIDUAL formats
                st.info(f"Manual entry for {scoring_type} format - UI integration pending")

            elif match_format == 'HEAD_TO_HEAD':
                # HEAD_TO_HEAD tournaments
                st.info("HEAD_TO_HEAD match entry - UI integration pending")

            else:
                st.warning(f"Unknown match format: {match_format}")

        card.close_container()
        st.markdown("---")

    # 🎯 Show live leaderboard ONLY if results have been submitted
    if any_results_submitted or sandbox_autofill:
        render_mini_leaderboard(tournament_id, title="Live Standings")
    else:
        st.info("📊 **No results submitted yet**")
        st.markdown("Leaderboard will appear after you submit at least one round of results.")

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Back to Attendance",
            key="btn_back_to_step3"
        ):
            st.session_state.workflow_step = 3
            st.rerun()

    with col2:
        if st.button(
            "View Final Leaderboard",
            type="primary",
            use_container_width=True,
            key="btn_continue_to_step5"
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
            key="btn_back_to_step4"
        ):
            st.session_state.workflow_step = 4
            st.rerun()

    with col2:
        if st.button(
            "Distribute Rewards",
            type="primary",
            use_container_width=True,
            key="btn_continue_to_step6"
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
            key="btn_distribute_rewards"
        ):
            with Loading.spinner("Distributing rewards..."):
                try:
                    # Distribute rewards via API
                    result = api_client.post(f"/api/v1/tournaments/{tournament_id}/distribute-rewards")
                    Success.message("Rewards distributed successfully!")

                    # Mark tournament as completed
                    api_client.patch(f"/api/v1/semesters/{tournament_id}", data={"tournament_status": "COMPLETED"})
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
            key="btn_back_to_step5"
        ):
            st.session_state.workflow_step = 5
            st.rerun()

    with col2:
        if st.button(
            "View in History",
            type="primary",
            use_container_width=True,
            key="btn_view_history"
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
