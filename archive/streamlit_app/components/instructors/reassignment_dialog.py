"""Reassignment Dialog - Immediately reassign when removing instructor"""

import streamlit as st
from typing import Optional
import sys
sys.path.append('..')
from api_helpers_instructors import deactivate_assignment, create_assignment


@st.dialog("Reassign Instructor")
def show_reassignment_dialog(
    assignment_id: int,
    instructor_name: str,
    assignment_data: dict,
    token: str
) -> None:
    """
    Dialog for reassigning when removing an instructor

    Business Rule: Cannot remove without immediate reassignment

    Workflow:
    1. Master clicks "Remove" on instructor
    2. This dialog appears
    3. Master must select replacement
    4. Old assignment deactivated, new one created
    """

    st.warning(f"Removing **{instructor_name}** requires immediate reassignment")

    st.markdown("**Current Assignment:**")
    st.caption(f"• Specialization: {assignment_data.get('specialization_type')}")
    st.caption(f"• Age Group: {assignment_data.get('age_group')}")
    st.caption(f"• Period: {assignment_data.get('time_period_start')} - {assignment_data.get('time_period_end')}")

    st.divider()

    # Reassignment form
    with st.form(key=f"reassign_form_{assignment_id}"):
        st.subheader("Select Replacement Instructor")

        # TODO: Fetch available instructors from API
        # For now, manual ID input
        new_instructor_id = st.number_input(
            "New Instructor ID",
            min_value=1,
            help="ID of replacement instructor"
        )

        st.info("Replacement instructor will inherit same period and assignment details")

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Reassign", type="primary", use_container_width=True)
        with col2:
            cancel = st.form_submit_button("Cancel", use_container_width=True)

        if cancel:
            st.rerun()

        if submit:
            try:
                # Deactivate old assignment
                deactivate_assignment(token, assignment_id)

                # Create new assignment
                create_assignment(
                    token=token,
                    location_id=assignment_data['location_id'],
                    instructor_id=int(new_instructor_id),
                    specialization_type=assignment_data['specialization_type'],
                    age_group=assignment_data['age_group'],
                    year=assignment_data['year'],
                    time_period_start=assignment_data['time_period_start'],
                    time_period_end=assignment_data['time_period_end'],
                    is_master=False
                )

                st.success(f"Reassigned successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error reassigning: {e}")
