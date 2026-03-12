"""Master Instructor Applications Review - Admin View

Admin reviews applications for master instructor positions and hires selected candidates.

CRITICAL: Application acceptance ≠ Contract acceptance!
- Admin selects candidate → Creates OFFERED contract
- Instructor must still ACCEPT the contract offer
"""

import streamlit as st
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
import sys
sys.path.append('..')
from api_helpers_instructors import (
    get_applications_for_position,
    hire_from_application,
    update_application_status
)


def render_master_applications_review(position_id: int, token: str) -> None:
    """
    Render master position applications with availability analysis

    Shows:
    - Applicant details
    - Availability match scores
    - Application message
    - Accept & Hire button (creates OFFERED contract)
    - Decline button
    """

    st.markdown("### 📋 Master Instructor Applications")

    # Fetch applications
    try:
        applications = get_applications_for_position(token, position_id)
    except Exception as e:
        st.error(f"❌ Error loading applications: {e}")
        return

    if not applications:
        st.info("📭 No applications yet for this master position.")
        return

    # Group by status
    pending = [app for app in applications if app.get('status') == 'PENDING']
    accepted = [app for app in applications if app.get('status') == 'ACCEPTED']
    rejected = [app for app in applications if app.get('status') == 'REJECTED']

    # Show counts
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Pending", len(pending))
    with col2:
        st.metric("Accepted", len(accepted))
    with col3:
        st.metric("Rejected", len(rejected))

    st.divider()

    # Render pending applications (most important)
    if pending:
        st.markdown("#### 🟡 Pending Applications")

        for app in pending:
            _render_pending_application_card(app, token)
            st.divider()

    # Render accepted applications
    if accepted:
        with st.expander(f"✅ Accepted Applications ({len(accepted)})", expanded=False):
            for app in accepted:
                _render_accepted_application_card(app)

    # Render rejected applications
    if rejected:
        with st.expander(f"❌ Rejected Applications ({len(rejected)})", expanded=False):
            for app in rejected:
                _render_rejected_application_card(app)


def _render_pending_application_card(app: Dict[str, Any], token: str) -> None:
    """Render pending application with Accept & Hire functionality"""

    app_id = app.get('id')
    applicant_name = app.get('applicant_name', 'Unknown')
    applicant_email = app.get('applicant_email', '')
    application_message = app.get('application_message', '')
    applied_at = app.get('applied_at', '')[:10] if app.get('applied_at') else 'N/A'

    # Availability info (if backend provides it)
    availability_match = app.get('availability_match_score', None)
    instructor_availability = app.get('instructor_availability', [])

    # Position info (for contract dates)
    position = app.get('position', {})
    position_description = position.get('description', '')

    # Extract suggested contract dates from description
    contract_start_suggested = None
    contract_end_suggested = None

    if "Contract:" in position_description:
        try:
            contract_line = [line for line in position_description.split('\n') if 'Contract:' in line][0]
            dates = contract_line.split('Contract:')[1].strip()
            start_str, end_str = dates.split(' to ')
            contract_start_suggested = datetime.strptime(start_str, '%Y-%m-%d').date()
            contract_end_suggested = datetime.strptime(end_str, '%Y-%m-%d').date()
        except:
            pass

    # Render card
    with st.container():
        st.markdown(f"### {applicant_name}")
        st.caption(f"📧 {applicant_email}")
        st.caption(f"📅 Applied: {applied_at}")

        # Availability badge
        if instructor_availability:
            st.caption(f"📆 Available: {', '.join(instructor_availability)}")

        if availability_match is not None:
            if availability_match >= 80:
                st.success(f"✅ Availability Match: {availability_match}%")
            elif availability_match >= 50:
                st.warning(f"⚠️ Availability Match: {availability_match}%")
            else:
                st.error(f"❌ Availability Match: {availability_match}%")

        # Application message
        if application_message:
            with st.expander("📝 Application Message", expanded=True):
                st.text(application_message)

        st.divider()

        # Action buttons
        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "✅ Accept & Hire",
                key=f"accept_hire_{app_id}",
                type="primary",
                use_container_width=True,
                help="Accept application and create contract offer"
            ):
                _handle_accept_and_hire(
                    app_id=app_id,
                    applicant_name=applicant_name,
                    contract_start_suggested=contract_start_suggested,
                    contract_end_suggested=contract_end_suggested,
                    token=token
                )

        with col2:
            if st.button(
                "❌ Reject",
                key=f"reject_{app_id}",
                type="secondary",
                use_container_width=True,
                help="Reject this application"
            ):
                _handle_reject_application(app_id, applicant_name, token)


def _render_accepted_application_card(app: Dict[str, Any]) -> None:
    """Render accepted application (offer created)"""

    applicant_name = app.get('applicant_name', 'Unknown')
    applicant_email = app.get('applicant_email', '')
    applied_at = app.get('applied_at', '')[:10] if app.get('applied_at') else 'N/A'

    st.markdown(f"**{applicant_name}**")
    st.caption(f"📧 {applicant_email}")
    st.caption(f"📅 Applied: {applied_at}")
    st.info("✅ Application accepted - contract offer sent to instructor")


def _render_rejected_application_card(app: Dict[str, Any]) -> None:
    """Render rejected application"""

    applicant_name = app.get('applicant_name', 'Unknown')
    applicant_email = app.get('applicant_email', '')
    applied_at = app.get('applied_at', '')[:10] if app.get('applied_at') else 'N/A'

    st.markdown(f"**{applicant_name}**")
    st.caption(f"📧 {applicant_email}")
    st.caption(f"📅 Applied: {applied_at}")


def _handle_accept_and_hire(
    app_id: int,
    applicant_name: str,
    contract_start_suggested: Optional[date],
    contract_end_suggested: Optional[date],
    token: str
) -> None:
    """Handle Accept & Hire action with contract date confirmation"""

    # Show contract date confirmation dialog
    dialog_key = f"hire_dialog_{app_id}"

    if not st.session_state.get(dialog_key, False):
        # First click - show confirmation dialog
        st.session_state[dialog_key] = True
        st.rerun()
    else:
        # Dialog is open - show form
        with st.form(key=f"hire_form_{app_id}"):
            st.markdown(f"### Confirm Contract Details for {applicant_name}")

            # Contract dates
            col1, col2 = st.columns(2)

            with col1:
                default_start = contract_start_suggested or date.today() + timedelta(days=30)
                contract_start = st.date_input(
                    "Contract Start",
                    value=default_start,
                    min_value=date.today(),
                    help="Contract start date"
                )

            with col2:
                default_end = contract_end_suggested or (contract_start + timedelta(days=365))
                contract_end = st.date_input(
                    "Contract End",
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
                help="How many days instructor has to respond"
            )

            # Show calculated info
            contract_duration = (contract_end - contract_start).days
            st.info(f"📅 Contract Duration: {contract_duration} days ({contract_duration // 365} years)")

            deadline_date = date.today() + timedelta(days=offer_deadline_days)
            st.caption(f"⏰ Offer Deadline: {deadline_date.strftime('%Y-%m-%d')}")

            # Submit buttons
            col1, col2 = st.columns(2)

            with col1:
                submit = st.form_submit_button(
                    "✅ Confirm & Send Offer",
                    type="primary",
                    use_container_width=True
                )

            with col2:
                cancel = st.form_submit_button(
                    "❌ Cancel",
                    use_container_width=True
                )

            if cancel:
                # Close dialog
                if dialog_key in st.session_state:
                    del st.session_state[dialog_key]
                st.rerun()

            if submit:
                # Validate
                if contract_end <= contract_start:
                    st.error("❌ Contract end must be after start date")
                else:
                    # Call hire_from_application API
                    try:
                        with st.spinner("Creating contract offer..."):
                            offer = hire_from_application(
                                token=token,
                                application_id=app_id,
                                contract_start=contract_start.isoformat() + "T00:00:00",
                                contract_end=contract_end.isoformat() + "T23:59:59",
                                offer_deadline_days=offer_deadline_days
                            )

                        st.success(f"🎉 Contract offer sent to {applicant_name}!")
                        st.info("""
**What happens next:**
1. Instructor receives OFFERED contract in their dashboard
2. Instructor has {offer_deadline_days} days to ACCEPT or DECLINE
3. If accepted, they become the master instructor
4. All other pending applications are auto-declined
5. Position status changes to FILLED
                        """.format(offer_deadline_days=offer_deadline_days))

                        st.balloons()

                        # Clear dialog state
                        if dialog_key in st.session_state:
                            del st.session_state[dialog_key]

                        st.rerun()

                    except Exception as e:
                        error_msg = str(e)

                        if "already has an active master" in error_msg.lower():
                            st.error("❌ This location already has an active master or pending offer.")
                        elif "instructor already has" in error_msg.lower():
                            st.error("❌ This instructor already has an active master position at another location.")
                        elif "not found" in error_msg.lower():
                            st.error("❌ Application not found. It may have been withdrawn.")
                        else:
                            st.error(f"❌ Error: {error_msg}")


def _handle_reject_application(app_id: int, applicant_name: str, token: str) -> None:
    """Handle reject application action"""

    confirm_key = f"confirm_reject_{app_id}"

    if not st.session_state.get(confirm_key, False):
        # First click - ask for confirmation
        st.session_state[confirm_key] = True
        st.warning(f"⚠️ Are you sure you want to reject {applicant_name}'s application? Click 'Reject' again to confirm.")
        st.rerun()
    else:
        # Second click - confirmed
        try:
            with st.spinner("Rejecting application..."):
                update_application_status(token, app_id, "REJECTED")

            st.info(f"Application from {applicant_name} has been rejected.")

            # Clear confirmation state
            if confirm_key in st.session_state:
                del st.session_state[confirm_key]

            st.rerun()

        except Exception as e:
            st.error(f"❌ Error rejecting application: {e}")

            # Clear confirmation state on error
            if confirm_key in st.session_state:
                del st.session_state[confirm_key]


def render_all_master_applications(token: str) -> None:
    """
    Render all master position applications across all locations (admin dashboard view)

    Groups applications by position/location
    """

    st.markdown("## 📋 Master Instructor Applications")

    # This would require a new API endpoint to fetch all master positions with pending applications
    # For now, show placeholder
    st.info("💡 To review applications, navigate to a specific location's Master section and check the posted openings.")

    # TODO: Implement when backend provides aggregate view
    # from api_helpers_instructors import get_all_master_positions_with_applications
    # positions = get_all_master_positions_with_applications(token)
    # for position in positions:
    #     render_master_applications_review(position['id'], token)
