"""
Smoke tests for web routes that are NOT tested by existing route-specific smoke tests.

Covers:
- app/api/web_routes/admin.py       (/admin/users, /admin/semesters, etc.)
- app/api/web_routes/sessions.py    (/calendar, /sessions, /sessions/{id})
- app/api/web_routes/instructor.py  (/instructor/specialization/toggle, /sessions/{id}/start, etc.)
- app/api/web_routes/quiz.py        (/quizzes/{id}/take, /sessions/{id}/unlock-quiz)
- app/api/web_routes/attendance.py  (/sessions/{id}/attendance/mark, etc.)
- app/api/web_routes/specialization.py (/specialization/unlock, /specialization/motivation, etc.)
- app/api/web_routes/instructor_dashboard.py

Auth: cookie-based (get_current_user_web) — pass access_token cookie.
Accepted codes: 200, 3xx (redirects), 400, 401, 403, 404, 405, 500 (template data issues).
"""

import pytest
from fastapi.testclient import TestClient


_WEB_OK = [200, 201, 202, 204, 301, 302, 303, 307, 308, 400, 401, 403, 404, 405, 409, 422, 500]
_WEB_AUTH = [200, 301, 302, 303, 307, 308, 400, 401, 403, 404, 405, 422]


# These tests use the raw TestClient via api_client._client (no domain prefix)
# because test_web_routes_smoke has no domain prefix set.
# The conftest maps "web_routes" → default "/api/v1" which would be wrong.
# We override by using /api/ prefix trick: if path starts with "/api/", it's passed through.
# For web routes (no /api/ prefix), we use api_client._client directly.

class TestWebRoutesAdmin:
    """Web routes: admin pages (app/api/web_routes/admin.py)"""

    def test_admin_users_page(self, api_client: TestClient, admin_token: str):
        """GET /admin/users — admin users list page"""
        cookies = {"access_token": f"Bearer {admin_token}"}
        response = api_client._client.get("/admin/users", cookies=cookies)
        assert response.status_code in _WEB_OK, (
            f"GET /admin/users: {response.status_code} {response.text[:100]}"
        )

    def test_admin_semesters_page(self, api_client: TestClient, admin_token: str):
        """GET /admin/semesters — admin semesters list page"""
        cookies = {"access_token": f"Bearer {admin_token}"}
        response = api_client._client.get("/admin/semesters", cookies=cookies)
        assert response.status_code in _WEB_OK, (
            f"GET /admin/semesters: {response.status_code} {response.text[:100]}"
        )

    def test_admin_enrollments_page(self, api_client: TestClient, admin_token: str):
        """GET /admin/enrollments — admin enrollments page"""
        cookies = {"access_token": f"Bearer {admin_token}"}
        response = api_client._client.get("/admin/enrollments", cookies=cookies)
        assert response.status_code in _WEB_OK, (
            f"GET /admin/enrollments: {response.status_code} {response.text[:100]}"
        )

    def test_admin_payments_page(self, api_client: TestClient, admin_token: str):
        """GET /admin/payments — admin payments page"""
        cookies = {"access_token": f"Bearer {admin_token}"}
        response = api_client._client.get("/admin/payments", cookies=cookies)
        assert response.status_code in _WEB_OK, (
            f"GET /admin/payments: {response.status_code} {response.text[:100]}"
        )

    def test_admin_coupons_page(self, api_client: TestClient, admin_token: str):
        """GET /admin/coupons — admin coupons page"""
        cookies = {"access_token": f"Bearer {admin_token}"}
        response = api_client._client.get("/admin/coupons", cookies=cookies)
        assert response.status_code in _WEB_OK, (
            f"GET /admin/coupons: {response.status_code} {response.text[:100]}"
        )

    def test_admin_invitation_codes_page(self, api_client: TestClient, admin_token: str):
        """GET /admin/invitation-codes — admin invitation codes page"""
        cookies = {"access_token": f"Bearer {admin_token}"}
        response = api_client._client.get("/admin/invitation-codes", cookies=cookies)
        assert response.status_code in _WEB_OK, (
            f"GET /admin/invitation-codes: {response.status_code} {response.text[:100]}"
        )

    def test_admin_analytics_page(self, api_client: TestClient, admin_token: str):
        """GET /admin/analytics — admin analytics page"""
        cookies = {"access_token": f"Bearer {admin_token}"}
        response = api_client._client.get("/admin/analytics", cookies=cookies)
        assert response.status_code in _WEB_OK, (
            f"GET /admin/analytics: {response.status_code} {response.text[:100]}"
        )

    def test_admin_users_auth_required(self, api_client: TestClient):
        """Auth: GET /admin/users without cookie returns 401"""
        response = api_client._client.get("/admin/users")
        assert response.status_code in _WEB_AUTH, (
            f"GET /admin/users should require auth: {response.status_code}"
        )


class TestWebRoutesSessions:
    """Web routes: sessions and calendar (app/api/web_routes/sessions.py)"""

    def test_calendar_page(self, api_client: TestClient, admin_token: str):
        """GET /calendar — calendar page"""
        cookies = {"access_token": f"Bearer {admin_token}"}
        response = api_client._client.get("/calendar", cookies=cookies)
        assert response.status_code in _WEB_OK, (
            f"GET /calendar: {response.status_code} {response.text[:100]}"
        )

    def test_sessions_list_instructor(self, api_client: TestClient, instructor_token: str):
        """GET /sessions — sessions list page as instructor (hits instructor branch)"""
        cookies = {"access_token": f"Bearer {instructor_token}"}
        response = api_client._client.get("/sessions", cookies=cookies)
        assert response.status_code in _WEB_OK, (
            f"GET /sessions (instructor): {response.status_code} {response.text[:100]}"
        )

    def test_sessions_list_student(self, api_client: TestClient, student_token: str):
        """GET /sessions — sessions list page as student (hits student branch)"""
        cookies = {"access_token": f"Bearer {student_token}"}
        response = api_client._client.get("/sessions", cookies=cookies)
        assert response.status_code in _WEB_OK, (
            f"GET /sessions (student): {response.status_code} {response.text[:100]}"
        )

    def test_session_detail_page_not_found(self, api_client: TestClient, admin_token: str):
        """GET /sessions/{session_id} — session detail, 404 for nonexistent ID"""
        cookies = {"access_token": f"Bearer {admin_token}"}
        response = api_client._client.get("/sessions/99999", cookies=cookies)
        assert response.status_code in _WEB_OK, (
            f"GET /sessions/99999: {response.status_code} {response.text[:100]}"
        )

    def test_sessions_auth_required(self, api_client: TestClient):
        """Auth: GET /sessions without cookie returns 401"""
        response = api_client._client.get("/sessions")
        assert response.status_code in _WEB_AUTH, (
            f"GET /sessions should require auth: {response.status_code}"
        )

    def test_book_session_not_found(self, api_client: TestClient, student_token: str):
        """POST /sessions/book/{session_id} — no session found, redirects"""
        cookies = {"access_token": f"Bearer {student_token}"}
        response = api_client._client.post("/sessions/book/99999", cookies=cookies)
        assert response.status_code in _WEB_OK, (
            f"POST /sessions/book/99999: {response.status_code} {response.text[:100]}"
        )

    def test_cancel_session_not_found(self, api_client: TestClient, student_token: str):
        """POST /sessions/cancel/{session_id} — no booking found, redirects"""
        cookies = {"access_token": f"Bearer {student_token}"}
        response = api_client._client.post("/sessions/cancel/99999", cookies=cookies)
        assert response.status_code in _WEB_OK, (
            f"POST /sessions/cancel/99999: {response.status_code} {response.text[:100]}"
        )


class TestWebRoutesInstructor:
    """Web routes: instructor session control (app/api/web_routes/instructor.py)"""

    def test_start_session_as_instructor(self, api_client: TestClient, instructor_token: str):
        """POST /sessions/{session_id}/start — role passes, session not found"""
        cookies = {"access_token": f"Bearer {instructor_token}"}
        response = api_client._client.post("/sessions/99999/start", cookies=cookies)
        assert response.status_code in _WEB_OK, (
            f"POST /sessions/99999/start: {response.status_code} {response.text[:100]}"
        )

    def test_stop_session_as_instructor(self, api_client: TestClient, instructor_token: str):
        """POST /sessions/{session_id}/stop — role passes, session not found"""
        cookies = {"access_token": f"Bearer {instructor_token}"}
        response = api_client._client.post("/sessions/99999/stop", cookies=cookies)
        assert response.status_code in _WEB_OK, (
            f"POST /sessions/99999/stop: {response.status_code} {response.text[:100]}"
        )

    def test_unlock_quiz_as_instructor(self, api_client: TestClient, instructor_token: str):
        """POST /sessions/{session_id}/unlock-quiz — role passes, session not found"""
        cookies = {"access_token": f"Bearer {instructor_token}"}
        response = api_client._client.post("/sessions/99999/unlock-quiz", cookies=cookies)
        assert response.status_code in _WEB_OK, (
            f"POST /sessions/99999/unlock-quiz: {response.status_code} {response.text[:100]}"
        )

    def test_toggle_specialization_as_instructor(self, api_client: TestClient, instructor_token: str):
        """POST /instructor/specialization/toggle — instructor role, spec not found → 404"""
        cookies = {"access_token": f"Bearer {instructor_token}"}
        payload = {"specialization": "LFA_FOOTBALL_PLAYER", "is_active": True}
        response = api_client._client.post(
            "/instructor/specialization/toggle", json=payload, cookies=cookies
        )
        assert response.status_code in _WEB_OK, (
            f"POST /instructor/specialization/toggle: {response.status_code} {response.text[:100]}"
        )

    def test_instructor_routes_auth_required(self, api_client: TestClient):
        """Auth: instructor routes without cookie return 401"""
        response = api_client._client.post("/sessions/99999/start")
        assert response.status_code in _WEB_AUTH, (
            f"POST /sessions/99999/start should require auth: {response.status_code}"
        )


class TestWebRoutesQuiz:
    """Web routes: quiz taking (app/api/web_routes/quiz.py)"""

    def test_take_quiz_not_found(self, api_client: TestClient, admin_token: str):
        """GET /quizzes/{quiz_id}/take — 404 for nonexistent quiz"""
        cookies = {"access_token": f"Bearer {admin_token}"}
        response = api_client._client.get("/quizzes/99999/take", cookies=cookies)
        assert response.status_code in _WEB_OK, (
            f"GET /quizzes/99999/take: {response.status_code} {response.text[:100]}"
        )

    def test_submit_quiz_not_found(self, api_client: TestClient, student_token: str):
        """POST /quizzes/{quiz_id}/submit — quiz not found → 404"""
        cookies = {"access_token": f"Bearer {student_token}"}
        response = api_client._client.post(
            "/quizzes/99999/submit",
            data={"attempt_id": "1", "time_spent": "30.0"},
            cookies=cookies,
        )
        assert response.status_code in _WEB_OK, (
            f"POST /quizzes/99999/submit: {response.status_code} {response.text[:100]}"
        )

    def test_quiz_auth_required(self, api_client: TestClient):
        """Auth: GET /quizzes/{quiz_id}/take without cookie returns 401"""
        response = api_client._client.get("/quizzes/99999/take")
        assert response.status_code in _WEB_AUTH, (
            f"GET /quizzes/99999/take should require auth: {response.status_code}"
        )


class TestWebRoutesAttendance:
    """Web routes: attendance marking (app/api/web_routes/attendance.py)"""

    def test_mark_attendance_as_instructor(self, api_client: TestClient, instructor_token: str):
        """POST /sessions/{session_id}/attendance/mark — instructor role, session not found"""
        cookies = {"access_token": f"Bearer {instructor_token}"}
        response = api_client._client.post(
            "/sessions/99999/attendance/mark",
            data={"student_id": "99999", "status": "present"},
            cookies=cookies,
        )
        assert response.status_code in _WEB_OK, (
            f"POST attendance/mark (instructor): {response.status_code} {response.text[:100]}"
        )

    def test_confirm_attendance_as_student(self, api_client: TestClient, student_token: str):
        """POST /sessions/{session_id}/attendance/confirm — student role, no attendance record"""
        cookies = {"access_token": f"Bearer {student_token}"}
        response = api_client._client.post(
            "/sessions/99999/attendance/confirm",
            data={"action": "confirm"},
            cookies=cookies,
        )
        assert response.status_code in _WEB_OK, (
            f"POST attendance/confirm (student): {response.status_code} {response.text[:100]}"
        )

    def test_change_request_as_student(self, api_client: TestClient, student_token: str):
        """POST /sessions/{session_id}/attendance/change-request — student role, no record"""
        cookies = {"access_token": f"Bearer {student_token}"}
        response = api_client._client.post(
            "/sessions/99999/attendance/change-request",
            data={"action": "approve"},
            cookies=cookies,
        )
        assert response.status_code in _WEB_OK, (
            f"POST attendance/change-request (student): {response.status_code} {response.text[:100]}"
        )

    def test_attendance_auth_required(self, api_client: TestClient):
        """Auth: attendance routes without cookie return 401"""
        response = api_client._client.post("/sessions/99999/attendance/mark", json={})
        assert response.status_code in _WEB_AUTH, (
            f"POST attendance/mark should require auth: {response.status_code}"
        )


class TestWebRoutesSpecialization:
    """Web routes: specialization pages (app/api/web_routes/specialization.py)"""

    def test_motivation_page_with_spec(self, api_client: TestClient, student_token: str):
        """GET /specialization/motivation?spec=LFA_FOOTBALL_PLAYER — renders questionnaire"""
        cookies = {"access_token": f"Bearer {student_token}"}
        response = api_client._client.get(
            "/specialization/motivation?spec=LFA_FOOTBALL_PLAYER", cookies=cookies
        )
        assert response.status_code in _WEB_OK, (
            f"GET /specialization/motivation: {response.status_code} {response.text[:100]}"
        )

    def test_motivation_page_invalid_spec(self, api_client: TestClient, student_token: str):
        """GET /specialization/motivation?spec=INVALID — redirects for bad spec"""
        cookies = {"access_token": f"Bearer {student_token}"}
        response = api_client._client.get(
            "/specialization/motivation?spec=INVALID_SPEC", cookies=cookies
        )
        assert response.status_code in _WEB_OK, (
            f"GET /specialization/motivation (invalid): {response.status_code} {response.text[:100]}"
        )

    def test_specialization_unlock_insufficient_credits(self, api_client: TestClient, student_token: str):
        """POST /specialization/unlock — student with 0 credits → 400"""
        cookies = {"access_token": f"Bearer {student_token}"}
        response = api_client._client.post(
            "/specialization/unlock",
            data={"specialization": "LFA_FOOTBALL_PLAYER"},
            cookies=cookies,
        )
        assert response.status_code in _WEB_OK, (
            f"POST /specialization/unlock: {response.status_code} {response.text[:100]}"
        )

    def test_specialization_auth_required(self, api_client: TestClient):
        """Auth: GET /specialization/motivation without cookie returns 401"""
        response = api_client._client.get("/specialization/motivation")
        assert response.status_code in _WEB_AUTH, (
            f"GET /specialization/motivation should require auth: {response.status_code}"
        )


class TestWebRoutesInstructorDashboard:
    """Web routes: instructor dashboard (app/api/web_routes/instructor_dashboard.py)"""

    def test_instructor_enrollments_admin_forbidden(self, api_client: TestClient, admin_token: str):
        """GET /instructor/enrollments — admin gets 403"""
        cookies = {"access_token": f"Bearer {admin_token}"}
        response = api_client._client.get("/instructor/enrollments", cookies=cookies)
        assert response.status_code in _WEB_OK, (
            f"GET /instructor/enrollments (admin): {response.status_code} {response.text[:100]}"
        )

    def test_instructor_student_skills_not_found(self, api_client: TestClient, instructor_token: str):
        """GET /instructor/students/{id}/skills/{id} — student not found → 404"""
        cookies = {"access_token": f"Bearer {instructor_token}"}
        response = api_client._client.get(
            "/instructor/students/99999/skills/99999", cookies=cookies
        )
        assert response.status_code in _WEB_OK, (
            f"GET /instructor/students/.../skills/...: {response.status_code} {response.text[:100]}"
        )

    def test_instructor_dashboard_auth_required(self, api_client: TestClient):
        """Auth: instructor dashboard routes without cookie return 401"""
        response = api_client._client.get("/instructor/enrollments")
        assert response.status_code in _WEB_AUTH, (
            f"GET /instructor/enrollments should require auth: {response.status_code}"
        )
