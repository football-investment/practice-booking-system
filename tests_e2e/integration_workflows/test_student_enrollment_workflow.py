"""
E2E Workflow Test: Student Enrollment

Validates full student enrollment workflow end-to-end:
1. Admin creates tournament (direct DB, no OPS dependency)
2. Tournament transitions through lifecycle states
3. Student enrolls (credit deduction, enrollment record creation)
4. Enrollment status validation

Architecture:
- Self-contained (no external dependencies)
- Deterministic (explicit tournament creation)
- CI-safe (no @lfa-seed.hu users required)
- Zero OPS scenario dependency
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import Dict
from datetime import datetime, timezone, timedelta


def test_student_enrollment_full_workflow(
    e2e_client: TestClient,
    e2e_db: Session,
    e2e_admin: Dict,
    e2e_student: Dict,
    e2e_instructor: Dict,
    e2e_tournament_types,
    e2e_campus
):
    """
    E2E Workflow: Student enrollment with credit deduction.

    Workflow steps:
    1. Admin creates tournament (direct DB - no OPS)
    2. Admin assigns instructor
    3. Instructor accepts assignment
    4. Tournament opens for enrollment
    5. Student enrolls (250 credits deducted)
    6. Verify enrollment status & credit balance

    Expected:
    - Student credit balance: 1000 → 750 (250 deducted)
    - Enrollment status: APPROVED
    - Enrollment is_active: True
    """
    from app.models.semester import Semester, SemesterStatus
    from app.models.tournament_configuration import TournamentConfiguration

    # ========================================================================
    # Step 1: Create tournament directly (bypass OPS scenario)
    # ========================================================================

    # Get knockout tournament type
    knockout_type = next(
        (tt for tt in e2e_tournament_types if tt.code == "knockout"),
        None
    )
    assert knockout_type is not None, "Knockout tournament type should exist"

    # Create tournament (Semester) - basic fields only
    tournament = Semester(
        name="E2E Test Tournament",
        code=f"E2E-TEST-{datetime.now().timestamp()}",
        start_date=(datetime.now(timezone.utc) + timedelta(days=7)).date(),
        end_date=(datetime.now(timezone.utc) + timedelta(days=14)).date(),
        age_group="PRO",
        status=SemesterStatus.DRAFT,  # Start in DRAFT
        tournament_status="DRAFT",  # Legacy string field
        enrollment_cost=250,
        campus_id=e2e_campus.id,  # Required for enrollment
        is_active=True
    )
    e2e_db.add(tournament)
    e2e_db.commit()
    e2e_db.refresh(tournament)

    # Create tournament configuration (P2 refactoring - separate table)
    tournament_config = TournamentConfiguration(
        semester_id=tournament.id,
        tournament_type_id=knockout_type.id,
        max_players=8,
        participant_type="INDIVIDUAL",
        is_multi_day=False,
        parallel_fields=1,
        scoring_type="HEAD_TO_HEAD",  # Knockout is HEAD_TO_HEAD format
        number_of_rounds=1
    )
    e2e_db.add(tournament_config)
    e2e_db.commit()
    e2e_db.refresh(tournament_config)

    tournament_id = tournament.id

    # Verify tournament created
    assert tournament_id is not None, "Tournament should be created"
    assert tournament.status == SemesterStatus.DRAFT, "Tournament should start in DRAFT"

    # ========================================================================
    # Step 1.5: Transition tournament to SEEKING_INSTRUCTOR
    # ========================================================================

    # Lifecycle rule: DRAFT → SEEKING_INSTRUCTOR transition (admin ready to find instructor)
    tournament.status = SemesterStatus.SEEKING_INSTRUCTOR
    tournament.tournament_status = "SEEKING_INSTRUCTOR"
    e2e_db.commit()
    e2e_db.refresh(tournament)

    assert tournament.status == SemesterStatus.SEEKING_INSTRUCTOR, (
        "Tournament should transition to SEEKING_INSTRUCTOR"
    )

    # ========================================================================
    # Step 2: Admin assigns instructor
    # ========================================================================

    admin_headers = {"Authorization": f"Bearer {e2e_admin['token']}"}

    assign_payload = {
        "instructor_id": e2e_instructor["user_id"]
    }

    response = e2e_client.post(
        f"/api/v1/tournaments/{tournament_id}/assign-instructor",
        json=assign_payload,
        headers=admin_headers
    )

    assert response.status_code in [200, 201], (
        f"Instructor assignment failed: {response.status_code} {response.text}"
    )

    # ========================================================================
    # Step 3: Instructor accepts assignment
    # ========================================================================

    instructor_headers = {"Authorization": f"Bearer {e2e_instructor['token']}"}

    response = e2e_client.post(
        f"/api/v1/tournaments/{tournament_id}/instructor/accept",
        json={},
        headers=instructor_headers
    )

    assert response.status_code in [200, 201], (
        f"Instructor acceptance failed: {response.status_code} {response.text}"
    )

    # ========================================================================
    # Step 4: Admin opens enrollment
    # ========================================================================

    # Transition INSTRUCTOR_CONFIRMED → ENROLLMENT_OPEN
    status_payload = {"new_status": "ENROLLMENT_OPEN"}

    response = e2e_client.patch(
        f"/api/v1/tournaments/{tournament_id}/status",
        json=status_payload,
        headers=admin_headers
    )

    assert response.status_code == 200, (
        f"Status transition to ENROLLMENT_OPEN failed: {response.status_code} {response.text}"
    )

    # ========================================================================
    # Step 5: Student enrolls
    # ========================================================================

    student_headers = {"Authorization": f"Bearer {e2e_student['token']}"}

    # Check initial balance
    initial_balance = e2e_student["credit_balance"]
    assert initial_balance == 1000, "Student should start with 1000 credits"

    # Enroll
    response = e2e_client.post(
        f"/api/v1/tournaments/{tournament_id}/enroll",
        json={},
        headers=student_headers
    )

    assert response.status_code in [200, 201], (
        f"Enrollment failed: {response.status_code} {response.text}"
    )

    enrollment_result = response.json()

    # ========================================================================
    # Step 6: Verify enrollment & credit deduction
    # ========================================================================

    # Verify enrollment success
    assert enrollment_result.get("success") is True, (
        "Enrollment should succeed"
    )

    # Verify credit deduction in response
    assert enrollment_result.get("credits_remaining") == 750, (
        f"Credit balance should be 750 (actual: {enrollment_result.get('credits_remaining')})"
    )

    # Verify enrollment object exists
    enrollment_obj = enrollment_result.get("enrollment")
    assert enrollment_obj is not None, "Enrollment object should be present in response"

    # Verify enrollment is active
    assert enrollment_obj.get("is_active") is True, (
        "Enrollment should be active"
    )

    # Verify credit deduction
    from app.models.user import User
    student_after = e2e_db.query(User).filter(
        User.id == e2e_student["user_id"]
    ).first()

    expected_balance = initial_balance - 250  # 1000 - 250 = 750
    assert student_after.credit_balance == expected_balance, (
        f"Credit balance should be {expected_balance} "
        f"(actual: {student_after.credit_balance})"
    )

    # ========================================================================
    # Success: Full workflow validated
    # ========================================================================

    print(f"\n✅ E2E Student Enrollment Workflow PASSED")
    print(f"   Tournament: {tournament_id} ({tournament.code})")
    print(f"   Student: {e2e_student['email']}")
    print(f"   Credits: {initial_balance} → {student_after.credit_balance}")
    print(f"   Enrollment: {enrollment_result.get('request_status')}")
    print(f"   Architecture: Self-contained (zero OPS dependency)")
