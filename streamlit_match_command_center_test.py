"""
Standalone Match Command Center Test Wrapper

This wrapper app is used for E2E testing of the match_command_center component.
It initializes the component library and renders the match command center view.
"""

import streamlit as st
from pathlib import Path
import sys

# Setup path
parent_dir = Path(__file__).parent
sys.path.insert(0, str(parent_dir))

# Import component
from streamlit_app.components.tournaments.instructor.match_command_center import render_match_command_center

# Import auth
from streamlit_components.core.auth import AuthManager

# Page config
st.set_page_config(
    page_title="Match Command Center - Test",
    page_icon="🎮",
    layout="wide"
)

def main():
    """Main test wrapper"""
    # Auto-login for testing (instructor)
    if not AuthManager.is_authenticated():
        # Auto-authenticate as instructor for testing
        st.session_state["auth_token"] = "test_token"
        st.session_state["current_user"] = {
            "id": 3,
            "email": "grandmaster@lfa.com",
            "role": "INSTRUCTOR",
            "name": "Grandmaster"
        }
        st.session_state["user_role"] = "INSTRUCTOR"

    # Get tournament ID from query params or default
    tournament_id = st.query_params.get("tournament_id", 1)

    # Render match command center
    render_match_command_center(int(tournament_id))

if __name__ == "__main__":
    main()
