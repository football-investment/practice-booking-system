"""
Refund Workflow E2E Tests - Revenue Safety Layer

Full business value chain validation for refund operations:
1. Student enrolls in tournament (credit deduction)
2. Student unenrolls from tournament (credit refund)
3. Credit refund verified (50% policy)
4. Audit trail validated (enrollment_refunded event)
5. Idempotency validated (double cancel prevention)
6. Invalid state rejection (refund after completion)

Marker: @pytest.mark.e2e
Purpose: Guarantee bidirectional financial integrity (enrollment + refund)
"""

import pytest
from datetime import date, timedelta, datetime, timezone
from sqlalchemy.orm import Session as DBSession

from app.models.user import User, UserRole
from app.models.semester import Semester, SemesterStatus
from app.models.license import UserLicense
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.models.credit_transaction import CreditTransaction
from app.models.audit_log import AuditLog, AuditAction
from app.core.security import get_password_hash
from app.database import get_db


@pytest.fixture
def refund_student(db_session: DBSession):
    """Create student with credits for refund flow"""
    user = User(
        name="Refund Test Student",
        email="refund.student@test.com",
        password_hash=get_password_hash("student123"),
        role=UserRole.STUDENT,
        is_active=True,
        credit_balance=1000,  # Sufficient for enrollment
        date_of_birth=date(2000, 1, 15)  # PRO category
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create LFA_FOOTBALL_PLAYER license (required for enrollment)
    license = UserLicense(
        user_id=user.id,
        specialization_type="LFA_FOOTBALL_PLAYER",
        is_active=True,
        started_at=datetime.now(timezone.utc)
    )
    db_session.add(license)
    db_session.commit()

    return user


@pytest.fixture
def refund_student_token(client, refund_student):
    """Get access token for refund student"""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "refund.student@test.com", "password": "student123"}
    )
    return response.json()["access_token"]


@pytest.fixture
def refund_tournament(db_session: DBSession):
    """Create tournament ready for enrollment and refund"""
    tournament = Semester(
        code="REFUND-TEST-2026",
        name="Refund Test Tournament 2026",
        specialization_type="LFA_FOOTBALL_PLAYER",
        age_group="PRO",
        start_date=date.today() + timedelta(days=30),
        end_date=date.today() + timedelta(days=60),
        status=SemesterStatus.READY_FOR_ENROLLMENT,
        tournament_status="ENROLLMENT_OPEN",
        enrollment_cost=500,
        is_active=True
    )
    db_session.add(tournament)
    db_session.commit()
    db_session.refresh(tournament)
    return tournament


@pytest.mark.e2e
class TestRefundWorkflowE2E:
    """E2E test suite for refund workflow - revenue safety layer"""

    def test_full_refund_workflow_happy_path(
        self,
        client,
        db_session,
        refund_student,
        refund_student_token,
        refund_tournament
    ):
        """
        E2E Test: Full refund workflow - happy path

        Business Value: Validate bidirectional financial integrity
        (enrollment deduction + refund credit).

        Flow:
        1. Student enrolls in tournament (500 credits deducted)
        2. Verify balance: 1000 → 500
        3. Student unenrolls from tournament
        4. Verify refund: 50% = 250 credits returned
        5. Verify final balance: 500 + 250 = 750
        6. Verify enrollment status: WITHDRAWN
        7. Verify audit trail: enrollment_refunded event
        """

        initial_balance = refund_student.credit_balance  # 1000
        enrollment_cost = refund_tournament.enrollment_cost  # 500

        # ============================================================
        # STEP 1: Student enrolls in tournament
        # ============================================================
        response = client.post(
            f"/api/v1/tournaments/{refund_tournament.id}/enroll",
            headers={"Authorization": f"Bearer {refund_student_token}"}
        )

        assert response.status_code == 200
        enrollment_data = response.json()
        assert enrollment_data["success"] is True

        db_session.refresh(refund_student)
        balance_after_enrollment = refund_student.credit_balance
        assert balance_after_enrollment == initial_balance - enrollment_cost

        print(f"✅ Step 1: Enrolled (1000 → {balance_after_enrollment} credits)")

        # ============================================================
        # STEP 2: Student unenrolls from tournament (refund)
        # ============================================================
        response = client.delete(
            f"/api/v1/tournaments/{refund_tournament.id}/unenroll",
            headers={"Authorization": f"Bearer {refund_student_token}"}
        )

        assert response.status_code == 200
        refund_data = response.json()
        assert refund_data["success"] is True

        # Verify refund amount (50% policy)
        expected_refund = enrollment_cost // 2  # 250 credits
        expected_penalty = enrollment_cost - expected_refund  # 250 credits
        assert refund_data["refund_amount"] == expected_refund
        assert refund_data["penalty_amount"] == expected_penalty

        print(f"✅ Step 2: Unenrolled (refund: {expected_refund}, penalty: {expected_penalty})")

        # ============================================================
        # STEP 3: Verify final balance
        # ============================================================
        db_session.refresh(refund_student)
        expected_final_balance = balance_after_enrollment + expected_refund
        assert refund_student.credit_balance == expected_final_balance

        print(f"✅ Step 3: Final balance: {refund_student.credit_balance} (expected: {expected_final_balance})")

        # ============================================================
        # STEP 4: Verify enrollment status
        # ============================================================
        enrollment = db_session.query(SemesterEnrollment).filter(
            SemesterEnrollment.user_id == refund_student.id,
            SemesterEnrollment.semester_id == refund_tournament.id
        ).first()

        assert enrollment is not None
        assert enrollment.request_status == EnrollmentStatus.WITHDRAWN
        assert enrollment.is_active is False

        print(f"✅ Step 4: Enrollment status: WITHDRAWN, is_active: False")

        # ============================================================
        # STEP 5: Verify credit transactions
        # ============================================================
        # Should have 2 transactions: enrollment deduction + refund
        transactions = db_session.query(CreditTransaction).filter(
            CreditTransaction.user_license_id == refund_student.licenses[0].id
        ).order_by(CreditTransaction.id).all()

        assert len(transactions) == 2

        # Transaction 1: Enrollment deduction
        assert transactions[0].transaction_type == "TOURNAMENT_ENROLLMENT"
        assert transactions[0].amount == -enrollment_cost

        # Transaction 2: Refund
        assert transactions[1].transaction_type == "TOURNAMENT_UNENROLL_REFUND"
        assert transactions[1].amount == expected_refund

        print(f"✅ Step 5: Credit transactions: 2 (enrollment + refund)")

        # ============================================================
        # STEP 6: Verify audit trail
        # ============================================================
        # Find enrollment_refunded event
        all_audits = db_session.query(AuditLog).filter(
            AuditLog.user_id == refund_student.id
        ).order_by(AuditLog.timestamp.desc()).all()

        refund_audit = None
        for audit in all_audits:
            if audit.details and audit.details.get("event") == "enrollment_refunded":
                refund_audit = audit
                break

        assert refund_audit is not None, "Refund audit log not found"

        audit_details = refund_audit.details
        assert audit_details.get("refunded_amount") == expected_refund
        assert audit_details.get("penalty_amount") == expected_penalty
        assert audit_details.get("balance_after") == expected_final_balance
        assert audit_details.get("original_enrollment_id") == enrollment.id

        print(f"✅ Step 6: Audit trail validated (enrollment_refunded event)")

        # ============================================================
        # E2E FLOW COMPLETE
        # ============================================================
        print("\n" + "="*60)
        print("🎉 REFUND E2E COMPLETE - Bidirectional Financial Integrity")
        print("="*60)
        print(f"Initial balance: {initial_balance}")
        print(f"After enrollment: {balance_after_enrollment} (-{enrollment_cost})")
        print(f"After refund: {refund_student.credit_balance} (+{expected_refund})")
        print(f"Refund policy: 50% (penalty: {expected_penalty})")
        print(f"Enrollment status: WITHDRAWN")
        print(f"Credit transactions: {len(transactions)}")
        print(f"Audit trail: ✅ COMPLETE")
        print("="*60)

    def test_double_cancel_idempotency(
        self,
        client,
        db_session,
        refund_student,
        refund_student_token,
        refund_tournament
    ):
        """
        E2E Test: Double cancel idempotency

        Business Value: Prevent double refunds (revenue protection).

        Flow:
        1. Student enrolls in tournament
        2. Student unenrolls successfully (refund processed)
        3. Attempt second unenroll → REJECTED (no active enrollment)
        4. Verify: Only ONE refund transaction exists
        5. Verify: Balance correct (no double refund)
        """

        initial_balance = refund_student.credit_balance  # 1000

        # ============================================================
        # SETUP: Enroll in tournament
        # ============================================================
        response = client.post(
            f"/api/v1/tournaments/{refund_tournament.id}/enroll",
            headers={"Authorization": f"Bearer {refund_student_token}"}
        )
        assert response.status_code == 200

        db_session.refresh(refund_student)
        balance_after_enrollment = refund_student.credit_balance

        print(f"✅ Setup: Enrolled ({initial_balance} → {balance_after_enrollment})")

        # ============================================================
        # FIRST UNENROLL: Success
        # ============================================================
        response = client.delete(
            f"/api/v1/tournaments/{refund_tournament.id}/unenroll",
            headers={"Authorization": f"Bearer {refund_student_token}"}
        )

        assert response.status_code == 200
        refund_data = response.json()
        assert refund_data["success"] is True

        db_session.refresh(refund_student)
        balance_after_first_refund = refund_student.credit_balance

        print(f"✅ First unenroll: Success (refund: {refund_data['refund_amount']})")

        # ============================================================
        # SECOND UNENROLL: Idempotency check
        # ============================================================
        response = client.delete(
            f"/api/v1/tournaments/{refund_tournament.id}/unenroll",
            headers={"Authorization": f"Bearer {refund_student_token}"}
        )

        # Should be rejected (no active enrollment)
        assert response.status_code == 404
        error_data = response.json()
        assert "no active enrollment" in error_data["error"]["message"].lower()

        print(f"✅ Second unenroll: Rejected (404 - no active enrollment)")

        # ============================================================
        # VALIDATION: Balance unchanged (no double refund)
        # ============================================================
        db_session.refresh(refund_student)
        assert refund_student.credit_balance == balance_after_first_refund

        print(f"✅ Balance unchanged: {balance_after_first_refund} (no double refund)")

        # ============================================================
        # VALIDATION: Only ONE refund transaction
        # ============================================================
        refund_transactions = db_session.query(CreditTransaction).filter(
            CreditTransaction.user_license_id == refund_student.licenses[0].id,
            CreditTransaction.transaction_type == "TOURNAMENT_UNENROLL_REFUND"
        ).all()

        assert len(refund_transactions) == 1

        print(f"✅ Refund transactions: {len(refund_transactions)} (singleton)")

        # ============================================================
        # E2E FLOW COMPLETE
        # ============================================================
        print("\n" + "="*60)
        print("🎉 IDEMPOTENCY E2E COMPLETE - Double Refund Prevention")
        print("="*60)
        print(f"Initial balance: {initial_balance}")
        print(f"After first refund: {balance_after_first_refund}")
        print(f"After second attempt: {refund_student.credit_balance} (unchanged)")
        print(f"Refund transactions: {len(refund_transactions)} (singleton)")
        print(f"Idempotency: ✅ PRESERVED")
        print("="*60)

    def test_refund_after_invalid_state_rejection(
        self,
        client,
        db_session,
        refund_student,
        refund_student_token
    ):
        """
        E2E Test: Refund after invalid state rejection

        Business Value: Prevent refunds for completed tournaments
        (revenue protection).

        Flow:
        1. Student enrolls in tournament
        2. Tournament completes (status → COMPLETED)
        3. Attempt unenroll → REJECTED (invalid tournament status)
        4. Verify: No refund processed
        5. Verify: Balance unchanged
        6. Verify: Enrollment still APPROVED and active
        """

        initial_balance = refund_student.credit_balance  # 1000

        # ============================================================
        # SETUP: Create and enroll in tournament
        # ============================================================
        tournament = Semester(
            code="COMPLETED-REFUND-2026",
            name="Completed Refund Test Tournament 2026",
            specialization_type="LFA_FOOTBALL_PLAYER",
            age_group="PRO",
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=60),
            status=SemesterStatus.READY_FOR_ENROLLMENT,
            tournament_status="ENROLLMENT_OPEN",
            enrollment_cost=500,
            is_active=True
        )
        db_session.add(tournament)
        db_session.commit()
        db_session.refresh(tournament)

        # Enroll student
        response = client.post(
            f"/api/v1/tournaments/{tournament.id}/enroll",
            headers={"Authorization": f"Bearer {refund_student_token}"}
        )
        assert response.status_code == 200

        db_session.refresh(refund_student)
        balance_after_enrollment = refund_student.credit_balance

        print(f"✅ Setup: Enrolled ({initial_balance} → {balance_after_enrollment})")

        # ============================================================
        # SIMULATE: Tournament completes
        # ============================================================
        tournament.tournament_status = "COMPLETED"
        tournament.status = SemesterStatus.COMPLETED
        db_session.commit()

        print(f"✅ Setup: Tournament completed (status → COMPLETED)")

        # ============================================================
        # ATTEMPT UNENROLL: Should be rejected
        # ============================================================
        response = client.delete(
            f"/api/v1/tournaments/{tournament.id}/unenroll",
            headers={"Authorization": f"Bearer {refund_student_token}"}
        )

        # Should be rejected (invalid tournament status)
        assert response.status_code == 400
        error_data = response.json()
        assert "cannot unenroll" in error_data["error"]["message"].lower()

        print(f"✅ Unenroll rejected: {error_data['error']['message']}")

        # ============================================================
        # VALIDATION: Balance unchanged (no refund)
        # ============================================================
        db_session.refresh(refund_student)
        assert refund_student.credit_balance == balance_after_enrollment

        print(f"✅ Balance unchanged: {balance_after_enrollment} (no refund)")

        # ============================================================
        # VALIDATION: Enrollment still APPROVED and active
        # ============================================================
        enrollment = db_session.query(SemesterEnrollment).filter(
            SemesterEnrollment.user_id == refund_student.id,
            SemesterEnrollment.semester_id == tournament.id
        ).first()

        assert enrollment is not None
        assert enrollment.request_status == EnrollmentStatus.APPROVED
        assert enrollment.is_active is True

        print(f"✅ Enrollment status: APPROVED, is_active: True (unchanged)")

        # ============================================================
        # VALIDATION: No refund transaction
        # ============================================================
        refund_transactions = db_session.query(CreditTransaction).filter(
            CreditTransaction.user_license_id == refund_student.licenses[0].id,
            CreditTransaction.transaction_type == "TOURNAMENT_UNENROLL_REFUND"
        ).all()

        assert len(refund_transactions) == 0

        print(f"✅ Refund transactions: {len(refund_transactions)} (none)")

        # ============================================================
        # E2E FLOW COMPLETE
        # ============================================================
        print("\n" + "="*60)
        print("🎉 INVALID STATE E2E COMPLETE - Refund Protection")
        print("="*60)
        print(f"Initial balance: {initial_balance}")
        print(f"After enrollment: {balance_after_enrollment}")
        print(f"After rejection: {refund_student.credit_balance} (unchanged)")
        print(f"Enrollment status: APPROVED (unchanged)")
        print(f"Refund transactions: 0 (none)")
        print(f"Revenue protection: ✅ PRESERVED")
        print("="*60)
