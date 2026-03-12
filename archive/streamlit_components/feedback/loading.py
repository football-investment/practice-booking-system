"""
Loading Feedback Component

Provides loading indicators with:
- Spinner with custom messages
- Progress bars
- Skeleton loaders
- Loading overlays
"""

import streamlit as st
from typing import Optional, Any, Callable
import time


class Loading:
    """
    Loading indicator component.

    Usage:
        with Loading.spinner("Processing..."):
            # Long running operation
            process_data()
    """

    @staticmethod
    def spinner(message: str = "Loading..."):
        """
        Show spinner with message.

        Args:
            message: Loading message

        Returns:
            Context manager for spinner
        """
        return st.spinner(message)

    @staticmethod
    def progress_bar(total: int, message: str = "Processing...") -> Callable:
        """
        Create a progress bar that can be updated.

        Args:
            total: Total number of steps
            message: Progress message

        Returns:
            Function to update progress

        Usage:
            update_progress = Loading.progress_bar(100, "Processing items")
            for i in range(100):
                update_progress(i + 1)
                process_item(i)
        """
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update(current: int, custom_message: Optional[str] = None):
            progress = current / total
            progress_bar.progress(min(progress, 1.0))
            msg = custom_message or f"{message} ({current}/{total})"
            status_text.text(msg)

            # Clear when complete
            if current >= total:
                time.sleep(0.5)
                progress_bar.empty()
                status_text.empty()

        return update

    @staticmethod
    def skeleton_text(lines: int = 3, line_height: str = "1rem") -> None:
        """
        Show skeleton text loader.

        Args:
            lines: Number of skeleton lines
            line_height: Height of each line
        """
        for i in range(lines):
            st.markdown(
                f"""
                <div style="
                    height: {line_height};
                    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
                    background-size: 200% 100%;
                    animation: loading 1.5s infinite;
                    border-radius: 4px;
                    margin-bottom: 0.5rem;
                    width: {100 - i * 10}%;
                ">
                </div>
                <style>
                @keyframes loading {{
                    0% {{ background-position: 200% 0; }}
                    100% {{ background-position: -200% 0; }}
                }}
                </style>
                """,
                unsafe_allow_html=True
            )

    @staticmethod
    def skeleton_card(width: str = "100%", height: str = "200px") -> None:
        """
        Show skeleton card loader.

        Args:
            width: Card width
            height: Card height
        """
        st.markdown(
            f"""
            <div style="
                width: {width};
                height: {height};
                background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
                background-size: 200% 100%;
                animation: loading 1.5s infinite;
                border-radius: 8px;
                margin-bottom: 1rem;
            ">
            </div>
            <style>
            @keyframes loading {{
                0% {{ background-position: 200% 0; }}
                100% {{ background-position: -200% 0; }}
            }}
            </style>
            """,
            unsafe_allow_html=True
        )

    @staticmethod
    def overlay(message: str = "Loading...") -> None:
        """
        Show full-screen loading overlay.

        Args:
            message: Loading message
        """
        st.markdown(
            f"""
            <div style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(255, 255, 255, 0.9);
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                z-index: 9999;
            ">
                <div style="
                    width: 50px;
                    height: 50px;
                    border: 5px solid #f3f3f3;
                    border-top: 5px solid #3498db;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                ">
                </div>
                <p style="margin-top: 1rem; color: #666; font-size: 1.1rem;">{message}</p>
            </div>
            <style>
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            </style>
            """,
            unsafe_allow_html=True
        )


class LoadingState:
    """
    Helper for managing loading state.

    Usage:
        loading = LoadingState("data_loading")
        loading.start("Loading data...")
        # ... load data ...
        loading.stop()
    """

    def __init__(self, state_key: str):
        """
        Initialize loading state manager.

        Args:
            state_key: Unique key for this loading state
        """
        self.state_key = f"loading_{state_key}"
        self.message_key = f"loading_message_{state_key}"

    def start(self, message: str = "Loading...") -> None:
        """
        Start loading state.

        Args:
            message: Loading message
        """
        st.session_state[self.state_key] = True
        st.session_state[self.message_key] = message

    def stop(self) -> None:
        """Stop loading state"""
        st.session_state[self.state_key] = False
        if self.message_key in st.session_state:
            del st.session_state[self.message_key]

    def is_loading(self) -> bool:
        """Check if currently loading"""
        return st.session_state.get(self.state_key, False)

    def get_message(self) -> str:
        """Get current loading message"""
        return st.session_state.get(self.message_key, "Loading...")

    def render(self) -> None:
        """Render loading indicator if loading"""
        if self.is_loading():
            with st.spinner(self.get_message()):
                # Keep spinner visible
                pass
