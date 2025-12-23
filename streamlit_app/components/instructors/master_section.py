"""Master Instructor Section - Admin view of location master"""

import streamlit as st
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List
import sys
sys.path.append('..')
from api_helpers_instructors import (
    get_master_instructor_by_location,
    create_master_instructor,
    terminate_master_instructor,
    get_available_instructors
)


def render_master_section(location_id: int, token: str) -> None:
    """
    Render master instructor card for a location (Admin only)

    Shows:
    - Current master (if exists) with enhanced details
    - Hire button (if no master) with improved form
    - Terminate button (if master exists)
    - Contract expiration warnings
    """

    st.subheader("Master Instructor")

    # Fetch current master
    try:
        master = get_master_instructor_by_location(token, location_id)
    except Exception as e:
        st.error(f"Error loading master instructor: {e}")
        return

    if master:
        _render_master_card(master, token)
    else:
        _render_no_master_state(location_id, token)


def _render_master_card(master: Dict[str, Any], token: str) -> None:
    """Render existing master instructor card with enhanced details"""

    # Parse contract dates
    contract_start_str = master.get('contract_start', '')[:10]
    contract_end_str = master.get('contract_end', '')[:10]

    try:
        contract_end = datetime.strptime(contract_end_str, '%Y-%m-%d').date()
        days_until_expiry = (contract_end - date.today()).days
    except:
        days_until_expiry = None

    # Status banner
    if master.get('is_active'):
        if days_until_expiry is not None and days_until_expiry < 30:
            st.warning(f"⏰ Contract expiring in {days_until_expiry} days!")
        else:
            st.success("✅ Active Master Instructor")
    else:
        st.info("⚪ Inactive Master Instructor")

    # Master details
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown(f"### {master.get('instructor_name', 'Unknown')}")
        st.caption(f"📧 {master.get('instructor_email', 'N/A')}")
        st.caption(f"📅 Contract: {contract_start_str} → {contract_end_str}")

        if days_until_expiry is not None:
            if days_until_expiry > 0:
                st.caption(f"⏳ {days_until_expiry} days remaining")
            else:
                st.caption(f"❌ Contract expired {abs(days_until_expiry)} days ago")

    with col2:
        if master.get('is_active'):
            if st.button("🔴 Terminate", key=f"terminate_master_{master['id']}", type="secondary", use_container_width=True):
                if st.session_state.get(f"confirm_terminate_{master['id']}", False):
                    _terminate_master(master['id'], token)
                else:
                    st.session_state[f"confirm_terminate_{master['id']}"] = True
                    st.rerun()

            # Confirmation message
            if st.session_state.get(f"confirm_terminate_{master['id']}", False):
                st.warning("⚠️ Click again to confirm")


def _render_no_master_state(location_id: int, token: str) -> None:
    """Render state when no master instructor exists"""

    # Call-to-action banner
    st.info("⚠️ **No master instructor assigned to this location.**\n\nA master instructor is required to manage semesters, post positions, and hire assistant instructors.")

    # Show hire form directly (not in expander)
    st.divider()
    _show_hire_master_form(location_id, token)


def _show_hire_master_form(location_id: int, token: str) -> None:
    """Enhanced form for hiring a new master instructor"""

    st.markdown("### Hire Master Instructor")

    # Fetch available instructors
    try:
        instructors = get_available_instructors(token)
    except Exception as e:
        st.error(f"Error loading instructors: {e}")
        return

    if not instructors:
        st.warning("⚠️ No instructors available. Please create instructor accounts first.")
        return

    with st.form(key=f"hire_master_form_{location_id}"):

        # Instructor selection dropdown
        instructor_options = {
            f"{inst.get('name', 'Unknown')} ({inst.get('email', 'N/A')})": inst.get('id')
            for inst in instructors
        }

        if not instructor_options:
            st.warning("No instructors available to hire.")
            st.form_submit_button("Hire", disabled=True)
            return

        selected_instructor_label = st.selectbox(
            "Select Instructor",
            options=list(instructor_options.keys()),
            help="Choose an instructor to hire as master for this location"
        )

        instructor_id = instructor_options[selected_instructor_label]

        # Show instructor preview
        selected_inst = next((i for i in instructors if i.get('id') == instructor_id), None)
        if selected_inst:
            with st.expander("👤 Instructor Details", expanded=False):
                st.caption(f"**Name:** {selected_inst.get('name', 'N/A')}")
                st.caption(f"**Email:** {selected_inst.get('email', 'N/A')}")
                st.caption(f"**ID:** {selected_inst.get('id', 'N/A')}")

        st.divider()

        # Contract dates
        col1, col2 = st.columns(2)

        with col1:
            contract_start = st.date_input(
                "Contract Start Date",
                value=date.today(),
                min_value=date.today(),
                help="Contract start date (cannot be in the past)"
            )

        with col2:
            # Default: 1 year from start
            default_end = date.today() + timedelta(days=365)
            contract_end = st.date_input(
                "Contract End Date",
                value=default_end,
                min_value=date.today() + timedelta(days=1),
                help="Contract end date (must be after start date)"
            )

        # Validation warnings
        if contract_end <= contract_start:
            st.error("❌ Contract end date must be after start date")

        contract_duration_days = (contract_end - contract_start).days
        if contract_duration_days < 365:
            st.warning(f"⚠️ Contract duration is only {contract_duration_days} days (< 1 year)")

        # Submit button
        submit = st.form_submit_button("✅ Hire Master Instructor", type="primary", use_container_width=True)

        if submit:
            # Validate dates
            if contract_end <= contract_start:
                st.error("❌ Invalid dates: Contract end must be after start")
                return

            try:
                # Convert dates to ISO format
                start_iso = datetime.combine(contract_start, datetime.min.time()).isoformat()
                end_iso = datetime.combine(contract_end, datetime.min.time()).isoformat()

                create_master_instructor(
                    token=token,
                    location_id=location_id,
                    instructor_id=int(instructor_id),
                    contract_start=start_iso,
                    contract_end=end_iso
                )

                st.success(f"✅ Master instructor hired successfully!")
                st.balloons()
                st.rerun()

            except Exception as e:
                error_msg = str(e)

                # Parse API errors for user-friendly messages
                if "already has an active master" in error_msg.lower():
                    st.error("❌ This location already has a master instructor. Please terminate the existing master before hiring a new one.")
                elif "invalid instructor_id" in error_msg.lower() or "not found" in error_msg.lower():
                    st.error("❌ Instructor not found. Please select a valid instructor from the dropdown.")
                elif "contract dates invalid" in error_msg.lower() or "end date must be after start" in error_msg.lower():
                    st.error("❌ Contract end date must be after start date.")
                else:
                    st.error(f"❌ Error hiring master: {error_msg}")


def _terminate_master(master_id: int, token: str) -> None:
    """Terminate master instructor contract"""

    try:
        terminate_master_instructor(token, master_id)
        st.success("✅ Master instructor terminated successfully")

        # Clear confirmation state
        if f"confirm_terminate_{master_id}" in st.session_state:
            del st.session_state[f"confirm_terminate_{master_id}"]

        st.rerun()
    except Exception as e:
        st.error(f"❌ Error terminating master: {e}")


def get_master_status(location_id: int, token: str) -> str:
    """
    Get master instructor status for a location
    Used by Smart Matrix to show status badge

    Returns:
    - "active" - has active master
    - "expiring" - has master but contract < 30 days
    - "no_master" - no master assigned
    """
    try:
        master = get_master_instructor_by_location(token, location_id)

        if not master or not master.get('is_active'):
            return "no_master"

        # Check contract expiration
        contract_end_str = master.get('contract_end', '')[:10]
        try:
            contract_end = datetime.strptime(contract_end_str, '%Y-%m-%d').date()
            days_until_expiry = (contract_end - date.today()).days

            if days_until_expiry < 30:
                return "expiring"
        except:
            pass

        return "active"

    except:
        return "no_master"
