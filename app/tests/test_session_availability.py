"""
Test Session Availability Bulk Query API

Validates batch availability queries for efficient session list display.
Tests UX improvement: N separate calls → 1 batch query.
"""
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.session import Session as SessionModel
from app.models.booking import Booking, BookingStatus
from app.models.user import User
from app.models.semester import Semester


@pytest.fixture
def test_semester(db_session: Session):
    """Create a test semester for session tests"""
    now = datetime.now(timezone.utc)
    semester = Semester(
        code="TEST2026",
        name="Test Semester 2026",
        start_date=now,
        end_date=now + timedelta(days=90)
    )
    db_session.add(semester)
    db_session.commit()
    db_session.refresh(semester)
    return semester


def test_availability_empty_sessions(client: TestClient):
    """Test availability query with no sessions"""
    response = client.get("/api/v1/sessions/availability?session_ids=999,998,997")

    assert response.status_code == 200
    data = response.json()

    # Should return empty result for non-existent sessions
    assert isinstance(data, dict)
    assert len(data) == 0


def test_availability_single_session_no_bookings(test_semester,
    client: TestClient,
    db_session: Session,
    admin_user: User,
    admin_token: str
):
    """Test availability for session with no bookings"""
    # Create a test session
    now = datetime.now(timezone.utc)
    session = SessionModel(
        title="Test Session",
        capacity=20,
        semester_id=test_semester.id,
        instructor_id=admin_user.id,
        date_start=now + timedelta(hours=1),
        date_end=now + timedelta(hours=2)
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    # Query availability
    response = client.get(f"/api/v1/sessions/availability?session_ids={session.id}")

    assert response.status_code == 200
    data = response.json()

    # Validate structure
    assert str(session.id) in data
    availability = data[str(session.id)]

    assert availability["capacity"] == 20
    assert availability["booked"] == 0
    assert availability["available"] == 20
    assert availability["waitlist_count"] == 0
    assert availability["status"] == "available"


def test_availability_session_partially_booked(test_semester,
    client: TestClient,
    db_session: Session,
    admin_user: User,
    student_user: User,
    admin_token: str
):
    """Test availability for session with some bookings"""
    # Create a test session
    now = datetime.now(timezone.utc)
    session = SessionModel(
        title="Test Session",
        capacity=10,
        semester_id=test_semester.id,
        instructor_id=admin_user.id,
        date_start=now + timedelta(hours=1),
        date_end=now + timedelta(hours=2)
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    # Create 3 confirmed bookings
    for i in range(3):
        booking = Booking(
            user_id=student_user.id,
            session_id=session.id,
            status=BookingStatus.CONFIRMED
        )
        db_session.add(booking)

    db_session.commit()

    # Query availability
    response = client.get(f"/api/v1/sessions/availability?session_ids={session.id}")

    assert response.status_code == 200
    data = response.json()

    availability = data[str(session.id)]

    assert availability["capacity"] == 10
    assert availability["booked"] == 3
    assert availability["available"] == 7
    assert availability["waitlist_count"] == 0
    assert availability["status"] == "available"


def test_availability_session_full_with_waitlist(test_semester,
    client: TestClient,
    db_session: Session,
    admin_user: User,
    student_user: User,
    admin_token: str
):
    """Test availability for full session with waitlist"""
    # Create a test session
    now = datetime.now(timezone.utc)
    session = SessionModel(
        title="Test Session",
        capacity=5,
        semester_id=test_semester.id,
        instructor_id=admin_user.id,
        date_start=now + timedelta(hours=1),
        date_end=now + timedelta(hours=2)
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    # Create 5 confirmed bookings (full capacity)
    for i in range(5):
        booking = Booking(
            user_id=student_user.id,
            session_id=session.id,
            status=BookingStatus.CONFIRMED
        )
        db_session.add(booking)

    # Create 2 waitlisted bookings
    for i in range(2):
        booking = Booking(
            user_id=student_user.id,
            session_id=session.id,
            status=BookingStatus.WAITLISTED,
            waitlist_position=i + 1
        )
        db_session.add(booking)

    db_session.commit()

    # Query availability
    response = client.get(f"/api/v1/sessions/availability?session_ids={session.id}")

    assert response.status_code == 200
    data = response.json()

    availability = data[str(session.id)]

    assert availability["capacity"] == 5
    assert availability["booked"] == 5
    assert availability["available"] == 0
    assert availability["waitlist_count"] == 2
    assert availability["status"] == "waitlist_only"


def test_availability_batch_multiple_sessions(test_semester,
    client: TestClient,
    db_session: Session,
    admin_user: User,
    student_user: User,
    admin_token: str
):
    """Test batch query for multiple sessions (UX improvement validation)"""
    # Create 3 test sessions with different availability states
    sessions = []

    # Session 1: Available (10/20)
    now = datetime.now(timezone.utc)
    session1 = SessionModel(
        title="Session 1",
        capacity=20,
        semester_id=test_semester.id,
        instructor_id=admin_user.id,
        date_start=now + timedelta(hours=1),
        date_end=now + timedelta(hours=2)
    )
    db_session.add(session1)
    db_session.commit()
    db_session.refresh(session1)
    sessions.append(session1)

    for i in range(10):
        booking = Booking(
            user_id=student_user.id,
            session_id=session1.id,
            status=BookingStatus.CONFIRMED
        )
        db_session.add(booking)

    # Session 2: Full (15/15)
    session2 = SessionModel(
        title="Session 2",
        capacity=15,
        semester_id=test_semester.id,
        instructor_id=admin_user.id,
        date_start=now + timedelta(hours=3),
        date_end=now + timedelta(hours=4)
    )
    db_session.add(session2)
    db_session.commit()
    db_session.refresh(session2)
    sessions.append(session2)

    for i in range(15):
        booking = Booking(
            user_id=student_user.id,
            session_id=session2.id,
            status=BookingStatus.CONFIRMED
        )
        db_session.add(booking)

    # Session 3: Empty (0/25)
    session3 = SessionModel(
        title="Session 3",
        capacity=25,
        semester_id=test_semester.id,
        instructor_id=admin_user.id,
        date_start=now + timedelta(hours=5),
        date_end=now + timedelta(hours=6)
    )
    db_session.add(session3)
    db_session.commit()
    db_session.refresh(session3)
    sessions.append(session3)

    db_session.commit()

    # Batch query all 3 sessions
    session_ids = ",".join(str(s.id) for s in sessions)
    response = client.get(f"/api/v1/sessions/availability?session_ids={session_ids}")

    assert response.status_code == 200
    data = response.json()

    # Validate all sessions returned
    assert len(data) == 3

    # Session 1: Partially booked
    s1_data = data[str(session1.id)]
    assert s1_data["capacity"] == 20
    assert s1_data["booked"] == 10
    assert s1_data["available"] == 10
    assert s1_data["status"] == "available"

    # Session 2: Full
    s2_data = data[str(session2.id)]
    assert s2_data["capacity"] == 15
    assert s2_data["booked"] == 15
    assert s2_data["available"] == 0
    assert s2_data["status"] == "full"

    # Session 3: Empty
    s3_data = data[str(session3.id)]
    assert s3_data["capacity"] == 25
    assert s3_data["booked"] == 0
    assert s3_data["available"] == 25
    assert s3_data["status"] == "available"


def test_availability_invalid_session_ids(client: TestClient):
    """Test error handling for invalid session ID format"""
    response = client.get("/api/v1/sessions/availability?session_ids=abc,def,xyz")

    assert response.status_code == 400
    data = response.json()
    assert "Invalid session IDs format" in data["error"]["message"]


def test_availability_exceeds_limit(client: TestClient):
    """Test error handling for too many sessions (>50)"""
    # Create 51 session IDs
    session_ids = ",".join(str(i) for i in range(1, 52))

    response = client.get(f"/api/v1/sessions/availability?session_ids={session_ids}")

    assert response.status_code == 400
    data = response.json()
    assert "Maximum 50 sessions per request" in data["error"]["message"]
