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

from api_helpers_semesters import get_all_locations
from api_client import APIClient


def get_period_label(specialization_type: str = None, plural: bool = True, capitalize: bool = True) -> str:
    """
    Get appropriate label (Season/Semester) based on specialization

    LFA_PLAYER specializations use "Season"
    All other specializations (COACH, INTERNSHIP, GANCUJU) use "Semester"

    Args:
        specialization_type: The specialization (e.g., 'LFA_PLAYER_PRE', 'COACH', etc.)
        plural: Return plural form if True
        capitalize: Capitalize first letter if True

    Returns:
        'Season'/'Seasons' for LFA_PLAYER, 'Semester'/'Semesters' for others
    """
    is_lfa_player = specialization_type and 'LFA_PLAYER' in specialization_type

    if is_lfa_player:
        label = "seasons" if plural else "season"
    else:
        label = "semesters" if plural else "semester"

    return label.capitalize() if capitalize else label


def get_period_label_for_semesters(semesters: List[Dict], plural: bool = True, capitalize: bool = True) -> str:
    """
    Determine the appropriate label for a list of semesters
    Uses "Season" if ALL semesters are LFA_PLAYER, otherwise "Semester"

    Args:
        semesters: List of semester dictionaries
        plural: Return plural form if True
        capitalize: Capitalize first letter if True

    Returns:
        'Season'/'Seasons' or 'Semester'/'Semesters'
    """
    if not semesters:
        return get_period_label(None, plural=plural, capitalize=capitalize)

    # Check if ALL semesters are LFA_PLAYER
    all_lfa_player = all(
        'LFA_PLAYER' in sem.get('specialization_type', '')
        for sem in semesters
    )

    if all_lfa_player:
        return get_period_label('LFA_PLAYER', plural=plural, capitalize=capitalize)
    else:
        return get_period_label(None, plural=plural, capitalize=capitalize)


def render_semester_cards(semesters: List[Dict], key_prefix: str = ""):
    """
    Render semester cards in a compact list format

    Args:
        semesters: List of semester dictionaries
        key_prefix: Unique prefix for widget keys
    """
    if not semesters:
        period_label = get_period_label_for_semesters([], plural=True, capitalize=False)
        st.info(f"📭 No {period_label} in this group")
        return

    for idx, sem in enumerate(semesters):
        status_emoji = "✅" if sem.get('is_active') else "⏸️"

        # Status badge mapping
        status_value = sem.get('status', 'DRAFT')
        status_badges = {
            'DRAFT': ('📝', 'gray'),
            'SEEKING_INSTRUCTOR': ('🔍', 'orange'),
            'INSTRUCTOR_ASSIGNED': ('👨\u200d🏫', 'yellow'),
            'READY_FOR_ENROLLMENT': ('🟢', 'green'),
            'ONGOING': ('🔵', 'blue'),
            'COMPLETED': ('✅', 'violet'),
            'CANCELLED': ('❌', 'red')
        }
        status_badge, status_color = status_badges.get(status_value, ('❓', 'gray'))

        col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1.5])

        with col1:
            st.write(f"{status_emoji} **{sem.get('code', 'N/A')}**")

        with col2:
            start = sem.get('start_date', 'N/A')
            end = sem.get('end_date', 'N/A')
            st.write(f"{start} → {end}")

        with col3:
            st.write(f"📚 Sessions: {sem.get('total_sessions', 0)}")

        with col4:
            st.write(f"👥 Enrollments: {sem.get('total_enrollments', 0)}")

        with col5:
            # Status badge with color
            st.markdown(f":{status_color}[{status_badge} {status_value}]")

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
        period_label = get_period_label_for_semesters(semesters, plural=True, capitalize=False)
        st.info(f"📭 No {period_label} found")
        return

    # Sort years in descending order
    for year in sorted(by_year.keys(), reverse=True):
        year_semesters = by_year[year]
        period_label = get_period_label_for_semesters(year_semesters, plural=True, capitalize=False)

        with st.expander(f"📅 **{year}** ({len(year_semesters)} {period_label})", expanded=False):
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
        period_label = get_period_label_for_semesters(semesters, plural=True, capitalize=False)
        st.info(f"📭 No {period_label} found")
        return

    # Sort specializations alphabetically
    for spec in sorted(by_spec.keys()):
        spec_semesters = by_spec[spec]
        period_label = get_period_label_for_semesters(spec_semesters, plural=True, capitalize=False)

        with st.expander(f"⚽ **{spec}** ({len(spec_semesters)} {period_label})", expanded=False):
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
    success_sem, error_sem, data = APIClient.from_config(token).semesters.get_list()

    if not success_sem:
        st.error(f"❌ Failed to fetch semesters: {error_sem}")
        return

    semesters = data.get("semesters", []) if data else []

    # Group semesters by location_city
    semesters_by_location = defaultdict(list)
    for sem in semesters:
        location_city = sem.get('location_city', 'Unknown')
        semesters_by_location[location_city].append(sem)

    # Display overall statistics
    st.markdown("#### 📈 Overall Statistics")
    overall_col1, overall_col2, overall_col3, overall_col4 = st.columns(4)

    # Use dynamic label for overall metrics
    overall_period_label = get_period_label_for_semesters(semesters, plural=True, capitalize=True)

    overall_col1.metric("Total Locations", len(locations))
    overall_col2.metric(f"Total {overall_period_label}", len(semesters))

    active_semesters = sum(1 for s in semesters if s.get('is_active'))
    overall_col3.metric(f"Active {overall_period_label}", active_semesters)
    overall_col4.metric(f"Inactive {overall_period_label}", len(semesters) - active_semesters)

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

        # Use dynamic label for this location's semesters
        location_period_label = get_period_label_for_semesters(semesters_at_location, plural=True, capitalize=False)
        location_period_label_single = get_period_label_for_semesters(semesters_at_location, plural=False, capitalize=True)
        location_period_label_plural = get_period_label_for_semesters(semesters_at_location, plural=True, capitalize=True)

        # Location type emoji és label
        location_type = location.get('location_type', 'PARTNER')
        location_type_emoji = "🏢" if location_type == 'CENTER' else "🤝"

        # Location expander
        with st.expander(
            f"{location_type_emoji} **{name}** ({city}, {country}) — **{location_type}** — {total} {location_period_label}",
            expanded=(total > 0)
        ):
            # Statistics row
            stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)

            stat_col1.metric(f"Total {location_period_label_plural}", total)
            stat_col2.metric("Active", active, delta=None)
            stat_col3.metric("Inactive", inactive, delta=None)
            stat_col4.metric("Specializations", len(unique_specs))

            # ✅ ÚJ: Capability info box
            if location_type == 'CENTER':
                st.success("🏢 **CENTER Location** → Képességek: Tournament ✅ | Mini Season ✅ | Academy Season ✅")
            else:
                st.warning("🤝 **PARTNER Location** → Képességek: Tournament ✅ | Mini Season ✅ | Academy Season ❌")

            if total == 0:
                st.info(f"📭 No {location_period_label} at this location yet")

                # Quick action: Generate semesters
                if st.button("🚀 Generate Semesters Here", key=f"gen_{location_id}", use_container_width=True):
                    st.info("💡 Navigate to the **🚀 Generate** tab to create semesters for this location")

                continue

            st.divider()

            # Grouping selector
            view_by = st.radio(
                f"📊 Group {location_period_label} by:",
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
                    st.info(f"💡 Navigate to the **🚀 Generate** tab to create more {location_period_label}")

            with action_col2:
                if st.button("🎯 View in Manage Tab", key=f"manage_{location_id}", use_container_width=True):
                    st.info(f"💡 Navigate to the **🎯 Manage** tab and filter by location: {city}")

    st.divider()

    # Footer info
    st.caption("💡 **Tip:** Use the tabs above to navigate between Overview, Locations, Generate, and Manage")
