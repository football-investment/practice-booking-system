"""
Admin Dashboard - Tournaments Tab Component
Tournaments management (sessions auto-generated)
"""

import streamlit as st
from pathlib import Path
import sys

# Setup imports
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

# Tournament components
from components.tournaments.player_tournament_generator import render_tournament_generator
from components.admin.tournament_list import render_tournament_list


def render_tournaments_tab(token, user):
    """
    Render the Tournaments tab with tournament management features.

    Parameters:
    - token: API authentication token
    - user: Authenticated user object
    """
    st.header("🏆 Tournament Management")
    st.caption("ℹ️ Tournament sessions are auto-generated when status changes to IN_PROGRESS")

    # 2-tab layout (removed "Manage Games" - sessions are auto-generated)
    tab1, tab2 = st.tabs([
        "📋 View Tournaments",
        "➕ Create Tournament"
    ])

    with tab1:
        render_tournament_list(token)

    with tab2:
        render_tournament_generator()
