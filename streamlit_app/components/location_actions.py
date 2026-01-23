"""
📍 Location Actions Component
Action buttons for location cards
"""

import streamlit as st
from typing import Dict, Any
import time
from api_helpers_general import delete_location, toggle_location_status, create_campus, get_campuses_by_location
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

    col1, col2, col3, col4, col5 = st.columns(5)

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
    # ADD CAMPUS BUTTON
    # ========================================================================
    with col4:
        if st.button(
            "🏫 Add Campus",
            key=f"add_campus_to_location_{location_id}",
            use_container_width=True
        ):
            _close_all_campus_modals()
            st.session_state[f'add_campus_modal_{location_id}'] = True
            st.rerun()

    # ========================================================================
    # DELETE BUTTON
    # ========================================================================
    with col5:
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
    # Priority: Edit > View > Add Campus > Delete > Toggle

    if st.session_state.get(f'edit_location_modal_{location_id}', False):
        render_edit_location_modal(location, token)
    elif st.session_state.get(f'view_location_modal_{location_id}', False):
        render_view_location_details(location)
    elif st.session_state.get(f'add_campus_modal_{location_id}', False):
        render_add_campus_modal(location, token)
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

# ============================================================================
# ADD CAMPUS MODAL
# ============================================================================

def render_add_campus_modal(location: Dict[str, Any], token: str) -> None:
    """
    Render add campus dialog for a specific location
    """
    location_id = location.get('id')
    location_name = location.get('name')
    modal_key = f'add_campus_modal_{location_id}'

    if modal_key not in st.session_state or not st.session_state[modal_key]:
        return

    @st.dialog(f"🏫 Add Campus to {location_name}", width="large")
    def add_campus_dialog():
        st.info(f"💡 **Adding campus to:** {location_name}")

        # Load existing campuses to check for duplicates
        campus_success, campuses = get_campuses_by_location(token, location_id, include_inactive=True)

        if campus_success and campuses:
            st.markdown(f"**Existing Campuses ({len(campuses)}):**")
            for campus in campuses:
                campus_status = "🟢" if campus.get('is_active') else "🔴"
                st.caption(f"{campus_status} {campus.get('name')}")
            st.divider()

        # Campus creation form
        with st.form(f"create_campus_form_{location_id}"):
            st.markdown("**➕ New Campus Details:**")

            col1, col2 = st.columns(2)

            with col1:
                campus_name = st.text_input(
                    "Campus Name *",
                    placeholder="New Campus",
                    help="Campus name within this location"
                )

                campus_venue = st.text_input(
                    "Venue",
                    placeholder="Building A",
                    help="Specific venue or building"
                )

            with col2:
                campus_address = st.text_area(
                    "Address",
                    placeholder="Fő utca 1., 2. emelet",
                    height=60
                )

                campus_notes = st.text_area(
                    "Notes",
                    placeholder="Additional information...",
                    height=60
                )

            campus_is_active = st.checkbox("Active", value=True)

            col_a, col_b = st.columns(2)

            with col_a:
                submit_btn = st.form_submit_button("✅ Create Campus", use_container_width=True, type="primary")

            with col_b:
                cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)

            if cancel_btn:
                st.session_state[modal_key] = False
                st.rerun()

            if submit_btn:
                if not campus_name:
                    st.error("❌ Campus name is required!")
                else:
                    # Check if campus name already exists
                    if campuses and any(c.get('name') == campus_name for c in campuses):
                        st.error(f"❌ Campus '{campus_name}' already exists in this location!")
                    else:
                        # Create campus
                        campus_data = {
                            "name": campus_name,
                            "venue": campus_venue if campus_venue else None,
                            "address": campus_address if campus_address else None,
                            "notes": campus_notes if campus_notes else None,
                            "is_active": campus_is_active
                        }

                        # 🔍 DEBUG: Show campus creation data
                        st.write("**🔍 DEBUG: Campus Creation Request**")
                        st.json(campus_data)

                        campus_success, campus_error, campus_response = create_campus(token, location_id, campus_data)

                        st.write(f"**🔍 DEBUG: Response - Success: {campus_success}, Error: {campus_error}**")
                        if campus_response:
                            st.json(campus_response)

                        if campus_success:
                            st.success(f"✅ Campus '{campus_name}' created successfully!")
                            time.sleep(2)
                            st.session_state[modal_key] = False
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to create campus: {campus_error}")

    add_campus_dialog()
