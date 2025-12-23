"""
Smart Matrix View - Gap Detection & Quick Actions
==================================================
Combines period generation + management in a single matrix view.

Allows admin to:
- See what periods/seasons are already generated
- Identify missing periods (gaps in coverage)
- Generate missing periods with one click
- Manage existing periods inline
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
    get_all_semesters,
    generate_lfa_player_pre_season,
    generate_lfa_player_youth_season,
    generate_lfa_player_amateur_season,
    generate_lfa_player_pro_season,
    update_semester,
    delete_semester
)
from components.period_labels import get_period_labels
from components.instructors import (
    show_cell_instructors_modal,
    render_instructor_panel,
    render_master_section
)
from components.instructors.master_section import get_master_status


# ============================================================================
# GAP DETECTION HELPERS
# ============================================================================

def extract_existing_months(semesters: list, spec_type: str, year: int) -> list:
    """
    Extract which months exist for PRE in given year

    Args:
        semesters: List of all semesters
        spec_type: "LFA_PLAYER_PRE"
        year: Year to check

    Returns:
        List of existing month codes, e.g., ["M01", "M02", "M03", ..., "M08"]
    """
    existing = []
    for sem in semesters:
        if sem.get("specialization_type") == spec_type:
            code = sem.get("code", "")
            # Code format: "2025/LFA_PLAYER_PRE_M03"
            if code.startswith(f"{year}/"):
                parts = code.split("_")
                if parts:
                    month_code = parts[-1]  # Extract "M03"
                    if month_code.startswith("M") and len(month_code) == 3:
                        existing.append(month_code)
    return sorted(existing)


def extract_existing_quarters(semesters: list, spec_type: str, year: int) -> list:
    """
    Extract which quarters exist for YOUTH in given year

    Args:
        semesters: List of all semesters
        spec_type: "LFA_PLAYER_YOUTH"
        year: Year to check

    Returns:
        List of existing quarter codes, e.g., ["Q1", "Q2"]
    """
    existing = []
    for sem in semesters:
        if sem.get("specialization_type") == spec_type:
            code = sem.get("code", "")
            # Code format: "2025/LFA_PLAYER_YOUTH_Q2"
            if code.startswith(f"{year}/"):
                parts = code.split("_")
                if parts:
                    quarter_code = parts[-1]  # Extract "Q2"
                    if quarter_code.startswith("Q") and len(quarter_code) == 2:
                        existing.append(quarter_code)
    return sorted(existing)


def check_annual_exists(semesters: list, spec_type: str, year: int) -> bool:
    """
    Check if annual season exists for AMATEUR or PRO

    Args:
        semesters: List of all semesters
        spec_type: "LFA_PLAYER_AMATEUR" or "LFA_PLAYER_PRO"
        year: Year to check

    Returns:
        True if annual season exists, False otherwise
    """
    for sem in semesters:
        if sem.get("specialization_type") == spec_type:
            code = sem.get("code", "")
            # Code format: "2025/LFA_PLAYER_AMATEUR_Season" or "2025/LFA_PLAYER_PRO_Season"
            if code.startswith(f"{year}/"):
                return True
    return False


def get_existing_semester_ids(semesters: list, spec_type: str, year: int, codes: list) -> list:
    """
    Get IDs of existing semesters matching the given codes

    Args:
        semesters: List of all semesters
        spec_type: Specialization type
        year: Year to check
        codes: List of codes to match (e.g., ["M01", "M02"])

    Returns:
        List of semester IDs
    """
    ids = []
    for sem in semesters:
        if sem.get("specialization_type") == spec_type:
            code = sem.get("code", "")
            if code.startswith(f"{year}/"):
                parts = code.split("_")
                if parts:
                    period_code = parts[-1]
                    if period_code in codes:
                        ids.append(sem.get("id"))
    return ids


def calculate_coverage(semesters: list, age_group: str, year: int) -> dict:
    """
    Calculate coverage for a specific age group and year

    Args:
        semesters: List of all semesters
        age_group: "PRE", "YOUTH", "AMATEUR", or "PRO"
        year: Year to check

    Returns:
        {
            "exists": 8,      # Number of periods that exist
            "total": 12,      # Total periods expected
            "missing": 4,     # Number missing
            "missing_codes": ["M09", "M10", "M11", "M12"],  # Which ones missing
            "existing_codes": ["M01", "M02", ...],  # Which ones exist
            "existing_ids": [1, 2, 3, ...],  # IDs of existing periods
            "percentage": 66.67  # Coverage percentage
        }
    """
    spec_type = f"LFA_PLAYER_{age_group}"

    # PRE: Check for M01-M12 (12 monthly periods)
    if age_group == "PRE":
        total = 12
        existing_codes = extract_existing_months(semesters, spec_type, year)
        all_codes = [f"M{i:02d}" for i in range(1, 13)]
        missing_codes = [code for code in all_codes if code not in existing_codes]
        existing_ids = get_existing_semester_ids(semesters, spec_type, year, existing_codes)

    # YOUTH: Check for Q1-Q4 (4 quarterly periods)
    elif age_group == "YOUTH":
        total = 4
        existing_codes = extract_existing_quarters(semesters, spec_type, year)
        all_codes = [f"Q{i}" for i in range(1, 5)]
        missing_codes = [code for code in all_codes if code not in existing_codes]
        existing_ids = get_existing_semester_ids(semesters, spec_type, year, existing_codes)

    # AMATEUR/PRO: Check for annual season (1 period)
    elif age_group in ["AMATEUR", "PRO"]:
        total = 1
        exists = check_annual_exists(semesters, spec_type, year)
        existing_codes = ["Season"] if exists else []
        missing_codes = [] if exists else ["Season"]
        existing_ids = get_existing_semester_ids(semesters, spec_type, year, ["Season"]) if exists else []

    else:
        return {
            "exists": 0,
            "total": 0,
            "missing": 0,
            "missing_codes": [],
            "existing_codes": [],
            "existing_ids": [],
            "percentage": 0
        }

    exists_count = len(existing_codes)
    percentage = (exists_count / total * 100) if total > 0 else 0

    return {
        "exists": exists_count,
        "total": total,
        "missing": len(missing_codes),
        "missing_codes": missing_codes,
        "existing_codes": existing_codes,
        "existing_ids": existing_ids,
        "percentage": round(percentage, 2)
    }


# ============================================================================
# ACTION HANDLERS
# ============================================================================

def generate_missing_periods(token: str, age_group: str, year: int, location_id: int, missing_codes: list):
    """
    Generate all missing periods for a given age group and year

    Args:
        token: Auth token
        age_group: "PRE", "YOUTH", "AMATEUR", or "PRO"
        year: Year to generate for
        location_id: Location ID
        missing_codes: List of missing codes to generate

    Returns:
        Tuple of (success_count, failed_list)
    """
    success_count = 0
    failed = []

    for code in missing_codes:
        success = False
        error = None

        if age_group == "PRE":
            # Extract month from "M09" -> 9
            month = int(code[1:])
            success, error, _ = generate_lfa_player_pre_season(token, year, month, location_id)

        elif age_group == "YOUTH":
            # Extract quarter from "Q3" -> 3
            quarter = int(code[1])
            success, error, _ = generate_lfa_player_youth_season(token, year, quarter, location_id)

        elif age_group == "AMATEUR":
            success, error, _ = generate_lfa_player_amateur_season(token, year, location_id)

        elif age_group == "PRO":
            success, error, _ = generate_lfa_player_pro_season(token, year, location_id)

        if success:
            success_count += 1
        else:
            failed.append((code, error))

    return success_count, failed


def render_manage_cell(token: str, semesters: list, age_group: str, year: int, existing_ids: list):
    """
    Render management UI inside a matrix cell when user clicks [Manage]

    Shows:
    - List of all periods in that cell
    - Toggle active/inactive for each
    - Delete button (if no sessions)
    - Session count per period

    Args:
        token: Auth token
        semesters: List of all semesters
        age_group: Age group
        year: Year
        existing_ids: IDs of existing semesters for this cell
    """
    labels = get_period_labels("LFA_PLAYER")
    period_label_lower = labels['singular_lower']

    with st.expander(f"📋 Manage {year} {age_group} {labels['plural']}", expanded=True):
        # Filter semesters for this cell
        cell_semesters = [sem for sem in semesters if sem.get("id") in existing_ids]

        if not cell_semesters:
            st.info(f"No {period_label_lower}s found")
            return

        for sem in sorted(cell_semesters, key=lambda x: x.get("code", "")):
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.caption(f"**{sem.get('code')}** - {sem.get('name')}")
                st.caption(f"📅 {sem.get('start_date')} to {sem.get('end_date')}")
                st.caption(f"📊 {sem.get('total_sessions', 0)} sessions")

            with col2:
                # Toggle active/inactive
                current_status = sem.get('is_active', False)
                new_status = st.toggle(
                    "Active",
                    value=current_status,
                    key=f"toggle_{sem['id']}_{year}_{age_group}"
                )
                if new_status != current_status:
                    success, error, _ = update_semester(token, sem['id'], {"is_active": new_status})
                    if success:
                        st.success("Updated!")
                        st.rerun()
                    else:
                        st.error(f"Failed: {error}")

            with col3:
                # Delete if empty
                if sem.get('total_sessions', 0) == 0:
                    if st.button("🗑️", key=f"del_{sem['id']}_{year}_{age_group}"):
                        success, error = delete_semester(token, sem['id'])
                        if success:
                            st.success("Deleted!")
                            st.rerun()
                        else:
                            st.error(f"Failed: {error}")
                else:
                    st.caption("Has sessions")

            st.divider()


# ============================================================================
# MATRIX RENDERING
# ============================================================================

def render_matrix_cell(
    token: str,
    semesters: list,
    age_group: str,
    year: int,
    location_id: int,
    coverage: dict,
    user_role: str = "admin",
    is_master: bool = False
):
    """
    Render a single matrix cell with coverage status and actions

    Args:
        token: Auth token
        semesters: List of all semesters
        age_group: Age group
        year: Year
        location_id: Location ID
        coverage: Coverage data from calculate_coverage()
        user_role: User role (admin, instructor, etc.)
        is_master: Whether current user is master instructor
    """
    labels = get_period_labels("LFA_PLAYER")
    period_label_lower = labels['singular_lower']

    # Full Coverage (✅ Green)
    if coverage['missing'] == 0 and coverage['exists'] > 0:
        st.success(f"✅ {coverage['exists']}/{coverage['total']}")

        # Two-column layout for Manage and Instructors buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📋 Manage", key=f"manage_{age_group}_{year}", use_container_width=True):
                render_manage_cell(token, semesters, age_group, year, coverage['existing_ids'])
        with col2:
            if st.button("👥", key=f"instructors_{age_group}_{year}", use_container_width=True, help="View Instructors"):
                show_cell_instructors_modal(
                    location_id=location_id,
                    specialization="LFA_PLAYER",
                    age_group=age_group,
                    year=year,
                    token=token,
                    is_master=is_master
                )

    # Partial Coverage (⚠️ Yellow)
    elif coverage['exists'] > 0 and coverage['missing'] > 0:
        st.warning(f"⚠️ {coverage['exists']}/{coverage['total']}")

        # Two-column layout for Generate and Instructors buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"+ {coverage['missing']} More", key=f"partial_{age_group}_{year}", use_container_width=True):
                with st.spinner(f"Generating {coverage['missing']} missing {period_label_lower}s..."):
                    success_count, failed = generate_missing_periods(
                        token, age_group, year, location_id, coverage['missing_codes']
                    )

                    if success_count > 0:
                        st.success(f"✅ Generated {success_count} {period_label_lower}s!")

                    if failed:
                        st.error(f"❌ Failed to generate {len(failed)}: {', '.join([f[0] for f in failed])}")
                        for code, error in failed:
                            st.caption(f"**{code}**: {error}")

                    st.rerun()
        with col2:
            if st.button("👥", key=f"instructors_partial_{age_group}_{year}", use_container_width=True, help="View Instructors"):
                show_cell_instructors_modal(
                    location_id=location_id,
                    specialization="LFA_PLAYER",
                    age_group=age_group,
                    year=year,
                    token=token,
                    is_master=is_master
                )

    # No Coverage (❌ Red)
    else:
        st.error(f"❌ 0/{coverage['total']}")

        # Two-column layout for Generate and Instructors buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("+ Generate", key=f"gen_{age_group}_{year}", use_container_width=True):
                with st.spinner(f"Generating all {coverage['total']} {period_label_lower}s..."):
                    all_codes = coverage['missing_codes']
                    success_count, failed = generate_missing_periods(
                        token, age_group, year, location_id, all_codes
                    )

                    if success_count > 0:
                        st.success(f"✅ Generated {success_count}/{coverage['total']} {period_label_lower}s!")

                    if failed:
                        st.error(f"❌ Failed to generate {len(failed)}: {', '.join([f[0] for f in failed])}")
                        for code, error in failed:
                            st.caption(f"**{code}**: {error}")

                    st.rerun()
        with col2:
            if st.button("👥", key=f"instructors_none_{age_group}_{year}", use_container_width=True, help="View Instructors"):
                show_cell_instructors_modal(
                    location_id=location_id,
                    specialization="LFA_PLAYER",
                    age_group=age_group,
                    year=year,
                    token=token,
                    is_master=is_master
                )


# ============================================================================
# MAIN RENDER FUNCTION
# ============================================================================

def render_smart_matrix(token: str, user_role: str = "admin"):
    """
    Render the Smart Matrix view with gap detection

    Allows admin to:
    - See coverage matrix (age groups × years)
    - Identify gaps in coverage
    - Generate missing periods
    - Manage existing periods
    - View and manage instructors

    Args:
        token: Auth token
        user_role: User role (admin, instructor, etc.) - defaults to admin for backward compatibility
    """
    st.markdown("### 📊 Smart Matrix - Coverage & Gap Detection")
    st.caption("Unified view combining generation and management")

    # ========================================================================
    # STEP 1: Location Selection
    # ========================================================================

    st.markdown("#### 📍 Select Location")

    success, error, all_locations = get_all_locations(token, include_inactive=False)

    if not success:
        st.error(f"❌ Failed to fetch locations: {error}")
        return

    active_locations = [loc for loc in all_locations if loc.get('is_active', False)]

    if not active_locations:
        st.error("❌ No active locations available! Please create a location first in the **📍 Locations** tab.")
        return

    location_options = {
        f"{loc['name']} ({loc['city']}, {loc['country']})": loc['id']
        for loc in active_locations
    }
    selected_location_label = st.selectbox(
        "Location",
        list(location_options.keys()),
        key="matrix_location_select"
    )
    selected_location_id = location_options[selected_location_label]

    # Show location details
    selected_location = next(
        (loc for loc in active_locations if loc['id'] == selected_location_id),
        None
    )
    if selected_location:
        st.caption(f"🏢 **City:** {selected_location['city']} | **Country:** {selected_location['country']}")
        if selected_location.get('venue'):
            st.caption(f"🏟️ **Venue:** {selected_location['venue']}")

    st.divider()

    # ========================================================================
    # STEP 1.5: Master Instructor Section (Admin Only)
    # ========================================================================

    if user_role == "admin":
        # Get master status for dynamic title and expand state
        master_status = get_master_status(selected_location_id, token)

        # Dynamic expander title based on status
        if master_status == "active":
            expander_title = "🌟 Master Instructor ✅ (Active)"
            should_expand = False  # Don't expand if everything is fine
        elif master_status == "expiring":
            expander_title = "🌟 Master Instructor ⏰ (Contract Expiring Soon)"
            should_expand = True  # Expand to draw attention
        else:  # no_master
            expander_title = "🌟 Master Instructor ⚠️ (No Master Assigned)"
            should_expand = True  # Expand to encourage hiring

        with st.expander(expander_title, expanded=should_expand):
            render_master_section(selected_location_id, token)

    st.divider()

    # ========================================================================
    # STEP 2: Fetch All Semesters
    # ========================================================================

    st.markdown("#### ⚽ LFA_PLAYER Coverage Matrix")

    with st.spinner("Loading semesters..."):
        success, error, semesters_data = get_all_semesters(token)

    if not success:
        st.error(f"❌ Failed to fetch semesters: {error}")
        return

    # Extract semesters list from response data
    all_semesters = semesters_data.get("semesters", []) if semesters_data else []

    # Get selected location city for filtering
    selected_city = selected_location.get('city') if selected_location else None

    # Filter for LFA_PLAYER specialization AND selected location (by city)
    lfa_semesters = [
        sem for sem in all_semesters
        if isinstance(sem, dict)
        and sem.get("specialization_type", "").startswith("LFA_PLAYER")
        and sem.get("location_city") == selected_city
    ]

    st.caption(f"📊 Found {len(lfa_semesters)} LFA_PLAYER periods/seasons in system")

    # ========================================================================
    # STEP 3: Year Range Selection
    # ========================================================================

    current_year = datetime.now().year

    col1, col2 = st.columns(2)
    with col1:
        start_year = st.number_input(
            "Start Year",
            min_value=current_year - 5,
            max_value=current_year + 5,
            value=current_year,
            step=1,
            key="matrix_start_year"
        )
    with col2:
        end_year = st.number_input(
            "End Year",
            min_value=start_year,
            max_value=current_year + 10,
            value=start_year + 2,
            step=1,
            key="matrix_end_year"
        )

    years = list(range(start_year, end_year + 1))

    st.divider()

    # ========================================================================
    # STEP 3.5: Instructor Management Panel
    # ========================================================================

    # TODO: Determine if current user is master instructor for this location
    # For now, assume admin users are NOT master (but can view/manage)
    is_master = False  # This should come from checking user's master status

    # Render instructor panel (collapsible)
    render_instructor_panel(
        location_id=selected_location_id,
        year=start_year,  # Use start year for filtering
        token=token,
        user_role=user_role,
        is_master=is_master
    )

    st.divider()

    # ========================================================================
    # STEP 4: Render Matrix
    # ========================================================================

    st.markdown("#### 📊 Coverage Matrix")

    age_groups = ["PRE", "YOUTH", "AMATEUR", "PRO"]

    # Header row
    header_cols = st.columns([2] + [1] * len(years))
    with header_cols[0]:
        st.markdown("**Age Group**")
    for i, year in enumerate(years):
        with header_cols[i + 1]:
            st.markdown(f"**{year}**")

    st.divider()

    # Data rows
    for age_group in age_groups:
        row_cols = st.columns([2] + [1] * len(years))

        # Age group label with cycle info
        with row_cols[0]:
            if age_group == "PRE":
                st.markdown(f"**{age_group}**")
                st.caption("(Monthly: 12/year)")
            elif age_group == "YOUTH":
                st.markdown(f"**{age_group}**")
                st.caption("(Quarterly: 4/year)")
            elif age_group in ["AMATEUR", "PRO"]:
                st.markdown(f"**{age_group}**")
                st.caption("(Annual: 1/year)")

        # Year cells
        for i, year in enumerate(years):
            with row_cols[i + 1]:
                coverage = calculate_coverage(lfa_semesters, age_group, year)
                render_matrix_cell(
                    token,
                    lfa_semesters,
                    age_group,
                    year,
                    selected_location_id,
                    coverage,
                    user_role,
                    is_master
                )

        st.divider()

    # ========================================================================
    # LEGEND
    # ========================================================================

    st.markdown("#### 📖 Legend")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.success("✅ Full Coverage")
        st.caption("All periods generated")
        st.caption("Click [Manage] to edit")

    with col2:
        st.warning("⚠️ Partial Coverage")
        st.caption("Some periods missing")
        st.caption("Click [+ X More] to generate missing")

    with col3:
        st.error("❌ No Coverage")
        st.caption("No periods generated")
        st.caption("Click [+ Generate] to create all")
