"""
Smoke tests for student_features web routes.

These routes use cookie-based authentication (get_current_user_web).
Prefix is "" — paths are tested directly without /api/v1/ prefix.
"""

import pytest
from fastapi.testclient import TestClient

_WEB_OK = [200, 201, 202, 204, 301, 302, 303, 307, 308, 400, 401, 403, 404, 405, 409, 422, 500]
_WEB_AUTH = [200, 301, 302, 303, 307, 308, 400, 401, 403, 404, 405, 422]


class TestStudentfeaturesSmoke:
    """Smoke tests for student_features web routes"""

    # ── GET /about-specializations ────────────────────────────

    def test_about_specializations_page_happy_path(self, api_client: TestClient, admin_token: str):
        """
        Happy path: GET /about-specializations
        Source: app/api/web_routes/student_features.py:about_specializations_page
        Uses cookie auth (get_current_user_web).
        """
        cookies = {"access_token": f"Bearer {admin_token}"}

        response = api_client.get("/about-specializations", cookies=cookies)

        assert response.status_code in _WEB_OK, (
            f"GET /about-specializations failed: {response.status_code} "
            f"{response.text[:200]}"
        )

    def test_about_specializations_page_auth_required(self, api_client: TestClient):
        """
        Auth validation: GET /about-specializations requires cookie authentication
        """
        response = api_client.get("/about-specializations")

        assert response.status_code in _WEB_AUTH, (
            f"GET /about-specializations should require auth: {response.status_code}"
        )

    def test_achievements_page_happy_path(self, api_client: TestClient, admin_token: str):
        """
        Happy path: GET /achievements
        Source: app/api/web_routes/student_features.py:achievements_page
        """
        cookies = {"access_token": f"Bearer {admin_token}"}

        response = api_client.get("/achievements", cookies=cookies)

        assert response.status_code in _WEB_OK, (
            f"GET /achievements failed: {response.status_code} "
            f"{response.text[:200]}"
        )

    def test_achievements_page_auth_required(self, api_client: TestClient):
        """
        Auth validation: GET /achievements requires cookie authentication
        """
        response = api_client.get("/achievements")

        assert response.status_code in _WEB_AUTH, (
            f"GET /achievements should require auth: {response.status_code}"
        )

    def test_credits_page_happy_path(self, api_client: TestClient, admin_token: str):
        """
        Happy path: GET /credits
        Source: app/api/web_routes/student_features.py:credits_page
        """
        cookies = {"access_token": f"Bearer {admin_token}"}

        response = api_client.get("/credits", cookies=cookies)

        assert response.status_code in _WEB_OK, (
            f"GET /credits failed: {response.status_code} "
            f"{response.text[:200]}"
        )

    def test_credits_page_auth_required(self, api_client: TestClient):
        """
        Auth validation: GET /credits requires cookie authentication
        """
        response = api_client.get("/credits")

        assert response.status_code in _WEB_AUTH, (
            f"GET /credits should require auth: {response.status_code}"
        )

    def test_progress_page_happy_path(self, api_client: TestClient, admin_token: str):
        """
        Happy path: GET /progress
        Source: app/api/web_routes/student_features.py:progress_page
        """
        cookies = {"access_token": f"Bearer {admin_token}"}

        response = api_client.get("/progress", cookies=cookies)

        assert response.status_code in _WEB_OK, (
            f"GET /progress failed: {response.status_code} "
            f"{response.text[:200]}"
        )

    def test_progress_page_auth_required(self, api_client: TestClient):
        """
        Auth validation: GET /progress requires cookie authentication
        """
        response = api_client.get("/progress")

        assert response.status_code in _WEB_AUTH, (
            f"GET /progress should require auth: {response.status_code}"
        )
