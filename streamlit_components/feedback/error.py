"""
Error Feedback Component

Provides error notifications with:
- Error messages
- Alert banners
- Validation errors
- Error details with expandable info
"""

import streamlit as st
from typing import Optional, Dict, Any
from ..core.api_client import APIError


class Error:
    """
    Error feedback component.

    Usage:
        Error.message("Failed to save tournament")
        Error.validation_errors({"name": "Required field"})
        Error.api_error(api_exception)
    """

    @staticmethod
    def message(
        text: str,
        icon: str = "❌",
        data_testid: Optional[str] = None
    ) -> None:
        """
        Show error message.

        Args:
            text: Error message
            icon: Icon emoji
            data_testid: Optional test selector
        """
        st.error(f"{icon} {text}")

    @staticmethod
    def banner(
        title: str,
        message: Optional[str] = None,
        dismissible: bool = True
    ) -> None:
        """
        Show error banner.

        Args:
            title: Banner title
            message: Optional detailed message
            dismissible: Whether banner can be dismissed
        """
        banner_id = title.lower().replace(" ", "_")

        # Check if dismissed
        if dismissible and st.session_state.get(f"dismissed_error_{banner_id}", False):
            return

        st.markdown(
            f"""
            <div data-testid="error-banner" style="
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                border-left: 4px solid #dc3545;
                border-radius: 4px;
                padding: 1rem 1.5rem;
                margin-bottom: 1.5rem;
                position: relative;
            ">
                <div style="display: flex; align-items: center;">
                    <span style="font-size: 1.5rem; margin-right: 0.75rem;">❌</span>
                    <div style="flex: 1;">
                        <strong style="color: #721c24; font-size: 1.1rem;">{title}</strong>
                        {f'<p style="color: #721c24; margin: 0.5rem 0 0 0;">{message}</p>' if message else ''}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if dismissible:
            if st.button("Dismiss", key=f"dismiss_error_{banner_id}"):
                st.session_state[f"dismissed_error_{banner_id}"] = True
                st.rerun()

    @staticmethod
    def validation_errors(errors: Dict[str, str]) -> None:
        """
        Show validation errors.

        Args:
            errors: Dictionary of field names to error messages
        """
        st.markdown(
            """
            <div style="
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                border-radius: 4px;
                padding: 1rem;
                margin-bottom: 1rem;
            ">
                <strong style="color: #721c24;">⚠️ Please fix the following errors:</strong>
            </div>
            """,
            unsafe_allow_html=True
        )

        for field, error in errors.items():
            st.markdown(
                f"""
                <div style="
                    padding: 0.5rem 1rem;
                    margin-bottom: 0.5rem;
                    background-color: #fff3cd;
                    border-left: 3px solid #ffc107;
                    border-radius: 4px;
                ">
                    <strong style="color: #856404;">{field}:</strong>
                    <span style="color: #856404;"> {error}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

    @staticmethod
    def api_error(error: APIError, show_details: bool = False) -> None:
        """
        Show API error with optional details.

        Args:
            error: APIError exception
            show_details: Whether to show expandable details
        """
        # Show main error message
        Error.message(f"Error {error.status_code}: {error.message}")

        # Show details in expander if requested
        if show_details and error.detail:
            with st.expander("Error Details"):
                st.json(error.detail)

    @staticmethod
    def with_retry(
        message: str,
        on_retry: callable,
        retry_label: str = "Try Again"
    ) -> None:
        """
        Show error with retry button.

        Args:
            message: Error message
            on_retry: Callback for retry button
            retry_label: Retry button label
        """
        col1, col2 = st.columns([3, 1])

        with col1:
            Error.message(message)

        with col2:
            if st.button(retry_label, type="secondary"):
                on_retry()

    @staticmethod
    def card(
        title: str,
        message: str,
        details: Optional[str] = None,
        action_label: Optional[str] = None,
        on_action: Optional[callable] = None
    ) -> None:
        """
        Show error card with optional details and action.

        Args:
            title: Card title
            message: Error message
            details: Optional detailed error info
            action_label: Optional action button label
            on_action: Optional action callback
        """
        st.markdown(
            f"""
            <div style="
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                border-radius: 8px;
                padding: 2rem;
                text-align: center;
                margin: 2rem 0;
            ">
                <div style="font-size: 3rem; margin-bottom: 1rem;">❌</div>
                <h3 style="color: #721c24; margin-bottom: 0.5rem;">{title}</h3>
                <p style="color: #721c24; margin: 0;">{message}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        if details:
            with st.expander("Show Details"):
                st.text(details)

        if action_label and on_action:
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button(action_label, type="primary", use_container_width=True):
                    on_action()


class ErrorState:
    """
    Helper for managing error state.

    Usage:
        error = ErrorState("form_submit")
        try:
            submit_form()
        except Exception as e:
            error.set(str(e))

        if error.has():
            Error.message(error.get())
            error.clear()
    """

    def __init__(self, state_key: str):
        """
        Initialize error state manager.

        Args:
            state_key: Unique key for this error state
        """
        self.state_key = f"error_{state_key}"
        self.details_key = f"error_details_{state_key}"

    def set(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Set error message.

        Args:
            message: Error message
            details: Optional error details
        """
        st.session_state[self.state_key] = message
        if details:
            st.session_state[self.details_key] = details

    def set_from_api_error(self, error: APIError) -> None:
        """
        Set error from APIError exception.

        Args:
            error: APIError exception
        """
        self.set(error.message, error.detail)

    def get(self) -> Optional[str]:
        """Get error message"""
        return st.session_state.get(self.state_key)

    def get_details(self) -> Optional[Dict[str, Any]]:
        """Get error details"""
        return st.session_state.get(self.details_key)

    def has(self) -> bool:
        """Check if error message exists"""
        return self.state_key in st.session_state and st.session_state[self.state_key] is not None

    def clear(self) -> None:
        """Clear error message and details"""
        if self.state_key in st.session_state:
            del st.session_state[self.state_key]
        if self.details_key in st.session_state:
            del st.session_state[self.details_key]

    def show_and_clear(self, show_details: bool = False) -> None:
        """Show error message and clear"""
        if self.has():
            Error.message(self.get())

            if show_details:
                details = self.get_details()
                if details:
                    with st.expander("Error Details"):
                        st.json(details)

            self.clear()
