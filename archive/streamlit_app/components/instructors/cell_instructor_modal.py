"""Cell Instructor Modal - Shows instructors for a specific matrix cell"""

import streamlit as st
from typing import Dict, Any
import sys
sys.path.append('..')
from api_helpers_instructors import get_matrix_cell_instructors, deactivate_assignment


@st.dialog("Cell Instructors")
def show_cell_instructors_modal(
    location_id: int,
    specialization: str,
    age_group: str,
    year: int,
    token: str,
    is_master: bool = False
) -> None:
    """
    Modal showing all instructors assigned to a specific cell

    Displays:
    - List of instructors with period coverage
    - Co-instructor flags
    - Coverage percentage
    - Remove button (for master)
    """

    try:
        cell_data = get_matrix_cell_instructors(
            token=token,
            location_id=location_id,
            specialization=specialization,
            age_group=age_group,
            year=year
        )
    except Exception as e:
        st.error(f"Error loading instructors: {e}")
        return

    st.subheader(f"{specialization} / {age_group} / {year}")

    instructors = cell_data.get('instructors', [])

    if not instructors:
        st.info("No instructors assigned to this cell")
        return

    # Coverage info
    coverage = cell_data.get('coverage_percentage', 0)
    total_months = cell_data.get('total_coverage_months', 0)
    required_months = cell_data.get('required_months', 12)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Coverage", f"{coverage:.0f}%")
    with col2:
        st.metric("Months", f"{total_months}/{required_months}")

    st.divider()

    # List instructors
    for instructor in instructors:
        col1, col2, col3 = st.columns([3, 2, 1])

        with col1:
            st.markdown(f"**{instructor.get('instructor_name', 'Unknown')}**")
            if instructor.get('is_master'):
                st.caption("🌟 Master Instructor")
            if instructor.get('is_co_instructor'):
                st.caption("👥 Co-Instructor")

        with col2:
            st.caption(f"Period: {instructor.get('period_coverage', 'N/A')}")

        with col3:
            if is_master and not instructor.get('is_master'):
                # Master can remove assistant instructors
                if st.button("Remove", key=f"remove_{instructor['instructor_id']}", type="secondary"):
                    # Show reassignment dialog
                    from .reassignment_dialog import show_reassignment_dialog
                    show_reassignment_dialog(
                        assignment_id=instructor.get('assignment_id'),  # Need to pass this from API
                        instructor_name=instructor.get('instructor_name'),
                        token=token
                    )

        st.divider()

    # Close button
    if st.button("Close", type="primary"):
        st.rerun()
