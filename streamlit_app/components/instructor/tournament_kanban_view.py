"""
Tournament Kanban View - Kanban board rendering for instructor tournaments
"""

import streamlit as st
from typing import Dict, List
from config import API_BASE_URL
from components.instructor.tournament_helpers import check_coach_level_sufficient, get_instructor_coach_level

def render_kanban_view(token: str, tournaments: List[Dict], application_statuses: Dict[int, Dict]):
    """
    Render tournaments in a Kanban board layout grouped by application status.
    Mobile-responsive: Columns stack vertically on narrow screens.

    Args:
        token: Authentication token
        tournaments: List of tournament dictionaries
        application_statuses: Dict mapping tournament_id -> application data
    """
    # 🔥 GET INSTRUCTOR COACH LEVEL (fetch fresh each time to avoid stale cache)
    instructor_coach_level = get_instructor_coach_level(token)

    # Group tournaments by application status
    not_applied = []
    pending = []
    accepted = []
    declined = []

    for tournament in tournaments:
        tournament_id = tournament.get('id')
        application_data = application_statuses.get(tournament_id)

        if application_data:
            status = application_data.get('status', 'PENDING')
            if status == 'PENDING':
                pending.append((tournament, application_data))
            elif status == 'ACCEPTED':
                accepted.append((tournament, application_data))
            else:
                declined.append((tournament, application_data))
        else:
            not_applied.append((tournament, None))

    # Mobile-friendly: Use tabs for narrow screens, columns for wide screens
    # Streamlit automatically makes columns responsive
    st.info("💡 **Kanban View** - Tournaments organized by your application status")

    # Create 4 columns for Kanban board (automatically stacks on mobile)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        with st.container():
            st.markdown("### 📋 Not Applied")
            st.caption(f"{len(not_applied)} tournaments")
            st.divider()

            if not_applied:
                # Limit to 5 visible cards, rest collapsed
                for idx, (tournament, app_data) in enumerate(not_applied[:5]):
                    render_kanban_card(token, tournament, app_data, "NOT_APPLIED", instructor_coach_level)

                if len(not_applied) > 5:
                    with st.expander(f"➕ Show {len(not_applied) - 5} more", expanded=False):
                        for tournament, app_data in not_applied[5:]:
                            render_kanban_card(token, tournament, app_data, "NOT_APPLIED", instructor_coach_level)
            else:
                st.caption("No tournaments")

    with col2:
        with st.container():
            st.markdown("### 🟡 Pending")
            st.caption(f"{len(pending)} applications")
            st.divider()

            if pending:
                for tournament, app_data in pending:
                    render_kanban_card(token, tournament, app_data, "PENDING", instructor_coach_level)
            else:
                st.caption("No applications")

    with col3:
        with st.container():
            st.markdown("### ✅ Accepted")
            st.caption(f"{len(accepted)} applications")
            st.divider()

            if accepted:
                for tournament, app_data in accepted:
                    render_kanban_card(token, tournament, app_data, "ACCEPTED", instructor_coach_level)
            else:
                st.caption("No applications")

    with col4:
        with st.container():
            st.markdown("### ❌ Declined")
            st.caption(f"{len(declined)} applications")
            st.divider()

            if declined:
                for tournament, app_data in declined:
                    render_kanban_card(token, tournament, app_data, "DECLINED", instructor_coach_level)
            else:
                st.caption("No applications")


def render_kanban_card(token: str, tournament: Dict, application_data: Dict, column_status: str, instructor_coach_level: int):
    """Render a compact card for Kanban view"""
    tournament_id = tournament.get('id')
    name = tournament.get('name', 'Unnamed')
    start_date = tournament.get('start_date', 'TBD')
    age_group = tournament.get('age_group', 'UNKNOWN')
    assignment_type = tournament.get('assignment_type', 'UNKNOWN')
    tournament_category = age_group  # Use age_group for coach level check

    # Format date
    try:
        date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        date_display = date_obj.strftime('%Y-%m-%d')
    except:
        date_display = start_date

    # Age group icon
    age_icons = {'PRE': '👶', 'YOUTH': '👦', 'AMATEUR': '🧑', 'PRO': '👨'}
    age_icon = age_icons.get(age_group, '❓')

    # Assignment type icon
    assignment_icon = '📝' if assignment_type == 'APPLICATION_BASED' else '🔒'

    # 🔥 CHECK COACH LEVEL
    has_sufficient_level = check_coach_level_sufficient(instructor_coach_level, tournament_category)

    with st.container():
        st.markdown(f"**🏆 {name}**")
        st.caption(f"📅 {date_display}")
        st.caption(f"{age_icon} {age_group}")
        st.caption(f"{assignment_icon} {assignment_type}")

        st.divider()

        # Action button based on status
        if column_status == "NOT_APPLIED":
            if assignment_type == 'APPLICATION_BASED':
                if has_sufficient_level:
                    if st.button("📝 Apply", key=f"kanban_apply_{tournament_id}", use_container_width=True, type="primary"):
                        st.session_state['apply_tournament_id'] = tournament_id
                        st.session_state['apply_tournament_name'] = name
                        st.session_state['show_apply_dialog'] = True
                        st.rerun()
                else:
                    # Show required level
                    required_levels = {"PRE": 1, "YOUTH": 3, "AMATEUR": 5, "PRO": 7}
                    required_level = required_levels.get(age_group, 1)
                    st.caption(f"🔒 Level {required_level}+ Required")
            else:
                st.caption("🔒 Invite Only")
        else:
            if st.button("📋 View", key=f"kanban_view_{tournament_id}", use_container_width=True):
                st.info("Application details shown in 'Inbox' tab")

        st.markdown("---")


def render_tournament_card(token: str, tournament: Dict, application_data: Dict = None):
    """
    Render a single tournament card with apply button.

    Args:
        token: Authentication token
        tournament: Tournament data dictionary
        application_data: Preloaded application data (None if not applied)
    """

    tournament_id = tournament.get('id')
    name = tournament.get('name', 'Unnamed Tournament')
    start_date = tournament.get('start_date', 'TBD')
    age_group = tournament.get('age_group', 'UNKNOWN')
    status = tournament.get('status', 'N/A')
    assignment_type = tournament.get('assignment_type', 'UNKNOWN')

    # Age group icon
    age_icons = {'PRE': '👶', 'YOUTH': '👦', 'AMATEUR': '🧑', 'PRO': '👨'}
    age_icon = age_icons.get(age_group, '❓')

    # Use preloaded application data (no API call needed)
    has_applied = application_data is not None
    application_status = application_data.get('status', 'PENDING') if has_applied else None

    with st.expander(f"🏆 {name}", expanded=False):
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"**Tournament:** {name}")
            st.caption(f"📅 **Date:** {start_date}")
            st.caption(f"🎯 **Age Group:** {age_icon} {age_group}")
            st.caption(f"📊 **Status:** {status}")
            st.caption(f"📋 **Assignment Type:** {assignment_type}")  # 🔥 FIX: Show assignment type

            # 🔥 FIX: Show application status if already applied
            if has_applied:
                status_icons = {
                    'PENDING': '🟡',
                    'ACCEPTED': '🟢',
                    'DECLINED': '🔴',
                    'CANCELLED': '⚫'
                }
                status_icon = status_icons.get(application_status, '⚪')
                st.caption(f"📝 **Your Application:** {status_icon} {application_status}")

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
            # 🔥 FIX: Only show Apply button for APPLICATION_BASED tournaments
            if assignment_type == 'APPLICATION_BASED':
                # 🔥 FIX: Check if already applied
                if has_applied:
                    # Show status instead of Apply button
                    if application_status == 'PENDING':
                        st.info("📩 **Application Pending**\n\nWaiting for admin review")
                    elif application_status == 'ACCEPTED':
                        st.success("✅ **Application Accepted**\n\nCheck Inbox tab")
                    elif application_status == 'DECLINED':
                        st.error("❌ **Application Declined**")
                    elif application_status == 'CANCELLED':
                        st.warning("⚫ **Application Cancelled**")
                else:
                    # Show Apply button
                    if st.button(f"📝 Apply", key=f"apply_{tournament_id}", use_container_width=True, type="primary"):
                        st.session_state['apply_tournament_id'] = tournament_id
                        st.session_state['apply_tournament_name'] = name
                        st.session_state['show_apply_dialog'] = True
                        st.rerun()
            elif assignment_type == 'OPEN_ASSIGNMENT':
                # Show info message for OPEN_ASSIGNMENT tournaments
                st.info("🔒 **Invite Only**\n\nAdmin will invite instructor directly")

        st.divider()



