"""
Tournament Approval Module - Instructor assignment workflows
"""

import streamlit as st
from pathlib import Path
import sys
from typing import List, Dict
import requests
import time

# Setup imports
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from config import API_BASE_URL, API_TIMEOUT


def render_instructor_applications_section(token: str, tournament: Dict):
    """
    Render instructor assignment section based on assignment_type.

    Two workflows:
    1. APPLICATION_BASED: Instructors apply → Admin approves → Instructor accepts
    2. OPEN_ASSIGNMENT: Admin directly invites instructor → Instructor accepts
    """
    tournament_id = tournament.get('id')
    status = tournament.get('status', 'N/A')
    master_instructor_id = tournament.get('master_instructor_id')
    assignment_type = tournament.get('assignment_type', 'UNKNOWN')

    st.subheader("👨‍🏫 Instructor Assignment")

    # Show current instructor status
    if master_instructor_id:
        st.success(f"✅ **Instructor Assigned** (ID: {master_instructor_id})")
    elif status == "SEEKING_INSTRUCTOR":
        st.warning(f"⏳ **Seeking Instructor** ({assignment_type})")
    else:
        st.info(f"**Status**: {status}")

    st.divider()

    # 🔥 BRANCHING: Different UI based on assignment_type
    if assignment_type == "APPLICATION_BASED":
        render_application_based_workflow(token, tournament_id)
    elif assignment_type == "OPEN_ASSIGNMENT":
        render_open_assignment_workflow(token, tournament_id, master_instructor_id)
    else:
        st.warning(f"⚠️ Unknown assignment type: {assignment_type}")


def render_application_based_workflow(token: str, tournament_id: int):
    """
    Workflow 1: APPLICATION_BASED
    Instructors apply → Admin reviews → Admin approves → Instructor accepts
    """
    # Fetch pending applications for this tournament
    applications = get_instructor_applications(token, tournament_id)

    if not applications:
        st.info("📭 No instructor applications yet")
        st.caption("Instructors can apply through their dashboard")
        return

    st.write(f"**Applications**: {len(applications)}")
    st.divider()

    # Check if there's already an accepted application
    has_accepted_application = any(app.get('status') == 'ACCEPTED' for app in applications)

    # Display each application
    for app in applications:
        render_instructor_application_card(token, tournament_id, app, has_accepted_application)


def render_open_assignment_workflow(token: str, tournament_id: int, current_instructor_id: int = None):
    """
    Workflow 2: OPEN_ASSIGNMENT
    Admin directly selects instructor → Sends invitation → Instructor accepts
    """
    # If instructor already assigned, show status
    if current_instructor_id:
        st.success("✅ Instructor directly assigned")
        return

    st.info("🔒 **Direct Assignment Mode**")
    st.caption("Select an instructor to invite directly (no application required)")
    st.divider()

    # Fetch all instructors with LFA_COACH license
    instructors = get_all_instructors_with_coach_license(token)

    if not instructors:
        st.warning("⚠️ No instructors available with LFA_COACH license")
        st.caption("Create instructor accounts first")
        return

    # Instructor selector
    instructor_options = {
        f"{instr.get('name', 'Unnamed')} ({instr.get('email', 'No email')})": instr['id']
        for instr in instructors
    }

    selected_instructor_name = st.selectbox(
        "Select Instructor",
        options=["-- Select an instructor --"] + list(instructor_options.keys()),
        key=f"instructor_selector_{tournament_id}"
    )

    if selected_instructor_name == "-- Select an instructor --":
        st.caption("ℹ️ Choose an instructor from the dropdown to proceed")
        return

    selected_instructor_id = instructor_options[selected_instructor_name]

    # Optional invitation message
    invitation_message = st.text_area(
        "Invitation Message (optional)",
        value=f"You have been selected to lead this tournament. Please accept this invitation.",
        key=f"invitation_message_{tournament_id}",
        height=100
    )

    st.divider()

    # Send invitation button
    if st.button(
        "📨 Send Direct Invitation",
        key=f"send_invitation_{tournament_id}",
        type="primary",
        use_container_width=True
    ):
        send_direct_invitation(token, tournament_id, selected_instructor_id, invitation_message)


def get_instructor_applications(token: str, tournament_id: int) -> List[Dict]:
    """Fetch instructor applications for a tournament"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/instructor-applications",
            headers={"Authorization": f"Bearer {token}"},
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            return data.get('applications', [])
        else:
            return []
    except Exception:
        return []


def render_instructor_application_card(token: str, tournament_id: int, application: Dict, has_accepted_application: bool = False):
    """
    Render a single instructor application with approve/reject buttons.

    Args:
        has_accepted_application: If True, hide approve/reject buttons for PENDING applications
                                  (since another application is already accepted)
    """
    app_id = application.get('id')
    instructor_name = application.get('instructor_name', 'Unknown')
    instructor_email = application.get('instructor_email', 'N/A')
    status = application.get('status', 'PENDING')
    applied_at = application.get('created_at', 'N/A')
    request_message = application.get('request_message') or application.get('application_message', '')

    # Status badge color
    status_color = {
        'PENDING': '🟡',
        'ACCEPTED': '🟢',
        'DECLINED': '🔴',
        'CANCELLED': '⚫',
        'EXPIRED': '⚪'
    }.get(status, '⚪')

    with st.container():
        st.markdown(f"**{status_color} Application #{app_id}** - {instructor_name}")

        col1, col2 = st.columns([3, 1])

        with col1:
            st.caption(f"📧 {instructor_email}")
            st.caption(f"📅 Applied: {applied_at[:19] if len(applied_at) > 19 else applied_at}")
            if request_message:
                st.caption(f"💬 Message: {request_message}")

        with col2:
            # Only show approve/reject buttons for PENDING applications IF no instructor is accepted yet
            if status == 'PENDING':
                if has_accepted_application:
                    # Another instructor is already accepted - don't show action buttons
                    st.caption("ℹ️ _Instructor already selected_")
                else:
                    # No accepted instructor yet - show approve/reject buttons
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button("✅", key=f"approve_app_{app_id}", help="Approve application"):
                            st.session_state['approve_app_id'] = app_id
                            st.session_state['approve_tournament_id'] = tournament_id
                            st.session_state['approve_instructor_name'] = instructor_name
                            show_approve_application_dialog()
                    with btn_col2:
                        if st.button("❌", key=f"reject_app_{app_id}", help="Reject application"):
                            st.session_state['reject_app_id'] = app_id
                            st.session_state['reject_tournament_id'] = tournament_id
                            st.session_state['reject_instructor_name'] = instructor_name
                            show_reject_application_dialog()
            else:
                st.caption(f"**Status**: {status}")

        st.divider()


@st.dialog("✅ Approve Instructor Application")
def show_approve_application_dialog():
    """Dialog for approving an instructor application"""
    app_id = st.session_state.get('approve_app_id')
    tournament_id = st.session_state.get('approve_tournament_id')
    instructor_name = st.session_state.get('approve_instructor_name', 'Unknown')

    st.write(f"**Approve application from**: {instructor_name}")
    st.write(f"**Application ID**: {app_id}")
    st.divider()

    # Optional response message
    response_message = st.text_area(
        "Response Message (optional)",
        value="Application approved - looking forward to working with you!",
        key="approve_response_message"
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Approve", use_container_width=True, type="primary", key="confirm_approve_application_btn"):
            token = st.session_state.get('token')

            try:
                response = requests.post(
                    f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/instructor-applications/{app_id}/approve",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"response_message": response_message},
                    timeout=API_TIMEOUT
                )

                if response.status_code == 200:
                    st.success("✅ Application approved successfully!")
                    st.info("ℹ️ Tournament is now ready - you can open enrollment for players.")
                    time.sleep(2)
                    # Clear session state
                    if 'approve_app_id' in st.session_state:
                        del st.session_state['approve_app_id']
                    if 'approve_tournament_id' in st.session_state:
                        del st.session_state['approve_tournament_id']
                    if 'approve_instructor_name' in st.session_state:
                        del st.session_state['approve_instructor_name']

                    # Force cache invalidation by setting a timestamp
                    # This ensures fresh tournament data is fetched after approval
                    st.session_state['last_tournament_update'] = time.time()

                    st.rerun()
                else:
                    error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                    error_msg = error_data.get('detail', response.text)
                    st.error(f"❌ Error: {error_msg}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    with col2:
        if st.button("Cancel", use_container_width=True):
            # Clear session state
            if 'approve_app_id' in st.session_state:
                del st.session_state['approve_app_id']
            if 'approve_tournament_id' in st.session_state:
                del st.session_state['approve_tournament_id']
            if 'approve_instructor_name' in st.session_state:
                del st.session_state['approve_instructor_name']
            st.rerun()


@st.dialog("❌ Reject Instructor Application")
def show_reject_application_dialog():
    """Dialog for rejecting an instructor application"""
    app_id = st.session_state.get('reject_app_id')
    tournament_id = st.session_state.get('reject_tournament_id')
    instructor_name = st.session_state.get('reject_instructor_name', 'Unknown')

    st.warning(f"**Reject application from**: {instructor_name}")
    st.write(f"**Application ID**: {app_id}")
    st.divider()

    # Optional response message
    response_message = st.text_area(
        "Rejection Reason (optional)",
        value="Thank you for your interest, but we have selected another instructor.",
        key="reject_response_message"
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("❌ Reject", use_container_width=True, type="primary"):
            token = st.session_state.get('token')

            # Note: Backend doesn't have a reject endpoint yet, we'll use PATCH to update status
            try:
                response = requests.patch(
                    f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/instructor-applications/{app_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "status": "DECLINED",
                        "response_message": response_message
                    },
                    timeout=API_TIMEOUT
                )

                if response.status_code == 200:
                    st.success("✅ Application rejected successfully!")
                    time.sleep(2)
                    # Clear session state
                    if 'reject_app_id' in st.session_state:
                        del st.session_state['reject_app_id']
                    if 'reject_tournament_id' in st.session_state:
                        del st.session_state['reject_tournament_id']
                    if 'reject_instructor_name' in st.session_state:
                        del st.session_state['reject_instructor_name']
                    st.rerun()
                else:
                    error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                    error_msg = error_data.get('detail', response.text)
                    st.error(f"❌ Error: {error_msg}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    with col2:
        if st.button("Cancel", use_container_width=True):
            # Clear session state
            if 'reject_app_id' in st.session_state:
                del st.session_state['reject_app_id']
            if 'reject_tournament_id' in st.session_state:
                del st.session_state['reject_tournament_id']
            if 'reject_instructor_name' in st.session_state:
                del st.session_state['reject_instructor_name']
            st.rerun()


def get_all_instructors_with_coach_license(token: str) -> List[Dict]:
    """
    Fetch all instructors with active LFA_COACH license.

    Returns: List of instructor user objects with license information
    """
    try:
        # Fetch all users with INSTRUCTOR role
        response = requests.get(
            f"{API_BASE_URL}/api/v1/users/",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "role": "instructor",
                "is_active": True,
                "size": 100
            },
            timeout=API_TIMEOUT
        )

        if response.status_code != 200:
            return []

        data = response.json()
        all_instructors = data.get("users", [])

        # For now, return all instructors
        # TODO: In production, filter for LFA_COACH license
        # The backend direct-assign-instructor endpoint validates license anyway
        return all_instructors

        # Filter for instructors with LFA_COACH license
        # Commented out for now because license endpoint structure needs verification
        # instructors_with_license = []
        #
        # for instructor in all_instructors:
        #     # Fetch licenses for this instructor
        #     license_response = requests.get(
        #         f"{API_BASE_URL}/api/v1/user-licenses/user/{instructor['id']}",
        #         headers={"Authorization": f"Bearer {token}"},
        #         timeout=API_TIMEOUT
        #     )
        #
        #     if license_response.status_code == 200:
        #         licenses = license_response.json()
        #
        #         # Check if they have LFA_COACH license
        #         has_coach_license = any(
        #             lic.get('specialization_type') == 'LFA_COACH'
        #             for lic in licenses
        #         )
        #
        #         if has_coach_license:
        #             instructors_with_license.append(instructor)
        #
        # return instructors_with_license

    except Exception as e:
        st.error(f"❌ Error fetching instructors: {str(e)}")
        return []


def send_direct_invitation(token: str, tournament_id: int, instructor_id: int, message: str):
    """
    Send direct invitation to instructor for OPEN_ASSIGNMENT tournament.

    Calls the backend API to directly assign instructor to tournament.
    """
    try:
        with st.spinner("Sending invitation..."):
            response = requests.post(
                f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/direct-assign-instructor",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "instructor_id": instructor_id,
                    "assignment_message": message
                },
                timeout=API_TIMEOUT
            )

            if response.status_code == 200:
                result = response.json()

                st.success("✅ **Invitation sent successfully!**")
                st.info("ℹ️ Instructor has been notified and must accept the assignment.")

                # Display assignment details
                st.divider()
                st.caption("**Assignment Details:**")
                st.caption(f"• Instructor: {result.get('instructor_name', 'Unknown')}")
                st.caption(f"• Status: {result.get('status', 'PENDING')}")
                st.caption(f"• Assignment ID: {result.get('assignment_id', 'N/A')}")

                time.sleep(2)
                st.rerun()

            elif response.status_code == 400:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                error_detail = error_data.get('detail', {})

                if isinstance(error_detail, dict):
                    error_msg = error_detail.get('message', response.text)
                    error_type = error_detail.get('error', 'unknown_error')

                    if error_type == 'license_required':
                        st.error("❌ **License Error**: Selected instructor does not have LFA_COACH license")
                    elif error_type == 'invalid_tournament_status':
                        st.error(f"❌ **Status Error**: {error_msg}")
                        st.caption(f"Current status: {error_detail.get('current_status', 'N/A')}")
                    else:
                        st.error(f"❌ **Error**: {error_msg}")
                else:
                    st.error(f"❌ Error: {error_detail}")

            elif response.status_code == 403:
                st.error("❌ **Permission Denied**: Only admins can directly assign instructors")

            elif response.status_code == 404:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                error_detail = error_data.get('detail', {})

                if isinstance(error_detail, dict):
                    error_type = error_detail.get('error', 'not_found')

                    if error_type == 'tournament_not_found':
                        st.error("❌ **Tournament Not Found**")
                    elif error_type == 'instructor_not_found':
                        st.error("❌ **Instructor Not Found**")
                    else:
                        st.error(f"❌ **Not Found**: {error_detail.get('message', 'Resource not found')}")
                else:
                    st.error("❌ Resource not found")

            else:
                st.error(f"❌ Failed to send invitation: Server error {response.status_code}")

    except Exception as e:
        st.error(f"❌ Error sending invitation: {str(e)}")
