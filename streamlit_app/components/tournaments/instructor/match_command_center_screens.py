"""
Match Command Center Screen Components

Screen rendering functions for match command center.
Uses component library for consistent UX.
"""

import streamlit as st
from typing import Dict, Any, List
from streamlit_components.layouts import Card, SingleColumnForm
from streamlit_components.feedback import Loading, Success, Error
from components.tournaments.instructor.match_command_center_helpers import (
    parse_time_format,
    format_time_display,
    mark_attendance,
    submit_round_results,
    finalize_individual_ranking_session,
    submit_match_results
)


def render_attendance_step(match: Dict[str, Any]):
    """Render attendance step for match"""
    st.markdown("### 📋 Mark Attendance")

    card = Card(title="Participant Attendance", card_id="attendance")
    with card.container():
        participants = match.get('participants', [])
        session_id = match.get('id')

        for participant in participants:
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.write(participant.get('name', 'Unknown'))

            with col2:
                if st.button("✅ Present", key=f"btn_present_{participant['id']}"):
                    mark_attendance(session_id, participant['id'], 'PRESENT')

            with col3:
                if st.button("❌ Absent", key=f"btn_absent_{participant['id']}"):
                    mark_attendance(session_id, participant['id'], 'ABSENT')
    card.close_container()


def render_individual_ranking_form(match: Dict[str, Any]):
    """Render individual ranking results form"""
    st.markdown("### 🏆 Enter Rankings")

    card = Card(title="Individual Rankings", card_id="individual_rankings")
    with card.container():
        form = SingleColumnForm("ranking_form")
        with form.container():
            participants = match.get('participants', [])
            rankings = []

            for i, participant in enumerate(participants, 1):
                rank = st.number_input(
                    f"Rank for {participant.get('name')}",
                    min_value=1,
                    max_value=len(participants),
                    value=i,
                    key=f"input_rank_{participant['id']}"
                )
                rankings.append({"user_id": participant['id'], "rank": rank})

            if st.button("Submit Rankings", type="primary", key="btn_submit_rankings"):
                with Loading.spinner("Submitting rankings..."):
                    submit_match_results(match['id'], {"rankings": rankings})
    card.close_container()


def render_rounds_based_entry(tournament_id: int, match: Dict[str, Any], num_rounds: int):
    """Render rounds-based entry form for multi-round INDIVIDUAL_RANKING tournaments - step by step"""

    # Get scoring type to determine input format
    scoring_method = match.get('structure_config', {}).get('scoring_method', 'SCORE_BASED')

    # Get rounds_data from match to determine current round
    rounds_data = match.get('rounds_data', {})
    completed_rounds = rounds_data.get('completed_rounds', 0)
    total_rounds = rounds_data.get('total_rounds', num_rounds)

    # Determine current round (next incomplete round)
    current_round = completed_rounds + 1

    # If all rounds completed, show completion message
    if current_round > total_rounds:
        st.success(f"✅ All {total_rounds} rounds completed!")
        st.info("You can now finalize the session to calculate final rankings.")
        return

    # Progress indicator
    st.markdown(f"### 🎯 Round {current_round} of {total_rounds}")
    st.progress(completed_rounds / total_rounds)

    participants = match.get('participants', [])

    if not participants:
        st.warning("No participants found for this match")
        return

    match_id = match['id']

    # Single card for current round only
    card = Card(title=f"Round {current_round}", card_id=f"round_{current_round}")
    with card.container():
        # 🎯 ATTENDANCE TRACKING (per round)
        st.markdown(f"#### 📋 Attendance")
        st.markdown("Mark who is present for this round:")

        # Initialize attendance state for this round
        attendance_key = f"round_{current_round}_attendance_{match_id}"
        if attendance_key not in st.session_state:
            st.session_state[attendance_key] = {
                str(p['id']): p.get('is_present', False)
                for p in participants
            }

        # Attendance checkboxes
        for participant in participants:
            user_id_str = str(participant['id'])
            is_present = st.checkbox(
                f"✅ {participant.get('name')} ({participant.get('email', '')})",
                value=st.session_state[attendance_key].get(user_id_str, False),
                key=f"attendance_round{current_round}_{user_id_str}_{match_id}"
            )
            st.session_state[attendance_key][user_id_str] = is_present

        st.markdown("---")

        # 🎯 SCORE ENTRY (only for present participants)
        st.markdown(f"#### 🎯 Results")

        round_results = {}  # Backend expects Dict[user_id_str, value_str]

        for participant in participants:
            user_id = str(participant['id'])  # Convert to string for backend

            # Only show input if participant is marked as present
            if not st.session_state[attendance_key].get(user_id, False):
                st.text(f"⏭️ {participant.get('name')} - Not present (skipped)")
                continue

            if scoring_method == 'TIME_BASED':
                # Time input (e.g., "12.5" seconds)
                time_value = st.number_input(
                    f"⏱️ {participant.get('name')} - Time (seconds)",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    key=f"input_round{current_round}_time_{user_id}_{match_id}"
                )
                round_results[user_id] = f"{time_value:.2f}s"
            else:
                # Score/distance input (e.g., "150" points or "7.5" meters)
                score_value = st.number_input(
                    f"📊 {participant.get('name')} - Score",
                    min_value=0,
                    key=f"input_round{current_round}_score_{user_id}_{match_id}"
                )
                round_results[user_id] = str(score_value)

        if st.button(f"Submit Round {current_round}", type="primary", key=f"btn_submit_round_{current_round}_{match_id}"):
            # Validate that at least one participant is present
            if not any(st.session_state[attendance_key].values()):
                Error.message("Please mark at least one participant as present")
            else:
                with Loading.spinner(f"Submitting round {current_round}..."):
                    if submit_round_results(tournament_id, match['id'], current_round, round_results):
                        # Clear attendance state for this round after successful submission
                        if attendance_key in st.session_state:
                            del st.session_state[attendance_key]
                        st.rerun()  # Refresh to show next round
    card.close_container()

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


def render_measured_value_entry(match: Dict[str, Any], metric_name: str, metric_unit: str):
    """Render measured value entry form"""
    st.markdown(f"### 📏 Enter {metric_name} ({metric_unit})")

    card = Card(title=f"{metric_name} Results", card_id="measured_values")
    with card.container():
        form = SingleColumnForm("measured_value_form")
        with form.container():
            participants = match.get('participants', [])
            measurements = []

            for participant in participants:
                value = st.number_input(
                    f"{participant.get('name')} - {metric_name}",
                    min_value=0.0,
                    key=f"input_measure_{participant['id']}"
                )
                measurements.append({"user_id": participant['id'], "value": value})

            if st.button("Submit Results", type="primary", key="btn_submit_measured"):
                with Loading.spinner("Submitting results..."):
                    submit_match_results(match['id'], {"measurements": measurements})
    card.close_container()


def render_placement_based_entry(match: Dict[str, Any]):
    """Render placement-based entry form"""
    st.markdown("### 🥇 Enter Placements")

    card = Card(title="Final Placements", card_id="placements")
    with card.container():
        form = SingleColumnForm("placement_form")
        with form.container():
            participants = match.get('participants', [])
            placements = []

            for i, participant in enumerate(participants, 1):
                placement = st.selectbox(
                    f"{participant.get('name')} - Placement",
                    options=list(range(1, len(participants) + 1)),
                    index=i - 1,
                    key=f"input_placement_{participant['id']}"
                )
                placements.append({"user_id": participant['id'], "placement": placement})

            if st.button("Submit Placements", type="primary", key="btn_submit_placements"):
                with Loading.spinner("Submitting placements..."):
                    submit_match_results(match['id'], {"placements": placements})
    card.close_container()


def render_head_to_head_form(match: Dict[str, Any]):
    """Render head-to-head match form"""
    st.markdown("### ⚔️ Head-to-Head Result")

    card = Card(title="Match Result", card_id="head_to_head")
    with card.container():
        form = SingleColumnForm("h2h_form")
        with form.container():
            participants = match.get('participants', [])

            if len(participants) == 2:
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**{participants[0].get('name')}**")
                    score1 = st.number_input("Score", min_value=0, key="input_score_p1")

                with col2:
                    st.write(f"**{participants[1].get('name')}**")
                    score2 = st.number_input("Score", min_value=0, key="input_score_p2")

                if st.button("Submit Result", type="primary", key="btn_submit_h2h"):
                    with Loading.spinner("Submitting result..."):
                        results = {
                            "scores": [
                                {"user_id": participants[0]['id'], "score": score1},
                                {"user_id": participants[1]['id'], "score": score2}
                            ]
                        }
                        submit_match_results(match['id'], results)
    card.close_container()


def render_team_match_form(match: Dict[str, Any]):
    """Render team match form"""
    st.markdown("### 👥 Team Match Result")

    card = Card(title="Team Scores", card_id="team_match")
    with card.container():
        form = SingleColumnForm("team_form")
        with form.container():
            teams = match.get('teams', [])

            team_scores = []
            for team in teams:
                score = st.number_input(
                    f"{team.get('name')} - Score",
                    min_value=0,
                    key=f"input_team_score_{team['id']}"
                )
                team_scores.append({"team_id": team['id'], "score": score})

            if st.button("Submit Team Result", type="primary", key="btn_submit_team"):
                with Loading.spinner("Submitting team result..."):
                    submit_match_results(match['id'], {"team_scores": team_scores})
    card.close_container()


def render_time_based_form(match: Dict[str, Any]):
    """Render time-based results form"""
    st.markdown("### ⏱️ Enter Times")

    card = Card(title="Time Results (MM:SS.CC)", card_id="time_based")
    with card.container():
        form = SingleColumnForm("time_form")
        with form.container():
            participants = match.get('participants', [])
            times = []

            for participant in participants:
                time_str = st.text_input(
                    f"{participant.get('name')} - Time (MM:SS.CC)",
                    placeholder="1:30.45",
                    key=f"input_time_{participant['id']}"
                )

                if time_str:
                    try:
                        time_seconds = parse_time_format(time_str)
                        times.append({"user_id": participant['id'], "time_seconds": time_seconds})
                    except ValueError as e:
                        st.error(f"Invalid time format: {str(e)}")

            if st.button("Submit Times", type="primary", key="btn_submit_times"):
                if len(times) == len(participants):
                    with Loading.spinner("Submitting times..."):
                        submit_match_results(match['id'], {"times": times})
                else:
                    Error.message("Please enter times for all participants")
    card.close_container()


def render_knockout_bracket(leaderboard_data: dict):
    """Render knockout bracket visualization"""
    st.markdown("### 🏆 Knockout Bracket")

    card = Card(title="Tournament Bracket", card_id="knockout_bracket")
    with card.container():
        st.info("Bracket visualization")
        # Bracket rendering logic here
    card.close_container()


def render_group_results_table(group_standings: dict):
    """Render group results table"""
    st.markdown("### 📊 Group Standings")

    card = Card(title="Group Results", card_id="group_standings")
    with card.container():
        for group_name, standings in group_standings.items():
            st.write(f"**{group_name}**")
            # Table rendering logic here
    card.close_container()
