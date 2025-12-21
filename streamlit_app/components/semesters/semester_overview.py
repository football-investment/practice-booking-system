"""
Semester Overview Component
Hierarchical structural view of Location → Semesters
"""

import streamlit as st
import sys
from pathlib import Path
from collections import defaultdict
from typing import List, Dict

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from api_helpers_semesters import (
    get_all_locations,
    get_all_semesters
)


def render_semester_cards(semesters: List[Dict], key_prefix: str = ""):
    """
    Render semester cards in a compact list format

    Args:
        semesters: List of semester dictionaries
        key_prefix: Unique prefix for widget keys
    """
    if not semesters:
        st.info("📭 No semesters in this group")
        return

    for idx, sem in enumerate(semesters):
        status = "✅" if sem.get('is_active') else "⏸️"

        col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

        with col1:
            st.write(f"{status} **{sem.get('code', 'N/A')}**")

        with col2:
            start = sem.get('start_date', 'N/A')
            end = sem.get('end_date', 'N/A')
            st.write(f"{start} → {end}")

        with col3:
            st.write(f"📚 Sessions: {sem.get('total_sessions', 0)}")

        with col4:
            st.write(f"👥 Enrollments: {sem.get('total_enrollments', 0)}")

        st.divider()


def render_by_year(semesters: List[Dict], location_key: str):
    """
    Render semesters grouped by year

    Args:
        semesters: List of semester dictionaries
        location_key: Unique key for this location
    """
    # Group by year
    by_year = defaultdict(list)
    for sem in semesters:
        code = sem.get('code', '')
        year = code.split('/')[0] if '/' in code else 'Unknown'
        by_year[year].append(sem)

    if not by_year:
        st.info("📭 No semesters found")
        return

    # Sort years in descending order
    for year in sorted(by_year.keys(), reverse=True):
        year_semesters = by_year[year]

        with st.expander(f"📅 **{year}** ({len(year_semesters)} semesters)", expanded=False):
            render_semester_cards(year_semesters, key_prefix=f"{location_key}_year_{year}")


def render_by_specialization(semesters: List[Dict], location_key: str):
    """
    Render semesters grouped by specialization

    Args:
        semesters: List of semester dictionaries
        location_key: Unique key for this location
    """
    # Group by base specialization
    by_spec = defaultdict(list)
    for sem in semesters:
        spec = sem.get('specialization_type', 'Unknown')

        # Extract base specialization (e.g., LFA_PLAYER_PRE -> LFA_PLAYER)
        if '_' in spec:
            parts = spec.split('_')
            # Join all parts except the last one (age group)
            base_spec = '_'.join(parts[:-1]) if len(parts) > 1 else spec
        else:
            base_spec = spec

        by_spec[base_spec].append(sem)

    if not by_spec:
        st.info("📭 No semesters found")
        return

    # Sort specializations alphabetically
    for spec in sorted(by_spec.keys()):
        spec_semesters = by_spec[spec]

        with st.expander(f"⚽ **{spec}** ({len(spec_semesters)} semesters)", expanded=False):
            render_semester_cards(spec_semesters, key_prefix=f"{location_key}_spec_{spec}")


def render_semester_overview(token: str):
    """
    Render hierarchical overview of Location → Semesters structure

    Features:
    - Group semesters by location
    - Show statistics per location
    - Hierarchical display (Year/Specialization grouping)
    - Quick navigation to other tabs
    """
    st.markdown("### 📊 Structural Overview")
    st.caption("Hierarchical view of all locations and their semesters")

    # Refresh button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Refresh", key="refresh_overview", use_container_width=True):
            st.rerun()

    # Fetch all locations
    success_loc, error_loc, locations = get_all_locations(token, include_inactive=False)

    if not success_loc:
        st.error(f"❌ Failed to fetch locations: {error_loc}")
        return

    if not locations:
        st.warning("⚠️ No active locations found. Create a location first in the **📍 Locations** tab!")
        return

    # Fetch all semesters
    success_sem, error_sem, data = get_all_semesters(token)

    if not success_sem:
        st.error(f"❌ Failed to fetch semesters: {error_sem}")
        return

    semesters = data.get("semesters", [])

    # Group semesters by location_city
    semesters_by_location = defaultdict(list)
    for sem in semesters:
        location_city = sem.get('location_city', 'Unknown')
        semesters_by_location[location_city].append(sem)

    # Display overall statistics
    st.markdown("#### 📈 Overall Statistics")
    overall_col1, overall_col2, overall_col3, overall_col4 = st.columns(4)

    overall_col1.metric("Total Locations", len(locations))
    overall_col2.metric("Total Semesters", len(semesters))

    active_semesters = sum(1 for s in semesters if s.get('is_active'))
    overall_col3.metric("Active Semesters", active_semesters)
    overall_col4.metric("Inactive Semesters", len(semesters) - active_semesters)

    st.divider()

    # Render each location
    st.markdown("#### 📍 Locations & Semesters")

    for location in locations:
        location_id = location.get('id', 0)
        city = location.get('city', 'Unknown')
        name = location.get('name', 'Unknown Location')
        country = location.get('country', 'Unknown')

        semesters_at_location = semesters_by_location.get(city, [])

        # Calculate statistics for this location
        total = len(semesters_at_location)
        active = sum(1 for s in semesters_at_location if s.get('is_active'))
        inactive = total - active

        # Extract unique specialization types
        unique_specs = set()
        for sem in semesters_at_location:
            spec = sem.get('specialization_type', '')
            if spec:
                # Extract base specialization
                if '_' in spec:
                    parts = spec.split('_')
                    base_spec = '_'.join(parts[:-1]) if len(parts) > 1 else spec
                else:
                    base_spec = spec
                unique_specs.add(base_spec)

        # Location expander
        with st.expander(
            f"📍 **{name}** ({city}, {country}) — {total} semesters",
            expanded=(total > 0)
        ):
            # Statistics row
            stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)

            stat_col1.metric("Total Semesters", total)
            stat_col2.metric("Active", active, delta=None)
            stat_col3.metric("Inactive", inactive, delta=None)
            stat_col4.metric("Specializations", len(unique_specs))

            if total == 0:
                st.info("📭 No semesters at this location yet")

                # Quick action: Generate semesters
                if st.button("🚀 Generate Semesters Here", key=f"gen_{location_id}", use_container_width=True):
                    st.info("💡 Navigate to the **🚀 Generate** tab to create semesters for this location")

                continue

            st.divider()

            # Grouping selector
            view_by = st.radio(
                "📊 Group semesters by:",
                ["Year", "Specialization"],
                horizontal=True,
                key=f"view_{location_id}"
            )

            st.markdown("---")

            # Render grouped semesters
            if view_by == "Year":
                render_by_year(semesters_at_location, location_key=str(location_id))
            else:
                render_by_specialization(semesters_at_location, location_key=str(location_id))

            st.divider()

            # Quick action buttons
            action_col1, action_col2 = st.columns(2)

            with action_col1:
                if st.button("🚀 Generate More Here", key=f"gen_more_{location_id}", use_container_width=True):
                    st.info("💡 Navigate to the **🚀 Generate** tab to create more semesters")

            with action_col2:
                if st.button("🎯 View in Manage Tab", key=f"manage_{location_id}", use_container_width=True):
                    st.info(f"💡 Navigate to the **🎯 Manage** tab and filter by location: {city}")

    st.divider()

    # Footer info
    st.caption("💡 **Tip:** Use the tabs above to navigate between Overview, Locations, Generate, and Manage")
