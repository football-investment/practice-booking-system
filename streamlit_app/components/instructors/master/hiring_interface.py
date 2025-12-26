"""Hiring Interface Component - Dual pathway hiring system orchestrator"""

import streamlit as st
import sys
sys.path.append('..')

from pathway_a import render_direct_hire_tab
from pathway_b import render_post_opening_tab


def render_hiring_interface(location_id: int, token: str) -> None:
    """
    Render dual-pathway hiring interface with tabs

    Presents two options:
    - PATHWAY A: Direct Hire (admin invites specific instructor)
    - PATHWAY B: Job Posting (admin posts opening, instructors apply)

    Args:
        location_id: ID of the location
        token: Authentication token
    """

    # Call-to-action banner
    st.info("**No master instructor assigned to this location.**\n\nA master instructor is required to manage semesters, post positions, and hire assistant instructors.")

    st.divider()

    # Dual pathway tabs
    tab1, tab2 = st.tabs(["Direct Hire", "Post Opening"])

    with tab1:
        render_direct_hire_tab(location_id, token)

    with tab2:
        render_post_opening_tab(location_id, token)
