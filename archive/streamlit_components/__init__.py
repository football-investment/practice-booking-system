"""
Streamlit Component Library

A comprehensive component library for building consistent Streamlit UIs with:
- Single column form layouts
- Reusable UI components
- Consistent styling
- Built-in feedback mechanisms
- Testable selectors (data-testid attributes)

Usage:
    from streamlit_components import api_client, auth, SingleColumnForm, Success, Error
    from streamlit_components.core import state, nav
    from streamlit_components.layouts import Card, Section
    from streamlit_components.feedback import Loading

    # Use components in your Streamlit app
    form = SingleColumnForm("my_form", title="Create Tournament")
    with form.container():
        name = st.text_input("Name", key=form.field_key("name"))
        if form.submit_button("Create"):
            Success.message("Tournament created!")
"""

# Core utilities
from .core import (
    APIClient,
    APIError,
    api_client,
    AuthManager,
    auth,
    StateManager,
    FormState,
    NavigationState,
    state,
    nav,
)

# Layout components
from .layouts import (
    SingleColumnForm,
    Card,
    InfoCard,
    Section,
    Divider,
    PageHeader,
)

# Feedback components
from .feedback import (
    Loading,
    LoadingState,
    Success,
    SuccessState,
    Error,
    ErrorState,
)

__version__ = "0.1.0"

__all__ = [
    # Core
    "APIClient",
    "APIError",
    "api_client",
    "AuthManager",
    "auth",
    "StateManager",
    "FormState",
    "NavigationState",
    "state",
    "nav",
    # Layouts
    "SingleColumnForm",
    "Card",
    "InfoCard",
    "Section",
    "Divider",
    "PageHeader",
    # Feedback
    "Loading",
    "LoadingState",
    "Success",
    "SuccessState",
    "Error",
    "ErrorState",
]
