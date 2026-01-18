"""
Tournament Application Components for Instructor Dashboard

Provides UI for instructors to:
1. Browse open tournaments (SEEKING_INSTRUCTOR status)
2. Apply to tournaments
3. View their application history
4. Accept approved assignments
"""

import streamlit as st
import requests
from typing import Dict
from config import API_BASE_URL, API_TIMEOUT
from components.instructor.tournament_helpers import (
    get_instructor_coach_level,
    check_coach_level_sufficient,
    batch_get_application_statuses,
    get_open_tournaments,
    get_my_applications
)
from components.instructor.tournament_table_view import render_table_view
from components.instructor.tournament_kanban_view import render_kanban_view
from components.instructor.tournament_application_forms import (
    render_system_message_card,
    render_my_tournament_card,
    render_direct_messages_placeholder,
    show_apply_dialog
)

def render_open_tournaments_tab(token: str, user: Dict):
    """
    Render the "Open Tournaments" tab showing SEEKING_INSTRUCTOR tournaments.
    """
    st.markdown("### 🔍 Open Tournaments")
    st.caption("Browse and apply to tournaments seeking instructors")

    # Check if user has LFA_COACH license and get coach level
    has_coach_license = False
    coach_level = 0
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/licenses/user/{user.get('id')}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            licenses = response.json()  # API returns a list directly, not {"licenses": [...]}
            if isinstance(licenses, dict):
                licenses = licenses.get('licenses', [])

            # Find LFA_COACH license and get level
            coach_license = next(
                (lic for lic in licenses if lic.get('specialization_type') == 'LFA_COACH' and lic.get('is_active', True)),
                None
            )
            if coach_license:
                has_coach_license = True
                coach_level = coach_license.get('current_level', 0)
    except:
        pass

    if not has_coach_license:
        st.warning("⚠️ **LFA_COACH License Required**")
        st.info("You need an active LFA_COACH license to apply for tournament instructor positions. Contact admin to obtain this license.")
        return

    # Fetch open tournaments
    with st.spinner("Loading open tournaments..."):
        open_tournaments = get_open_tournaments(token)

    if not open_tournaments:
        st.info("📭 No open tournaments currently seeking instructors")
        st.caption("Check back later for new opportunities")
        return

    # Store coach level in session state for use in rendering (show all, but disable apply for unqualified)
    st.session_state['instructor_coach_level'] = coach_level

    # OPTIMIZATION: Batch fetch application statuses for all tournaments upfront
    tournament_ids = [t.get('id') for t in open_tournaments]

    # 🔥 FIX: Only fetch if cache doesn't exist OR if cache was explicitly cleared
    if 'tournament_application_statuses' not in st.session_state:
        application_statuses = batch_get_application_statuses(token, tournament_ids)
        st.session_state['tournament_application_statuses'] = application_statuses
    else:
        # Use cached data
        application_statuses = st.session_state['tournament_application_statuses']

    # Initialize view preference in session state
    if 'tournament_view_mode' not in st.session_state:
        st.session_state['tournament_view_mode'] = 'table'  # Default to table view

    st.success(f"✅ Found {len(open_tournaments)} tournament(s) seeking instructors")

    # View toggle button
    col_toggle1, col_toggle2, col_toggle3 = st.columns([1, 1, 4])
    with col_toggle1:
        if st.button("📊 Table View",
                     use_container_width=True,
                     type="primary" if st.session_state['tournament_view_mode'] == 'table' else "secondary"):
            st.session_state['tournament_view_mode'] = 'table'
            st.rerun()

    with col_toggle2:
        if st.button("📋 Kanban View",
                     use_container_width=True,
                     type="primary" if st.session_state['tournament_view_mode'] == 'kanban' else "secondary"):
            st.session_state['tournament_view_mode'] = 'kanban'
            st.rerun()

    st.divider()

    # Render based on selected view mode
    if st.session_state['tournament_view_mode'] == 'table':
        render_table_view(token, open_tournaments, application_statuses)
    else:
        render_kanban_view(token, open_tournaments, application_statuses)

    # 🔥 FIX: Show apply dialog if triggered (works for both Table and Kanban views)
    if st.session_state.get('show_apply_dialog'):
        show_apply_dialog(token)



def render_my_applications_tab(token: str, user: Dict):
    """
    Render the "Inbox" tab - Universal messaging system for assignments, invitations, and direct messages.

    Phase 1: System Messages only (tournament/semester assignments)
    Future: Direct messaging between users
    """
    st.markdown("### 📬 Inbox")
    st.caption("Your messages, invitations, and assignments")

    # Tab structure: System Messages | Direct Messages (Coming Soon)
    inbox_tab1, inbox_tab2 = st.tabs(["🔔 System Messages", "💬 Direct Messages (Coming Soon)"])

    with inbox_tab1:
        render_system_messages_tab(token, user)

    with inbox_tab2:
        render_direct_messages_placeholder()



def render_system_messages_tab(token: str, user: Dict):
    """
    Render System Messages tab - Tournament/Semester assignments and invitations.
    """
    st.markdown("#### 🔔 System Messages")
    st.caption("Tournament invitations, assignment requests, and system notifications")

    # Fetch instructor's applications (these are system messages)
    with st.spinner("Loading your messages..."):
        applications = get_my_applications(token)

    if not applications:
        st.info("📭 No system messages")
        st.caption("Visit the 'Open Tournaments' tab to browse available opportunities")
        return

    # Separate by status
    pending = [a for a in applications if a.get('status') == 'PENDING']
    accepted = [a for a in applications if a.get('status') == 'ACCEPTED']
    declined = [a for a in applications if a.get('status') in ['DECLINED', 'CANCELLED', 'EXPIRED']]

    # Remove duplicate applications by ID (just in case)
    seen_ids = set()
    accepted_unique = []
    for app in accepted:
        app_id = app.get('id')
        if app_id not in seen_ids:
            seen_ids.add(app_id)
            accepted_unique.append(app)
    accepted = accepted_unique

    # Show stats
    stats_col1, stats_col2, stats_col3 = st.columns(3)

    with stats_col1:
        st.metric("🤝 Pending", len(pending))
    with stats_col2:
        st.metric("⏳ Action Required", len(accepted))
    with stats_col3:
        st.metric("📋 Archived", len(declined))

    st.divider()

    # PENDING applications
    if pending:
        st.markdown("##### 🤝 PENDING")
        st.caption("Waiting for admin review")
        for app in pending:
            render_system_message_card(token, app, "PENDING")
        st.divider()

    # ACCEPTED applications (need instructor to accept assignment)
    if accepted:
        st.markdown("##### ⏳ ACTION REQUIRED")
        st.warning("⚠️ These invitations/applications have been approved. Please accept to confirm your assignment!")
        for app in accepted:
            render_system_message_card(token, app, "ACCEPTED")
        st.divider()

    # DECLINED/CANCELLED/EXPIRED applications
    if declined:
        with st.expander(f"📋 Archived Messages ({len(declined)})", expanded=False):
            for app in declined:
                render_system_message_card(token, app, "DECLINED")



def render_direct_messages_placeholder():
    """
    Placeholder for Direct Messages feature (Phase 2).
    """
    st.markdown("#### 💬 Direct Messages")
    st.info("🚧 **Coming Soon!**")
    st.markdown("""
    Direct messaging will allow you to:
    - 📤 Send messages to other instructors
    - 📧 Communicate with admins
    - 💬 Participate in group conversations
    - 🎯 Discuss tournament/semester-specific topics

    This feature is currently under development.
    """)



def render_my_tournaments_tab(token: str, user: Dict):
    """
    Render the "My Tournaments" tab showing tournaments where instructor is assigned.
    """
    st.markdown("### 🏆 My Tournaments")
    st.caption("Tournaments where you are the assigned instructor")

    # Fetch all semesters
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/semesters",
            headers={"Authorization": f"Bearer {token}"},
            params={"size": 100},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            all_semesters = response.json().get('items', [])

            # Filter for tournaments where current user is master instructor
            my_tournaments = [
                t for t in all_semesters
                if t.get('code', '').startswith('TOURN-') and t.get('master_instructor_id') == user.get('id')
            ]

            if not my_tournaments:
                st.info("📭 You are not currently assigned to any tournaments")
                st.caption("Apply to tournaments in the 'Open Tournaments' tab")
                return

            # Separate by status
            upcoming = [t for t in my_tournaments if t.get('status') in ['READY_FOR_ENROLLMENT', 'ENROLLING']]
            ongoing = [t for t in my_tournaments if t.get('status') == 'ONGOING']
            completed = [t for t in my_tournaments if t.get('status') == 'COMPLETED']

            # Stats
            stats_col1, stats_col2, stats_col3 = st.columns(3)

            with stats_col1:
                st.metric("🔜 Upcoming", len(upcoming))
            with stats_col2:
                st.metric("🔴 Ongoing", len(ongoing))
            with stats_col3:
                st.metric("✅ Completed", len(completed))

            st.divider()

            # Display tournaments
            all_tournaments_display = upcoming + ongoing + completed

            for tournament in all_tournaments_display:
                render_my_tournament_card(token, tournament)

        else:
            st.error("Failed to load tournaments")
    except Exception as e:
        st.error(f"Error: {str(e)}")


