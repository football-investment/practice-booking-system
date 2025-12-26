"""
Admin Dashboard - Locations Tab Component
Locations and campuses management
"""

import streamlit as st
from pathlib import Path
import sys

# Setup imports
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from api_helpers import get_locations, get_campuses_by_location
from components.location_filters import render_location_filters, apply_location_filters
from components.location_actions import render_location_action_buttons
from components.campus_actions import render_campus_action_buttons
from components.location_modals import render_create_location_modal


def render_locations_tab(token, user):
    """
    Render the Locations tab with location and campus management.

    Parameters:
    - token: API authentication token
    - user: Authenticated user object
    """

    # Load locations FIRST (before rendering any UI)
    with st.spinner("Loading locations..."):
        success, locations = get_locations(token, include_inactive=True)

    # Main layout with sidebar filters
    filter_col, main_col = st.columns([1, 3])

    # Sidebar: Filters (render ONCE with loaded data)
    with filter_col:
        # Create button in sidebar
        st.markdown("### ➕ Actions")
        if st.button("➕ Create Location", use_container_width=True, type="primary"):
            st.session_state.create_location_modal = True
            st.rerun()

        st.divider()

        # Filters below create button (render ONCE)
        if success and locations:
            location_filters = render_location_filters(locations)
        else:
            location_filters = render_location_filters([])

    # Main area: Location cards
    with main_col:
        st.markdown("### 📍 Location Management")
        st.caption("Manage LFA Education Center locations")

        if success and locations:
            # Apply filters
            filtered_locations = apply_location_filters(locations, location_filters)

            # Stats widgets
            active_locations = [loc for loc in filtered_locations if loc.get('is_active', False)]
            inactive_locations = [loc for loc in filtered_locations if not loc.get('is_active', False)]

            stats_col1, stats_col2, stats_col3 = st.columns(3)
            with stats_col1:
                st.metric("📍 Total", len(filtered_locations))
            with stats_col2:
                st.metric("🟢 Active", len(active_locations))
            with stats_col3:
                st.metric("🔴 Inactive", len(inactive_locations))

            st.divider()

            # Location cards with action buttons
            if filtered_locations:
                st.caption(f"📋 Showing {len(filtered_locations)} location(s):")
                for location in filtered_locations:
                    location_id = location.get('id')
                    is_active = location.get('is_active', False)
                    status_emoji = "🟢" if is_active else "🔴"
                    name = location.get('name', 'Unknown Location')

                    with st.expander(f"{status_emoji} **{name}** (ID: {location_id})"):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.markdown("**📍 Location Info**")
                            st.caption(f"Name: {location.get('name', 'N/A')}")
                            st.caption(f"City: {location.get('city', 'N/A')}")
                            st.caption(f"Country: {location.get('country', 'N/A')}")

                        with col2:
                            st.markdown("**📮 Address Details**")
                            postal_code = location.get('postal_code') or 'N/A'
                            st.caption(f"Postal Code: {postal_code}")
                            venue = location.get('venue') or 'N/A'
                            st.caption(f"Venue: {venue}")

                        with col3:
                            st.markdown("**✅ Status**")
                            st.caption(f"Status: {'✅ Active' if is_active else '❌ Inactive'}")

                            # Address preview
                            address = location.get('address')
                            if address:
                                address_preview = address[:30] + "..." if len(address) > 30 else address
                                st.caption(f"Address: {address_preview}")

                        # Notes preview
                        notes = location.get('notes')
                        if notes:
                            st.markdown("**📝 Notes:**")
                            notes_preview = notes[:80] + "..." if len(notes) > 80 else notes
                            st.caption(notes_preview)

                        st.divider()

                        # CAMPUSES WITHIN THIS LOCATION
                        st.markdown("**🏫 Campuses at this location:**")
                        campus_success, campuses = get_campuses_by_location(token, location_id, include_inactive=True)

                        if campus_success and campuses:
                            # Display each campus in an expander with action buttons
                            for campus in campuses:
                                campus_status_emoji = "🟢" if campus.get('is_active') else "🔴"
                                campus_name = campus.get('name', 'Unknown Campus')
                                campus_id = campus.get('id')

                                # Campus expander
                                with st.expander(f"{campus_status_emoji} **{campus_name}** (Campus ID: {campus_id})"):
                                    col1, col2 = st.columns(2)

                                    with col1:
                                        st.markdown("**📍 Campus Info**")
                                        st.caption(f"Name: {campus.get('name', 'N/A')}")
                                        st.caption(f"Venue: {campus.get('venue', 'N/A')}")

                                    with col2:
                                        st.markdown("**✅ Status**")
                                        st.caption(f"Status: {'🟢 Active' if campus.get('is_active') else '🔴 Inactive'}")
                                        address = campus.get('address')
                                        if address:
                                            address_preview = address[:30] + "..." if len(address) > 30 else address
                                            st.caption(f"Address: {address_preview}")

                                    # Notes preview
                                    notes = campus.get('notes')
                                    if notes:
                                        st.markdown("**📝 Notes:**")
                                        notes_preview = notes[:50] + "..." if len(notes) > 50 else notes
                                        st.caption(notes_preview)

                                    st.divider()
                                    # Action buttons
                                    render_campus_action_buttons(campus, location_id, token)
                        elif campus_success and not campuses:
                            st.caption("  ⚠️ No campuses found for this location")
                        else:
                            st.caption(f"  ❌ Error loading campuses: {campuses}")

                        st.divider()
                        # Action buttons (from compact component)
                        render_location_action_buttons(location, token)
            else:
                st.info("No locations match the selected filters")

        elif success and not locations:
            st.info("📍 No locations found. Create your first location!")
        else:
            st.error("❌ Failed to load locations")

        # Render create modal if open
        render_create_location_modal(token)
