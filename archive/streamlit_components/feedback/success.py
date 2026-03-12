"""
Success Feedback Component

Provides success notifications with:
- Success messages
- Checkmark animations
- Toast notifications
- Confirmation banners
"""

import streamlit as st
from typing import Optional


class Success:
    """
    Success feedback component.

    Usage:
        Success.message("Tournament created successfully!")
        Success.toast("Saved!")
        Success.banner("Operation completed", "Your changes have been saved.")
    """

    @staticmethod
    def message(
        text: str,
        icon: str = "✅",
        data_testid: Optional[str] = None
    ) -> None:
        """
        Show success message.

        Args:
            text: Success message
            icon: Icon emoji
            data_testid: Optional test selector
        """
        st.success(f"{icon} {text}")

    @staticmethod
    def toast(text: str, duration: int = 3) -> None:
        """
        Show success toast notification.

        Args:
            text: Toast message
            duration: Duration in seconds
        """
        st.toast(f"✅ {text}", icon="✅")

    @staticmethod
    def banner(
        title: str,
        message: Optional[str] = None,
        dismissible: bool = True
    ) -> None:
        """
        Show success banner.

        Args:
            title: Banner title
            message: Optional detailed message
            dismissible: Whether banner can be dismissed
        """
        banner_id = title.lower().replace(" ", "_")

        # Check if dismissed
        if dismissible and st.session_state.get(f"dismissed_{banner_id}", False):
            return

        st.markdown(
            f"""
            <div data-testid="success-banner" style="
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                border-left: 4px solid #28a745;
                border-radius: 4px;
                padding: 1rem 1.5rem;
                margin-bottom: 1.5rem;
                position: relative;
            ">
                <div style="display: flex; align-items: center;">
                    <span style="font-size: 1.5rem; margin-right: 0.75rem;">✅</span>
                    <div style="flex: 1;">
                        <strong style="color: #155724; font-size: 1.1rem;">{title}</strong>
                        {f'<p style="color: #155724; margin: 0.5rem 0 0 0;">{message}</p>' if message else ''}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if dismissible:
            if st.button("Dismiss", key=f"dismiss_{banner_id}"):
                st.session_state[f"dismissed_{banner_id}"] = True
                st.rerun()

    @staticmethod
    def checkmark(size: str = "3rem", animated: bool = True) -> None:
        """
        Show checkmark icon.

        Args:
            size: Size of checkmark
            animated: Whether to animate
        """
        animation = """
        @keyframes checkmark {{
            0% {{ transform: scale(0) rotate(45deg); }}
            50% {{ transform: scale(1.2) rotate(45deg); }}
            100% {{ transform: scale(1) rotate(45deg); }}
        }}
        """ if animated else ""

        st.markdown(
            f"""
            <div style="text-align: center; margin: 2rem 0;">
                <div style="
                    display: inline-block;
                    width: {size};
                    height: {size};
                    border-radius: 50%;
                    background-color: #28a745;
                    position: relative;
                    animation: {('checkmark 0.5s ease-in-out' if animated else 'none')};
                ">
                    <span style="
                        color: white;
                        font-size: calc({size} * 0.6);
                        position: absolute;
                        top: 50%;
                        left: 50%;
                        transform: translate(-50%, -50%);
                    ">✓</span>
                </div>
            </div>
            <style>{animation}</style>
            """,
            unsafe_allow_html=True
        )

    @staticmethod
    def card(
        title: str,
        message: str,
        action_label: Optional[str] = None,
        on_action: Optional[callable] = None
    ) -> None:
        """
        Show success card with optional action.

        Args:
            title: Card title
            message: Success message
            action_label: Optional action button label
            on_action: Optional action callback
        """
        st.markdown(
            f"""
            <div style="
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                border-radius: 8px;
                padding: 2rem;
                text-align: center;
                margin: 2rem 0;
            ">
                <div style="font-size: 3rem; margin-bottom: 1rem;">✅</div>
                <h3 style="color: #155724; margin-bottom: 0.5rem;">{title}</h3>
                <p style="color: #155724; margin: 0;">{message}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        if action_label and on_action:
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button(action_label, type="primary", use_container_width=True):
                    on_action()


class SuccessState:
    """
    Helper for managing success state.

    Usage:
        success = SuccessState("form_submit")
        success.set("Form submitted successfully!")
        if success.has():
            Success.message(success.get())
            success.clear()
    """

    def __init__(self, state_key: str):
        """
        Initialize success state manager.

        Args:
            state_key: Unique key for this success state
        """
        self.state_key = f"success_{state_key}"

    def set(self, message: str) -> None:
        """
        Set success message.

        Args:
            message: Success message
        """
        st.session_state[self.state_key] = message

    def get(self) -> Optional[str]:
        """Get success message"""
        return st.session_state.get(self.state_key)

    def has(self) -> bool:
        """Check if success message exists"""
        return self.state_key in st.session_state and st.session_state[self.state_key] is not None

    def clear(self) -> None:
        """Clear success message"""
        if self.state_key in st.session_state:
            del st.session_state[self.state_key]

    def show_and_clear(self, icon: str = "✅") -> None:
        """Show success message and clear"""
        if self.has():
            Success.message(self.get(), icon=icon)
            self.clear()
