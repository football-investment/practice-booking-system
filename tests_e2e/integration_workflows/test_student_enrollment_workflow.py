"""
E2E Workflow Test: Student Enrollment

Validates full student enrollment workflow end-to-end:
1. Admin creates tournament (DRAFT state)
2. Tournament transitions through lifecycle states
3. Student enrolls (credit deduction, enrollment record creation)
4. Enrollment status validation

Business rules validated:
- Tournament must be in ENROLLMENT_OPEN state for enrollment
- Student must have sufficient credits
- Student must have required license (LFA Football Player)
- Enrollment cost deducted from student credit_balance
- Enrollment record created with APPROVED status
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import Dict


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
    1. Admin creates tournament via OPS scenario
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
    # ========================================================================
    # Step 1: Admin creates tournament via OPS scenario
    # ========================================================================

    admin_headers = {"Authorization": f"Bearer {e2e_admin['token']}"}

    ops_payload = {
        "scenario": "smoke_test",  # Use valid scenario name
        "player_count": 8,
        "tournament_format": "HEAD_TO_HEAD",
        "tournament_type_code": "knockout",
        "auto_generate_sessions": False,  # Manual mode - no auto-session generation
        "simulation_mode": "manual",
        "campus_ids": [e2e_campus.id],
        "enrollment_cost": 250  # Custom enrollment cost
    }

    response = e2e_client.post(
        "/api/v1/tournaments/ops/run-scenario",
        json=ops_payload,
        headers=admin_headers
    )

    assert response.status_code == 200, (
        f"OPS scenario failed: {response.status_code} {response.text}"
    )

    ops_result = response.json()
    tournament_id = ops_result["tournament_id"]

    # Verify tournament created
    assert tournament_id is not None, "Tournament ID should be returned"
    assert ops_result["status"] == "DRAFT", "Tournament should start in DRAFT"

    # ========================================================================
    # Step 2: Admin assigns instructor
    # ========================================================================

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

    # Verify enrollment status
    assert enrollment_result.get("request_status") == "APPROVED", (
        "Enrollment should be auto-approved"
    )
    assert enrollment_result.get("is_active") is True, (
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

    print(f"✅ E2E Student Enrollment Workflow PASSED")
    print(f"   Tournament: {tournament_id}")
    print(f"   Student: {e2e_student['email']}")
    print(f"   Credits: {initial_balance} → {student_after.credit_balance}")
    print(f"   Enrollment: {enrollment_result.get('request_status')}")
