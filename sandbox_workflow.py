"""
Tournament Workflow Steps Module

Contains all 6 instructor workflow steps for tournament management.
Each step uses the component library for consistent UX and E2E testing.
"""

import streamlit as st
import requests
import logging
from typing import Dict
from streamlit_components.core import api_client, APIError
from streamlit_components.layouts import SingleColumnForm
from streamlit_components.feedback import Loading, Success, Error
from sandbox_helpers import render_mini_leaderboard, fetch_tournament_sessions

API_BASE_URL = "http://localhost:8000/api/v1"

# Configure logging
logger = logging.getLogger(__name__)


def render_step_create_tournament(config: Dict):
    """
    Step 1: Create tournament with configuration

    This step:
    - Displays tournament configuration
    - Creates tournament via API
    - Enrolls participants
    - Generates sessions
    - Moves to next step

    ✅ FIX: Removed st.columns() to prevent form rendering interference
    """
    st.markdown("### 1. Create Tournament")

    # ✅ VALIDATION MARKER
    # TEMPORARILY DISABLED ALL PREVIEW WIDGETS FOR DEBUGGING FORM ISSUE
    # TODO: Re-enable after form works
    pass

    # ✅ FORM: Create Tournament button
    with st.form(key="form_create_tournament", clear_on_submit=False):
        st.markdown("### Ready to Create Tournament")
        st.info("Click below to create the tournament with the configuration shown above.")
        create_clicked = st.form_submit_button(
            "Create Tournament",
            type="primary",
            use_container_width=True
        )

    # Handle form submission
    if create_clicked:
        st.write("🔧 DEBUG: Form button clicked!")
        with st.spinner("Creating tournament..."):
            try:
                st.write("🔧 DEBUG: Entered try block")
                # Use clean tournament creation endpoint (production entry point)
                selected_users = config.get("selected_users", [])
                st.write(f"🔧 DEBUG: selected_users = {len(selected_users)}")

                # If no users selected, use test STUDENT users with LFA_FOOTBALL_PLAYER licenses
                if not selected_users:
                    max_players = config.get("max_players", 8)
                    # Test students: ID 4-7, 13-18 (all have licenses, verified above)
                    test_students = [4, 5, 6, 7, 13, 14, 15, 16, 17, 18]
                    selected_users = test_students[:max_players]
                    st.write(f"🔧 DEBUG: Using {len(selected_users)} test students: {selected_users}")

                st.write(f"🔧 DEBUG: config keys available: {list(config.keys())}")

                # Map frontend tournament_format to API tournament_type codes
                format_to_api_type = {
                    "HEAD_TO_HEAD": "league",
                    "league": "league",
                    "knockout": "knockout",
                    "GROUP_KNOCKOUT": "hybrid",
                    "group_knockout": "hybrid",
                    "hybrid": "hybrid"
                }

                tournament_format = config.get("tournament_format", "league")
                api_tournament_type = format_to_api_type.get(tournament_format, "league")

                # Build reward configuration
                reward_config = []
                rewards = config.get("rewards", {})
                for rank_key, reward_data in rewards.items():
                    if rank_key.startswith("rank_"):
                        rank_num = int(rank_key.split("_")[1])
                        reward_config.append({
                            "rank": rank_num,
                            "xp_reward": reward_data.get("xp", 0),
                            "credits_reward": reward_data.get("credits", 0)
                        })

                # Fallback rewards if not configured
                if not reward_config:
                    reward_config = [
                        {"rank": 1, "xp_reward": 100, "credits_reward": 50},
                        {"rank": 2, "xp_reward": 75, "credits_reward": 30},
                        {"rank": 3, "xp_reward": 50, "credits_reward": 20}
                    ]

                # Build clean API payload
                api_payload = {
                    "name": config.get("tournament_name", "LFA Sandbox Tournament"),
                    "tournament_type": api_tournament_type,
                    "age_group": config.get("age_group", "PRE"),
                    "max_players": config.get("max_players", 8),
                    "skills_to_test": config["skills_to_test"],
                    "reward_config": reward_config,
                    "game_preset_id": config.get("game_preset_id"),
                    "game_config": {
                        "scoring_mode": config.get("scoring_mode"),
                        "number_of_rounds": config.get("number_of_rounds"),
                        "scoring_type": config.get("scoring_type"),
                        "ranking_direction": config.get("ranking_direction"),
                        "measurement_unit": config.get("measurement_unit")
                    } if config.get("scoring_mode") else None,
                    "enrollment_cost": 0  # Free for sandbox testing
                }

                headers = {"Content-Type": "application/json"}
                if "auth_token" in st.session_state:
                    headers["Authorization"] = f"Bearer {st.session_state.auth_token}"

                st.write(f"🔧 DEBUG: Calling API with payload keys: {list(api_payload.keys())}")
                st.write(f"🔧 DEBUG: tournament_type={api_payload['tournament_type']}, max_players={api_payload['max_players']}")

                response = requests.post(
                    f"{API_BASE_URL}/tournaments/create",
                    json=api_payload,
                    headers=headers
                )

                st.write(f"🔧 DEBUG: API response status={response.status_code}")

                if response.status_code in [200, 201]:
                    result = response.json()
                    tournament_id = result.get("tournament_id")

                    if not tournament_id:
                        st.error(f"Tournament created but ID missing. Response: {str(result)[:200]}")
                        return

                    st.success(f"✅ Tournament created successfully! ID: {tournament_id}")

                    # Enroll participants
                    if selected_users:
                        st.info(f"Enrolling {len(selected_users)} participants...")

                        enroll_payload = {"player_ids": selected_users}
                        enroll_response = requests.post(
                            f"{API_BASE_URL}/tournaments/{tournament_id}/admin/batch-enroll",
                            json=enroll_payload,
                            headers=headers
                        )

                        if enroll_response.status_code in [200, 201]:
                            enroll_data = enroll_response.json()
                            enrolled_count = enroll_data.get("enrolled_count", 0)
                            st.success(f"✅ Enrolled {enrolled_count} participants")
                        else:
                            try:
                                error_data = enroll_response.json()
                                error_msg = error_data.get("detail", str(error_data))
                            except:
                                error_msg = enroll_response.text[:500]
                            st.error(f"Failed to enroll participants (HTTP {enroll_response.status_code}): {error_msg}")
                            return
                    else:
                        st.warning("No participants to enroll")

                    # Store tournament_id in session state
                    st.session_state.tournament_id = tournament_id
                    st.session_state.workflow_step = 2

                    st.info("Proceeding to Session Management...")
                    st.rerun()
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("detail", str(error_data))
                    except:
                        error_msg = response.text[:500]
                    st.error(f"Failed to create tournament (HTTP {response.status_code}): {error_msg}")

            except Exception as e:
                import traceback
                st.error(f"❌ Error creating tournament: {str(e)}")
                st.code(traceback.format_exc())
                st.write(f"🔧 DEBUG: Exception type: {type(e).__name__}")


def render_step_manage_sessions():
    """
    Step 2: Session Management

    Generates tournament sessions if not already generated.
    """
    tournament_id = st.session_state.get('tournament_id')
    st.markdown("### 2. Manage Sessions")

    # Check if sessions already generated
    sessions_generated = st.session_state.get('sessions_generated', False)

    if not sessions_generated:
        st.info("Generating tournament sessions...")

        try:
            headers = {"Content-Type": "application/json"}
            if "auth_token" in st.session_state:
                headers["Authorization"] = f"Bearer {st.session_state.auth_token}"

            session_payload = {
                "parallel_fields": 1,
                "session_duration_minutes": 90,
                "break_minutes": 15,
                "number_of_rounds": 1
            }

            session_response = requests.post(
                f"{API_BASE_URL}/tournaments/{tournament_id}/generate-sessions",
                json=session_payload,
                headers=headers
            )

            if session_response.status_code in [200, 201]:
                session_data = session_response.json()
                sessions_created = session_data.get("total_sessions", 0)
                st.success(f"✅ Generated {sessions_created} tournament sessions")
                st.session_state.sessions_generated = True
            else:
                try:
                    error_data = session_response.json()
                    error_msg = error_data.get("detail", str(error_data))
                except:
                    error_msg = session_response.text[:500]
                st.error(f"Failed to generate sessions (HTTP {session_response.status_code}): {error_msg}")
                st.warning("Cannot proceed without sessions. Please fix the issue and try again.")
                if st.button("← Back to Step 1"):
                    st.session_state.workflow_step = 1
                    st.rerun()
                return

        except Exception as e:
            st.error(f"Error generating sessions: {str(e)}")
            if st.button("← Back to Step 1"):
                st.session_state.workflow_step = 1
                st.rerun()
            return

    else:
        st.success(f"✅ Sessions already generated for tournament #{tournament_id}")

    # Navigation
    if st.button("← Back to Step 1"):
        st.session_state.workflow_step = 1
        st.rerun()

    if st.button("Continue to Attendance →"):
        st.session_state.workflow_step = 3
        st.rerun()


def render_step_track_attendance():
    """Step 3: Mark Attendance"""
    tournament_id = st.session_state.get('tournament_id')
    st.markdown("### 3. Mark Attendance")
    st.info(f"Attendance for tournament #{tournament_id}")

    # Navigation
    if st.button("← Back to Step 2"):
        st.session_state.workflow_step = 2
        st.rerun()

    if st.button("Continue to Enter Results →"):
        st.session_state.workflow_step = 4
        st.rerun()


def render_step_enter_results():
    """
    Step 4: Enter Results for All Tournament Matches

    For Group+Knockout tournaments:
    1. Fetch all sessions for the tournament
    2. Display Group Stage matches (9 matches for 7 players)
    3. Allow result submission for each match
    4. Provide "Finalize Group Stage" button
    5. Display Knockout Stage matches (3 matches)
    6. Allow result submission for knockout matches
    """
    tournament_id = st.session_state.get('tournament_id')
    st.markdown("### 4. Enter Results")

    # Fetch tournament sessions
    try:
        headers = {"Content-Type": "application/json"}
        has_token = "auth_token" in st.session_state
        if has_token:
            headers["Authorization"] = f"Bearer {st.session_state.auth_token}"

        # 🔍 DEBUG: Log auth state
        print(f"📡 [STEP 4 API] Calling /tournaments/{tournament_id}/sessions")
        print(f"📡 [STEP 4 API] Has auth_token: {has_token}")
        if has_token:
            print(f"📡 [STEP 4 API] Token length: {len(st.session_state.auth_token)}")

        response = requests.get(
            f"{API_BASE_URL}/tournaments/{tournament_id}/sessions",
            headers=headers
        )

        # 🔍 DEBUG: Log API response
        print(f"📡 [STEP 4 API] Response status: {response.status_code}")
        st.write(f"🔧 DEBUG: API Response Status = {response.status_code}")

        if response.status_code != 200:
            st.error(f"Failed to fetch sessions (HTTP {response.status_code})")
            st.write(f"🔧 DEBUG: Response Text = {response.text[:500]}")
            return

        sessions = response.json()

        # 🔍 DEBUG: Log fetched sessions count
        st.write(f"🔧 DEBUG: Total sessions fetched = {len(sessions)}")
        st.write(f"🔧 DEBUG: Session IDs = {[s.get('id') for s in sessions][:10]}")  # First 10
        st.write(f"🔧 DEBUG: Tournament phases = {list(set([s.get('tournament_phase') for s in sessions]))}")

        # Separate Group Stage and Knockout sessions (using canonical enum values)
        group_sessions = [s for s in sessions if s.get('tournament_phase') == 'GROUP_STAGE']
        knockout_sessions = [s for s in sessions if s.get('tournament_phase') == 'KNOCKOUT']

        # 🔍 DEBUG: Log separated counts
        st.write(f"🔧 DEBUG: Group Stage sessions = {len(group_sessions)}")
        st.write(f"🔧 DEBUG: Knockout sessions = {len(knockout_sessions)}")

        # 🔍 DEBUG: Inspect first group session
        if group_sessions:
            first_session = group_sessions[0]
            st.write(f"🔧 DEBUG: First session keys = {list(first_session.keys())}")
            st.write(f"🔧 DEBUG: participant_user_ids = {first_session.get('participant_user_ids')}")
            st.write(f"🔧 DEBUG: game_results = {first_session.get('game_results')}")

        # ============================================================================
        # GROUP STAGE MATCHES
        # ============================================================================
        st.markdown("#### 🏆 Group Stage Matches")
        st.caption(f"Total: {len(group_sessions)} matches")

        if group_sessions:
            for session in group_sessions:
                session_id = session['id']
                title = session.get('title', f"Match #{session_id}")
                participants = session.get('participant_user_ids', [])
                game_results = session.get('game_results')

                # Display match card
                st.markdown(f"**{title}**")

                if len(participants) == 2:
                    # Get participant names (simplified - using IDs for now)
                    p1_id = participants[0]
                    p2_id = participants[1]

                    # Check if result already submitted
                    if game_results:
                        st.success(f"✅ Result submitted for Session {session_id}")
                        if isinstance(game_results, dict):
                            raw_results = game_results.get('raw_results', [])
                            if len(raw_results) == 2:
                                st.text(f"Player {raw_results[0]['user_id']}: {raw_results[0]['score']} points")
                                st.text(f"Player {raw_results[1]['user_id']}: {raw_results[1]['score']} points")
                    else:
                        # Result submission form
                        with st.form(key=f"form_match_{session_id}"):
                            st.text(f"Player 1 ID: {p1_id}")
                            p1_score = st.number_input(f"Player 1 Score", min_value=0, value=0, key=f"p1_score_{session_id}")

                            st.text(f"Player 2 ID: {p2_id}")
                            p2_score = st.number_input(f"Player 2 Score", min_value=0, value=0, key=f"p2_score_{session_id}")

                            submit_result = st.form_submit_button("Submit Result", type="primary")

                        if submit_result:
                            # Submit result via API
                            payload = {
                                "results": [
                                    {"user_id": p1_id, "score": p1_score},
                                    {"user_id": p2_id, "score": p2_score}
                                ]
                            }

                            result_response = requests.patch(
                                f"{API_BASE_URL}/sessions/{session_id}/head-to-head-results",
                                json=payload,
                                headers=headers
                            )

                            if result_response.status_code == 200:
                                st.success(f"✅ Result submitted for Session {session_id}")
                                st.rerun()
                            else:
                                try:
                                    error_data = result_response.json()
                                    error_msg = error_data.get('detail', str(error_data))
                                except:
                                    error_msg = result_response.text[:500]
                                st.error(f"Failed to submit result (HTTP {result_response.status_code}): {error_msg}")
                else:
                    participant_count = len(participants) if isinstance(participants, list) else 0
                    st.warning(f"⚠️ Invalid participant count: {participant_count}")

                st.markdown("---")

        # ============================================================================
        # FINALIZE GROUP STAGE BUTTON
        # ============================================================================
        all_group_results_submitted = all(s.get('game_results') is not None for s in group_sessions)

        if group_sessions and all_group_results_submitted:
            st.markdown("#### ✅ All Group Stage Results Submitted")

            with st.form(key="form_finalize_group_stage"):
                st.info("Finalize the group stage to generate knockout matches")
                finalize_clicked = st.form_submit_button("Finalize Group Stage", type="primary")

            if finalize_clicked:
                finalize_response = requests.post(
                    f"{API_BASE_URL}/tournaments/{tournament_id}/finalize-group-stage",
                    headers=headers
                )

                if finalize_response.status_code in [200, 201]:
                    st.success("✅ Group Stage finalized successfully!")
                    st.info("Knockout matches have been generated")
                    st.rerun()
                else:
                    try:
                        error_data = finalize_response.json()
                        error_msg = error_data.get('detail', str(error_data))
                    except:
                        error_msg = finalize_response.text[:500]
                    st.error(f"Failed to finalize group stage (HTTP {finalize_response.status_code}): {error_msg}")

        # ============================================================================
        # KNOCKOUT STAGE MATCHES
        # ============================================================================
        if knockout_sessions:
            st.markdown("#### 🏆 Knockout Stage Matches")
            st.caption(f"Total: {len(knockout_sessions)} matches")

            for session in knockout_sessions:
                session_id = session['id']
                title = session.get('title', f"Match #{session_id}")
                participants = session.get('participant_user_ids') or []  # Handle None explicitly
                game_results = session.get('game_results')

                # ✅ FIX: ALWAYS show match title and container (even for TBD matches)
                st.markdown(f"**{title}**")

                # Case 1: Match has results submitted
                if game_results:
                    st.success(f"✅ Result submitted for Session {session_id}")
                    if isinstance(game_results, dict):
                        raw_results = game_results.get('raw_results', [])
                        if len(raw_results) == 2:
                            st.text(f"Player {raw_results[0]['user_id']}: {raw_results[0]['score']} points")
                            st.text(f"Player {raw_results[1]['user_id']}: {raw_results[1]['score']} points")

                # Case 2: Match has participants ready (can submit results)
                elif isinstance(participants, list) and len(participants) == 2:
                    p1_id = participants[0]
                    p2_id = participants[1]

                    with st.form(key=f"form_knockout_{session_id}"):
                        st.text(f"Player 1 ID: {p1_id}")
                        p1_score = st.number_input(f"Player 1 Score", min_value=0, value=0, key=f"ko_p1_{session_id}")

                        st.text(f"Player 2 ID: {p2_id}")
                        p2_score = st.number_input(f"Player 2 Score", min_value=0, value=0, key=f"ko_p2_{session_id}")

                        submit_knockout = st.form_submit_button("Submit Result", type="primary")

                    if submit_knockout:
                        payload = {
                            "results": [
                                {"user_id": p1_id, "score": p1_score},
                                {"user_id": p2_id, "score": p2_score}
                            ]
                        }

                        ko_response = requests.patch(
                            f"{API_BASE_URL}/sessions/{session_id}/head-to-head-results",
                            json=payload,
                            headers=headers
                        )

                        if ko_response.status_code == 200:
                            st.success(f"✅ Result submitted for Session {session_id}")
                            st.rerun()
                        else:
                            try:
                                error_data = ko_response.json()
                                error_msg = error_data.get('detail', str(error_data))
                            except:
                                error_msg = ko_response.text[:500]
                            st.error(f"Failed to submit result (HTTP {ko_response.status_code}): {error_msg}")

                # Case 3: Match is TBD (participants not yet determined from previous round)
                else:
                    participant_count = len(participants) if isinstance(participants, list) else 0
                    st.info(f"⏳ Waiting for previous round to complete (participants: {participant_count}/2)")

                st.markdown("---")

        # ============================================================================
        # NAVIGATION
        # ============================================================================
        all_knockout_submitted = all(s.get('game_results') is not None for s in knockout_sessions) if knockout_sessions else False

        if all_group_results_submitted and all_knockout_submitted:
            st.success("✅ All match results submitted")
            if st.button("Continue to Leaderboard →", type="primary"):
                st.session_state.workflow_step = 5
                st.rerun()

        if st.button("← Back to Step 3"):
            st.session_state.workflow_step = 3
            st.rerun()

    except Exception as e:
        st.error(f"Error loading sessions: {str(e)}")
        if st.button("← Back to Step 3"):
            st.session_state.workflow_step = 3
            st.rerun()


def render_step_view_leaderboard():
    """
    Step 5: View Tournament Leaderboard

    Displays final standings for the tournament using the instructor leaderboard endpoint.
    """
    tournament_id = st.session_state.get('tournament_id')
    st.markdown("### 5. View Leaderboard")

    # Fetch leaderboard
    try:
        headers = {"Content-Type": "application/json"}
        if "auth_token" in st.session_state:
            headers["Authorization"] = f"Bearer {st.session_state.auth_token}"

        response = requests.get(
            f"{API_BASE_URL}/tournaments/{tournament_id}/leaderboard",
            headers=headers
        )

        if response.status_code != 200:
            st.error(f"Failed to fetch leaderboard (HTTP {response.status_code})")
            return

        data = response.json()

        # Display tournament info
        st.markdown(f"#### 🏆 {data.get('tournament_name', 'Tournament')} - Final Standings")
        st.caption(f"Format: {data.get('tournament_format', 'N/A')} | Status: {data.get('tournament_status', 'N/A')}")

        # Display match statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Matches", data.get('total_matches', 0))
        with col2:
            st.metric("Completed", data.get('completed_matches', 0))
        with col3:
            st.metric("Remaining", data.get('remaining_matches', 0))

        st.markdown("---")

        # Display final standings
        final_standings = data.get('final_standings', [])

        if final_standings:
            st.markdown("#### 🥇 Final Standings")

            for standing in final_standings:
                rank = standing.get('rank', '—')
                name = standing.get('name', 'Unknown Player')
                user_id = standing.get('user_id', '—')
                score = standing.get('score', 0)

                if rank == 1:
                    st.markdown(f"**🥇 #{rank} - {name}** (User ID: {user_id}) - Score: {score}")
                elif rank == 2:
                    st.markdown(f"**🥈 #{rank} - {name}** (User ID: {user_id}) - Score: {score}")
                elif rank == 3:
                    st.markdown(f"**🥉 #{rank} - {name}** (User ID: {user_id}) - Score: {score}")
                else:
                    st.markdown(f"**#{rank} - {name}** (User ID: {user_id}) - Score: {score}")

        else:
            # Fallback to leaderboard if final_standings not available
            leaderboard = data.get('leaderboard', [])

            if leaderboard:
                st.markdown("#### 📊 Leaderboard")

                for entry in leaderboard:
                    rank = entry.get('rank', '—')
                    name = entry.get('name', 'Unknown Player')
                    user_id = entry.get('user_id', '—')
                    wins = entry.get('wins', 0)
                    total_score = entry.get('total_score', 0)

                    if rank == 1:
                        st.markdown(f"**🥇 #{rank} - {name}** (ID: {user_id}) - Wins: {wins}, Total Score: {total_score}")
                    elif rank == 2:
                        st.markdown(f"**🥈 #{rank} - {name}** (ID: {user_id}) - Wins: {wins}, Total Score: {total_score}")
                    elif rank == 3:
                        st.markdown(f"**🥉 #{rank} - {name}** (ID: {user_id}) - Wins: {wins}, Total Score: {total_score}")
                    else:
                        st.markdown(f"**#{rank} - {name}** (ID: {user_id}) - Wins: {wins}, Total Score: {total_score}")
            else:
                st.info("No leaderboard data available yet")

        st.markdown("---")

        # Navigation
        if st.button("← Back to Step 4"):
            st.session_state.workflow_step = 4
            st.rerun()

        if st.button("Continue to Complete Tournament →", type="primary"):
            st.session_state.workflow_step = 6
            st.rerun()

    except Exception as e:
        st.error(f"Error loading leaderboard: {str(e)}")
        if st.button("← Back to Step 4"):
            st.session_state.workflow_step = 4
            st.rerun()


def render_step_distribute_rewards():
    """
    Step 6: Complete Tournament and Distribute Rewards

    This step:
    1. Marks tournament as COMPLETED
    2. Triggers reward distribution
    3. Moves to Step 7 to view distributed rewards
    """
    logger.info("🔷 [STEP 6 ENTRY] render_step_distribute_rewards() started")

    tournament_id = st.session_state.get('tournament_id')
    logger.info(f"🔷 [STEP 6] tournament_id={tournament_id}")

    st.markdown("### 6. Complete Tournament & Distribute Rewards")
    logger.info("🔷 [STEP 6] Title rendered")

    st.info("Complete the tournament to finalize standings and distribute rewards to winners.")
    logger.info("🔷 [STEP 6] Info message rendered")

    # Complete Tournament Form
    logger.info("🔷 [STEP 6] Creating form")
    with st.form(key="form_complete_tournament"):
        logger.info("🔷 [STEP 6] Inside form context")
        st.markdown("#### ✅ Ready to Complete Tournament")
        st.caption("This action will:")
        st.caption("• Mark the tournament as COMPLETED")
        st.caption("• Lock all results (no further changes allowed)")
        st.caption("• Distribute rewards to winners based on final standings")
        logger.info("🔷 [STEP 6] Form content rendered")

        complete_clicked = st.form_submit_button("Complete Tournament", type="primary", use_container_width=True)
        logger.info("🔷 [STEP 6] Form submit button created")

    if complete_clicked:
        # DEBUG: Log that callback was triggered
        import sys
        logger.info(f"🔥 DEBUG: complete_clicked callback triggered! tournament_id={tournament_id}")

        try:
            headers = {"Content-Type": "application/json"}
            if "auth_token" in st.session_state:
                headers["Authorization"] = f"Bearer {st.session_state.auth_token}"
                logger.info(f"🔥 DEBUG: Has auth_token")
            else:
                logger.info(f"🔥 DEBUG: NO auth_token in session_state!")

            # Complete tournament
            logger.info(f"🔥 DEBUG: Calling /tournaments/{tournament_id}/complete")
            complete_response = requests.post(
                f"{API_BASE_URL}/tournaments/{tournament_id}/complete",
                headers=headers
            )
            logger.info(f"🔥 DEBUG: Complete response status={complete_response.status_code}")

            if complete_response.status_code in [200, 201]:
                logger.info(f"🔥 DEBUG: Complete API success, showing st.success()")
                st.success("✅ Tournament completed successfully!")
                logger.info(f"🔥 DEBUG: st.success() completed")

                # Distribute rewards
                logger.info(f"🔥 DEBUG: Showing st.info() for rewards")
                st.info("Distributing rewards...")
                logger.info(f"🔥 DEBUG: st.info() completed, calling distribute-rewards API")

                rewards_response = requests.post(
                    f"{API_BASE_URL}/tournaments/{tournament_id}/distribute-rewards",
                    headers=headers,
                    json={}  # Empty body - all fields are optional
                )
                logger.info(f"🔥 DEBUG: Rewards API response status={rewards_response.status_code}")

                if rewards_response.status_code in [200, 201]:
                    logger.info(f"🔥 DEBUG: Rewards API success, showing st.success()")
                    st.success("✅ Rewards distributed successfully!")
                    logger.info(f"🔥 DEBUG: Setting workflow_step=7")
                    st.session_state.workflow_step = 7

                    # Sync URL with session state to prevent query param from overwriting
                    logger.info(f"🔥 DEBUG: Syncing URL query param to step=7")
                    st.query_params["step"] = "7"

                    logger.info(f"🔥 DEBUG: Calling st.rerun()")
                    st.rerun()
                    logger.info(f"🔥 DEBUG: st.rerun() returned (should never see this)")
                else:
                    try:
                        error_data = rewards_response.json()
                        error_msg = error_data.get('detail', str(error_data))
                    except:
                        error_msg = rewards_response.text[:500]
                    st.warning(f"Tournament completed but reward distribution failed (HTTP {rewards_response.status_code}): {error_msg}")

            else:
                try:
                    error_data = complete_response.json()
                    error_msg = error_data.get('detail', str(error_data))
                except:
                    error_msg = complete_response.text[:500]
                st.error(f"Failed to complete tournament (HTTP {complete_response.status_code}): {error_msg}")

        except Exception as e:
            st.error(f"Error completing tournament: {str(e)}")

    # Navigation
    logger.info("🔷 [STEP 6] Creating navigation button")
    if st.button("← Back to Step 5"):
        logger.info("🔷 [STEP 6] Back button clicked")
        st.session_state.workflow_step = 5
        st.rerun()

    logger.info("🔷 [STEP 6 EXIT] render_step_distribute_rewards() completed")


def render_step_view_rewards():
    """
    Step 7: View Distributed Rewards

    Displays all rewards distributed to tournament winners.
    """
    tournament_id = st.session_state.get('tournament_id')
    st.markdown("### 7. View Distributed Rewards")

    # Fetch distributed rewards
    try:
        headers = {"Content-Type": "application/json"}
        if "auth_token" in st.session_state:
            headers["Authorization"] = f"Bearer {st.session_state.auth_token}"

        response = requests.get(
            f"{API_BASE_URL}/tournaments/{tournament_id}/distributed-rewards",
            headers=headers
        )

        if response.status_code == 200:
            data = response.json()

            st.success("✅ Tournament completed successfully!")

            # Display rewards summary
            rewards = data.get('rewards', [])

            if rewards:
                st.markdown("#### 🏅 Rewards Distributed")

                for reward in rewards:
                    user_id = reward.get('user_id', '—')
                    user_name = reward.get('user_name', 'Unknown Player')
                    rank = reward.get('rank', '—')
                    xp_awarded = reward.get('xp_awarded', 0)
                    credits_awarded = reward.get('credits_awarded', 0)

                    # Display reward card
                    st.markdown(f"**Rank #{rank}: {user_name}** (User ID: {user_id})")
                    st.text(f"  • XP: +{xp_awarded}")
                    st.text(f"  • Credits: +{credits_awarded}")
                    st.markdown("---")

                # Summary statistics
                total_xp = sum(r.get('xp_awarded', 0) for r in rewards)
                total_credits = sum(r.get('credits_awarded', 0) for r in rewards)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Winners Rewarded", len(rewards))
                with col2:
                    st.metric("Total XP Distributed", total_xp)
                with col3:
                    st.metric("Total Credits Distributed", total_credits)

            else:
                st.info("No rewards data available")

        else:
            st.warning(f"Could not fetch rewards (HTTP {response.status_code})")

    except Exception as e:
        st.error(f"Error loading rewards: {str(e)}")

    st.markdown("---")

    # Navigation
    if st.button("← Back to Step 6"):
        st.session_state.workflow_step = 6
        st.rerun()

    if st.button("🏁 Finish & Return Home", type="primary"):
        st.session_state.screen = "home"
        st.session_state.workflow_step = 1
        st.rerun()
