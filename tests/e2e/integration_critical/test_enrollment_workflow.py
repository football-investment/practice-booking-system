"""
Enrollment Workflow E2E — Integration Critical (BLOCKING CI gate)

Sprint 38 — validates tournament enrollment flow missing from BLOCKING Python gates.

Tests:
  1. test_student_tournament_enrollment_lifecycle
     — Student enrolls → auto-approved → appears in admin enrollment list
  2. test_duplicate_enrollment_rejected
     — Student enrolls twice → second attempt rejected 400/409
  3. test_admin_batch_enrollment
     — Admin batch-enrolls students → all appear in enrolled list

Tournament fixture: created directly in DB (same pattern as booking_lifecycle)
with tournament_status="IN_PROGRESS" to allow enrollment.

Cleanup: Delete semester + users after each test (function-scoped fixtures).
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import pytest
import requests


# ---------------------------------------------------------------------------
# Auth header helper
# ---------------------------------------------------------------------------

def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Tournament fixture (direct DB creation — avoids API schema surprises)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def enrollment_tournament(api_url: str, admin_token: str, test_campus_ids: List[int]):
    """
    CREATE: 1 Tournament (Semester) in DB with tournament_status=IN_PROGRESS.
    CLEANUP: Cancel tournament via API after test completes.

    Returns:
        {"tournament_id": int}
    """
    from app.database import get_db
    from app.models.semester import Semester

    ts = int(time.time() * 1000)
    campus_id = test_campus_ids[0]
    now = datetime.now(timezone.utc)

    db = next(get_db())
    tournament_id: Optional[int] = None

    try:
        semester = Semester(
            code=f"ENROLL_TEST_{ts}",
            name=f"Enrollment Test Tournament {ts}",
            start_date=now.date(),
            end_date=(now + timedelta(days=180)).date(),
            tournament_status="IN_PROGRESS",
            enrollment_cost=0,
            age_group="PRO",
            campus_id=campus_id,
        )
        db.add(semester)
        db.commit()
        db.refresh(semester)
        tournament_id = semester.id
        yield {"tournament_id": tournament_id}

    finally:
        db.close()

    # CLEANUP: Cancel tournament via API (triggers enrollment cleanup)
    if tournament_id:
        try:
            requests.post(
                f"{api_url}/api/v1/tournaments/{tournament_id}/cancel",
                headers=_auth(admin_token),
                json={"reason": "E2E test cleanup"}
            )
        except Exception as e:
            print(f"⚠️  Cleanup warning: failed to cancel tournament {tournament_id}: {e}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEnrollmentWorkflow:

    # -----------------------------------------------------------------------
    # 1. Student enrollment lifecycle — auto-approved
    # -----------------------------------------------------------------------

    def test_student_tournament_enrollment_lifecycle(
        self,
        api_url: str,
        admin_token: str,
        test_students: List[Dict],
        enrollment_tournament: Dict,
    ):
        """
        Student enrolls → auto-approved → appears in admin enrollment list.
        """
        tid = enrollment_tournament["tournament_id"]
        student = test_students[0]

        # Student enrolls
        enroll_resp = requests.post(
            f"{api_url}/api/v1/tournaments/{tid}/enroll",
            headers=_auth(student["token"])
        )
        assert enroll_resp.status_code in [200, 201], (
            f"Enrollment failed: {enroll_resp.status_code} — {enroll_resp.text}"
        )

        enroll_data = enroll_resp.json()
        # Tournament enrollment is auto-approved
        # Response shape: {"enrollment": {"request_status": ...}, ...}
        enroll_status = enroll_data.get("enrollment", {}).get("request_status") or enroll_data.get("request_status")
        assert enroll_status in ["APPROVED", "approved", "AUTO_APPROVED"], (
            f"Expected auto-approved, got: {enroll_data}"
        )

        # Admin lists enrollments — student must appear
        # Tournament enrollment uses SemesterEnrollment (semester_id=tournament_id)
        list_resp = requests.get(
            f"{api_url}/api/v1/semester-enrollments/semesters/{tid}/enrollments",
            headers=_auth(admin_token)
        )
        assert list_resp.status_code in [200, 201], (
            f"Admin enrollment list failed: {list_resp.text}"
        )

        enrollments = list_resp.json()
        # Handle both list and dict-with-items responses
        if isinstance(enrollments, dict):
            items = enrollments.get("items", enrollments.get("enrollments", []))
        else:
            items = enrollments

        student_ids = [e.get("user_id") or e.get("student_id") for e in items]
        assert student["id"] in student_ids, (
            f"Student {student['id']} not found in enrollment list: {student_ids}"
        )

    # -----------------------------------------------------------------------
    # 2. Duplicate enrollment rejected
    # -----------------------------------------------------------------------

    def test_duplicate_enrollment_rejected(
        self,
        api_url: str,
        test_students: List[Dict],
        enrollment_tournament: Dict,
    ):
        """
        Second enrollment attempt by same student must be rejected (400/409).
        """
        tid = enrollment_tournament["tournament_id"]
        student = test_students[1]

        # First enrollment
        first_resp = requests.post(
            f"{api_url}/api/v1/tournaments/{tid}/enroll",
            headers=_auth(student["token"])
        )
        assert first_resp.status_code in [200, 201], (
            f"First enrollment failed: {first_resp.text}"
        )

        # Second enrollment — must fail
        second_resp = requests.post(
            f"{api_url}/api/v1/tournaments/{tid}/enroll",
            headers=_auth(student["token"])
        )
        assert second_resp.status_code in [400, 409], (
            f"Expected 400/409 for duplicate enrollment, got {second_resp.status_code}: {second_resp.text}"
        )

    # -----------------------------------------------------------------------
    # 3. Admin batch enrollment
    # -----------------------------------------------------------------------

    def test_admin_batch_enrollment(
        self,
        api_url: str,
        admin_token: str,
        test_students: List[Dict],
        enrollment_tournament: Dict,
    ):
        """
        Admin batch-enrolls 2 students → both appear in enrolled list.
        """
        tid = enrollment_tournament["tournament_id"]
        # Use students[2] and [3] (not used in previous tests)
        student_a = test_students[2]
        student_b = test_students[3]

        batch_resp = requests.post(
            f"{api_url}/api/v1/tournaments/{tid}/admin/batch-enroll",
            headers=_auth(admin_token),
            json={"player_ids": [student_a["id"], student_b["id"]]}
        )
        assert batch_resp.status_code in [200, 201], (
            f"Batch enroll failed: {batch_resp.status_code} — {batch_resp.text}"
        )

        # Verify both appear in enrollment list
        list_resp = requests.get(
            f"{api_url}/api/v1/semester-enrollments/semesters/{tid}/enrollments",
            headers=_auth(admin_token)
        )
        assert list_resp.status_code in [200, 201]

        enrollments = list_resp.json()
        if isinstance(enrollments, dict):
            items = enrollments.get("items", enrollments.get("enrollments", []))
        else:
            items = enrollments

        enrolled_ids = {e.get("user_id") or e.get("student_id") for e in items}
        assert student_a["id"] in enrolled_ids, f"Student A {student_a['id']} not enrolled"
        assert student_b["id"] in enrolled_ids, f"Student B {student_b['id']} not enrolled"
