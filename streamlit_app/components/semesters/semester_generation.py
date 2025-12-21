"""
Semester/Season Generation Component - MODULAR INDIVIDUAL PERIOD SELECTION
===========================================================================
Generate individual periods/seasons based on specialization type.

✅ LFA_PLAYER: Individual season selection (PRE: month, YOUTH: quarter, AMATEUR: Fall/Spring, PRO: annual)
⚠️ INTERNSHIP/COACH/GANCUJU: Uses old bulk generator (temporary - will be modularized in Phase 2)

✅ INTELLIGENT LABELING: Automatically uses "Season" for LFA_PLAYER, "Semester" for others
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from api_helpers_semesters import (
    get_all_locations,
    get_available_templates,
    generate_semesters,
    # 🚀 NEW: Modular LFA_PLAYER generators
    generate_lfa_player_pre_season,
    generate_lfa_player_youth_season,
    generate_lfa_player_amateur_season,
    generate_lfa_player_pro_season
)
from components.period_labels import (
    get_period_label,
    get_period_labels,
    get_count_text
)


def render_semester_generation(token: str):
    """
    Render the semester/season generation interface with INDIVIDUAL PERIOD SELECTION

    - LFA_PLAYER: Select specific month/quarter/season to generate
    - INTERNSHIP/COACH/GANCUJU: Uses old bulk generator (Phase 2: will be modularized)

    ✅ INTELLIGENT LABELING: Header text adapts based on selected specialization
    """
    st.markdown("### 🚀 Generate Individual Periods")
    st.caption("Select exactly which period/season to generate")

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

    st.markdown("#### ⚽ Period Configuration")

    col1, col2, col3 = st.columns(3)

    with col1:
        current_year = datetime.now().year
        gen_year = st.number_input("Year", min_value=current_year - 2, max_value=current_year + 3, value=current_year, step=1)

    with col2:
        gen_spec = st.selectbox("Specialization", available_specs, key="gen_spec_select")

    with col3:
        # Filter age groups based on selected specialization
        available_age_groups = sorted([
            t["age_group"] for t in available_templates
            if t["specialization"] == gen_spec
        ])
        gen_age_group = st.selectbox("Age Group", available_age_groups, key="gen_age_select")

    st.divider()

    # ============================================================================
    # 🚀 NEW: MODULAR LFA_PLAYER SEASON GENERATORS (Individual Selection)
    # ============================================================================

    if gen_spec == "LFA_PLAYER":
        st.markdown("#### 🎯 Select Specific Period to Generate")

        labels = get_period_labels(gen_spec)
        period_label = labels['singular']
        period_label_lower = labels['singular_lower']

        # PRE: 12 monthly seasons
        if gen_age_group == "PRE":
            months = {
                1: "January", 2: "February", 3: "March", 4: "April",
                5: "May", 6: "June", 7: "July", 8: "August",
                9: "September", 10: "October", 11: "November", 12: "December"
            }
            selected_month = st.selectbox(
                f"Select Month (generates 1 {period_label_lower})",
                list(months.keys()),
                format_func=lambda x: f"M{x:02d} - {months[x]}"
            )

            st.caption(f"📊 This will generate **{period_label} M{selected_month:02d}** for **{gen_year}/LFA_PLAYER/PRE** at **{selected_location_label}**")

            if st.button(f"🚀 Generate {period_label} M{selected_month:02d}", type="primary", use_container_width=True):
                with st.spinner(f"Generating {period_label_lower}..."):
                    success, error, result = generate_lfa_player_pre_season(
                        token, gen_year, selected_month, gen_location_id
                    )

                    if success:
                        st.success(f"✅ {result['message']}")
                        with st.expander(f"📋 View Generated {period_label}"):
                            period = result['period']
                            st.markdown(f"**Code:** {period['code']}")
                            st.markdown(f"**Name:** {period['name']}")
                            st.markdown(f"**Dates:** {period['start_date']} to {period['end_date']}")
                            st.markdown(f"**Theme:** {period['theme']}")
                            st.caption(f"**Focus:** {period['focus_description']}")
                    else:
                        st.error(f"❌ Failed: {error}")

        # YOUTH: 4 quarterly seasons
        elif gen_age_group == "YOUTH":
            quarters = {
                1: "Q1 (Jan-Mar)",
                2: "Q2 (Apr-Jun)",
                3: "Q3 (Jul-Sep)",
                4: "Q4 (Oct-Dec)"
            }
            selected_quarter = st.selectbox(
                f"Select Quarter (generates 1 {period_label_lower})",
                list(quarters.keys()),
                format_func=lambda x: quarters[x]
            )

            st.caption(f"📊 This will generate **{period_label} Q{selected_quarter}** for **{gen_year}/LFA_PLAYER/YOUTH** at **{selected_location_label}**")

            if st.button(f"🚀 Generate {period_label} Q{selected_quarter}", type="primary", use_container_width=True):
                with st.spinner(f"Generating {period_label_lower}..."):
                    success, error, result = generate_lfa_player_youth_season(
                        token, gen_year, selected_quarter, gen_location_id
                    )

                    if success:
                        st.success(f"✅ {result['message']}")
                        with st.expander(f"📋 View Generated {period_label}"):
                            period = result['period']
                            st.markdown(f"**Code:** {period['code']}")
                            st.markdown(f"**Name:** {period['name']}")
                            st.markdown(f"**Dates:** {period['start_date']} to {period['end_date']}")
                            st.markdown(f"**Theme:** {period['theme']}")
                            st.caption(f"**Focus:** {period['focus_description']}")
                    else:
                        st.error(f"❌ Failed: {error}")

        # AMATEUR: 1 annual season (Jul-Jun)
        elif gen_age_group == "AMATEUR":
            st.caption(f"📊 This will generate **1 annual {period_label_lower}** for **{gen_year}/{gen_year+1} LFA_PLAYER/AMATEUR** (Jul {gen_year} - Jun {gen_year+1}) at **{selected_location_label}**")

            if st.button(f"🚀 Generate Annual {period_label}", type="primary", use_container_width=True):
                with st.spinner(f"Generating {period_label_lower}..."):
                    success, error, result = generate_lfa_player_amateur_season(
                        token, gen_year, gen_location_id
                    )

                    if success:
                        st.success(f"✅ {result['message']}")
                        with st.expander(f"📋 View Generated {period_label}"):
                            period = result['period']
                            st.markdown(f"**Code:** {period['code']}")
                            st.markdown(f"**Name:** {period['name']}")
                            st.markdown(f"**Dates:** {period['start_date']} to {period['end_date']}")
                            st.markdown(f"**Theme:** {period['theme']}")
                            st.caption(f"**Focus:** {period['focus_description']}")
                    else:
                        st.error(f"❌ Failed: {error}")

        # PRO: 1 annual season
        elif gen_age_group == "PRO":
            st.caption(f"📊 This will generate **1 annual {period_label_lower}** for **{gen_year}/LFA_PLAYER/PRO** (Jul {gen_year} - Jun {gen_year+1}) at **{selected_location_label}**")

            if st.button(f"🚀 Generate Annual {period_label}", type="primary", use_container_width=True):
                with st.spinner(f"Generating {period_label_lower}..."):
                    success, error, result = generate_lfa_player_pro_season(
                        token, gen_year, gen_location_id
                    )

                    if success:
                        st.success(f"✅ {result['message']}")
                        with st.expander(f"📋 View Generated {period_label}"):
                            period = result['period']
                            st.markdown(f"**Code:** {period['code']}")
                            st.markdown(f"**Name:** {period['name']}")
                            st.markdown(f"**Dates:** {period['start_date']} to {period['end_date']}")
                            st.markdown(f"**Theme:** {period['theme']}")
                            st.caption(f"**Focus:** {period['focus_description']}")
                    else:
                        st.error(f"❌ Failed: {error}")

    # ============================================================================
    # ⚠️ OLD BULK GENERATOR (INTERNSHIP/COACH/GANCUJU - temporary until Phase 2)
    # ============================================================================
    else:
        st.warning("⚠️ **INTERNSHIP/COACH/GANCUJU generators will be modularized in Phase 2**")
        st.info("💡 For now, this will generate ALL periods for the selected year (bulk generation)")

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

                # Map technical cycle_type to user-friendly label
                cycle_type_map = {
                    "monthly": "Monthly",
                    "quarterly": "Quarterly",
                    "semi-annual": "Semi-Annual",
                    "annual": "Annual"
                }
                cycle_display = cycle_type_map.get(selected_template['cycle_type'], selected_template['cycle_type'].title())

                st.caption(f"📊 **{cycle_display}** cycle: {period_count_text}/year")
                st.caption(f"This will generate **{selected_template['semester_count']} {labels['plural_lower']}** for **{gen_year}/{gen_spec}/{gen_age_group}** at **{selected_location_label}**")

        st.divider()

        # Generate button with DYNAMIC LABEL
        labels = get_period_labels(gen_spec)
        button_text = f"🚀 Generate {labels['plural']}"

        if st.button(button_text, use_container_width=True, type="primary"):
            if not gen_location_id or not gen_spec or not gen_age_group:
                st.error("❌ Please select all required fields")
                return

            # ✅ INTELLIGENT LABELING for spinner and messages
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
