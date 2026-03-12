"""Pathway A Component - Direct Hire Form"""

import streamlit as st
from datetime import datetime, timedelta, date
from typing import Dict, Any, List
import json
import sys
sys.path.append('..')
from api_helpers_instructors import (
    get_available_instructors,
    create_direct_hire_offer
)


def render_direct_hire_tab(location_id: int, token: str) -> None:
    """
    PATHWAY A: Direct Hire - Admin directly invites specific instructor

    Allows admin to:
    - Select instructor from available pool
    - View license information and validation
    - Set contract dates
    - Configure offer deadline
    - Override availability checks if needed
    - Send offer

    Args:
        location_id: ID of the location
        token: Authentication token
    """

    st.markdown("### Direct Hire Master Instructor")
    st.caption("Directly invite a specific instructor to become master at this location")

    # Fetch available instructors
    try:
        instructors = get_available_instructors(token)
    except Exception as e:
        st.error(f"Error loading instructors: {e}")
        return

    if not instructors:
        st.warning("No instructors available. Please create instructor accounts first.")
        return

    with st.form(key=f"direct_hire_form_{location_id}"):

        # Instructor selection
        instructor_options = {
            f"{inst.get('name', 'Unknown')} ({inst.get('email', 'N/A')})": inst.get('id')
            for inst in instructors
        }

        if not instructor_options:
            st.warning("No instructors available to hire.")
            st.form_submit_button("Send Offer", disabled=True)
            return

        selected_instructor_label = st.selectbox(
            "Select Instructor",
            options=list(instructor_options.keys()),
            help="Choose an instructor to send master offer"
        )

        instructor_id = instructor_options[selected_instructor_label]

        # Show instructor preview with license validation
        selected_inst = next((i for i in instructors if i.get('id') == instructor_id), None)
        if selected_inst:
            _render_instructor_details_and_validation(selected_inst)

        st.divider()

        # Contract dates
        col1, col2 = st.columns(2)

        with col1:
            contract_start = st.date_input(
                "Contract Start Date",
                value=date.today() + timedelta(days=30),
                min_value=date.today(),
                help="Contract start date"
            )

        with col2:
            default_end = contract_start + timedelta(days=365)
            contract_end = st.date_input(
                "Contract End Date",
                value=default_end,
                min_value=contract_start + timedelta(days=1),
                help="Contract end date"
            )

        # Offer deadline
        offer_deadline_days = st.slider(
            "Offer Valid For (days)",
            min_value=1,
            max_value=90,
            value=14,
            help="Number of days instructor has to accept/decline"
        )

        st.caption(f"Offer deadline: {(date.today() + timedelta(days=offer_deadline_days)).strftime('%Y-%m-%d')}")

        # Validation warnings
        if contract_end <= contract_start:
            st.error("Contract end date must be after start date")

        contract_duration_days = (contract_end - contract_start).days
        if contract_duration_days < 365:
            st.warning(f"Contract duration is only {contract_duration_days} days (< 1 year)")

        # Availability override checkbox
        override_availability = st.checkbox(
            "Override availability warnings",
            value=False,
            help="Send offer even if instructor's availability doesn't match contract period"
        )

        # Submit button
        submit = st.form_submit_button("Send Offer", type="primary", use_container_width=True)

        if submit:
            _handle_direct_hire_submission(
                location_id=location_id,
                instructor_id=int(instructor_id),
                selected_instructor_label=selected_instructor_label,
                contract_start=contract_start,
                contract_end=contract_end,
                offer_deadline_days=offer_deadline_days,
                override_availability=override_availability,
                token=token
            )


def _render_instructor_details_and_validation(instructor: Dict[str, Any]) -> None:
    """
    Render instructor details with license validation for master role

    Args:
        instructor: Instructor data dictionary
    """
    with st.expander("Instructor Details & License Check", expanded=True):
        st.caption(f"**Name:** {instructor.get('name', 'N/A')}")
        st.caption(f"**Email:** {instructor.get('email', 'N/A')}")

        # License Information
        specialization = instructor.get('specialization')
        current_level = instructor.get('current_level', 1)

        if specialization:
            st.divider()
            st.markdown("**License Information**")

            # Map specialization to display name
            spec_names = {
                "LFA_COACH": "LFA Coach",
                "LFA_FOOTBALL_PLAYER": "LFA Football Player",
                "GANCUJU_PLAYER": "GanCuju Player",
                "INTERNSHIP": "Internship"
            }
            spec_display = spec_names.get(specialization, specialization)
            st.caption(f"License: **{spec_display}** (Level {current_level})")

            # Validate for Master Instructor role
            if specialization != "LFA_COACH":
                st.error("**INCOMPATIBLE**: Only LFA Coach license holders can be Master Instructors")
                st.caption("This instructor needs an LFA Coach license to be hired as Master")
            elif current_level in [1, 3, 5, 7]:
                # Assistant Coach levels
                st.warning(f"**INCOMPATIBLE**: Level {current_level} is Assistant Coach")
                st.caption("Master Instructors must be Head Coach (Level 2, 4, 6, or 8)")
                st.caption(f"Recommendation: Hire a Level {current_level + 1}+ instructor")
            elif current_level in [2, 4, 6, 8]:
                # Head Coach levels - show qualified age groups
                age_group_qualified = {
                    2: ("PRE Football", ["PRE"]),
                    4: ("YOUTH Football", ["PRE", "YOUTH"]),
                    6: ("AMATEUR Football", ["PRE", "YOUTH", "AMATEUR"]),
                    8: ("PRO Football", ["PRE", "YOUTH", "AMATEUR", "PRO"])
                }

                age_label, can_teach = age_group_qualified.get(current_level, ("Unknown", []))
                st.success(f"**Head Coach Level {current_level}** - Qualified for {age_label}")
                st.caption(f"Can teach: {', '.join(can_teach)} semesters")

                # Warning about location semester compatibility
                st.info("**Note**: Ensure this location's semesters match the instructor's qualified age groups. The system will validate compatibility before sending the offer.")
            else:
                st.warning(f"Unknown license level: {current_level}")
        else:
            st.warning("No license information available for this instructor")


def _handle_direct_hire_submission(
    location_id: int,
    instructor_id: int,
    selected_instructor_label: str,
    contract_start: date,
    contract_end: date,
    offer_deadline_days: int,
    override_availability: bool,
    token: str
) -> None:
    """
    Handle form submission for direct hire offer

    Args:
        location_id: Location ID
        instructor_id: Instructor ID
        selected_instructor_label: Display label for instructor
        contract_start: Contract start date
        contract_end: Contract end date
        offer_deadline_days: Days valid for offer
        override_availability: Whether to override availability checks
        token: Authentication token
    """
    # Validate dates
    if contract_end <= contract_start:
        st.error("Invalid dates: Contract end must be after start")
        return

    try:
        # Convert dates to ISO format
        start_iso = datetime.combine(contract_start, datetime.min.time()).isoformat()
        end_iso = datetime.combine(contract_end, datetime.min.time()).isoformat()

        # Create direct hire offer
        offer = create_direct_hire_offer(
            token=token,
            location_id=location_id,
            instructor_id=instructor_id,
            contract_start=start_iso,
            contract_end=end_iso,
            offer_deadline_days=offer_deadline_days,
            override_availability=override_availability
        )

        # Show success with availability warnings
        st.success(f"Offer sent to {selected_instructor_label}!")

        match_score = offer.get('availability_match_score', 100)
        if match_score < 100:
            st.warning(f"Availability Match: {match_score}%")
            warnings = offer.get('availability_warnings', [])
            for warning in warnings:
                st.caption(f"• {warning}")

        st.info("Instructor will see this offer in their dashboard and can accept or decline.")
        st.balloons()
        st.rerun()

    except Exception as e:
        _handle_direct_hire_error(str(e), override_availability)


def _handle_direct_hire_error(error_msg: str, override_availability: bool) -> None:
    """
    Parse and display specific error messages for direct hire

    Args:
        error_msg: Error message from API
        override_availability: Whether availability override was attempted
    """
    if "already has an active master" in error_msg.lower():
        st.error("This location already has a master instructor.")
    elif "license incompatibility" in error_msg.lower():
        st.error("**License Incompatibility Detected**")
        st.markdown("The instructor's license does not qualify them to teach the semesters at this location.")

        # Try to extract details from error message
        try:
            # The error message might contain JSON
            start = error_msg.find('{')
            end = error_msg.rfind('}') + 1
            if start >= 0 and end > start:
                error_detail = json.loads(error_msg[start:end])
                if isinstance(error_detail, dict):
                    st.caption(f"**Instructor License:** {error_detail.get('instructor_license', 'N/A')}")
                    st.caption(f"**Can Teach:** {', '.join(error_detail.get('can_teach', []))}")
                    incompatible = error_detail.get('incompatible_semesters', [])
                    if incompatible:
                        st.caption(f"**Incompatible Semesters:** {len(incompatible)}")
                        for sem in incompatible[:3]:  # Show first 3
                            st.caption(f"  • {sem.get('code')} ({sem.get('age_group')})")
                    st.info(f"{error_detail.get('recommendation', 'Hire an instructor with compatible license level')}")
        except:
            pass
    elif "master instructor must have lfa_coach license" in error_msg.lower():
        st.error("**Wrong License Type**")
        st.markdown("Only instructors with **LFA Coach** license can be Master Instructors.")
        st.info("LFA Player licenses do not grant teaching permissions.")
    elif "assistant coach" in error_msg.lower():
        st.error("**Assistant Coach License**")
        st.markdown("Master Instructors must be **Head Coach** (Level 2, 4, 6, or 8).")
        st.info("Assistant Coaches (Level 1, 3, 5, 7) cannot serve as Master Instructors.")
    elif "availability" in error_msg.lower() and not override_availability:
        st.error(f"{error_msg}")
        st.info("You can check 'Override availability warnings' to send the offer anyway.")
    elif "instructor_id" in error_msg.lower():
        st.error("Instructor not found.")
    else:
        st.error(f"Error sending offer: {error_msg}")
