"""
Card Layout Component

Provides a consistent card-based layout with:
- Optional header with title and actions
- Body content area
- Optional footer
- Customizable styling
- Shadow and border effects
"""

import streamlit as st
from typing import Optional, Callable


class Card:
    """
    Card container component for grouping related content.

    Usage:
        card = Card(title="Tournament Details")
        with card.container():
            st.write("Tournament Name: Test Tournament")
            st.write("Format: League")
            if card.action_button("Edit"):
                st.write("Edit clicked!")
    """

    def __init__(
        self,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        card_id: Optional[str] = None,
        elevation: int = 1,
        padding: str = "1.5rem"
    ):
        """
        Initialize card component.

        Args:
            title: Optional card title
            subtitle: Optional card subtitle
            card_id: Optional unique ID for styling/testing
            elevation: Shadow depth (0-3, higher = more shadow)
            padding: CSS padding value
        """
        self.title = title
        self.subtitle = subtitle
        self.card_id = card_id or "card"
        self.elevation = min(max(elevation, 0), 3)
        self.padding = padding

        # Shadow styles by elevation
        self._shadows = {
            0: "none",
            1: "0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24)",
            2: "0 3px 6px rgba(0,0,0,0.15), 0 2px 4px rgba(0,0,0,0.12)",
            3: "0 10px 20px rgba(0,0,0,0.15), 0 3px 6px rgba(0,0,0,0.10)"
        }

    def container(self):
        """
        Create card container.

        Returns:
            Context manager for card container
        """
        # Apply card styling
        st.markdown(
            f"""
            <style>
            .card-{self.card_id} {{
                background: white;
                border-radius: 8px;
                padding: {self.padding};
                box-shadow: {self._shadows[self.elevation]};
                margin-bottom: 1.5rem;
                border: 1px solid #e0e0e0;
            }}
            .card-header-{self.card_id} {{
                margin-bottom: 1rem;
                padding-bottom: 0.75rem;
                border-bottom: 1px solid #f0f2f6;
            }}
            .card-title-{self.card_id} {{
                font-size: 1.25rem;
                font-weight: 600;
                color: #31333F;
                margin: 0;
            }}
            .card-subtitle-{self.card_id} {{
                font-size: 0.9rem;
                color: #6c757d;
                margin-top: 0.25rem;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )

        # Create card container
        container = st.container()

        with container:
            # Wrap in div for styling
            st.markdown(f'<div class="card-{self.card_id}" data-testid="card-{self.card_id}">', unsafe_allow_html=True)

            # Show header if title provided
            if self.title:
                st.markdown(
                    f"""
                    <div class="card-header-{self.card_id}">
                        <h3 class="card-title-{self.card_id}" data-testid="card-title">{self.title}</h3>
                        {f'<p class="card-subtitle-{self.card_id}">{self.subtitle}</p>' if self.subtitle else ''}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        return container

    def close_container(self) -> None:
        """Close card container div"""
        st.markdown('</div>', unsafe_allow_html=True)

    def action_button(
        self,
        label: str,
        icon: Optional[str] = None,
        button_type: str = "secondary",
        on_click: Optional[Callable] = None,
        disabled: bool = False
    ) -> bool:
        """
        Create an action button within the card.

        Args:
            label: Button label
            icon: Optional emoji icon
            button_type: "primary" or "secondary"
            on_click: Optional callback
            disabled: Whether button is disabled

        Returns:
            True if button was clicked
        """
        display_label = f"{icon} {label}" if icon else label

        return st.button(
            display_label,
            type=button_type,
            on_click=on_click,
            disabled=disabled,
            key=f"btn_{self.card_id}_{label.lower().replace(' ', '_')}"
        )


class InfoCard(Card):
    """
    Specialized card for displaying information with status colors.

    Usage:
        info = InfoCard(title="Status", status="success")
        with info.container():
            st.write("All systems operational")
    """

    def __init__(
        self,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        status: str = "info",
        card_id: Optional[str] = None
    ):
        """
        Initialize info card.

        Args:
            title: Card title
            subtitle: Card subtitle
            status: Status type (info, success, warning, error)
            card_id: Optional unique ID
        """
        super().__init__(title, subtitle, card_id or f"info_{status}", elevation=1)
        self.status = status

        # Status colors
        self._colors = {
            "info": "#17a2b8",
            "success": "#28a745",
            "warning": "#ffc107",
            "error": "#dc3545"
        }

    def container(self):
        """Create info card container with status color"""
        # Apply status-specific styling
        color = self._colors.get(self.status, self._colors["info"])

        st.markdown(
            f"""
            <style>
            .card-{self.card_id} {{
                background: white;
                border-radius: 8px;
                padding: {self.padding};
                box-shadow: {self._shadows[self.elevation]};
                margin-bottom: 1.5rem;
                border-left: 4px solid {color};
            }}
            </style>
            """,
            unsafe_allow_html=True
        )

        return super().container()
