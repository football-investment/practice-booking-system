"""
📍 Location Modals Component
Edit, View, and Create modals for Location Management
"""

import streamlit as st
from typing import Dict, Any, Optional, List
from datetime import datetime
from api_helpers_general import create_location, update_location, create_campus, get_locations


# ============================================================================
# CREATE LOCATION MODAL - TWO-STEP WIZARD
# ============================================================================

def render_create_location_modal(token: str) -> bool:
    """
    Render two-step location creation wizard
    Step 1: Location details
    Step 2: Add campuses (optional, but recommended)
    Returns True if location was created
    """
    if 'create_location_modal' not in st.session_state or not st.session_state.create_location_modal:
        return False

    # Initialize wizard state
    if 'location_wizard_step' not in st.session_state:
        st.session_state.location_wizard_step = 1
    if 'location_wizard_data' not in st.session_state:
        st.session_state.location_wizard_data = {}
    if 'location_wizard_campuses' not in st.session_state:
        st.session_state.location_wizard_campuses = []

    @st.dialog("➕ Create New Location", width="large")
    def create_modal():
        current_step = st.session_state.location_wizard_step

        # Progress indicator
        st.progress(current_step / 2, text=f"Step {current_step} of 2")
        st.divider()

        # =====================================================================
        # STEP 1: LOCATION DETAILS
        # =====================================================================
        if current_step == 1:
            st.markdown("### 📍 Step 1: Location Details")

            with st.form("location_details_form"):
                col1, col2 = st.columns(2)

                with col1:
                    name = st.text_input(
                        "Location Name *",
                        value=st.session_state.location_wizard_data.get('name', ''),
                        placeholder="LFA Education Center - Budapest",
                        help="Full name of the location"
                    )

                    city = st.text_input(
                        "City *",
                        value=st.session_state.location_wizard_data.get('city', ''),
                        placeholder="Budapest"
                    )

                    postal_code = st.text_input(
                        "Postal Code",
                        value=st.session_state.location_wizard_data.get('postal_code', ''),
                        placeholder="1011"
                    )

                    country = st.text_input(
                        "Country *",
                        value=st.session_state.location_wizard_data.get('country', 'Hungary'),
                        placeholder="Hungary"
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
                    next_step = st.form_submit_button("Next: Add Campuses →", use_container_width=True, type="primary")

                if cancel:
                    # Reset wizard state
                    st.session_state.create_location_modal = False
                    st.session_state.location_wizard_step = 1
                    st.session_state.location_wizard_data = {}
                    st.session_state.location_wizard_campuses = []
                    st.rerun()

                if next_step:
                    # Validation
                    if not name or not city or not country:
                        st.error("❌ Name, City, and Country are required!")
                    else:
                        # Check for duplicate location name
                        success, existing_locations = get_locations(token, include_inactive=True)
                        duplicate_found = False
                        if success and existing_locations:
                            existing_names = [loc.get('name') for loc in existing_locations]
                            if name in existing_names:
                                st.error(f"❌ Location '{name}' already exists! Please choose a different name.")
                                duplicate_found = True

                        if not duplicate_found:
                            # Save step 1 data
                            st.session_state.location_wizard_data = {
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
                            st.session_state.location_wizard_step = 2
                            st.rerun()

        # =====================================================================
        # STEP 2: ADD CAMPUSES
        # =====================================================================
        elif current_step == 2:
            st.markdown("### 🏫 Step 2: Add Campuses (Optional)")
            st.caption(f"Location: **{st.session_state.location_wizard_data.get('name')}**")

            # Display current campuses
            if st.session_state.location_wizard_campuses:
                st.markdown(f"**Campuses to create ({len(st.session_state.location_wizard_campuses)}):**")
                for idx, campus in enumerate(st.session_state.location_wizard_campuses):
                    with st.expander(f"🏫 {campus['name']}", expanded=False):
                        st.markdown(f"**Venue:** {campus.get('venue', 'N/A')}")
                        st.markdown(f"**Address:** {campus.get('address', 'N/A')}")
                        if campus.get('notes'):
                            st.markdown(f"**Notes:** {campus['notes']}")
                        if st.button(f"🗑️ Remove", key=f"remove_campus_{idx}"):
                            st.session_state.location_wizard_campuses.pop(idx)
                            st.rerun()
            else:
                st.info("📍 No campuses added yet. Add at least one campus or skip to create location only.")

            st.divider()

            # Add new campus form
            with st.form("add_campus_form"):
                st.markdown("**➕ Add New Campus:**")

                col1, col2 = st.columns(2)

                with col1:
                    campus_name = st.text_input(
                        "Campus Name *",
                        placeholder="Main Campus",
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

                campus_is_active = st.checkbox("Active", value=True, key="campus_active")

                add_campus_btn = st.form_submit_button("➕ Add Campus", use_container_width=True)

                if add_campus_btn:
                    if not campus_name:
                        st.error("❌ Campus name is required!")
                    else:
                        # Check if campus name already exists in pending list
                        pending_names = [c['name'] for c in st.session_state.location_wizard_campuses]
                        if campus_name in pending_names:
                            st.error(f"❌ Campus '{campus_name}' is already in the list!")
                        else:
                            # Add campus to list
                            new_campus = {
                                "name": campus_name,
                                "venue": campus_venue if campus_venue else None,
                                "address": campus_address if campus_address else None,
                                "notes": campus_notes if campus_notes else None,
                                "is_active": campus_is_active
                            }
                            st.session_state.location_wizard_campuses.append(new_campus)
                            st.success(f"✅ Campus '{campus_name}' added!")
                            st.rerun()

            st.divider()

            # Navigation buttons
            col1, col2 = st.columns(2)

            with col1:
                if st.button("← Back", use_container_width=True):
                    st.session_state.location_wizard_step = 1
                    st.rerun()

            with col2:
                if st.button("✅ Create Location & Campuses", use_container_width=True, type="primary"):
                    # Create location first
                    success, error, response = create_location(token, st.session_state.location_wizard_data)

                    if success:
                        location_id = response.get('id')
                        location_name = response.get('name')

                        # Create campuses if any (BEFORE showing any success messages)
                        campus_success_list = []
                        campus_errors = []

                        if st.session_state.location_wizard_campuses:
                            for campus_data in st.session_state.location_wizard_campuses:
                                campus_success, campus_error, _ = create_campus(token, location_id, campus_data)
                                if not campus_success:
                                    campus_errors.append(f"❌ {campus_data['name']}: {campus_error}")
                                else:
                                    campus_success_list.append(campus_data['name'])

                        # NOW show all success messages at once (after ALL API calls complete)
                        st.success(f"✅ Location '{location_name}' created successfully!")

                        for campus_name in campus_success_list:
                            st.success(f"✅ Campus '{campus_name}' created!")

                        if campus_errors:
                            st.warning("⚠️ Some campuses failed to create:")
                            for error in campus_errors:
                                st.caption(error)

                        # Reset wizard state and refresh (ONLY after all operations complete)
                        st.session_state.create_location_modal = False
                        st.session_state.location_wizard_step = 1
                        st.session_state.location_wizard_data = {}
                        st.session_state.location_wizard_campuses = []
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
    Render edit location modal with campus management
    Returns True if location was updated
    """
    from api_helpers_general import get_campuses_by_location

    location_id = location.get('id')
    modal_key = f'edit_location_modal_{location_id}'

    if modal_key not in st.session_state or not st.session_state[modal_key]:
        return False

    # Initialize campus list for this edit session
    if f'edit_campuses_to_add_{location_id}' not in st.session_state:
        st.session_state[f'edit_campuses_to_add_{location_id}'] = []

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
                st.session_state[f'edit_campuses_to_add_{location_id}'] = []
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
                    st.session_state[f'edit_campuses_to_add_{location_id}'] = []
                    st.rerun()
                else:
                    st.error(f"❌ Failed to update location: {error}")

        # CAMPUS MANAGEMENT SECTION (Outside the location form)
        st.divider()
        st.markdown("### 🏫 Campus Management")

        # Load existing campuses
        campus_success, campuses = get_campuses_by_location(token, location_id, include_inactive=True)

        if campus_success and campuses:
            st.markdown(f"**Existing Campuses ({len(campuses)}):**")
            for campus in campuses:
                campus_status = "🟢" if campus.get('is_active') else "🔴"
                st.caption(f"{campus_status} {campus.get('name')}")
        else:
            st.info("No campuses found for this location")

        # New campuses to add
        if st.session_state[f'edit_campuses_to_add_{location_id}']:
            st.markdown(f"**New Campuses to Add ({len(st.session_state[f'edit_campuses_to_add_{location_id}'])}):**")
            for idx, campus in enumerate(st.session_state[f'edit_campuses_to_add_{location_id}']):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.caption(f"🏫 {campus['name']}")
                with col2:
                    if st.button("🗑️", key=f"remove_new_campus_{location_id}_{idx}"):
                        st.session_state[f'edit_campuses_to_add_{location_id}'].pop(idx)
                        st.rerun()

        st.divider()

        # Add new campus form
        with st.form(f"add_campus_to_location_{location_id}"):
            st.markdown("**➕ Add New Campus:**")

            col1, col2 = st.columns(2)

            with col1:
                campus_name = st.text_input(
                    "Campus Name *",
                    placeholder="New Campus",
                    help="Campus name within this location",
                    key=f"edit_campus_name_{location_id}"
                )

                campus_venue = st.text_input(
                    "Venue",
                    placeholder="Building A",
                    help="Specific venue or building",
                    key=f"edit_campus_venue_{location_id}"
                )

            with col2:
                campus_address = st.text_area(
                    "Address",
                    placeholder="Fő utca 1., 2. emelet",
                    height=60,
                    key=f"edit_campus_address_{location_id}"
                )

                campus_notes = st.text_area(
                    "Notes",
                    placeholder="Additional information...",
                    height=60,
                    key=f"edit_campus_notes_{location_id}"
                )

            campus_is_active = st.checkbox("Active", value=True, key=f"campus_active_edit_{location_id}")

            add_campus_btn = st.form_submit_button("➕ Add Campus", use_container_width=True)

            if add_campus_btn:
                if not campus_name:
                    st.error("❌ Campus name is required!")
                else:
                    # Check if campus name already exists in pending list
                    pending_names = [c['name'] for c in st.session_state[f'edit_campuses_to_add_{location_id}']]
                    if campus_name in pending_names:
                        st.error(f"❌ Campus '{campus_name}' is already in the pending list!")
                    # Check if campus name already exists in database
                    elif campuses and any(c.get('name') == campus_name for c in campuses):
                        st.error(f"❌ Campus '{campus_name}' already exists in this location!")
                    else:
                        # Add campus to pending list
                        new_campus = {
                            "name": campus_name,
                            "venue": campus_venue if campus_venue else None,
                            "address": campus_address if campus_address else None,
                            "notes": campus_notes if campus_notes else None,
                            "is_active": campus_is_active
                        }
                        st.session_state[f'edit_campuses_to_add_{location_id}'].append(new_campus)
                        st.success(f"✅ Campus '{campus_name}' added to list!")
                        st.rerun()

        # Create all pending campuses button
        if st.session_state[f'edit_campuses_to_add_{location_id}']:
            st.divider()
            if st.button(f"✅ Create {len(st.session_state[f'edit_campuses_to_add_{location_id}'])} New Campus(es)",
                        use_container_width=True,
                        type="primary"):
                campus_success_list = []
                campus_errors = []

                for campus_data in st.session_state[f'edit_campuses_to_add_{location_id}']:
                    campus_success, campus_error, _ = create_campus(token, location_id, campus_data)
                    if not campus_success:
                        campus_errors.append(f"❌ {campus_data['name']}: {campus_error}")
                    else:
                        campus_success_list.append(campus_data['name'])

                # Show results
                for campus_name in campus_success_list:
                    st.success(f"✅ Campus '{campus_name}' created!")

                if campus_errors:
                    st.warning("⚠️ Some campuses failed to create:")
                    for error in campus_errors:
                        st.caption(error)

                # Clear pending list and refresh
                st.session_state[f'edit_campuses_to_add_{location_id}'] = []
                st.rerun()

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
