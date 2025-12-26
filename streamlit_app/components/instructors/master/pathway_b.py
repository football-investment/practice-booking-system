"""Pathway B Component - Job Posting Interface"""

import streamlit as st
from datetime import datetime, timedelta, date
from typing import Dict, Any
import sys
sys.path.append('..')
from api_helpers_instructors import create_position, get_positions_by_location


def render_post_opening_tab(location_id: int, token: str) -> None:
    """
    PATHWAY B: Job Posting - Admin posts master opening, instructors apply

    Allows admin to:
    - Create job posting with description
    - Set contract period (year + quarters)
    - Configure application deadline
    - Set priority level
    - View existing master position postings

    Args:
        location_id: ID of the location
        token: Authentication token
    """

    st.markdown("### Post Master Instructor Opening")
    st.caption("Create a job posting that instructors can apply to")

    with st.form(key=f"post_opening_form_{location_id}"):

        st.markdown("**Position Details**")

        col1, col2 = st.columns(2)

        with col1:
            current_year = datetime.now().year
            year = st.selectbox(
                "Year",
                options=list(range(current_year, current_year + 3)),
                help="Year for the master position"
            )

        with col2:
            priority = st.slider(
                "Priority",
                min_value=1,
                max_value=10,
                value=10,
                help="Priority level (10 = highest for master positions)"
            )

        st.divider()

        st.markdown("**Contract Period**")

        col1, col2 = st.columns(2)

        with col1:
            time_period_start = st.selectbox(
                "Start Quarter",
                options=["Q1", "Q2", "Q3", "Q4"],
                help="Starting quarter (Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec)"
            )

        with col2:
            time_period_end = st.selectbox(
                "End Quarter",
                options=["Q1", "Q2", "Q3", "Q4"],
                index=3,
                help="Ending quarter"
            )

        quarter_starts = {"Q1": (1, 1), "Q2": (4, 1), "Q3": (7, 1), "Q4": (10, 1)}
        quarter_ends = {"Q1": (3, 31), "Q2": (6, 30), "Q3": (9, 30), "Q4": (12, 31)}

        start_month, start_day = quarter_starts[time_period_start]
        end_month, end_day = quarter_ends[time_period_end]

        default_contract_start = date(year, start_month, start_day)
        default_contract_end = date(year, end_month, end_day)

        col1, col2 = st.columns(2)

        with col1:
            contract_start = st.date_input(
                "Suggested Contract Start",
                value=default_contract_start,
                help="Suggested contract start date"
            )

        with col2:
            contract_end = st.date_input(
                "Suggested Contract End",
                value=default_contract_end,
                help="Suggested contract end date"
            )

        st.divider()

        st.markdown("**Job Description**")

        description = st.text_area(
            "Description",
            height=200,
            help="Describe the master instructor role, responsibilities, and requirements",
            placeholder="We are seeking an experienced Master Instructor...\n\nResponsibilities:\n- Manage training operations\n- Hire and manage assistant instructors\n- Oversee semester planning\n\nRequirements:\n- [X] years experience\n- Leadership skills\n- Available [time period]"
        )

        if description and len(description.strip()) < 10:
            st.warning("Please provide a detailed description (minimum 10 characters)")

        st.divider()

        st.markdown("**Application Deadline**")

        col1, col2 = st.columns([2, 1])

        with col1:
            default_deadline = date.today() + timedelta(days=30)
            application_deadline = st.date_input(
                "Application Deadline",
                value=default_deadline,
                min_value=date.today() + timedelta(days=1),
                help="Last day for instructors to apply"
            )

        with col2:
            days_until_deadline = (application_deadline - date.today()).days
            st.metric("Days Open", days_until_deadline)

        submit = st.form_submit_button(
            "Post Master Opening",
            type="primary",
            use_container_width=True
        )

        if submit:
            _handle_post_opening_submission(
                location_id=location_id,
                token=token,
                description=description,
                application_deadline=application_deadline,
                contract_start=contract_start,
                contract_end=contract_end,
                year=year,
                time_period_start=time_period_start,
                time_period_end=time_period_end,
                priority=priority
            )

    with st.expander("How Job Posting Works"):
        st.caption("1. Post opening with job description\n2. Instructors apply\n3. Review applications\n4. Select candidate creates OFFERED contract\n5. Instructor must accept offer")

    st.divider()

    # Show existing master positions for this location
    render_master_position_applications(location_id, token)


def _handle_post_opening_submission(
    location_id: int,
    token: str,
    description: str,
    application_deadline: date,
    contract_start: date,
    contract_end: date,
    year: int,
    time_period_start: str,
    time_period_end: str,
    priority: int
) -> None:
    """
    Handle submission of job posting form

    Args:
        location_id: Location ID
        token: Authentication token
        description: Job description text
        application_deadline: Deadline for applications
        contract_start: Contract start date
        contract_end: Contract end date
        year: Year for position
        time_period_start: Start quarter
        time_period_end: End quarter
        priority: Priority level
    """
    if not description or len(description.strip()) < 10:
        st.error("Job description is required (minimum 10 characters)")
    elif application_deadline <= date.today():
        st.error("Application deadline must be in the future")
    elif contract_end <= contract_start:
        st.error("Contract end date must be after start date")
    else:
        try:
            deadline_iso = datetime.combine(application_deadline, datetime.max.time()).isoformat()

            position = create_position(
                token=token,
                location_id=location_id,
                specialization_type="MASTER_INSTRUCTOR",
                age_group="ALL",
                year=year,
                time_period_start=time_period_start,
                time_period_end=time_period_end,
                description=f"[MASTER POSITION]\n\n{description}\n\nContract: {contract_start} to {contract_end}",
                application_deadline=deadline_iso,
                priority=priority
            )

            st.success("Master instructor opening posted!")
            st.info(f"**Position ID:** {position.get('id')}\n**Deadline:** {application_deadline.strftime('%Y-%m-%d')}\n\nInstructors can now apply. Check Application Review to see applications.")
            st.balloons()

        except Exception as e:
            error_msg = str(e)
            if "already has an active master" in error_msg.lower():
                st.error("This location already has an active master or pending offer.")
            else:
                st.error(f"Error: {error_msg}")


def render_master_position_applications(location_id: int, token: str) -> None:
    """
    Show existing master positions and their applications for this location

    Displays:
    - Active master position postings
    - Number of applications received
    - Button to review applications

    Args:
        location_id: ID of the location
        token: Authentication token
    """

    try:
        # Fetch all positions for this location
        all_positions = get_positions_by_location(token, location_id)

        # Filter master positions only
        master_positions = [
            pos for pos in all_positions
            if pos.get('description', '').startswith('[MASTER POSITION]')
        ]

        if not master_positions:
            st.info("No active master position postings yet. Create one above!")
            return

        st.markdown("### Active Master Position Postings")

        for position in master_positions:
            _render_master_position_card(position, token)

    except Exception as e:
        st.error(f"Error loading master positions: {e}")


def _render_master_position_card(position: Dict[str, Any], token: str) -> None:
    """
    Render a single master position card with applications

    Args:
        position: Position data dictionary
        token: Authentication token
    """

    from master_applications_review import render_master_applications_review

    position_id = position.get('id')
    year = position.get('year')
    time_period = f"{position.get('time_period_start')} - {position.get('time_period_end')}"
    status = position.get('status', 'UNKNOWN')
    application_deadline = position.get('application_deadline', '')[:10] if position.get('application_deadline') else 'N/A'

    # Get description without [MASTER POSITION] prefix
    full_description = position.get('description', '')
    description = full_description.replace('[MASTER POSITION]\n\n', '').split('\n\nContract:')[0]

    with st.expander(f"Master Position - {year} ({time_period}) - Status: {status}", expanded=True):
        st.markdown(f"**Year:** {year}")
        st.markdown(f"**Period:** {time_period}")
        st.markdown(f"**Application Deadline:** {application_deadline}")
        st.markdown(f"**Status:** {status}")

        # Show description
        with st.expander("Job Description", expanded=False):
            st.text(description)

        st.divider()

        # Show applications
        render_master_applications_review(position_id, token)
