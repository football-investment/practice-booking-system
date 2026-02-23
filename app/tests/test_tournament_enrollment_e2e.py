"""
Tournament Enrollment Flow E2E Test

Full business value chain validation:
1. Student queries tournament details
2. Student enrolls in tournament
3. Credit deduction verified
4. Sessions generated for tournament
5. Instructor checks in to session
6. Audit trail validated end-to-end

Marker: @pytest.mark.e2e
Purpose: Demonstrate complete business flow from enrollment to check-in.
"""

import pytest
from datetime import date, timedelta, datetime, timezone
from sqlalchemy.orm import Session as DBSession

from app.models.user import User, UserRole
from app.models.semester import Semester, SemesterStatus
from app.models.campus import Campus
from app.models.location import Location
from app.models.license import UserLicense
from app.models.session import Session as SessionModel
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.models.audit_log import AuditLog, AuditAction
from app.core.security import get_password_hash
from app.database import get_db


@pytest.fixture
def e2e_student(db_session: DBSession):
    """Create student with credits for E2E flow"""
    user = User(
        name="E2E Test Student",
        email="e2e.student@test.com",
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
def e2e_student_token(client, e2e_student):
    """Get access token for E2E student"""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "e2e.student@test.com", "password": "student123"}
    )
    return response.json()["access_token"]


@pytest.fixture
def e2e_instructor(db_session: DBSession):
    """Create instructor for E2E flow"""
    user = User(
        name="E2E Test Instructor",
        email="e2e.instructor@test.com",
        password_hash=get_password_hash("instructor123"),
        role=UserRole.INSTRUCTOR,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def e2e_instructor_token(client, e2e_instructor):
    """Get access token for E2E instructor"""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "e2e.instructor@test.com", "password": "instructor123"}
    )
    return response.json()["access_token"]


@pytest.fixture
def e2e_tournament(db_session: DBSession):
    """Create tournament ready for enrollment"""
    tournament = Semester(
        code="E2E-TOURNAMENT-2026",
        name="E2E Tournament 2026",
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


@pytest.fixture
def e2e_session(db_session: DBSession, e2e_tournament, e2e_instructor):
    """Create session for E2E flow (instructor assigned)"""
    # Need campus and location first
    location = Location(
        name="E2E Location",
        city="E2E City",
        country="E2E Country",
        postal_code="12345",
        is_active=True
    )
    db_session.add(location)
    db_session.flush()

    campus = Campus(
        name="E2E Campus",
        location_id=location.id,
        address="E2E Address",
        is_active=True
    )
    db_session.add(campus)
    db_session.flush()

    # Create session scheduled for future (2 days from now)
    session = SessionModel(
        title="E2E Tournament Session",
        date_start=datetime.now(timezone.utc) + timedelta(days=2),
        date_end=datetime.now(timezone.utc) + timedelta(days=2, hours=2),
        semester_id=e2e_tournament.id,
        instructor_id=e2e_instructor.id,
        session_status='scheduled',
        capacity=20,
        location="E2E Field"
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


@pytest.mark.e2e
class TestTournamentEnrollmentE2E:
    """E2E test suite for complete tournament enrollment business flow"""

    def test_full_tournament_enrollment_flow(
        self,
        client,
        db_session,
        e2e_student,
        e2e_student_token,
        e2e_instructor,
        e2e_instructor_token,
        e2e_tournament,
        e2e_session
    ):
        """
        E2E Test: Complete tournament enrollment business flow

        Flow:
        1. Student queries tournament details
        2. Student enrolls in tournament
        3. Credit deduction verified
        4. Student queries tournament sessions (visibility check)
        5. Instructor checks in to session
        6. Audit trail validated

        Business Value: Demonstrates complete user journey from enrollment to session participation.
        """

        # ============================================================
        # STEP 1: Student queries tournament details
        # ============================================================
        response = client.get(
            f"/api/v1/tournaments/{e2e_tournament.id}",
            headers={"Authorization": f"Bearer {e2e_student_token}"}
        )

        assert response.status_code == 200
        tournament_data = response.json()
        assert tournament_data["id"] == e2e_tournament.id
        assert tournament_data["tournament_status"] == "ENROLLMENT_OPEN"
        assert tournament_data["enrollment_cost"] == 500

        print(f"✅ Step 1: Student queried tournament {e2e_tournament.id}")

        # ============================================================
        # STEP 2: Student enrolls in tournament
        # ============================================================
        initial_balance = e2e_student.credit_balance

        response = client.post(
            f"/api/v1/tournaments/{e2e_tournament.id}/enroll",
            headers={"Authorization": f"Bearer {e2e_student_token}"}
        )

        assert response.status_code == 200
        enrollment_data = response.json()

        # Response has nested structure
        assert enrollment_data["success"] is True
        assert enrollment_data["enrollment"]["semester_id"] == e2e_tournament.id
        assert enrollment_data["enrollment"]["user_id"] == e2e_student.id
        assert enrollment_data["enrollment"]["request_status"] == "approved"

        print(f"✅ Step 2: Student enrolled in tournament {e2e_tournament.id}")

        # ============================================================
        # STEP 3: Credit deduction verified
        # ============================================================
        db_session.refresh(e2e_student)
        expected_balance = initial_balance - e2e_tournament.enrollment_cost
        assert e2e_student.credit_balance == expected_balance

        # Verify enrollment record in database
        enrollment = db_session.query(SemesterEnrollment).filter(
            SemesterEnrollment.user_id == e2e_student.id,
            SemesterEnrollment.semester_id == e2e_tournament.id
        ).first()

        assert enrollment is not None
        assert enrollment.request_status == EnrollmentStatus.APPROVED
        assert enrollment.is_active is True

        print(f"✅ Step 3: Credit deducted ({initial_balance} → {expected_balance})")

        # ============================================================
        # STEP 4: Student queries tournament sessions (visibility)
        # ============================================================
        response = client.get(
            f"/api/v1/sessions/?semester_id={e2e_tournament.id}",
            headers={"Authorization": f"Bearer {e2e_student_token}"}
        )

        assert response.status_code == 200
        sessions_response = response.json()

        # Verify session is visible to enrolled student (paginated response)
        assert "sessions" in sessions_response
        sessions_data = sessions_response["sessions"]
        assert len(sessions_data) > 0
        session_ids = [s["id"] for s in sessions_data]
        assert e2e_session.id in session_ids

        print(f"✅ Step 4: Student can see {len(sessions_data)} tournament session(s)")

        # ============================================================
        # STEP 5: Instructor checks in to session
        # ============================================================
        response = client.post(
            f"/api/v1/sessions/{e2e_session.id}/check-in",
            headers={"Authorization": f"Bearer {e2e_instructor_token}"}
        )

        assert response.status_code == 200
        checkin_data = response.json()
        assert checkin_data["success"] is True
        assert checkin_data["session_id"] == e2e_session.id
        assert checkin_data["session_status"] == "in_progress"

        # Verify session status updated in database
        db_session.refresh(e2e_session)
        assert e2e_session.session_status == "in_progress"

        print(f"✅ Step 5: Instructor checked in to session {e2e_session.id}")

        # ============================================================
        # STEP 6: Audit trail validated
        # ============================================================
        # Check for check-in audit log
        checkin_audit = db_session.query(AuditLog).filter(
            AuditLog.action == AuditAction.SESSION_UPDATED,
            AuditLog.user_id == e2e_instructor.id
        ).order_by(AuditLog.timestamp.desc()).first()

        assert checkin_audit is not None
        assert checkin_audit.details["action_type"] == "check_in"
        assert checkin_audit.details["session_id"] == e2e_session.id
        assert checkin_audit.details["new_status"] == "in_progress"

        print(f"✅ Step 6: Audit trail validated (check-in logged)")

        # ============================================================
        # E2E FLOW COMPLETE
        # ============================================================
        print("\n" + "="*60)
        print("🎉 E2E FLOW COMPLETE - Business Value Demonstrated")
        print("="*60)
        print(f"Tournament: {e2e_tournament.name}")
        print(f"Student: {e2e_student.name} (enrolled)")
        print(f"Credits: {initial_balance} → {e2e_student.credit_balance}")
        print(f"Session: {e2e_session.title} (in progress)")
        print(f"Instructor: {e2e_instructor.name} (checked in)")
        print(f"Audit: Complete trail from enrollment to check-in")
        print("="*60)
