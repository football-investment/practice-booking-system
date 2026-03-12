"""Instructor Panel - Collapsible panel in Smart Matrix for instructor management"""

import streamlit as st
from typing import Optional
import sys
sys.path.append('..')
from api_helpers_instructors import (
    get_my_positions,
    get_job_board,
    get_my_applications,
    apply_to_position
)
from .position_posting_modal import show_position_posting_modal
from .application_review import render_application_review


def render_instructor_panel(
    location_id: int,
    year: int,
    token: str,
    user_role: str,
    is_master: bool = False
) -> None:
    """
    Collapsible instructor management panel

    Shows different content based on role:
    - Admin: Master management (handled separately)
    - Master: My Positions + Applications
    - All instructors: Job Board + My Applications
    """

    with st.expander("Instructor Management", expanded=False):
        if is_master:
            _render_master_view(location_id, year, token)
        else:
            _render_instructor_view(location_id, year, token)


def _render_master_view(location_id: int, year: int, token: str) -> None:
    """Master instructor view: Manage positions and review applications"""

    tab1, tab2 = st.tabs(["My Positions", "Job Board"])

    with tab1:
        st.subheader("My Posted Positions")

        if st.button("Post New Position", type="primary"):
            show_position_posting_modal(location_id, token)

        # Fetch positions
        try:
            response = get_my_positions(token, location_id)
            positions = response.get('positions', [])
        except Exception as e:
            st.error(f"Error loading positions: {e}")
            return

        if not positions:
            st.info("No positions posted yet")
            return

        # Display positions
        for pos in positions:
            with st.expander(
                f"{pos['specialization_type']}/{pos['age_group']} {pos['year']} - {pos['status']}"
            ):
                st.markdown(f"**Period:** {pos['time_period_start']} - {pos['time_period_end']}")
                st.markdown(f"**Priority:** {pos['priority']}/10")
                st.markdown(f"**Deadline:** {pos['application_deadline'][:10]}")
                st.markdown("**Description:**")
                st.write(pos['description'])

                st.divider()

                # Show applications
                render_application_review(pos['id'], pos, token)

    with tab2:
        _render_job_board(location_id, year, token)


def _render_instructor_view(location_id: int, year: int, token: str) -> None:
    """Regular instructor view: Browse jobs and manage applications"""

    tab1, tab2 = st.tabs(["Job Board", "My Applications"])

    with tab1:
        _render_job_board(location_id, year, token)

    with tab2:
        _render_my_applications(token)


def _render_job_board(location_id: int, year: int, token: str) -> None:
    """Job board - all open positions"""

    st.subheader("Available Positions")

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        spec_filter = st.selectbox(
            "Specialization",
            options=["All", "LFA_PLAYER", "INTERNSHIP", "GANCUJU", "COACH"],
            index=0
        )
    with col2:
        age_filter = st.selectbox(
            "Age Group",
            options=["All", "PRE", "YOUTH", "AMATEUR", "PRO"],
            index=0
        )

    # Fetch positions
    try:
        response = get_job_board(
            token=token,
            location_id=location_id,
            specialization=None if spec_filter == "All" else spec_filter,
            age_group=None if age_filter == "All" else age_filter,
            year=year
        )
        positions = response.get('positions', [])
    except Exception as e:
        st.error(f"Error loading job board: {e}")
        return

    if not positions:
        st.info("No open positions match your filters")
        return

    # Display positions
    for pos in positions:
        with st.expander(
            f"{pos['specialization_type']}/{pos['age_group']} {pos['year']} - Priority {pos['priority']}/10"
        ):
            st.markdown(f"**Location:** {pos.get('location_name', 'N/A')}")
            st.markdown(f"**Period:** {pos['period']}")
            st.markdown(f"**Deadline:** {pos['application_deadline'][:10]}")
            st.markdown(f"**Posted by:** {pos['posted_by_name']}")
            st.markdown("**Description:**")
            st.write(pos['description'])

            # Application status
            if pos.get('user_has_applied'):
                status = pos.get('user_application_status', 'PENDING')
                if status == 'PENDING':
                    st.info("You have applied - Pending review")
                elif status == 'ACCEPTED':
                    st.success("Application accepted!")
                elif status == 'DECLINED':
                    st.warning("Application declined")
            else:
                if st.button("Apply", key=f"apply_{pos['id']}", type="primary"):
                    _show_apply_modal(pos, token)


def _show_apply_modal(position: dict, token: str) -> None:
    """Modal for applying to a position"""

    with st.form(key=f"apply_form_{position['id']}"):
        st.subheader("Apply to Position")

        application_message = st.text_area(
            "Cover Letter / Application Message",
            height=200,
            placeholder="Explain why you're a good fit for this position...",
            help="Minimum 50 characters"
        )

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Submit Application", type="primary", use_container_width=True)
        with col2:
            cancel = st.form_submit_button("Cancel", use_container_width=True)

        if cancel:
            st.rerun()

        if submit:
            if len(application_message) < 50:
                st.error("Application message must be at least 50 characters")
                return

            try:
                apply_to_position(token, position['id'], application_message)
                st.success("Application submitted!")
                st.rerun()
            except Exception as e:
                st.error(f"Error submitting application: {e}")


def _render_my_applications(token: str) -> None:
    """Show instructor's own applications"""

    st.subheader("My Applications")

    try:
        response = get_my_applications(token)
        applications = response.get('applications', [])
    except Exception as e:
        st.error(f"Error loading applications: {e}")
        return

    if not applications:
        st.info("You haven't applied to any positions yet")
        return

    # Group by status
    tab1, tab2, tab3 = st.tabs(["Pending", "Accepted", "Declined"])

    with tab1:
        pending = [a for a in applications if a['status'] == 'PENDING']
        _display_application_list(pending)

    with tab2:
        accepted = [a for a in applications if a['status'] == 'ACCEPTED']
        _display_application_list(accepted)

    with tab3:
        declined = [a for a in applications if a['status'] == 'DECLINED']
        _display_application_list(declined)


def _display_application_list(applications: list) -> None:
    """Display list of applications"""

    if not applications:
        st.info("No applications in this category")
        return

    for app in applications:
        with st.expander(f"{app.get('position_title', 'Position')} - {app.get('created_at', '')[:10]}"):
            st.markdown(f"**Status:** {app['status']}")
            st.markdown(f"**Applied:** {app.get('created_at', '')[:10]}")
            if app.get('reviewed_at'):
                st.markdown(f"**Reviewed:** {app['reviewed_at'][:10]}")
            st.markdown("**Your Application:**")
            st.write(app.get('application_message', ''))
