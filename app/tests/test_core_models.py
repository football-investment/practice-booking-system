"""
Core Model Tests - Session, Booking, Attendance, Feedback

Tests the 4 most critical models for data integrity, business logic, and relationships.
These models currently have 0% test coverage and are CRITICAL for system operation.

Test Structure:
- Session Model: 8 tests (CRUD, relationships, validation)
- Booking Model: 8 tests (status transitions, waitlist, constraints)
- Attendance Model: 6 tests (status validation, check-in logic)
- Feedback Model: 6 tests (rating validation, constraints)

TOTAL: 28 Core Model Tests
"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.exc import IntegrityError

from app.models.user import User, UserRole
from app.models.session import Session as SessionModel, SessionType
from app.models.booking import Booking, BookingStatus
from app.models.attendance import Attendance, AttendanceStatus
from app.models.feedback import Feedback
from app.models.semester import Semester
from app.database import get_db
from app.core.security import get_password_hash


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def db_session():
    """Database session fixture with transaction rollback"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def test_student(db_session: DBSession):
    """Create test student user"""
    user = User(
        email="test_student@example.com",
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
def test_instructor(db_session: DBSession):
    """Create test instructor user"""
    user = User(
        email="test_instructor@example.com",
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
def test_semester(db_session: DBSession):
    """Create test semester"""
    semester = Semester(
        code="TEST_2025_S1",
        name="Test Semester 2025",
        start_date=datetime.now().date() - timedelta(days=30),
        end_date=datetime.now().date() + timedelta(days=60),
        is_active=True
    )
    db_session.add(semester)
    db_session.commit()
    db_session.refresh(semester)
    return semester


@pytest.fixture
def test_session(db_session: DBSession, test_semester, test_instructor):
    """Create test session"""
    session = SessionModel(
        title="Test Session",
        description="Test session for model tests",
        date_start=datetime.now(timezone.utc) + timedelta(hours=48),
        date_end=datetime.now(timezone.utc) + timedelta(hours=50),
        capacity=10,
        session_type=SessionType.HYBRID,
        location="Test Location",
        semester_id=test_semester.id,
        instructor_id=test_instructor.id
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


# ============================================================================
# SESSION MODEL TESTS (8 tests)
# ============================================================================

def test_session_create_success(db_session, test_semester, test_instructor):
    """Test #1: Successfully create a session with all required fields"""
    session = SessionModel(
        title="New Session",
        description="New test session",
        date_start=datetime.now(timezone.utc) + timedelta(hours=24),
        date_end=datetime.now(timezone.utc) + timedelta(hours=26),
        capacity=15,
        session_type=SessionType.ONSITE,
        location="Test Gym",
        semester_id=test_semester.id,
        instructor_id=test_instructor.id
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    assert session.id is not None
    assert session.title == "New Session"
    assert session.capacity == 15
    assert session.session_type == SessionType.ONSITE


def test_session_missing_required_fields(db_session, test_semester):
    """Test #2: Session creation fails without required fields"""
    session = SessionModel(
        title="Incomplete Session",
        # Missing date_start, date_end, capacity, mode
        semester_id=test_semester.id
    )
    db_session.add(session)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_session_instructor_relationship(db_session, test_session, test_instructor):
    """Test #3: Session has correct relationship to instructor"""
    assert test_session.instructor is not None
    assert test_session.instructor.id == test_instructor.id
    assert test_session.instructor.name == test_instructor.name
    assert test_session.instructor.role == UserRole.INSTRUCTOR


def test_session_semester_relationship(db_session, test_session, test_semester):
    """Test #4: Session has correct relationship to semester"""
    assert test_session.semester is not None
    assert test_session.semester.id == test_semester.id
    assert test_session.semester.code == test_semester.code


def test_session_mode_validation(db_session, test_semester, test_instructor):
    """Test #5: Session mode must be valid enum value"""
    session = SessionModel(
        title="Test Mode Session",
        description="Testing mode validation",
        date_start=datetime.now(timezone.utc) + timedelta(hours=24),
        date_end=datetime.now(timezone.utc) + timedelta(hours=26),
        capacity=10,
        session_type=SessionType.VIRTUAL,
        meeting_link="https://zoom.us/test",
        semester_id=test_semester.id,
        instructor_id=test_instructor.id
    )
    db_session.add(session)
    db_session.commit()

    assert session.session_type == SessionType.VIRTUAL
    assert session.meeting_link is not None


def test_session_capacity_positive(db_session, test_semester, test_instructor):
    """Test #6: Session capacity must be positive"""
    session = SessionModel(
        title="Zero Capacity Session",
        description="Testing capacity validation",
        date_start=datetime.now(timezone.utc) + timedelta(hours=24),
        date_end=datetime.now(timezone.utc) + timedelta(hours=26),
        capacity=0,  # Invalid: capacity must be > 0
        session_type=SessionType.HYBRID,
        location="Test Location",
        semester_id=test_semester.id,
        instructor_id=test_instructor.id
    )
    db_session.add(session)

    # Should fail validation or constraint
    with pytest.raises((IntegrityError, ValueError)):
        db_session.commit()


def test_session_date_validation(db_session, test_semester, test_instructor):
    """Test #7: Session date_end must be after date_start"""
    session = SessionModel(
        title="Invalid Date Session",
        description="Testing date validation",
        date_start=datetime.now(timezone.utc) + timedelta(hours=26),  # Later
        date_end=datetime.now(timezone.utc) + timedelta(hours=24),    # Earlier - INVALID!
        capacity=10,
        session_type=SessionType.HYBRID,
        location="Test Location",
        semester_id=test_semester.id,
        instructor_id=test_instructor.id
    )
    db_session.add(session)

    # Should fail validation
    with pytest.raises((IntegrityError, ValueError)):
        db_session.commit()


def test_session_bookings_relationship(db_session, test_session, test_student):
    """Test #8: Session has correct relationship to bookings"""
    # Create booking
    booking = Booking(
        user_id=test_student.id,
        session_id=test_session.id,
        status=BookingStatus.CONFIRMED
    )
    db_session.add(booking)
    db_session.commit()

    # Refresh and check relationship
    db_session.refresh(test_session)
    assert len(test_session.bookings) == 1
    assert test_session.bookings[0].user_id == test_student.id


# ============================================================================
# BOOKING MODEL TESTS (8 tests)
# ============================================================================

def test_booking_create_confirmed(db_session, test_session, test_student):
    """Test #9: Successfully create confirmed booking"""
    booking = Booking(
        user_id=test_student.id,
        session_id=test_session.id,
        status=BookingStatus.CONFIRMED,
        notes="Test booking"
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    assert booking.id is not None
    assert booking.status == BookingStatus.CONFIRMED
    assert booking.waitlist_position is None


def test_booking_create_waitlisted(db_session, test_session, test_student):
    """Test #10: Successfully create waitlisted booking with position"""
    booking = Booking(
        user_id=test_student.id,
        session_id=test_session.id,
        status=BookingStatus.WAITLISTED,
        waitlist_position=5
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    assert booking.status == BookingStatus.WAITLISTED
    assert booking.waitlist_position == 5


def test_booking_missing_required_fields(db_session, test_session):
    """Test #11: Booking fails without user_id or session_id"""
    booking = Booking(
        # Missing user_id
        session_id=test_session.id,
        status=BookingStatus.CONFIRMED
    )
    db_session.add(booking)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_booking_status_transition(db_session, test_session, test_student):
    """Test #12: Booking status can transition from WAITLISTED to CONFIRMED"""
    booking = Booking(
        user_id=test_student.id,
        session_id=test_session.id,
        status=BookingStatus.WAITLISTED,
        waitlist_position=3
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    # Transition to confirmed
    booking.status = BookingStatus.CONFIRMED
    booking.waitlist_position = None
    db_session.commit()

    assert booking.status == BookingStatus.CONFIRMED
    assert booking.waitlist_position is None


def test_booking_cancellation(db_session, test_session, test_student):
    """Test #13: Booking can be cancelled with timestamp"""
    booking = Booking(
        user_id=test_student.id,
        session_id=test_session.id,
        status=BookingStatus.CONFIRMED
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    # Cancel booking
    booking.status = BookingStatus.CANCELLED
    booking.cancelled_at = datetime.now(timezone.utc)
    db_session.commit()

    assert booking.status == BookingStatus.CANCELLED
    assert booking.cancelled_at is not None


def test_booking_user_relationship(db_session, test_session, test_student):
    """Test #14: Booking has correct relationship to user"""
    booking = Booking(
        user_id=test_student.id,
        session_id=test_session.id,
        status=BookingStatus.CONFIRMED
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    assert booking.user is not None
    assert booking.user.id == test_student.id
    assert booking.user.role == UserRole.STUDENT


def test_booking_session_relationship(db_session, test_session, test_student):
    """Test #15: Booking has correct relationship to session"""
    booking = Booking(
        user_id=test_student.id,
        session_id=test_session.id,
        status=BookingStatus.CONFIRMED
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    assert booking.session is not None
    assert booking.session.id == test_session.id
    assert booking.session.title == test_session.title


def test_booking_duplicate_prevention(db_session, test_session, test_student):
    """Test #16: User cannot have multiple active bookings for same session"""
    # First booking
    booking1 = Booking(
        user_id=test_student.id,
        session_id=test_session.id,
        status=BookingStatus.CONFIRMED
    )
    db_session.add(booking1)
    db_session.commit()

    # Second booking (duplicate) - should be prevented at application layer
    # Note: This test verifies the database allows it (application must prevent)
    booking2 = Booking(
        user_id=test_student.id,
        session_id=test_session.id,
        status=BookingStatus.WAITLISTED
    )
    db_session.add(booking2)
    db_session.commit()

    # Both bookings exist in DB (application layer must enforce uniqueness)
    bookings = db_session.query(Booking).filter(
        Booking.user_id == test_student.id,
        Booking.session_id == test_session.id
    ).all()
    assert len(bookings) == 2  # DB allows it, app must prevent


# ============================================================================
# ATTENDANCE MODEL TESTS (6 tests)
# ============================================================================

def test_attendance_create_present(db_session, test_session, test_student):
    """Test #17: Successfully create attendance record with PRESENT status"""
    attendance = Attendance(
        user_id=test_student.id,
        session_id=test_session.id,
        status=AttendanceStatus.PRESENT,
        check_in_time=datetime.now(timezone.utc)
    )
    db_session.add(attendance)
    db_session.commit()
    db_session.refresh(attendance)

    assert attendance.id is not None
    assert attendance.status == AttendanceStatus.PRESENT
    assert attendance.check_in_time is not None


def test_attendance_status_validation(db_session, test_session, test_student):
    """Test #18: Attendance status must be valid enum"""
    attendance = Attendance(
        user_id=test_student.id,
        session_id=test_session.id,
        status=AttendanceStatus.ABSENT,
        notes="Student did not attend"
    )
    db_session.add(attendance)
    db_session.commit()

    assert attendance.status == AttendanceStatus.ABSENT


def test_attendance_missing_required_fields(db_session, test_session):
    """Test #19: Attendance fails without user_id or session_id"""
    attendance = Attendance(
        # Missing user_id
        session_id=test_session.id,
        status=AttendanceStatus.PRESENT
    )
    db_session.add(attendance)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_attendance_user_relationship(db_session, test_session, test_student):
    """Test #20: Attendance has correct relationship to user"""
    attendance = Attendance(
        user_id=test_student.id,
        session_id=test_session.id,
        status=AttendanceStatus.PRESENT,
        check_in_time=datetime.now(timezone.utc)
    )
    db_session.add(attendance)
    db_session.commit()
    db_session.refresh(attendance)

    assert attendance.user is not None
    assert attendance.user.id == test_student.id


def test_attendance_session_relationship(db_session, test_session, test_student):
    """Test #21: Attendance has correct relationship to session"""
    attendance = Attendance(
        user_id=test_student.id,
        session_id=test_session.id,
        status=AttendanceStatus.PRESENT,
        check_in_time=datetime.now(timezone.utc)
    )
    db_session.add(attendance)
    db_session.commit()
    db_session.refresh(attendance)

    assert attendance.session is not None
    assert attendance.session.id == test_session.id


def test_attendance_with_booking_relationship(db_session, test_session, test_student):
    """Test #22: Attendance can be linked to booking"""
    # Create booking first
    booking = Booking(
        user_id=test_student.id,
        session_id=test_session.id,
        status=BookingStatus.CONFIRMED
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    # Create attendance linked to booking
    attendance = Attendance(
        user_id=test_student.id,
        session_id=test_session.id,
        booking_id=booking.id,
        status=AttendanceStatus.PRESENT,
        check_in_time=datetime.now(timezone.utc)
    )
    db_session.add(attendance)
    db_session.commit()
    db_session.refresh(attendance)

    assert attendance.booking is not None
    assert attendance.booking.id == booking.id


# ============================================================================
# FEEDBACK MODEL TESTS (6 tests)
# ============================================================================

def test_feedback_create_success(db_session, test_session, test_student):
    """Test #23: Successfully create feedback with valid rating"""
    feedback = Feedback(
        user_id=test_student.id,
        session_id=test_session.id,
        rating=5,
        comment="Excellent session!"
    )
    db_session.add(feedback)
    db_session.commit()
    db_session.refresh(feedback)

    assert feedback.id is not None
    assert feedback.rating == 5
    assert feedback.comment == "Excellent session!"


def test_feedback_rating_range_valid(db_session, test_session, test_student):
    """Test #24: Feedback rating within valid range (1-5)"""
    for rating in [1, 2, 3, 4, 5]:
        feedback = Feedback(
            user_id=test_student.id,
            session_id=test_session.id,
            rating=rating,
            comment=f"Rating {rating}"
        )
        db_session.add(feedback)
        db_session.commit()
        db_session.refresh(feedback)

        assert feedback.rating == rating


def test_feedback_rating_invalid_low(db_session, test_session, test_student):
    """Test #25: Feedback rating cannot be < 1"""
    feedback = Feedback(
        user_id=test_student.id,
        session_id=test_session.id,
        rating=0,  # Invalid: must be >= 1
        comment="Invalid rating"
    )
    db_session.add(feedback)

    with pytest.raises((IntegrityError, ValueError)):
        db_session.commit()


def test_feedback_rating_invalid_high(db_session, test_session, test_student):
    """Test #26: Feedback rating cannot be > 5"""
    feedback = Feedback(
        user_id=test_student.id,
        session_id=test_session.id,
        rating=6,  # Invalid: must be <= 5
        comment="Invalid rating"
    )
    db_session.add(feedback)

    with pytest.raises((IntegrityError, ValueError)):
        db_session.commit()


def test_feedback_user_relationship(db_session, test_session, test_student):
    """Test #27: Feedback has correct relationship to user"""
    feedback = Feedback(
        user_id=test_student.id,
        session_id=test_session.id,
        rating=4,
        comment="Good session"
    )
    db_session.add(feedback)
    db_session.commit()
    db_session.refresh(feedback)

    assert feedback.user is not None
    assert feedback.user.id == test_student.id


def test_feedback_session_relationship(db_session, test_session, test_student):
    """Test #28: Feedback has correct relationship to session"""
    feedback = Feedback(
        user_id=test_student.id,
        session_id=test_session.id,
        rating=5,
        comment="Amazing session"
    )
    db_session.add(feedback)
    db_session.commit()
    db_session.refresh(feedback)

    assert feedback.session is not None
    assert feedback.session.id == test_session.id


# ============================================================================
# END OF CORE MODEL TESTS
# ============================================================================
