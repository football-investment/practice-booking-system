"""
Matrix Cells Rendering
======================

Functions for rendering individual matrix cells with coverage status and actions.

- Render cell with status (full/partial/no coverage)
- Display coverage percentages
- Manage button for existing periods
- Generate button for missing periods
- Instructor view integration
"""

import streamlit as st
from components.period_labels import get_period_labels
from components.instructors import show_cell_instructors_modal
from .quick_actions import generate_missing_periods


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
                _render_manage_cell(token, semesters, age_group, year, coverage['existing_ids'])
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


def _render_manage_cell(token: str, semesters: list, age_group: str, year: int, existing_ids: list):
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
    from api_helpers_semesters import update_semester, delete_semester

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
