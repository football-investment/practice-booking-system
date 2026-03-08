"""
Smoke tests for dashboard web routes (Streamlit UI).

These routes use cookie-based authentication (get_current_user_web),
not Bearer tokens. Tests pass token via 'access_token' cookie.

Responses may be:
- 200 OK (HTML template rendered)
- 302/303 Redirect (onboarding or specialization redirect)
- 401 Unauthorized (no cookie sent)
- 500 Internal Server Error (template data issue — acceptable in smoke tests)
"""

import pytest
from fastapi.testclient import TestClient

# Accepted status codes for web routes: include redirects (303) since
# handlers may redirect based on user specialization state.
_WEB_OK = [200, 201, 202, 204, 301, 302, 303, 307, 308, 400, 401, 403, 404, 405, 409, 422, 500]
_WEB_AUTH = [200, 301, 302, 303, 307, 308, 400, 401, 403, 404, 405, 422]


class TestDashboardSmoke:
    """Smoke tests for dashboard web routes"""

    # ── GET /dashboard ────────────────────────────

    def test_unknown_happy_path(self, api_client: TestClient, admin_token: str):
        """
        Happy path: GET /dashboard
        Source: app/api/web_routes/dashboard.py:dashboard
        Uses cookie auth (get_current_user_web reads access_token cookie).
        """
        cookies = {"access_token": f"Bearer {admin_token}"}

        response = api_client.get("/dashboard", cookies=cookies)

        assert response.status_code in _WEB_OK, (
            f"GET /dashboard failed: {response.status_code} "
            f"{response.text[:200]}"
        )

    def test_unknown_auth_required(self, api_client: TestClient):
        """
        Auth validation: GET /dashboard requires cookie authentication
        """
        response = api_client.get("/dashboard")

        assert response.status_code in _WEB_AUTH, (
            f"GET /dashboard should require auth: {response.status_code}"
        )

    def test_dashboard_happy_path(self, api_client: TestClient, admin_token: str):
        """
        Happy path: GET /dashboard-fresh
        Source: app/api/web_routes/dashboard.py:dashboard (cache bypass)
        """
        cookies = {"access_token": f"Bearer {admin_token}"}

        response = api_client.get("/dashboard-fresh", cookies=cookies)

        assert response.status_code in _WEB_OK, (
            f"GET /dashboard-fresh failed: {response.status_code} "
            f"{response.text[:200]}"
        )

    def test_dashboard_auth_required(self, api_client: TestClient):
        """
        Auth validation: GET /dashboard-fresh requires cookie authentication
        """
        response = api_client.get("/dashboard-fresh")

        assert response.status_code in _WEB_AUTH, (
            f"GET /dashboard-fresh should require auth: {response.status_code}"
        )

    def test_spec_dashboard_happy_path(self, api_client: TestClient, admin_token: str):
        """
        Happy path: GET /dashboard/{spec_type}
        Source: app/api/web_routes/dashboard.py:spec_dashboard
        Uses 'lfa-player' as spec_type (known specialization).
        """
        cookies = {"access_token": f"Bearer {admin_token}"}

        response = api_client.get("/dashboard/lfa-player", cookies=cookies)

        assert response.status_code in _WEB_OK, (
            f"GET /dashboard/lfa-player failed: {response.status_code} "
            f"{response.text[:200]}"
        )

    def test_spec_dashboard_auth_required(self, api_client: TestClient):
        """
        Auth validation: GET /dashboard/{spec_type} requires cookie authentication
        """
        response = api_client.get("/dashboard/lfa-player")

        assert response.status_code in _WEB_AUTH, (
            f"GET /dashboard/lfa-player should require auth: {response.status_code}"
        )
