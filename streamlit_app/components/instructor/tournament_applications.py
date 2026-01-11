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
import time
from typing import Dict, List, Any
from datetime import datetime
from config import API_BASE_URL, API_TIMEOUT


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_open_tournaments(token: str) -> List[Dict]:
    """
    Fetch tournaments with SEEKING_INSTRUCTOR status.

    Returns:
        List of tournament dictionaries
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/semesters",
            headers={"Authorization": f"Bearer {token}"},
            params={"size": 100},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            # API returns {"semesters": [...]} format
            all_semesters = data.get('semesters', data.get('items', []))

            # Filter for tournaments with SEEKING_INSTRUCTOR status
            open_tournaments = [
                t for t in all_semesters
                if t.get('code', '').startswith('TOURN-') and t.get('status') == 'SEEKING_INSTRUCTOR'
            ]

            return open_tournaments
        else:
            return []
    except Exception as e:
        st.error(f"Error fetching tournaments: {str(e)}")
        return []


def get_my_applications(token: str) -> List[Dict]:
    """
    Fetch instructor's own tournament applications.

    Returns:
        List of application dictionaries with tournament details
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/tournaments/instructor/my-applications",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            return data.get('applications', [])
        else:
            return []
    except Exception as e:
        # Endpoint might not exist yet - return empty list
        return []


def apply_to_tournament(token: str, tournament_id: int, message: str) -> bool:
    """
    Submit an application to a tournament.

    Returns:
        True if successful, False otherwise
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/instructor-applications",
            headers={"Authorization": f"Bearer {token}"},
            json={"application_message": message},
            timeout=API_TIMEOUT
        )

        response.raise_for_status()
        return True
    except requests.exceptions.HTTPError as e:
        error_data = e.response.json() if e.response else {}
        error_message = error_data.get('error', {}).get('message', {})

        if error_message.get('error') == 'duplicate_application':
            st.error("⚠️ You have already applied to this tournament")
        elif error_message.get('error') == 'missing_coach_license':
            st.error("⚠️ You need an active LFA_COACH license to apply")
        else:
            st.error(f"Application failed: {str(e)}")
        return False
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        return False


def accept_assignment(token: str, tournament_id: int) -> bool:
    """
    Accept an approved instructor assignment.

    Returns:
        True if successful, False otherwise
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/instructor/accept",
            headers={"Authorization": f"Bearer {token}"},
            json={},  # Empty request body required by endpoint
            timeout=API_TIMEOUT
        )

        response.raise_for_status()
        return True
    except requests.exceptions.HTTPError as e:
        error_data = e.response.json() if e.response else {}
        st.error(f"Failed to accept assignment: {error_data.get('detail', str(e))}")
        return False
    except Exception as e:
        st.error(f"Accept error: {str(e)}")
        return False


# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_open_tournaments_tab(token: str, user: Dict):
    """
    Render the "Open Tournaments" tab showing SEEKING_INSTRUCTOR tournaments.
    """
    st.markdown("### 🔍 Open Tournaments")
    st.caption("Browse and apply to tournaments seeking instructors")

    # Check if user has LFA_COACH license
    has_coach_license = False
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
            has_coach_license = any(
                lic.get('specialization_type') == 'LFA_COACH' and lic.get('is_active', True)
                for lic in licenses
            )
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

    st.success(f"✅ Found {len(open_tournaments)} tournament(s) seeking instructors")
    st.divider()

    # Display each tournament
    for tournament in open_tournaments:
        render_tournament_card(token, tournament)


def render_tournament_card(token: str, tournament: Dict):
    """Render a single tournament card with apply button"""

    tournament_id = tournament.get('id')
    name = tournament.get('name', 'Unnamed Tournament')
    start_date = tournament.get('start_date', 'TBD')
    age_group = tournament.get('specialization_type', 'UNKNOWN').replace('LFA_PLAYER_', '')
    status = tournament.get('status', 'N/A')

    # Age group icon
    age_icons = {'PRE': '👶', 'YOUTH': '👦', 'AMATEUR': '🧑', 'PRO': '👨'}
    age_icon = age_icons.get(age_group, '❓')

    with st.expander(f"🏆 {name}", expanded=False):
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"**Tournament:** {name}")
            st.caption(f"📅 **Date:** {start_date}")
            st.caption(f"🎯 **Age Group:** {age_icon} {age_group}")
            st.caption(f"📊 **Status:** {status}")

            # Get tournament sessions count if available
            try:
                sessions_response = requests.get(
                    f"{API_BASE_URL}/api/v1/sessions",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"semester_id": tournament_id, "size": 100},
                    timeout=API_TIMEOUT
                )
                if sessions_response.status_code == 200:
                    sessions = sessions_response.json().get('items', [])
                    st.caption(f"📋 **Sessions:** {len(sessions)}")
            except:
                pass

        with col2:
            # Apply button
            if st.button(f"📝 Apply", key=f"apply_{tournament_id}", use_container_width=True, type="primary"):
                st.session_state['apply_tournament_id'] = tournament_id
                st.session_state['apply_tournament_name'] = name
                st.session_state['show_apply_dialog'] = True
                st.rerun()

        st.divider()

    # Show apply dialog if triggered
    if st.session_state.get('show_apply_dialog') and st.session_state.get('apply_tournament_id') == tournament_id:
        show_apply_dialog(token)


@st.dialog("📝 Apply to Tournament")
def show_apply_dialog(token: str):
    """Dialog for submitting tournament application"""

    tournament_id = st.session_state.get('apply_tournament_id')
    tournament_name = st.session_state.get('apply_tournament_name', 'Unknown')

    st.markdown(f"**Applying to:** {tournament_name}")
    st.caption(f"Tournament ID: {tournament_id}")
    st.divider()

    # Application message
    application_message = st.text_area(
        "Application Message",
        value="I am interested in leading this tournament as the master instructor.",
        height=150,
        key="application_message_input"
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Submit Application", use_container_width=True, type="primary"):
            if not application_message.strip():
                st.error("⚠️ Please provide an application message")
            else:
                if apply_to_tournament(token, tournament_id, application_message):
                    st.success("✅ Application submitted successfully!")
                    st.info("ℹ️ Admin will review your application. Check the 'My Applications' tab for status updates.")
                    time.sleep(2)
                    # Clear dialog state
                    st.session_state['show_apply_dialog'] = False
                    st.rerun()

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state['show_apply_dialog'] = False
            st.rerun()


def render_my_applications_tab(token: str, user: Dict):
    """
    Render the "My Applications" tab showing instructor's application history.
    """
    st.markdown("### 📋 My Applications")
    st.caption("View your tournament application history and status")

    # Fetch instructor's applications
    with st.spinner("Loading your applications..."):
        applications = get_my_applications(token)

    if not applications:
        st.info("📭 You haven't applied to any tournaments yet")
        st.caption("Visit the 'Open Tournaments' tab to browse available opportunities")
        return

    # Separate by status
    pending = [a for a in applications if a.get('status') == 'PENDING']
    accepted = [a for a in applications if a.get('status') == 'ACCEPTED']
    declined = [a for a in applications if a.get('status') in ['DECLINED', 'CANCELLED', 'EXPIRED']]

    # Show stats
    stats_col1, stats_col2, stats_col3 = st.columns(3)

    with stats_col1:
        st.metric("⏳ Pending", len(pending))
    with stats_col2:
        st.metric("✅ Accepted", len(accepted))
    with stats_col3:
        st.metric("❌ Declined", len(declined))

    st.divider()

    # PENDING applications
    if pending:
        st.markdown("### ⏳ PENDING Applications")
        for app in pending:
            render_application_card(token, app, "PENDING")
        st.divider()

    # ACCEPTED applications (need instructor to accept assignment)
    if accepted:
        st.markdown("### ✅ ACCEPTED Applications (Action Required)")
        st.warning("⚠️ These applications have been approved by admin. Accept the assignment to activate your instructor role!")
        for app in accepted:
            render_application_card(token, app, "ACCEPTED")
        st.divider()

    # DECLINED/CANCELLED/EXPIRED applications
    if declined:
        with st.expander(f"❌ Declined/Cancelled ({len(declined)})", expanded=False):
            for app in declined:
                render_application_card(token, app, "DECLINED")


def render_application_card(token: str, application: Dict, status_category: str):
    """Render a single application card"""

    app_id = application.get('id')
    tournament_id = application.get('tournament_id')
    tournament_name = application.get('tournament_name', 'Unknown Tournament')
    status = application.get('status')
    tournament_status = application.get('tournament_status')  # NEW: Get tournament status
    created_at = application.get('created_at')
    application_message = application.get('application_message', 'N/A')
    response_message = application.get('response_message')
    responded_at = application.get('responded_at')

    # Format dates
    try:
        created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
    except:
        created_date = 'N/A'

    # Status badge styling - USE TOURNAMENT STATUS for more accurate state
    # Application status "ACCEPTED" means admin approved, but tournament may still need instructor acceptance
    if status == 'PENDING':
        badge_color = '#FFF3E0'
        badge_text_color = '#E65100'
        badge_icon = '⏳'
        display_status = 'PENDING'
    elif status == 'ACCEPTED' and tournament_status == 'PENDING_INSTRUCTOR_ACCEPTANCE':
        # Admin approved, but instructor needs to accept
        badge_color = '#FFF3E0'
        badge_text_color = '#F57C00'
        badge_icon = '⏳'
        display_status = 'ACTION REQUIRED'
    elif status == 'ACCEPTED':
        # Fully accepted (instructor confirmed)
        badge_color = '#E8F5E9'
        badge_text_color = '#2E7D32'
        badge_icon = '✅'
        display_status = 'CONFIRMED'
    else:
        badge_color = '#FFEBEE'
        badge_text_color = '#C62828'
        badge_icon = '❌'
        display_status = status

    with st.container():
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"**🏆 {tournament_name}**")
            st.caption(f"📝 **Applied:** {created_date}")
            st.caption(f"💬 **Your message:** {application_message}")

            if response_message:
                st.caption(f"📧 **Admin response:** {response_message}")
                if responded_at:
                    try:
                        response_date = datetime.fromisoformat(responded_at.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
                        st.caption(f"📅 **Responded:** {response_date}")
                    except:
                        pass

        with col2:
            # Status badge - using display_status instead of raw status
            st.markdown(
                f"<div style='text-align: center; padding: 10px; background-color: {badge_color}; "
                f"border-radius: 5px; font-weight: bold; color: {badge_text_color};'>"
                f"{badge_icon} {display_status}</div>",
                unsafe_allow_html=True
            )

            # Accept button for ACCEPTED applications that need instructor action
            if status == 'ACCEPTED' and tournament_status == 'PENDING_INSTRUCTOR_ACCEPTANCE':
                if st.button(f"✅ Accept Assignment", key=f"accept_{app_id}", use_container_width=True, type="primary"):
                    if accept_assignment(token, tournament_id):
                        st.success("✅ Assignment accepted successfully!")
                        st.info("🎉 You are now the master instructor for this tournament!")
                        time.sleep(3)  # Give time for success message to be visible
                        st.rerun()

        st.divider()


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


def render_my_tournament_card(token: str, tournament: Dict):
    """Render tournament card for instructor's assigned tournaments"""

    name = tournament.get('name', 'Unnamed Tournament')
    start_date = tournament.get('start_date', 'TBD')
    status = tournament.get('status', 'N/A')
    tournament_id = tournament.get('id')
    age_group = tournament.get('specialization_type', 'UNKNOWN').replace('LFA_PLAYER_', '')

    # Age group icon
    age_icons = {'PRE': '👶', 'YOUTH': '👦', 'AMATEUR': '🧑', 'PRO': '👨'}
    age_icon = age_icons.get(age_group, '❓')

    # Status styling
    if status in ['READY_FOR_ENROLLMENT', 'ENROLLING']:
        status_color = '#E3F2FD'
        status_text = '#1565C0'
        status_icon = '🔜'
    elif status == 'ONGOING':
        status_color = '#D4EDDA'
        status_text = '#155724'
        status_icon = '🔴'
    else:
        status_color = '#E8E8E8'
        status_text = '#616161'
        status_icon = '✅'

    with st.expander(f"🏆 {name}", expanded=(status == 'ONGOING')):
        col1, col2 = st.columns([3, 1])

        with col1:
            st.caption(f"📅 **Date:** {start_date}")
            st.caption(f"🎯 **Age Group:** {age_icon} {age_group}")
            st.caption(f"📊 **Status:** {status}")

            # Get enrollment count
            try:
                enroll_response = requests.get(
                    f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/enrollments",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=API_TIMEOUT
                )
                if enroll_response.status_code == 200:
                    enrollments = enroll_response.json().get('enrollments', [])
                    st.caption(f"👥 **Enrolled Players:** {len(enrollments)}")
            except:
                pass

        with col2:
            st.markdown(
                f"<div style='text-align: center; padding: 10px; background-color: {status_color}; "
                f"border-radius: 5px; font-weight: bold; color: {status_text};'>"
                f"{status_icon} {status}</div>",
                unsafe_allow_html=True
            )

        st.divider()
