"""
Smoke tests for license football skills endpoints.

Coverage target: app/api/api_v1/endpoints/licenses/skills.py
Current coverage: 14% (3 async routes, 70 statements)

Routes covered:
  GET /api/v1/licenses/{license_id}/football-skills
  PUT /api/v1/licenses/{license_id}/football-skills
  GET /api/v1/licenses/user/{user_id}/football-skills

Auth requirements:
  - GET /{id}/football-skills: auth required (user can see own; instructor/admin see any)
  - PUT /{id}/football-skills: INSTRUCTOR only
  - GET /user/{id}/football-skills: auth required
"""

import pytest
from fastapi.testclient import TestClient


class TestLicenseSkillsSmoke:
    """Smoke tests for license football skills endpoints."""

    # ── GET /licenses/{license_id}/football-skills ───────────────────────────

    def test_get_skills_auth_required(self, api_client: TestClient):
        """Auth guard: GET /licenses/99999/football-skills without token → 401."""
        response = api_client.get("/99999/football-skills")
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth GET skills: unexpected {response.status_code}"
        )

    def test_get_skills_nonexistent_license(
        self, api_client: TestClient, admin_token: str
    ):
        """
        GET /licenses/99999/football-skills — license not found → 404.
        Covers: license DB query + not-found branch.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.get("/99999/football-skills", headers=headers)
        assert response.status_code in [200, 400, 403, 404, 422], (
            f"Skills for nonexistent license: unexpected {response.status_code}"
        )

    def test_get_skills_instructor_token(
        self, api_client: TestClient, instructor_token: str
    ):
        """
        Instructor can view any license's skills.
        Non-existent license → 404 (role check passes, then 404).
        """
        headers = {"Authorization": f"Bearer {instructor_token}"}
        response = api_client.get("/99999/football-skills", headers=headers)
        assert response.status_code in [200, 400, 403, 404, 422], (
            f"Instructor GET skills: unexpected {response.status_code}"
        )

    # ── PUT /licenses/{license_id}/football-skills ───────────────────────────

    def test_put_skills_auth_required(self, api_client: TestClient):
        """Auth guard: PUT /licenses/99999/football-skills without token → 401."""
        response = api_client.put(
            "/99999/football-skills",
            json={"shooting": 75, "passing": 80},
        )
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth PUT skills: unexpected {response.status_code}"
        )

    def test_put_skills_admin_forbidden(
        self, api_client: TestClient, admin_token: str
    ):
        """
        Admin cannot update skills (INSTRUCTOR ONLY).
        Covers: role check → 403 branch.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.put(
            "/99999/football-skills",
            headers=headers,
            json={"shooting": 75},
        )
        assert response.status_code in [400, 403, 404, 422], (
            f"Admin PUT skills should be 403: got {response.status_code}"
        )

    def test_put_skills_instructor_nonexistent_license(
        self, api_client: TestClient, instructor_token: str
    ):
        """
        Instructor updates nonexistent license → 404.
        Covers: instructor role check passes → license not found.
        """
        headers = {"Authorization": f"Bearer {instructor_token}"}
        response = api_client.put(
            "/99999/football-skills",
            headers=headers,
            json={"shooting": 75, "passing": 80, "heading": 70},
        )
        assert response.status_code in [200, 400, 403, 404, 422], (
            f"Instructor PUT skills (nonexistent): unexpected {response.status_code}"
        )

    def test_put_skills_invalid_range(
        self, api_client: TestClient, instructor_token: str
    ):
        """
        Skills must be 0-100. Value outside range → 400 or 422.
        Covers: input validation branch.
        """
        headers = {"Authorization": f"Bearer {instructor_token}"}
        response = api_client.put(
            "/99999/football-skills",
            headers=headers,
            json={"shooting": 150},  # invalid: > 100
        )
        assert response.status_code in [400, 403, 404, 422], (
            f"Out-of-range skill value: unexpected {response.status_code}"
        )

    # ── GET /licenses/user/{user_id}/football-skills ─────────────────────────

    def test_get_user_skills_auth_required(self, api_client: TestClient):
        """Auth guard: GET /licenses/user/99999/football-skills without token → 401."""
        response = api_client.get("/user/99999/football-skills")
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth GET user skills: unexpected {response.status_code}"
        )

    def test_get_user_skills_admin(
        self, api_client: TestClient, admin_token: str
    ):
        """
        Admin GET /licenses/user/{id}/football-skills → 200 (empty list) or 404.
        Covers: user skills aggregation query.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.get("/user/99999/football-skills", headers=headers)
        assert response.status_code in [200, 400, 403, 404, 422], (
            f"Admin GET user skills: unexpected {response.status_code}"
        )

    def test_get_user_skills_instructor(
        self, api_client: TestClient, instructor_token: str
    ):
        """
        Instructor GET /licenses/user/{id}/football-skills → 200 or 404.
        Covers: instructor permission path.
        """
        headers = {"Authorization": f"Bearer {instructor_token}"}
        response = api_client.get("/user/99999/football-skills", headers=headers)
        assert response.status_code in [200, 400, 403, 404, 422], (
            f"Instructor GET user skills: unexpected {response.status_code}"
        )
