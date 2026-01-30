"""
Single Column Form Layout Component

Provides a consistent, user-friendly form layout pattern with:
- Single column design (easier to scan and complete)
- Clear section organization
- Built-in submit/cancel buttons
- Responsive design
- Test selectors (data-testid attributes)
"""

import streamlit as st
from typing import Optional, Callable, Dict, Any
from ..core.state import FormState


class SingleColumnForm:
    """
    Single column form layout component.

    Usage:
        form = SingleColumnForm("tournament_form", title="Create Tournament")
        with form.container():
            form.section("Basic Information")
            name = st.text_input("Tournament Name", key=form.field_key("name"))
            format_type = st.selectbox("Format", ["LEAGUE", "KNOCKOUT"], key=form.field_key("format"))

            form.section("Schedule")
            start_date = st.date_input("Start Date", key=form.field_key("start_date"))

            if form.submit_button("Create Tournament"):
                # Process form
                data = form.get_data()
                st.success(f"Created: {data['name']}")
    """

    def __init__(
        self,
        form_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        max_width: int = 800
    ):
        """
        Initialize single column form.

        Args:
            form_id: Unique form identifier
            title: Optional form title
            description: Optional form description
            max_width: Maximum width in pixels (default: 800)
        """
        self.form_id = form_id
        self.title = title
        self.description = description
        self.max_width = max_width
        self.state = FormState(form_id)

        # Track current section for styling
        self._current_section = None

    def field_key(self, field_name: str) -> str:
        """
        Generate Streamlit widget key for form field.

        Args:
            field_name: Field name

        Returns:
            Unique key for widget
        """
        return f"form_{self.form_id}_{field_name}"

    def container(self):
        """
        Create form container with single column layout.

        Returns:
            Context manager for form container
        """
        # Create centered container with max width
        container = st.container()

        with container:
            # Add CSS for single column layout
            st.markdown(
                f"""
                <style>
                .single-column-form-{self.form_id} {{
                    max-width: {self.max_width}px;
                    margin: 0 auto;
                }}
                .form-section-{self.form_id} {{
                    margin-top: 2rem;
                    margin-bottom: 1rem;
                    padding-bottom: 0.5rem;
                    border-bottom: 2px solid #f0f2f6;
                }}
                .form-section-{self.form_id} h3 {{
                    color: #31333F;
                    font-size: 1.2rem;
                    font-weight: 600;
                    margin-bottom: 0.5rem;
                }}
                </style>
                """,
                unsafe_allow_html=True
            )

            # Show title if provided
            if self.title:
                st.markdown(
                    f'<h2 data-testid="form-title-{self.form_id}">{self.title}</h2>',
                    unsafe_allow_html=True
                )

            # Show description if provided
            if self.description:
                st.markdown(
                    f'<p data-testid="form-description-{self.form_id}" style="color: #6c757d; margin-bottom: 2rem;">{self.description}</p>',
                    unsafe_allow_html=True
                )

        return container

    def section(self, title: str) -> None:
        """
        Create a form section with title.

        Args:
            title: Section title
        """
        self._current_section = title

        st.markdown(
            f"""
            <div class="form-section-{self.form_id}" data-testid="form-section-{title.lower().replace(' ', '-')}">
                <h3>{title}</h3>
            </div>
            """,
            unsafe_allow_html=True
        )

    def submit_button(
        self,
        label: str = "Submit",
        disabled: bool = False,
        on_click: Optional[Callable] = None
    ) -> bool:
        """
        Create submit button with consistent styling.

        Args:
            label: Button label
            disabled: Whether button is disabled
            on_click: Optional callback function

        Returns:
            True if button was clicked
        """
        return st.button(
            label,
            type="primary",
            disabled=disabled,
            on_click=on_click,
            key=f"submit_{self.form_id}",
            use_container_width=True
        )

    def cancel_button(
        self,
        label: str = "Cancel",
        on_click: Optional[Callable] = None
    ) -> bool:
        """
        Create cancel button with consistent styling.

        Args:
            label: Button label
            on_click: Optional callback function

        Returns:
            True if button was clicked
        """
        return st.button(
            label,
            type="secondary",
            on_click=on_click,
            key=f"cancel_{self.form_id}",
            use_container_width=True
        )

    def action_buttons(
        self,
        submit_label: str = "Submit",
        cancel_label: str = "Cancel",
        submit_disabled: bool = False,
        on_submit: Optional[Callable] = None,
        on_cancel: Optional[Callable] = None
    ) -> Dict[str, bool]:
        """
        Create submit and cancel buttons side by side.

        Args:
            submit_label: Submit button label
            cancel_label: Cancel button label
            submit_disabled: Whether submit is disabled
            on_submit: Optional submit callback
            on_cancel: Optional cancel callback

        Returns:
            Dictionary with 'submit' and 'cancel' click states
        """
        col1, col2 = st.columns(2)

        with col1:
            cancel_clicked = self.cancel_button(cancel_label, on_cancel)

        with col2:
            submit_clicked = self.submit_button(submit_label, submit_disabled, on_submit)

        return {
            "submit": submit_clicked,
            "cancel": cancel_clicked
        }

    def get_data(self) -> Dict[str, Any]:
        """
        Get all form field data as dictionary.

        Returns:
            Dictionary of field names to values
        """
        return self.state.get_all_fields()

    def clear(self) -> None:
        """Clear all form data"""
        self.state.clear()

    def set_defaults(self, defaults: Dict[str, Any]) -> None:
        """
        Set default values for form fields.

        Args:
            defaults: Dictionary of field names to default values
        """
        self.state.initialize_fields(defaults)
