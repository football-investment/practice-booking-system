"""
Standalone Tournament List Test Wrapper

This wrapper app is used for E2E testing of the tournament_list component.
It initializes the component library and renders the tournament list view.
"""

import streamlit as st
from pathlib import Path
import sys

# Setup path
parent_dir = Path(__file__).parent
sys.path.insert(0, str(parent_dir))

# Import component
from streamlit_app.components.admin.tournament_list import render_tournament_list

# Import auth
from streamlit_components.core.auth import AuthManager

# Page config
st.set_page_config(
    page_title="Tournament List - Test",
    page_icon="🏆",
    layout="wide"
)

def main():
    """Main test wrapper"""
    # Auto-login for testing (admin)
    if not AuthManager.is_authenticated():
        # Auto-authenticate as admin for testing
        st.session_state["auth_token"] = "test_token"
        st.session_state["current_user"] = {
            "id": 1,
            "email": "admin@lfa.com",
            "role": "ADMIN",
            "name": "Admin User"
        }
        st.session_state["user_role"] = "ADMIN"

    # Render tournament list
    render_tournament_list()

if __name__ == "__main__":
    main()
