"""
Session Modals Component
Edit, View, and Manage modals for sessions
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from api_helpers import update_session


def render_edit_session_modal(session: Dict[str, Any], token: str) -> bool:
    """
    Render edit session modal with form

    Args:
        session: Session data dictionary
        token: Authentication token

    Returns:
        True if session was updated, False otherwise
    """
    session_id = session.get('id')
    modal_key = f"edit_session_modal_{session_id}"

    # Check if modal should be shown
    if not st.session_state.get(modal_key, False):
        return False

    st.markdown("---")
    st.markdown(f"### ✏️ Edit Session (ID: {session_id})")

    # Parse existing dates
    try:
        date_start = datetime.fromisoformat(session.get('date_start', '').replace('Z', '+00:00'))
        date_end = datetime.fromisoformat(session.get('date_end', '').replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        date_start = datetime.now()
        date_end = datetime.now() + timedelta(hours=2)

    # Form fields
    with st.form(key=f"edit_session_form_{session_id}"):
        col1, col2 = st.columns(2)

        with col1:
            title = st.text_input(
                "Title *",
                value=session.get('title', ''),
                max_chars=200
            )

            session_type = st.selectbox(
                "Session Type *",
                options=["on_site", "hybrid", "virtual", "gancuju"],
                index=["on_site", "hybrid", "virtual", "gancuju"].index(session.get('session_type', 'on_site'))
            )

            capacity = st.number_input(
                "Capacity *",
                min_value=1,
                max_value=100,
                value=session.get('capacity', 10)
            )

        with col2:
            date_start_date = st.date_input(
                "Start Date *",
                value=date_start.date()
            )

            date_start_time = st.time_input(
                "Start Time *",
                value=date_start.time()
            )

            duration_minutes = st.number_input(
                "Duration (minutes) *",
                min_value=15,
                max_value=480,
                value=int((date_end - date_start).total_seconds() / 60)
            )

        description = st.text_area(
            "Description",
            value=session.get('description', ''),
            max_chars=1000,
            height=100
        )

        location = st.text_input(
            "Location",
            value=session.get('location', ''),
            max_chars=200
        )

        # Submit buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            submit = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)
        with col2:
            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

        if cancel:
            del st.session_state[modal_key]
            st.rerun()

        if submit:
            # Validation
            if not title.strip():
                st.error("Title is required!")
                return False

            # Combine date and time
            new_date_start = datetime.combine(date_start_date, date_start_time)
            new_date_end = new_date_start + timedelta(minutes=duration_minutes)

            # Prepare update data
            update_data = {
                "title": title.strip(),
                "description": description.strip() if description else None,
                "date_start": new_date_start.isoformat(),
                "date_end": new_date_end.isoformat(),
                "session_type": session_type,
                "capacity": capacity,
                "location": location.strip() if location else None
            }

            # Call API
            success, error, updated_session = update_session(token, session_id, update_data)

            if success:
                st.success(f"✅ Session '{title}' updated successfully!")
                del st.session_state[modal_key]
                st.rerun()
                return True
            else:
                st.error(f"❌ Failed to update session: {error}")
                return False

    return False


def render_view_session_details(session: Dict[str, Any]) -> None:
    """
    Render detailed view of a session

    Args:
        session: Session data dictionary
    """
    session_id = session.get('id')
    modal_key = f"view_session_details_{session_id}"

    # Check if modal should be shown
    if not st.session_state.get(modal_key, False):
        return

    st.markdown("---")
    st.markdown(f"### 👁️ Session Details (ID: {session_id})")

    # Parse dates
    try:
        date_start = datetime.fromisoformat(session.get('date_start', '').replace('Z', '+00:00'))
        date_end = datetime.fromisoformat(session.get('date_end', '').replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        date_start = None
        date_end = None

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**📋 Basic Information**")
        st.caption(f"**ID:** {session.get('id')}")
        st.caption(f"**Title:** {session.get('title', 'N/A')}")
        st.caption(f"**Type:** {session.get('session_type', 'N/A')}")
        st.caption(f"**Location:** {session.get('location', 'N/A')}")

    with col2:
        st.markdown("**📅 Schedule**")
        if date_start:
            st.caption(f"**Start:** {date_start.strftime('%Y-%m-%d %H:%M')}")
        else:
            st.caption("**Start:** N/A")

        if date_end:
            st.caption(f"**End:** {date_end.strftime('%Y-%m-%d %H:%M')}")
            if date_start:
                duration = int((date_end - date_start).total_seconds() / 60)
                st.caption(f"**Duration:** {duration} minutes")
        else:
            st.caption("**End:** N/A")

    with col3:
        st.markdown("**👥 Capacity & Bookings**")
        capacity = session.get('capacity', 0)
        bookings = session.get('bookings', [])
        st.caption(f"**Capacity:** {capacity}")
        st.caption(f"**Bookings:** {len(bookings)}")
        st.caption(f"**Available:** {capacity - len(bookings)}")

    # Description
    if session.get('description'):
        st.markdown("**📝 Description**")
        st.info(session.get('description'))

    # Bookings list
    if bookings:
        st.markdown("**📋 Booked Users**")
        for booking in bookings:
            user = booking.get('user', {})
            st.caption(f"• {user.get('name', 'Unknown')} ({user.get('email', 'N/A')})")

    # Close button
    if st.button("❌ Close", key=f"close_details_{session_id}"):
        del st.session_state[modal_key]
        st.rerun()


def render_manage_bookings_modal(session: Dict[str, Any], token: str) -> None:
    """
    Render manage bookings modal

    Args:
        session: Session data dictionary
        token: Authentication token
    """
    session_id = session.get('id')
    modal_key = f"manage_bookings_{session_id}"

    # Check if modal should be shown
    if not st.session_state.get(modal_key, False):
        return

    st.markdown("---")
    st.markdown(f"### 📋 Manage Bookings (ID: {session_id})")
    st.caption(f"Session: **{session.get('title', 'Untitled')}**")

    bookings = session.get('bookings', [])
    capacity = session.get('capacity', 0)

    # Stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Capacity", capacity)
    with col2:
        st.metric("Booked", len(bookings))
    with col3:
        st.metric("Available", capacity - len(bookings))

    st.divider()

    # Bookings list
    if bookings:
        st.markdown("**Current Bookings:**")
        for idx, booking in enumerate(bookings, 1):
            user = booking.get('user', {})
            booking_id = booking.get('id')

            col1, col2 = st.columns([3, 1])
            with col1:
                st.caption(f"{idx}. {user.get('name', 'Unknown')} ({user.get('email', 'N/A')})")
            with col2:
                # TODO: Add remove booking functionality
                if st.button("🗑️", key=f"remove_booking_{booking_id}", help="Remove booking"):
                    st.info("🚧 Remove booking functionality coming soon!")
    else:
        st.info("No bookings yet")

    # Close button
    if st.button("❌ Close", key=f"close_bookings_{session_id}"):
        del st.session_state[modal_key]
        st.rerun()
