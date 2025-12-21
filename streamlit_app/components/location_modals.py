"""
📍 Location Modals Component
Edit, View, and Create modals for Location Management
"""

import streamlit as st
from typing import Dict, Any, Optional
from datetime import datetime
from api_helpers import create_location, update_location


# ============================================================================
# CREATE LOCATION MODAL
# ============================================================================

def render_create_location_modal(token: str) -> bool:
    """
    Render create location modal
    Returns True if location was created
    """
    if 'create_location_modal' not in st.session_state or not st.session_state.create_location_modal:
        return False

    @st.dialog("➕ Create New Location", width="large")
    def create_modal():
        with st.form("create_location_form"):
            st.markdown("### 📍 Location Details")

            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input(
                    "Location Name *",
                    placeholder="LFA Education Center - Budapest",
                    help="Full name of the location"
                )

                city = st.text_input(
                    "City *",
                    placeholder="Budapest"
                )

                postal_code = st.text_input(
                    "Postal Code",
                    placeholder="1011"
                )

                country = st.text_input(
                    "Country *",
                    value="Hungary"
                )

            with col2:
                venue = st.text_input(
                    "Venue",
                    placeholder="Buda Campus",
                    help="Specific venue or building name"
                )

                address = st.text_area(
                    "Address",
                    placeholder="Fő utca 1.",
                    height=100
                )

                notes = st.text_area(
                    "Notes",
                    placeholder="Additional information...",
                    height=100
                )

                is_active = st.checkbox("Active", value=True)

            col1, col2 = st.columns(2)

            with col1:
                submit = st.form_submit_button("✅ Create Location", use_container_width=True, type="primary")

            with col2:
                cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

            if cancel:
                st.session_state.create_location_modal = False
                st.rerun()

            if submit:
                # Validation
                if not name or not city or not country:
                    st.error("❌ Name, City, and Country are required!")
                    return

                # Create location data
                location_data = {
                    "name": name,
                    "city": city,
                    "country": country,
                    "postal_code": postal_code if postal_code else None,
                    "venue": venue if venue else None,
                    "address": address if address else None,
                    "notes": notes if notes else None,
                    "is_active": is_active
                }

                # Call API
                success, error, response = create_location(token, location_data)

                if success:
                    st.success(f"✅ Location '{name}' created successfully!")
                    st.session_state.create_location_modal = False
                    st.rerun()
                else:
                    st.error(f"❌ Failed to create location: {error}")

    create_modal()
    return False


# ============================================================================
# EDIT LOCATION MODAL
# ============================================================================

def render_edit_location_modal(location: Dict[str, Any], token: str) -> bool:
    """
    Render edit location modal
    Returns True if location was updated
    """
    location_id = location.get('id')
    modal_key = f'edit_location_modal_{location_id}'

    if modal_key not in st.session_state or not st.session_state[modal_key]:
        return False

    @st.dialog(f"✏️ Edit Location: {location.get('name')}", width="large")
    def edit_modal():
        with st.form(f"edit_location_form_{location_id}"):
            st.markdown("### 📍 Location Details")

            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input(
                    "Location Name *",
                    value=location.get('name', ''),
                    help="Full name of the location"
                )

                city = st.text_input(
                    "City *",
                    value=location.get('city', '')
                )

                postal_code = st.text_input(
                    "Postal Code",
                    value=location.get('postal_code', '') or ''
                )

                country = st.text_input(
                    "Country *",
                    value=location.get('country', '')
                )

            with col2:
                venue = st.text_input(
                    "Venue",
                    value=location.get('venue', '') or '',
                    help="Specific venue or building name"
                )

                address = st.text_area(
                    "Address",
                    value=location.get('address', '') or '',
                    height=100
                )

                notes = st.text_area(
                    "Notes",
                    value=location.get('notes', '') or '',
                    height=100
                )

                is_active = st.checkbox(
                    "Active",
                    value=location.get('is_active', True)
                )

            col1, col2 = st.columns(2)

            with col1:
                submit = st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary")

            with col2:
                cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

            if cancel:
                st.session_state[modal_key] = False
                st.rerun()

            if submit:
                # Validation
                if not name or not city or not country:
                    st.error("❌ Name, City, and Country are required!")
                    return

                # Create update data
                update_data = {
                    "name": name,
                    "city": city,
                    "country": country,
                    "postal_code": postal_code if postal_code else None,
                    "venue": venue if venue else None,
                    "address": address if address else None,
                    "notes": notes if notes else None,
                    "is_active": is_active
                }

                # Call API
                success, error, response = update_location(token, location_id, update_data)

                if success:
                    st.success(f"✅ Location '{name}' updated successfully!")
                    st.session_state[modal_key] = False
                    st.rerun()
                else:
                    st.error(f"❌ Failed to update location: {error}")

    edit_modal()
    return False


# ============================================================================
# VIEW LOCATION DETAILS MODAL
# ============================================================================

def render_view_location_details(location: Dict[str, Any]) -> None:
    """
    Render detailed view modal for location
    """
    location_id = location.get('id')
    modal_key = f'view_location_modal_{location_id}'

    if modal_key not in st.session_state or not st.session_state[modal_key]:
        return

    @st.dialog(f"📍 Location Details: {location.get('name')}", width="large")
    def view_modal():
        # Basic Information
        st.markdown("### 📍 Basic Information")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**Location Name:** {location.get('name', 'N/A')}")
            st.markdown(f"**City:** {location.get('city', 'N/A')}")
            st.markdown(f"**Postal Code:** {location.get('postal_code') or 'N/A'}")
            st.markdown(f"**Country:** {location.get('country', 'N/A')}")

        with col2:
            st.markdown(f"**Venue:** {location.get('venue') or 'N/A'}")
            status_emoji = "🟢" if location.get('is_active') else "🔴"
            status_text = "Active" if location.get('is_active') else "Inactive"
            st.markdown(f"**Status:** {status_emoji} {status_text}")

        # Address & Notes
        st.divider()
        st.markdown("### 📮 Address & Notes")

        address = location.get('address')
        if address:
            st.markdown(f"**Address:**\n\n{address}")
        else:
            st.markdown("**Address:** N/A")

        notes = location.get('notes')
        if notes:
            st.markdown(f"**Notes:**\n\n{notes}")
        else:
            st.markdown("**Notes:** N/A")

        # Metadata
        st.divider()
        st.markdown("### 🕒 Metadata")
        col1, col2 = st.columns(2)

        with col1:
            created_at = location.get('created_at', 'N/A')
            if created_at and created_at != 'N/A':
                try:
                    created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    st.markdown(f"**Created:** {created_dt.strftime('%Y-%m-%d %H:%M')}")
                except:
                    st.markdown(f"**Created:** {created_at}")
            else:
                st.markdown("**Created:** N/A")

        with col2:
            updated_at = location.get('updated_at', 'N/A')
            if updated_at and updated_at != 'N/A':
                try:
                    updated_dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    st.markdown(f"**Updated:** {updated_dt.strftime('%Y-%m-%d %H:%M')}")
                except:
                    st.markdown(f"**Updated:** {updated_at}")
            else:
                st.markdown("**Updated:** N/A")

        # Close button
        if st.button("❌ Close", use_container_width=True):
            st.session_state[modal_key] = False
            st.rerun()

    view_modal()
