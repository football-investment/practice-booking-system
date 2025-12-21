"""
Session Rules Tests - 6 Rules × 4 Tests Each = 24 Tests

Tests all 6 Session Rules as defined in SESSION_RULES_ETALON.md:
1. Rule #1: 24h Booking Deadline
2. Rule #2: 12h Cancellation Deadline
3. Rule #3: 15min Check-in Window
4. Rule #4: 24h Feedback Window
5. Rule #5: Session-Type Quiz Access
6. Rule #6: Intelligent XP Calculation

Each rule has 4 tests:
- Success case (rule allows operation)
- Failure case (rule blocks operation)
- Edge case (boundary condition)
- Error handling case
"""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from ...main import app
from ...models.user import User, UserRole
from ...models.session import Session as SessionModel, SessionMode
from ...models.booking import Booking, BookingStatus
from ...models.attendance import Attendance, AttendanceStatus
from ...models.feedback import Feedback
from ...models.quiz import Quiz, QuizAttempt
from ...models.semester import Semester
from ...database import get_db
from ...core.security import get_password_hash

client = TestClient(app)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def db_session():
    """Database session fixture"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def student_user(db_session: Session):
    """Create test student user"""
    user = User(
        email="student@test.com",
        name="Test Student",
        hashed_password=get_password_hash("testpass123"),
        role=UserRole.STUDENT,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def instructor_user(db_session: Session):
    """Create test instructor user"""
    user = User(
        email="instructor@test.com",
        name="Test Instructor",
        hashed_password=get_password_hash("testpass123"),
        role=UserRole.INSTRUCTOR,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def active_semester(db_session: Session):
    """Create active test semester"""
    semester = Semester(
        code="TEST_2025_S1",
        name="Test Semester 2025 S1",
        start_date=datetime.now().date() - timedelta(days=30),
        end_date=datetime.now().date() + timedelta(days=60),
        is_active=True
    )
    db_session.add(semester)
    db_session.commit()
    db_session.refresh(semester)
    return semester


@pytest.fixture
def future_session(db_session: Session, active_semester, instructor_user):
    """Create session starting in 48 hours (allows 24h booking deadline)"""
    session = SessionModel(
        title="Test Session - Future",
        description="Test session for booking",
        date_start=datetime.now(timezone.utc) + timedelta(hours=48),
        date_end=datetime.now(timezone.utc) + timedelta(hours=50),
        capacity=10,
        mode=SessionMode.HYBRID,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


def get_auth_token(email: str, password: str = "testpass123"):
    """Get JWT token for user authentication"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


# ============================================================================
# RULE #1: 24h BOOKING DEADLINE
# ============================================================================

def test_rule1_success_book_48h_before(db_session, student_user, future_session):
    """
    Rule #1 Success: User can book session 48 hours before start
    """
    token = get_auth_token(student_user.email)

    response = client.post(
        "/api/v1/bookings/",
        json={"session_id": future_session.id},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == future_session.id
    assert data["status"] == "confirmed"


def test_rule1_failure_book_12h_before(db_session, student_user, instructor_user, active_semester):
    """
    Rule #1 Failure: User cannot book session 12 hours before start (violates 24h rule)
    """
    # Create session starting in 12 hours (within 24h deadline)
    near_session = SessionModel(
        title="Test Session - Near",
        description="Session starting soon",
        date_start=datetime.now(timezone.utc) + timedelta(hours=12),
        date_end=datetime.now(timezone.utc) + timedelta(hours=14),
        capacity=10,
        mode=SessionMode.HYBRID,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(near_session)
    db_session.commit()

    token = get_auth_token(student_user.email)

    response = client.post(
        "/api/v1/bookings/",
        json={"session_id": near_session.id},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 400
    assert "24 hours" in response.json()["detail"].lower()


def test_rule1_edge_exactly_24h_before(db_session, student_user, instructor_user, active_semester):
    """
    Rule #1 Edge Case: User can book exactly 24 hours before start (boundary)
    """
    # Create session starting in exactly 24 hours
    exact_session = SessionModel(
        title="Test Session - Exact 24h",
        description="Session at boundary",
        date_start=datetime.now(timezone.utc) + timedelta(hours=24, minutes=1),  # Just over 24h
        date_end=datetime.now(timezone.utc) + timedelta(hours=26),
        capacity=10,
        mode=SessionMode.HYBRID,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(exact_session)
    db_session.commit()

    token = get_auth_token(student_user.email)

    response = client.post(
        "/api/v1/bookings/",
        json={"session_id": exact_session.id},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200


def test_rule1_error_book_past_session(db_session, student_user, instructor_user, active_semester):
    """
    Rule #1 Error: User cannot book past session
    """
    # Create past session
    past_session = SessionModel(
        title="Test Session - Past",
        description="Session in the past",
        date_start=datetime.now(timezone.utc) - timedelta(hours=2),
        date_end=datetime.now(timezone.utc) - timedelta(hours=1),
        capacity=10,
        mode=SessionMode.HYBRID,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(past_session)
    db_session.commit()

    token = get_auth_token(student_user.email)

    response = client.post(
        "/api/v1/bookings/",
        json={"session_id": past_session.id},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 400
    assert "past" in response.json()["detail"].lower()


# ============================================================================
# RULE #2: 12h CANCELLATION DEADLINE
# ============================================================================

def test_rule2_success_cancel_48h_before(db_session, student_user, future_session):
    """
    Rule #2 Success: User can cancel booking 48 hours before start
    """
    # First create booking
    booking = Booking(
        user_id=student_user.id,
        session_id=future_session.id,
        status=BookingStatus.CONFIRMED
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    token = get_auth_token(student_user.email)

    response = client.delete(
        f"/api/v1/bookings/{booking.id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert "cancelled successfully" in response.json()["message"].lower()


def test_rule2_failure_cancel_6h_before(db_session, student_user, instructor_user, active_semester):
    """
    Rule #2 Failure: User cannot cancel booking 6 hours before start (violates 12h rule)
    """
    # Create session starting in 6 hours
    near_session = SessionModel(
        title="Test Session - Near",
        description="Session starting soon",
        date_start=datetime.now(timezone.utc) + timedelta(hours=6),
        date_end=datetime.now(timezone.utc) + timedelta(hours=8),
        capacity=10,
        mode=SessionMode.HYBRID,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(near_session)
    db_session.commit()

    # Create booking
    booking = Booking(
        user_id=student_user.id,
        session_id=near_session.id,
        status=BookingStatus.CONFIRMED
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    token = get_auth_token(student_user.email)

    response = client.delete(
        f"/api/v1/bookings/{booking.id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 400
    assert "12 hours" in response.json()["detail"].lower()


def test_rule2_edge_exactly_12h_before(db_session, student_user, instructor_user, active_semester):
    """
    Rule #2 Edge Case: User can cancel exactly 12 hours before start (boundary)
    """
    # Create session starting in exactly 12 hours + 1 minute
    exact_session = SessionModel(
        title="Test Session - Exact 12h",
        description="Session at boundary",
        date_start=datetime.now(timezone.utc) + timedelta(hours=12, minutes=1),
        date_end=datetime.now(timezone.utc) + timedelta(hours=14),
        capacity=10,
        mode=SessionMode.HYBRID,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(exact_session)
    db_session.commit()

    # Create booking
    booking = Booking(
        user_id=student_user.id,
        session_id=exact_session.id,
        status=BookingStatus.CONFIRMED
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    token = get_auth_token(student_user.email)

    response = client.delete(
        f"/api/v1/bookings/{booking.id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200


def test_rule2_error_cancel_past_session(db_session, student_user, instructor_user, active_semester):
    """
    Rule #2 Error: User cannot cancel past session booking
    """
    # Create past session
    past_session = SessionModel(
        title="Test Session - Past",
        description="Session in the past",
        date_start=datetime.now(timezone.utc) - timedelta(hours=2),
        date_end=datetime.now(timezone.utc) - timedelta(hours=1),
        capacity=10,
        mode=SessionMode.HYBRID,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(past_session)
    db_session.commit()

    # Create booking
    booking = Booking(
        user_id=student_user.id,
        session_id=past_session.id,
        status=BookingStatus.CONFIRMED
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    token = get_auth_token(student_user.email)

    response = client.delete(
        f"/api/v1/bookings/{booking.id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 400
    assert "past" in response.json()["detail"].lower()


# ============================================================================
# RULE #3: 15min CHECK-IN WINDOW
# ============================================================================

def test_rule3_success_checkin_5min_before_start(db_session, student_user, instructor_user, active_semester):
    """
    Rule #3 Success: User can check in 5 minutes before session start
    """
    # Create session starting in 5 minutes
    imminent_session = SessionModel(
        title="Test Session - Starting Soon",
        description="Session starting in 5 minutes",
        date_start=datetime.now(timezone.utc) + timedelta(minutes=5),
        date_end=datetime.now(timezone.utc) + timedelta(hours=2),
        capacity=10,
        mode=SessionMode.HYBRID,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(imminent_session)
    db_session.commit()

    # Create confirmed booking
    booking = Booking(
        user_id=student_user.id,
        session_id=imminent_session.id,
        status=BookingStatus.CONFIRMED
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    token = get_auth_token(student_user.email)

    response = client.post(
        f"/api/v1/attendance/{booking.id}/checkin",
        json={"notes": "Checked in successfully"},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "present"


def test_rule3_failure_checkin_30min_before_start(db_session, student_user, instructor_user, active_semester):
    """
    Rule #3 Failure: User cannot check in 30 minutes before start (violates 15min rule)
    """
    # Create session starting in 30 minutes
    early_session = SessionModel(
        title="Test Session - Too Early",
        description="Session starting in 30 minutes",
        date_start=datetime.now(timezone.utc) + timedelta(minutes=30),
        date_end=datetime.now(timezone.utc) + timedelta(hours=2),
        capacity=10,
        mode=SessionMode.HYBRID,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(early_session)
    db_session.commit()

    # Create confirmed booking
    booking = Booking(
        user_id=student_user.id,
        session_id=early_session.id,
        status=BookingStatus.CONFIRMED
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    token = get_auth_token(student_user.email)

    response = client.post(
        f"/api/v1/attendance/{booking.id}/checkin",
        json={"notes": "Trying to check in early"},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 400
    assert "15 minutes" in response.json()["detail"].lower()


def test_rule3_edge_exactly_15min_before(db_session, student_user, instructor_user, active_semester):
    """
    Rule #3 Edge Case: User can check in exactly 15 minutes before start (boundary)
    """
    # Create session starting in exactly 15 minutes
    exact_session = SessionModel(
        title="Test Session - Exact 15min",
        description="Session at boundary",
        date_start=datetime.now(timezone.utc) + timedelta(minutes=15),
        date_end=datetime.now(timezone.utc) + timedelta(hours=2),
        capacity=10,
        mode=SessionMode.HYBRID,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(exact_session)
    db_session.commit()

    # Create confirmed booking
    booking = Booking(
        user_id=student_user.id,
        session_id=exact_session.id,
        status=BookingStatus.CONFIRMED
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    token = get_auth_token(student_user.email)

    response = client.post(
        f"/api/v1/attendance/{booking.id}/checkin",
        json={"notes": "Checking in at boundary"},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200


def test_rule3_error_checkin_after_session_end(db_session, student_user, instructor_user, active_semester):
    """
    Rule #3 Error: User cannot check in after session has ended
    """
    # Create past session
    past_session = SessionModel(
        title="Test Session - Past",
        description="Session already ended",
        date_start=datetime.now(timezone.utc) - timedelta(hours=3),
        date_end=datetime.now(timezone.utc) - timedelta(hours=1),
        capacity=10,
        mode=SessionMode.HYBRID,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(past_session)
    db_session.commit()

    # Create confirmed booking
    booking = Booking(
        user_id=student_user.id,
        session_id=past_session.id,
        status=BookingStatus.CONFIRMED
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    token = get_auth_token(student_user.email)

    response = client.post(
        f"/api/v1/attendance/{booking.id}/checkin",
        json={"notes": "Trying to check in late"},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 400
    assert "ended" in response.json()["detail"].lower()


# ============================================================================
# RULE #4: 24h FEEDBACK WINDOW
# ============================================================================

def test_rule4_success_feedback_within_24h(db_session, student_user, instructor_user, active_semester):
    """
    Rule #4 Success: User can submit feedback within 24 hours after session
    """
    # Create past session (ended 12 hours ago)
    recent_session = SessionModel(
        title="Test Session - Recent",
        description="Session ended 12 hours ago",
        date_start=datetime.now(timezone.utc) - timedelta(hours=14),
        date_end=datetime.now(timezone.utc) - timedelta(hours=12),
        capacity=10,
        mode=SessionMode.HYBRID,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(recent_session)
    db_session.commit()

    # Create attendance record
    attendance = Attendance(
        user_id=student_user.id,
        session_id=recent_session.id,
        status=AttendanceStatus.PRESENT,
        check_in_time=recent_session.date_start
    )
    db_session.add(attendance)
    db_session.commit()

    token = get_auth_token(student_user.email)

    response = client.post(
        "/api/v1/feedback/",
        json={
            "session_id": recent_session.id,
            "rating": 5,
            "comment": "Great session!"
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["rating"] == 5


def test_rule4_failure_feedback_after_24h(db_session, student_user, instructor_user, active_semester):
    """
    Rule #4 Failure: User cannot submit feedback after 24h window (violates rule)
    """
    # Create past session (ended 30 hours ago)
    old_session = SessionModel(
        title="Test Session - Old",
        description="Session ended 30 hours ago",
        date_start=datetime.now(timezone.utc) - timedelta(hours=32),
        date_end=datetime.now(timezone.utc) - timedelta(hours=30),
        capacity=10,
        mode=SessionMode.HYBRID,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(old_session)
    db_session.commit()

    # Create attendance record
    attendance = Attendance(
        user_id=student_user.id,
        session_id=old_session.id,
        status=AttendanceStatus.PRESENT,
        check_in_time=old_session.date_start
    )
    db_session.add(attendance)
    db_session.commit()

    token = get_auth_token(student_user.email)

    response = client.post(
        "/api/v1/feedback/",
        json={
            "session_id": old_session.id,
            "rating": 5,
            "comment": "Late feedback"
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 400
    assert "24" in response.json()["detail"].lower()


def test_rule4_edge_exactly_24h_after(db_session, student_user, instructor_user, active_semester):
    """
    Rule #4 Edge Case: User can submit feedback exactly 24 hours after session (boundary)
    """
    # Create past session (ended exactly 24 hours ago)
    exact_session = SessionModel(
        title="Test Session - Exact 24h",
        description="Session ended exactly 24h ago",
        date_start=datetime.now(timezone.utc) - timedelta(hours=26),
        date_end=datetime.now(timezone.utc) - timedelta(hours=24, minutes=1),  # Just under 24h
        capacity=10,
        mode=SessionMode.HYBRID,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(exact_session)
    db_session.commit()

    # Create attendance record
    attendance = Attendance(
        user_id=student_user.id,
        session_id=exact_session.id,
        status=AttendanceStatus.PRESENT,
        check_in_time=exact_session.date_start
    )
    db_session.add(attendance)
    db_session.commit()

    token = get_auth_token(student_user.email)

    response = client.post(
        "/api/v1/feedback/",
        json={
            "session_id": exact_session.id,
            "rating": 5,
            "comment": "Feedback at boundary"
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200


def test_rule4_error_feedback_without_attendance(db_session, student_user, instructor_user, active_semester):
    """
    Rule #4 Error: User cannot submit feedback if they didn't attend session
    """
    # Create past session
    past_session = SessionModel(
        title="Test Session - Not Attended",
        description="Session user didn't attend",
        date_start=datetime.now(timezone.utc) - timedelta(hours=14),
        date_end=datetime.now(timezone.utc) - timedelta(hours=12),
        capacity=10,
        mode=SessionMode.HYBRID,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(past_session)
    db_session.commit()

    # NO attendance record created

    token = get_auth_token(student_user.email)

    response = client.post(
        "/api/v1/feedback/",
        json={
            "session_id": past_session.id,
            "rating": 5,
            "comment": "Feedback without attending"
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 400
    assert "attend" in response.json()["detail"].lower()


# ============================================================================
# RULE #5: SESSION-TYPE QUIZ ACCESS
# ============================================================================

def test_rule5_success_quiz_on_hybrid_session(db_session, student_user, instructor_user, active_semester):
    """
    Rule #5 Success: Student can take quiz during HYBRID session
    """
    # Create HYBRID session
    hybrid_session = SessionModel(
        title="Test Session - Hybrid",
        description="Hybrid session with quiz",
        date_start=datetime.now(timezone.utc) - timedelta(minutes=30),  # Started 30 min ago
        date_end=datetime.now(timezone.utc) + timedelta(minutes=90),    # Ends in 90 min
        capacity=10,
        mode=SessionMode.HYBRID,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(hybrid_session)
    db_session.commit()

    # Create quiz for session
    quiz = Quiz(
        session_id=hybrid_session.id,
        title="Test Quiz",
        duration_minutes=30,
        passing_score=70
    )
    db_session.add(quiz)
    db_session.commit()
    db_session.refresh(quiz)

    token = get_auth_token(student_user.email)

    response = client.post(
        f"/api/v1/quiz/{quiz.id}/attempt",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200


def test_rule5_failure_quiz_on_onsite_session(db_session, student_user, instructor_user, active_semester):
    """
    Rule #5 Failure: Student cannot take quiz during ONSITE session (violates rule)
    """
    # Create ONSITE session
    onsite_session = SessionModel(
        title="Test Session - Onsite",
        description="Onsite session (no quiz allowed)",
        date_start=datetime.now(timezone.utc) - timedelta(minutes=30),
        date_end=datetime.now(timezone.utc) + timedelta(minutes=90),
        capacity=10,
        mode=SessionMode.ONSITE,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(onsite_session)
    db_session.commit()

    # Try to create quiz for ONSITE session (should fail or block access)
    quiz = Quiz(
        session_id=onsite_session.id,
        title="Test Quiz",
        duration_minutes=30,
        passing_score=70
    )
    db_session.add(quiz)
    db_session.commit()
    db_session.refresh(quiz)

    token = get_auth_token(student_user.email)

    response = client.post(
        f"/api/v1/quiz/{quiz.id}/attempt",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 400
    assert "hybrid" in response.json()["detail"].lower() or "virtual" in response.json()["detail"].lower()


def test_rule5_edge_quiz_on_virtual_session(db_session, student_user, instructor_user, active_semester):
    """
    Rule #5 Edge Case: Student can take quiz during VIRTUAL session (also allowed)
    """
    # Create VIRTUAL session
    virtual_session = SessionModel(
        title="Test Session - Virtual",
        description="Virtual session with quiz",
        date_start=datetime.now(timezone.utc) - timedelta(minutes=30),
        date_end=datetime.now(timezone.utc) + timedelta(minutes=90),
        capacity=10,
        mode=SessionMode.VIRTUAL,
        meeting_link="https://zoom.us/test",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(virtual_session)
    db_session.commit()

    # Create quiz for session
    quiz = Quiz(
        session_id=virtual_session.id,
        title="Test Quiz",
        duration_minutes=30,
        passing_score=70
    )
    db_session.add(quiz)
    db_session.commit()
    db_session.refresh(quiz)

    token = get_auth_token(student_user.email)

    response = client.post(
        f"/api/v1/quiz/{quiz.id}/attempt",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200


def test_rule5_error_quiz_outside_session_time(db_session, student_user, instructor_user, active_semester):
    """
    Rule #5 Error: Student cannot take quiz before session starts
    """
    # Create future HYBRID session
    future_hybrid = SessionModel(
        title="Test Session - Future Hybrid",
        description="Hybrid session not started yet",
        date_start=datetime.now(timezone.utc) + timedelta(hours=2),
        date_end=datetime.now(timezone.utc) + timedelta(hours=4),
        capacity=10,
        mode=SessionMode.HYBRID,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(future_hybrid)
    db_session.commit()

    # Create quiz for session
    quiz = Quiz(
        session_id=future_hybrid.id,
        title="Test Quiz",
        duration_minutes=30,
        passing_score=70
    )
    db_session.add(quiz)
    db_session.commit()
    db_session.refresh(quiz)

    token = get_auth_token(student_user.email)

    response = client.post(
        f"/api/v1/quiz/{quiz.id}/attempt",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 400
    assert "not started" in response.json()["detail"].lower()


# ============================================================================
# RULE #6: INTELLIGENT XP CALCULATION
# ============================================================================

def test_rule6_success_xp_base_50_points(db_session, student_user, instructor_user, active_semester):
    """
    Rule #6 Success: Student gets base 50 XP for attending session
    """
    # Create and attend session
    session = SessionModel(
        title="Test Session - XP",
        description="Session for XP test",
        date_start=datetime.now(timezone.utc) - timedelta(hours=3),
        date_end=datetime.now(timezone.utc) - timedelta(hours=1),
        capacity=10,
        mode=SessionMode.HYBRID,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(session)
    db_session.commit()

    # Create attendance
    attendance = Attendance(
        user_id=student_user.id,
        session_id=session.id,
        status=AttendanceStatus.PRESENT,
        check_in_time=session.date_start
    )
    db_session.add(attendance)
    db_session.commit()

    # Check XP calculation
    token = get_auth_token(student_user.email)
    response = client.get(
        "/api/v1/users/me/xp",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    # Base XP should be at least 50
    assert response.json()["total_xp"] >= 50


def test_rule6_failure_no_xp_without_attendance(db_session, student_user, instructor_user, active_semester):
    """
    Rule #6 Failure: Student gets 0 XP if they didn't attend session
    """
    # Create session but no attendance
    session = SessionModel(
        title="Test Session - No Attendance",
        description="Session not attended",
        date_start=datetime.now(timezone.utc) - timedelta(hours=3),
        date_end=datetime.now(timezone.utc) - timedelta(hours=1),
        capacity=10,
        mode=SessionMode.HYBRID,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(session)
    db_session.commit()

    # No attendance record

    # Check XP calculation
    token = get_auth_token(student_user.email)
    response = client.get(
        "/api/v1/users/me/xp",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    # Should have 0 XP (no attendance)
    assert response.json()["total_xp"] == 0


def test_rule6_edge_xp_with_instructor_rating(db_session, student_user, instructor_user, active_semester):
    """
    Rule #6 Edge Case: XP increases with instructor rating (Base 50 + 0-50 from instructor)
    """
    # Create and attend session
    session = SessionModel(
        title="Test Session - With Rating",
        description="Session with instructor rating",
        date_start=datetime.now(timezone.utc) - timedelta(hours=3),
        date_end=datetime.now(timezone.utc) - timedelta(hours=1),
        capacity=10,
        mode=SessionMode.HYBRID,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(session)
    db_session.commit()

    # Create attendance with instructor rating (simulated - may need instructor feedback feature)
    attendance = Attendance(
        user_id=student_user.id,
        session_id=session.id,
        status=AttendanceStatus.PRESENT,
        check_in_time=session.date_start,
        instructor_rating=10  # Full 10/10 = +50 XP bonus
    )
    db_session.add(attendance)
    db_session.commit()

    # Check XP calculation
    token = get_auth_token(student_user.email)
    response = client.get(
        "/api/v1/users/me/xp",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    # Should have Base 50 + 50 (instructor bonus) = 100 XP
    assert response.json()["total_xp"] >= 100


def test_rule6_error_xp_with_quiz_bonus(db_session, student_user, instructor_user, active_semester):
    """
    Rule #6 Edge Case: XP increases with quiz score (Base 50 + 0-150 from quiz)
    """
    # Create and attend session
    session = SessionModel(
        title="Test Session - With Quiz",
        description="Session with quiz",
        date_start=datetime.now(timezone.utc) - timedelta(hours=3),
        date_end=datetime.now(timezone.utc) - timedelta(hours=1),
        capacity=10,
        mode=SessionMode.HYBRID,
        location="Test Location",
        semester_id=active_semester.id,
        instructor_id=instructor_user.id
    )
    db_session.add(session)
    db_session.commit()

    # Create quiz
    quiz = Quiz(
        session_id=session.id,
        title="Test Quiz",
        duration_minutes=30,
        passing_score=70
    )
    db_session.add(quiz)
    db_session.commit()

    # Create attendance
    attendance = Attendance(
        user_id=student_user.id,
        session_id=session.id,
        status=AttendanceStatus.PRESENT,
        check_in_time=session.date_start
    )
    db_session.add(attendance)
    db_session.commit()

    # Create quiz attempt with 100% score
    quiz_attempt = QuizAttempt(
        user_id=student_user.id,
        quiz_id=quiz.id,
        score=100,
        passed=True
    )
    db_session.add(quiz_attempt)
    db_session.commit()

    # Check XP calculation
    token = get_auth_token(student_user.email)
    response = client.get(
        "/api/v1/users/me/xp",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    # Should have Base 50 + 150 (quiz bonus) = 200 XP
    assert response.json()["total_xp"] >= 200


# ============================================================================
# END OF SESSION RULES TESTS
# ============================================================================
