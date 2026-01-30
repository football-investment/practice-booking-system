"""
Authentication Management for Streamlit UI

Handles:
- Token storage in session state
- Login/logout workflows
- User role checking
- Token validation
"""

import streamlit as st
from typing import Optional, Dict, Any
from .api_client import api_client, APIError


class AuthManager:
    """
    Centralized authentication manager for Streamlit apps.

    Usage:
        auth = AuthManager()
        if auth.login("user@example.com", "password"):
            st.success("Logged in!")
    """

    TOKEN_KEY = "auth_token"
    USER_KEY = "current_user"
    ROLE_KEY = "user_role"

    @staticmethod
    def is_authenticated() -> bool:
        """Check if user is currently authenticated"""
        return AuthManager.TOKEN_KEY in st.session_state and st.session_state[AuthManager.TOKEN_KEY] is not None

    @staticmethod
    def get_current_user() -> Optional[Dict[str, Any]]:
        """Get current user data from session state"""
        return st.session_state.get(AuthManager.USER_KEY)

    @staticmethod
    def get_user_role() -> Optional[str]:
        """Get current user role"""
        return st.session_state.get(AuthManager.ROLE_KEY)

    @staticmethod
    def has_role(role: str) -> bool:
        """
        Check if current user has specified role.

        Args:
            role: Role to check (ADMIN, INSTRUCTOR, USER)

        Returns:
            True if user has role
        """
        current_role = AuthManager.get_user_role()
        return current_role == role

    @staticmethod
    def is_admin() -> bool:
        """Check if current user is admin"""
        return AuthManager.has_role("ADMIN")

    @staticmethod
    def is_instructor() -> bool:
        """Check if current user is instructor"""
        return AuthManager.has_role("INSTRUCTOR")

    @staticmethod
    def login(email: str, password: str) -> bool:
        """
        Perform login and store credentials in session state.

        Args:
            email: User email
            password: User password

        Returns:
            True if login successful, False otherwise
        """
        try:
            # Call login endpoint
            response = api_client.post("/auth/login", data={
                "username": email,  # FastAPI OAuth2 uses 'username' field
                "password": password
            })

            # Store token and user data
            st.session_state[AuthManager.TOKEN_KEY] = response.get("access_token")
            st.session_state[AuthManager.USER_KEY] = response.get("user", {})
            st.session_state[AuthManager.ROLE_KEY] = response.get("user", {}).get("role")

            return True

        except APIError as e:
            st.error(f"Login failed: {e.message}")
            return False

    @staticmethod
    def logout():
        """Clear authentication data from session state"""
        if AuthManager.TOKEN_KEY in st.session_state:
            del st.session_state[AuthManager.TOKEN_KEY]
        if AuthManager.USER_KEY in st.session_state:
            del st.session_state[AuthManager.USER_KEY]
        if AuthManager.ROLE_KEY in st.session_state:
            del st.session_state[AuthManager.ROLE_KEY]

    @staticmethod
    def require_auth():
        """
        Require authentication for current page.
        Shows login form if not authenticated.
        """
        if not AuthManager.is_authenticated():
            st.warning("Please log in to continue")
            AuthManager.show_login_form()
            st.stop()

    @staticmethod
    def require_role(role: str):
        """
        Require specific role for current page.
        Shows error if user doesn't have role.

        Args:
            role: Required role (ADMIN, INSTRUCTOR, USER)
        """
        AuthManager.require_auth()

        if not AuthManager.has_role(role):
            st.error(f"This page requires {role} role")
            st.stop()

    @staticmethod
    def show_login_form():
        """Display login form"""
        with st.form("login_form"):
            st.subheader("Login")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")

            if submit:
                if AuthManager.login(email, password):
                    st.success("Login successful!")
                    st.rerun()

    @staticmethod
    def show_user_info():
        """Display current user info in sidebar"""
        if AuthManager.is_authenticated():
            user = AuthManager.get_current_user()
            if user:
                st.sidebar.markdown("---")
                st.sidebar.markdown(f"**User:** {user.get('email', 'Unknown')}")
                st.sidebar.markdown(f"**Role:** {user.get('role', 'Unknown')}")

                if st.sidebar.button("Logout"):
                    AuthManager.logout()
                    st.rerun()


# Singleton instance
auth = AuthManager()
