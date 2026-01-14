"""
Admin Dashboard - Tournaments Tab Component
Tournaments management with game type editing
"""

import streamlit as st
from pathlib import Path
import sys

# Setup imports
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

# Tournament components
from components.tournaments.player_tournament_generator import render_tournament_generator
from components.admin.tournament_list import render_tournament_list, render_game_type_manager


def render_tournaments_tab(token, user):
    """
    Render the Tournaments tab with tournament management features.

    Parameters:
    - token: API authentication token
    - user: Authenticated user object
    """
    st.header("🏆 Tournament Management")

    # 3-tab layout
    tab1, tab2, tab3 = st.tabs([
        "📋 View Tournaments",
        "➕ Create Tournament",
        "⚙️ Manage Games"
    ])

    with tab1:
        render_tournament_list(token)

    with tab2:
        render_tournament_generator()

    with tab3:
        render_game_type_manager(token)
