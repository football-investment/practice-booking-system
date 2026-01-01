"""
📍 Location Actions Component
Action buttons for location cards
"""

import streamlit as st
from typing import Dict, Any
from api_helpers_general import delete_location, toggle_location_status
from components.location_modals import (
    render_edit_location_modal,
    render_view_location_details
)


def _close_all_campus_modals():
    """Helper to close any open campus modals to prevent dialog conflicts"""
    keys_to_remove = []
    for key in st.session_state.keys():
        if 'campus_modal' in key or 'edit_campus_modal' in key or 'delete_campus_confirmation' in key or 'view_campus_modal' in key or 'toggle_campus_status' in key:
            keys_to_remove.append(key)
    for key in keys_to_remove:
        del st.session_state[key]


def render_location_action_buttons(location: Dict[str, Any], token: str) -> None:
    """
    Render action buttons for a location card
    """
    location_id = location.get('id')
    is_active = location.get('is_active', False)

    col1, col2, col3, col4 = st.columns(4)

    # ========================================================================
    # VIEW BUTTON
    # ========================================================================
    with col1:
        if st.button(
            "👁️ View",
            key=f"view_location_{location_id}",
            use_container_width=True
        ):
            _close_all_campus_modals()
            st.session_state[f'view_location_modal_{location_id}'] = True
            st.rerun()

    # ========================================================================
    # EDIT BUTTON
    # ========================================================================
    with col2:
        if st.button(
            "✏️ Edit",
            key=f"edit_location_{location_id}",
            use_container_width=True
        ):
            _close_all_campus_modals()
            st.session_state[f'edit_location_modal_{location_id}'] = True
            st.rerun()

    # ========================================================================
    # ACTIVATE/DEACTIVATE BUTTON
    # ========================================================================
    with col3:
        if is_active:
            if st.button(
                "🔴 Deactivate",
                key=f"deactivate_location_{location_id}",
                use_container_width=True
            ):
                _close_all_campus_modals()
                st.session_state[f'confirm_deactivate_location_{location_id}'] = True
                st.rerun()
        else:
            if st.button(
                "🟢 Activate",
                key=f"activate_location_{location_id}",
                use_container_width=True
            ):
                _close_all_campus_modals()
                st.session_state[f'confirm_activate_location_{location_id}'] = True
                st.rerun()

    # ========================================================================
    # DELETE BUTTON
    # ========================================================================
    with col4:
        if st.button(
            "🗑️ Delete",
            key=f"delete_location_{location_id}",
            use_container_width=True,
            type="secondary"
        ):
            _close_all_campus_modals()
            st.session_state[f'confirm_delete_location_{location_id}'] = True
            st.rerun()

    # ========================================================================
    # RENDER MODALS (only one at a time - Streamlit limitation)
    # ========================================================================
    # Priority: Edit > View > Delete > Toggle

    if st.session_state.get(f'edit_location_modal_{location_id}', False):
        render_edit_location_modal(location, token)
    elif st.session_state.get(f'view_location_modal_{location_id}', False):
        render_view_location_details(location)
    elif st.session_state.get(f'confirm_delete_location_{location_id}', False):
        render_delete_confirmation(location, token)
    elif st.session_state.get(f'confirm_activate_location_{location_id}', False) or st.session_state.get(f'confirm_deactivate_location_{location_id}', False):
        render_status_toggle_confirmation(location, token)


# ============================================================================
# DELETE CONFIRMATION DIALOG
# ============================================================================

def render_delete_confirmation(location: Dict[str, Any], token: str) -> None:
    """
    Render delete confirmation dialog
    """
    location_id = location.get('id')
    confirm_key = f'confirm_delete_location_{location_id}'

    if confirm_key not in st.session_state or not st.session_state[confirm_key]:
        return

    @st.dialog(f"⚠️ Delete Location", width="small")
    def confirm_dialog():
        st.warning(
            f"Are you sure you want to delete **{location.get('name')}**?\n\n"
            f"This is a soft delete - the location will be marked as inactive."
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Confirm Delete", use_container_width=True, type="primary"):
                # Call API to delete
                success, error = delete_location(token, location_id)

                if success:
                    st.success("✅ Location deleted successfully!")
                    st.session_state[confirm_key] = False
                    st.rerun()
                else:
                    st.error(f"❌ Failed to delete location: {error}")

        with col2:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state[confirm_key] = False
                st.rerun()

    confirm_dialog()


# ============================================================================
# STATUS TOGGLE CONFIRMATION DIALOG
# ============================================================================

def render_status_toggle_confirmation(location: Dict[str, Any], token: str) -> None:
    """
    Render activate/deactivate confirmation dialog
    """
    location_id = location.get('id')
    is_active = location.get('is_active', False)

    # Check which confirmation is active
    if is_active:
        confirm_key = f'confirm_deactivate_location_{location_id}'
        action = "deactivate"
        action_emoji = "🔴"
    else:
        confirm_key = f'confirm_activate_location_{location_id}'
        action = "activate"
        action_emoji = "🟢"

    if confirm_key not in st.session_state or not st.session_state[confirm_key]:
        return

    @st.dialog(f"{action_emoji} {action.capitalize()} Location", width="small")
    def confirm_dialog():
        st.warning(
            f"Are you sure you want to {action} **{location.get('name')}**?"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                f"✅ Confirm {action.capitalize()}",
                use_container_width=True,
                type="primary"
            ):
                # Toggle status
                new_status = not is_active
                success, error = toggle_location_status(token, location_id, new_status)

                if success:
                    st.success(f"✅ Location {action}d successfully!")
                    st.session_state[confirm_key] = False
                    st.rerun()
                else:
                    st.error(f"❌ Failed to {action} location: {error}")

        with col2:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state[confirm_key] = False
                st.rerun()

    confirm_dialog()
