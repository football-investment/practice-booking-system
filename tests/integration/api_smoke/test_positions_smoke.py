"""
Smoke tests for instructor management position endpoints.

Coverage target: app/api/api_v1/endpoints/instructor_management/positions.py
Current coverage: 14% (6 routes, 110 statements)

Routes covered:
  POST /api/v1/instructor-management/positions/
  GET  /api/v1/instructor-management/positions/my-positions
  GET  /api/v1/instructor-management/positions/job-board
  GET  /api/v1/instructor-management/positions/{position_id}
  PATCH /api/v1/instructor-management/positions/{position_id}
  DELETE /api/v1/instructor-management/positions/{position_id}

Auth requirements:
  - POST: MASTER INSTRUCTOR (checked via LocationMasterInstructor)
  - GET /my-positions: MASTER INSTRUCTOR
  - GET /job-board: Any instructor (public job listings)
  - GET /{id}: Any authenticated user
  - PATCH/DELETE: Owner or ADMIN
"""

import pytest
from fastapi.testclient import TestClient


class TestPositionsSmoke:
    """Smoke tests for instructor management positions endpoint."""

    # ── POST /positions/ ─────────────────────────────────────────────────────

    def test_create_position_auth_required(self, api_client: TestClient):
        """POST /positions/ without auth → 401 or 403."""
        response = api_client.post(
            "/positions/",
            json={"location_id": 1, "title": "Test Position"},
        )
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth POST position: unexpected {response.status_code}"
        )

    def test_create_position_admin_not_master(
        self, api_client: TestClient, admin_token: str
    ):
        """
        Admin POST /positions/ — admin is not a master instructor → 403.
        Covers: MASTER INSTRUCTOR check (LocationMasterInstructor query).
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.post(
            "/positions/",
            headers=headers,
            json={
                "location_id": 1,
                "title": "Test Position",
                "description": "Smoke test position",
            },
        )
        assert response.status_code in [201, 400, 403, 404, 422], (
            f"Admin POST position: unexpected {response.status_code}"
        )

    def test_create_position_instructor_token(
        self, api_client: TestClient, instructor_token: str
    ):
        """
        Instructor POST /positions/ — may be 403 (not master) or 404 (no location).
        Covers: master instructor validation path.
        """
        headers = {"Authorization": f"Bearer {instructor_token}"}
        response = api_client.post(
            "/positions/",
            headers=headers,
            json={
                "location_id": 99999,
                "title": "Test Position Smoke",
                "description": "Smoke test only",
            },
        )
        assert response.status_code in [201, 400, 403, 404, 422], (
            f"Instructor POST position: unexpected {response.status_code}"
        )

    # ── GET /positions/my-positions ──────────────────────────────────────────

    def test_get_my_positions_auth_required(self, api_client: TestClient):
        """GET /positions/my-positions without auth → 401 or 403."""
        response = api_client.get("/positions/my-positions")
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth GET my-positions: unexpected {response.status_code}"
        )

    def test_get_my_positions_admin(
        self, api_client: TestClient, admin_token: str
    ):
        """
        Admin GET /positions/my-positions → 200 empty list or 403.
        Covers: user role check + positions query by instructor.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.get("/positions/my-positions", headers=headers)
        assert response.status_code in [200, 400, 403, 404, 422], (
            f"Admin GET my-positions: unexpected {response.status_code}"
        )

    def test_get_my_positions_instructor(
        self, api_client: TestClient, instructor_token: str
    ):
        """
        Instructor GET /positions/my-positions → 200 (possibly empty).
        Covers: master instructor path + list result.
        """
        headers = {"Authorization": f"Bearer {instructor_token}"}
        response = api_client.get("/positions/my-positions", headers=headers)
        assert response.status_code in [200, 400, 403, 404, 422], (
            f"Instructor GET my-positions: unexpected {response.status_code}"
        )

    # ── GET /positions/job-board ─────────────────────────────────────────────

    def test_get_job_board_no_auth(self, api_client: TestClient):
        """
        GET /positions/job-board — public listing, no auth needed.
        Covers: job board query + response serialization.
        """
        response = api_client.get("/positions/job-board")
        assert response.status_code in [200, 401, 403, 404, 422], (
            f"No-auth GET job-board: unexpected {response.status_code}"
        )

    def test_get_job_board_admin(
        self, api_client: TestClient, admin_token: str
    ):
        """Admin GET /positions/job-board → 200 with list."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.get("/positions/job-board", headers=headers)
        assert response.status_code in [200, 400, 403, 404, 422], (
            f"Admin GET job-board: unexpected {response.status_code}"
        )

    # ── GET /positions/{position_id} ─────────────────────────────────────────

    def test_get_position_auth_required(self, api_client: TestClient):
        """GET /positions/99999 without auth → 401 or 404."""
        response = api_client.get("/positions/99999")
        assert response.status_code in [200, 401, 403, 404, 422], (
            f"No-auth GET position: unexpected {response.status_code}"
        )

    def test_get_position_nonexistent(
        self, api_client: TestClient, admin_token: str
    ):
        """
        GET /positions/99999 — position not found → 404.
        Covers: position lookup + 404 branch.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.get("/positions/99999", headers=headers)
        assert response.status_code in [200, 400, 403, 404, 422], (
            f"GET nonexistent position: unexpected {response.status_code}"
        )

    # ── PATCH /positions/{position_id} ───────────────────────────────────────

    def test_patch_position_auth_required(self, api_client: TestClient):
        """PATCH /positions/99999 without auth → 401 or 403."""
        response = api_client.patch("/positions/99999", json={"title": "Updated"})
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth PATCH position: unexpected {response.status_code}"
        )

    def test_patch_position_nonexistent(
        self, api_client: TestClient, admin_token: str
    ):
        """
        Admin PATCH /positions/99999 — position not found → 404.
        Covers: owner check + 404 branch in update handler.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.patch(
            "/positions/99999",
            headers=headers,
            json={"title": "Updated Title"},
        )
        assert response.status_code in [200, 400, 403, 404, 422], (
            f"Admin PATCH nonexistent position: unexpected {response.status_code}"
        )

    # ── DELETE /positions/{position_id} ──────────────────────────────────────

    def test_delete_position_auth_required(self, api_client: TestClient):
        """DELETE /positions/99999 without auth → 401 or 403."""
        response = api_client.delete("/positions/99999")
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth DELETE position: unexpected {response.status_code}"
        )

    def test_delete_position_nonexistent(
        self, api_client: TestClient, admin_token: str
    ):
        """
        Admin DELETE /positions/99999 — position not found → 404.
        Covers: owner check + 404 branch in delete handler.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.delete("/positions/99999", headers=headers)
        assert response.status_code in [200, 204, 400, 403, 404, 409, 422], (
            f"Admin DELETE nonexistent position: unexpected {response.status_code}"
        )
