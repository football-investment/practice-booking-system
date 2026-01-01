"""
Admin Dashboard - Tournaments Tab Component
Tournaments management with game type editing
"""

import streamlit as st
from pathlib import Path
import sys
from typing import List, Dict

# Setup imports
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

# Tournament components
from components.tournaments.player_tournament_generator import render_tournament_generator
from api_helpers_general import get_semesters, get_sessions
from api_helpers_tournaments import update_session_game_type, update_tournament


# Game type options for tournament sessions
# Simple league format - everyone plays everyone, ranked by table (like Premier League)
GAME_TYPE_OPTIONS = [
    "League Match"
]


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
                st.write(f"**Start**: {tournament.get('start_date', 'N/A')}")
                st.write(f"**End**: {tournament.get('end_date', 'N/A')}")

            with col2:
                st.write(f"**Age Group**: {tournament.get('age_group', 'N/A')}")
                st.write(f"**Cost**: {tournament.get('enrollment_cost', 0)} credits")
                st.write(f"**ID**: {tournament.get('id', 'N/A')}")

            with col3:
                if st.button("✏️ Edit", key=f"edit_tournament_{tournament['id']}"):
                    st.session_state['edit_tournament_id'] = tournament['id']
                    st.session_state['edit_tournament_data'] = tournament
                    show_edit_tournament_dialog()


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

    # Game details
    title = st.text_input("Game Title", value="League Match", key="new_game_title")

    # Game Type
    game_type = st.selectbox(
        "Game Type",
        options=GAME_TYPE_OPTIONS,
        index=0,
        key="new_game_type"
    )

    st.divider()
    st.subheader("📅 Date & Time")

    col1, col2 = st.columns(2)

    with col1:
        game_date = st.date_input(
            "Date",
            value=date.today(),
            key="new_game_date"
        )

    with col2:
        st.write("")  # Spacing

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
            create_payload = {
                "title": title,
                "description": "",
                "date_start": start_datetime.isoformat(),
                "date_end": end_datetime.isoformat(),
                "session_type": "on_site",
                "capacity": 20,
                "semester_id": tournament_id,
                "instructor_id": tournament_data.get('master_instructor_id'),
                "credit_cost": 1,
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
