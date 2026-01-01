"""
Smart Matrix View - Main Orchestrator
=====================================

Main entry point for the Smart Matrix view.
Re-exports from modular subcomponents:
- smart_matrix.gap_detection
- smart_matrix.matrix_cells
- smart_matrix.quick_actions
- smart_matrix.location_matrix
- smart_matrix.instructor_integration
"""

import streamlit as st
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from api_helpers_semesters import get_all_locations, get_all_semesters

# Import from the smart_matrix subdirectory/package
# Use try/except to handle both relative and absolute import contexts
try:
    from .smart_matrix import (
        render_coverage_matrix,
        render_legend,
        render_master_instructor_section,
        render_instructor_management_panel,
    )
except ImportError:
    # Fallback for when loaded via importlib (not as package)
    from components.semesters.smart_matrix import (
        render_coverage_matrix,
        render_legend,
        render_master_instructor_section,
        render_instructor_management_panel,
    )


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

    # Enhanced location selector with type info
    location_options = {}
    for loc in active_locations:
        loc_id = loc['id']
        loc_type = loc.get('location_type', 'PARTNER')
        type_emoji = "🏢" if loc_type == 'CENTER' else "🤝"
        label = f"{type_emoji} {loc['name']} ({loc['city']}, {loc['country']}) — {loc_type}"

        location_options[label] = {
            'id': loc_id,
            'type': loc_type,
            'city': loc['city']
        }

    selected_location_label = st.selectbox(
        "Location",
        list(location_options.keys()),
        key="matrix_location_select"
    )

    # Extract location data
    selected_location_data = location_options[selected_location_label]
    selected_location_id = selected_location_data['id']
    location_type = selected_location_data['type']

    # Show location details
    selected_location = next(
        (loc for loc in active_locations if loc['id'] == selected_location_id),
        None
    )
    if selected_location:
        st.caption(f"🏢 **City:** {selected_location['city']} | **Country:** {selected_location['country']}")
        if selected_location.get('venue'):
            st.caption(f"🏟️ **Venue:** {selected_location['venue']}")

        # ✅ ÚJ: Capability info box
        if location_type == 'CENTER':
            st.success("🏢 **CENTER Location** → Képességek: Tournament ✅ | Mini Season ✅ | Academy Season ✅")
        else:
            st.warning("🤝 **PARTNER Location** → Képességek: Tournament ✅ | Mini Season ✅ | Academy Season ❌")

    st.divider()

    # ========================================================================
    # STEP 1.5: Master Instructor Section (Admin Only)
    # ========================================================================

    if user_role == "admin":
        render_master_instructor_section(selected_location_id, token)
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
    render_instructor_management_panel(
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

    render_coverage_matrix(
        token,
        lfa_semesters,
        years,
        selected_location_id,
        user_role,
        is_master
    )

    # ========================================================================
    # LEGEND
    # ========================================================================

    st.markdown("#### 📖 Legend")
    render_legend()
