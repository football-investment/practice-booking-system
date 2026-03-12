"""
Global Error Boundary for Streamlit Pages
Prevents app crashes and provides user-friendly error messages
"""

import streamlit as st
import logging
from functools import wraps
from typing import Callable, Any
from config import ENVIRONMENT

# Configure logging
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def page_error_boundary(func: Callable) -> Callable:
    """
    Decorator to wrap page functions with error boundary
    Catches all exceptions and displays user-friendly error message

    Usage:
        @page_error_boundary
        def main():
            # Page logic here
            pass

        if __name__ == "__main__":
            main()

    Args:
        func: Page function to wrap

    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log error with full traceback
            logger.error(
                f"Page error in {func.__name__}: {str(e)}",
                exc_info=True,
                extra={
                    'function': func.__name__,
                    'args': args,
                    'kwargs': kwargs
                }
            )

            # Display user-friendly error message
            st.error(
                "⚠️ **An unexpected error occurred**\n\n"
                "Please try one of the following:\n"
                "- Refresh the page\n"
                "- Log out and log back in\n"
                "- Contact support if the issue persists"
            )

            # Show error details in development mode only
            if ENVIRONMENT == "development":
                with st.expander("🔍 Error Details (Development Only)"):
                    st.exception(e)

            # Don't re-raise - keep app running
            st.stop()

    return wrapper


def api_error_handler(error_message: str, show_details: bool = False) -> None:
    """
    Display user-friendly API error message

    Usage:
        success, error, data = some_api_call()
        if not success:
            api_error_handler(error)
            return

    Args:
        error_message: Error message from API
        show_details: Whether to show detailed error (default: False in production)
    """
    st.error(
        "⚠️ **Unable to complete request**\n\n"
        "The server encountered an error. Please try again in a moment."
    )

    # Show details in development or if explicitly requested
    if (ENVIRONMENT == "development" or show_details) and error_message:
        with st.expander("🔍 Error Details"):
            st.code(error_message, language="text")


def handle_session_error() -> None:
    """
    Handle session-related errors (expired token, invalid session)
    Clears session and redirects to login
    """
    from session_manager import clear_session

    st.warning(
        "⚠️ **Session Error**\n\n"
        "Your session is invalid or has expired. Please log in again."
    )

    # Clear session
    clear_session()

    # Show login button
    if st.button("Go to Login", type="primary"):
        st.switch_page("🏠_Home.py")

    st.stop()


def handle_network_error() -> None:
    """
    Handle network connectivity errors
    """
    st.error(
        "⚠️ **Network Error**\n\n"
        "Unable to connect to the server. Please check your internet connection and try again."
    )

    if st.button("Retry", type="primary"):
        st.rerun()

    st.stop()
