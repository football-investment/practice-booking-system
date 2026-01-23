"""
Tournament List Module - Tournament listing and game management
"""

import streamlit as st
from pathlib import Path
import sys
from typing import List, Dict
import requests
from datetime import datetime, date
from datetime import time as dt_time
import time as time_module
import psycopg2
import json
import os

# Setup path
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

# Import config and helpers
from config import API_BASE_URL, API_TIMEOUT
from api_helpers_general import get_semesters
from api_helpers_tournaments import (
    update_tournament,
    get_tournament_enrollment_count,
    generate_tournament_sessions,
    preview_tournament_sessions,
    delete_generated_sessions
)
from components.admin.tournament_constants import GAME_TYPE_OPTIONS
from components.admin.tournament_approval import render_instructor_applications_section
from components.admin.tournament_creation import (
    render_reward_distribution_section,
    show_close_enrollment_dialog,
    show_start_tournament_dialog
)


def get_user_names_from_db(user_ids: List[int]) -> Dict[int, str]:
    """
    Fetch user names from database by IDs.
    Returns dict: {user_id: "Name (email)"}
    """
    try:
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        if not user_ids:
            return {}

        query = """
            SELECT id, name, email
            FROM users
            WHERE id = ANY(%s)
        """
        cursor.execute(query, (user_ids,))
        rows = cursor.fetchall()

        user_names = {}
        for row in rows:
            user_id, name, email = row
            display_name = f"{name} ({email})" if name else email
            user_names[user_id] = display_name

        cursor.close()
        conn.close()

        return user_names

    except Exception as e:
        st.error(f"❌ Error fetching user names: {str(e)}")
        return {}


def get_tournament_sessions_from_db(tournament_id: int) -> List[Dict]:
    """
    Fetch tournament sessions directly from database with all tournament-specific fields.
    This bypasses the API schema limitations.
    """
    try:
        # Get database connection string
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")

        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        query = """
            SELECT
                id,
                title,
                tournament_phase,
                tournament_round,
                group_identifier,
                match_format,
                scoring_type,
                participant_user_ids,
                structure_config,
                session_status
            FROM sessions
            WHERE semester_id = %s
            AND auto_generated = true
            ORDER BY id
        """

        cursor.execute(query, (tournament_id,))
        rows = cursor.fetchall()

        sessions = []
        for row in rows:
            sessions.append({
                'id': row[0],
                'title': row[1],
                'tournament_phase': row[2],
                'tournament_round': row[3],
                'group_identifier': row[4],
                'match_format': row[5],
                'scoring_type': row[6],
                'participant_user_ids': row[7] if row[7] else [],
                'structure_config': row[8] if row[8] else {},
                'session_status': row[9]
            })

        cursor.close()
        conn.close()

        return sessions

    except Exception as e:
        st.error(f"❌ Database error: {str(e)}")
        return []


def render_tournament_list(token: str):
    """Display list of all tournaments"""

    st.subheader("📋 All Tournaments")

    # Fetch all semesters
    success, semesters = get_semesters(token)

    if not success:
        st.error("Failed to load tournaments")
        return

    # Filter for tournaments (TOURN- prefix)
    tournaments = [s for s in semesters if s.get('code', '').startswith('TOURN-')]

    if not tournaments:
        st.info("No tournaments found")
        return

    # Display tournaments
    for tournament in tournaments:
        with st.expander(f"🏆 {tournament.get('name', 'Unknown')} ({tournament.get('code', 'N/A')})"):
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                st.write(f"**Status**: {tournament.get('status', 'N/A')}")

                # Show tournament status with assignment type indicator
                tournament_status = tournament.get('tournament_status', 'N/A')
                assignment_type = tournament.get('assignment_type', 'UNKNOWN')

                if tournament_status == 'SEEKING_INSTRUCTOR':
                    if assignment_type == 'APPLICATION_BASED':
                        st.write(f"**Tournament Status**: 📝 {tournament_status}")
                        st.caption("Instructors can apply")
                    elif assignment_type == 'OPEN_ASSIGNMENT':
                        st.write(f"**Tournament Status**: 🔒 {tournament_status}")
                        st.caption("Admin assigns directly")
                    else:
                        st.write(f"**Tournament Status**: {tournament_status}")
                else:
                    st.write(f"**Tournament Status**: {tournament_status}")

                st.write(f"**Start**: {tournament.get('start_date', 'N/A')}")
                st.write(f"**End**: {tournament.get('end_date', 'N/A')}")

            with col2:
                st.write(f"**Age Category**: {tournament.get('age_group', 'N/A')}")

                # Highlight assignment type
                assignment_type = tournament.get('assignment_type', 'N/A')
                if assignment_type == 'APPLICATION_BASED':
                    st.write(f"**Assignment Type**: 📝 {assignment_type}")
                elif assignment_type == 'OPEN_ASSIGNMENT':
                    st.write(f"**Assignment Type**: 🔒 {assignment_type}")
                else:
                    st.write(f"**Assignment Type**: {assignment_type}")

                # ✅ Show assigned instructor
                instructor_id = tournament.get('master_instructor_id')
                instructor_name = tournament.get('master_instructor_name')
                instructor_email = tournament.get('master_instructor_email')

                if instructor_id and instructor_name:
                    st.write(f"**👨‍🏫 Instructor**: {instructor_name} ({instructor_email})")
                elif instructor_id:
                    st.write(f"**👨‍🏫 Instructor**: Assigned (ID: {instructor_id})")
                else:
                    st.write(f"**👨‍🏫 Instructor**: Not assigned")

                # ✅ Show enrollment count with min/max requirements
                enrollment_count = get_tournament_enrollment_count(token, tournament['id'])
                max_players = tournament.get('max_players', 'N/A')

                # Get tournament type info for min players requirement
                tournament_type_id = tournament.get('tournament_type_id')
                min_players_requirement = "?"
                if tournament_type_id:
                    # Fetch tournament type to get min_players
                    try:
                        import requests
                        response = requests.get(
                            f"{API_BASE_URL}/api/v1/tournament-types/{tournament_type_id}",
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=API_TIMEOUT
                        )
                        if response.status_code == 200:
                            tournament_type = response.json()
                            min_players_requirement = tournament_type.get('min_players', '?')
                    except:
                        pass

                # Color code based on requirements with helpful tooltips
                if isinstance(min_players_requirement, int):
                    if enrollment_count < min_players_requirement:
                        # Below minimum - show red indicator with explanation
                        col_enroll, col_info = st.columns([4, 1])
                        with col_enroll:
                            st.write(f"**Enrollments**: 🔴 {enrollment_count}/{max_players}")
                        with col_info:
                            st.markdown(
                                f"ℹ️",
                                help=f"Minimum {min_players_requirement} players required to start this tournament type. Currently {min_players_requirement - enrollment_count} more needed."
                            )
                        st.caption(f"⚠️ Need {min_players_requirement - enrollment_count} more players to start!")
                    else:
                        # Meets minimum - show green indicator
                        col_enroll, col_info = st.columns([4, 1])
                        with col_enroll:
                            st.write(f"**Enrollments**: ✅ {enrollment_count}/{max_players}")
                        with col_info:
                            st.markdown(
                                f"ℹ️",
                                help=f"Minimum requirement met ({min_players_requirement} players). Tournament can be started."
                            )
                else:
                    st.write(f"**Enrollments**: {enrollment_count}/{max_players}")

                st.write(f"**Enrollment Cost**: {tournament.get('enrollment_cost', 0)} credits")

                # Show schedule configuration if set
                match_duration = tournament.get('match_duration_minutes')
                break_duration = tournament.get('break_duration_minutes')
                parallel_fields = tournament.get('parallel_fields')
                if match_duration or break_duration or parallel_fields:
                    st.divider()
                    st.caption("⚙️ **Match Schedule Configuration**")
                    if match_duration:
                        st.caption(f"   • Match Duration: {match_duration} min")
                    if break_duration:
                        st.caption(f"   • Break Duration: {break_duration} min")
                    if parallel_fields:
                        st.caption(f"   • Parallel Fields: {parallel_fields} pitch{'es' if parallel_fields > 1 else ''}")

            with col3:
                btn_col1, btn_col2, btn_col3 = st.columns(3)
                with btn_col1:
                    if st.button("✏️", key=f"edit_tournament_{tournament['id']}", help="Edit tournament"):
                        st.session_state['edit_tournament_id'] = tournament['id']
                        st.session_state['edit_tournament_data'] = tournament
                        show_edit_tournament_dialog()
                with btn_col2:
                    # Show schedule edit button BEFORE session generation (admin sets schedule as INPUT for generator)
                    # Available until enrollment starts (user requirement: "bármikor lehet változtatni! amig nem keződik el jelntkezés!")
                    enrollment_started = tournament.get('tournament_status') in ['ENROLLMENT_OPEN', 'IN_PROGRESS', 'COMPLETED']
                    if not enrollment_started:
                        if st.button("⚙️", key=f"edit_schedule_{tournament['id']}", help="Edit match schedule"):
                            st.session_state['edit_schedule_tournament_id'] = tournament['id']
                            st.session_state['edit_schedule_tournament_name'] = tournament.get('name', 'Unknown')
                            show_edit_schedule_dialog()
                with btn_col3:
                    if st.button("🗑️", key=f"delete_tournament_{tournament['id']}", help="Delete tournament"):
                        st.session_state['delete_tournament_id'] = tournament['id']
                        st.session_state['delete_tournament_name'] = tournament.get('name', 'Untitled')
                        show_delete_tournament_dialog()

            # ========================================================================
            # TOURNAMENT STATUS ACTIONS
            # ========================================================================
            st.divider()
            tournament_status = tournament.get('tournament_status', 'N/A')

            # Open Enrollment button (INSTRUCTOR_CONFIRMED → ENROLLMENT_OPEN)
            # Simplified: Direct transition (READY_FOR_ENROLLMENT removed)
            if tournament_status == 'INSTRUCTOR_CONFIRMED':
                # Show player requirement info before opening enrollment
                tournament_type_id = tournament.get('tournament_type_id')
                if tournament_type_id:
                    try:
                        import requests
                        response = requests.get(
                            f"{API_BASE_URL}/api/v1/tournament-types/{tournament_type_id}",
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=API_TIMEOUT
                        )
                        if response.status_code == 200:
                            tournament_type = response.json()
                            min_players = tournament_type.get('min_players', '?')
                            max_players = tournament.get('max_players', '?')
                            st.info(
                                f"ℹ️ **Ready to open enrollment**\n\n"
                                f"**Tournament Type**: {tournament_type.get('display_name', 'N/A')}\n"
                                f"**Player Requirements**: {min_players} - {max_players} players\n\n"
                                f"💡 *Once enrollment opens, players can see and register for this tournament.*"
                            )
                    except:
                        pass

                if st.button(
                    "📝 Open Enrollment (Make Visible to Players)",
                    key=f"open_enrollment_{tournament['id']}",
                    help="Open enrollment - players can see and register for tournament",
                    type="primary",
                    use_container_width=True
                ):
                    # Direct transition to ENROLLMENT_OPEN
                    success, error, updated = update_tournament(
                        token,
                        tournament['id'],
                        {"tournament_status": "ENROLLMENT_OPEN"}
                    )
                    if success:
                        st.success("✅ Enrollment opened! Tournament is now visible to players.")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to open enrollment: {error}")

            # Close Enrollment button (ENROLLMENT_OPEN → ENROLLMENT_CLOSED)
            if tournament_status == 'ENROLLMENT_OPEN':
                # Show current enrollment status before closing
                enrollment_count = get_tournament_enrollment_count(token, tournament['id'])
                tournament_type_id = tournament.get('tournament_type_id')
                min_players_required = 2  # Default fallback

                if tournament_type_id:
                    try:
                        import requests
                        response = requests.get(
                            f"{API_BASE_URL}/api/v1/tournament-types/{tournament_type_id}",
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=API_TIMEOUT
                        )
                        if response.status_code == 200:
                            tournament_type = response.json()
                            min_players_required = tournament_type.get('min_players', 2)
                    except:
                        pass

                # Show status indicator before closing enrollment
                if enrollment_count >= min_players_required:
                    st.success(f"✅ Ready to close enrollment: {enrollment_count} players enrolled (min: {min_players_required})")
                else:
                    st.warning(f"⚠️ Only {enrollment_count}/{min_players_required} players enrolled. Need {min_players_required - enrollment_count} more to start tournament later.")

                if st.button(
                    "🔒 Close Enrollment",
                    key=f"close_enrollment_{tournament['id']}",
                    help=f"Close enrollment and prepare to start tournament (Current: {enrollment_count} players)",
                    type="secondary",
                    use_container_width=True
                ):
                    st.session_state['close_enrollment_tournament_id'] = tournament['id']
                    st.session_state['close_enrollment_tournament_name'] = tournament.get('name', 'Unknown')
                    show_close_enrollment_dialog()

            # Start Tournament button (ENROLLMENT_CLOSED → IN_PROGRESS)
            if tournament_status == 'ENROLLMENT_CLOSED':
                # Validate min players BEFORE allowing start
                enrollment_count = get_tournament_enrollment_count(token, tournament['id'])
                tournament_type_id = tournament.get('tournament_type_id')
                min_players_required = 2  # Default fallback

                if tournament_type_id:
                    try:
                        import requests
                        response = requests.get(
                            f"{API_BASE_URL}/api/v1/tournament-types/{tournament_type_id}",
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=API_TIMEOUT
                        )
                        if response.status_code == 200:
                            tournament_type = response.json()
                            min_players_required = tournament_type.get('min_players', 2)
                    except:
                        pass

                # Check if enough players
                can_start = enrollment_count >= min_players_required

                if can_start:
                    if st.button(
                        "🚀 Start Tournament",
                        key=f"start_tournament_{tournament['id']}",
                        help=f"Start tournament - All requirements met ({enrollment_count}/{min_players_required} players enrolled)",
                        type="primary",
                        use_container_width=True
                    ):
                        st.session_state['start_tournament_id'] = tournament['id']
                        st.session_state['start_tournament_name'] = tournament.get('name', 'Unknown')
                        show_start_tournament_dialog()
                else:
                    # Show detailed explanation for why tournament cannot start
                    tournament_type_name = "this tournament"
                    if tournament.get('tournament_type_id'):
                        try:
                            import requests
                            response = requests.get(
                                f"{API_BASE_URL}/api/v1/tournament-types/{tournament.get('tournament_type_id')}",
                                headers={"Authorization": f"Bearer {token}"},
                                timeout=API_TIMEOUT
                            )
                            if response.status_code == 200:
                                tournament_type_name = response.json().get('display_name', 'this tournament')
                        except:
                            pass

                    st.info(
                        f"ℹ️ **Tournament cannot start yet**\n\n"
                        f"**Reason**: Insufficient players\n"
                        f"**Required**: Minimum {min_players_required} players for {tournament_type_name}\n"
                        f"**Current**: {enrollment_count} enrolled\n"
                        f"**Missing**: {min_players_required - enrollment_count} more player(s) needed\n\n"
                        f"💡 *Tip: Wait for more players to enroll, or promote the tournament to attract participants.*"
                    )
                    st.button(
                        f"🔒 Start Tournament (Need {min_players_required - enrollment_count} more)",
                        key=f"start_tournament_{tournament['id']}",
                        disabled=True,
                        use_container_width=True,
                        help=f"Tournament requires minimum {min_players_required} players. Currently only {enrollment_count} enrolled."
                    )

            # 🎯 AUTO-GENERATION INFO: Sessions auto-generated when status → IN_PROGRESS
            if tournament_status == 'IN_PROGRESS':
                sessions_generated = tournament.get('sessions_generated', False)

                if sessions_generated:
                    # Sessions already generated - show info and reset button
                    st.success(f"✅ Sessions auto-generated when tournament started")
                    st.caption(f"Generated at: {tournament.get('sessions_generated_at', 'N/A')}")

                    # ============================================================
                    # DEBUG: Check completion status
                    # ============================================================
                    st.write("**🔍 DEBUG: Tournament Completion Check**")

                    # Get leaderboard/results to check if all matches completed
                    try:
                        import requests
                        response = requests.get(
                            f"{API_BASE_URL}/api/v1/tournaments/{tournament['id']}/leaderboard",
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=API_TIMEOUT
                        )
                        if response.status_code == 200:
                            leaderboard_data = response.json()
                            total_matches = leaderboard_data.get('total_matches', 0)
                            completed_matches = leaderboard_data.get('completed_matches', 0)
                            remaining_matches = leaderboard_data.get('remaining_matches', 0)

                            st.write(f"- Total matches: {total_matches}")
                            st.write(f"- Completed: {completed_matches}")
                            st.write(f"- Remaining: {remaining_matches}")

                            # Show Complete Tournament button if all matches done
                            if remaining_matches == 0 and total_matches > 0:
                                st.success("✅ All matches completed! Tournament can be closed.")

                                if st.button(
                                    "🏆 Complete Tournament",
                                    key=f"complete_tournament_{tournament['id']}",
                                    help="Mark tournament as completed and finalize standings",
                                    type="primary",
                                    use_container_width=True
                                ):
                                    success, error, updated = update_tournament(
                                        token,
                                        tournament['id'],
                                        {"tournament_status": "COMPLETED"}
                                    )
                                    if success:
                                        st.success("✅ Tournament completed! Standings finalized.")
                                        st.balloons()
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Failed to complete tournament: {error}")
                            else:
                                st.info(f"⏳ {remaining_matches} matches remaining before completion.")
                        else:
                            st.warning(f"⚠️ Could not fetch match status: {response.status_code}")
                    except Exception as e:
                        st.error(f"❌ Error checking completion: {str(e)}")

                    # ============================================================
                    # PROFESSIONAL TOURNAMENT DRAW & BRACKET UI
                    # ============================================================
                    st.divider()
                    st.subheader("🏆 Tournament Draw & Bracket")

                    try:
                        # Fetch sessions from database
                        sessions_data = get_tournament_sessions_from_db(tournament['id'])

                        if not sessions_data:
                            st.warning("⚠️ No sessions generated. Generate sessions to see the draw.")
                        else:
                            # Separate by phase
                            group_sessions = [s for s in sessions_data if s.get('tournament_phase') == 'Group Stage']
                            knockout_sessions = [s for s in sessions_data if s.get('tournament_phase') == 'Knockout Stage']

                            # ============================================================
                            # GROUP STAGE - Side-by-side columns
                            # ============================================================
                            if group_sessions:
                                st.markdown("### ⚽ Group Stage Draw")

                                # Organize by group
                                groups = {}
                                for session in group_sessions:
                                    group = session.get('group_identifier', 'Unknown')
                                    if group not in groups:
                                        groups[group] = []
                                    groups[group].append(session)

                                # Fetch all participant names (collect from ALL matches, not just first)
                                all_participant_ids = set()
                                for group_matches in groups.values():
                                    for match in group_matches:
                                        participant_ids = match.get('participant_user_ids', [])
                                        all_participant_ids.update(participant_ids)

                                user_names = get_user_names_from_db(list(all_participant_ids))

                                # Display groups side-by-side
                                group_names = sorted(groups.keys())
                                cols = st.columns(len(group_names))

                                for group_name, col in zip(group_names, cols):
                                    with col:
                                        group_matches = groups[group_name]
                                        # Collect ALL unique participants from ALL matches in this group
                                        participants = set()
                                        for match in group_matches:
                                            participants.update(match.get('participant_user_ids', []))
                                        participants = sorted(list(participants))  # Sort for consistent display

                                        st.markdown(f"#### 📍 GROUP {group_name}")

                                        # Participants with names
                                        st.markdown("**👥 Participants:**")
                                        for i, user_id in enumerate(participants, 1):
                                            user_name = user_names.get(user_id, f"User {user_id}")
                                            st.caption(f"{i}. {user_name}")

                                        st.write("")

                                        # Matches
                                        st.markdown("**⚽ Matches:**")
                                        for match in sorted(group_matches, key=lambda x: x.get('tournament_round', 0)):
                                            round_num = match.get('tournament_round', 'N/A')
                                            match_id = match.get('id', 'N/A')
                                            status = match.get('session_status', 'scheduled')

                                            if status == 'completed':
                                                st.success(f"✅ Round {round_num}")
                                            else:
                                                st.info(f"⏳ Round {round_num}")
                                            st.caption(f"   Match #{match_id}")

                                        st.write("")

                                        # Standings (placeholder)
                                        st.markdown("**📊 Standings:**")
                                        st.caption("🔒 Updates after matches")

                                        st.write("")

                                        # Qualifiers
                                        st.markdown("**🎯 Qualifies to KO:**")
                                        st.caption(f"• **{group_name}1** (1st)")
                                        st.caption(f"• **{group_name}2** (2nd)")

                            # ============================================================
                            # KNOCKOUT STAGE - Bracket diagram
                            # ============================================================
                            if knockout_sessions:
                                st.markdown("### 🏆 Knockout Bracket")

                                # Organize by round
                                knockout_rounds = {}
                                for session in knockout_sessions:
                                    structure = session.get('structure_config', {})
                                    round_name = structure.get('round_name', 'Unknown Round')
                                    if round_name not in knockout_rounds:
                                        knockout_rounds[round_name] = []
                                    knockout_rounds[round_name].append(session)

                                # Display rounds in order
                                round_order = ['Round of 8', 'Round of 4', 'Round of 2', 'Final', '3rd Place Match']

                                for round_name in round_order:
                                    if round_name in knockout_rounds:
                                        matches = knockout_rounds[round_name]

                                        st.markdown(f"#### 🎯 {round_name}")

                                        for idx, match in enumerate(matches, 1):
                                            structure_config = match.get('structure_config', {})
                                            matchup = structure_config.get('matchup', None)
                                            seed_1 = structure_config.get('seed_1', None)
                                            seed_2 = structure_config.get('seed_2', None)
                                            participants = match.get('participant_user_ids', [])
                                            match_id = match.get('id', 'N/A')

                                            # Bracket box with HTML styling
                                            st.markdown(f"""
                                            <div style="border: 3px solid #2196F3; border-radius: 12px; padding: 20px; margin: 15px 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                                                <div style="font-weight: bold; font-size: 18px; margin-bottom: 10px;">⚔️ Match #{match_id}</div>
                                            """, unsafe_allow_html=True)

                                            if participants and len(participants) >= 2:
                                                # Show actual participants with names
                                                player1_name = user_names.get(participants[0], f"User {participants[0]}")
                                                player2_name = user_names.get(participants[1], f"User {participants[1]}")

                                                st.markdown(f"""
                                                    <div style="font-size: 16px; margin: 8px 0;">
                                                        <span style="background: #4CAF50; padding: 5px 10px; border-radius: 5px;">{player1_name}</span>
                                                    </div>
                                                    <div style="text-align: center; font-size: 20px; margin: 5px 0;">VS</div>
                                                    <div style="font-size: 16px; margin: 8px 0;">
                                                        <span style="background: #FF5722; padding: 5px 10px; border-radius: 5px;">{player2_name}</span>
                                                    </div>
                                                """, unsafe_allow_html=True)
                                            elif matchup and seed_1 and seed_2:
                                                # Show seeding placeholders
                                                st.markdown(f"""
                                                    <div style="font-size: 16px; margin: 8px 0;">
                                                        <span style="background: rgba(255,255,255,0.2); padding: 5px 10px; border-radius: 5px;">🎯 {seed_1}</span> (Group {seed_1[0]} - 1st place)
                                                    </div>
                                                    <div style="text-align: center; font-size: 20px; margin: 5px 0;">VS</div>
                                                    <div style="font-size: 16px; margin: 8px 0;">
                                                        <span style="background: rgba(255,255,255,0.2); padding: 5px 10px; border-radius: 5px;">🎯 {seed_2}</span> (Group {seed_2[0]} - 2nd place)
                                                    </div>
                                                """, unsafe_allow_html=True)
                                            else:
                                                # TBD
                                                st.markdown("""
                                                    <div style="text-align: center; font-size: 16px; color: #FFD700;">
                                                        🔒 Awaiting previous round results
                                                    </div>
                                                """, unsafe_allow_html=True)

                                            st.markdown("</div>", unsafe_allow_html=True)

                                        if round_name != 'Final' and round_name != '3rd Place Match':
                                            st.markdown("### ⬇️ **Winner advances** ⬇️")

                                        st.write("")

                    except Exception as e:
                        st.error(f"❌ Error loading draw: {str(e)}")

                    st.divider()

                    # ============================================================
                    # DEBUG: Show all generated sessions with proper structure
                    # ============================================================
                    with st.expander("🔍 DEBUG: View All Generated Sessions", expanded=False):
                        try:
                            # Fetch sessions directly from database (bypasses API schema limitations)
                            sessions_data = get_tournament_sessions_from_db(tournament['id'])

                            st.caption(f"**📊 Total Sessions Generated:** {len(sessions_data)}")

                            # Group sessions by tournament_phase
                            group_sessions = [s for s in sessions_data if s.get('tournament_phase') == 'Group Stage']
                            knockout_sessions = [s for s in sessions_data if s.get('tournament_phase') == 'Knockout Stage']

                            st.write(f"**⚽ Group Stage:** {len(group_sessions)} matches")
                            st.write(f"**🏆 Knockout Stage:** {len(knockout_sessions)} matches")

                            # ============================================================
                            # GROUP STAGE
                            # ============================================================
                            if group_sessions:
                                st.divider()
                                st.markdown("### ⚽ Group Stage")

                                # Organize by group
                                groups = {}
                                for session in group_sessions:
                                    group = session.get('group_identifier', 'Unknown')
                                    if group not in groups:
                                        groups[group] = []
                                    groups[group].append(session)

                                # Display each group
                                for group_name in sorted(groups.keys()):
                                    st.markdown(f"#### 📍 Group {group_name}")
                                    group_matches = groups[group_name]

                                    # Show participant IDs for this group
                                    if group_matches:
                                        first_match = group_matches[0]
                                        participants = first_match.get('participant_user_ids', [])
                                        st.caption(f"**👥 Participants (User IDs):** {participants}")

                                    # Show rounds
                                    for match in sorted(group_matches, key=lambda x: x.get('tournament_round', 0)):
                                        round_num = match.get('tournament_round', 'N/A')
                                        match_format = match.get('match_format', 'N/A')
                                        structure_config = match.get('structure_config', {})

                                        st.write(f"  **Round {round_num}** ({match_format})")
                                        st.caption(f"    ⚙️ Config: {structure_config}")

                                    st.write("")  # Spacing

                            # ============================================================
                            # KNOCKOUT STAGE
                            # ============================================================
                            if knockout_sessions:
                                st.divider()
                                st.markdown("### 🏆 Knockout Stage")

                                # Organize by knockout round
                                knockout_rounds = {}
                                for session in knockout_sessions:
                                    structure = session.get('structure_config', {})
                                    round_name = structure.get('round_name', 'Unknown Round')
                                    if round_name not in knockout_rounds:
                                        knockout_rounds[round_name] = []
                                    knockout_rounds[round_name].append(session)

                                # Display knockout rounds in order
                                round_order = ['Round of 8', 'Round of 4', 'Round of 2', 'Final', 'Bronze Match']
                                for round_name in round_order:
                                    if round_name in knockout_rounds:
                                        st.markdown(f"#### 🎯 {round_name}")
                                        matches = knockout_rounds[round_name]

                                        for idx, match in enumerate(matches, 1):
                                            match_format = match.get('match_format', 'N/A')
                                            participants = match.get('participant_user_ids', [])
                                            structure_config = match.get('structure_config', {})

                                            # Extract seeding information
                                            matchup = structure_config.get('matchup', None)
                                            seed_1 = structure_config.get('seed_1', None)
                                            seed_2 = structure_config.get('seed_2', None)

                                            if participants:
                                                # Participants already assigned (after group stage)
                                                st.write(f"  **Match {idx}:** User IDs {participants}")
                                            elif matchup:
                                                # Show seeding placeholders (A1 vs B2, etc.)
                                                st.write(f"  **Match {idx}:** {matchup}")
                                                if seed_1 and seed_2:
                                                    st.caption(f"    🎯 Seeding: {seed_1} (Group {seed_1[0]} 1st) vs {seed_2} (Group {seed_2[0]} 2nd)")
                                            else:
                                                st.write(f"  **Match {idx}:** 🔒 Awaiting seeding from group stage")

                                            st.caption(f"    Format: {match_format}")

                                        st.write("")  # Spacing

                            # ============================================================
                            # SUMMARY
                            # ============================================================
                            st.divider()
                            st.info(f"""
                                **📋 Summary:**
                                - Group Stage matches show all participants (everyone plays everyone)
                                - Knockout Stage matches are empty until group stage completes
                                - After group stage, seeding will populate knockout participant_user_ids
                                - match_format: INDIVIDUAL_RANKING (group) vs HEAD_TO_HEAD (knockout)
                            """)

                        except Exception as e:
                            st.error(f"❌ Error fetching sessions: {str(e)}")

                    if st.button(
                        "🔄 Reset & Regenerate Sessions",
                        key=f"reset_sessions_{tournament['id']}",
                        help="Delete auto-generated sessions and regenerate (WARNING: Cannot undo!)",
                        use_container_width=True
                    ):
                        st.session_state['reset_sessions_tournament_id'] = tournament['id']
                        st.session_state['reset_sessions_tournament_name'] = tournament.get('name', 'Unknown')
                        show_reset_sessions_dialog()
                else:
                    # Sessions should have been auto-generated but weren't (error state)
                    st.warning("⚠️ Sessions not yet generated. They should have been auto-generated when status changed to IN_PROGRESS.")
                    st.caption("If sessions are missing, reset tournament status to ENROLLMENT_CLOSED and change it back to IN_PROGRESS.")

                    # ✅ NEW: Add manual generation button
                    if st.button(
                        "🎯 Manually Generate Sessions",
                        key=f"manual_generate_{tournament['id']}",
                        help="Generate tournament sessions manually",
                        use_container_width=True,
                        type="primary"
                    ):
                        st.session_state['generate_sessions_tournament_id'] = tournament['id']
                        st.session_state['generate_sessions_tournament_name'] = tournament.get('name', 'Unknown')
                        st.session_state['generate_sessions_tournament_type_id'] = tournament.get('tournament_type_id')
                        st.rerun()

            # ========================================================================
            # INSTRUCTOR APPLICATION MANAGEMENT
            # ========================================================================
            st.divider()
            render_instructor_applications_section(token, tournament)

            # ========================================================================
            # REWARD DISTRIBUTION
            # ========================================================================
            st.write(f"**🔍 DEBUG: Checking reward distribution eligibility**")
            st.write(f"- status (old): {tournament.get('status')}")
            st.write(f"- tournament_status (new): {tournament.get('tournament_status')}")

            if tournament.get('tournament_status') == 'COMPLETED':
                st.divider()
                st.success("✅ Tournament is COMPLETED - showing reward distribution")
                render_reward_distribution_section(token, tournament)
            elif tournament.get('tournament_status') == 'REWARDS_DISTRIBUTED':
                st.divider()
                st.success("✅ Rewards have been distributed!")

                # Fetch and display reward transactions
                try:
                    import traceback
                    st.write(f"**🔍 DEBUG: Fetching rankings from API**")
                    st.write(f"- Tournament ID: {tournament['id']}")
                    st.write(f"- API URL: {API_BASE_URL}/api/v1/tournaments/{tournament['id']}/rankings")

                    import requests as req_module
                    response = req_module.get(
                        f"{API_BASE_URL}/api/v1/tournaments/{tournament['id']}/rankings",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=API_TIMEOUT
                    )

                    st.write(f"- Response status: {response.status_code}")

                    if response.status_code == 200:
                        rankings_data = response.json()
                        st.write(f"- Rankings data: {rankings_data}")

                        st.subheader("🏆 Final Rankings & Rewards")

                        for ranking in rankings_data.get('rankings', []):
                            rank = ranking.get('rank', 'N/A')
                            player_name = ranking.get('user_name', 'Unknown')
                            player_email = ranking.get('user_email', '')
                            points = ranking.get('points', 0)

                            # Get reward info from policy
                            reward_policy = tournament.get('reward_policy_snapshot', {})
                            placement_rewards = reward_policy.get('placement_rewards', {})

                            # Map rank to reward tier
                            reward_tier_map = {1: '1ST', 2: '2ND', 3: '3RD'}
                            tier = reward_tier_map.get(rank, 'PARTICIPANT')
                            reward = placement_rewards.get(tier, {'credits': 0, 'xp': 0})

                            credits = reward.get('credits', 0)
                            xp = reward.get('xp', 0)

                            # Medal emoji
                            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "🎖️"

                            st.markdown(
                                f"{medal} **#{rank} - {player_name}** ({player_email}): "
                                f"**{points} points** → Rewarded: **+{credits} credits**, +{xp} XP"
                            )
                    else:
                        st.warning(f"⚠️ Could not fetch rankings data - Status: {response.status_code}")
                        st.write(f"Response: {response.text}")
                except Exception as e:
                    import traceback
                    st.error(f"❌ Error fetching rankings: {str(e)}")
                    st.code(traceback.format_exc())
            else:
                st.info(f"⏳ Reward distribution will appear when tournament_status = COMPLETED (currently: {tournament.get('tournament_status')})")

    # ============================================================================
    # DIALOG TRIGGERS: Check if any dialogs should be opened
    # ============================================================================
    if 'generate_sessions_tournament_id' in st.session_state:
        show_generate_sessions_dialog()

    if 'reset_sessions_tournament_id' in st.session_state:
        show_reset_sessions_dialog()

    if 'edit_schedule_tournament_id' in st.session_state:
        show_edit_schedule_dialog()


def render_game_type_manager(token: str):
    """View auto-generated tournament sessions (READ-ONLY)"""
    st.subheader("📋 View Tournament Sessions")
    st.caption("ℹ️ Sessions are auto-generated when tournament status changes to IN_PROGRESS")

    # Get all tournaments
    tournaments = get_all_tournaments(token)

    if not tournaments:
        st.info("No tournaments available")
        return

    # Tournament selector
    tournament_options = {
        f"{t['name']} ({t['code']})": t['id']
        for t in tournaments
    }

    selected_name = st.selectbox(
        "Select Tournament",
        options=list(tournament_options.keys()),
        key="tournament_selector"
    )

    if not selected_name:
        return

    tournament_id = tournament_options[selected_name]

    # Get sessions for this tournament
    sessions = get_tournament_sessions(token, tournament_id)

    # Header - READ ONLY (no Add button)
    st.write(f"**Total Sessions**: {len(sessions)}")

    st.divider()

    if not sessions:
        st.info("ℹ️ No sessions yet. Sessions will be auto-generated when tournament status changes to IN_PROGRESS.")
        return

    # Display sessions
    for idx, session in enumerate(sessions):
        with st.expander(
            f"Game #{idx+1}: {session.get('date_start', 'N/A')[:10]} - {session.get('title', 'Untitled')}",
            expanded=False
        ):
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                date_start = session.get('date_start', 'N/A')
                date_end = session.get('date_end', 'N/A')

                if date_start != 'N/A':
                    st.write(f"**Date**: {date_start[:10]}")
                    st.write(f"**Start**: {date_start[11:16] if len(date_start) > 11 else 'N/A'}")
                if date_end != 'N/A':
                    st.write(f"**End**: {date_end[11:16] if len(date_end) > 11 else 'N/A'}")

            with col2:
                current_type = session.get('game_type') or 'Not Set'
                st.info(f"🎯 **Game Type**: {current_type}")
                st.caption(f"Session ID: {session.get('id', 'N/A')}")

            with col3:
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("✏️", key=f"edit_game_{session['id']}", help="Edit game"):
                        st.session_state['edit_game_id'] = session['id']
                        st.session_state['edit_game_current_type'] = current_type
                        st.session_state['edit_game_data'] = session
                        show_edit_game_type_dialog()
                with btn_col2:
                    if st.button("🗑️", key=f"delete_game_{session['id']}", help="Delete game"):
                        st.session_state['delete_game_id'] = session['id']
                        st.session_state['delete_game_title'] = session.get('title', 'Untitled')
                        show_delete_game_dialog()


@st.dialog("Edit Game")
def show_edit_game_type_dialog():
    """Dialog for editing game title, type, date and time"""
    session_id = st.session_state.get('edit_game_id')
    current_type = st.session_state.get('edit_game_current_type', 'Not Set')
    session_data = st.session_state.get('edit_game_data', {})

    st.write(f"**Session ID**: {session_id}")
    st.divider()

    # Game Title
    current_title = session_data.get('title', 'League Match')
    new_title = st.text_input(
        "Game Title",
        value=current_title,
        key="edit_game_title"
    )

    # Game Type selector
    try:
        default_index = GAME_TYPE_OPTIONS.index(current_type) if current_type in GAME_TYPE_OPTIONS else 0
    except:
        default_index = 0

    new_type = st.selectbox(
        "Game Type",
        options=GAME_TYPE_OPTIONS,
        index=default_index,
        key="game_type_selector"
    )

    st.divider()

    # Date and Time inputs
    st.subheader("📅 Date & Time")

    # Parse current date_start
    current_start = session_data.get('date_start', '')
    current_end = session_data.get('date_end', '')

    try:
        if 'T' in current_start:
            start_dt = datetime.fromisoformat(current_start.replace('Z', ''))
        else:
            start_dt = datetime.strptime(current_start, '%Y-%m-%d %H:%M:%S')
        start_date_obj = start_dt.date()
        start_time_obj = start_dt.time()
    except:
        start_date_obj = date.today()
        start_time_obj = time(9, 0)

    try:
        if 'T' in current_end:
            end_dt = datetime.fromisoformat(current_end.replace('Z', ''))
        else:
            end_dt = datetime.strptime(current_end, '%Y-%m-%d %H:%M:%S')
        end_time_obj = end_dt.time()
    except:
        end_time_obj = time(10, 30)

    col1, col2 = st.columns(2)

    with col1:
        new_date = st.date_input(
            "Date",
            value=start_date_obj,
            key="session_date"
        )

    with col2:
        st.write("")  # Spacing

    col3, col4 = st.columns(2)

    with col3:
        new_start_time = st.time_input(
            "Start Time",
            value=start_time_obj,
            key="session_start_time"
        )

    with col4:
        new_end_time = st.time_input(
            "End Time",
            value=end_time_obj,
            key="session_end_time"
        )

    st.divider()

    # Action buttons
    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Save Changes", use_container_width=True):
            token = st.session_state.get('token')

            # Combine date and time
            new_start_datetime = datetime.combine(new_date, new_start_time)
            new_end_datetime = datetime.combine(new_date, new_end_time)

            # Validate that end time is after start time
            if new_end_datetime <= new_start_datetime:
                st.error("❌ End time must be after start time!")
                return

            # Build update payload
            update_payload = {
                "title": new_title,
                "game_type": new_type,
                "date_start": new_start_datetime.isoformat(),
                "date_end": new_end_datetime.isoformat()
            }

            try:
                response = requests.patch(
                    f"{API_BASE_URL}/api/v1/sessions/{session_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    json=update_payload,
                    timeout=API_TIMEOUT
                )

                if response.status_code == 200:
                    st.success("✅ Game updated successfully!")
                    st.balloons()
                    # Clear session state
                    if 'edit_game_id' in st.session_state:
                        del st.session_state['edit_game_id']
                    if 'edit_game_current_type' in st.session_state:
                        del st.session_state['edit_game_current_type']
                    if 'edit_game_data' in st.session_state:
                        del st.session_state['edit_game_data']
                    st.rerun()
                else:
                    error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                    error_msg = error_data.get('detail', response.text)
                    st.error(f"❌ Error: {error_msg}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            # Clear session state
            if 'edit_game_id' in st.session_state:
                del st.session_state['edit_game_id']
            if 'edit_game_current_type' in st.session_state:
                del st.session_state['edit_game_current_type']
            if 'edit_game_data' in st.session_state:
                del st.session_state['edit_game_data']
            st.rerun()


@st.dialog("Edit Tournament")
def show_edit_tournament_dialog():
    """Dialog for editing ALL tournament details - Admin can edit EVERYTHING they created"""
    tournament_id = st.session_state.get('edit_tournament_id')
    tournament_data = st.session_state.get('edit_tournament_data', {})

    st.write(f"**Tournament ID**: {tournament_id}")
    st.caption(f"Code: {tournament_data.get('code', 'N/A')}")
    st.divider()

    # Basic Info
    st.subheader("📋 Basic Info")

    new_name = st.text_input(
        "Tournament Name",
        value=tournament_data.get('name', ''),
        key="tournament_name",
        help="Tournament name (e.g., 'Winter Cup 2026')"
    )

    col1, col2 = st.columns(2)
    with col1:
        # Parse current start date
        current_start = tournament_data.get('start_date', '')
        try:
            if 'T' in current_start:
                start_date_obj = datetime.fromisoformat(current_start.replace('Z', '')).date()
            else:
                start_date_obj = datetime.strptime(current_start[:10], '%Y-%m-%d').date()
        except:
            start_date_obj = date.today()

        new_start_date = st.date_input(
            "Start Date",
            value=start_date_obj,
            key="tournament_start_date"
        )

    with col2:
        # Parse current end date
        current_end = tournament_data.get('end_date', '')
        try:
            if 'T' in current_end:
                end_date_obj = datetime.fromisoformat(current_end.replace('Z', '')).date()
            else:
                end_date_obj = datetime.strptime(current_end[:10], '%Y-%m-%d').date()
        except:
            end_date_obj = date.today()

        new_end_date = st.date_input(
            "End Date",
            value=end_date_obj,
            key="tournament_end_date"
        )

    st.divider()

    # Tournament Type & Settings
    st.subheader("🏆 Tournament Type & Settings")

    col1, col2 = st.columns(2)
    with col1:
        # Specialization Type
        SPEC_OPTIONS = ["LFA_FOOTBALL_PLAYER", "LFA_COACH", "GANCUJU_PLAYER"]
        current_spec = tournament_data.get('specialization_type', 'LFA_FOOTBALL_PLAYER')
        try:
            spec_index = SPEC_OPTIONS.index(current_spec)
        except:
            spec_index = 0

        new_specialization_type = st.selectbox(
            "Specialization Type",
            options=SPEC_OPTIONS,
            index=spec_index,
            key="tournament_spec_type"
        )

        # Age Group
        AGE_OPTIONS = ["PRE", "YOUTH", "AMATEUR", "PRO", None]
        current_age = tournament_data.get('age_group')
        try:
            age_index = AGE_OPTIONS.index(current_age) if current_age else 4
        except:
            age_index = 4

        new_age_group = st.selectbox(
            "Age Group (optional)",
            options=["PRE", "YOUTH", "AMATEUR", "PRO", "None"],
            index=age_index,
            key="tournament_age_group"
        )
        if new_age_group == "None":
            new_age_group = None

    with col2:
        # Assignment Type
        ASSIGNMENT_OPTIONS = ["OPEN_ASSIGNMENT", "APPLICATION_BASED"]
        current_assignment = tournament_data.get('assignment_type', 'OPEN_ASSIGNMENT')
        try:
            assignment_index = ASSIGNMENT_OPTIONS.index(current_assignment)
        except:
            assignment_index = 0

        new_assignment_type = st.selectbox(
            "Assignment Type",
            options=ASSIGNMENT_OPTIONS,
            index=assignment_index,
            key="tournament_assignment_type",
            help="OPEN_ASSIGNMENT: Admin assigns instructor | APPLICATION_BASED: Instructors apply"
        )

        # Max Players
        new_max_players = st.number_input(
            "Max Players",
            min_value=2,
            max_value=100,
            value=tournament_data.get('max_players', 8),
            key="tournament_max_players"
        )

    col1, col2 = st.columns(2)
    with col1:
        # Enrollment Cost
        new_enrollment_cost = st.number_input(
            "Enrollment Cost (credits)",
            min_value=0,
            max_value=10000,
            value=tournament_data.get('enrollment_cost', 500),
            key="tournament_enrollment_cost"
        )

    with col2:
        # Participant Type
        PARTICIPANT_OPTIONS = ["INDIVIDUAL", "TEAM", "MIXED"]
        current_participant = tournament_data.get('participant_type', 'INDIVIDUAL')
        try:
            participant_index = PARTICIPANT_OPTIONS.index(current_participant)
        except:
            participant_index = 0

        new_participant_type = st.selectbox(
            "Participant Type",
            options=PARTICIPANT_OPTIONS,
            index=participant_index,
            key="tournament_participant_type"
        )

    st.divider()

    # Status
    st.subheader("📊 Tournament Status")

    # Simplified tournament status workflow (READY_FOR_ENROLLMENT removed - redundant)
    TOURNAMENT_STATUS_OPTIONS = [
        "DRAFT",
        "SEEKING_INSTRUCTOR",
        "PENDING_INSTRUCTOR_ACCEPTANCE",
        "INSTRUCTOR_CONFIRMED",
        "ENROLLMENT_OPEN",  # Admin opens enrollment (players can register)
        "ENROLLMENT_CLOSED",  # Enrollment closed, waiting for tournament start
        "IN_PROGRESS",  # Tournament running (sessions auto-generated)
        "COMPLETED",
        "REWARDS_DISTRIBUTED",
        "CANCELLED",
        "ARCHIVED"
    ]

    current_tournament_status = tournament_data.get('tournament_status', 'DRAFT')

    # MIGRATION: Map deprecated READY_FOR_ENROLLMENT to ENROLLMENT_OPEN
    if current_tournament_status == "READY_FOR_ENROLLMENT":
        current_tournament_status = "ENROLLMENT_OPEN"
        st.warning("⚠️ READY_FOR_ENROLLMENT is deprecated. Mapped to ENROLLMENT_OPEN.")

    try:
        status_index = TOURNAMENT_STATUS_OPTIONS.index(current_tournament_status)
    except:
        status_index = 0

    new_tournament_status = st.selectbox(
        "Tournament Status",
        options=TOURNAMENT_STATUS_OPTIONS,
        index=status_index,
        key="tournament_status_select",
        help="Tournament lifecycle status"
    )

    st.divider()

    # Action buttons
    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Save Changes", use_container_width=True):
            token = st.session_state.get('token')

            # Validate that end date is not BEFORE start date (same day is OK for 1-day tournaments!)
            if new_end_date < new_start_date:
                st.error("❌ End date cannot be before start date!")
                return

            # Build update payload with ALL editable fields
            update_data = {
                "name": new_name,
                "start_date": new_start_date.isoformat(),
                "end_date": new_end_date.isoformat(),
                "specialization_type": new_specialization_type,
                "age_group": new_age_group,
                "assignment_type": new_assignment_type,
                "max_players": new_max_players,
                "enrollment_cost": new_enrollment_cost,
                "participant_type": new_participant_type
            }

            # ✅ FIX: Only include tournament_status if it actually changed
            current_tournament_status = tournament_data.get('tournament_status')
            if new_tournament_status != current_tournament_status:
                update_data["tournament_status"] = new_tournament_status

            # 🔍 DEBUG: Show what we're sending
            st.write("**🔍 DEBUG: Tournament Update Request**")
            st.write(f"- Tournament ID: {tournament_id}")
            st.write(f"- Update data: {update_data}")

            success, error, updated = update_tournament(token, tournament_id, update_data)

            # 🔍 DEBUG: Show result
            st.write("**🔍 DEBUG: Update Result**")
            st.write(f"- Success: {success}")
            st.write(f"- Error: {error}")
            st.write(f"- Updated data: {updated}")

            if success:
                st.success("✅ Tournament updated successfully!")
                st.balloons()
                # Clear session state
                if 'edit_tournament_id' in st.session_state:
                    del st.session_state['edit_tournament_id']
                if 'edit_tournament_data' in st.session_state:
                    del st.session_state['edit_tournament_data']
                st.rerun()
            else:
                st.error(f"❌ Error: {error}")

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            # Clear session state
            if 'edit_tournament_id' in st.session_state:
                del st.session_state['edit_tournament_id']
            if 'edit_tournament_data' in st.session_state:
                del st.session_state['edit_tournament_data']
            st.rerun()


def get_all_tournaments(token: str) -> List[Dict]:
    """Get all tournaments (semesters with TOURN- code prefix)"""
    success, semesters = get_semesters(token)

    if not success:
        return []

    # Filter for tournaments
    tournaments = [
        s for s in semesters
        if s.get('code', '').startswith('TOURN-')
    ]

    return tournaments


def get_tournament_sessions(token: str, tournament_id: int) -> List[Dict]:
    """Get all sessions for a tournament"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/sessions/",
            headers={"Authorization": f"Bearer {token}"},
            params={"semester_id": tournament_id},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            sessions = response.json().get('sessions', [])
            # Sort by date
            sessions.sort(key=lambda s: s.get('date_start', ''))
            return sessions
        else:
            return []
    except Exception:
        return []


@st.dialog("Add New Game")
def show_add_game_dialog():
    """Dialog for adding a new game to tournament"""
    tournament_id = st.session_state.get('add_game_tournament_id')
    tournament_data = st.session_state.get('add_game_tournament_data', {})

    st.write(f"**Tournament**: {tournament_data.get('name', 'N/A')}")
    st.divider()

    # ✅ AUTO-FILL: Tournament date parsing
    tournament_date_str = tournament_data.get('start_date')
    if tournament_date_str:
        try:
            # Parse ISO date string (e.g., "2026-01-19")
            tournament_date = datetime.fromisoformat(tournament_date_str).date()
        except:
            tournament_date = date.today()
    else:
        tournament_date = date.today()

    # ✅ AUTO-FILL: Game number for title
    token = st.session_state.get('token')
    existing_games = get_tournament_sessions(token, tournament_id) if token else []
    next_game_number = len(existing_games) + 1
    default_title = f"Match {next_game_number}"

    # Game details
    title = st.text_input(
        "Game Title",
        value=default_title,
        key="new_game_title",
        help="Auto-generated based on game count. You can change it."
    )

    # Game Type
    game_type = st.selectbox(
        "Game Type",
        options=GAME_TYPE_OPTIONS,
        index=0,
        key="new_game_type",
        help="Select the format for this match"
    )

    st.divider()
    st.subheader("📅 Date & Time")

    col1, col2 = st.columns(2)

    with col1:
        game_date = st.date_input(
            "Date",
            value=tournament_date,  # ✅ AUTO-FILLED from tournament
            key="new_game_date",
            help="Auto-filled from tournament date. You can change if needed."
        )

    with col2:
        st.info(f"🏆 Tournament Date: {tournament_date.strftime('%Y-%m-%d')}")

    col3, col4 = st.columns(2)

    with col3:
        start_time = st.time_input(
            "Start Time",
            value=dt_time(14, 0),
            key="new_game_start_time"
        )

    with col4:
        end_time = st.time_input(
            "End Time",
            value=dt_time(15, 30),
            key="new_game_end_time"
        )

    st.divider()

    # Action buttons
    col1, col2 = st.columns(2)

    with col1:
        if st.button("➕ Create Game", use_container_width=True):
            token = st.session_state.get('token')

            # Combine date and time
            start_datetime = datetime.combine(game_date, start_time)
            end_datetime = datetime.combine(game_date, end_time)

            # Validate that end time is after start time
            if end_datetime <= start_datetime:
                st.error("❌ End time must be after start time!")
                return

            # Build create payload
            # ✅ TOURNAMENT GAME: Automatically mark as tournament game
            create_payload = {
                "title": title,
                "description": f"Tournament Game: {game_type}",
                "date_start": start_datetime.isoformat(),
                "date_end": end_datetime.isoformat(),
                "session_type": "on_site",
                "capacity": tournament_data.get('max_players', 20),  # ✅ Use tournament max_players
                "semester_id": tournament_id,
                "instructor_id": tournament_data.get('master_instructor_id'),
                "credit_cost": 0,  # ✅ Tournament games are included in tournament enrollment cost
                "is_tournament_game": True,  # ✅ AUTO: Mark as tournament game
                "game_type": game_type
            }

            try:
                response = requests.post(
                    f"{API_BASE_URL}/api/v1/sessions/",
                    headers={"Authorization": f"Bearer {token}"},
                    json=create_payload,
                    timeout=API_TIMEOUT
                )

                if response.status_code == 200:
                    st.success("✅ Game created successfully!")
                    st.balloons()
                    # Clear session state
                    if 'add_game_tournament_id' in st.session_state:
                        del st.session_state['add_game_tournament_id']
                    if 'add_game_tournament_data' in st.session_state:
                        del st.session_state['add_game_tournament_data']
                    st.rerun()
                else:
                    error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                    error_msg = error_data.get('detail', response.text)
                    st.error(f"❌ Error: {error_msg}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            # Clear session state
            if 'add_game_tournament_id' in st.session_state:
                del st.session_state['add_game_tournament_id']
            if 'add_game_tournament_data' in st.session_state:
                del st.session_state['add_game_tournament_data']
            st.rerun()


@st.dialog("Delete Game")
def show_delete_game_dialog():
    """Dialog for confirming game deletion"""
    session_id = st.session_state.get('delete_game_id')
    game_title = st.session_state.get('delete_game_title', 'Untitled')

    st.warning(f"⚠️ Are you sure you want to delete this game?")
    st.write(f"**Game**: {game_title}")
    st.write(f"**Session ID**: {session_id}")
    st.divider()

    st.error("**This action cannot be undone!**")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ Delete", use_container_width=True, type="primary"):
            token = st.session_state.get('token')

            try:
                response = requests.delete(
                    f"{API_BASE_URL}/api/v1/sessions/{session_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=API_TIMEOUT
                )

                if response.status_code == 200:
                    st.success("✅ Game deleted successfully!")
                    # Clear session state
                    if 'delete_game_id' in st.session_state:
                        del st.session_state['delete_game_id']
                    if 'delete_game_title' in st.session_state:
                        del st.session_state['delete_game_title']
                    st.rerun()
                else:
                    error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                    error_msg = error_data.get('detail', response.text)
                    st.error(f"❌ Error: {error_msg}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            # Clear session state
            if 'delete_game_id' in st.session_state:
                del st.session_state['delete_game_id']
            if 'delete_game_title' in st.session_state:
                del st.session_state['delete_game_title']
            st.rerun()


@st.dialog("🗑️ Delete Tournament")
def show_delete_tournament_dialog():
    """Show confirmation dialog for deleting a tournament"""
    tournament_id = st.session_state.get('delete_tournament_id')
    tournament_name = st.session_state.get('delete_tournament_name', 'Untitled')

    st.warning(f"Are you sure you want to delete tournament **{tournament_name}**?")
    st.write("⚠️ This action cannot be undone. All associated sessions and bookings will be permanently deleted.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✓ Confirm Delete", type="primary", use_container_width=True):
            token = st.session_state.get('token')
            if not token:
                st.error("❌ Authentication token not found. Please log in again.")
                return

            # Call DELETE API endpoint
            response = requests.delete(
                f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}",
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 204:
                st.success(f"✅ Tournament '{tournament_name}' deleted successfully!")
                st.balloons()
                # Clear session state
                if 'delete_tournament_id' in st.session_state:
                    del st.session_state['delete_tournament_id']
                if 'delete_tournament_name' in st.session_state:
                    del st.session_state['delete_tournament_name']
                time_module.sleep(1)
                st.rerun()
            elif response.status_code == 403:
                st.error("❌ Permission denied. Only admins can delete tournaments.")
            elif response.status_code == 404:
                st.error(f"❌ Tournament not found (ID: {tournament_id})")
            else:
                st.error(f"❌ Failed to delete tournament. Server error: {response.status_code}")

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            # Clear session state
            if 'delete_tournament_id' in st.session_state:
                del st.session_state['delete_tournament_id']
            if 'delete_tournament_name' in st.session_state:
                del st.session_state['delete_tournament_name']
            st.rerun()


# ============================================================================
# 🎯 NEW PHASE 3: SESSION GENERATION DIALOGS
# ============================================================================

@st.dialog("🎯 Generate Tournament Sessions")
def show_generate_sessions_dialog():
    """Dialog for generating tournament sessions"""
    tournament_id = st.session_state.get('generate_sessions_tournament_id')
    tournament_name = st.session_state.get('generate_sessions_tournament_name', 'Unknown')
    tournament_type_id = st.session_state.get('generate_sessions_tournament_type_id')

    st.write(f"**Tournament**: {tournament_name}")
    st.write(f"**Tournament ID**: {tournament_id}")
    st.divider()

    st.info("🔄 **Auto-Generation Process:**")
    st.write("1. Fetches enrolled player count")
    st.write("2. Validates against tournament type constraints")
    st.write("3. Generates session structure based on tournament format")
    st.write("4. Creates sessions in database with auto_generated=True")

    st.divider()

    # Configuration options
    st.subheader("⚙️ Generation Settings")

    parallel_fields = st.number_input(
        "Parallel Fields",
        min_value=1,
        max_value=10,
        value=1,
        help="Number of fields available for simultaneous matches"
    )

    session_duration = st.number_input(
        "Session Duration (minutes)",
        min_value=1,
        max_value=180,
        value=90,
        step=1,
        help="Duration of each match"
    )

    break_minutes = st.number_input(
        "Break Between Sessions (minutes)",
        min_value=0,
        max_value=60,
        value=15,
        step=1,
        help="Break time between consecutive matches"
    )

    # ============================================================================
    # 🔍 DEBUG PANEL: Show request parameters being sent to backend
    # ============================================================================
    st.divider()
    with st.expander("🔍 Debug: Request Parameters", expanded=False):
        st.caption("This shows the exact values that will be sent to the backend API")
        st.json({
            "tournament_id": tournament_id,
            "tournament_name": tournament_name,
            "parallel_fields": parallel_fields,
            "session_duration_minutes": session_duration,
            "break_minutes": break_minutes
        })
        st.info("ℹ️ **Backend Validation Rules:**\n- `session_duration_minutes` must be ≥ 1 and ≤ 180 (business allows 1-5 min matches)\n- `parallel_fields` must be ≥ 1 and ≤ 10\n- `break_minutes` must be ≥ 0 and ≤ 60")

    st.divider()
    st.warning("⚠️ **CRITICAL**: Once generated, sessions cannot be automatically deleted. You must reset them manually if needed.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🎯 Generate Sessions", use_container_width=True, type="primary"):
            token = st.session_state.get('token')

            if not token:
                st.error("❌ Authentication token not found. Please log in again.")
                return

            # Call session generation API
            success, error, result = generate_tournament_sessions(
                token,
                tournament_id,
                parallel_fields=parallel_fields,
                session_duration_minutes=session_duration,
                break_minutes=break_minutes
            )

            if success:
                st.success(f"✅ Successfully generated {result.get('sessions_created', 0)} sessions!")
                st.balloons()

                # Show generation details
                st.divider()
                st.write("**📊 Generation Summary:**")
                st.write(f"- **Tournament**: {result.get('tournament_name', 'N/A')}")
                st.write(f"- **Sessions Created**: {result.get('sessions_created', 0)}")
                st.write(f"- **Generated At**: {result.get('sessions_generated_at', 'N/A')}")

                # ✅ DEBUG PANEL: Show generated sessions with participant_user_ids
                with st.expander("🔍 Debug: Generated Sessions Structure", expanded=True):
                    st.caption("This shows the explicit match participants for each session")

                    # Fetch generated sessions from database
                    import requests
                    headers = {"Authorization": f"Bearer {token}"}
                    sessions_url = f"http://localhost:8000/api/v1/tournaments/{tournament_id}/sessions"

                    try:
                        sessions_response = requests.get(sessions_url, headers=headers)
                        if sessions_response.status_code == 200:
                            sessions_data = sessions_response.json()

                            # Group by phase
                            group_stage = []
                            knockout_stage = []

                            for session in sessions_data:
                                if session.get('tournament_phase') == 'Group Stage':
                                    group_stage.append(session)
                                elif session.get('tournament_phase') == 'Knockout Stage':
                                    knockout_stage.append(session)

                            # Show Group Stage
                            if group_stage:
                                st.markdown("### 📌 Group Stage Sessions")
                                for session in group_stage:
                                    participant_ids = session.get('participant_user_ids', [])
                                    col1, col2, col3 = st.columns([2, 2, 1])
                                    with col1:
                                        st.caption(f"**{session.get('title', 'N/A')}**")
                                    with col2:
                                        if participant_ids:
                                            st.caption(f"Participants: {participant_ids}")
                                        else:
                                            st.caption("⚠️ No participants assigned")
                                    with col3:
                                        st.caption(f"Format: {session.get('match_format', 'N/A')}")

                            # Show Knockout Stage (organized by round)
                            if knockout_stage:
                                st.markdown("### 🏆 Knockout Stage Sessions")

                                # ✅ NEW: Organize by round and detect bracket structure
                                play_in_matches = [s for s in knockout_stage if s.get('tournament_round') == 0]
                                main_bracket = [s for s in knockout_stage if s.get('tournament_round', 1) > 0 and '3rd Place' not in s.get('title', '')]
                                bronze_match = [s for s in knockout_stage if '3rd Place' in s.get('title', '')]

                                # Show Play-in Round (if exists)
                                if play_in_matches:
                                    st.markdown("#### 🎯 Play-in Round (Byes for top seeds)")
                                    for session in play_in_matches:
                                        participant_ids = session.get('participant_user_ids')
                                        structure_config = session.get('structure_config', {})
                                        seed_high = structure_config.get('seed_high', '?')
                                        seed_low = structure_config.get('seed_low', '?')

                                        col1, col2, col3 = st.columns([2, 2, 1])
                                        with col1:
                                            st.caption(f"**{session.get('title', 'N/A')}**")
                                        with col2:
                                            if participant_ids is None:
                                                st.caption(f"🔒 Seed {seed_high} vs Seed {seed_low} (awaiting seeding)")
                                            else:
                                                st.caption(f"Participants: {participant_ids}")
                                        with col3:
                                            st.caption(f"Format: {session.get('match_format', 'N/A')}")

                                    st.caption("ℹ️ **Top seeds get BYE to next round**")
                                    st.divider()

                                # Show Main Bracket
                                if main_bracket:
                                    st.markdown("#### 🏅 Main Bracket")
                                    for session in main_bracket:
                                        participant_ids = session.get('participant_user_ids')
                                        col1, col2, col3 = st.columns([2, 2, 1])
                                        with col1:
                                            st.caption(f"**{session.get('title', 'N/A')}**")
                                        with col2:
                                            if participant_ids is None:
                                                st.caption("🔒 Awaiting group stage results")
                                            elif participant_ids:
                                                st.caption(f"Participants: {participant_ids}")
                                            else:
                                                st.caption("⚠️ No participants assigned")
                                        with col3:
                                            st.caption(f"Format: {session.get('match_format', 'N/A')}")

                                # Show Bronze Match (if exists)
                                if bronze_match:
                                    st.divider()
                                    st.markdown("#### 🥉 Bronze Match")
                                    for session in bronze_match:
                                        participant_ids = session.get('participant_user_ids')
                                        col1, col2, col3 = st.columns([2, 2, 1])
                                        with col1:
                                            st.caption(f"**{session.get('title', 'N/A')}**")
                                        with col2:
                                            if participant_ids is None:
                                                st.caption("🔒 Awaiting semifinal results")
                                            elif participant_ids:
                                                st.caption(f"Participants: {participant_ids}")
                                            else:
                                                st.caption("⚠️ No participants assigned")
                                        with col3:
                                            st.caption(f"Format: {session.get('match_format', 'N/A')}")

                            st.divider()
                            st.info("ℹ️ **Match participants come from `participant_user_ids`, NOT from tournament-wide enrollment.**")
                        else:
                            st.warning("Could not fetch session details for debug panel")
                    except Exception as e:
                        st.warning(f"Debug panel error: {str(e)}")

                # Clear session state
                if 'generate_sessions_tournament_id' in st.session_state:
                    del st.session_state['generate_sessions_tournament_id']
                if 'generate_sessions_tournament_name' in st.session_state:
                    del st.session_state['generate_sessions_tournament_name']
                if 'generate_sessions_tournament_type_id' in st.session_state:
                    del st.session_state['generate_sessions_tournament_type_id']

                time_module.sleep(2)
                st.rerun()
            else:
                st.error(f"❌ Failed to generate sessions: {error}")

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            # Clear session state
            if 'generate_sessions_tournament_id' in st.session_state:
                del st.session_state['generate_sessions_tournament_id']
            if 'generate_sessions_tournament_name' in st.session_state:
                del st.session_state['generate_sessions_tournament_name']
            if 'generate_sessions_tournament_type_id' in st.session_state:
                del st.session_state['generate_sessions_tournament_type_id']
            st.rerun()


@st.dialog("👁️ Preview Tournament Sessions")
def show_preview_sessions_dialog():
    """Dialog for previewing tournament sessions WITHOUT creating them"""
    tournament_id = st.session_state.get('preview_sessions_tournament_id')
    tournament_name = st.session_state.get('preview_sessions_tournament_name', 'Unknown')

    st.write(f"**Tournament**: {tournament_name}")
    st.write(f"**Tournament ID**: {tournament_id}")
    st.divider()

    # Configuration options
    parallel_fields = st.number_input(
        "Parallel Fields",
        min_value=1,
        max_value=10,
        value=1,
        help="Number of fields available for simultaneous matches",
        key="preview_parallel_fields"
    )

    session_duration = st.number_input(
        "Session Duration (minutes)",
        min_value=30,
        max_value=180,
        value=90,
        step=15,
        help="Duration of each match",
        key="preview_session_duration"
    )

    break_minutes = st.number_input(
        "Break Between Sessions (minutes)",
        min_value=0,
        max_value=60,
        value=15,
        step=5,
        help="Break time between consecutive matches",
        key="preview_break_minutes"
    )

    st.divider()

    if st.button("👁️ Load Preview", use_container_width=True, type="primary"):
        token = st.session_state.get('token')

        if not token:
            st.error("❌ Authentication token not found. Please log in again.")
            return

        # Call preview API
        success, error, preview_data = preview_tournament_sessions(
            token,
            tournament_id,
            parallel_fields=parallel_fields,
            session_duration_minutes=session_duration,
            break_minutes=break_minutes
        )

        if success:
            st.success("✅ Preview loaded successfully!")
            st.divider()

            # Display preview data
            st.write("**📊 Tournament Information:**")
            st.write(f"- **Tournament Type**: {preview_data.get('tournament_type_code', 'N/A')}")
            st.write(f"- **Player Count**: {preview_data.get('player_count', 0)}")
            st.write(f"- **Total Sessions**: {len(preview_data.get('sessions', []))}")

            st.divider()
            st.subheader("📅 Session Structure Preview")

            sessions = preview_data.get('sessions', [])
            if sessions:
                for idx, session in enumerate(sessions, 1):
                    with st.expander(f"Session {idx}: {session.get('title', 'N/A')}", expanded=False):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.write(f"**Date Start**: {session.get('date_start', 'N/A')[:16]}")
                            st.write(f"**Date End**: {session.get('date_end', 'N/A')[:16]}")

                        with col2:
                            st.write(f"**Phase**: {session.get('tournament_phase', 'N/A')}")
                            st.write(f"**Round**: {session.get('tournament_round', 'N/A')}")
                            st.write(f"**Game Type**: {session.get('game_type', 'N/A')}")
            else:
                st.info("No sessions in preview")
        else:
            st.error(f"❌ Failed to load preview: {error}")

    st.divider()

    if st.button("✓ Close", use_container_width=True):
        # Clear session state
        if 'preview_sessions_tournament_id' in st.session_state:
            del st.session_state['preview_sessions_tournament_id']
        if 'preview_sessions_tournament_name' in st.session_state:
            del st.session_state['preview_sessions_tournament_name']
        st.rerun()


@st.dialog("🔄 Reset Generated Sessions")
def show_reset_sessions_dialog():
    """Dialog for resetting (deleting) auto-generated sessions"""
    tournament_id = st.session_state.get('reset_sessions_tournament_id')
    tournament_name = st.session_state.get('reset_sessions_tournament_name', 'Unknown')

    st.warning(f"⚠️ Are you sure you want to reset all auto-generated sessions for **{tournament_name}**?")
    st.write(f"**Tournament ID**: {tournament_id}")
    st.divider()

    st.error("**⚠️ THIS ACTION CANNOT BE UNDONE!**")
    st.write("This will permanently delete all auto-generated sessions for this tournament.")
    st.write("You can re-generate sessions after resetting, but all existing data will be lost.")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ Confirm Reset", use_container_width=True, type="primary"):
            token = st.session_state.get('token')

            if not token:
                st.error("❌ Authentication token not found. Please log in again.")
                return

            # Call delete sessions API
            success, error, result = delete_generated_sessions(token, tournament_id)

            if success:
                st.success(f"✅ Successfully deleted {result.get('deleted_count', 0)} sessions!")
                st.info("🔄 Now opening session generation dialog...")

                # Transfer to generate sessions dialog
                st.session_state['generate_sessions_tournament_id'] = tournament_id
                st.session_state['generate_sessions_tournament_name'] = tournament_name
                # Keep tournament_type_id if we have it
                if 'reset_sessions_tournament_type_id' in st.session_state:
                    st.session_state['generate_sessions_tournament_type_id'] = st.session_state['reset_sessions_tournament_type_id']

                # Clear reset session state
                if 'reset_sessions_tournament_id' in st.session_state:
                    del st.session_state['reset_sessions_tournament_id']
                if 'reset_sessions_tournament_name' in st.session_state:
                    del st.session_state['reset_sessions_tournament_name']

                time_module.sleep(1)
                st.rerun()
            else:
                st.error(f"❌ Failed to reset sessions: {error}")

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            # Clear session state
            if 'reset_sessions_tournament_id' in st.session_state:
                del st.session_state['reset_sessions_tournament_id']
            if 'reset_sessions_tournament_name' in st.session_state:
                del st.session_state['reset_sessions_tournament_name']
            st.rerun()


@st.dialog("⚙️ Configure Match Schedule")
def show_edit_schedule_dialog():
    """Dialog for configuring tournament match schedule (BEFORE session generation)

    These settings are INPUT parameters for the session generator.
    User requirement: "bármikor lehet változtatni! amig nem keződik el jelntkezés!"
    """
    tournament_id = st.session_state.get('edit_schedule_tournament_id')
    tournament_name = st.session_state.get('edit_schedule_tournament_name', 'Unknown')

    st.write(f"**Tournament**: {tournament_name}")
    st.write(f"**Tournament ID**: {tournament_id}")
    st.divider()

    st.info("ℹ️ Configure match schedule settings. These will be used when generating tournament sessions.")

    # Get current tournament configuration
    try:
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                start_date,
                match_duration_minutes,
                break_duration_minutes,
                parallel_fields,
                tournament_type_id
            FROM semesters
            WHERE id = %s
        """, (tournament_id,))

        result = cursor.fetchone()

        if result:
            current_start = result[0]
            current_match_duration = result[1]
            current_break_duration = result[2]
            current_parallel_fields = result[3]
            tournament_type_id = result[4]
        else:
            current_start = date.today()
            current_match_duration = None
            current_break_duration = None
            current_parallel_fields = None
            tournament_type_id = None

        # Get default values from tournament type if available
        default_match_duration = 90
        default_break_duration = 15

        if tournament_type_id:
            cursor.execute("""
                SELECT session_duration_minutes, break_between_sessions_minutes
                FROM tournament_types
                WHERE id = %s
            """, (tournament_type_id,))

            type_result = cursor.fetchone()
            if type_result:
                default_match_duration = type_result[0]
                default_break_duration = type_result[1]

        cursor.close()
        conn.close()

        # Use saved values if available, otherwise use tournament type defaults
        display_match_duration = current_match_duration if current_match_duration else default_match_duration
        display_break_duration = current_break_duration if current_break_duration else default_break_duration
        display_parallel_fields = current_parallel_fields if current_parallel_fields else 1

        st.caption(f"📊 Current start date: {current_start.strftime('%Y-%m-%d') if current_start else 'Not set'}")
        st.caption(f"⏱️ Current match duration: {display_match_duration} min")
        st.caption(f"⏸️ Current break duration: {display_break_duration} min")
        st.caption(f"⚽ Current parallel fields: {display_parallel_fields}")

    except Exception as e:
        st.error(f"❌ Error fetching current configuration: {str(e)}")
        current_start = date.today()
        display_match_duration = 90
        display_break_duration = 15
        display_parallel_fields = 1

    st.divider()

    # Schedule inputs
    col1, col2 = st.columns(2)

    with col1:
        new_start_date = st.date_input(
            "Tournament Start Date",
            value=current_start if current_start else date.today(),
            key="schedule_start_date"
        )

    with col2:
        # Note: start_time will be added when sessions are generated (not stored in semester)
        st.info("💡 Match times will be calculated when sessions are generated")

    col3, col4, col5 = st.columns(3)

    with col3:
        match_duration = st.number_input(
            "Match Duration (minutes)",
            min_value=1,
            max_value=180,
            value=display_match_duration,
            key="schedule_match_duration",
            help="Duration of each match"
        )

    with col4:
        break_duration = st.number_input(
            "Break Between Matches (minutes)",
            min_value=0,
            max_value=60,
            value=display_break_duration,
            key="schedule_break_duration",
            help="Break time between consecutive matches"
        )

    with col5:
        parallel_fields = st.number_input(
            "Parallel Fields/Pitches",
            min_value=1,
            max_value=4,
            value=display_parallel_fields,
            key="schedule_parallel_fields",
            help="Number of fields available for simultaneous matches (optimizes schedule)"
        )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Save Configuration", use_container_width=True, type="primary"):
            try:
                # Connect to database
                db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
                conn = psycopg2.connect(db_url)
                cursor = conn.cursor()

                # Update tournament schedule configuration
                cursor.execute("""
                    UPDATE semesters
                    SET
                        start_date = %s,
                        match_duration_minutes = %s,
                        break_duration_minutes = %s,
                        parallel_fields = %s
                    WHERE id = %s
                """, (new_start_date, match_duration, break_duration, parallel_fields, tournament_id))

                conn.commit()
                cursor.close()
                conn.close()

                st.success(f"✅ Successfully saved schedule configuration!")
                time_module.sleep(1)

                # Clear session state
                if 'edit_schedule_tournament_id' in st.session_state:
                    del st.session_state['edit_schedule_tournament_id']
                if 'edit_schedule_tournament_name' in st.session_state:
                    del st.session_state['edit_schedule_tournament_name']

                st.rerun()

            except Exception as e:
                st.error(f"❌ Error saving configuration: {str(e)}")

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            # Clear session state
            if 'edit_schedule_tournament_id' in st.session_state:
                del st.session_state['edit_schedule_tournament_id']
            if 'edit_schedule_tournament_name' in st.session_state:
                del st.session_state['edit_schedule_tournament_name']
            st.rerun()
