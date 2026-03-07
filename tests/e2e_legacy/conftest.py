"""
E2E Test Configuration

This file makes fixtures from fixtures.py available to all E2E tests,
routes requests.* calls through FastAPI TestClient (no live server needed),
and configures Playwright for headed mode with slowmo.
"""

import pytest
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse
from fastapi.testclient import TestClient

from app.main import app

# Import all fixtures to make them available
from .fixtures import (
    admin_token,
    test_instructor,
    test_players,
    create_tournament,
    tournament_in_draft,
    tournament_with_instructor,
    complete_tournament_setup
)


# ================================================================
# TESTCLIENT ADAPTER — routes requests.* to FastAPI TestClient
# Session-scoped so session-scoped fixtures (admin_token) also work.
# ================================================================

class _E2ETestClientAdapter:
    """Intercepts requests.* calls to localhost:8000 and routes through TestClient."""

    def __init__(self):
        self.client = TestClient(app, raise_server_exceptions=False, follow_redirects=True)

    def _is_local(self, url: str) -> bool:
        parsed = urlparse(url)
        return parsed.hostname == "localhost" and parsed.port == 8000

    def _path(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path
        if parsed.query:
            path += "?" + parsed.query
        return path

    def _adapt_response(self, resp):
        adapted = MagicMock()
        adapted.status_code = resp.status_code
        adapted.text = resp.text
        adapted.json = resp.json
        adapted.headers = dict(resp.headers)
        adapted.content = resp.content
        adapted.url = str(resp.url)
        adapted.ok = resp.is_success if hasattr(resp, 'is_success') else (200 <= resp.status_code < 400)
        adapted.raise_for_status = resp.raise_for_status
        return adapted

    def _dispatch(self, method, url, **kwargs):
        if self._is_local(url):
            fn = getattr(self.client, method)
            return self._adapt_response(fn(self._path(url), **kwargs))
        import requests as _real
        return getattr(_real.Session(), method)(url, **kwargs)

    def post(self, url, **kwargs):
        return self._dispatch("post", url, **kwargs)

    def get(self, url, **kwargs):
        return self._dispatch("get", url, **kwargs)

    def put(self, url, **kwargs):
        return self._dispatch("put", url, **kwargs)

    def patch(self, url, **kwargs):
        return self._dispatch("patch", url, **kwargs)

    def delete(self, url, **kwargs):
        return self._dispatch("delete", url, **kwargs)


@pytest.fixture(scope="session", autouse=True)
def _route_e2e_requests_through_testclient():
    """
    Session-scoped: patches requests.* for the entire E2E test session.
    Uses unittest.mock.patch (not monkeypatch) because monkeypatch is function-scoped.
    """
    adapter = _E2ETestClientAdapter()
    with patch("requests.post", adapter.post), \
         patch("requests.get", adapter.get), \
         patch("requests.put", adapter.put), \
         patch("requests.patch", adapter.patch), \
         patch("requests.delete", adapter.delete):
        yield


# ================================================================
# PLAYWRIGHT CONFIGURATION FOR HEADED MODE
# ================================================================

@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args, pytestconfig):
    """
    Configure Playwright browser launch arguments for headed mode.

    This fixture overrides the default pytest-playwright settings to:
    - Run in headless mode for CI/CD compatibility
    - Set viewport size
    - Use Firefox browser
    """
    return {
        **browser_type_launch_args,
        "headless": True,  # Run headless for CI/CD
        "slow_mo": 0,      # No delay for faster execution
    }


@pytest.fixture(scope="session")
def browser_name(pytestconfig):
    """
    Force Firefox browser for all Playwright tests.
    """
    return "firefox"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """
    Configure browser context arguments.

    Sets viewport size and other context-level settings.
    """
    return {
        **browser_context_args,
        "viewport": {
            "width": 1920,
            "height": 1080,
        },
        "ignore_https_errors": True,
    }


# Make pytest aware of the fixtures
__all__ = [
    "admin_token",
    "test_instructor",
    "test_players",
    "create_tournament",
    "tournament_in_draft",
    "tournament_with_instructor",
    "complete_tournament_setup",
    "browser_type_launch_args",
    "browser_context_args",
    "browser_name",
]
