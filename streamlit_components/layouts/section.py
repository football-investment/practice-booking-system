"""
Section Divider Component

Provides visual separation and organization with:
- Section headers
- Optional descriptions
- Collapsible sections
- Visual dividers
"""

import streamlit as st
from typing import Optional


class Section:
    """
    Section divider component for organizing content.

    Usage:
        section = Section("Player Selection")
        section.render()
        st.selectbox("Select Player", players)
    """

    def __init__(
        self,
        title: str,
        description: Optional[str] = None,
        collapsible: bool = False,
        expanded: bool = True,
        section_id: Optional[str] = None
    ):
        """
        Initialize section component.

        Args:
            title: Section title
            description: Optional section description
            collapsible: Whether section can be collapsed
            expanded: Whether section starts expanded (if collapsible)
            section_id: Optional unique ID for testing
        """
        self.title = title
        self.description = description
        self.collapsible = collapsible
        self.expanded = expanded
        self.section_id = section_id or title.lower().replace(" ", "-")

    def render(self) -> None:
        """Render section header"""
        if self.collapsible:
            # Use expander for collapsible sections
            with st.expander(self.title, expanded=self.expanded):
                if self.description:
                    st.markdown(
                        f'<p style="color: #6c757d; margin-bottom: 1rem;">{self.description}</p>',
                        unsafe_allow_html=True
                    )
        else:
            # Non-collapsible section with styling
            st.markdown(
                f"""
                <div data-testid="section-{self.section_id}" style="margin-top: 2rem; margin-bottom: 1.5rem;">
                    <h3 style="color: #31333F; font-size: 1.3rem; font-weight: 600; margin-bottom: 0.5rem; border-bottom: 2px solid #f0f2f6; padding-bottom: 0.5rem;">
                        {self.title}
                    </h3>
                    {f'<p style="color: #6c757d; margin-top: 0.5rem;">{self.description}</p>' if self.description else ''}
                </div>
                """,
                unsafe_allow_html=True
            )

    def container(self):
        """
        Get container for section content.

        Returns:
            Context manager for section content
        """
        if self.collapsible:
            return st.expander(self.title, expanded=self.expanded)
        else:
            self.render()
            return st.container()


class Divider:
    """
    Visual divider component.

    Usage:
        Divider().render()
        # or
        Divider.horizontal()
    """

    @staticmethod
    def horizontal(margin: str = "2rem 0") -> None:
        """
        Render horizontal divider line.

        Args:
            margin: CSS margin value
        """
        st.markdown(
            f"""
            <hr style="border: none; border-top: 1px solid #e0e0e0; margin: {margin};">
            """,
            unsafe_allow_html=True
        )

    @staticmethod
    def spacer(height: str = "2rem") -> None:
        """
        Add vertical space.

        Args:
            height: CSS height value
        """
        st.markdown(
            f'<div style="height: {height};"></div>',
            unsafe_allow_html=True
        )

    def render(self, style: str = "horizontal", margin: str = "2rem 0") -> None:
        """
        Render divider.

        Args:
            style: "horizontal" or "spacer"
            margin: CSS margin value
        """
        if style == "horizontal":
            self.horizontal(margin)
        elif style == "spacer":
            self.spacer(margin)


class PageHeader:
    """
    Page header component with title and breadcrumbs.

    Usage:
        header = PageHeader(
            title="Tournament Management",
            breadcrumbs=["Home", "Tournaments", "Create"]
        )
        header.render()
    """

    def __init__(
        self,
        title: str,
        subtitle: Optional[str] = None,
        breadcrumbs: Optional[list] = None
    ):
        """
        Initialize page header.

        Args:
            title: Page title
            subtitle: Optional subtitle
            breadcrumbs: Optional list of breadcrumb items
        """
        self.title = title
        self.subtitle = subtitle
        self.breadcrumbs = breadcrumbs or []

    def render(self) -> None:
        """Render page header"""
        # Render breadcrumbs if provided
        if self.breadcrumbs:
            breadcrumb_html = " › ".join([
                f'<span style="color: #6c757d;">{item}</span>'
                for item in self.breadcrumbs
            ])
            st.markdown(
                f'<div style="font-size: 0.9rem; margin-bottom: 0.5rem;">{breadcrumb_html}</div>',
                unsafe_allow_html=True
            )

        # Render title
        st.markdown(
            f"""
            <h1 style="color: #31333F; font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem;" data-testid="page-title">
                {self.title}
            </h1>
            """,
            unsafe_allow_html=True
        )

        # Render subtitle if provided
        if self.subtitle:
            st.markdown(
                f'<p style="color: #6c757d; font-size: 1.1rem; margin-bottom: 2rem;">{self.subtitle}</p>',
                unsafe_allow_html=True
            )

        # Add divider
        Divider.horizontal(margin="1rem 0 2rem 0")
