"""
📍 Location Modals Component
Edit, View, and Create modals for Location Management
"""

import streamlit as st
from typing import Dict, Any, Optional, List
from datetime import datetime
import time
from api_helpers_general import create_location, update_location, get_locations


# ============================================================================
# CREATE LOCATION MODAL - SIMPLE SINGLE-STEP CREATION
# ============================================================================

def render_create_location_modal(token: str) -> bool:
    """
    Render single-step location creation form
    Creates location immediately. Campuses can be added afterwards via Edit modal.
    Returns True if location was created
    """
    if 'create_location_modal' not in st.session_state or not st.session_state.create_location_modal:
        return False

    # Initialize wizard state
    if 'location_wizard_data' not in st.session_state:
        st.session_state.location_wizard_data = {}

    @st.dialog("➕ Create New Location", width="large")
    def create_modal():
        st.markdown("### 📍 Location Details")
        st.info("💡 **Tip:** After creating the location, you can add campuses in the Edit modal.")

        with st.form("location_details_form"):
                col1, col2 = st.columns(2)

                with col1:
                    city = st.text_input(
                        "City *",
                        value=st.session_state.location_wizard_data.get('city', ''),
                        placeholder="Budapest",
                        help="City name (will be used in display name)"
                    )

                    country = st.text_input(
                        "Country *",
                        value=st.session_state.location_wizard_data.get('country', 'Hungary'),
                        placeholder="Hungary"
                    )

                    country_code = st.text_input(
                        "Country Code *",
                        value=st.session_state.location_wizard_data.get('country_code', ''),
                        placeholder="HU",
                        max_chars=2,
                        help="2-letter ISO country code (e.g., HU, AT, SK)"
                    ).upper()

                    location_code = st.text_input(
                        "Location Code *",
                        value=st.session_state.location_wizard_data.get('location_code', ''),
                        placeholder="BDPST",
                        max_chars=10,
                        help="Unique location identifier (e.g., BDPST for Budapest)"
                    ).upper()

                    postal_code = st.text_input(
                        "Postal Code",
                        value=st.session_state.location_wizard_data.get('postal_code', ''),
                        placeholder="1011"
                    )

                with col2:
                    venue = st.text_input(
                        "Venue",
                        value=st.session_state.location_wizard_data.get('venue', ''),
                        placeholder="Main Building",
                        help="Specific venue or building name"
                    )

                    # Location Type dropdown (PARTNER or CENTER)
                    current_type = st.session_state.location_wizard_data.get('location_type', 'CENTER')
                    type_index = 0 if current_type == 'CENTER' else 1
                    location_type = st.selectbox(
                        "Location Type *",
                        options=["CENTER", "PARTNER"],
                        index=type_index,
                        help="CENTER: Full capabilities (Mini Seasons + Academy + Tournaments). PARTNER: Limited capabilities (Mini Seasons + Tournaments only)"
                    )

                    address = st.text_area(
                        "Address",
                        value=st.session_state.location_wizard_data.get('address', ''),
                        placeholder="Fő utca 1.",
                        height=80
                    )

                    notes = st.text_area(
                        "Notes",
                        value=st.session_state.location_wizard_data.get('notes', ''),
                        placeholder="Additional information...",
                        height=60
                    )

                    is_active = st.checkbox(
                        "Active",
                        value=st.session_state.location_wizard_data.get('is_active', True)
                    )

                col1, col2 = st.columns(2)

                with col1:
                    cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

                with col2:
                    submit = st.form_submit_button("✅ Create Location", use_container_width=True, type="primary")

                if cancel:
                    # Reset wizard state
                    st.session_state.create_location_modal = False
                    st.session_state.location_wizard_data = {}
                    st.rerun()

                if submit:
                    # Validation
                    if not city or not country or not country_code or not location_code:
                        st.error("❌ City, Country, Country Code, and Location Code are required!")
                    else:
                        # Generate display name: 🇭🇺 HU - Budapest
                        def get_flag_emoji(code):
                            if len(code) == 2:
                                return chr(ord(code[0]) + 127397) + chr(ord(code[1]) + 127397)
                            return "🌍"

                        flag = get_flag_emoji(country_code.upper())
                        name = f"{flag} {country_code.upper()} - {city}"

                        # Check for duplicate location code
                        success, existing_locations = get_locations(token, include_inactive=True)
                        duplicate_found = False
                        if success and existing_locations:
                            existing_codes = [loc.get('location_code') for loc in existing_locations if loc.get('location_code')]
                            if location_code.upper() in existing_codes:
                                st.error(f"❌ Location code '{location_code.upper()}' already exists! Please choose a different code.")
                                duplicate_found = True

                        if not duplicate_found:
                            # Create location data
                            location_data = {
                                "name": name,
                                "city": city,
                                "country": country,
                                "country_code": country_code.upper(),
                                "location_code": location_code.upper(),
                                "location_type": location_type,
                                "postal_code": postal_code if postal_code else None,
                                "venue": venue if venue else None,
                                "address": address if address else None,
                                "notes": notes if notes else None,
                                "is_active": is_active
                            }

                            # Create location immediately
                            success, error, response = create_location(token, location_data)

                            if success:
                                st.success(f"✅ Location '{name}' created successfully!")
                                st.info("💡 You can now add campuses in the Edit modal.")
                                time.sleep(2)
                                # Reset wizard state
                                st.session_state.create_location_modal = False
                                st.session_state.location_wizard_data = {}
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to create location: {error}")

    create_modal()
    return False


# ============================================================================
# EDIT LOCATION MODAL - WITH CAMPUS MANAGEMENT
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
        # Location Details Form
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

                # Location Type dropdown (PARTNER or CENTER)
                current_location_type = location.get('location_type', 'CENTER')
                location_type_index = 0 if current_location_type == 'CENTER' else 1
                location_type = st.selectbox(
                    "Location Type *",
                    options=["CENTER", "PARTNER"],
                    index=location_type_index,
                    help="CENTER: Full capabilities (Mini Seasons + Academy + Tournaments). PARTNER: Limited capabilities (Mini Seasons + Tournaments only)"
                )

                address = st.text_area(
                    "Address",
                    value=location.get('address', '') or '',
                    height=80
                )

                notes = st.text_area(
                    "Notes",
                    value=location.get('notes', '') or '',
                    height=60
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

                # Check for duplicate location name (only if name is being changed)
                if name != location.get('name'):
                    success, existing_locations = get_locations(token, include_inactive=True)
                    if success and existing_locations:
                        existing_names = [loc.get('name') for loc in existing_locations if loc.get('id') != location_id]
                        if name in existing_names:
                            st.error(f"❌ Location '{name}' already exists! Please choose a different name.")
                            return

                # Create update data
                update_data = {
                    "name": name,
                    "city": city,
                    "country": country,
                    "location_type": location_type,
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
