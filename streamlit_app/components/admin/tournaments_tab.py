"""
Admin Dashboard - Tournaments Tab Component
Tournaments management
"""

import streamlit as st
from pathlib import Path
import sys

# Setup imports
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

# Tournament components
from components.tournaments.player_tournament_generator import render_tournament_generator


def render_tournaments_tab(token, user):
    """
    Render the Tournaments tab with tournament management features.

    Parameters:
    - token: API authentication token
    - user: Authenticated user object
    """

    render_tournament_generator()
