"""
Admin Dashboard - Tournaments Tab Component
Tournaments management with game type editing
"""

import streamlit as st
from pathlib import Path
import sys
from typing import List, Dict
import requests
import time

# Setup imports
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

# Tournament components
from components.tournaments.player_tournament_generator import render_tournament_generator
from api_helpers_general import get_semesters, get_sessions
from api_helpers_tournaments import update_session_game_type, update_tournament


# ==================================================
# GAME TYPE OPTIONS - Tournament Match Formats
# ==================================================
# All game types support fixed durations: 1, 3, or 5 minutes

GAME_TYPE_OPTIONS = [
    "League Match",
    "King of the Court",
    "Group Stage + Placement Matches",
    "Elimination Bracket"
]

# ==================================================
# GAME TYPE DEFINITIONS - Complete Specifications
# ==================================================

GAME_TYPE_DEFINITIONS = {
    "League Match": {
        "display_name": "⚽ League Match",
        "category": "LEAGUE",
        "description": (
            "All participants play against each other in a round-robin format. "
            "Points awarded: win=3, draw=1, loss=0. "
            "Matches can have fixed durations: 1, 3, or 5 minutes. "
            "Used for season-long competitions with multiple rounds."
        ),
        "scoring_system": "TABLE_BASED",
        "ranking_method": "POINTS",
        "use_case": "Long-term competitions, everyone plays everyone",
        "requires_result": True,
        "allows_draw": True,
        "fixed_game_times": [1, 3, 5]  # minutes
    },

    "King of the Court": {
        "display_name": "🏆 King of the Court",
        "category": "SPECIAL",
        "description": (
            "Players compete in a challenge format. 1v1, 1v2, or 1v3 setup. "
            "A fixed game time (1, 3, 5 minutes) per round. "
            "Winner stays on the court; losers rotate out. "
            "The goal is to stay on the court as long as possible."
        ),
        "scoring_system": "WIN_STREAK",
        "ranking_method": "SURVIVAL",
        "use_case": "Short, intense challenge competitions",
        "requires_result": True,
        "allows_draw": False,
        "fixed_game_times": [1, 3, 5]  # minutes
    },

    "Group Stage + Placement Matches": {
        "display_name": "🏆 Group Stage + Placement",
        "category": "GROUP_STAGE",
        "description": (
            "Tournament split into groups. Each group plays round-robin. "
            "After group stage, placement matches determine ranking (1st-4th, 5th-8th, etc.). "
            "Each game has a fixed duration: 1, 3, or 5 minutes. "
            "Used for tournaments needing group stage + knockout-style placement."
        ),
        "scoring_system": "GROUP_TABLE",
        "ranking_method": "POINTS_ADVANCE",
        "use_case": "Tournaments requiring fair group competition and placement",
        "requires_result": True,
        "allows_draw": True,
        "fixed_game_times": [1, 3, 5]  # minutes
    },

    "Elimination Bracket": {
        "display_name": "🔥 Elimination Bracket",
        "category": "KNOCKOUT",
        "description": (
            "Single or double elimination bracket. Loser is out, winner advances. "
            "Each game has fixed duration: 1, 3, or 5 minutes. "
            "Used for tournaments where final winner is determined by knockout rounds."
        ),
        "scoring_system": "WIN_LOSS",
        "ranking_method": "ADVANCE",
        "use_case": "Direct knockout tournaments, final determines champion",
        "requires_result": True,
        "allows_draw": False,
        "fixed_game_times": [1, 3, 5]  # minutes
    }
}


def render_tournaments_tab(token, user):
    """
    Render the Tournaments tab with tournament management features.

    Parameters:
    - token: API authentication token
    - user: Authenticated user object
    """
    st.header("🏆 Tournament Management")

    # 3-tab layout
    tab1, tab2, tab3 = st.tabs([
        "📋 View Tournaments",
        "➕ Create Tournament",
        "⚙️ Manage Games"
    ])

    with tab1:
        render_tournament_list(token)

    with tab2:
        render_tournament_generator()

    with tab3:
        render_game_type_manager(token)


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

                st.write(f"**Max Players**: {tournament.get('max_players', 'N/A')}")
                st.write(f"**Enrollment Cost**: {tournament.get('enrollment_cost', 0)} credits")

            with col3:
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("✏️", key=f"edit_tournament_{tournament['id']}", help="Edit tournament"):
                        st.session_state['edit_tournament_id'] = tournament['id']
                        st.session_state['edit_tournament_data'] = tournament
                        show_edit_tournament_dialog()
                with btn_col2:
                    if st.button("🗑️", key=f"delete_tournament_{tournament['id']}", help="Delete tournament"):
                        st.session_state['delete_tournament_id'] = tournament['id']
                        st.session_state['delete_tournament_name'] = tournament.get('name', 'Untitled')
                        show_delete_tournament_dialog()

            # ========================================================================
            # TOURNAMENT STATUS ACTIONS
            # ========================================================================
            st.divider()
            tournament_status = tournament.get('tournament_status', 'N/A')

            # Open Enrollment button (INSTRUCTOR_CONFIRMED → READY_FOR_ENROLLMENT)
            if tournament_status == 'INSTRUCTOR_CONFIRMED':
                if st.button(
                    "📝 Open Enrollment",
                    key=f"open_enrollment_{tournament['id']}",
                    help="Allow players to enroll in tournament",
                    type="primary",
                    use_container_width=True
                ):
                    st.session_state['open_enrollment_tournament_id'] = tournament['id']
                    st.session_state['open_enrollment_tournament_name'] = tournament.get('name', 'Unknown')
                    show_open_enrollment_dialog()

            # Start Tournament button (READY_FOR_ENROLLMENT → IN_PROGRESS)
            if tournament_status == 'READY_FOR_ENROLLMENT':
                if st.button(
                    "🚀 Start Tournament",
                    key=f"start_tournament_{tournament['id']}",
                    help="Start tournament (requires minimum 2 participants)",
                    type="primary",
                    use_container_width=True
                ):
                    st.session_state['start_tournament_id'] = tournament['id']
                    st.session_state['start_tournament_name'] = tournament.get('name', 'Unknown')
                    show_start_tournament_dialog()

            # ========================================================================
            # INSTRUCTOR APPLICATION MANAGEMENT
            # ========================================================================
            st.divider()
            render_instructor_applications_section(token, tournament)

            # ========================================================================
            # REWARD DISTRIBUTION
            # ========================================================================
            if tournament.get('status') == 'COMPLETED':
                st.divider()
                render_reward_distribution_section(token, tournament)


def render_game_type_manager(token: str):
    """Manage game types for tournament sessions"""
    st.subheader("⚙️ Manage Tournament Games")

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

    # Header with Add button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"**Total Games**: {len(sessions)}")
    with col2:
        if st.button("➕ Add Game", use_container_width=True):
            # Get tournament data
            selected_tournament = next((t for t in tournaments if t['id'] == tournament_id), None)
            st.session_state['add_game_tournament_id'] = tournament_id
            st.session_state['add_game_tournament_data'] = selected_tournament
            show_add_game_dialog()

    st.divider()

    if not sessions:
        st.info("No games yet. Click 'Add Game' to create the first one.")
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
    from datetime import datetime, date, time
    import requests
    from config import API_BASE_URL, API_TIMEOUT

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
    """Dialog for editing tournament details"""
    from datetime import datetime, date

    tournament_id = st.session_state.get('edit_tournament_id')
    tournament_data = st.session_state.get('edit_tournament_data', {})

    st.write(f"**Tournament ID**: {tournament_id}")
    st.write(f"**Name**: {tournament_data.get('name', 'N/A')}")
    st.write(f"**Code**: {tournament_data.get('code', 'N/A')}")
    st.divider()

    # Current dates
    current_start = tournament_data.get('start_date', '')
    current_end = tournament_data.get('end_date', '')

    # Parse current dates
    try:
        if 'T' in current_start:
            start_date_obj = datetime.fromisoformat(current_start.replace('Z', '')).date()
        else:
            start_date_obj = datetime.strptime(current_start[:10], '%Y-%m-%d').date()
    except:
        start_date_obj = date.today()

    try:
        if 'T' in current_end:
            end_date_obj = datetime.fromisoformat(current_end.replace('Z', '')).date()
        else:
            end_date_obj = datetime.strptime(current_end[:10], '%Y-%m-%d').date()
    except:
        end_date_obj = date.today()

    # Date inputs
    col1, col2 = st.columns(2)

    with col1:
        new_start_date = st.date_input(
            "Start Date",
            value=start_date_obj,
            key="tournament_start_date"
        )

    with col2:
        new_end_date = st.date_input(
            "End Date",
            value=end_date_obj,
            key="tournament_end_date"
        )

    # Status selector
    STATUS_OPTIONS = [
        "DRAFT",
        "SEEKING_INSTRUCTOR",
        "INSTRUCTOR_ASSIGNED",
        "READY_FOR_ENROLLMENT",
        "ONGOING",
        "COMPLETED",
        "CANCELLED"
    ]

    current_status = tournament_data.get('status', 'DRAFT')
    try:
        status_index = STATUS_OPTIONS.index(current_status)
    except:
        status_index = 0

    new_status = st.selectbox(
        "Tournament Status",
        options=STATUS_OPTIONS,
        index=status_index,
        key="tournament_status"
    )

    st.divider()

    # Action buttons
    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Save Changes", use_container_width=True):
            token = st.session_state.get('token')

            # Validate that end date is after start date
            if new_end_date <= new_start_date:
                st.error("❌ End date must be after start date!")
                return

            # Build update payload
            update_data = {
                "start_date": new_start_date.isoformat(),
                "end_date": new_end_date.isoformat(),
                "status": new_status
            }

            success, error, updated = update_tournament(token, tournament_id, update_data)

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
    import requests
    from config import API_BASE_URL, API_TIMEOUT

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
    from datetime import datetime, date, time
    import requests
    from config import API_BASE_URL, API_TIMEOUT

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
            value=time(14, 0),
            key="new_game_start_time"
        )

    with col4:
        end_time = st.time_input(
            "End Time",
            value=time(15, 30),
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
    import requests
    from config import API_BASE_URL, API_TIMEOUT

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
    from config import API_BASE_URL

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
                time.sleep(1)
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


# ========================================
# INSTRUCTOR APPLICATION MANAGEMENT
# ========================================

def render_instructor_applications_section(token: str, tournament: Dict):
    """
    Render instructor assignment section based on assignment_type.

    Two workflows:
    1. APPLICATION_BASED: Instructors apply → Admin approves → Instructor accepts
    2. OPEN_ASSIGNMENT: Admin directly invites instructor → Instructor accepts
    """
    from config import API_BASE_URL, API_TIMEOUT

    tournament_id = tournament.get('id')
    status = tournament.get('status', 'N/A')
    master_instructor_id = tournament.get('master_instructor_id')
    assignment_type = tournament.get('assignment_type', 'UNKNOWN')

    st.subheader("👨‍🏫 Instructor Assignment")

    # Show current instructor status
    if master_instructor_id:
        st.success(f"✅ **Instructor Assigned** (ID: {master_instructor_id})")
    elif status == "SEEKING_INSTRUCTOR":
        st.warning(f"⏳ **Seeking Instructor** ({assignment_type})")
    else:
        st.info(f"**Status**: {status}")

    st.divider()

    # 🔥 BRANCHING: Different UI based on assignment_type
    if assignment_type == "APPLICATION_BASED":
        render_application_based_workflow(token, tournament_id)
    elif assignment_type == "OPEN_ASSIGNMENT":
        render_open_assignment_workflow(token, tournament_id, master_instructor_id)
    else:
        st.warning(f"⚠️ Unknown assignment type: {assignment_type}")


def render_application_based_workflow(token: str, tournament_id: int):
    """
    Workflow 1: APPLICATION_BASED
    Instructors apply → Admin reviews → Admin approves → Instructor accepts
    """
    # Fetch pending applications for this tournament
    applications = get_instructor_applications(token, tournament_id)

    if not applications:
        st.info("📭 No instructor applications yet")
        st.caption("Instructors can apply through their dashboard")
        return

    st.write(f"**Applications**: {len(applications)}")
    st.divider()

    # Check if there's already an accepted application
    has_accepted_application = any(app.get('status') == 'ACCEPTED' for app in applications)

    # Display each application
    for app in applications:
        render_instructor_application_card(token, tournament_id, app, has_accepted_application)


def render_open_assignment_workflow(token: str, tournament_id: int, current_instructor_id: int = None):
    """
    Workflow 2: OPEN_ASSIGNMENT
    Admin directly selects instructor → Sends invitation → Instructor accepts
    """
    from config import API_BASE_URL, API_TIMEOUT

    # If instructor already assigned, show status
    if current_instructor_id:
        st.success("✅ Instructor directly assigned")
        return

    st.info("🔒 **Direct Assignment Mode**")
    st.caption("Select an instructor to invite directly (no application required)")
    st.divider()

    # Fetch all instructors with LFA_COACH license
    instructors = get_all_instructors_with_coach_license(token)

    if not instructors:
        st.warning("⚠️ No instructors available with LFA_COACH license")
        st.caption("Create instructor accounts first")
        return

    # Instructor selector
    instructor_options = {
        f"{instr.get('name', 'Unnamed')} ({instr.get('email', 'No email')})": instr['id']
        for instr in instructors
    }

    selected_instructor_name = st.selectbox(
        "Select Instructor",
        options=["-- Select an instructor --"] + list(instructor_options.keys()),
        key=f"instructor_selector_{tournament_id}"
    )

    if selected_instructor_name == "-- Select an instructor --":
        st.caption("ℹ️ Choose an instructor from the dropdown to proceed")
        return

    selected_instructor_id = instructor_options[selected_instructor_name]

    # Optional invitation message
    invitation_message = st.text_area(
        "Invitation Message (optional)",
        value=f"You have been selected to lead this tournament. Please accept this invitation.",
        key=f"invitation_message_{tournament_id}",
        height=100
    )

    st.divider()

    # Send invitation button
    if st.button(
        "📨 Send Direct Invitation",
        key=f"send_invitation_{tournament_id}",
        type="primary",
        use_container_width=True
    ):
        send_direct_invitation(token, tournament_id, selected_instructor_id, invitation_message)


def get_instructor_applications(token: str, tournament_id: int) -> List[Dict]:
    """Fetch instructor applications for a tournament"""
    from config import API_BASE_URL, API_TIMEOUT

    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/instructor-applications",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            return data.get('applications', [])
        else:
            return []
    except Exception:
        return []


def render_instructor_application_card(token: str, tournament_id: int, application: Dict, has_accepted_application: bool = False):
    """
    Render a single instructor application with approve/reject buttons.

    Args:
        has_accepted_application: If True, hide approve/reject buttons for PENDING applications
                                  (since another application is already accepted)
    """
    from config import API_BASE_URL, API_TIMEOUT

    app_id = application.get('id')
    instructor_name = application.get('instructor_name', 'Unknown')
    instructor_email = application.get('instructor_email', 'N/A')
    status = application.get('status', 'PENDING')
    applied_at = application.get('created_at', 'N/A')
    request_message = application.get('request_message') or application.get('application_message', '')

    # Status badge color
    status_color = {
        'PENDING': '🟡',
        'ACCEPTED': '🟢',
        'DECLINED': '🔴',
        'CANCELLED': '⚫',
        'EXPIRED': '⚪'
    }.get(status, '⚪')

    with st.container():
        st.markdown(f"**{status_color} Application #{app_id}** - {instructor_name}")

        col1, col2 = st.columns([3, 1])

        with col1:
            st.caption(f"📧 {instructor_email}")
            st.caption(f"📅 Applied: {applied_at[:19] if len(applied_at) > 19 else applied_at}")
            if request_message:
                st.caption(f"💬 Message: {request_message}")

        with col2:
            # Only show approve/reject buttons for PENDING applications IF no instructor is accepted yet
            if status == 'PENDING':
                if has_accepted_application:
                    # Another instructor is already accepted - don't show action buttons
                    st.caption("ℹ️ _Instructor already selected_")
                else:
                    # No accepted instructor yet - show approve/reject buttons
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button("✅", key=f"approve_app_{app_id}", help="Approve application"):
                            st.session_state['approve_app_id'] = app_id
                            st.session_state['approve_tournament_id'] = tournament_id
                            st.session_state['approve_instructor_name'] = instructor_name
                            show_approve_application_dialog()
                    with btn_col2:
                        if st.button("❌", key=f"reject_app_{app_id}", help="Reject application"):
                            st.session_state['reject_app_id'] = app_id
                            st.session_state['reject_tournament_id'] = tournament_id
                            st.session_state['reject_instructor_name'] = instructor_name
                            show_reject_application_dialog()
            else:
                st.caption(f"**Status**: {status}")

        st.divider()


@st.dialog("✅ Approve Instructor Application")
def show_approve_application_dialog():
    """Dialog for approving an instructor application"""
    from config import API_BASE_URL, API_TIMEOUT

    app_id = st.session_state.get('approve_app_id')
    tournament_id = st.session_state.get('approve_tournament_id')
    instructor_name = st.session_state.get('approve_instructor_name', 'Unknown')

    st.write(f"**Approve application from**: {instructor_name}")
    st.write(f"**Application ID**: {app_id}")
    st.divider()

    # Optional response message
    response_message = st.text_area(
        "Response Message (optional)",
        value="Application approved - looking forward to working with you!",
        key="approve_response_message"
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Approve", use_container_width=True, type="primary"):
            token = st.session_state.get('token')

            try:
                response = requests.post(
                    f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/instructor-applications/{app_id}/approve",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"response_message": response_message},
                    timeout=API_TIMEOUT
                )

                if response.status_code == 200:
                    st.success("✅ Application approved successfully!")
                    st.info("ℹ️ Tournament is now ready - you can open enrollment for players.")
                    time.sleep(2)
                    # Clear session state
                    if 'approve_app_id' in st.session_state:
                        del st.session_state['approve_app_id']
                    if 'approve_tournament_id' in st.session_state:
                        del st.session_state['approve_tournament_id']
                    if 'approve_instructor_name' in st.session_state:
                        del st.session_state['approve_instructor_name']

                    # Force cache invalidation by setting a timestamp
                    # This ensures fresh tournament data is fetched after approval
                    st.session_state['last_tournament_update'] = time.time()

                    st.rerun()
                else:
                    error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                    error_msg = error_data.get('detail', response.text)
                    st.error(f"❌ Error: {error_msg}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    with col2:
        if st.button("Cancel", use_container_width=True):
            # Clear session state
            if 'approve_app_id' in st.session_state:
                del st.session_state['approve_app_id']
            if 'approve_tournament_id' in st.session_state:
                del st.session_state['approve_tournament_id']
            if 'approve_instructor_name' in st.session_state:
                del st.session_state['approve_instructor_name']
            st.rerun()


@st.dialog("❌ Reject Instructor Application")
def show_reject_application_dialog():
    """Dialog for rejecting an instructor application"""
    from config import API_BASE_URL, API_TIMEOUT

    app_id = st.session_state.get('reject_app_id')
    tournament_id = st.session_state.get('reject_tournament_id')
    instructor_name = st.session_state.get('reject_instructor_name', 'Unknown')

    st.warning(f"**Reject application from**: {instructor_name}")
    st.write(f"**Application ID**: {app_id}")
    st.divider()

    # Optional response message
    response_message = st.text_area(
        "Rejection Reason (optional)",
        value="Thank you for your interest, but we have selected another instructor.",
        key="reject_response_message"
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("❌ Reject", use_container_width=True, type="primary"):
            token = st.session_state.get('token')

            # Note: Backend doesn't have a reject endpoint yet, we'll use PATCH to update status
            try:
                response = requests.patch(
                    f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/instructor-applications/{app_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "status": "DECLINED",
                        "response_message": response_message
                    },
                    timeout=API_TIMEOUT
                )

                if response.status_code == 200:
                    st.success("✅ Application rejected successfully!")
                    time.sleep(2)
                    # Clear session state
                    if 'reject_app_id' in st.session_state:
                        del st.session_state['reject_app_id']
                    if 'reject_tournament_id' in st.session_state:
                        del st.session_state['reject_tournament_id']
                    if 'reject_instructor_name' in st.session_state:
                        del st.session_state['reject_instructor_name']
                    st.rerun()
                else:
                    error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                    error_msg = error_data.get('detail', response.text)
                    st.error(f"❌ Error: {error_msg}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    with col2:
        if st.button("Cancel", use_container_width=True):
            # Clear session state
            if 'reject_app_id' in st.session_state:
                del st.session_state['reject_app_id']
            if 'reject_tournament_id' in st.session_state:
                del st.session_state['reject_tournament_id']
            if 'reject_instructor_name' in st.session_state:
                del st.session_state['reject_instructor_name']
            st.rerun()


# ============================================================================
# REWARD DISTRIBUTION SECTION
# ============================================================================

def render_reward_distribution_section(token: str, tournament: Dict):
    """
    Render reward distribution section for COMPLETED tournaments.

    Shows:
    - Tournament completion status
    - Reward distribution button
    - Distribution results
    """
    from config import API_BASE_URL, API_TIMEOUT

    tournament_id = tournament.get('id')
    tournament_name = tournament.get('name', 'Unknown')

    st.subheader("🎁 Reward Distribution")

    # Check if rewards already distributed
    reward_policy = tournament.get('reward_policy_snapshot')
    if reward_policy:
        st.success("✅ **Reward policy configured**")
        st.caption(f"Policy: {reward_policy.get('name', 'Unknown')}")
    else:
        st.warning("⚠️ **No reward policy configured for this tournament**")
        st.caption("Rewards cannot be distributed without a configured policy.")
        return

    st.divider()

    # Distribute Rewards button
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.button(
            "🎁 Distribute Rewards",
            key=f"distribute_{tournament_id}",
            use_container_width=True,
            type="primary",
            help="Distribute XP and credits to tournament participants based on rankings"
        ):
            # Call distribute rewards endpoint
            try:
                with st.spinner("Distributing rewards..."):
                    response = requests.post(
                        f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/distribute-rewards",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=API_TIMEOUT
                    )

                    if response.status_code == 200:
                        result = response.json()

                        st.success("✅ **Rewards distributed successfully!**")

                        # Display distribution summary
                        col_a, col_b, col_c = st.columns(3)

                        with col_a:
                            st.metric(
                                "👥 Participants",
                                result.get('total_participants', 0)
                            )

                        with col_b:
                            st.metric(
                                "⭐ Total XP",
                                result.get('xp_distributed', 0)
                            )

                        with col_c:
                            st.metric(
                                "💰 Total Credits",
                                result.get('credits_distributed', 0)
                            )

                        # Show individual rewards if available
                        if 'rewards' in result:
                            st.divider()
                            st.caption("**Individual Rewards:**")

                            for reward in result.get('rewards', []):
                                placement = reward.get('placement', 'N/A')
                                player_name = reward.get('player_name', 'Unknown')
                                xp = reward.get('xp', 0)
                                credits = reward.get('credits', 0)

                                st.caption(
                                    f"• **{placement}** - {player_name}: "
                                    f"+{xp} XP, +{credits} credits"
                                )

                        time.sleep(2)
                        st.rerun()

                    else:
                        error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                        error_msg = error_data.get('detail', response.text)
                        st.error(f"❌ Distribution failed: {error_msg}")

            except Exception as e:
                st.error(f"❌ Error distributing rewards: {str(e)}")


# ============================================================================
# TOURNAMENT STATUS TRANSITION DIALOGS
# ============================================================================

@st.dialog("📝 Open Enrollment")
def show_open_enrollment_dialog():
    """Dialog for opening enrollment (INSTRUCTOR_CONFIRMED → READY_FOR_ENROLLMENT)"""
    from config import API_BASE_URL, API_TIMEOUT

    tournament_id = st.session_state.get('open_enrollment_tournament_id')
    tournament_name = st.session_state.get('open_enrollment_tournament_name', 'Unknown')

    st.write(f"**Tournament**: {tournament_name}")
    st.write(f"**Tournament ID**: {tournament_id}")
    st.divider()

    st.info("ℹ️ This will open enrollment for this tournament.")
    st.warning("⚠️ Players will be able to enroll after this action.")

    # Reason for transition
    reason = st.text_area(
        "Reason",
        value="Opening enrollment for tournament",
        key="open_enrollment_reason"
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📝 Open Enrollment", use_container_width=True, type="primary"):
            token = st.session_state.get('token')

            try:
                response = requests.patch(
                    f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/status",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "new_status": "READY_FOR_ENROLLMENT",
                        "reason": reason
                    },
                    timeout=API_TIMEOUT
                )

                if response.status_code == 200:
                    st.success("✅ Enrollment opened successfully!")
                    st.balloons()
                    time.sleep(2)
                    # Clear session state
                    if 'open_enrollment_tournament_id' in st.session_state:
                        del st.session_state['open_enrollment_tournament_id']
                    if 'open_enrollment_tournament_name' in st.session_state:
                        del st.session_state['open_enrollment_tournament_name']
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
            if 'open_enrollment_tournament_id' in st.session_state:
                del st.session_state['open_enrollment_tournament_id']
            if 'open_enrollment_tournament_name' in st.session_state:
                del st.session_state['open_enrollment_tournament_name']
            st.rerun()


@st.dialog("🚀 Start Tournament")
def show_start_tournament_dialog():
    """Dialog for starting a tournament (READY_FOR_ENROLLMENT → IN_PROGRESS)"""
    from config import API_BASE_URL, API_TIMEOUT

    tournament_id = st.session_state.get('start_tournament_id')
    tournament_name = st.session_state.get('start_tournament_name', 'Unknown')

    st.write(f"**Tournament**: {tournament_name}")
    st.write(f"**Tournament ID**: {tournament_id}")
    st.divider()

    st.info("ℹ️ This will start the tournament and transition to **IN_PROGRESS** status.")
    st.warning("⚠️ Requires minimum 2 enrolled participants.")

    # Reason for transition
    reason = st.text_area(
        "Transition Reason",
        value="Tournament started - enrollment closed",
        key="start_tournament_reason"
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 Start Tournament", use_container_width=True, type="primary"):
            token = st.session_state.get('token')

            try:
                response = requests.patch(
                    f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/status",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "new_status": "IN_PROGRESS",
                        "reason": reason
                    },
                    timeout=API_TIMEOUT
                )

                if response.status_code == 200:
                    st.success("✅ Tournament started successfully!")
                    st.balloons()
                    time.sleep(2)
                    # Clear session state
                    if 'start_tournament_id' in st.session_state:
                        del st.session_state['start_tournament_id']
                    if 'start_tournament_name' in st.session_state:
                        del st.session_state['start_tournament_name']
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
            if 'start_tournament_id' in st.session_state:
                del st.session_state['start_tournament_id']
            if 'start_tournament_name' in st.session_state:
                del st.session_state['start_tournament_name']
            st.rerun()


# ============================================================================
# HELPER FUNCTIONS FOR OPEN_ASSIGNMENT WORKFLOW
# ============================================================================

def get_all_instructors_with_coach_license(token: str) -> List[Dict]:
    """
    Fetch all instructors with active LFA_COACH license.

    Returns: List of instructor user objects with license information
    """
    from config import API_BASE_URL, API_TIMEOUT

    try:
        # Fetch all users with INSTRUCTOR role
        response = requests.get(
            f"{API_BASE_URL}/api/v1/users/",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "role": "instructor",
                "is_active": True,
                "size": 100
            },
            timeout=API_TIMEOUT
        )

        if response.status_code != 200:
            return []

        data = response.json()
        all_instructors = data.get("users", [])

        # For now, return all instructors
        # TODO: In production, filter for LFA_COACH license
        # The backend direct-assign-instructor endpoint validates license anyway
        return all_instructors

        # Filter for instructors with LFA_COACH license
        # Commented out for now because license endpoint structure needs verification
        # instructors_with_license = []
        #
        # for instructor in all_instructors:
        #     # Fetch licenses for this instructor
        #     license_response = requests.get(
        #         f"{API_BASE_URL}/api/v1/user-licenses/user/{instructor['id']}",
        #         headers={"Authorization": f"Bearer {token}"},
        #         timeout=API_TIMEOUT
        #     )
        #
        #     if license_response.status_code == 200:
        #         licenses = license_response.json()
        #
        #         # Check if they have LFA_COACH license
        #         has_coach_license = any(
        #             lic.get('specialization_type') == 'LFA_COACH'
        #             for lic in licenses
        #         )
        #
        #         if has_coach_license:
        #             instructors_with_license.append(instructor)
        #
        # return instructors_with_license

    except Exception as e:
        st.error(f"❌ Error fetching instructors: {str(e)}")
        return []


def send_direct_invitation(token: str, tournament_id: int, instructor_id: int, message: str):
    """
    Send direct invitation to instructor for OPEN_ASSIGNMENT tournament.

    Calls the backend API to directly assign instructor to tournament.
    """
    from config import API_BASE_URL, API_TIMEOUT

    try:
        with st.spinner("Sending invitation..."):
            response = requests.post(
                f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/direct-assign-instructor",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "instructor_id": instructor_id,
                    "assignment_message": message
                },
                timeout=API_TIMEOUT
            )

            if response.status_code == 200:
                result = response.json()

                st.success("✅ **Invitation sent successfully!**")
                st.info("ℹ️ Instructor has been notified and must accept the assignment.")

                # Display assignment details
                st.divider()
                st.caption("**Assignment Details:**")
                st.caption(f"• Instructor: {result.get('instructor_name', 'Unknown')}")
                st.caption(f"• Status: {result.get('status', 'PENDING')}")
                st.caption(f"• Assignment ID: {result.get('assignment_id', 'N/A')}")

                time.sleep(2)
                st.rerun()

            elif response.status_code == 400:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                error_detail = error_data.get('detail', {})

                if isinstance(error_detail, dict):
                    error_msg = error_detail.get('message', response.text)
                    error_type = error_detail.get('error', 'unknown_error')

                    if error_type == 'license_required':
                        st.error("❌ **License Error**: Selected instructor does not have LFA_COACH license")
                    elif error_type == 'invalid_tournament_status':
                        st.error(f"❌ **Status Error**: {error_msg}")
                        st.caption(f"Current status: {error_detail.get('current_status', 'N/A')}")
                    else:
                        st.error(f"❌ **Error**: {error_msg}")
                else:
                    st.error(f"❌ Error: {error_detail}")

            elif response.status_code == 403:
                st.error("❌ **Permission Denied**: Only admins can directly assign instructors")

            elif response.status_code == 404:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                error_detail = error_data.get('detail', {})

                if isinstance(error_detail, dict):
                    error_type = error_detail.get('error', 'not_found')

                    if error_type == 'tournament_not_found':
                        st.error("❌ **Tournament Not Found**")
                    elif error_type == 'instructor_not_found':
                        st.error("❌ **Instructor Not Found**")
                    else:
                        st.error(f"❌ **Not Found**: {error_detail.get('message', 'Resource not found')}")
                else:
                    st.error("❌ Resource not found")

            else:
                st.error(f"❌ Failed to send invitation: Server error {response.status_code}")

    except Exception as e:
        st.error(f"❌ Error sending invitation: {str(e)}")
