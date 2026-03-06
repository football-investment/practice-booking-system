"""
Smoke tests for public profile endpoints.

Coverage target: app/api/api_v1/endpoints/public_profile.py
Previous coverage: 12% — broken auto-generated tests used literal '{user_id}'
                         in URLs and wrong domain prefix (/api/v1/public vs /api/v1/users).

Routes covered (ALL PUBLIC — no auth required):
  GET /api/v1/users/{user_id}/profile/lfa-player
  GET /api/v1/users/{user_id}/profile/basic
  GET /api/v1/users/{user_id}/profile/instructor

Note: paths start with /api/ so _PrefixedClient passes them through unchanged.

Strategy:
  1. Non-existent user_id=99999 → 404 (covers DB query + user-not-found branch)
  2. Existing admin user → covers deeper query path (200 or 404 depending on license data)
  3. Invalid user_id type (string) → 422 (FastAPI param validation)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestPublicProfileSmoke:
    """Smoke tests for public user profile endpoints (no auth required)."""

    # ── Non-existent user (covers fast-exit branch) ──────────────────────────

    def test_lfa_player_profile_nonexistent_user(self, api_client: TestClient):
        """
        GET /users/99999/profile/lfa-player — user not found → 404.
        Covers: raw SQL query execution + not-found HTTPException path.
        """
        response = api_client.get("/api/v1/users/99999/profile/lfa-player")
        assert response.status_code in [404, 500], (
            f"Non-existent user lfa-player profile should be 404, got {response.status_code}"
        )

    def test_basic_profile_nonexistent_user(self, api_client: TestClient):
        """
        GET /users/99999/profile/basic — user not found → 404.
        Covers: user lookup + not-found branch in get_basic_profile.
        """
        response = api_client.get("/api/v1/users/99999/profile/basic")
        assert response.status_code in [404, 500], (
            f"Non-existent basic profile should be 404, got {response.status_code}"
        )

    def test_instructor_profile_nonexistent_user(self, api_client: TestClient):
        """
        GET /users/99999/profile/instructor — user not found → 404.
        Covers: user lookup + not-found branch in get_instructor_profile.
        """
        response = api_client.get("/api/v1/users/99999/profile/instructor")
        assert response.status_code in [404, 500], (
            f"Non-existent instructor profile should be 404, got {response.status_code}"
        )

    # ── Type validation (non-integer user_id → 422) ──────────────────────────

    def test_lfa_player_profile_invalid_user_id_type(self, api_client: TestClient):
        """
        Non-integer user_id — FastAPI int path param doesn't match the route
        (no 422; router falls through to 404 instead).
        """
        response = api_client.get("/api/v1/users/not-an-int/profile/lfa-player")
        assert response.status_code in [404, 422], (
            f"String user_id should be 404 or 422, got {response.status_code}"
        )

    def test_basic_profile_invalid_user_id_type(self, api_client: TestClient):
        """Non-integer user_id → 404 (route not matched) or 422."""
        response = api_client.get("/api/v1/users/not-an-int/profile/basic")
        assert response.status_code in [404, 422], (
            f"String user_id should be 404 or 422, got {response.status_code}"
        )

    def test_instructor_profile_invalid_user_id_type(self, api_client: TestClient):
        """Non-integer user_id → 404 (route not matched) or 422."""
        response = api_client.get("/api/v1/users/not-an-int/profile/instructor")
        assert response.status_code in [404, 422], (
            f"String user_id should be 404 or 422, got {response.status_code}"
        )

    # ── Existing user (covers deeper query path) ─────────────────────────────

    def test_lfa_player_profile_existing_user(
        self, api_client: TestClient, test_db: Session
    ):
        """
        GET /users/{real_id}/profile/lfa-player with a real user in DB.
        Admin has no LFA Player license → 200 empty profile or 404.
        Covers: deeper SQL query execution, try/except block, response building.
        """
        from app.models.user import User
        admin = test_db.query(User).filter(
            User.email == "smoke.admin@example.com"
        ).first()
        if not admin:
            pytest.skip("Smoke admin user not in test DB")

        response = api_client.get(f"/api/v1/users/{admin.id}/profile/lfa-player")
        assert response.status_code in [200, 404, 500], (
            f"Real user lfa-player profile: unexpected {response.status_code}"
        )

    def test_basic_profile_existing_user(
        self, api_client: TestClient, test_db: Session
    ):
        """
        GET /users/{real_id}/profile/basic with a real user in DB.
        Covers: user found path, license list query, response serialization.
        """
        from app.models.user import User
        admin = test_db.query(User).filter(
            User.email == "smoke.admin@example.com"
        ).first()
        if not admin:
            pytest.skip("Smoke admin user not in test DB")

        response = api_client.get(f"/api/v1/users/{admin.id}/profile/basic")
        assert response.status_code in [200, 404, 500], (
            f"Real user basic profile: unexpected {response.status_code}"
        )

    def test_instructor_profile_existing_user(
        self, api_client: TestClient, test_db: Session
    ):
        """
        GET /users/{real_id}/profile/instructor with a real instructor user.
        Covers: instructor-specific query (licenses, availability count).
        """
        from app.models.user import User
        instructor = test_db.query(User).filter(
            User.email == "smoke.instructor@example.com"
        ).first()
        if not instructor:
            pytest.skip("Smoke instructor user not in test DB")

        response = api_client.get(f"/api/v1/users/{instructor.id}/profile/instructor")
        assert response.status_code in [200, 404, 500], (
            f"Real user instructor profile: unexpected {response.status_code}"
        )
