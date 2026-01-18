"""
Tournament Table View - Table rendering for instructor tournament list
"""

import streamlit as st
import requests
from typing import Dict, List
from config import API_BASE_URL, API_TIMEOUT
from components.instructor.tournament_helpers import check_coach_level_sufficient, get_instructor_coach_level

def render_table_view(token: str, tournaments: List[Dict], application_statuses: Dict[int, Dict]):
    """
    Render tournaments in a sortable table format with inline filters.

    Args:
        token: Authentication token
        tournaments: List of tournament dictionaries
        application_statuses: Dict mapping tournament_id -> application data
    """
    import pandas as pd

    # 🔥 GET INSTRUCTOR COACH LEVEL (fetch fresh each time to avoid stale cache)
    instructor_coach_level = get_instructor_coach_level(token)

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


