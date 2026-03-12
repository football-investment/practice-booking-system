"""Application Review - Master reviews and accepts/declines applications"""

import streamlit as st
from typing import List, Dict, Any
import sys
sys.path.append('..')
from api_helpers_instructors import (
    get_applications_for_position,
    accept_application,
    decline_application,
    create_assignment
)


def render_application_review(position_id: int, position_data: Dict[str, Any], token: str) -> None:
    """
    Render application review interface for a position

    Master can:
    - View all applications
    - Accept (creates assignment)
    - Decline
    """

    st.subheader("Review Applications")
    st.caption(f"{position_data.get('specialization_type')}/{position_data.get('age_group')} {position_data.get('year')}")

    # Fetch applications
    try:
        response = get_applications_for_position(token, position_id)
        applications = response.get('applications', [])
    except Exception as e:
        st.error(f"Error loading applications: {e}")
        return

    if not applications:
        st.info("No applications yet")
        return

    # Tabs for status
    tab1, tab2, tab3 = st.tabs(["Pending", "Accepted", "Declined"])

    with tab1:
        pending = [a for a in applications if a['status'] == 'PENDING']
        _render_application_list(pending, position_data, token, show_actions=True)

    with tab2:
        accepted = [a for a in applications if a['status'] == 'ACCEPTED']
        _render_application_list(accepted, position_data, token, show_actions=False)

    with tab3:
        declined = [a for a in applications if a['status'] == 'DECLINED']
        _render_application_list(declined, position_data, token, show_actions=False)


def _render_application_list(
    applications: List[Dict[str, Any]],
    position_data: Dict[str, Any],
    token: str,
    show_actions: bool
) -> None:
    """Render list of applications"""

    if not applications:
        st.info("No applications in this category")
        return

    for app in applications:
        with st.expander(f"{app.get('applicant_name', 'Unknown')} - {app.get('created_at', '')[:10]}"):
            st.markdown(f"**Email:** {app.get('applicant_email', 'N/A')}")
            st.markdown("**Application Message:**")
            st.write(app.get('application_message', ''))

            if show_actions:
                col1, col2 = st.columns(2)

                with col1:
                    if st.button(
                        "Accept & Assign",
                        key=f"accept_{app['id']}",
                        type="primary",
                        use_container_width=True
                    ):
                        _accept_and_assign(app, position_data, token)

                with col2:
                    if st.button(
                        "Decline",
                        key=f"decline_{app['id']}",
                        type="secondary",
                        use_container_width=True
                    ):
                        _decline_application(app['id'], token)


def _accept_and_assign(app: Dict[str, Any], position_data: Dict[str, Any], token: str) -> None:
    """Accept application and create assignment"""

    try:
        # Accept application
        accept_application(token, app['id'])

        # Create assignment
        create_assignment(
            token=token,
            location_id=position_data['location_id'],
            instructor_id=app['applicant_id'],
            specialization_type=position_data['specialization_type'],
            age_group=position_data['age_group'],
            year=position_data['year'],
            time_period_start=position_data['time_period_start'],
            time_period_end=position_data['time_period_end'],
            is_master=False
        )

        st.success(f"Accepted {app.get('applicant_name')} and created assignment!")
        st.rerun()
    except Exception as e:
        st.error(f"Error accepting application: {e}")


def _decline_application(application_id: int, token: str) -> None:
    """Decline an application"""

    try:
        decline_application(token, application_id)
        st.success("Application declined")
        st.rerun()
    except Exception as e:
        st.error(f"Error declining application: {e}")
