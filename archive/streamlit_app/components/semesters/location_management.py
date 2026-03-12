"""
Location Management Component
Manage LFA Education Center locations (create, list, toggle active/inactive)
Extracted from unified_workflow_dashboard.py lines 1626-1738
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from api_helpers_semesters import (
    get_all_locations,
    create_location,
    update_location
)


def render_location_management(token: str):
    """
    Render the location management interface
    - List all locations (expandable cards)
    - Toggle active/inactive
    - Create new location form

    Source: unified_workflow_dashboard.py lines 1626-1738
    """
    st.markdown("### 📍 LFA Education Center Locations")
    st.caption("Manage academy locations where semesters can be held")

    # Fetch all locations
    success, error, all_locations = get_all_locations(token, include_inactive=True)

    if success and all_locations:
        # Show existing locations
        st.markdown("#### 📋 Existing Locations")
        for loc in all_locations:
            status_icon = "✅" if loc['is_active'] else "❌"
            with st.expander(f"{status_icon} {loc['name']} ({loc['city']}, {loc['country']})"):
                st.markdown(f"**ID:** {loc['id']}")
                st.markdown(f"**City:** {loc['city']}")
                if loc.get('postal_code'):
                    st.markdown(f"**Postal Code:** {loc['postal_code']}")
                st.markdown(f"**Country:** {loc['country']}")
                if loc.get('venue'):
                    st.markdown(f"**Venue:** {loc['venue']}")
                if loc.get('address'):
                    st.markdown(f"**Address:** {loc['address']}")
                if loc.get('notes'):
                    st.markdown(f"**Notes:** {loc['notes']}")
                st.markdown(f"**Active:** {'Yes' if loc['is_active'] else 'No'}")

                # Toggle active status
                new_status = not loc['is_active']
                action_label = "Activate" if new_status else "Deactivate"

                if st.button(f"🔄 {action_label}", key=f"toggle_{loc['id']}"):
                    update_success, update_error, updated_loc = update_location(
                        token,
                        loc['id'],
                        {"is_active": new_status}
                    )

                    if update_success:
                        st.success(f"✅ Location {action_label.lower()}d successfully!")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to update location: {update_error}")
    elif success and not all_locations:
        st.info("📭 No locations created yet")
    else:
        st.error(f"❌ Failed to fetch locations: {error}")

    st.divider()

    # Create new location form
    st.markdown("#### ➕ Create New Location")

    with st.form("create_location_form"):
        new_name = st.text_input("Location Name *", placeholder="LFA Education Center - Budapest")

        col1, col2, col3 = st.columns(3)
        with col1:
            new_city = st.text_input("City *", placeholder="Budapest")
        with col2:
            new_postal_code = st.text_input("Postal Code", placeholder="1011")
        with col3:
            new_country = st.text_input("Country *", placeholder="Hungary")

        new_venue = st.text_input("Venue", placeholder="Buda Campus (optional)")
        new_address = st.text_input("Address", placeholder="Fő utca 1. (optional)")
        new_notes = st.text_area("Notes", placeholder="Additional information (optional)")
        new_is_active = st.checkbox("Active", value=True)

        create_btn = st.form_submit_button("➕ Create Location", use_container_width=True, type="primary")

        if create_btn:
            if not new_name or not new_city or not new_country:
                st.error("❌ Please fill in all required fields (Name, City, Country)")
            else:
                # Prepare location data
                location_data = {
                    "name": new_name,
                    "city": new_city,
                    "postal_code": new_postal_code if new_postal_code else None,
                    "country": new_country,
                    "venue": new_venue if new_venue else None,
                    "address": new_address if new_address else None,
                    "notes": new_notes if new_notes else None,
                    "is_active": new_is_active
                }

                create_success, create_error, created_location = create_location(token, location_data)

                if create_success:
                    st.success(f"✅ Location created: {created_location['name']}")
                    st.rerun()
                else:
                    st.error(f"❌ Failed to create location: {create_error}")
