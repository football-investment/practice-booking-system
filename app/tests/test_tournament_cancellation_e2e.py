"""
End-to-End Tournament Cancellation & Refund Tests

This test suite validates the tournament cancellation workflow with automatic credit refunds.

Test Coverage:
1. Admin cancels tournament with APPROVED enrollments → Full refunds processed
2. Admin cancels tournament with PENDING enrollments → Auto-rejected, no refunds
3. Admin cancels tournament with mixed enrollments → Correct refund/reject logic
4. Cannot cancel COMPLETED tournaments
5. Cannot cancel already CANCELLED tournaments
6. Only ADMIN can cancel tournaments
7. Credit balances correctly updated after refund
8. Audit trail created (credit transactions)
9. Tournament status correctly updated

Created: 2026-01-23 (Feature development post-refactoring)
"""

import pytest
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session

from app.models.semester import Semester, SemesterStatus
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.models.user import User, UserRole
from app.models.license import UserLicense, SpecializationType
from app.models.credit_transaction import CreditTransaction, TransactionType
from app.models.tournament_type import TournamentType
from app.models.location import Location
from app.models.campus import Campus


@pytest.mark.tournament
@pytest.mark.integration
@pytest.mark.slow
def test_cancel_tournament_with_approved_enrollments_full_refund(db: Session, admin_user: User, student_users: list[User]):
    """
    Test cancelling a tournament with APPROVED enrollments.

    Expected behavior:
    - All APPROVED enrollments get full refunds
    - Credit balances restored
    - REFUND transactions created
    - Enrollments marked inactive
    - Tournament status → CANCELLED
    """
    # Setup: Create tournament
    tournament = Semester(
        code="TEST-CANCEL-2026",
        name="Test Cancellation Tournament",
        start_date=date.today() + timedelta(days=30),
        end_date=date.today() + timedelta(days=60),
        status=SemesterStatus.READY_FOR_ENROLLMENT,
        tournament_status="READY_FOR_ENROLLMENT",
        enrollment_cost=500,  # 500 credits per enrollment
        specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER.value,
        age_group="YOUTH"
    )
    db.add(tournament)
    db.commit()
    db.refresh(tournament)

    # Setup: Create 3 student licenses and enrollments (APPROVED)
    enrollments = []
    initial_balances = []

    for i, student in enumerate(student_users[:3]):
        # Create license with 1000 credits
        license = UserLicense(
            user_id=student.id,
            specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER,
            credit_balance=1000,
            onboarding_completed=True,
            current_level=1
        )
        db.add(license)
        db.flush()

        # Create APPROVED enrollment (credit already deducted)
        enrollment = SemesterEnrollment(
            user_id=student.id,
            semester_id=tournament.id,
            user_license_id=license.id,
            request_status=EnrollmentStatus.APPROVED,
            is_active=True
        )
        db.add(enrollment)
        db.flush()

        # Simulate credit deduction for enrollment (would have happened during approval)
        license.credit_balance -= tournament.enrollment_cost

        enrollments.append(enrollment)
        initial_balances.append(500)  # 1000 - 500 = 500 after enrollment

    db.commit()

    # Verify initial state
    for i, enrollment in enumerate(enrollments):
        license = db.query(UserLicense).filter(UserLicense.id == enrollment.user_license_id).first()
        assert license.credit_balance == initial_balances[i]
        assert enrollment.request_status == EnrollmentStatus.APPROVED
        assert enrollment.is_active == True

    # ACTION: Admin cancels tournament
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    response = client.post(
        f"/api/v1/tournaments/{tournament.id}/cancel",
        json={
            "reason": "Insufficient instructor availability",
            "notify_participants": False  # Skip notifications for test
        },
        headers={"Authorization": f"Bearer {admin_user.id}"}  # Simplified auth for test
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()

    assert data["message"] == "Tournament cancelled successfully"
    assert data["tournament_id"] == tournament.id
    assert data["tournament_name"] == tournament.name
    assert data["refunds_processed"]["count"] == 3
    assert data["refunds_processed"]["total_credits_refunded"] == 1500  # 3 * 500
    assert len(data["refunds_processed"]["enrollments_refunded"]) == 3
    assert data["enrollments_rejected"]["count"] == 0

    # Verify tournament status
    db.refresh(tournament)
    assert tournament.status == SemesterStatus.CANCELLED
    assert tournament.tournament_status == "CANCELLED"

    # Verify enrollments marked inactive
    for enrollment in enrollments:
        db.refresh(enrollment)
        assert enrollment.is_active == False

    # Verify credit balances restored
    for i, enrollment in enumerate(enrollments):
        license = db.query(UserLicense).filter(UserLicense.id == enrollment.user_license_id).first()
        expected_balance = initial_balances[i] + tournament.enrollment_cost
        assert license.credit_balance == expected_balance  # Should be restored to 1000

    # Verify REFUND transactions created
    refund_transactions = db.query(CreditTransaction).filter(
        CreditTransaction.transaction_type == TransactionType.REFUND.value,
        CreditTransaction.semester_id == tournament.id
    ).all()

    assert len(refund_transactions) == 3
    for tx in refund_transactions:
        assert tx.amount == 500  # Refund amount
        assert "cancellation refund" in tx.description.lower()


@pytest.mark.tournament
@pytest.mark.integration
def test_cancel_tournament_with_pending_enrollments_auto_reject(db: Session, admin_user: User, student_users: list[User]):
    """
    Test cancelling a tournament with PENDING enrollments.

    Expected behavior:
    - PENDING enrollments auto-rejected
    - No refunds (not yet paid)
    - Enrollments marked inactive
    - Tournament status → CANCELLED
    """
    # Setup: Create tournament
    tournament = Semester(
        code="TEST-CANCEL-PENDING-2026",
        name="Test Cancellation with Pending",
        start_date=date.today() + timedelta(days=30),
        end_date=date.today() + timedelta(days=60),
        status=SemesterStatus.READY_FOR_ENROLLMENT,
        tournament_status="READY_FOR_ENROLLMENT",
        enrollment_cost=500,
        specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER.value,
        age_group="YOUTH"
    )
    db.add(tournament)
    db.commit()
    db.refresh(tournament)

    # Setup: Create 2 PENDING enrollments
    enrollments = []

    for student in student_users[:2]:
        license = UserLicense(
            user_id=student.id,
            specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER,
            credit_balance=1000,
            onboarding_completed=True,
            current_level=1
        )
        db.add(license)
        db.flush()

        enrollment = SemesterEnrollment(
            user_id=student.id,
            semester_id=tournament.id,
            user_license_id=license.id,
            request_status=EnrollmentStatus.PENDING,  # Not yet approved/paid
            is_active=True
        )
        db.add(enrollment)
        enrollments.append(enrollment)

    db.commit()

    # ACTION: Admin cancels tournament
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    response = client.post(
        f"/api/v1/tournaments/{tournament.id}/cancel",
        json={
            "reason": "Tournament cancelled due to weather",
            "notify_participants": False
        },
        headers={"Authorization": f"Bearer {admin_user.id}"}
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()

    assert data["refunds_processed"]["count"] == 0  # No refunds for PENDING
    assert data["enrollments_rejected"]["count"] == 2  # 2 PENDING auto-rejected
    assert len(data["enrollments_rejected"]["enrollment_ids"]) == 2

    # Verify enrollments auto-rejected and inactive
    for enrollment in enrollments:
        db.refresh(enrollment)
        assert enrollment.request_status == EnrollmentStatus.REJECTED
        assert enrollment.is_active == False

    # Verify credit balances unchanged (never paid)
    for enrollment in enrollments:
        license = db.query(UserLicense).filter(UserLicense.id == enrollment.user_license_id).first()
        assert license.credit_balance == 1000  # Unchanged

    # Verify no REFUND transactions
    refund_transactions = db.query(CreditTransaction).filter(
        CreditTransaction.transaction_type == TransactionType.REFUND.value,
        CreditTransaction.semester_id == tournament.id
    ).all()

    assert len(refund_transactions) == 0


@pytest.mark.tournament
@pytest.mark.integration
def test_cancel_tournament_mixed_enrollments(db: Session, admin_user: User, student_users: list[User]):
    """
    Test cancelling a tournament with mixed enrollment statuses.

    Expected behavior:
    - APPROVED → Refunded
    - PENDING → Auto-rejected
    - REJECTED/WITHDRAWN → No action
    """
    # Setup: Create tournament
    tournament = Semester(
        code="TEST-CANCEL-MIXED-2026",
        name="Test Cancellation Mixed Status",
        start_date=date.today() + timedelta(days=30),
        end_date=date.today() + timedelta(days=60),
        status=SemesterStatus.READY_FOR_ENROLLMENT,
        tournament_status="READY_FOR_ENROLLMENT",
        enrollment_cost=500,
        specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER.value,
        age_group="YOUTH"
    )
    db.add(tournament)
    db.commit()

    # Setup: Create enrollments with different statuses
    statuses = [
        (EnrollmentStatus.APPROVED, 500),  # Should refund
        (EnrollmentStatus.APPROVED, 500),  # Should refund
        (EnrollmentStatus.PENDING, 1000),  # Should auto-reject, no refund
        (EnrollmentStatus.REJECTED, 1000),  # No action
    ]

    for i, (status, balance) in enumerate(statuses):
        student = student_users[i]

        license = UserLicense(
            user_id=student.id,
            specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER,
            credit_balance=balance,
            onboarding_completed=True,
            current_level=1
        )
        db.add(license)
        db.flush()

        enrollment = SemesterEnrollment(
            user_id=student.id,
            semester_id=tournament.id,
            user_license_id=license.id,
            request_status=status,
            is_active=True
        )
        db.add(enrollment)

    db.commit()

    # ACTION: Cancel tournament
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    response = client.post(
        f"/api/v1/tournaments/{tournament.id}/cancel",
        json={
            "reason": "Venue unavailable",
            "notify_participants": False
        },
        headers={"Authorization": f"Bearer {admin_user.id}"}
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()

    assert data["refunds_processed"]["count"] == 2  # 2 APPROVED
    assert data["refunds_processed"]["total_credits_refunded"] == 1000  # 2 * 500
    assert data["enrollments_rejected"]["count"] == 1  # 1 PENDING


@pytest.mark.tournament
@pytest.mark.integration
def test_cannot_cancel_completed_tournament(db: Session, admin_user: User):
    """Test that COMPLETED tournaments cannot be cancelled"""
    tournament = Semester(
        code="TEST-COMPLETED-2026",
        name="Completed Tournament",
        start_date=date.today() - timedelta(days=60),
        end_date=date.today() - timedelta(days=30),
        status=SemesterStatus.COMPLETED,
        tournament_status="COMPLETED",
        enrollment_cost=500,
        specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER.value,
        age_group="YOUTH"
    )
    db.add(tournament)
    db.commit()

    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    response = client.post(
        f"/api/v1/tournaments/{tournament.id}/cancel",
        json={
            "reason": "Test reason",
            "notify_participants": False
        },
        headers={"Authorization": f"Bearer {admin_user.id}"}
    )

    assert response.status_code == 400
    data = response.json()
    assert "cannot_cancel_completed" in data["detail"]["error"]


@pytest.mark.tournament
@pytest.mark.integration
def test_cannot_cancel_already_cancelled_tournament(db: Session, admin_user: User):
    """Test that already CANCELLED tournaments cannot be cancelled again"""
    tournament = Semester(
        code="TEST-ALREADY-CANCELLED-2026",
        name="Already Cancelled Tournament",
        start_date=date.today() + timedelta(days=30),
        end_date=date.today() + timedelta(days=60),
        status=SemesterStatus.CANCELLED,
        tournament_status="CANCELLED",
        enrollment_cost=500,
        specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER.value,
        age_group="YOUTH"
    )
    db.add(tournament)
    db.commit()

    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    response = client.post(
        f"/api/v1/tournaments/{tournament.id}/cancel",
        json={
            "reason": "Test reason",
            "notify_participants": False
        },
        headers={"Authorization": f"Bearer {admin_user.id}"}
    )

    assert response.status_code == 400
    data = response.json()
    assert "already_cancelled" in data["detail"]["error"]


@pytest.mark.tournament
@pytest.mark.integration
def test_only_admin_can_cancel_tournament(db: Session, student_users: list[User]):
    """Test that only ADMIN role can cancel tournaments"""
    tournament = Semester(
        code="TEST-ADMIN-ONLY-2026",
        name="Admin Only Test",
        start_date=date.today() + timedelta(days=30),
        end_date=date.today() + timedelta(days=60),
        status=SemesterStatus.READY_FOR_ENROLLMENT,
        tournament_status="READY_FOR_ENROLLMENT",
        enrollment_cost=500,
        specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER.value,
        age_group="YOUTH"
    )
    db.add(tournament)
    db.commit()

    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # Try to cancel as STUDENT (should fail)
    student = student_users[0]
    response = client.post(
        f"/api/v1/tournaments/{tournament.id}/cancel",
        json={
            "reason": "Student trying to cancel",
            "notify_participants": False
        },
        headers={"Authorization": f"Bearer {student.id}"}
    )

    assert response.status_code == 403
    data = response.json()
    assert "authorization_error" in data["detail"]["error"]
    assert "Only admins" in data["detail"]["message"]
