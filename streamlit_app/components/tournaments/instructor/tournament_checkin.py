"""
Tournament Check-in Component - TOURNAMENT-ONLY VERSION

This is a specialized check-in wizard for TOURNAMENTS ONLY.
Key differences from regular session check-in:
- ONLY 2 attendance statuses: Present, Absent (no Late/Excused)
- Tournament-specific workflow
- Master instructor group assignment
- Integration with tournament game results

For regular sessions (with 4 attendance statuses), use:
    streamlit_app/components/sessions/session_checkin.py

Wizard flow:
Step 1: Tournament Session Selection
Step 2: Attendance Roll Call (Present/Absent ONLY)
Step 3: Group Creation
Step 4: Group Overview & Adjustments
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List
import time
from streamlit_app.api_helpers_general import get_sessions
from streamlit_app.api_helpers_session_groups import (
    get_session_bookings,
    get_session_attendance,
    mark_student_attendance,
    auto_assign_groups,
    get_session_groups,
    move_student_to_group,
    delete_session_groups
)
from streamlit_app.api_helpers_tournaments import get_tournament_enrollment_count
from components.sessions.shared.attendance_core import (
    calculate_attendance_summary,
    render_attendance_status_badge
)


def render_tournament_checkin(token: str, user_id: int):
    """
    Render tournament-specific check-in wizard.

    IMPORTANT: This function is for TOURNAMENT SESSIONS ONLY.
    - Attendance: ONLY Present/Absent (no Late/Excused)
    - Master instructor workflow
    - Tournament game integration

    Args:
        token: Authentication token
        user_id: Current user (master instructor) ID
    """
    st.markdown("### 🏆 Tournament Check-in & Group Assignment")
    st.caption("Tournament-specific wizard: Present/Absent attendance only")

    # Initialize wizard state
    if 'wizard_step' not in st.session_state:
        st.session_state.wizard_step = 1
    if 'selected_session_id' not in st.session_state:
        st.session_state.selected_session_id = None
    if 'selected_session' not in st.session_state:
        st.session_state.selected_session = None
    if 'attendance_marked' not in st.session_state:
        st.session_state.attendance_marked = {}
    if 'groups_created' not in st.session_state:
        st.session_state.groups_created = False

    st.divider()

    # Render progress indicator
    _render_wizard_progress(st.session_state.wizard_step)

    st.divider()

    # Route to current step
    if st.session_state.wizard_step == 1:
        _render_step1_tournament_selection(token, user_id)
    elif st.session_state.wizard_step == 2:
        _render_step2_tournament_attendance(token, user_id)
    elif st.session_state.wizard_step == 3:
        _render_step3_group_creation(token, user_id)
    elif st.session_state.wizard_step == 4:
        _render_step4_group_overview(token, user_id)


def _render_wizard_progress(current_step: int):
    """Visual progress indicator for tournament wizard"""
    steps = [
        {"num": 1, "icon": "🏆", "label": "Select Tournament"},
        {"num": 2, "icon": "✅", "label": "Mark Attendance"},
        {"num": 3, "icon": "🎯", "label": "Create Groups"},
        {"num": 4, "icon": "📊", "label": "Review & Finish"}
    ]

    cols = st.columns(4)

    for i, step in enumerate(steps):
        with cols[i]:
            if step["num"] < current_step:
                # Completed
                st.markdown(f"""
                <div style="text-align: center; padding: 10px; background: #d1fae5; border-radius: 8px; border: 2px solid #10b981;">
                    <div style="font-size: 24px;">✓</div>
                    <div style="font-size: 12px; color: #065f46; font-weight: 600;">{step['label']}</div>
                </div>
                """, unsafe_allow_html=True)
            elif step["num"] == current_step:
                # Current
                st.markdown(f"""
                <div style="text-align: center; padding: 10px; background: #dbeafe; border-radius: 8px; border: 2px solid #3b82f6;">
                    <div style="font-size: 24px;">{step['icon']}</div>
                    <div style="font-size: 12px; color: #1e40af; font-weight: 600;">{step['label']}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Future
                st.markdown(f"""
                <div style="text-align: center; padding: 10px; background: #f3f4f6; border-radius: 8px; border: 2px solid #d1d5db;">
                    <div style="font-size: 24px; opacity: 0.4;">{step['icon']}</div>
                    <div style="font-size: 12px; color: #6b7280;">{step['label']}</div>
                </div>
                """, unsafe_allow_html=True)


def _render_step1_tournament_selection(token: str, user_id: int):
    """Step 1: Select TOURNAMENT session (filters for is_tournament_game=True)"""
    st.markdown("## Step 1: Select Tournament Session")
    st.caption("Select a tournament game session to check in students")

    # Fetch sessions (instructor's sessions)
    success, sessions = get_sessions(token)

    if not success or not sessions:
        st.info("No sessions available for check-in.")
        return

    # Filter for TOURNAMENT SESSIONS ONLY
    tournament_sessions = [s for s in sessions if s.get('is_tournament_game', False)]

    if not tournament_sessions:
        st.warning("No tournament sessions found. This check-in is for tournaments only.")
        st.caption("For regular sessions, use the regular Session Check-in tab.")
        return

    # Show today's tournament sessions first
    today = datetime.now().date()
    today_tournaments = [s for s in tournament_sessions
                        if datetime.fromisoformat(s['date_start'].replace('Z', '+00:00')).date() == today]
    upcoming_tournaments = [s for s in tournament_sessions
                           if datetime.fromisoformat(s['date_start'].replace('Z', '+00:00')).date() > today]
    past_tournaments = [s for s in tournament_sessions
                       if datetime.fromisoformat(s['date_start'].replace('Z', '+00:00')).date() < today]

    if today_tournaments:
        st.markdown("### 🏆 Today's Tournament Games")
        for session in today_tournaments:
            _render_tournament_session_card(session, token)
        st.divider()

    if upcoming_tournaments:
        st.markdown("### 📅 Upcoming Tournament Games")
        for session in upcoming_tournaments[:5]:
            _render_tournament_session_card(session, token)

    if past_tournaments and not today_tournaments and not upcoming_tournaments:
        st.markdown("### 📜 Past Tournament Games")
        for session in past_tournaments[:5]:
            _render_tournament_session_card(session, token)


def _render_tournament_session_card(session: Dict, token: str):
    """Render clickable tournament session card"""
    session_id = session['id']
    title = session.get('title', 'Untitled Tournament Game')
    game_type = session.get('game_type', 'Tournament Game')
    date_start = datetime.fromisoformat(session['date_start'].replace('Z', '+00:00'))
    capacity = session.get('capacity', 0)

    # ✅ NEW: Get enrollment count for the tournament (source of truth)
    tournament_id = session.get('semester_id')
    enrollment_count = get_tournament_enrollment_count(token, tournament_id) if tournament_id else 0

    with st.container():
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"**🏆 {title}**")
            st.caption(f"🎮 {game_type} | 📅 {date_start.strftime('%Y-%m-%d %H:%M')} | 👥 {enrollment_count}/{capacity} enrolled")

        with col2:
            if st.button(f"Select ➡️", key=f"select_tournament_{session_id}", use_container_width=True):
                st.session_state.selected_session_id = session_id
                st.session_state.selected_session = session
                st.session_state.wizard_step = 2
                st.rerun()

        st.divider()


def _render_step2_tournament_attendance(token: str, user_id: int):
    """
    Step 2: Mark attendance for TOURNAMENT (ONLY Present/Absent buttons)

    CRITICAL: This function shows ONLY 2 buttons (Present, Absent).
    No Late or Excused statuses for tournaments.
    """
    session_id = st.session_state.selected_session_id
    selected_session = st.session_state.selected_session

    if not session_id or not selected_session:
        st.error("No tournament session selected")
        return

    st.markdown("## Step 2: Mark Attendance (Tournament)")
    st.caption(f"🏆 {selected_session.get('title', 'Tournament')} | 🎮 {selected_session.get('game_type', 'Game')}")
    st.info("**Tournament Mode**: Only Present and Absent statuses available")

    # Fetch bookings and attendance
    success_bookings, bookings = get_session_bookings(token, session_id)
    success, attendance_records = get_session_attendance(token, session_id)

    # ✅ DEBUG: Log what we received to troubleshoot duplicate booking errors
    if bookings:
        booking_ids = [b.get('id') for b in bookings]
        print(f"🔍 DEBUG: Fetched {len(bookings)} bookings for session {session_id}: {booking_ids}")

        # Check for duplicates (should be caught by deduplication in api_helpers)
        if len(booking_ids) != len(set(booking_ids)):
            duplicate_ids = [bid for bid in booking_ids if booking_ids.count(bid) > 1]
            print(f"⚠️ WARNING: Duplicate booking IDs detected: {set(duplicate_ids)}")
            st.error(f"⚠️ Data Error: Duplicate bookings detected. Please refresh the page or contact support.")
            return

    if not bookings:
        st.warning("No bookings found for this tournament session.")
        return

    # Build attendance map
    attendance_map = {att.get('user_id'): att.get('status') for att in attendance_records}

    # Calculate summary
    present, absent, late, excused, pending = calculate_attendance_summary(bookings, attendance_map)

    # Tournament summary - ONLY 3 metrics (no Late, no Excused)
    st.markdown("#### 📊 Tournament Attendance Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("✅ Present", present)
    with col2:
        st.metric("❌ Absent", absent)
    with col3:
        st.metric("⏳ Pending", pending)

    st.divider()

    # Display students with TOURNAMENT attendance controls (2 buttons ONLY)
    st.markdown("#### 👥 Player Check-in")

    for booking in bookings:
        user = booking.get('user', {})
        user_id_student = user.get('id')
        user_name = user.get('name', 'Unknown Player')
        user_email = user.get('email', 'N/A')
        booking_id = booking.get('id')

        current_status = attendance_map.get(user_id_student, None)

        col1, col2 = st.columns([2, 2])

        with col1:
            render_attendance_status_badge(user_name, user_email, current_status)

        with col2:
            # TOURNAMENT: ONLY 2 BUTTONS (Present, Absent)
            btn_col1, btn_col2 = st.columns(2)

            with btn_col1:
                if st.button("✅ Present", key=f"present_booking_{booking_id}", use_container_width=True,
                            type="primary" if current_status == 'present' else "secondary"):
                    success, msg = mark_student_attendance(token, session_id, user_id_student, "present", booking_id)
                    if success:
                        st.rerun()
                    else:
                        st.error(f"Error: {msg}")

            with btn_col2:
                if st.button("❌ Absent", key=f"absent_booking_{booking_id}", use_container_width=True,
                            type="primary" if current_status == 'absent' else "secondary"):
                    success, msg = mark_student_attendance(token, session_id, user_id_student, "absent", booking_id)
                    if success:
                        st.rerun()
                    else:
                        st.error(f"Error: {msg}")

        st.divider()

    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("⬅️ Back to Tournament Selection", use_container_width=True):
            st.session_state.wizard_step = 1
            st.rerun()

    with col3:
        can_proceed = present > 0
        if can_proceed:
            if st.button("Next: Create Groups ➡️", type="primary", use_container_width=True):
                st.session_state.wizard_step = 3
                st.rerun()
        else:
            st.button("⚠️ Mark at least 1 player present", disabled=True, use_container_width=True)


def _render_step3_group_creation(token: str, user_id: int):
    """Step 3: Auto-create groups (same logic as regular sessions)"""
    session_id = st.session_state.selected_session_id
    selected_session = st.session_state.selected_session

    if not session_id or not selected_session:
        st.error("No tournament session selected")
        return

    st.markdown("## Step 3: Create Tournament Groups")
    st.caption(f"🏆 {selected_session.get('title', 'Tournament')}")

    # Check existing groups
    existing_groups = get_session_groups(token, session_id)

    if existing_groups:
        st.warning(f"⚠️ Groups already exist for this tournament session ({len(existing_groups)} groups)")
        st.info("Delete existing groups to create new ones, or proceed to review.")

        if st.button("🗑️ Delete Existing Groups & Start Fresh", type="secondary"):
            success, msg = delete_session_groups(token, session_id)
            if success:
                st.success("Groups deleted! Create new groups below.")
                st.rerun()
            else:
                st.error(f"Error: {msg}")
        st.divider()

    # Auto-assign configuration
    st.markdown("### ⚡ Auto-Assign Teams")

    col1, col2 = st.columns(2)
    with col1:
        num_groups = st.number_input(
            "Number of Teams",
            min_value=2,
            max_value=10,
            value=4,
            help="How many teams to create for this tournament game?"
        )
    with col2:
        group_size = st.number_input(
            "Players per Team",
            min_value=3,
            max_value=15,
            value=5,
            help="Recommended team size"
        )

    st.caption(f"ℹ️ Will attempt to create {num_groups} teams with ~{group_size} players each")

    if st.button("🎯 Auto-Create Teams", type="primary", use_container_width=True):
        with st.spinner("Creating tournament teams..."):
            success, msg = auto_assign_groups(token, session_id, num_groups, group_size)

            if success:
                st.success(f"✅ {msg}")
                st.session_state.groups_created = True
                time.sleep(1)
                st.session_state.wizard_step = 4
                st.rerun()
            else:
                st.error(f"❌ {msg}")

    st.divider()

    # Navigation
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("⬅️ Back to Attendance", use_container_width=True):
            st.session_state.wizard_step = 2
            st.rerun()

    if existing_groups:
        with col2:
            if st.button("Skip to Review ➡️", use_container_width=True):
                st.session_state.wizard_step = 4
                st.rerun()


def _render_step4_group_overview(token: str, user_id: int):
    """Step 4: Review and adjust tournament teams"""
    session_id = st.session_state.selected_session_id
    selected_session = st.session_state.selected_session

    if not session_id or not selected_session:
        st.error("No tournament session selected")
        return

    st.markdown("## Step 4: Tournament Teams Overview")
    st.caption(f"🏆 {selected_session.get('title', 'Tournament')}")

    # Fetch groups
    groups = get_session_groups(token, session_id)

    if not groups:
        st.warning("No teams created yet.")
        if st.button("⬅️ Back to Create Teams"):
            st.session_state.wizard_step = 3
            st.rerun()
        return

    st.success(f"✅ {len(groups)} teams created successfully!")

    # Display teams
    for group in groups:
        group_id = group.get('id')
        group_name = group.get('name', f'Team {group_id}')
        members = group.get('members', [])

        with st.expander(f"🎮 {group_name} ({len(members)} players)", expanded=True):
            if members:
                for member in members:
                    user = member.get('user', {})
                    st.markdown(f"- **{user.get('name', 'Unknown')}** ({user.get('email', 'N/A')})")
            else:
                st.caption("No players assigned to this team")

    st.divider()

    # Final actions
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("⬅️ Back to Teams Creation", use_container_width=True):
            st.session_state.wizard_step = 3
            st.rerun()

    with col2:
        if st.button("🔄 Restart Check-in", use_container_width=True):
            st.session_state.wizard_step = 1
            st.session_state.groups_created = False
            st.rerun()

    with col3:
        if st.button("✅ Finish & Close", type="primary", use_container_width=True):
            st.session_state.wizard_step = 1
            st.session_state.selected_session_id = None
            st.session_state.selected_session = None
            st.session_state.groups_created = False
            st.success("🏆 Tournament check-in completed!")
            time.sleep(1.5)
            st.rerun()
