"""
Instructor Dashboard — Tab 4: My Students
==========================================

Phase 3 extraction Step 3.3.
Displays students enrolled in the instructor's master-led semesters.
Only active Master Instructors have student data; others see an info panel.

Public API:
    render_students_tab(token)
"""

from __future__ import annotations

from typing import Dict, Any

import streamlit as st

from api_helpers_instructors import get_my_master_offers


def render_students_tab(token: str) -> None:
    """Render the 'My Students' tab content.

    Args:
        token: Bearer JWT for the authenticated instructor.
    """
    st.markdown("### 👥 My Students")
    st.caption("Students enrolled in your master-led semesters")

    # Check if user is an active Master Instructor
    with st.spinner("Checking master instructor status..."):
        try:
            my_offers = get_my_master_offers(token, include_expired=False)
            active_master_offers = [
                o for o in my_offers
                if o.get('offer_status') == 'ACCEPTED' and o.get('is_active')
            ]
        except Exception:
            active_master_offers = []

    if not active_master_offers:
        # Not a Master Instructor — show info message
        st.info("👨‍🏫 **Master Instructor Only**")
        st.markdown("""
        This section is only available when you are an **active Master Instructor** at a training location.

        **How to become a Master Instructor:**
        1. Check the "📩 Master Offers" tab for pending invitations
        2. Accept an offer from a training location
        3. Once accepted, you'll see your students here

        **Current Status:** Not currently serving as Master Instructor
        """)
        return

    # Active Master Instructor — show students
    master_location = active_master_offers[0].get('location_name', 'Unknown Location')
    master_city = active_master_offers[0].get('location_city', '')

    st.success(f"✅ Master Instructor at: **{master_location}** ({master_city})")

    with st.spinner("Loading students..."):
        # TODO: Implement proper endpoint to get students for master's semesters
        st.info("🚧 Student management feature coming soon")
        st.caption("This will show all students enrolled in semesters at your location.")

    # FUTURE: Replace with actual student query
    # success, students = get_master_students(token, location_id)
    # Display students with same pattern as before
