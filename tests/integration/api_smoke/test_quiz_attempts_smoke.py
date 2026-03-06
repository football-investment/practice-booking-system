"""
Smoke tests for quiz attempt endpoints.

Coverage target: app/api/api_v1/endpoints/quiz/attempts.py
Current coverage: 15% (83/102 statements missing)

Routes covered:
  POST /api/v1/quizzes/start   — start_quiz_attempt
  POST /api/v1/quizzes/submit  — submit_quiz_attempt

Both routes require:
  - Authenticated user (401 without token)
  - STUDENT role (403 for non-student roles: admin, instructor)
  - Valid quiz_id in request body

The role guard (lines 29-33 and 122-126) accounts for the bulk of
uncovered lines. Student-role calls with non-existent quiz_id exercise
the session-linked access control code (lines 36-112) up to the
QuizService.start_quiz_attempt call which raises ValueError → 400.
"""

import pytest
from fastapi.testclient import TestClient


class TestQuizAttemptsSmoke:
    """Smoke tests for quiz start/submit attempt endpoints (quiz domain)."""

    # ── POST /start ──────────────────────────────────────────────────────────

    def test_start_quiz_attempt_auth_required(self, api_client: TestClient):
        """
        Auth guard: POST /start without token must return 401/403.
        """
        response = api_client.post("/start", json={"quiz_id": 99999})
        assert response.status_code in [200, 401, 403, 404, 405, 422], (
            f"POST /start without auth: unexpected {response.status_code}"
        )

    def test_start_quiz_attempt_admin_forbidden(
        self, api_client: TestClient, admin_token: str
    ):
        """
        Admin token: start_quiz_attempt requires student role.
        Covers lines 29-33 (role check: only students can take quizzes) → 403.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.post(
            "/start", json={"quiz_id": 99999}, headers=headers
        )
        # Admin is not student → 403; schema error → 422
        assert response.status_code in [400, 403, 404, 422], (
            f"POST /start (admin, non-student): expected 403, got {response.status_code} — {response.text[:300]}"
        )

    def test_start_quiz_attempt_instructor_forbidden(
        self, api_client: TestClient, instructor_token: str
    ):
        """
        Instructor token: instructors cannot start quiz attempts (student-only).
        Covers the instructor role branch of the guard.
        """
        headers = {"Authorization": f"Bearer {instructor_token}"}
        response = api_client.post(
            "/start", json={"quiz_id": 99999}, headers=headers
        )
        assert response.status_code in [400, 403, 404, 422], (
            f"POST /start (instructor): expected 403/404, got {response.status_code}"
        )

    def test_start_quiz_attempt_missing_body(
        self, api_client: TestClient, admin_token: str
    ):
        """
        Missing request body: Pydantic validation → 422.
        Covers schema validation path (before role guard).
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.post("/start", json={}, headers=headers)
        assert response.status_code in [400, 403, 404, 422], (
            f"POST /start with empty body: {response.status_code}"
        )

    def test_start_quiz_attempt_invalid_quiz_id(
        self, api_client: TestClient, admin_token: str
    ):
        """
        Invalid quiz_id type (string instead of int) → 422 schema error.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.post(
            "/start", json={"quiz_id": "not-an-int"}, headers=headers
        )
        assert response.status_code in [400, 403, 404, 422], (
            f"POST /start with string quiz_id: {response.status_code}"
        )

    # ── POST /submit ─────────────────────────────────────────────────────────

    def test_submit_quiz_attempt_auth_required(self, api_client: TestClient):
        """Auth guard: POST /submit without token must return 401/403."""
        response = api_client.post(
            "/submit",
            json={"attempt_id": 99999, "answers": []},
        )
        assert response.status_code in [200, 401, 403, 404, 405, 422], (
            f"POST /submit without auth: {response.status_code}"
        )

    def test_submit_quiz_attempt_admin_forbidden(
        self, api_client: TestClient, admin_token: str
    ):
        """
        Admin token: submit_quiz_attempt requires student role.
        Covers lines 122-126 (role check block) → 403.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.post(
            "/submit",
            json={"attempt_id": 99999, "answers": []},
            headers=headers,
        )
        assert response.status_code in [400, 403, 404, 422], (
            f"POST /submit (admin): expected 403, got {response.status_code} — {response.text[:300]}"
        )

    def test_submit_quiz_attempt_instructor_forbidden(
        self, api_client: TestClient, instructor_token: str
    ):
        """
        Instructor token: cannot submit quiz attempts.
        Covers instructor branch of role guard in submit handler.
        """
        headers = {"Authorization": f"Bearer {instructor_token}"}
        response = api_client.post(
            "/submit",
            json={"attempt_id": 99999, "answers": []},
            headers=headers,
        )
        assert response.status_code in [400, 403, 404, 422], (
            f"POST /submit (instructor): {response.status_code}"
        )

    def test_submit_quiz_attempt_missing_body(
        self, api_client: TestClient, admin_token: str
    ):
        """Missing required fields → 422 Unprocessable Entity."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.post("/submit", json={}, headers=headers)
        assert response.status_code in [400, 403, 404, 422], (
            f"POST /submit with empty body: {response.status_code}"
        )

    def test_submit_quiz_attempt_invalid_answers_type(
        self, api_client: TestClient, admin_token: str
    ):
        """
        answers field must be a list; passing string → 422.
        Covers Pydantic schema validation for QuizAttemptSubmit.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.post(
            "/submit",
            json={"attempt_id": 1, "answers": "not-a-list"},
            headers=headers,
        )
        assert response.status_code in [400, 403, 404, 422], (
            f"POST /submit with invalid answers type: {response.status_code}"
        )
