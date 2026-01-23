"""
Session Check-in and Group Assignment Component - REGULAR SESSIONS ONLY

This component is for REGULAR SESSIONS with 4 attendance statuses:
Present, Absent, Late, Excused

For TOURNAMENT SESSIONS (2 statuses: Present/Absent only), use:
    streamlit_app/components/tournaments/instructor/tournament_checkin.py

Wizard flow:
Step 1: Session Selection & Booking List
Step 2: Attendance Roll Call (4 statuses)
Step 3: Group Creation
Step 4: Group Overview & Adjustments
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
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
    Render wizard-based session check-in interface for REGULAR SESSIONS.

    This function handles REGULAR sessions with 4 attendance statuses:
    Present, Absent, Late, Excused

    For TOURNAMENT sessions (2 statuses: Present/Absent), use:
        components.tournaments.instructor.tournament_checkin.render_tournament_checkin()

    Args:
        token: Authentication token
        user_id: Current user (instructor) ID
    """
    st.markdown("### ✅ Regular Session Check-in & Group Assignment")
    st.caption("Step-by-step wizard for marking attendance (4 statuses) and creating groups")

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
    render_wizard_progress(st.session_state.wizard_step)

    st.divider()

    # Route to current step
    if st.session_state.wizard_step == 1:
        render_step1_session_selection(token, user_id)
    elif st.session_state.wizard_step == 2:
        render_step2_attendance(token, user_id)
    elif st.session_state.wizard_step == 3:
        render_step3_group_creation(token, user_id)
    elif st.session_state.wizard_step == 4:
        render_step4_group_overview(token, user_id)


def render_wizard_progress(current_step: int):
    """Visual progress indicator showing current step"""
    steps = [
        {"num": 1, "icon": "📋", "label": "Select Session"},
        {"num": 2, "icon": "✅", "label": "Mark Attendance"},
        {"num": 3, "icon": "🎯", "label": "Create Groups"},
        {"num": 4, "icon": "📊", "label": "Review & Finish"}
    ]

    cols = st.columns(4)

    for i, step in enumerate(steps):
        with cols[i]:
            if step["num"] < current_step:
                # Completed step - green
                st.markdown(f"""
                <div style="text-align: center; padding: 10px; background: #d1fae5; border-radius: 8px; border: 2px solid #10b981;">
                    <div style="font-size: 24px;">✓</div>
                    <div style="font-size: 12px; color: #065f46; font-weight: 600;">{step['label']}</div>
                </div>
                """, unsafe_allow_html=True)
            elif step["num"] == current_step:
                # Current step - blue/orange
                st.markdown(f"""
                <div style="text-align: center; padding: 10px; background: #dbeafe; border-radius: 8px; border: 2px solid #3b82f6;">
                    <div style="font-size: 24px;">{step['icon']}</div>
                    <div style="font-size: 12px; color: #1e40af; font-weight: 600;">{step['label']}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Future step - gray
                st.markdown(f"""
                <div style="text-align: center; padding: 10px; background: #f3f4f6; border-radius: 8px; border: 2px solid #d1d5db;">
                    <div style="font-size: 24px; opacity: 0.4;">{step['icon']}</div>
                    <div style="font-size: 12px; color: #6b7280;">{step['label']}</div>
                </div>
                """, unsafe_allow_html=True)


def render_step1_session_selection(token: str, user_id: int):
    """STEP 1: Session Selection & Booking List"""
    st.markdown("### 📋 Step 1: Select Regular Session")
    st.caption("Choose a session and view registered students")

    # Get instructor's upcoming sessions
    with st.spinner("Loading your sessions..."):
        success, sessions = get_sessions(token, size=50, specialization_filter=False)

    if not success or not sessions:
        st.info("No sessions found. Sessions will appear here once they are scheduled.")
        return

    # Filter to instructor's sessions (EXCLUDE tournament sessions)
    my_sessions = [
        s for s in sessions
        if s.get('instructor_id') == user_id and not s.get('is_tournament_game', False)
    ]

    if not my_sessions:
        st.info("No sessions assigned to you as instructor.")
        return

    # Filter to upcoming and recent sessions (within 7 days)
    now = datetime.now()
    recent_sessions = []
    for session in my_sessions:
        try:
            start_time = datetime.fromisoformat(session.get('date_start', '').replace('Z', '+00:00'))
            if (now - timedelta(days=1)) <= start_time <= (now + timedelta(days=7)):
                recent_sessions.append(session)
        except:
            pass

    if not recent_sessions:
        st.info("No sessions in the next 7 days. Check back closer to session time.")
        return

    # Session selector
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

    # Display session details
    st.markdown("#### 📋 Session Details")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Session ID", session_id)
    with col2:
        st.metric("Type", selected_session.get('session_type', 'Unknown'))
    with col3:
        tournament_code = selected_session.get('tournament_code', 'N/A')
        st.metric("Tournament Code", tournament_code if tournament_code else 'N/A')

    st.divider()

    # Get bookings
    st.markdown("#### 👥 Registered Students")
    success, bookings = get_session_bookings(token, session_id)

    if not success or not bookings:
        st.warning("⚠️ No bookings for this session yet.")
        st.info("Students must book this session before you can mark attendance.")
        return

    # Display bookings table
    st.markdown(f"**Total Registered:** {len(bookings)} students")

    # Create table data
    table_data = []
    for booking in bookings:
        user = booking.get('user', {})
        table_data.append({
            "Name": user.get('name', 'Unknown'),
            "Email": user.get('email', 'N/A'),
            "Status": booking.get('status', 'N/A'),
            "Attendance": "Not checked in yet"
        })

    if table_data:
        st.dataframe(
            table_data,
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    # Start check-in button
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("▶️ Start Check-in Process", type="primary", use_container_width=True):
            st.session_state.selected_session_id = session_id
            st.session_state.selected_session = selected_session
            st.session_state.wizard_step = 2
            st.rerun()


def render_step2_attendance(token: str, user_id: int):
    """STEP 2: Attendance Roll Call"""
    st.markdown("### ✅ Step 2: Attendance Roll Call")
    st.caption("Mark which students are present at the session")

    session_id = st.session_state.selected_session_id
    selected_session = st.session_state.get('selected_session', {})

    # Detect if this is a tournament session
    is_tournament_session = selected_session.get('is_tournament_game', False)

    if not session_id:
        st.error("No session selected. Please go back to Step 1.")
        return

    # Get bookings
    success, bookings = get_session_bookings(token, session_id)

    if not success or not bookings:
        st.error("Failed to load bookings. Please try again.")
        return

    # Get existing attendance
    att_success, attendance_records = get_session_attendance(token, session_id)
    attendance_map = {}
    if att_success:
        for att in attendance_records:
            attendance_map[att.get('user_id')] = att.get('status', 'unknown')

    # Calculate summary stats
    present_count = sum(1 for s in attendance_map.values() if s == 'present')
    absent_count = sum(1 for s in attendance_map.values() if s == 'absent')
    late_count = sum(1 for s in attendance_map.values() if s == 'late')
    excused_count = sum(1 for s in attendance_map.values() if s == 'excused')
    pending_count = len(bookings) - len(attendance_map)

    # Live summary bar - Tournament: 2 statuses, Regular: 4 statuses
    st.markdown("#### 📊 Attendance Summary")

    if is_tournament_session:
        # TOURNAMENT: Only Present/Absent
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("✅ Present", present_count)
        with col2:
            st.metric("❌ Absent", absent_count)
        with col3:
            st.metric("⏳ Pending", pending_count)
    else:
        # REGULAR SESSION: All 4 statuses
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("✅ Present", present_count)
        with col2:
            st.metric("❌ Absent", absent_count)
        with col3:
            st.metric("⏰ Late", late_count)
        with col4:
            st.metric("🎫 Excused", excused_count)
        with col5:
            st.metric("⏳ Pending", pending_count)

    st.divider()

    # Display students with attendance controls
    st.markdown("#### 👥 Student Check-in")

    for booking in bookings:
        user = booking.get('user', {})
        user_id = user.get('id')
        user_name = user.get('name', 'Unknown Student')
        user_email = user.get('email', 'N/A')
        booking_id = booking.get('id')

        current_status = attendance_map.get(user_id, None)

        # Display student name with current status
        col1, col2 = st.columns([2, 3])

        with col1:
            if current_status == 'present':
                st.success(f"✅ **{user_name}**")
                st.caption(user_email)
            elif current_status == 'absent':
                st.error(f"❌ **{user_name}**")
                st.caption(user_email)
            elif current_status == 'late':
                st.warning(f"⏰ **{user_name}**")
                st.caption(user_email)
            else:
                st.info(f"⏳ **{user_name}**")
                st.caption(user_email)

        with col2:
            if is_tournament_session:
                # TOURNAMENT: Only 2 buttons (Present/Absent)
                btn_col1, btn_col2 = st.columns(2)

                with btn_col1:
                    if st.button("✅ Present", key=f"present_booking_{booking_id}", use_container_width=True,
                                type="primary" if current_status == 'present' else "secondary"):
                        success, msg = mark_student_attendance(token, session_id, user_id, "present", booking_id)
                        if success:
                            st.rerun()
                        else:
                            st.error(f"Error: {msg}")

                with btn_col2:
                    if st.button("❌ Absent", key=f"absent_booking_{booking_id}", use_container_width=True,
                                type="primary" if current_status == 'absent' else "secondary"):
                        success, msg = mark_student_attendance(token, session_id, user_id, "absent", booking_id)
                        if success:
                            st.rerun()
                        else:
                            st.error(f"Error: {msg}")
            else:
                # REGULAR SESSION: Show all 4 attendance buttons
                btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)

                with btn_col1:
                    if st.button("✅ Present", key=f"present_booking_{booking_id}", use_container_width=True,
                                type="primary" if current_status == 'present' else "secondary"):
                        success, msg = mark_student_attendance(token, session_id, user_id, "present", booking_id)
                        if success:
                            st.rerun()
                        else:
                            st.error(f"Error: {msg}")

                with btn_col2:
                    if st.button("❌ Absent", key=f"absent_booking_{booking_id}", use_container_width=True,
                                type="primary" if current_status == 'absent' else "secondary"):
                        success, msg = mark_student_attendance(token, session_id, user_id, "absent", booking_id)
                        if success:
                            st.rerun()
                        else:
                            st.error(f"Error: {msg}")

                with btn_col3:
                    if st.button("⏰ Late", key=f"late_booking_{booking_id}", use_container_width=True,
                                type="primary" if current_status == 'late' else "secondary"):
                        success, msg = mark_student_attendance(token, session_id, user_id, "late", booking_id)
                        if success:
                            st.rerun()
                        else:
                            st.error(f"Error: {msg}")

                with btn_col4:
                    if st.button("🎫 Excused", key=f"excused_booking_{booking_id}", use_container_width=True,
                                type="primary" if current_status == 'excused' else "secondary"):
                        success, msg = mark_student_attendance(token, session_id, user_id, "excused", booking_id)
                        if success:
                            st.rerun()
                        else:
                            st.error(f"Error: {msg}")

        st.divider()

    # Navigation buttons
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("⬅️ Back to Session Selection", use_container_width=True):
            st.session_state.wizard_step = 1
            st.rerun()

    with col3:
        # Validation: at least 1 student marked present
        can_proceed = present_count > 0

        if can_proceed:
            if st.button("Next: Create Groups ➡️", type="primary", use_container_width=True):
                st.session_state.wizard_step = 3
                st.rerun()
        else:
            st.button("Next: Create Groups ➡️", use_container_width=True, disabled=True)
            st.caption("⚠️ Mark at least 1 student as present to continue")

    # Warning if students unmarked
    if pending_count > 0:
        st.warning(f"⚠️ {pending_count} students not checked in yet.")


def render_step3_group_creation(token: str, user_id: int):
    """STEP 3: Group Creation"""
    st.markdown("### 🎯 Step 3: Create Groups")
    st.caption("Auto-assign students to balanced groups")

    session_id = st.session_state.selected_session_id
    if not session_id:
        st.error("No session selected. Please go back to Step 1.")
        return

    # Get attendance summary
    att_success, attendance_records = get_session_attendance(token, session_id)

    if not att_success or not attendance_records:
        st.error("No attendance records found. Please go back to Step 2.")
        return

    present_students = [a for a in attendance_records if a.get('status') == 'present']
    absent_students = [a for a in attendance_records if a.get('status') == 'absent']

    # Attendance summary box
    st.markdown("#### 📊 Attendance Summary")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("✅ Students Present", len(present_students))
    with col2:
        st.metric("❌ Students Absent", len(absent_students))

    if len(present_students) == 0:
        st.warning("⚠️ No students marked as present. Cannot create groups.")
        st.markdown("---")
        if st.button("⬅️ Back to Attendance", use_container_width=True):
            st.session_state.wizard_step = 2
            st.rerun()
        return

    st.success(f"✅ Ready to assign {len(present_students)} students to groups")

    st.divider()

    # Check if groups already exist
    success, existing_groups = get_session_groups(token, session_id)

    if success and existing_groups and existing_groups.get('groups'):
        st.warning("⚠️ Groups already exist for this session!")
        st.markdown("You can:")
        st.markdown("- **Skip to Step 4** to review existing groups")
        st.markdown("- **Delete and re-assign** below")

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🗑️ Delete Groups & Reassign", type="secondary", use_container_width=True):
                delete_success, delete_msg = delete_session_groups(token, session_id)
                if delete_success:
                    st.success("✅ Groups deleted. You can now re-assign.")
                    st.session_state.groups_created = False
                    st.rerun()
                else:
                    st.error(f"Error: {delete_msg}")

        with col2:
            if st.button("Skip to Review ➡️", type="primary", use_container_width=True):
                st.session_state.groups_created = True
                st.session_state.wizard_step = 4
                st.rerun()

        st.markdown("---")
        if st.button("⬅️ Back to Attendance"):
            st.session_state.wizard_step = 2
            st.rerun()

        return

    # Group configuration info
    st.markdown("#### ⚙️ Auto-Assign Algorithm")
    st.markdown("- Distributes **PRESENT** students evenly across available instructors")
    st.markdown("- Each instructor gets a balanced group")
    st.markdown("- Example: 6 students + 2 instructors = 2 groups of 3")

    st.divider()

    # Auto-assign button
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
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

                st.session_state.groups_created = True

                # Auto-advance to Step 4 after 2 seconds
                time.sleep(2)
                st.info("➡️ Advancing to Group Overview...")
                time.sleep(1)
                st.session_state.wizard_step = 4
                st.rerun()
            else:
                st.error(f"❌ Failed to create groups: {msg}")

    # Navigation
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("⬅️ Back to Attendance", use_container_width=True):
            st.session_state.wizard_step = 2
            st.rerun()

    with col2:
        if st.session_state.groups_created:
            if st.button("Next: Review Groups ➡️", type="primary", use_container_width=True):
                st.session_state.wizard_step = 4
                st.rerun()


def render_step4_group_overview(token: str, user_id: int):
    """STEP 4: Group Overview & Adjustments"""
    st.markdown("### 📊 Step 4: Group Overview & Adjustments")
    st.caption("Review groups and make manual adjustments if needed")

    session_id = st.session_state.selected_session_id
    if not session_id:
        st.error("No session selected. Please go back to Step 1.")
        return

    # Get groups
    success, group_data = get_session_groups(token, session_id)

    if not success or not group_data or not group_data.get('groups'):
        st.warning("⚠️ No groups created yet.")
        st.info("Go back to Step 3 to create groups.")

        st.markdown("---")
        if st.button("⬅️ Back to Group Creation", use_container_width=True):
            st.session_state.wizard_step = 3
            st.rerun()
        return

    groups = group_data.get('groups', [])
    total_students = group_data.get('total_students', 0)
    total_instructors = group_data.get('total_instructors', 0)

    # Summary metrics
    st.markdown("#### 📈 Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👥 Total Students", total_students)
    with col2:
        st.metric("👨‍🏫 Instructors", total_instructors)
    with col3:
        st.metric("🎯 Groups Created", len(groups))

    st.divider()

    # Display groups
    st.markdown("#### 👥 Group Assignments")

    for group in groups:
        group_num = group.get('group_number')
        instructor_name = group.get('instructor_name', 'Unknown')
        student_count = group.get('student_count', 0)
        students = group.get('students', [])

        with st.expander(f"**Group {group_num}** - {instructor_name} ({student_count} students)", expanded=True):
            if students:
                for student in students:
                    st.markdown(f"• {student}")
            else:
                st.caption("No students in this group")

    st.divider()

    # Manual adjustment
    st.markdown("#### ✏️ Manual Adjustments (Optional)")
    st.caption("Move students between groups if needed")

    # Student selector
    all_students = []
    for group in groups:
        for student_name, student_id in zip(group.get('students', []), group.get('student_ids', [])):
            all_students.append({
                'name': student_name,
                'id': student_id,
                'current_group': group.get('group_number'),
                'group_id': group.get('group_number')
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
                st.info("Manual move feature coming soon!")

    st.divider()

    # Final action buttons
    st.markdown("#### ✅ Finish Check-in")

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("⬅️ Back to Group Creation", use_container_width=True):
            st.session_state.wizard_step = 3
            st.rerun()

    with col2:
        if st.button("🗑️ Delete All Groups", type="secondary", use_container_width=True):
            success, msg = delete_session_groups(token, session_id)
            if success:
                st.success("Groups deleted successfully")
                st.session_state.groups_created = False
                st.rerun()
            else:
                st.error(f"Error: {msg}")

    with col3:
        if st.button("✅ Finish Check-in", type="primary", use_container_width=True):
            # Reset wizard state
            st.session_state.wizard_step = 1
            st.session_state.selected_session_id = None
            st.session_state.selected_session = None
            st.session_state.attendance_marked = {}
            st.session_state.groups_created = False

            st.success("✅ Tournament check-in completed successfully!")
            st.balloons()
            time.sleep(2)
            st.rerun()
