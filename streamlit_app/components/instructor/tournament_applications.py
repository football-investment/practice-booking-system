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
import hashlib
import uuid
from typing import Dict, List, Any
from datetime import datetime
from config import API_BASE_URL, API_TIMEOUT


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_instructor_coach_level(token: str) -> int:
    """
    Get the instructor's highest LFA_COACH license level.

    This is a WORKAROUND: Since there's no /api/v1/user-licenses/me endpoint,
    we query the database directly using a SQL-like approach through the users endpoint.

    For now, we'll use a simpler approach: check the user's profile data
    which may include license information, or query the database directly.

    Returns:
        int: Highest coach level (1-8), or 0 if no LFA_COACH license found
    """
    try:
        # WORKAROUND: Query database directly since API endpoint doesn't exist
        # We'll need to implement this properly on the backend
        # For now, return a default based on user email for testing

        # Get current user info
        response = requests.get(
            f"{API_BASE_URL}/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            user_data = response.json()
            user_id = user_data.get('id')

            # Query database directly (temporary solution)
            import psycopg2
            conn = psycopg2.connect(
                host="localhost",
                database="lfa_intern_system",
                user="postgres",
                password="postgres",
                port=5432
            )
            cur = conn.cursor()

            # Get highest LFA_COACH license level
            cur.execute("""
                SELECT MAX(current_level)
                FROM user_licenses
                WHERE user_id = %s AND specialization_type = 'LFA_COACH'
            """, (user_id,))

            result = cur.fetchone()
            cur.close()
            conn.close()

            if result and result[0] is not None:
                return int(result[0])

        return 0
    except Exception as e:
        # Fallback: return 0 if any error occurs
        print(f"Error getting coach level: {e}")
        return 0


def check_coach_level_sufficient(coach_level: int, age_group: str) -> bool:
    """
    Check if instructor's coach level is sufficient for tournament age group.

    Args:
        coach_level: Instructor's coach level (1-8)
        age_group: Tournament age group (e.g., 'PRE', 'YOUTH', 'AMATEUR', 'PRO')

    Returns:
        bool: True if level is sufficient, False otherwise
    """
    MINIMUM_COACH_LEVELS = {
        "PRE": 1,       # Level 1 (lowest)
        "YOUTH": 3,     # Level 3
        "AMATEUR": 5,   # Level 5
        "PRO": 7        # Level 7 (highest)
    }

    required_level = MINIMUM_COACH_LEVELS.get(age_group)

    # If age group not in mapping, allow (backward compatibility)
    if required_level is None:
        return True

    return coach_level >= required_level


def batch_get_application_statuses(token: str, tournament_ids: List[int]) -> Dict[int, Dict]:
    """
    Batch fetch application status for multiple tournaments.

    Args:
        token: Authentication token
        tournament_ids: List of tournament IDs to check

    Returns:
        Dictionary mapping tournament_id -> application data
        Example: {25: {"status": "PENDING", "id": 123}, 26: None}
    """
    application_map = {}

    # For each tournament, check if instructor has applied
    for tournament_id in tournament_ids:
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/my-application",
                headers={"Authorization": f"Bearer {token}"},
                timeout=API_TIMEOUT
            )
            if response.status_code == 200:
                application_map[tournament_id] = response.json()
            else:
                application_map[tournament_id] = None
        except:
            application_map[tournament_id] = None

    return application_map


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

            # Filter for all tournaments with SEEKING_INSTRUCTOR status
            # Show both APPLICATION_BASED and OPEN_ASSIGNMENT
            # Apply button only shows for APPLICATION_BASED
            open_tournaments = [
                t for t in all_semesters
                if (t.get('code', '').startswith('TOURN-') and
                    t.get('status') == 'SEEKING_INSTRUCTOR')
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


def render_table_view(token: str, tournaments: List[Dict], application_statuses: Dict[int, Dict]):
    """
    Render tournaments in a sortable table format with inline filters.

    Args:
        token: Authentication token
        tournaments: List of tournament dictionaries
        application_statuses: Dict mapping tournament_id -> application data
    """
    import pandas as pd

    # 🔥 GET INSTRUCTOR COACH LEVEL (cached in session state)
    if 'instructor_coach_level' not in st.session_state:
        st.session_state['instructor_coach_level'] = get_instructor_coach_level(token)

    instructor_coach_level = st.session_state['instructor_coach_level']

    # Initialize filter state
    if 'table_filters' not in st.session_state:
        st.session_state['table_filters'] = {
            'age_groups': [],
            'assignment_types': [],
            'application_statuses': []
        }

    # Inline filters
    st.markdown("#### 🔍 Filters")
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([2, 2, 2, 1])

    with filter_col1:
        age_group_options = ['PRE', 'YOUTH', 'AMATEUR', 'PRO']
        selected_ages = st.multiselect(
            "Age Group",
            options=age_group_options,
            default=st.session_state['table_filters']['age_groups'],
            key='filter_age_groups'
        )
        st.session_state['table_filters']['age_groups'] = selected_ages

    with filter_col2:
        assignment_type_options = ['APPLICATION_BASED', 'OPEN_ASSIGNMENT']
        selected_assignment_types = st.multiselect(
            "Assignment Type",
            options=assignment_type_options,
            default=st.session_state['table_filters']['assignment_types'],
            key='filter_assignment_types'
        )
        st.session_state['table_filters']['assignment_types'] = selected_assignment_types

    with filter_col3:
        status_options = ['Not Applied', 'Pending', 'Accepted', 'Declined']
        selected_statuses = st.multiselect(
            "Your Status",
            options=status_options,
            default=st.session_state['table_filters']['application_statuses'],
            key='filter_application_statuses'
        )
        st.session_state['table_filters']['application_statuses'] = selected_statuses

    with filter_col4:
        if st.button("🔄 Reset", use_container_width=True):
            st.session_state['table_filters'] = {
                'age_groups': [],
                'assignment_types': [],
                'application_statuses': []
            }
            st.rerun()

    st.divider()

    # Prepare data for table display
    table_data = []
    for tournament in tournaments:
        tournament_id = tournament.get('id')
        age_group = tournament.get('age_group', 'UNKNOWN')
        assignment_type = tournament.get('assignment_type', 'UNKNOWN')
        application_data = application_statuses.get(tournament_id)

        # Determine application status
        if application_data:
            app_status = application_data.get('status', 'PENDING')
            status_display = app_status.title()
        else:
            app_status = 'NOT_APPLIED'
            status_display = 'Not Applied'

        # Apply filters
        if selected_ages and age_group not in selected_ages:
            continue
        if selected_assignment_types and assignment_type not in selected_assignment_types:
            continue
        if selected_statuses:
            if status_display not in selected_statuses:
                continue

        # Format date
        start_date = tournament.get('start_date', 'TBD')
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

        # Status icon
        status_icons = {
            'NOT_APPLIED': '-',
            'PENDING': '🟡',
            'ACCEPTED': '🟢',
            'DECLINED': '🔴',
            'CANCELLED': '⚫'
        }
        status_icon = status_icons.get(app_status, '⚪')

        # 🔥 CHECK COACH LEVEL: Can only apply if level is sufficient
        has_sufficient_level = check_coach_level_sufficient(instructor_coach_level, age_group)

        table_data.append({
            'id': tournament_id,
            'name': tournament.get('name', 'Unnamed'),
            'date': date_display,
            'date_sort': start_date,  # For sorting
            'age_group': f"{age_icon} {age_group}",
            'age_group_sort': age_group,  # For sorting
            'assignment_type': f"{assignment_icon} {assignment_type}",
            'assignment_type_sort': assignment_type,  # For sorting
            'status': f"{status_icon} {status_display}",
            'status_sort': app_status,  # For sorting
            'can_apply': assignment_type == 'APPLICATION_BASED' and not application_data and has_sufficient_level,
            'has_sufficient_level': has_sufficient_level,  # Track for UI messaging
            'application_data': application_data,
            'tournament': tournament
        })

    if not table_data:
        st.info("📭 No tournaments match the selected filters")
        return

    # Sort controls
    sort_col1, sort_col2 = st.columns([3, 1])
    with sort_col1:
        sort_by = st.selectbox(
            "Sort by",
            options=['Date', 'Name', 'Age Group', 'Assignment Type', 'Your Status'],
            index=0,  # Default: Date
            key='table_sort_by'
        )

    with sort_col2:
        sort_order = st.radio(
            "Order",
            options=['Ascending', 'Descending'],
            index=0,  # Default: Ascending
            horizontal=True,
            key='table_sort_order'
        )

    # Apply sorting
    sort_key_map = {
        'Date': 'date_sort',
        'Name': 'name',
        'Age Group': 'age_group_sort',
        'Assignment Type': 'assignment_type_sort',
        'Your Status': 'status_sort'
    }
    sort_key = sort_key_map[sort_by]
    table_data.sort(key=lambda x: x[sort_key], reverse=(sort_order == 'Descending'))

    st.divider()

    # Pagination
    page_size = 10
    total_items = len(table_data)
    total_pages = (total_items + page_size - 1) // page_size

    if 'table_current_page' not in st.session_state:
        st.session_state['table_current_page'] = 1

    # Pagination controls
    if total_pages > 1:
        pag_col1, pag_col2, pag_col3 = st.columns([1, 2, 1])
        with pag_col1:
            if st.button("⬅️ Previous", disabled=(st.session_state['table_current_page'] == 1)):
                st.session_state['table_current_page'] -= 1
                st.rerun()

        with pag_col2:
            st.markdown(f"<div style='text-align: center;'>Page {st.session_state['table_current_page']} of {total_pages}</div>", unsafe_allow_html=True)

        with pag_col3:
            if st.button("Next ➡️", disabled=(st.session_state['table_current_page'] == total_pages)):
                st.session_state['table_current_page'] += 1
                st.rerun()

        st.divider()

    # Paginate data
    start_idx = (st.session_state['table_current_page'] - 1) * page_size
    end_idx = start_idx + page_size
    page_data = table_data[start_idx:end_idx]

    # Render table rows
    for row in page_data:
        render_table_row(token, row)


def render_table_row(token: str, row: Dict):
    """Render a single row in the table view with mobile-responsive layout"""
    with st.container():
        # Desktop view: All columns in one row
        # Mobile view: Stack content vertically

        # Primary info (always visible)
        st.markdown(f"**🏆 {row['name']}**")

        # Secondary info in columns (responsive)
        info_col1, info_col2, info_col3, info_col4 = st.columns([2, 2, 2, 2])

        with info_col1:
            st.caption(f"📅 {row['date']}")

        with info_col2:
            st.caption(row['age_group'])

        with info_col3:
            st.caption(row['assignment_type'])

        with info_col4:
            st.caption(row['status'])

        # Action button (full width for mobile)
        if row['can_apply']:
            if st.button("📝 Apply", key=f"apply_table_{row['id']}", use_container_width=True, type="primary"):
                st.session_state['apply_tournament_id'] = row['id']
                st.session_state['apply_tournament_name'] = row['name']
                st.session_state['show_apply_dialog'] = True
                st.rerun()
        elif row['assignment_type_sort'] == 'APPLICATION_BASED' and not row['application_data'] and not row['has_sufficient_level']:
            # Show required level for this tournament
            age_group_raw = row['age_group_sort']
            required_levels = {"PRE": 1, "YOUTH": 3, "AMATEUR": 5, "PRO": 7}
            required_level = required_levels.get(age_group_raw, 1)
            st.warning(f"🔒 Level {required_level}+ Required")
        elif row['assignment_type_sort'] == 'OPEN_ASSIGNMENT' and not row['application_data']:
            st.info("🔒 **Invite Only** - Admin will invite instructor directly")
        elif row['application_data']:
            if st.button("📋 View Details", key=f"view_table_{row['id']}", use_container_width=True):
                st.session_state['view_tournament_id'] = row['id']
                st.session_state['view_tournament_data'] = row
                st.session_state['show_tournament_dialog'] = True
                st.rerun()

        st.divider()

    # Show tournament detail dialog if triggered
    if (st.session_state.get('show_tournament_dialog') and
        st.session_state.get('view_tournament_id') == row['id']):
        show_tournament_detail_dialog(token, row)


@st.dialog("🏆 Tournament Details")
def show_tournament_detail_dialog(token: str, row: Dict):
    """Show full tournament details in a dialog"""
    tournament = row['tournament']
    application_data = row['application_data']

    st.markdown(f"### {row['name']}")

    col1, col2 = st.columns(2)

    with col1:
        st.caption(f"📅 **Date:** {row['date']}")
        st.caption(f"🎯 **Age Group:** {row['age_group']}")
        st.caption(f"📋 **Assignment Type:** {row['assignment_type']}")

    with col2:
        st.caption(f"📊 **Status:** {tournament.get('status', 'N/A')}")
        st.caption(f"📝 **Your Status:** {row['status']}")

    st.divider()

    # Show sessions if available
    try:
        sessions_response = requests.get(
            f"{API_BASE_URL}/api/v1/sessions",
            headers={"Authorization": f"Bearer {token}"},
            params={"semester_id": row['id'], "size": 100},
            timeout=API_TIMEOUT
        )
        if sessions_response.status_code == 200:
            sessions = sessions_response.json().get('items', [])
            st.caption(f"📋 **Sessions:** {len(sessions)}")
    except:
        pass

    # Show application details if applied
    if application_data:
        st.markdown("#### Your Application")
        st.info(f"💬 **Your message:** {application_data.get('application_message', 'N/A')}")

        response_message = application_data.get('response_message')
        if response_message:
            st.success(f"📧 **Admin response:** {response_message}")

    if st.button("Close", use_container_width=True):
        st.session_state['show_tournament_dialog'] = False
        st.rerun()


def render_kanban_view(token: str, tournaments: List[Dict], application_statuses: Dict[int, Dict]):
    """
    Render tournaments in a Kanban board layout grouped by application status.
    Mobile-responsive: Columns stack vertically on narrow screens.

    Args:
        token: Authentication token
        tournaments: List of tournament dictionaries
        application_statuses: Dict mapping tournament_id -> application data
    """
    # 🔥 GET INSTRUCTOR COACH LEVEL (cached in session state)
    if 'instructor_coach_level' not in st.session_state:
        st.session_state['instructor_coach_level'] = get_instructor_coach_level(token)

    instructor_coach_level = st.session_state['instructor_coach_level']

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
                    st.info("ℹ️ Admin will review your application. Check the 'Inbox' tab for status updates.")
                    time.sleep(2)
                    # Clear dialog state
                    st.session_state['show_apply_dialog'] = False
                    # 🔥 FIX: Clear cache to force refresh on next render
                    if 'tournament_application_statuses' in st.session_state:
                        del st.session_state['tournament_application_statuses']
                    st.rerun()

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state['show_apply_dialog'] = False
            st.rerun()


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


def render_system_message_card(token: str, application: Dict, status_category: str):
    """
    Render a universal system message card.

    Supports:
    - Tournament invitations (OPEN_ASSIGNMENT)
    - Tournament applications (APPLICATION_BASED)
    - Future: Semester assignments, session requests, etc.
    """

    app_id = application.get('id')
    tournament_id = application.get('tournament_id')
    tournament_name = application.get('tournament_name', 'Unknown Tournament')
    status = application.get('status')
    tournament_status = application.get('tournament_status')
    created_at = application.get('created_at')
    application_message = application.get('application_message', 'N/A')
    response_message = application.get('response_message')
    responded_at = application.get('responded_at')

    # Get tournament details for more context
    age_group = application.get('age_group', 'UNKNOWN')
    assignment_type = application.get('assignment_type', 'APPLICATION_BASED')
    start_date = application.get('start_date', 'N/A')

    # Format dates
    try:
        created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).strftime('%Y-%m-%d')
    except:
        created_date = 'N/A'

    try:
        event_date = datetime.fromisoformat(start_date.replace('Z', '+00:00')).strftime('%Y-%m-%d')
    except:
        event_date = 'N/A'

    # Age group icon mapping
    age_icons = {
        'PRE': '👶',
        'YOUTH': '👦',
        'AMATEUR': '🧑',
        'PRO': '👨'
    }
    age_icon = age_icons.get(age_group, '❓')

    # Assignment type badge - Dark mode compatible colors
    if assignment_type == 'OPEN_ASSIGNMENT':
        type_badge = "📩 Direct Invitation from Admin"
        type_bg_color = "rgba(33, 150, 243, 0.15)"  # Blue with transparency
        type_text_color = "#42A5F5"  # Bright blue for dark mode
    else:
        type_badge = "📝 Your Application"
        type_bg_color = "rgba(156, 39, 176, 0.15)"  # Purple with transparency
        type_text_color = "#AB47BC"  # Bright purple for dark mode

    # Status badge styling - Dark mode compatible
    if status == 'PENDING':
        status_badge_color = 'rgba(255, 152, 0, 0.2)'  # Orange with transparency
        status_badge_text_color = '#FFB74D'  # Bright orange
        status_icon = '🤝'
        display_status = 'PENDING'
    elif status == 'ACCEPTED' and tournament_status == 'PENDING_INSTRUCTOR_ACCEPTANCE':
        status_badge_color = 'rgba(255, 152, 0, 0.2)'
        status_badge_text_color = '#FFA726'  # Bright orange
        status_icon = '⏳'
        display_status = 'ACTION REQUIRED'
    elif status == 'ACCEPTED':
        status_badge_color = 'rgba(76, 175, 80, 0.2)'  # Green with transparency
        status_badge_text_color = '#81C784'  # Bright green
        status_icon = '✅'
        display_status = 'CONFIRMED'
    else:
        status_badge_color = 'rgba(244, 67, 54, 0.2)'  # Red with transparency
        status_badge_text_color = '#E57373'  # Bright red
        status_icon = '❌'
        display_status = status

    # Compact inbox-style card - all info in minimal space like email inbox
    card_html = f"""
    <div style='border: 1px solid rgba(128, 128, 128, 0.3); border-radius: 6px; padding: 10px;
                margin-bottom: 6px; background-color: rgba(128, 128, 128, 0.05);'>
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <div style='display: flex; gap: 10px; align-items: center; flex: 1;'>
                <span style='font-size: 16px;'>🏆</span>
                <span style='background-color: {type_bg_color}; color: {type_text_color};
                            padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 500;'>
                    {type_badge.replace("📩 ", "").replace("📝 ", "")}
                </span>
                <span style='font-weight: 600; font-size: 13px;'>{tournament_name}</span>
            </div>
            <div style='display: flex; gap: 10px; align-items: center;'>
                <span style='font-size: 10px; color: rgba(128, 128, 128, 0.8);'>📅 {event_date}</span>
                <span style='font-size: 10px; color: rgba(128, 128, 128, 0.8);'>{age_icon} {age_group}</span>
                <span style='background-color: {status_badge_color}; color: {status_badge_text_color};
                            padding: 2px 8px; border-radius: 10px; font-weight: bold; font-size: 10px;'>
                    {status_icon} {display_status}
                </span>
                <span style='font-size: 10px; color: rgba(128, 128, 128, 0.6);'>#{app_id}</span>
            </div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    # Expandable message section (collapsed by default to save space)
    message_preview = (application_message[:60] + "...") if len(application_message) > 60 else application_message
    with st.expander(f"💬 {message_preview}", expanded=False):
        if assignment_type == 'OPEN_ASSIGNMENT' and response_message:
            st.markdown(f"**Admin invitation:**")
            st.markdown(f"_{response_message}_")
        else:
            st.markdown(f"**Your application:**")
            st.markdown(f"_{application_message}_")

        # Admin response (if any)
        if response_message and assignment_type == 'APPLICATION_BASED':
            st.markdown(f"**📧 Admin response:**")
            st.markdown(f"_{response_message}_")

    # Action buttons
    button_col1, button_col2, button_col3 = st.columns([1, 1, 2])

    with button_col1:
        # Accept button for assignments that need instructor action
        if status == 'ACCEPTED' and tournament_status == 'PENDING_INSTRUCTOR_ACCEPTANCE':
            # Use UUID to ensure 100% uniqueness even if function is called multiple times in same render
            accept_key = f"accept_btn_{app_id}_{uuid.uuid4().hex[:8]}"
            if st.button(f"✅ Accept", key=accept_key, use_container_width=True, type="primary"):
                if accept_assignment(token, tournament_id):
                    st.success("✅ Assignment accepted successfully!")
                    st.info("🎉 You are now the master instructor for this tournament!")
                    time.sleep(2)
                    st.rerun()

    with button_col2:
        # Decline button (future implementation)
        if status == 'ACCEPTED' and tournament_status == 'PENDING_INSTRUCTOR_ACCEPTANCE':
            # Use UUID to ensure 100% uniqueness
            decline_key = f"decline_btn_{app_id}_{uuid.uuid4().hex[:8]}"
            if st.button(f"❌ Decline", key=decline_key, use_container_width=True):
                st.warning("⚠️ Decline functionality coming soon!")

    st.divider()


def render_application_card(token: str, application: Dict, status_category: str):
    """
    DEPRECATED: Use render_system_message_card instead.
    This function is kept for backward compatibility only.
    """
    # Redirect to new universal card renderer
    render_system_message_card(token, application, status_category)



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
    age_group = tournament.get('age_group', 'UNKNOWN')

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
