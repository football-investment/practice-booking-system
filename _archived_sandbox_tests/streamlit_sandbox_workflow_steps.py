"""
Streamlit Sandbox Workflow Steps Implementation

Implements the instructor workflow steps for tournament management:
- Step 1: Create Tournament
- Step 2: Manage Sessions
- Step 3: Track Attendance
- Step 4: Enter Results (HEAD_TO_HEAD support)
- Step 5: View Leaderboard
- Step 6: Distribute Rewards
- Step 7: View Rewards
"""

import streamlit as st
import time
import requests
from typing import Dict, Any, List
from datetime import datetime

from streamlit_components.core import api_client
from streamlit_components.layouts import Card
from streamlit_components.feedback import Loading, Success, Error


def get_user_friendly_phase_label(title: str, tournament_phase: str) -> str:
    """
    Convert generic round titles to user-friendly phase labels.

    Examples:
        "Round of 4 - Match 1" -> "Semi-Final - Match 1"
        "Round of 2 - Match 1" -> "Final"
        "Round of 8 - Match 1" -> "Quarter-Final - Match 1"
        "Group Stage - Match 1" -> "Group Stage - Match 1" (unchanged)

    Args:
        title: Original session title from database
        tournament_phase: Tournament phase (e.g., "Knockout Stage", "Group Stage")

    Returns:
        User-friendly title with proper phase labels
    """
    if tournament_phase != "Knockout Stage":
        return title  # Only modify knockout stage titles

    # Map round sizes to user-friendly names
    title_lower = title.lower()

    if "round of 2" in title_lower or "final" in title_lower:
        # Don't modify if already contains "semi", "quarter", "bronze", "3rd"
        if any(x in title_lower for x in ["semi", "quarter", "bronze", "3rd"]):
            return title
        # Replace "Round of 2" with "Final"
        return title.replace("Round of 2 - Match 1", "Final").replace("round of 2 - match 1", "Final")

    if "round of 4" in title_lower:
        # Don't modify if already contains proper phase name
        if "semi" in title_lower or "quarter" in title_lower:
            return title
        # Replace "Round of 4" with "Semi-Final"
        return title.replace("Round of 4", "Semi-Final").replace("round of 4", "Semi-Final")

    if "round of 8" in title_lower:
        if "quarter" in title_lower:
            return title
        return title.replace("Round of 8", "Quarter-Final").replace("round of 8", "Quarter-Final")

    # Default: return original title
    return title


def render_step_create_tournament(config: Dict[str, Any]):
    """Step 1: Create Tournament"""
    st.title("Step 1: Create Tournament")

    # 🔵 VALIDATION MARKER: streamlit_sandbox_workflow_steps.py IS EXECUTING
    st.info("🔵 **VALIDATION**: Using `streamlit_sandbox_workflow_steps.py` implementation")

    tournament_id = st.session_state.get('tournament_id')

    if tournament_id:
        st.success(f"✅ Tournament created: ID {tournament_id}")

        if st.button("Continue to Session Management", key="btn_continue_step2"):
            st.session_state.workflow_step = 2
            st.rerun()
    else:
        # Show tournament configuration preview
        st.subheader("Tournament Configuration Preview")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**📋 Basic Information**")
            st.text(f"Tournament Name: {config.get('tournament_name', 'N/A')}")
            st.text(f"Age Group: {config.get('age_group', 'N/A')}")
            st.text(f"Max Players: {config.get('max_players', 'N/A')}")

        with col2:
            st.markdown("**🏆 Format & Structure**")
            st.text(f"Tournament Format: {config.get('tournament_format', 'N/A')}")
            st.text(f"Scoring Mode: {config.get('scoring_mode', 'N/A')}")

        st.markdown("**📅 Schedule & Location**")
        st.text(f"Start Date: {config.get('start_date', 'N/A')}")
        st.text(f"End Date: {config.get('end_date', 'N/A')}")

        st.markdown("---")

        # ✅ STREAMLIT FORM PATTERN: Ensures reliable event handler registration
        # Wrapping button in st.form() guarantees handler is registered before user interaction
        # This solves the timing issue where rapid screen transitions prevent button event binding
        with st.form(key="form_create_tournament", clear_on_submit=False):
            st.markdown("### Ready to Create Tournament")
            st.info("Click below to create the tournament with the configuration shown above.")

            # Form submit button - guaranteed to have event handler registered
            submit_clicked = st.form_submit_button(
                "Create Tournament",
                type="primary",
                use_container_width=True
            )

        # Handle form submission AFTER the form block closes
        # This ensures Streamlit processes the form properly
        if submit_clicked:
            # Show debug info: request payload
            with st.expander("🔍 DEBUG: Request Payload", expanded=False):
                st.json(config)

            # Create tournament via API
            with Loading.spinner("Creating tournament..."):
                try:
                    response = api_client.post("/tournaments", config)

                    # Show debug info: API response
                    with st.expander("🔍 DEBUG: API Response", expanded=True):
                        st.json(response if isinstance(response, dict) else {"raw": str(response)})

                    if response and isinstance(response, dict) and response.get('id'):
                        tournament_id = response['id']
                        st.session_state.tournament_id = tournament_id
                        st.success(f"✅ Tournament created successfully! (ID: {tournament_id})")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to create tournament: Invalid response")
                        st.json(response if isinstance(response, dict) else {"raw": str(response)})
                except Exception as e:
                    st.error(f"❌ Failed to create tournament: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc(), language="python")


def render_step_manage_sessions():
    """Step 2: Manage Sessions"""
    st.title("Step 2: Manage Sessions")

    tournament_id = st.session_state.get('tournament_id')
    if not tournament_id:
        st.error("No tournament selected")
        return

    st.info("Sessions are auto-generated. Review them below:")

    # Fetch sessions
    try:
        response = api_client.get(f"/tournaments/{tournament_id}/sessions")
        if response.status_code == 200:
            sessions = response.json()
            st.write(f"Total sessions: {len(sessions)}")

            # Show session list
            for session in sessions[:10]:  # Show first 10
                st.text(f"- {session.get('title', 'N/A')}")
        else:
            st.error(f"Failed to load sessions: {response.status_code}")
    except Exception as e:
        st.error(f"Error: {e}")

    if st.button("Continue to Attendance Tracking", key="btn_continue_step3"):
        st.session_state.workflow_step = 3
        st.rerun()


def render_step_track_attendance():
    """Step 3: Track Attendance"""
    st.title("Step 3: Track Attendance")

    tournament_id = st.session_state.get('tournament_id')
    if not tournament_id:
        st.error("No tournament selected")
        return

    st.info("Attendance tracking is auto-managed for sandbox tournaments.")
    st.success("✅ All participants marked as present")

    if st.button("Continue to Enter Results", key="btn_continue_step4", use_container_width=True):
        st.session_state.workflow_step = 4
        st.rerun()


def render_step_enter_results():
    """Step 4: Enter Results (HEAD_TO_HEAD support with Phase-Aware UI)"""
    st.title("Step 4: Enter Results")

    tournament_id = st.session_state.get('tournament_id')
    if not tournament_id:
        st.error("No tournament selected")
        return

    # Initialize current phase in session state if not present
    if 'current_phase' not in st.session_state:
        st.session_state.current_phase = "Group Stage"

    # Fetch all sessions
    try:
        response = api_client.get(f"/semesters/{tournament_id}")
        if response.status_code != 200:
            st.error(f"Failed to load tournament: {response.status_code}")
            return

        tournament_data = response.json()
        tournament_format = tournament_data.get('format', 'KNOCKOUT')

        # Get sessions - use semester_id filter only
        sessions_response = api_client.get(f"/sessions", params={"semester_id": tournament_id, "size": 100})
        if sessions_response.status_code != 200:
            st.error(f"Failed to load sessions: {sessions_response.status_code}")
            return

        sessions_data = sessions_response.json()
        # Extract items from paginated response
        all_sessions = sessions_data.get('items', []) if isinstance(sessions_data, dict) else sessions_data

        # Filter to tournament games only
        all_sessions = [s for s in all_sessions if s.get('is_tournament_game', False)]

        # ===========================================================================
        # PHASE-AWARE UI: Separate Group Stage and Knockout Stage
        # ===========================================================================
        is_group_knockout = tournament_format == 'GROUP_KNOCKOUT'

        if is_group_knockout:
            # Separate sessions by phase
            group_sessions = [s for s in all_sessions if s.get('tournament_phase') == 'Group Stage']
            knockout_sessions = [s for s in all_sessions if s.get('tournament_phase') == 'Knockout Stage']

            # Calculate completion status
            group_completed = [s for s in group_sessions if s.get('game_results')]
            group_pending = [s for s in group_sessions if not s.get('game_results')]
            knockout_completed = [s for s in knockout_sessions if s.get('game_results')]
            knockout_pending = [s for s in knockout_sessions if not s.get('game_results')]

            group_phase_done = len(group_pending) == 0 and len(group_sessions) > 0
            knockout_phase_exists = len(knockout_sessions) > 0

            # Display phase status
            col1, col2 = st.columns(2)
            with col1:
                if group_phase_done:
                    st.success(f"✅ Group Stage Complete ({len(group_completed)}/{len(group_sessions)})")
                else:
                    st.info(f"📊 Group Stage: {len(group_completed)}/{len(group_sessions)} matches")

            with col2:
                if knockout_phase_exists:
                    if len(knockout_pending) == 0:
                        st.success(f"✅ Knockout Stage Complete ({len(knockout_completed)}/{len(knockout_sessions)})")
                    else:
                        st.info(f"🏆 Knockout Stage: {len(knockout_completed)}/{len(knockout_sessions)} matches")
                else:
                    st.warning("⏳ Knockout Stage: Not yet generated")

            st.markdown("---")

            # ===========================================================================
            # PHASE TRANSITION LOGIC
            # ===========================================================================
            current_phase = st.session_state.current_phase

            # Auto-transition to knockout if group stage is done
            if group_phase_done and knockout_phase_exists and current_phase == "Group Stage":
                st.session_state.current_phase = "Knockout Stage"
                current_phase = "Knockout Stage"
                st.rerun()

            # Display current phase
            st.subheader(f"Current Phase: {current_phase}")

            # Phase selector
            if group_phase_done and knockout_phase_exists:
                phase_options = ["Group Stage", "Knockout Stage"]
                selected_phase = st.selectbox(
                    "View Phase:",
                    options=phase_options,
                    index=phase_options.index(current_phase),
                    key="phase_selector"
                )

                if selected_phase != current_phase:
                    st.session_state.current_phase = selected_phase
                    st.rerun()

            # Filter sessions based on current phase
            if current_phase == "Group Stage":
                phase_sessions = group_sessions
                pending_sessions = group_pending
                completed_sessions = group_completed
            else:  # Knockout Stage
                phase_sessions = knockout_sessions
                pending_sessions = knockout_pending
                completed_sessions = knockout_completed

            # 🐛 DEBUG: Log current phase and pending sessions
            print(f"\n🐛 DEBUG render_step_enter_results (Phase-Aware):")
            print(f"   - Tournament format: {tournament_format}")
            print(f"   - Current phase: {current_phase}")
            print(f"   - Group sessions: {len(group_sessions)} (pending: {len(group_pending)})")
            print(f"   - Knockout sessions: {len(knockout_sessions)} (pending: {len(knockout_pending)})")
            print(f"   - Showing {len(pending_sessions)} pending sessions for {current_phase}")
            for s in pending_sessions:
                participants = s.get('participant_user_ids', [])
                print(f"      - Session {s['id']}: round={s.get('round_number')}, participants={participants}")

        else:
            # Non-group-knockout tournaments: Show all sessions (original behavior)
            pending_sessions = [s for s in all_sessions if not s.get('game_results')]
            completed_sessions = [s for s in all_sessions if s.get('game_results')]

            st.write(f"**Completed**: {len(completed_sessions)} / {len(all_sessions)}")
            st.write(f"**Pending**: {len(pending_sessions)}")

            # 🐛 DEBUG: Log all pending sessions
            print(f"\n🐛 DEBUG render_step_enter_results: {len(pending_sessions)} pending sessions")
            for s in pending_sessions:
                participants = s.get('participant_user_ids', [])
                print(f"   - Session {s['id']}: phase={s.get('tournament_phase')}, round={s.get('round_number')}, participants={participants}")

        # ===========================================================================
        # RESULT SUBMISSION UI (common for all formats)
        # ===========================================================================
        if not pending_sessions:
            st.success("✅ All sessions have results!")

            if st.button("Continue to Leaderboard", key="btn_continue_step5", use_container_width=True):
                st.session_state.workflow_step = 5
                st.rerun()
            return

        st.markdown("---")
        st.subheader("Submit Results")

        # Show pending sessions
        for idx, session in enumerate(pending_sessions):
            session_id = session['id']
            title = session.get('title', f"Session {session_id}")
            participants = session.get('participant_user_ids', [])
            tournament_phase = session.get('tournament_phase', 'N/A')

            # ✅ UX IMPROVEMENT: Convert generic round titles to user-friendly labels
            # "Round of 4" -> "Semi-Final", "Round of 2" -> "Final"
            display_title = get_user_friendly_phase_label(title, tournament_phase)

            if not participants or len(participants) < 2:
                st.warning(f"⚠️ {display_title}: Missing participants")
                continue

            with st.expander(f"📋 {display_title} ({tournament_phase})", expanded=(idx == 0)):
                st.write(f"**Session ID**: {session_id}")
                st.write(f"**Phase**: {tournament_phase}")
                st.write(f"**Participants**: {participants}")

                # HEAD_TO_HEAD result entry
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Player 1**: User {participants[0]}")
                    score1 = st.number_input(
                        "Score",
                        min_value=0,
                        max_value=10,
                        value=0,
                        key=f"score1_{session_id}",
                        help="Goals scored by Player 1"
                    )

                with col2:
                    st.write(f"**Player 2**: User {participants[1]}")
                    score2 = st.number_input(
                        "Score",
                        min_value=0,
                        max_value=10,
                        value=0,
                        key=f"score2_{session_id}",
                        help="Goals scored by Player 2"
                    )

                if st.button(f"Submit Result", key=f"btn_submit_{session_id}", use_container_width=True):
                    # Submit via API
                    payload = {
                        "results": [
                            {"user_id": participants[0], "score": score1},
                            {"user_id": participants[1], "score": score2}
                        ]
                    }

                    with Loading.spinner("Submitting result..."):
                        try:
                            response = api_client.patch(
                                f"/sessions/{session_id}/head-to-head-results",
                                json=payload
                            )

                            if response.status_code == 200:
                                Success.toast(f"✅ Result submitted: {score1}-{score2}")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                Error.toast(f"Failed: {response.status_code}")
                                st.error(response.text)
                        except Exception as e:
                            Error.toast(f"Error: {e}")

    except Exception as e:
        st.error(f"Error loading data: {e}")


def render_step_view_leaderboard():
    """Step 5: View Leaderboard"""
    st.title("Step 5: View Leaderboard")

    tournament_id = st.session_state.get('tournament_id')
    if not tournament_id:
        st.error("No tournament selected")
        return

    try:
        response = api_client.get(f"/tournaments/{tournament_id}/rankings")
        if response.status_code == 200:
            rankings = response.json()

            st.subheader("Final Rankings")
            for rank in rankings:
                st.write(f"{rank['rank']}. User {rank['user_id']} - {rank['points']} pts")
        else:
            st.warning("Rankings not available yet. Complete all matches first.")
    except Exception as e:
        st.error(f"Error: {e}")

    if st.button("Continue to Rewards", key="btn_continue_step6"):
        st.session_state.workflow_step = 6
        st.rerun()


def render_step_distribute_rewards():
    """Step 6: Distribute Rewards"""
    st.title("Step 6: Distribute Rewards")

    tournament_id = st.session_state.get('tournament_id')
    if not tournament_id:
        st.error("No tournament selected")
        return

    st.info("Distribute credits and XP to tournament participants based on final rankings.")

    if st.button("Distribute Rewards", key="btn_distribute_rewards", use_container_width=True):
        with Loading.spinner("Distributing rewards..."):
            try:
                # First complete tournament
                complete_response = api_client.post(f"/tournaments/{tournament_id}/complete")

                if complete_response.status_code == 200:
                    # Then distribute rewards
                    response = api_client.post(
                        f"/tournaments/{tournament_id}/distribute-rewards",
                        json={"reason": "Tournament completion"}
                    )

                    if response.status_code == 200:
                        Success.toast("✅ Rewards distributed!")
                        time.sleep(0.5)
                        st.session_state.workflow_step = 7
                        st.rerun()
                    else:
                        Error.toast(f"Failed to distribute: {response.status_code}")
                        st.error(response.text)
                else:
                    Error.toast(f"Failed to complete tournament: {complete_response.status_code}")
                    st.error(complete_response.text)
            except Exception as e:
                Error.toast(f"Error: {e}")


def render_step_view_rewards():
    """Step 7: View Rewards"""
    st.title("Step 7: View Rewards")

    tournament_id = st.session_state.get('tournament_id')
    if not tournament_id:
        st.error("No tournament selected")
        return

    st.success("🎉 Tournament Complete!")
    st.balloons()

    st.info("Rewards have been distributed. Check participant accounts for updated credits and XP.")

    if st.button("Back to Home", key="btn_back_home"):
        st.session_state.screen = "home"
        st.session_state.workflow_step = 1
        st.rerun()
