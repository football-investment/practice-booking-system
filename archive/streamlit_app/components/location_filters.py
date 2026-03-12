"""
📍 Location Filters Component
Compact filter panel for Location Management
"""

import streamlit as st
from typing import List, Dict, Any


def render_location_filters(locations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Render location filter sidebar
    Returns filter values as dict
    """
    st.markdown("### 🔍 Filters")

    # Extract unique cities
    all_cities = sorted(list(set(loc.get('city', '') for loc in locations if loc.get('city'))))

    # City filter
    city_filter = st.selectbox(
        "🏙️ City",
        options=["All"] + all_cities,
        key="location_city_filter"
    )

    # Status filter
    status_filter = st.selectbox(
        "✅ Status",
        options=["Active Only", "Inactive Only", "All"],
        key="location_status_filter"
    )

    # Search by name
    search_term = st.text_input(
        "🔎 Search by name",
        placeholder="Type location name...",
        key="location_search"
    )

    st.divider()

    # Quick stats
    active_count = sum(1 for loc in locations if loc.get('is_active', False))
    inactive_count = len(locations) - active_count

    st.markdown("### 📊 Statistics")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Active", active_count)
    with col2:
        st.metric("Inactive", inactive_count)

    return {
        "city": city_filter,
        "status": status_filter,
        "search": search_term.lower().strip()
    }


def apply_location_filters(locations: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Apply filters to location list
    """
    filtered = locations

    # Apply city filter
    if filters["city"] != "All":
        filtered = [loc for loc in filtered if loc.get('city') == filters["city"]]

    # Apply status filter
    if filters["status"] == "Active Only":
        filtered = [loc for loc in filtered if loc.get('is_active', False)]
    elif filters["status"] == "Inactive Only":
        filtered = [loc for loc in filtered if not loc.get('is_active', False)]

    # Apply search filter
    if filters["search"]:
        filtered = [
            loc for loc in filtered
            if filters["search"] in loc.get('name', '').lower()
        ]

    return filtered
