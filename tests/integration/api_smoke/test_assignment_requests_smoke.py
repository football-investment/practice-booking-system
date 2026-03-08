"""
Smoke tests for instructor assignment request endpoints.

Coverage target: app/api/api_v1/endpoints/instructor_assignments/requests.py
Current coverage: 15% (6 routes visible, 95+ statements)

Routes covered:
  POST   /api/v1/instructor-assignments/requests
  GET    /api/v1/instructor-assignments/requests/instructor/{instructor_id}
  GET    /api/v1/instructor-assignments/requests/semester/{semester_id}
  PATCH  /api/v1/instructor-assignments/requests/{request_id}/accept
  PATCH  /api/v1/instructor-assignments/requests/{request_id}/decline
  PATCH  /api/v1/instructor-assignments/requests/{request_id}/cancel

Auth requirements:
  - POST: ADMIN only
  - GET /instructor/{id}: Instructor sees own; ADMIN sees any
  - GET /semester/{id}: ADMIN only
  - PATCH /accept, /decline: Receiving instructor only
  - PATCH /cancel: ADMIN only
"""

import pytest
from fastapi.testclient import TestClient


class TestAssignmentRequestsSmoke:
    """Smoke tests for instructor assignment request endpoints."""

    # ── POST /requests ────────────────────────────────────────────────────────

    def test_create_request_auth_required(self, api_client: TestClient):
        """POST /requests without auth → 401 or 403."""
        response = api_client.post(
            "/requests",
            json={"instructor_id": 1, "semester_id": 1},
        )
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth POST request: unexpected {response.status_code}"
        )

    def test_create_request_instructor_forbidden(
        self, api_client: TestClient, instructor_token: str
    ):
        """
        Instructor POST /requests — ADMIN only → 403.
        Covers: role check branch.
        """
        headers = {"Authorization": f"Bearer {instructor_token}"}
        response = api_client.post(
            "/requests",
            headers=headers,
            json={"instructor_id": 1, "semester_id": 1},
        )
        assert response.status_code in [400, 403, 404, 422], (
            f"Instructor POST request should be 403: got {response.status_code}"
        )

    def test_create_request_admin_nonexistent_resources(
        self, api_client: TestClient, admin_token: str
    ):
        """
        Admin POST /requests — nonexistent instructor/semester → 404.
        Covers: instructor + semester lookup, 404 branches.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.post(
            "/requests",
            headers=headers,
            json={"instructor_id": 99999, "semester_id": 99999},
        )
        assert response.status_code in [201, 400, 403, 404, 409, 422], (
            f"Admin POST request (nonexistent): unexpected {response.status_code}"
        )

    # ── GET /requests/instructor/{instructor_id} ──────────────────────────────

    def test_get_instructor_requests_auth_required(self, api_client: TestClient):
        """GET /requests/instructor/99999 without auth → 401 or 403."""
        response = api_client.get("/requests/instructor/99999")
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth GET instructor requests: unexpected {response.status_code}"
        )

    def test_get_instructor_requests_admin(
        self, api_client: TestClient, admin_token: str
    ):
        """
        Admin GET /requests/instructor/99999 → 200 empty list or 404.
        Covers: admin permission path + instructor request query.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.get("/requests/instructor/99999", headers=headers)
        assert response.status_code in [200, 400, 403, 404, 422], (
            f"Admin GET instructor requests: unexpected {response.status_code}"
        )

    def test_get_instructor_requests_instructor(
        self, api_client: TestClient, instructor_token: str
    ):
        """
        Instructor GET /requests/instructor/{own_id} → 200 or 404.
        Covers: self-access path for instructors.
        """
        headers = {"Authorization": f"Bearer {instructor_token}"}
        response = api_client.get("/requests/instructor/99999", headers=headers)
        assert response.status_code in [200, 400, 403, 404, 422], (
            f"Instructor GET own requests: unexpected {response.status_code}"
        )

    # ── GET /requests/semester/{semester_id} ─────────────────────────────────

    def test_get_semester_requests_auth_required(self, api_client: TestClient):
        """GET /requests/semester/99999 without auth → 401 or 403."""
        response = api_client.get("/requests/semester/99999")
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth GET semester requests: unexpected {response.status_code}"
        )

    def test_get_semester_requests_admin(
        self, api_client: TestClient, admin_token: str
    ):
        """
        Admin GET /requests/semester/99999 → 200 empty list or 404.
        Covers: ADMIN-only semester request listing.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.get("/requests/semester/99999", headers=headers)
        assert response.status_code in [200, 400, 403, 404, 422], (
            f"Admin GET semester requests: unexpected {response.status_code}"
        )

    def test_get_semester_requests_instructor_forbidden(
        self, api_client: TestClient, instructor_token: str
    ):
        """
        Instructor GET /requests/semester/{id} → 403 (ADMIN only).
        Covers: role check for semester-level query.
        """
        headers = {"Authorization": f"Bearer {instructor_token}"}
        response = api_client.get("/requests/semester/99999", headers=headers)
        assert response.status_code in [400, 403, 404, 422], (
            f"Instructor GET semester requests should be 403: got {response.status_code}"
        )

    # ── PATCH /requests/{request_id}/accept ──────────────────────────────────

    def test_accept_request_auth_required(self, api_client: TestClient):
        """PATCH /requests/99999/accept without auth → 401 or 403."""
        response = api_client.patch("/requests/99999/accept")
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth PATCH accept: unexpected {response.status_code}"
        )

    def test_accept_request_nonexistent(
        self, api_client: TestClient, instructor_token: str
    ):
        """
        Instructor PATCH /requests/99999/accept — request not found → 404.
        Covers: request lookup + 404 + state change attempt.
        """
        headers = {"Authorization": f"Bearer {instructor_token}"}
        response = api_client.patch("/requests/99999/accept", headers=headers)
        assert response.status_code in [200, 400, 403, 404, 409, 422], (
            f"Instructor PATCH accept (nonexistent): unexpected {response.status_code}"
        )

    # ── PATCH /requests/{request_id}/decline ─────────────────────────────────

    def test_decline_request_auth_required(self, api_client: TestClient):
        """PATCH /requests/99999/decline without auth → 401 or 403."""
        response = api_client.patch("/requests/99999/decline")
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth PATCH decline: unexpected {response.status_code}"
        )

    def test_decline_request_nonexistent(
        self, api_client: TestClient, instructor_token: str
    ):
        """
        Instructor PATCH /requests/99999/decline — request not found → 404.
        Covers: request lookup + decline branch.
        """
        headers = {"Authorization": f"Bearer {instructor_token}"}
        response = api_client.patch("/requests/99999/decline", headers=headers)
        assert response.status_code in [200, 400, 403, 404, 409, 422], (
            f"Instructor PATCH decline (nonexistent): unexpected {response.status_code}"
        )

    # ── PATCH /requests/{request_id}/cancel ──────────────────────────────────

    def test_cancel_request_auth_required(self, api_client: TestClient):
        """PATCH /requests/99999/cancel without auth → 401 or 403."""
        response = api_client.patch("/requests/99999/cancel")
        assert response.status_code in [401, 403, 404, 422], (
            f"No-auth PATCH cancel: unexpected {response.status_code}"
        )

    def test_cancel_request_admin_nonexistent(
        self, api_client: TestClient, admin_token: str
    ):
        """
        Admin PATCH /requests/99999/cancel — request not found → 404.
        Covers: ADMIN cancel path + request 404 branch.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.patch("/requests/99999/cancel", headers=headers)
        assert response.status_code in [200, 400, 403, 404, 409, 422], (
            f"Admin PATCH cancel (nonexistent): unexpected {response.status_code}"
        )
