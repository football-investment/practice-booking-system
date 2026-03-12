"""
User Filters Component
Compact, reusable filtering UI for admin dashboard
"""

import streamlit as st
from typing import List, Dict, Any


def render_user_filters() -> Dict[str, Any]:
    """
    Render user filter UI and return selected filter values

    Returns:
        dict: Selected filter values {
            'roles': list,
            'statuses': list,
            'search_query': str
        }
    """
    st.markdown("### 👥 User Filters")

    # Role filter
    st.markdown("**🎭 Role**")
    roles = st.multiselect(
        "Select roles",
        options=["student", "instructor", "admin"],
        default=[],
        key="user_filter_roles"
    )

    st.divider()

    # Status filter
    st.markdown("**✅ Status**")
    statuses = st.multiselect(
        "Select status",
        options=["active", "inactive"],
        default=[],
        key="user_filter_statuses"
    )

    st.divider()

    # Search filter
    st.markdown("**🔍 Search**")
    search_query = st.text_input(
        "Name or Email",
        placeholder="Enter name or email...",
        key="user_filter_search"
    )

    st.divider()

    # Clear filters button
    if st.button("🗑️ Clear All Filters", use_container_width=True, key="clear_user_filters"):
        st.session_state.user_filter_roles = []
        st.session_state.user_filter_statuses = []
        st.session_state.user_filter_search = ""
        st.rerun()

    return {
        'roles': roles,
        'statuses': statuses,
        'search_query': search_query.lower() if search_query else ""
    }


def apply_user_filters(users: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Apply filters to user list

    Args:
        users: List of user dictionaries
        filters: Filter values from render_user_filters()

    Returns:
        Filtered user list
    """
    filtered_users = users.copy()

    # Filter by role
    if filters['roles']:
        filtered_users = [
            u for u in filtered_users
            if u.get('role', '').lower() in filters['roles']
        ]

    # Filter by status
    if filters['statuses']:
        status_filtered = []
        for u in filtered_users:
            is_active = u.get('is_active', False)
            if 'active' in filters['statuses'] and is_active:
                status_filtered.append(u)
            elif 'inactive' in filters['statuses'] and not is_active:
                status_filtered.append(u)
        filtered_users = status_filtered

    # Filter by search query (name or email)
    if filters['search_query']:
        query = filters['search_query']
        filtered_users = [
            u for u in filtered_users
            if query in u.get('name', '').lower() or query in u.get('email', '').lower()
        ]

    return filtered_users
