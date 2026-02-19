"""
Lifecycle test suite conftest.

Overrides the root conftest base_url fixture (which returns the Streamlit URL)
with the FastAPI API URL. This prevents pytest-base-url from treating all
lifecycle tests as "destructive against a sensitive environment" (localhost:8501).

The production-flow tests (T09) write real data — they ARE destructive by design.
The base_url here tells the pytest-base-url sensitive-URL guard to evaluate
against localhost:8000 (the API), not localhost:8501 (Streamlit).
"""
import os
import pytest


@pytest.fixture(scope="session")
def base_url() -> str:  # type: ignore[override]
    """FastAPI backend URL — used by pytest-base-url for sensitive-URL evaluation."""
    return os.environ.get("API_URL", "http://localhost:8000")
