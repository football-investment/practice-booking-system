"""
Session Check-in and Group Assignment Component

Head coach workflow:
1. Select session
2. Mark attendance
3. Auto-assign or manually create groups
4. View/adjust group assignments
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from api_helpers import get_sessions
from api_helpers_session_groups import (
    get_session_bookings,
    get_session_attendance,
    mark_student_attendance,
    auto_assign_groups,
    get_session_groups,
    move_student_to_group,
    delete_session_groups
)


def render_session_checkin(token: str, user_id: int):
    """
    Render session check-in and group assignment interface

    Args:
        token: Authentication token
        user_id: Current user (instructor) ID
    """
    st.markdown("### ✅ Session Check-in & Group Assignment")
    st.caption("Mark attendance and create student groups for your sessions")

    st.divider()

    # Get instructor's upcoming sessions
    with st.spinner("Loading your sessions..."):
        success, sessions = get_sessions(token, size=50, specialization_filter=True)

    if not success or not sessions:
        st.info("No sessions found. Sessions will appear here once they are scheduled.")
        return

    # Filter to instructor's sessions (where they are the instructor)
    my_sessions = [s for s in sessions if s.get('instructor_id') == user_id]

    if not my_sessions:
        st.info("No sessions assigned to you as instructor.")
        return

    # Filter to upcoming and today's sessions (within 7 days)
    now = datetime.now()
    recent_sessions = []
    for session in my_sessions:
        try:
            start_time = datetime.fromisoformat(session.get('date_start', '').replace('Z', '+00:00'))
            # Include sessions from 1 day ago to 7 days in future
            if (now - timedelta(days=1)) <= start_time <= (now + timedelta(days=7)):
                recent_sessions.append(session)
        except:
            pass

    if not recent_sessions:
        st.info("No sessions in the next 7 days. Check back closer to session time.")
        return

    # Session selector
    st.markdown("#### 📅 Select Session")

    session_options = {}
    for session in sorted(recent_sessions, key=lambda s: s.get('date_start', '')):
        try:
            start_time = datetime.fromisoformat(session.get('date_start', '').replace('Z', '+00:00'))
            is_today = start_time.date() == now.date()
            is_past = start_time < now
            time_indicator = "🔴 NOW" if is_today and not is_past else ("✅ PAST" if is_past else "🔜 UPCOMING")

            label = f"{time_indicator} | {session.get('title')} - {start_time.strftime('%Y-%m-%d %H:%M')}"
            session_options[label] = session
        except:
            pass

    if not session_options:
        st.info("No valid sessions to check in.")
        return

    selected_label = st.selectbox(
        "Choose session:",
        options=list(session_options.keys()),
        help="Select a session to mark attendance and create groups"
    )

    selected_session = session_options[selected_label]
    session_id = selected_session['id']

    st.divider()

    # Create tabs for workflow
    tab1, tab2, tab3 = st.tabs(["👥 Attendance", "🎯 Auto-Assign Groups", "📊 Group Overview"])

    # ========================================
    # TAB 1: ATTENDANCE MARKING
    # ========================================
    with tab1:
        render_attendance_tab(token, selected_session)

    # ========================================
    # TAB 2: AUTO-ASSIGN GROUPS
    # ========================================
    with tab2:
        render_auto_assign_tab(token, session_id)

    # ========================================
    # TAB 3: GROUP OVERVIEW
    # ========================================
    with tab3:
        render_group_overview_tab(token, session_id)


def render_attendance_tab(token: str, session: Dict):
    """Render attendance marking interface"""
    session_id = session['id']

    st.markdown("#### 👥 Mark Student Attendance")
    st.caption("Check in students who are present at the session")

    # Get bookings
    success, bookings = get_session_bookings(token, session_id)

    if not success or not bookings:
        st.info("No bookings for this session yet.")
        return

    # Get existing attendance
    att_success, attendance_records = get_session_attendance(token, session_id)
    attendance_map = {}
    if att_success:
        for att in attendance_records:
            attendance_map[att.get('user_id')] = att.get('status', 'unknown')

    st.markdown(f"**Total Bookings:** {len(bookings)}")

    st.divider()

    # Display students with attendance status
    for booking in bookings:
        user = booking.get('user', {})
        user_id = user.get('id')
        user_name = user.get('name', 'Unknown Student')
        booking_id = booking.get('id')

        current_status = attendance_map.get(user_id, None)

        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            if current_status == 'present':
                st.success(f"✅ {user_name}")
            elif current_status == 'absent':
                st.error(f"❌ {user_name}")
            elif current_status == 'late':
                st.warning(f"⏰ {user_name}")
            else:
                st.info(f"⏳ {user_name}")

        with col2:
            if st.button("✅ Present", key=f"present_{user_id}", use_container_width=True):
                success, msg = mark_student_attendance(token, session_id, user_id, "present", booking_id)
                if success:
                    st.success("Marked present")
                    st.rerun()
                else:
                    st.error(f"Error: {msg}")

        with col3:
            if st.button("❌ Absent", key=f"absent_{user_id}", use_container_width=True):
                success, msg = mark_student_attendance(token, session_id, user_id, "absent", booking_id)
                if success:
                    st.warning("Marked absent")
                    st.rerun()
                else:
                    st.error(f"Error: {msg}")

    # Summary
    if attendance_map:
        st.divider()
        present_count = sum(1 for s in attendance_map.values() if s == 'present')
        absent_count = sum(1 for s in attendance_map.values() if s == 'absent')

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("✅ Present", present_count)
        with col2:
            st.metric("❌ Absent", absent_count)
        with col3:
            st.metric("⏳ Not Checked", len(bookings) - len(attendance_map))


def render_auto_assign_tab(token: str, session_id: int):
    """Render auto-assign groups interface"""
    st.markdown("#### 🎯 Auto-Assign Students to Groups")
    st.caption("Automatically create balanced groups based on attendance")

    # Check if groups already exist
    success, existing_groups = get_session_groups(token, session_id)

    if success and existing_groups and existing_groups.get('groups'):
        st.warning("⚠️ Groups already exist for this session!")
        st.markdown("You can:")
        st.markdown("- View groups in the **Group Overview** tab")
        st.markdown("- Delete and re-assign below")

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🗑️ Delete Groups & Reassign", type="secondary", use_container_width=True):
                delete_success, delete_msg = delete_session_groups(token, session_id)
                if delete_success:
                    st.success("Groups deleted. You can now re-assign.")
                    st.rerun()
                else:
                    st.error(f"Error: {delete_msg}")

        with col2:
            st.caption("This will remove all current group assignments")

        return

    # Get attendance summary
    att_success, attendance_records = get_session_attendance(token, session_id)

    if not att_success or not attendance_records:
        st.info("No attendance records yet. Mark attendance in the 'Attendance' tab first.")
        return

    present_students = [a for a in attendance_records if a.get('status') == 'present']
    absent_students = [a for a in attendance_records if a.get('status') == 'absent']

    st.markdown(f"**Students Present:** {len(present_students)}")
    st.markdown(f"**Students Absent:** {len(absent_students)}")

    if len(present_students) == 0:
        st.warning("⚠️ No students marked as present yet. Cannot create groups.")
        return

    st.divider()

    st.markdown("**Auto-Assign Algorithm:**")
    st.markdown("- Distributes PRESENT students evenly across available instructors")
    st.markdown("- Each instructor gets a balanced group")
    st.markdown("- Example: 6 students + 2 instructors = 2 groups of 3")

    st.divider()

    if st.button("🎯 Auto-Assign Groups Now", type="primary", use_container_width=True):
        with st.spinner("Creating groups..."):
            success, group_data, msg = auto_assign_groups(token, session_id)

        if success:
            st.success("✅ Groups created successfully!")
            st.balloons()

            # Show created groups
            if group_data and group_data.get('groups'):
                st.markdown("**Created Groups:**")
                for group in group_data['groups']:
                    st.markdown(f"**Group {group['group_number']}:** {group['instructor_name']} - {group['student_count']} students")
                    st.caption(f"Students: {', '.join(group['students'])}")

            st.info("Go to 'Group Overview' tab to view and adjust groups")
            st.rerun()
        else:
            st.error(f"❌ Failed to create groups: {msg}")


def render_group_overview_tab(token: str, session_id: int):
    """Render group overview and manual adjustment interface"""
    st.markdown("#### 📊 Group Overview")
    st.caption("View and manually adjust group assignments")

    # Get groups
    success, group_data = get_session_groups(token, session_id)

    if not success or not group_data or not group_data.get('groups'):
        st.info("No groups created yet. Use the 'Auto-Assign Groups' tab to create groups.")
        return

    groups = group_data.get('groups', [])
    total_students = group_data.get('total_students', 0)
    total_instructors = group_data.get('total_instructors', 0)

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👥 Total Students", total_students)
    with col2:
        st.metric("👨‍🏫 Instructors", total_instructors)
    with col3:
        st.metric("🎯 Groups", len(groups))

    st.divider()

    # Display groups
    for group in groups:
        group_num = group.get('group_number')
        instructor_name = group.get('instructor_name', 'Unknown')
        student_count = group.get('student_count', 0)
        students = group.get('students', [])

        with st.expander(f"**Group {group_num}** - {instructor_name} ({student_count} students)", expanded=True):
            if students:
                for student in students:
                    st.markdown(f"- {student}")
            else:
                st.caption("No students in this group")

    st.divider()

    # Manual adjustment
    st.markdown("#### ✏️ Manual Adjustments")
    st.caption("Move students between groups if needed")

    # Student selector
    all_students = []
    for group in groups:
        for student_name, student_id in zip(group.get('students', []), group.get('student_ids', [])):
            all_students.append({
                'name': student_name,
                'id': student_id,
                'current_group': group.get('group_number'),
                'group_id': group.get('group_number')  # Simplified - would need actual group DB ID
            })

    if all_students:
        student_names = [f"{s['name']} (Group {s['current_group']})" for s in all_students]

        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            selected_student_label = st.selectbox("Select student:", student_names)
            selected_idx = student_names.index(selected_student_label)
            selected_student = all_students[selected_idx]

        with col2:
            available_groups = [g['group_number'] for g in groups if g['group_number'] != selected_student['current_group']]
            if available_groups:
                target_group = st.selectbox("Move to group:", available_groups)
            else:
                st.caption("No other groups available")
                target_group = None

        with col3:
            if target_group and st.button("➡️ Move", use_container_width=True):
                # TODO: Implement move (need actual group IDs from backend)
                st.info("Manual move feature coming soon!")
                # success, msg = move_student_to_group(token, selected_student['id'], from_group_id, to_group_id)

    else:
        st.caption("No students to move")

    st.divider()

    # Reset option
    if st.button("🗑️ Delete All Groups", type="secondary"):
        success, msg = delete_session_groups(token, session_id)
        if success:
            st.success("Groups deleted successfully")
            st.rerun()
        else:
            st.error(f"Error: {msg}")
