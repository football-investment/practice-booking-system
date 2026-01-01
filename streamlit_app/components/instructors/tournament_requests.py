"""
Tournament Requests Component - Instructor Dashboard

Allows instructors to:
1. View pending tournament assignment requests
2. Accept/decline tournament invitations
3. See tournament details before accepting
"""
import streamlit as st
from typing import List, Dict, Any, Optional
import requests
from streamlit_app.config import API_BASE_URL


def render_tournament_requests():
    """Render tournament assignment requests for instructor"""
    st.header("📩 Tournament Requests")
    st.caption("Review and respond to tournament assignment invitations")

    # Fetch pending requests
    pending_requests = _get_pending_requests()

    if not pending_requests:
        st.info("✅ No pending tournament requests")
        st.caption("When admins invite you to lead tournaments, they will appear here.")
        return

    st.write(f"**{len(pending_requests)} Pending Request(s)**")
    st.divider()

    # Render each request
    for request in pending_requests:
        _render_request_card(request)


def _render_request_card(request: Dict[str, Any]):
    """Render a single tournament request card"""
    # Get tournament details
    tournament = _get_tournament_details(request.get('semester_id'))

    if not tournament:
        st.error(f"❌ Tournament not found (Request ID: {request.get('id')})")
        return

    with st.container():
        st.markdown("---")

        # Header
        col1, col2 = st.columns([3, 1])

        with col1:
            st.subheader(f"🏆 {tournament.get('name', 'Unnamed Tournament')}")
            st.caption(f"Request ID: {request.get('id')}")

        with col2:
            # Status badge
            st.markdown(
                f"<div style='text-align: right; padding: 10px; background-color: #FFF3CD; "
                f"border-radius: 5px; font-weight: bold; color: #856404;'>📩 PENDING</div>",
                unsafe_allow_html=True
            )

        # Tournament details
        st.divider()

        detail_col1, detail_col2, detail_col3 = st.columns(3)

        with detail_col1:
            st.write("**📅 Date:**")
            st.write(tournament.get('start_date', 'N/A'))

        with detail_col2:
            st.write("**📍 Location:**")
            location_id = tournament.get('location_id')
            if location_id:
                location = _get_location_details(location_id)
                st.write(location.get('name', 'N/A') if location else f"Location ID: {location_id}")
            else:
                st.write("Not specified")

        with detail_col3:
            st.write("**🎯 Specialization:**")
            st.write(tournament.get('specialization_type', 'N/A'))

        # Sessions info
        st.write("**📅 Sessions:**")
        sessions = _get_tournament_sessions(tournament.get('id'))

        if sessions:
            session_summary = ", ".join([
                f"{s.get('title', 'Session')} ({s.get('time', 'N/A')})"
                for s in sessions[:3]  # Show first 3
            ])
            st.caption(session_summary)

            if len(sessions) > 3:
                st.caption(f"... and {len(sessions) - 3} more session(s)")

            # Capacity summary
            total_capacity = sum(s.get('capacity', 0) for s in sessions)
            st.caption(f"Total Capacity: {total_capacity} students across {len(sessions)} sessions")
        else:
            st.caption("No sessions configured")

        # Admin message
        message = request.get('message')
        if message:
            st.write("**💬 Message from Admin:**")
            st.info(message)

        # Action buttons
        st.divider()

        action_col1, action_col2, action_col3 = st.columns([1, 1, 2])

        with action_col1:
            if st.button(
                "✅ Accept",
                key=f"accept_btn_{request.get('id')}",
                type="primary",
                use_container_width=True
            ):
                _accept_request(request.get('id'))

        with action_col2:
            if st.button(
                "❌ Decline",
                key=f"decline_btn_{request.get('id')}",
                use_container_width=True
            ):
                # Show decline reason form
                st.session_state[f'declining_{request.get("id")}'] = True
                st.rerun()

        with action_col3:
            # View full details button
            if st.button(
                "📊 View Full Details",
                key=f"details_btn_{request.get('id')}",
                use_container_width=True
            ):
                st.session_state[f'show_details_{request.get("id")}'] = True
                st.rerun()

        # Decline reason form (if declining)
        if st.session_state.get(f'declining_{request.get("id")}', False):
            st.divider()
            st.write("**Decline Reason (Optional):**")

            decline_reason = st.text_area(
                "Why are you declining this request?",
                placeholder="e.g., Not available on that date, Already committed to another tournament, etc.",
                key=f"decline_reason_{request.get('id')}"
            )

            decline_col1, decline_col2 = st.columns(2)

            with decline_col1:
                if st.button(
                    "🚫 Confirm Decline",
                    key=f"confirm_decline_{request.get('id')}",
                    type="secondary",
                    use_container_width=True
                ):
                    _decline_request(request.get('id'), decline_reason)

            with decline_col2:
                if st.button(
                    "↩️ Cancel",
                    key=f"cancel_decline_{request.get('id')}",
                    use_container_width=True
                ):
                    st.session_state[f'declining_{request.get("id")}'] = False
                    st.rerun()

        # Full details modal (if requested)
        if st.session_state.get(f'show_details_{request.get("id")}', False):
            st.divider()
            st.write("**📊 Full Tournament Details:**")

            with st.expander("Tournament Summary", expanded=True):
                st.json({
                    "tournament_id": tournament.get('id'),
                    "code": tournament.get('code'),
                    "name": tournament.get('name'),
                    "date": tournament.get('start_date'),
                    "status": tournament.get('status'),
                    "specialization": tournament.get('specialization_type'),
                    "age_group": tournament.get('age_group'),
                    "location_id": tournament.get('location_id'),
                    "sessions_count": len(sessions) if sessions else 0
                })

            if st.button(
                "✖️ Close Details",
                key=f"close_details_{request.get('id')}"
            ):
                st.session_state[f'show_details_{request.get("id")}'] = False
                st.rerun()


def _get_pending_requests() -> List[Dict[str, Any]]:
    """Fetch pending tournament requests for current instructor"""
    try:
        instructor_id = st.session_state.user.get('id')
        response = requests.get(
            f"{API_BASE_URL}/api/v1/tournaments/requests/instructor/{instructor_id}",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )

        if response.status_code == 200:
            requests_list = response.json()
            # All requests from this endpoint are tournament requests
            return requests_list
        return []
    except Exception as e:
        st.error(f"Error loading requests: {str(e)}")
        return []


def _is_tournament_request(semester_id: int) -> bool:
    """Check if semester is a tournament"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/semesters/{semester_id}",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )

        if response.status_code == 200:
            semester = response.json()
            return semester.get('code', '').startswith('TOURN-')
        return False
    except:
        return False


def _get_tournament_details(semester_id: int) -> Optional[Dict[str, Any]]:
    """Fetch tournament details"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/tournaments/{semester_id}/summary",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )

        if response.status_code == 200:
            return response.json()

        # Fallback: try semesters endpoint
        response = requests.get(
            f"{API_BASE_URL}/api/v1/semesters/{semester_id}",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )

        if response.status_code == 200:
            return response.json()

        return None
    except:
        return None


def _get_tournament_sessions(tournament_id: int) -> List[Dict[str, Any]]:
    """Fetch tournament sessions"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/sessions",
            headers={"Authorization": f"Bearer {st.session_state.token}"},
            params={"semester_id": tournament_id}
        )

        if response.status_code == 200:
            sessions = response.json()
            # Format time for display
            for session in sessions:
                if session.get('date_start'):
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(session['date_start'].replace('Z', '+00:00'))
                        session['time'] = dt.strftime('%H:%M')
                    except:
                        session['time'] = 'N/A'
            return sessions
        return []
    except:
        return []


def _get_location_details(location_id: int) -> Optional[Dict[str, Any]]:
    """Fetch location details"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/locations/{location_id}",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )

        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None


def _accept_request(request_id: int):
    """Accept tournament assignment request"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/requests/{request_id}/accept",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )

        if response.status_code == 200:
            st.success("✅ Request accepted! You are now the master instructor for this tournament.")
            st.balloons()

            # Clear any session state
            for key in list(st.session_state.keys()):
                if f'_{request_id}' in key:
                    del st.session_state[key]

            st.rerun()
        else:
            error_detail = response.json().get("detail", "Unknown error")
            st.error(f"❌ Error accepting request: {error_detail}")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")


def _decline_request(request_id: int, reason: Optional[str] = None):
    """Decline tournament assignment request"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/requests/{request_id}/decline",
            headers={"Authorization": f"Bearer {st.session_state.token}"},
            json={"reason": reason if reason else None}
        )

        if response.status_code == 200:
            st.warning("Request declined.")
            st.info("Admin can send a new request if needed.")

            # Clear any session state
            for key in list(st.session_state.keys()):
                if f'_{request_id}' in key:
                    del st.session_state[key]

            st.rerun()
        else:
            error_detail = response.json().get("detail", "Unknown error")
            st.error(f"❌ Error declining request: {error_detail}")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
