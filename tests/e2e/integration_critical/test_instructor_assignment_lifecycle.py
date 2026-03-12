"""
Instructor Assignment Lifecycle E2E — Integration Critical (BLOCKING CI gate)

Sprint 40 — validates the Cycle 2 instructor assignment flow (lifecycle_instructor.py).
This is distinct from the application-based flow in instructor_assignment.py.

Endpoints under test:
  POST /api/v1/tournaments/{id}/assign-instructor   — admin assigns instructor
  POST /api/v1/tournaments/{id}/instructor/accept   — assigned instructor accepts
  POST /api/v1/tournaments/{id}/instructor/decline  — assigned instructor declines

Tests:
  1. test_assign_instructor_accept_flow
     Admin assigns → status=PENDING_INSTRUCTOR_ACCEPTANCE →
     Instructor accepts → status=INSTRUCTOR_CONFIRMED

  2. test_assign_instructor_decline_flow
     Admin assigns → instructor declines →
     status=SEEKING_INSTRUCTOR (reset)

  3. test_non_admin_cannot_assign
     Instructor attempts POST /assign-instructor → 403

  4. test_wrong_instructor_cannot_accept
     Admin assigns instructor A → instructor B tries accept → 403

Fixture design:
  - `assignment_tournament` is function-scoped: each test gets a fresh tournament
    in SEEKING_INSTRUCTOR status (instructor assignment resets status — tests are destructive)
  - `test_instructor` / `test_instructor_b` from conftest (function-scoped)
  - Cleanup: cancel tournament via API after each test

Sprint 40 fix context: production code in lifecycle_instructor.py previously
referenced `UserRole.GRANDMASTER` (non-existent) — fixed to `UserRole.INSTRUCTOR`.
This gate ensures the fixed endpoint actually works end-to-end.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import pytest
import requests

from tests.e2e.integration_critical.conftest import (
    get_admin_token,
    create_test_user,
    delete_test_user,
)


# ---------------------------------------------------------------------------
# Auth header helper
# ---------------------------------------------------------------------------

def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Tournament fixture (direct DB creation — same pattern as enrollment_workflow)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def assignment_tournament(api_url: str, admin_token: str):
    """
    CREATE: 1 Tournament (Semester) in SEEKING_INSTRUCTOR status.
    CLEANUP: Cancel tournament via API after test.

    function-scoped because tests mutate tournament status
    (assign → accept/decline changes status each time).

    Returns:
        {"tournament_id": int}
    """
    from app.database import get_db
    from app.models.semester import Semester

    ts = int(time.time() * 1000)
    now = datetime.now(timezone.utc)

    db = next(get_db())
    tournament_id: Optional[int] = None

    try:
        semester = Semester(
            code=f"INST_ASSIGN_TEST_{ts}",
            name=f"Instructor Assignment Test {ts}",
            start_date=now.date(),
            end_date=(now + timedelta(days=90)).date(),
            tournament_status="SEEKING_INSTRUCTOR",
            enrollment_cost=0,
            age_group="PRO",
        )
        db.add(semester)
        db.commit()
        db.refresh(semester)
        tournament_id = semester.id
        yield {"tournament_id": tournament_id}

    finally:
        db.close()

    # CLEANUP: attempt to cancel via API (best-effort)
    if tournament_id:
        try:
            admin_tok = get_admin_token(api_url)
            requests.post(
                f"{api_url}/api/v1/tournaments/{tournament_id}/cancel",
                headers=_auth(admin_tok),
                json={"reason": "E2E test cleanup — instructor assignment lifecycle"}
            )
        except Exception as e:
            print(f"⚠️  Cleanup warning: could not cancel tournament {tournament_id}: {e}")


@pytest.fixture(scope="function")
def test_instructor_b(api_url: str, admin_token: str) -> Dict:
    """
    CREATE + CLEANUP: A second instructor for 'wrong user' tests.
    """
    ts = int(time.time() * 1000)
    instructor = create_test_user(api_url, admin_token, "INSTRUCTOR", ts + 1)

    yield instructor

    try:
        fresh_admin_token = get_admin_token(api_url)
        delete_test_user(api_url, fresh_admin_token, instructor["id"])
    except Exception as e:
        print(f"⚠️  Cleanup warning: Failed to delete instructor_b {instructor['id']}: {e}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestInstructorAssignmentLifecycle:

    # -----------------------------------------------------------------------
    # 1. Full accept flow
    # -----------------------------------------------------------------------

    def test_assign_instructor_accept_flow(
        self,
        api_url: str,
        admin_token: str,
        assignment_tournament: Dict,
        test_instructor: Dict,
    ):
        """
        Full Cycle 2 accept flow:
          Admin assigns → PENDING_INSTRUCTOR_ACCEPTANCE →
          Instructor accepts → INSTRUCTOR_CONFIRMED
        """
        tid = assignment_tournament["tournament_id"]
        instructor = test_instructor

        # Admin assigns instructor
        assign_resp = requests.post(
            f"{api_url}/api/v1/tournaments/{tid}/assign-instructor",
            headers=_auth(admin_token),
            json={"instructor_id": instructor["id"], "message": "Please confirm your assignment"}
        )
        assert assign_resp.status_code == 200, (
            f"assign-instructor failed: {assign_resp.status_code} — {assign_resp.text}"
        )
        assign_data = assign_resp.json()
        assert assign_data["status"] == "PENDING_INSTRUCTOR_ACCEPTANCE", (
            f"Expected PENDING_INSTRUCTOR_ACCEPTANCE, got: {assign_data}"
        )
        assert assign_data["action"] == "assigned"
        assert assign_data["instructor_id"] == instructor["id"]

        # Instructor accepts assignment
        accept_resp = requests.post(
            f"{api_url}/api/v1/tournaments/{tid}/instructor/accept",
            headers=_auth(instructor["token"]),
            json={"message": "Happy to teach this tournament"}
        )
        assert accept_resp.status_code == 200, (
            f"instructor/accept failed: {accept_resp.status_code} — {accept_resp.text}"
        )
        accept_data = accept_resp.json()
        assert accept_data["status"] == "INSTRUCTOR_CONFIRMED", (
            f"Expected INSTRUCTOR_CONFIRMED, got: {accept_data}"
        )
        assert accept_data["action"] == "accepted"

    # -----------------------------------------------------------------------
    # 2. Decline flow
    # -----------------------------------------------------------------------

    def test_assign_instructor_decline_flow(
        self,
        api_url: str,
        admin_token: str,
        assignment_tournament: Dict,
        test_instructor: Dict,
    ):
        """
        Admin assigns → Instructor declines → status resets to SEEKING_INSTRUCTOR.
        """
        tid = assignment_tournament["tournament_id"]
        instructor = test_instructor

        # Admin assigns instructor
        assign_resp = requests.post(
            f"{api_url}/api/v1/tournaments/{tid}/assign-instructor",
            headers=_auth(admin_token),
            json={"instructor_id": instructor["id"]}
        )
        assert assign_resp.status_code == 200, (
            f"assign-instructor failed: {assign_resp.status_code} — {assign_resp.text}"
        )
        assert assign_resp.json()["status"] == "PENDING_INSTRUCTOR_ACCEPTANCE"

        # Instructor declines
        decline_resp = requests.post(
            f"{api_url}/api/v1/tournaments/{tid}/instructor/decline",
            headers=_auth(instructor["token"]),
            json={"message": "Schedule conflict"}
        )
        assert decline_resp.status_code == 200, (
            f"instructor/decline failed: {decline_resp.status_code} — {decline_resp.text}"
        )
        decline_data = decline_resp.json()
        assert decline_data["status"] == "SEEKING_INSTRUCTOR", (
            f"Expected SEEKING_INSTRUCTOR after decline, got: {decline_data}"
        )
        assert decline_data["action"] == "declined"

    # -----------------------------------------------------------------------
    # 3. Non-admin cannot assign instructor
    # -----------------------------------------------------------------------

    def test_non_admin_cannot_assign(
        self,
        api_url: str,
        assignment_tournament: Dict,
        test_instructor: Dict,
    ):
        """
        An instructor (non-admin) trying to assign another instructor → 403 Forbidden.
        """
        tid = assignment_tournament["tournament_id"]
        instructor = test_instructor

        assign_resp = requests.post(
            f"{api_url}/api/v1/tournaments/{tid}/assign-instructor",
            headers=_auth(instructor["token"]),  # instructor token, not admin
            json={"instructor_id": instructor["id"]}
        )
        assert assign_resp.status_code == 403, (
            f"Expected 403 for non-admin assign attempt, got {assign_resp.status_code}: {assign_resp.text}"
        )

    # -----------------------------------------------------------------------
    # 4. Wrong instructor cannot accept
    # -----------------------------------------------------------------------

    def test_wrong_instructor_cannot_accept(
        self,
        api_url: str,
        admin_token: str,
        assignment_tournament: Dict,
        test_instructor: Dict,
        test_instructor_b: Dict,
    ):
        """
        Admin assigns instructor A → instructor B tries to accept → 403.
        """
        tid = assignment_tournament["tournament_id"]
        instructor_a = test_instructor
        instructor_b = test_instructor_b

        # Admin assigns instructor A
        assign_resp = requests.post(
            f"{api_url}/api/v1/tournaments/{tid}/assign-instructor",
            headers=_auth(admin_token),
            json={"instructor_id": instructor_a["id"]}
        )
        assert assign_resp.status_code == 200, (
            f"assign-instructor failed: {assign_resp.status_code} — {assign_resp.text}"
        )

        # Instructor B (different user) tries to accept
        accept_resp = requests.post(
            f"{api_url}/api/v1/tournaments/{tid}/instructor/accept",
            headers=_auth(instructor_b["token"]),
            json={"message": "I'll take it!"}
        )
        assert accept_resp.status_code == 403, (
            f"Expected 403 for wrong instructor accept, got {accept_resp.status_code}: {accept_resp.text}"
        )
