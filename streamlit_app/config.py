"""
Configuration file for LFA Education Center Streamlit App
BUILT FROM WORKING unified_workflow_dashboard.py patterns
"""

import streamlit as st

# API Configuration
API_BASE_URL = "http://localhost:8000"
API_TIMEOUT = 10  # Default timeout for API requests

# Session keys
SESSION_TOKEN_KEY = "token"
SESSION_USER_KEY = "user"
SESSION_ROLE_KEY = "role"

# Page config
PAGE_TITLE = "LFA Education Center"
PAGE_ICON = "⚽"
LAYOUT = "wide"

# Specializations (from working dashboard)
SPECIALIZATIONS = {
    # Lowercase versions (legacy)
    "lfa_player": "LFA Player",
    "lfa_coach": "LFA Coach",
    "lfa_internship": "LFA Internship",
    "gancuju_white": "Gancuju White Belt",
    "gancuju_yellow": "Gancuju Yellow Belt",
    "gancuju_green": "Gancuju Green Belt",
    "gancuju_blue": "Gancuju Blue Belt",
    "gancuju_brown": "Gancuju Brown Belt",
    "gancuju_black": "Gancuju Black Belt",
    # Uppercase versions (backend enum format)
    "LFA_PLAYER": "LFA Football Player",
    "LFA_PLAYER_PRE": "LFA Player PRE",
    "LFA_PLAYER_YOUTH": "LFA Player YOUTH",
    "LFA_PLAYER_AMATEUR": "LFA Player AMATEUR",
    "LFA_PLAYER_PRO": "LFA Player PRO",
    "INTERNSHIP": "Internship",
    "GANCUJU_PLAYER": "GānCuju Player",
    "LFA_COACH": "LFA Coach"
}

# Simple CSS - minimal styling + HIDE PAGE LIST (not sidebar)
CUSTOM_CSS = """
<style>
    /* Main content padding */
    .main {
        padding: 2rem;
    }

    /* Page title color */
    h1 {
        color: #1E40AF !important;
    }

    /* HIDE the page navigation list (Home, Admin Dashboard, etc.) */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }

    /* Fix metrics styling */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
    }

    /* Better card styling for expanders */
    .streamlit-expanderHeader {
        font-weight: 600 !important;
        background-color: rgba(28, 131, 225, 0.1) !important;
        border-radius: 0.5rem !important;
    }
</style>
"""
