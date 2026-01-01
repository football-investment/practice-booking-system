"""
Semester Management Component
Manage existing semesters (list, filter, toggle active, delete)
Extracted from unified_workflow_dashboard.py lines 1867-2098 (P0 scope)

✅ INTELLIGENT LABELING: Automatically uses "Season" for LFA_PLAYER, "Semester" for others
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from api_helpers_semesters import (
    get_all_semesters,
    update_semester,
    delete_semester
)
from components.period_labels import (
    get_period_label,
    get_count_text
)


def render_semester_management(token: str):
    """
    Render the semester/season management interface
    - List all semesters/seasons with filters
    - Individual semester/season cards
    - Toggle active/inactive
    - Delete functionality (empty semesters/seasons only)

    Source: unified_workflow_dashboard.py lines 1867-2098 (P0 scope)
    ✅ INTELLIGENT LABELING: Adapts "Season" vs "Semester" based on specialization
    """
    st.markdown("### 🎯 Manage Existing Periods")
    st.caption("View all semesters/seasons and manage them")

    # Refresh button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Refresh", key="refresh_semesters", use_container_width=True):
            st.rerun()

    # Fetch all semesters
    success, error, data = get_all_semesters(token)

    if not success:
        st.error(f"❌ Failed to fetch semesters: {error}")
        return

    semesters = data.get("semesters", [])

    if not semesters:
        st.info("📭 No periods found. Generate some in the **🚀 Generate** tab!")
        return

    st.success(f"📊 Found **{len(semesters)}** periods")

    # Filter options
    st.markdown("#### 🔍 Filters")
    filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns(5)

    with filter_col1:
        # Extract unique locations (city) - FIRST FILTER
        all_locations = list(set([
            s['location_city'] for s in semesters if s.get('location_city')
        ]))
        selected_location = st.selectbox(
            "📍 Location",
            ["All"] + sorted([loc for loc in all_locations if loc]),
            key="filter_location"
        )

    with filter_col2:
        # Extract unique years
        all_years = list(set([
            s['code'].split('/')[0]
            for s in semesters
            if s.get('code') and '/' in s['code']
        ]))
        selected_year = st.selectbox(
            "📅 Year",
            ["All"] + sorted(all_years, reverse=True),
            key="filter_year"
        )

    with filter_col3:
        # Extract unique specializations (base type without age group)
        all_base_specs = set()
        for s in semesters:
            spec_type = s.get('specialization_type')
            if spec_type and '_' in spec_type:
                # Extract base spec (e.g., "LFA_PLAYER_PRE" -> "LFA_PLAYER")
                parts = spec_type.split('_')
                # Join all parts except the last one (age group)
                base_spec = '_'.join(parts[:-1])
                all_base_specs.add(base_spec)
            elif spec_type:
                all_base_specs.add(spec_type)

        selected_base_spec = st.selectbox(
            "⚽ Specialization",
            ["All"] + sorted(list(all_base_specs)),
            key="filter_base_spec"
        )

    with filter_col4:
        # Extract unique age groups
        all_age_groups = list(set([
            s['age_group'] for s in semesters if s.get('age_group')
        ]))
        selected_age_group = st.selectbox(
            "👥 Age Group",
            ["All"] + sorted(all_age_groups),
            key="filter_age_group"
        )

    with filter_col5:
        # Extract unique location types from semesters
        location_types_in_use = set()
        for s in semesters:
            loc_type = s.get('location_type', 'PARTNER')
            if loc_type:  # Skip None values
                location_types_in_use.add(loc_type)

        selected_location_type = st.selectbox(
            "🏢 Location Type",
            ["All"] + sorted(list(location_types_in_use)),
            key="filter_location_type"
        )

    # Apply filters
    filtered_semesters = semesters

    # Filter by year
    if selected_year != "All":
        filtered_semesters = [s for s in filtered_semesters if s.get('code', '').startswith(selected_year)]

    # Filter by base specialization
    if selected_base_spec != "All":
        filtered_semesters = [s for s in filtered_semesters
                            if s.get('specialization_type', '').startswith(selected_base_spec)]

    # Filter by age group
    if selected_age_group != "All":
        filtered_semesters = [s for s in filtered_semesters
                            if s.get('age_group') == selected_age_group]

    # Filter by location
    if selected_location != "All":
        filtered_semesters = [s for s in filtered_semesters
                            if s.get('location_city') == selected_location]

    # ✅ ÚJ: Location Type filter
    if selected_location_type != "All":
        filtered_semesters = [s for s in filtered_semesters if s.get('location_type') == selected_location_type]

    st.divider()

    # Dynamic header based on selected specialization
    # If a specific specialization is selected, use intelligent labeling
    if selected_base_spec != "All":
        period_label = get_period_label(selected_base_spec, plural=True)
        st.markdown(f"#### 📅 {period_label} ({len(filtered_semesters)})")
    else:
        st.markdown(f"#### 📅 Periods ({len(filtered_semesters)})")

    if not filtered_semesters:
        if selected_base_spec != "All":
            period_label_lower = get_period_label(selected_base_spec, plural=True, capitalize=False)
            st.info(f"🔍 No {period_label_lower} match the selected filters")
        else:
            st.info("🔍 No periods match the selected filters")
        return

    # Individual semester list
    for semester in filtered_semesters:
        # Status indicator
        is_active = semester.get('is_active', False)
        status_icon = "✅" if is_active else "⏸️"
        status_text = "ACTIVE" if is_active else "INACTIVE"

        with st.expander(f"{status_icon} **{semester.get('code', 'N/A')}** - {semester.get('name', 'N/A')} [{status_text}]"):
            # Semester details
            info_col1, info_col2, info_col3 = st.columns(3)

            with info_col1:
                st.markdown(f"**ID:** {semester.get('id', 'N/A')}")
                st.markdown(f"**Code:** {semester.get('code', 'N/A')}")
                st.markdown(f"**Name:** {semester.get('name', 'N/A')}")

            with info_col2:
                st.markdown(f"**Start:** {semester.get('start_date', 'N/A')}")
                st.markdown(f"**End:** {semester.get('end_date', 'N/A')}")
                st.markdown(f"**Specialization:** {semester.get('specialization_type', 'N/A')}")

            with info_col3:
                st.markdown(f"**Sessions:** {semester.get('total_sessions', 0)}")
                st.markdown(f"**Enrollments:** {semester.get('total_enrollments', 0)}")
                st.markdown(f"**Active:** {'Yes' if is_active else 'No'}")

            # Location info
            st.markdown(f"**📍 Location:** {semester.get('location_city', 'N/A')}, {semester.get('location_country', 'N/A')}")

            # ✅ ÚJ: Location Type Badge
            loc_type = semester.get('location_type', 'PARTNER')
            type_emoji = "🏢" if loc_type == 'CENTER' else "🤝"
            st.markdown(f"**{type_emoji} Location Type:** {loc_type}")

            st.markdown(f"**🎯 Theme:** {semester.get('theme', 'N/A')}")

            # Master instructor
            master_id = semester.get('master_instructor_id')
            if master_id:
                st.markdown(f"**👨‍🏫 Master Instructor ID:** {master_id}")
            else:
                st.markdown("**👨‍🏫 Master Instructor:** Not assigned")

            st.divider()

            # Action buttons
            action_col1, action_col2 = st.columns(2)

            with action_col1:
                # Toggle active/inactive
                new_active_status = not is_active
                toggle_label = "Activate" if new_active_status else "Deactivate"

                if st.button(f"🔄 {toggle_label}", key=f"toggle_{semester['id']}", use_container_width=True):
                    update_success, update_error, updated_sem = update_semester(
                        token,
                        semester['id'],
                        {"is_active": new_active_status}
                    )

                    if update_success:
                        # Get dynamic label for success message
                        spec_type = semester.get('specialization_type', '')
                        period_label_lower = get_period_label(spec_type, plural=False, capitalize=False)
                        st.success(f"✅ {period_label_lower.capitalize()} {toggle_label.lower()}d!")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed: {update_error}")

            with action_col2:
                # Delete button (only if no sessions)
                total_sessions = semester.get('total_sessions', 0)
                if total_sessions == 0:
                    if st.button("🗑️ Delete", key=f"delete_{semester['id']}", use_container_width=True):
                        delete_success, delete_error = delete_semester(token, semester['id'])

                        if delete_success:
                            # Get dynamic label for success message
                            spec_type = semester.get('specialization_type', '')
                            period_label_lower = get_period_label(spec_type, plural=False, capitalize=False)
                            st.success(f"✅ {period_label_lower.capitalize()} deleted!")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to delete: {delete_error}")
                else:
                    st.warning(f"⚠️ Cannot delete (has {total_sessions} sessions)")
