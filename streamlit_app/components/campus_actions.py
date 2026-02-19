"""
Campus Action Buttons Component
Compact action buttons for campus management
"""
import streamlit as st
from typing import Dict


def _close_all_location_modals():
    """Helper to close any open location modals to prevent dialog conflicts"""
    keys_to_remove = []
    for key in st.session_state.keys():
        if 'location_modal' in key or 'edit_location_modal' in key or 'delete_location_confirmation' in key:
            keys_to_remove.append(key)
    for key in keys_to_remove:
        del st.session_state[key]


def render_campus_action_buttons(campus: Dict, location_id: int, token: str):
    """
    Render action buttons for a campus

    Args:
        campus: Campus data dict
        location_id: Parent location ID
        token: Authentication token
    """
    campus_id = campus.get('id')
    is_active = campus.get('is_active', False)

    # Action buttons in columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button(f"✏️ Edit", key=f"edit_campus_{campus_id}", use_container_width=True):
            # Close any location modals
            _close_all_location_modals()
            st.session_state[f'edit_campus_modal_{campus_id}'] = True
            st.rerun()

    with col2:
        if is_active:
            if st.button(f"🔴 Deactivate", key=f"deactivate_campus_{campus_id}", use_container_width=True):
                _close_all_location_modals()
                st.session_state[f'toggle_campus_status_{campus_id}'] = True
                st.session_state[f'target_campus_status_{campus_id}'] = False
                st.rerun()
        else:
            if st.button(f"🟢 Activate", key=f"activate_campus_{campus_id}", use_container_width=True):
                _close_all_location_modals()
                st.session_state[f'toggle_campus_status_{campus_id}'] = True
                st.session_state[f'target_campus_status_{campus_id}'] = True
                st.rerun()

    with col3:
        if st.button(f"🗑️ Delete", key=f"delete_campus_{campus_id}", use_container_width=True):
            _close_all_location_modals()
            st.session_state[f'delete_campus_confirmation_{campus_id}'] = True
            st.rerun()

    with col4:
        if st.button(f"👁️ View", key=f"view_campus_{campus_id}", use_container_width=True):
            _close_all_location_modals()
            st.session_state[f'view_campus_modal_{campus_id}'] = True
            st.rerun()

    # Handle modals (only one at a time - Streamlit limitation)
    # Priority: Edit > View > Toggle > Delete
    if st.session_state.get(f'edit_campus_modal_{campus_id}', False):
        render_edit_campus_modal(campus, location_id, token)
    elif st.session_state.get(f'view_campus_modal_{campus_id}', False):
        render_view_campus_details(campus)
    elif st.session_state.get(f'toggle_campus_status_{campus_id}', False):
        render_campus_status_toggle_confirmation(campus, token)
    elif st.session_state.get(f'delete_campus_confirmation_{campus_id}', False):
        render_delete_campus_confirmation(campus, token)


def render_edit_campus_modal(campus: Dict, location_id: int, token: str):
    """Edit campus modal"""
    from api_helpers_general import update_campus

    campus_id = campus.get('id')

    @st.dialog(f"✏️ Edit Campus: {campus.get('name')}")
    def edit_modal():
        with st.form(f"edit_campus_form_{campus_id}"):
            name = st.text_input("Campus Name *", value=campus.get('name', ''))
            venue = st.text_input("Venue", value=campus.get('venue', ''))
            address = st.text_area("Address", value=campus.get('address', ''))
            notes = st.text_area("Notes", value=campus.get('notes', ''))
            is_active = st.checkbox("Active", value=campus.get('is_active', True))

            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary")
            with col2:
                cancelled = st.form_submit_button("❌ Cancel", use_container_width=True)

            if cancelled:
                del st.session_state[f'edit_campus_modal_{campus_id}']
                st.rerun()

            if submitted:
                if not name:
                    st.error("Campus name is required")
                else:
                    data = {
                        "name": name,
                        "venue": venue,
                        "address": address,
                        "notes": notes,
                        "is_active": is_active
                    }

                    success, error, _ = update_campus(token, campus_id, data)

                    if success:
                        st.success(f"✅ Campus '{name}' updated successfully!")
                        del st.session_state[f'edit_campus_modal_{campus_id}']
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to update campus: {error}")

    edit_modal()


def render_campus_status_toggle_confirmation(campus: Dict, token: str):
    """Campus status toggle confirmation dialog"""
    from api_helpers_general import toggle_campus_status

    campus_id = campus.get('id')
    campus_name = campus.get('name', 'Unknown Campus')
    target_status = st.session_state.get(f'target_campus_status_{campus_id}', True)
    action = "activate" if target_status else "deactivate"

    @st.dialog(f"{'🟢 Activate' if target_status else '🔴 Deactivate'} Campus")
    def toggle_modal():
        st.warning(f"Are you sure you want to {action} campus **{campus_name}**?")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirm", use_container_width=True, type="primary"):
                success, error = toggle_campus_status(token, campus_id, target_status)

                if success:
                    st.success(f"✅ Campus '{campus_name}' {'activated' if target_status else 'deactivated'}!")
                    del st.session_state[f'toggle_campus_status_{campus_id}']
                    del st.session_state[f'target_campus_status_{campus_id}']
                    st.rerun()
                else:
                    st.error(f"❌ Failed to {action} campus: {error}")

        with col2:
            if st.button("❌ Cancel", use_container_width=True):
                del st.session_state[f'toggle_campus_status_{campus_id}']
                del st.session_state[f'target_campus_status_{campus_id}']
                st.rerun()

    toggle_modal()


def render_delete_campus_confirmation(campus: Dict, token: str):
    """Campus delete confirmation dialog"""
    from api_helpers_general import delete_campus

    campus_id = campus.get('id')
    campus_name = campus.get('name', 'Unknown Campus')

    @st.dialog("🗑️ Delete Campus")
    def delete_modal():
        st.error(f"⚠️ Are you sure you want to delete campus **{campus_name}**?")
        st.caption("This is a soft delete - the campus will be deactivated but data will be retained.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Delete", use_container_width=True, type="primary"):
                success, error = delete_campus(token, campus_id)

                if success:
                    st.success(f"✅ Campus '{campus_name}' deleted!")
                    del st.session_state[f'delete_campus_confirmation_{campus_id}']
                    st.rerun()
                else:
                    st.error(f"❌ Failed to delete campus: {error}")

        with col2:
            if st.button("❌ Cancel", use_container_width=True):
                del st.session_state[f'delete_campus_confirmation_{campus_id}']
                st.rerun()

    delete_modal()


def render_view_campus_details(campus: Dict):
    """Campus details view modal"""
    campus_id = campus.get('id')
    campus_name = campus.get('name', 'Unknown Campus')

    @st.dialog(f"👁️ Campus Details: {campus_name}")
    def view_modal():
        st.markdown("### 🏫 Basic Information")
        st.markdown(f"**ID:** {campus.get('id', 'N/A')}")
        st.markdown(f"**Name:** {campus.get('name', 'N/A')}")
        st.markdown(f"**Venue:** {campus.get('venue', 'N/A')}")
        st.markdown(f"**Status:** {'🟢 Active' if campus.get('is_active') else '🔴 Inactive'}")

        st.divider()

        st.markdown("### 📍 Address & Details")
        st.markdown(f"**Address:** {campus.get('address', 'N/A')}")

        notes = campus.get('notes')
        if notes:
            st.markdown("**Notes:**")
            st.text(notes)

        st.divider()

        st.markdown("### 📅 Metadata")
        st.caption(f"Created: {campus.get('created_at', 'N/A')}")
        st.caption(f"Updated: {campus.get('updated_at', 'N/A')}")

        if st.button("✅ Close", use_container_width=True):
            del st.session_state[f'view_campus_modal_{campus_id}']
            st.rerun()

    view_modal()
