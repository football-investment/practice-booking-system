"""
Semester Generation Component
Generate semesters for a given year/specialization/age group/location
Extracted from unified_workflow_dashboard.py lines 1740-1865

✅ INTELLIGENT LABELING: Automatically uses "Season" for LFA_PLAYER, "Semester" for others
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from api_helpers_semesters import (
    get_all_locations,
    get_available_templates,
    generate_semesters
)
from components.period_labels import (
    get_period_label,
    get_period_labels,
    get_header_text,
    get_generate_button_text,
    get_count_text
)


def render_semester_generation(token: str):
    """
    Render the semester/season generation interface
    - Select active location
    - Choose year/specialization/age group
    - Preview template info
    - Generate button (adapts to "Seasons" for LFA_PLAYER, "Semesters" for others)

    Source: unified_workflow_dashboard.py lines 1740-1865
    ✅ INTELLIGENT LABELING: Header text adapts based on selected specialization
    """
    # Default header (will update after specialization selection)
    st.markdown("### 🚀 Generate Periods for a Year")
    st.caption("⚠️ **Important:** You must select an active location before generating!")

    # Fetch active locations first
    success, error, all_locations = get_all_locations(token, include_inactive=False)

    if not success:
        st.error(f"❌ Failed to fetch locations: {error}")
        return

    # Filter for active locations only
    active_locations = [loc for loc in all_locations if loc.get('is_active', False)]

    if not active_locations:
        st.error("❌ No active locations available! Please create a location first in the **📍 Locations** tab.")
        return

    # Location selector
    st.markdown("#### 📍 Select Location")
    location_options = {
        f"{loc['name']} ({loc['city']}, {loc['country']})": loc['id']
        for loc in active_locations
    }
    selected_location_label = st.selectbox(
        "Location",
        list(location_options.keys()),
        key="gen_location_select"
    )
    gen_location_id = location_options[selected_location_label]

    # Find selected location details
    selected_location = next(
        (loc for loc in active_locations if loc['id'] == gen_location_id),
        None
    )
    if selected_location:
        st.caption(f"🏢 **City:** {selected_location['city']} | **Country:** {selected_location['country']}")
        if selected_location.get('venue'):
            st.caption(f"🏟️ **Venue:** {selected_location['venue']}")

    st.divider()

    # Fetch available templates from backend
    templates_success, templates_error, templates_data = get_available_templates(token)

    if not templates_success:
        st.error(f"❌ Failed to fetch available templates: {templates_error}")
        return

    available_templates = templates_data.get("available_templates", [])

    if not available_templates:
        st.error("❌ No templates available in the system")
        return

    # Extract unique specializations
    available_specs = sorted(list(set(t["specialization"] for t in available_templates)))

    st.markdown("#### 🎯 Period Configuration")

    col1, col2, col3 = st.columns(3)

    with col1:
        gen_year = st.number_input("Year", min_value=2024, max_value=2030, value=2026, step=1)

    with col2:
        gen_spec = st.selectbox("Specialization", available_specs, key="gen_spec_select")

    with col3:
        # Filter age groups based on selected specialization
        available_age_groups = sorted([
            t["age_group"] for t in available_templates
            if t["specialization"] == gen_spec
        ])
        gen_age_group = st.selectbox("Age Group", available_age_groups, key="gen_age_select")

    # Show info about selected template with DYNAMIC LABELS
    if gen_spec and gen_age_group:
        selected_template = next(
            (t for t in available_templates
             if t["specialization"] == gen_spec and t["age_group"] == gen_age_group),
            None
        )
        if selected_template:
            # ✅ INTELLIGENT LABELING based on specialization
            labels = get_period_labels(gen_spec)
            period_count_text = get_count_text(selected_template['semester_count'], gen_spec)

            st.caption(f"📊 **{selected_template['cycle_type'].title()}** cycle: {period_count_text}/year")
            st.caption(f"This will generate **{selected_template['semester_count']} {labels['plural_lower']}** for **{gen_year}/{gen_spec}/{gen_age_group}** at **{selected_location_label}**")

    st.divider()

    # Generate button with DYNAMIC LABEL
    button_text = get_generate_button_text(gen_spec) if gen_spec else "🚀 Generate Periods"
    if st.button(button_text, use_container_width=True, type="primary"):
        if not gen_location_id or not gen_spec or not gen_age_group:
            st.error("❌ Please select all required fields")
            return

        # ✅ INTELLIGENT LABELING for spinner and messages
        labels = get_period_labels(gen_spec)
        spinner_text = f"Generating {labels['plural_lower']}..."

        with st.spinner(spinner_text):
            gen_success, gen_error, result = generate_semesters(
                token,
                gen_year,
                gen_spec,
                gen_age_group,
                gen_location_id
            )

            if gen_success:
                st.success(f"✅ {result['message']}")

                # ✅ Dynamic count text
                count_text = get_count_text(result['generated_count'], gen_spec)
                st.info(f"📅 Generated {count_text} at {selected_location_label}")

                expander_label = f"📋 View Generated {labels['plural']}"
                with st.expander(expander_label):
                    for sem in result['semesters']:
                        st.markdown(f"**{sem['code']}** - {sem['name']}")
                        st.caption(f"📍 {sem['start_date']} to {sem['end_date']}")
                        st.caption(f"🎯 Theme: {sem['theme']}")
                        st.divider()
            else:
                st.error(f"❌ Failed: {gen_error}")
