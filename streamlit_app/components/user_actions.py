"""
User Actions Component
Compact, reusable action buttons for user cards
"""

import streamlit as st
from typing import Dict, Any, Optional
from api_helpers import toggle_user_status
from components.user_modals import (
    render_edit_user_modal,
    render_view_user_profile,
    render_reset_password_dialog
)


def render_user_action_buttons(user: Dict[str, Any], token: str) -> None:
    """
    Render action buttons for a user card

    Args:
        user: User data dictionary
        token: Authentication token
    """
    user_id = user.get('id')
    user_name = user.get('name', 'Unknown User')
    user_email = user.get('email', 'N/A')
    is_active = user.get('is_active', False)

    col1, col2, col3, col4 = st.columns(4)

    # Edit button (WORKING - opens modal)
    with col1:
        if st.button("✏️ Edit", key=f"edit_user_{user_id}", use_container_width=True):
            st.session_state[f'edit_user_modal_{user_id}'] = True
            st.rerun()

    # Activate/Deactivate button (WORKING)
    with col2:
        if is_active:
            button_label = "🔒 Deactivate"
            button_type = "secondary"
        else:
            button_label = "✅ Activate"
            button_type = "primary"

        if st.button(button_label, key=f"toggle_user_{user_id}", use_container_width=True, type=button_type):
            # Store user ID in session state for confirmation dialog
            st.session_state[f'confirm_toggle_user_{user_id}'] = True
            st.rerun()

    # Reset Password button (WORKING - opens dialog)
    with col3:
        if st.button("🔑 Reset PW", key=f"reset_pw_{user_id}", use_container_width=True):
            st.session_state[f'reset_password_{user_id}'] = True
            st.rerun()

    # View Profile button (WORKING - opens profile view)
    with col4:
        if st.button("👁️ Profile", key=f"view_profile_{user_id}", use_container_width=True):
            st.session_state[f'view_user_profile_{user_id}'] = True
            st.rerun()

    # Render modals if they should be shown
    render_edit_user_modal(user, token)
    render_view_user_profile(user)
    render_reset_password_dialog(user, token)

    # Confirmation dialog for activate/deactivate
    if st.session_state.get(f'confirm_toggle_user_{user_id}', False):
        action = "deactivate" if is_active else "activate"
        new_status = not is_active

        st.warning(f"⚠️ Are you sure you want to **{action}** user **{user_name}** ({user_email})?")

        confirm_col1, confirm_col2, confirm_col3 = st.columns([1, 1, 2])

        with confirm_col1:
            if st.button(f"✅ Yes, {action.title()}", key=f"confirm_toggle_yes_{user_id}", type="primary"):
                # Call API to toggle user status
                success, error = toggle_user_status(token, user_id, new_status)

                if success:
                    status_text = "activated" if new_status else "deactivated"
                    st.success(f"✅ User {user_name} {status_text} successfully!")
                    # Clear confirmation state
                    del st.session_state[f'confirm_toggle_user_{user_id}']
                    st.rerun()
                else:
                    st.error(f"❌ Failed to {action} user: {error}")
                    del st.session_state[f'confirm_toggle_user_{user_id}']

        with confirm_col2:
            if st.button("❌ Cancel", key=f"confirm_toggle_no_{user_id}"):
                # Clear confirmation state
                del st.session_state[f'confirm_toggle_user_{user_id}']
                st.rerun()


