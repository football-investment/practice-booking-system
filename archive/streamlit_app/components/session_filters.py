"""
Session Filters Component
Compact, reusable filtering UI for admin dashboard
"""

import streamlit as st
from datetime import datetime, date
from typing import List, Dict, Any


def render_session_filters(token: str = None) -> Dict[str, Any]:
    """
    Render session filter UI and return selected filter values

    Args:
        token: Authentication token for fetching locations (optional)

    Returns:
        dict: Selected filter values {
            'date_from': date,
            'date_to': date,
            'session_types': list,
            'statuses': list,
            'location': str
        }
    """
    st.markdown("### 📊 Session Filters")

    # Date range filter
    st.markdown("**📅 Date Range**")
    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input(
            "From",
            value=date.today(),
            key="session_filter_date_from"
        )
    with col2:
        date_to = st.date_input(
            "To",
            value=None,
            key="session_filter_date_to"
        )

    st.divider()

    # Session type filter
    st.markdown("**🏷️ Session Type**")
    session_types = st.multiselect(
        "Select types",
        options=["on_site", "hybrid", "virtual"],
        default=[],
        key="session_filter_types"
    )

    st.divider()

    # Status filter
    st.markdown("**📊 Status**")
    statuses = st.multiselect(
        "Select status",
        options=["upcoming", "past"],
        default=[],
        key="session_filter_status"
    )

    st.divider()

    # Location filter (dropdown with actual locations)
    st.markdown("**📍 Location**")

    location_filter = None
    if token:
        # Import here to avoid circular imports
        from api_helpers import get_locations

        # Fetch locations
        success_loc, all_locations = get_locations(token, include_inactive=False)

        if success_loc and all_locations:
            # Create display options: "All Locations" + individual cities
            location_options = ["All Locations"] + [
                f"{loc['city']}, {loc.get('country', '')}" if loc.get('country') else loc['city']
                for loc in all_locations
            ]

            selected_location = st.selectbox(
                "Filter by location",
                options=location_options,
                key="session_filter_location"
            )

            # If not "All Locations", extract city name for filtering
            if selected_location != "All Locations":
                # Extract city name (before comma)
                location_filter = selected_location.split(',')[0].strip()
            else:
                location_filter = None
        else:
            st.caption("⚠️ Could not load locations")
            location_filter = None
    else:
        # Fallback to text input if no token provided
        location_filter_text = st.text_input(
            "Filter by location",
            placeholder="e.g. Budapest...",
            key="session_filter_location_text"
        )
        location_filter = location_filter_text if location_filter_text else None

    st.divider()

    # Clear filters button
    if st.button("🗑️ Clear All Filters", use_container_width=True):
        st.session_state.session_filter_date_from = date.today()
        st.session_state.session_filter_date_to = None
        st.session_state.session_filter_types = []
        st.session_state.session_filter_status = []
        # Reset location filter (selectbox will default to "All Locations")
        if 'session_filter_location' in st.session_state:
            del st.session_state.session_filter_location
        if 'session_filter_location_text' in st.session_state:
            st.session_state.session_filter_location_text = ""
        st.rerun()

    return {
        'date_from': date_from,
        'date_to': date_to,
        'session_types': session_types,
        'statuses': statuses,
        'location': location_filter
    }


def apply_session_filters(sessions: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Apply filters to session list

    Args:
        sessions: List of session dictionaries
        filters: Filter values from render_session_filters()

    Returns:
        Filtered session list
    """
    filtered_sessions = sessions.copy()
    now = datetime.now()

    # Filter by date range
    if filters['date_from']:
        date_from_dt = datetime.combine(filters['date_from'], datetime.min.time())
        filtered_sessions = [
            s for s in filtered_sessions
            if s.get('date_start') and datetime.fromisoformat(s['date_start'].replace('Z', '+00:00')) >= date_from_dt
        ]

    if filters['date_to']:
        date_to_dt = datetime.combine(filters['date_to'], datetime.max.time())
        filtered_sessions = [
            s for s in filtered_sessions
            if s.get('date_start') and datetime.fromisoformat(s['date_start'].replace('Z', '+00:00')) <= date_to_dt
        ]

    # Filter by session type
    if filters['session_types']:
        filtered_sessions = [
            s for s in filtered_sessions
            if s.get('session_type') in filters['session_types']
        ]

    # Filter by status (upcoming/past)
    if filters['statuses']:
        status_filtered = []
        for s in filtered_sessions:
            if not s.get('date_start'):
                continue
            start_time = datetime.fromisoformat(s['date_start'].replace('Z', '+00:00'))
            is_upcoming = start_time > now

            if 'upcoming' in filters['statuses'] and is_upcoming:
                status_filtered.append(s)
            elif 'past' in filters['statuses'] and not is_upcoming:
                status_filtered.append(s)

        filtered_sessions = status_filtered

    # Filter by location (case-insensitive substring match)
    if filters.get('location'):
        location_search = filters['location'].lower().strip()
        filtered_sessions = [
            s for s in filtered_sessions
            if s.get('location') and location_search in s['location'].lower()
        ]

    return filtered_sessions
