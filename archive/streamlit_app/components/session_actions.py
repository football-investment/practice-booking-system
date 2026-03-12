"""
Session Actions Component
Compact, reusable action buttons for session cards
"""

import streamlit as st
from typing import Dict, Any, Optional
from api_helpers import delete_session
from components.session_modals import (
    render_edit_session_modal,
    render_view_session_details,
    render_manage_bookings_modal
)


def render_session_action_buttons(session: Dict[str, Any], token: str) -> None:
    """
    Render action buttons for a session card

    Args:
        session: Session data dictionary
        token: Authentication token
    """
    session_id = session.get('id')
    session_title = session.get('title', 'Untitled Session')

    col1, col2, col3, col4 = st.columns(4)

    # Edit button (WORKING - opens modal)
    with col1:
        if st.button("✏️ Edit", key=f"edit_session_{session_id}", use_container_width=True):
            st.session_state[f'edit_session_modal_{session_id}'] = True
            st.rerun()

    # Delete button (WORKING)
    with col2:
        if st.button("🗑️ Delete", key=f"delete_session_{session_id}", use_container_width=True, type="secondary"):
            # Store session ID in session state for confirmation dialog
            st.session_state[f'confirm_delete_session_{session_id}'] = True
            st.rerun()

    # View Details button (WORKING - opens details view)
    with col3:
        if st.button("👁️ Details", key=f"view_session_{session_id}", use_container_width=True):
            st.session_state[f'view_session_details_{session_id}'] = True
            st.rerun()

    # Manage Bookings button (WORKING - opens bookings modal)
    with col4:
        if st.button("📋 Bookings", key=f"bookings_session_{session_id}", use_container_width=True):
            st.session_state[f'manage_bookings_{session_id}'] = True
            st.rerun()

    # Render modals if they should be shown
    render_edit_session_modal(session, token)
    render_view_session_details(session)
    render_manage_bookings_modal(session, token)

    # Confirmation dialog for delete
    if st.session_state.get(f'confirm_delete_session_{session_id}', False):
        st.warning(f"⚠️ Are you sure you want to delete session **{session_title}** (ID: {session_id})?")

        confirm_col1, confirm_col2, confirm_col3 = st.columns([1, 1, 2])

        with confirm_col1:
            if st.button("✅ Yes, Delete", key=f"confirm_yes_{session_id}", type="primary"):
                # Call API to delete session
                success, error = delete_session(token, session_id)

                if success:
                    st.success(f"✅ Session {session_title} deleted successfully!")
                    # Clear confirmation state
                    del st.session_state[f'confirm_delete_session_{session_id}']
                    st.rerun()
                else:
                    st.error(f"❌ Failed to delete session: {error}")
                    del st.session_state[f'confirm_delete_session_{session_id}']

        with confirm_col2:
            if st.button("❌ Cancel", key=f"confirm_no_{session_id}"):
                # Clear confirmation state
                del st.session_state[f'confirm_delete_session_{session_id}']
                st.rerun()


