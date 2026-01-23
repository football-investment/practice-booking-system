"""
Instructor Integration
======================

Functions for integrating instructor management with the smart matrix view.

- Render instructor panel
- Render master instructor section
- Get master instructor status
"""

import streamlit as st
from components.instructors import (
    render_instructor_panel,
    render_master_section
)
from components.instructors.master_section import get_master_status


def render_master_instructor_section(location_id: int, token: str):
    """
    Render the master instructor section for a location

    Shows:
    - Master instructor status (active, expiring, no master)
    - Master hiring workflow
    - Contract details

    Args:
        location_id: Location ID
        token: Auth token
    """
    # Get master status for dynamic title and expand state
    master_status = get_master_status(location_id, token)

    # Dynamic expander title based on status
    if master_status == "active":
        expander_title = "Master Instructor (Active)"
        should_expand = False  # Don't expand if everything is fine
    elif master_status == "expiring":
        expander_title = "Master Instructor (Contract Expiring Soon)"
        should_expand = True  # Expand to draw attention
    else:  # no_master
        expander_title = "Master Instructor (No Master Assigned)"
        should_expand = True  # Expand to encourage hiring

    with st.expander(expander_title, expanded=should_expand):
        render_master_section(location_id, token)


def render_instructor_management_panel(
    location_id: int,
    year: int,
    token: str,
    user_role: str = "admin",
    is_master: bool = False
):
    """
    Render the instructor management panel

    Shows:
    - Instructor assignments for the location
    - Quick hire/assign actions
    - Instructor status

    Args:
        location_id: Location ID
        year: Year to filter instructors
        token: Auth token
        user_role: User role (admin, instructor, etc.)
        is_master: Whether current user is master instructor
    """
    render_instructor_panel(
        location_id=location_id,
        year=year,
        token=token,
        user_role=user_role,
        is_master=is_master
    )
