"""
Streamlit State Management Helpers

Provides utilities for managing Streamlit session state with:
- Type-safe state access
- Default value handling
- State initialization helpers
- Common state patterns
"""

import streamlit as st
from typing import Any, Optional, Dict, Callable


class StateManager:
    """
    Helper class for managing Streamlit session state.

    Usage:
        state = StateManager()
        state.set("tournament_id", 123)
        tournament_id = state.get("tournament_id", default=None)
    """

    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """
        Get value from session state with default.

        Args:
            key: State key
            default: Default value if key doesn't exist

        Returns:
            Value from state or default
        """
        return st.session_state.get(key, default)

    @staticmethod
    def set(key: str, value: Any) -> None:
        """
        Set value in session state.

        Args:
            key: State key
            value: Value to set
        """
        st.session_state[key] = value

    @staticmethod
    def delete(key: str) -> None:
        """
        Delete key from session state.

        Args:
            key: State key to delete
        """
        if key in st.session_state:
            del st.session_state[key]

    @staticmethod
    def has(key: str) -> bool:
        """
        Check if key exists in session state.

        Args:
            key: State key

        Returns:
            True if key exists
        """
        return key in st.session_state

    @staticmethod
    def initialize(key: str, value: Any) -> Any:
        """
        Initialize state key if it doesn't exist.

        Args:
            key: State key
            value: Initial value

        Returns:
            Current value (existing or newly set)
        """
        if key not in st.session_state:
            st.session_state[key] = value
        return st.session_state[key]

    @staticmethod
    def clear_all() -> None:
        """Clear all session state (use with caution!)"""
        st.session_state.clear()

    @staticmethod
    def clear_prefix(prefix: str) -> None:
        """
        Clear all state keys starting with prefix.

        Args:
            prefix: Prefix to match (e.g., "form_")
        """
        keys_to_delete = [key for key in st.session_state.keys() if key.startswith(prefix)]
        for key in keys_to_delete:
            del st.session_state[key]

    @staticmethod
    def get_all(prefix: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all state keys/values, optionally filtered by prefix.

        Args:
            prefix: Optional prefix to filter keys

        Returns:
            Dictionary of state keys and values
        """
        if prefix:
            return {k: v for k, v in st.session_state.items() if k.startswith(prefix)}
        return dict(st.session_state)


class FormState:
    """
    Helper for managing form-specific state.

    Usage:
        form = FormState("tournament_form")
        form.set_field("name", "Test Tournament")
        name = form.get_field("name")
    """

    def __init__(self, form_id: str):
        """
        Initialize form state manager.

        Args:
            form_id: Unique identifier for this form
        """
        self.form_id = form_id
        self.prefix = f"form_{form_id}_"

    def _key(self, field: str) -> str:
        """Generate state key for field"""
        return f"{self.prefix}{field}"

    def get_field(self, field: str, default: Any = None) -> Any:
        """Get form field value"""
        return StateManager.get(self._key(field), default)

    def set_field(self, field: str, value: Any) -> None:
        """Set form field value"""
        StateManager.set(self._key(field), value)

    def has_field(self, field: str) -> bool:
        """Check if form field exists"""
        return StateManager.has(self._key(field))

    def get_all_fields(self) -> Dict[str, Any]:
        """Get all form fields as dictionary"""
        all_state = StateManager.get_all(self.prefix)
        # Remove prefix from keys
        return {k.replace(self.prefix, ""): v for k, v in all_state.items()}

    def clear(self) -> None:
        """Clear all fields for this form"""
        StateManager.clear_prefix(self.prefix)

    def initialize_fields(self, fields: Dict[str, Any]) -> None:
        """
        Initialize multiple form fields at once.

        Args:
            fields: Dictionary of field names and initial values
        """
        for field, value in fields.items():
            if not self.has_field(field):
                self.set_field(field, value)


class NavigationState:
    """
    Helper for managing page navigation state.

    Usage:
        nav = NavigationState()
        nav.goto("tournaments")
        current_page = nav.current_page()
    """

    PAGE_KEY = "current_page"
    PARAMS_KEY = "page_params"

    @staticmethod
    def goto(page: str, params: Optional[Dict[str, Any]] = None) -> None:
        """
        Navigate to a page with optional parameters.

        Args:
            page: Page identifier
            params: Optional parameters to pass to page
        """
        StateManager.set(NavigationState.PAGE_KEY, page)
        if params:
            StateManager.set(NavigationState.PARAMS_KEY, params)
        else:
            StateManager.delete(NavigationState.PARAMS_KEY)

    @staticmethod
    def current_page() -> Optional[str]:
        """Get current page identifier"""
        return StateManager.get(NavigationState.PAGE_KEY)

    @staticmethod
    def get_params() -> Dict[str, Any]:
        """Get current page parameters"""
        return StateManager.get(NavigationState.PARAMS_KEY, {})

    @staticmethod
    def get_param(key: str, default: Any = None) -> Any:
        """Get specific page parameter"""
        params = NavigationState.get_params()
        return params.get(key, default)


# Singleton instances
state = StateManager()
nav = NavigationState()
