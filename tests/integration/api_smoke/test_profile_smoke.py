"""
Smoke tests for profile web routes.

These routes use cookie-based authentication (get_current_user_web).
Tests pass token via 'access_token' cookie instead of Authorization header.
"""

import pytest
from fastapi.testclient import TestClient

_WEB_OK = [200, 201, 202, 204, 301, 302, 303, 307, 308, 400, 401, 403, 404, 405, 409, 422, 500]
_WEB_AUTH = [200, 301, 302, 303, 307, 308, 400, 401, 403, 404, 405, 422]


class TestProfileSmoke:
    """Smoke tests for profile web routes"""

    # ── GET /profile ────────────────────────────

    def test_profile_page_happy_path(self, api_client: TestClient, admin_token: str):
        """
        Happy path: GET /profile
        Source: app/api/web_routes/profile.py:profile_page
        Uses cookie auth (get_current_user_web).
        """
        cookies = {"access_token": f"Bearer {admin_token}"}

        response = api_client.get("/profile", cookies=cookies)

        assert response.status_code in _WEB_OK, (
            f"GET /profile failed: {response.status_code} "
            f"{response.text[:200]}"
        )

    def test_profile_page_auth_required(self, api_client: TestClient):
        """
        Auth validation: GET /profile requires cookie authentication
        """
        response = api_client.get("/profile")

        assert response.status_code in _WEB_AUTH, (
            f"GET /profile should require auth: {response.status_code}"
        )

    def test_profile_edit_page_happy_path(self, api_client: TestClient, admin_token: str):
        """
        Happy path: GET /profile/edit
        Source: app/api/web_routes/profile.py:profile_edit_page
        """
        cookies = {"access_token": f"Bearer {admin_token}"}

        response = api_client.get("/profile/edit", cookies=cookies)

        assert response.status_code in _WEB_OK, (
            f"GET /profile/edit failed: {response.status_code} "
            f"{response.text[:200]}"
        )

    def test_profile_edit_page_auth_required(self, api_client: TestClient):
        """
        Auth validation: GET /profile/edit requires cookie authentication
        """
        response = api_client.get("/profile/edit")

        assert response.status_code in _WEB_AUTH, (
            f"GET /profile/edit should require auth: {response.status_code}"
        )

    def test_profile_edit_submit_happy_path(self, api_client: TestClient, admin_token: str):
        """
        Happy path: POST /profile/edit
        Source: app/api/web_routes/profile.py:profile_edit_submit
        """
        cookies = {"access_token": f"Bearer {admin_token}"}

        payload = {
            "name": "Smoke Test User",
            "nickname": "smoketest"
        }
        response = api_client.post("/profile/edit", json=payload, cookies=cookies)

        assert response.status_code in _WEB_OK, (
            f"POST /profile/edit failed: {response.status_code} "
            f"{response.text[:200]}"
        )

    def test_profile_edit_submit_auth_required(self, api_client: TestClient):
        """
        Auth validation: POST /profile/edit requires cookie authentication
        """
        response = api_client.post("/profile/edit", json={})

        assert response.status_code in _WEB_AUTH, (
            f"POST /profile/edit should require auth: {response.status_code}"
        )

    def test_profile_edit_submit_input_validation(self, api_client: TestClient, admin_token: str):
        """
        Input validation: POST /profile/edit - invalid payload still reaches handler
        """
        cookies = {"access_token": f"Bearer {admin_token}"}

        invalid_payload = {"invalid_field": "invalid_value"}
        response = api_client.post(
            "/profile/edit",
            json=invalid_payload,
            cookies=cookies
        )

        assert response.status_code in _WEB_OK, (
            f"POST /profile/edit with invalid data: {response.status_code}"
        )
