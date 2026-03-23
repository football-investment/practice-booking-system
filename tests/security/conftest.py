"""
Security test configuration.

Routes requests.post/get/etc calls targeting localhost:8000
through FastAPI TestClient so tests run without a live server.
"""

import pytest
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse
from fastapi.testclient import TestClient

from app.main import app


class TestClientAdapter:
    """
    Drop-in adapter that intercepts requests.* calls to localhost:8000
    and routes them through FastAPI TestClient.

    The security tests use:
        requests.post("http://localhost:8000/api/v1/auth/login", json={...})

    This adapter makes them work without a running server by translating to:
        test_client.post("/api/v1/auth/login", json={...})

    Each call creates a fresh TestClient to match the stateless behaviour of
    individual requests.get() / requests.post() calls (no implicit cookie jar).
    Tests that need cookies across a request pair pass them explicitly via the
    `cookies=` kwarg, which the TestClient honours correctly.
    """

    def _fresh_client(self) -> TestClient:
        return TestClient(app, raise_server_exceptions=False, follow_redirects=True)

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
        """Make TestClient response look like requests.Response."""
        adapted = MagicMock()
        adapted.status_code = resp.status_code
        adapted.text = resp.text
        adapted.json = resp.json
        # Use httpx.Headers directly: case-insensitive + supports get_list()
        adapted.headers = resp.headers
        adapted.content = resp.content
        adapted.url = str(resp.url)
        adapted.ok = resp.is_success if hasattr(resp, 'is_success') else (200 <= resp.status_code < 400)
        # Copy cookies so tests can check response.cookies["csrf_token"]
        adapted.cookies = dict(resp.cookies)
        return adapted

    def post(self, url, **kwargs):
        if self._is_local(url):
            return self._adapt_response(self._fresh_client().post(self._path(url), **kwargs))
        import requests as _real
        return _real.Session().post(url, **kwargs)

    def get(self, url, **kwargs):
        if self._is_local(url):
            return self._adapt_response(self._fresh_client().get(self._path(url), **kwargs))
        import requests as _real
        return _real.Session().get(url, **kwargs)

    def put(self, url, **kwargs):
        if self._is_local(url):
            return self._adapt_response(self._fresh_client().put(self._path(url), **kwargs))
        import requests as _real
        return _real.Session().put(url, **kwargs)

    def patch(self, url, **kwargs):
        if self._is_local(url):
            return self._adapt_response(self._fresh_client().patch(self._path(url), **kwargs))
        import requests as _real
        return _real.Session().patch(url, **kwargs)

    def delete(self, url, **kwargs):
        if self._is_local(url):
            return self._adapt_response(self._fresh_client().delete(self._path(url), **kwargs))
        import requests as _real
        return _real.Session().delete(url, **kwargs)

    def options(self, url, **kwargs):
        if self._is_local(url):
            return self._adapt_response(self._fresh_client().options(self._path(url), **kwargs))
        import requests as _real
        return _real.Session().options(url, **kwargs)

    def request(self, method, url, **kwargs):
        if self._is_local(url):
            fn = getattr(self._fresh_client(), method.lower())
            return self._adapt_response(fn(self._path(url), **kwargs))
        import requests as _real
        return _real.Session().request(method, url, **kwargs)


@pytest.fixture(autouse=True)
def _route_requests_through_testclient(monkeypatch):
    """
    Auto-applied fixture: intercepts all requests.* calls in security tests
    and routes localhost:8000 traffic through FastAPI TestClient.
    """
    adapter = TestClientAdapter()
    monkeypatch.setattr("requests.post", adapter.post)
    monkeypatch.setattr("requests.get", adapter.get)
    monkeypatch.setattr("requests.put", adapter.put)
    monkeypatch.setattr("requests.patch", adapter.patch)
    monkeypatch.setattr("requests.delete", adapter.delete)
    monkeypatch.setattr("requests.options", adapter.options)
    monkeypatch.setattr("requests.request", adapter.request)
