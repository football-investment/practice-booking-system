"""
Session Check-In API Tests

Tests POST /api/v1/sessions/{id}/check-in endpoint:
1. Successful check-in (assigned instructor, valid session)
2. Non-instructor forbidden (403)
3. Unassigned instructor forbidden (403)
4. Already started session returns 400
5. Session not found returns 404
6. Audit log created on successful check-in
"""

import pytest
from datetime import date, timedelta, datetime, timezone
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.session import Session as SessionModel
from app.models.semester import Semester, SemesterStatus
from app.models.license import UserLicense
from app.models.audit_log import AuditLog, AuditAction
from app.core.security import get_password_hash
from app.database import get_db


@pytest.fixture
def test_instructor(db_session: Session):
    """Create test instructor"""
    user = User(
        name="Test Instructor",
        email="session.checkin.instructor@test.com",
        password_hash=get_password_hash("instructor123"),
        role=UserRole.INSTRUCTOR,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_instructor_token(client, test_instructor):
    """Get access token for test instructor"""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "session.checkin.instructor@test.com", "password": "instructor123"}
    )
    return response.json()["access_token"]


@pytest.fixture
def other_instructor(db_session: Session):
    """Create another instructor (not assigned to test session)"""
    user = User(
        name="Other Instructor",
        email="other.instructor@test.com",
        password_hash=get_password_hash("instructor123"),
        role=UserRole.INSTRUCTOR,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_instructor_token(client, other_instructor):
    """Get access token for other instructor"""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "other.instructor@test.com", "password": "instructor123"}
    )
    return response.json()["access_token"]


@pytest.fixture
def test_student_checkin(db_session: Session):
    """Create test student (non-instructor)"""
    user = User(
        name="Test Student",
        email="session.checkin.student@test.com",
        password_hash=get_password_hash("student123"),
        role=UserRole.STUDENT,
        is_active=True,
        credit_balance=1000,
        date_of_birth=date(2010, 1, 15)
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_student_checkin_token(client, test_student_checkin):
    """Get access token for test student"""
    # Create license for student
    license = UserLicense(
        user_id=test_student_checkin.id,
        specialization_type="LFA_FOOTBALL_PLAYER",
        is_active=True,
        started_at=datetime.now(timezone.utc)
    )
    client.app.dependency_overrides[get_db]().add(license)
    client.app.dependency_overrides[get_db]().commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "session.checkin.student@test.com", "password": "student123"}
    )
    return response.json()["access_token"]


@pytest.fixture
def test_semester_checkin(db_session: Session):
    """Create test semester for sessions"""
    semester = Semester(
        code="CHECKIN-TEST-2026",
        name="Check-in Test Semester 2026",
        specialization_type="LFA_FOOTBALL_PLAYER",
        start_date=date.today() + timedelta(days=30),
        end_date=date.today() + timedelta(days=60),
        status=SemesterStatus.READY_FOR_ENROLLMENT,
        is_active=True
    )
    db_session.add(semester)
    db_session.commit()
    db_session.refresh(semester)
    return semester


@pytest.fixture
def scheduled_session(db_session: Session, test_instructor, test_semester_checkin):
    """Create scheduled session assigned to test instructor"""
    session = SessionModel(
        title="Test Session - Scheduled",
        date_start=datetime.now(timezone.utc) + timedelta(hours=2),
        date_end=datetime.now(timezone.utc) + timedelta(hours=4),
        semester_id=test_semester_checkin.id,
        instructor_id=test_instructor.id,
        session_status='scheduled',
        capacity=20,
        location="Test Field 1"
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


@pytest.fixture
def in_progress_session(db_session: Session, test_instructor, test_semester_checkin):
    """Create session already in progress"""
    session = SessionModel(
        title="Test Session - In Progress",
        date_start=datetime.now(timezone.utc) + timedelta(hours=2),
        date_end=datetime.now(timezone.utc) + timedelta(hours=4),
        semester_id=test_semester_checkin.id,
        instructor_id=test_instructor.id,
        session_status='in_progress',
        capacity=20,
        location="Test Field 2"
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


class TestSessionCheckInAPI:
    """Test suite for POST /api/v1/sessions/{id}/check-in endpoint"""

    def test_check_in_success(
        self, client, db_session, scheduled_session, test_instructor_token
    ):
        """Test 1: Assigned instructor can check in successfully"""
        response = client.post(
            f"/api/v1/sessions/{scheduled_session.id}/check-in",
            headers={"Authorization": f"Bearer {test_instructor_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["success"] is True
        assert data["session_id"] == scheduled_session.id
        assert data["session_status"] == "in_progress"
        assert "checked_in_at" in data
        assert "Checked in to session successfully" in data["message"]

        # Verify session status updated in database
        db_session.refresh(scheduled_session)
        assert scheduled_session.session_status == "in_progress"

    def test_check_in_non_instructor_forbidden(
        self, client, scheduled_session, test_student_checkin_token
    ):
        """Test 2: Non-instructor gets 403 Forbidden"""
        response = client.post(
            f"/api/v1/sessions/{scheduled_session.id}/check-in",
            headers={"Authorization": f"Bearer {test_student_checkin_token}"}
        )

        assert response.status_code == 403
        data = response.json()
        assert "error" in data
        assert "Only instructors can check in" in data["error"]["message"]

    def test_check_in_unassigned_instructor_forbidden(
        self, client, scheduled_session, other_instructor_token
    ):
        """Test 3: Unassigned instructor gets 403 Forbidden"""
        response = client.post(
            f"/api/v1/sessions/{scheduled_session.id}/check-in",
            headers={"Authorization": f"Bearer {other_instructor_token}"}
        )

        assert response.status_code == 403
        data = response.json()
        assert "error" in data
        assert "not assigned to session" in data["error"]["message"]

    def test_check_in_already_started_session(
        self, client, in_progress_session, test_instructor_token
    ):
        """Test 4: Already started session returns 400"""
        response = client.post(
            f"/api/v1/sessions/{in_progress_session.id}/check-in",
            headers={"Authorization": f"Bearer {test_instructor_token}"}
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "already in_progress" in data["error"]["message"]

    def test_check_in_session_not_found(
        self, client, test_instructor_token
    ):
        """Test 5: Session not found returns 404"""
        response = client.post(
            "/api/v1/sessions/99999/check-in",  # Non-existent session
            headers={"Authorization": f"Bearer {test_instructor_token}"}
        )

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "not found" in data["error"]["message"].lower()

    def test_check_in_audit_log_created(
        self, client, db_session, scheduled_session, test_instructor, test_instructor_token
    ):
        """Test 6: Audit log created on successful check-in"""
        # Get initial audit log count
        initial_count = db_session.query(AuditLog).filter(
            AuditLog.action == AuditAction.SESSION_UPDATED,
            AuditLog.user_id == test_instructor.id
        ).count()

        # Perform check-in
        response = client.post(
            f"/api/v1/sessions/{scheduled_session.id}/check-in",
            headers={"Authorization": f"Bearer {test_instructor_token}"}
        )

        assert response.status_code == 200

        # Verify audit log created
        final_count = db_session.query(AuditLog).filter(
            AuditLog.action == AuditAction.SESSION_UPDATED,
            AuditLog.user_id == test_instructor.id
        ).count()

        assert final_count == initial_count + 1

        # Verify audit log details
        audit_log = db_session.query(AuditLog).filter(
            AuditLog.action == AuditAction.SESSION_UPDATED,
            AuditLog.user_id == test_instructor.id
        ).order_by(AuditLog.timestamp.desc()).first()

        assert audit_log is not None
        assert audit_log.details["session_id"] == scheduled_session.id
        assert audit_log.details["action_type"] == "check_in"
        assert audit_log.details["new_status"] == "in_progress"
        assert audit_log.details["instructor_id"] == test_instructor.id
