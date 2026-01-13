"""
Pytest configuration and shared fixtures.

This file is automatically discovered by pytest and provides:
- Database setup/teardown
- Test data fixtures
- Authentication helpers
- Common test utilities
"""

import pytest
from datetime import date, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.models.specialization import SpecializationType
from app.models.semester import Semester, SemesterStatus
from app.models.session import Session as SessionModel, SessionType
from app.models.booking import Booking, BookingStatus
from app.models.instructor_assignment import InstructorAssignmentRequest, AssignmentRequestStatus
from app.models.coupon import Coupon, CouponUsage, CouponType
from app.core.security import get_password_hash
from app.core.auth import create_access_token


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def test_db():
    """
    Create a fresh test database for each test function.

    Uses SQLite in-memory database for speed.
    Automatically tears down after test completes.

    Usage:
        def test_something(test_db):
            user = User(email="test@example.com")
            test_db.add(user)
            test_db.commit()
    """
    # Create in-memory SQLite database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """
    FastAPI TestClient with test database dependency override.

    Usage:
        def test_api_endpoint(client):
            response = client.get("/api/v1/sessions/")
            assert response.status_code == 200
    """
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ============================================================================
# USER FIXTURES
# ============================================================================

@pytest.fixture
def admin_user(test_db: Session) -> User:
    """Create and return an admin user."""
    user = User(
        email="admin@lfa.com",
        name="Admin User",
        password_hash=get_password_hash("admin123"),
        role=UserRole.ADMIN,
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def instructor_user(test_db: Session) -> User:
    """Create and return an instructor user."""
    user = User(
        email="instructor@lfa.com",
        name="Instructor User",
        password_hash=get_password_hash("instructor123"),
        role=UserRole.INSTRUCTOR,
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def student_user(test_db: Session) -> User:
    """Create and return a student user."""
    user = User(
        email="student@lfa.com",
        name="Student User",
        password_hash=get_password_hash("student123"),
        role=UserRole.STUDENT,
        is_active=True,
        date_of_birth=date(2005, 1, 15)  # 18 years old
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def student_users(test_db: Session) -> list[User]:
    """Create and return 10 student users for bulk testing."""
    students = []
    for i in range(10):
        user = User(
            email=f"student{i+1}@lfa.com",
            name=f"Student {i+1}",
            password_hash=get_password_hash("student123"),
            role=UserRole.STUDENT,
            is_active=True,
            date_of_birth=date(2005, 1, i+1)
        )
        test_db.add(user)
        students.append(user)

    test_db.commit()
    for student in students:
        test_db.refresh(student)

    return students


# ============================================================================
# AUTHENTICATION FIXTURES
# ============================================================================

@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Generate JWT token for admin user."""
    return create_access_token(data={"sub": admin_user.email})


@pytest.fixture
def instructor_token(instructor_user: User) -> str:
    """Generate JWT token for instructor user."""
    return create_access_token(data={"sub": instructor_user.email})


@pytest.fixture
def student_token(student_user: User) -> str:
    """Generate JWT token for student user."""
    return create_access_token(data={"sub": student_user.email})


# ============================================================================
# TOURNAMENT FIXTURES
# ============================================================================

@pytest.fixture
def tournament_date() -> date:
    """Standard tournament date for testing (7 days from now)."""
    return date.today() + timedelta(days=7)


@pytest.fixture
def tournament_semester(test_db: Session, tournament_date: date) -> Semester:
    """
    Create a tournament semester in SEEKING_INSTRUCTOR status.

    This is the initial state after admin creates a tournament.
    """
    semester = Semester(
        code=f"TOURN-{tournament_date.strftime('%Y%m%d')}",
        name="Test Tournament",
        start_date=tournament_date,
        end_date=tournament_date,  # 1-day tournament
        is_active=True,
        status=SemesterStatus.SEEKING_INSTRUCTOR,
        master_instructor_id=None,  # No instructor yet
        specialization_type=SpecializationType.LFA_PLAYER_YOUTH.value,
        age_group="YOUTH"
    )
    test_db.add(semester)
    test_db.commit()
    test_db.refresh(semester)
    return semester


@pytest.fixture
def tournament_semester_with_instructor(
    test_db: Session,
    tournament_date: date,
    instructor_user: User
) -> Semester:
    """
    Create a tournament semester in READY_FOR_ENROLLMENT status.

    This is the state after instructor accepts the assignment.
    """
    semester = Semester(
        code=f"TOURN-{tournament_date.strftime('%Y%m%d')}-READY",
        name="Ready Tournament",
        start_date=tournament_date,
        end_date=tournament_date,
        is_active=True,
        status=SemesterStatus.READY_FOR_ENROLLMENT,
        master_instructor_id=instructor_user.id,
        specialization_type=SpecializationType.LFA_PLAYER_YOUTH.value,
        age_group="YOUTH"
    )
    test_db.add(semester)
    test_db.commit()
    test_db.refresh(semester)
    return semester


@pytest.fixture
def tournament_sessions(
    test_db: Session,
    tournament_semester: Semester,
    tournament_date: date
) -> list[SessionModel]:
    """
    Create 3 tournament sessions for testing.

    Sessions at 09:00, 11:00, 14:00.
    """
    sessions = []
    times = ["09:00", "11:00", "14:00"]

    for i, time_str in enumerate(times):
        start_time = datetime.strptime(f"{tournament_date} {time_str}", "%Y-%m-%d %H:%M")
        end_time = start_time + timedelta(minutes=90)

        session = SessionModel(
            title=f"Tournament Game {i+1}",
            description=f"Game {i+1} description",
            date_start=start_time,
            date_end=end_time,
            session_type=SessionType.on_site,
            capacity=20,
            instructor_id=None,  # Will be assigned when instructor accepts
            semester_id=tournament_semester.id,
            credit_cost=1,
            is_tournament_game=True,
            game_type=f"Round {i+1}"
        )
        test_db.add(session)
        sessions.append(session)

    test_db.commit()
    for session in sessions:
        test_db.refresh(session)

    return sessions


@pytest.fixture
def tournament_session_with_bookings(
    test_db: Session,
    tournament_semester_with_instructor: Semester,
    tournament_date: date,
    student_users: list[User]
) -> SessionModel:
    """
    Create a tournament session with 5 confirmed bookings.

    Useful for testing attendance marking.
    """
    start_time = datetime.strptime(f"{tournament_date} 10:00", "%Y-%m-%d %H:%M")
    end_time = start_time + timedelta(minutes=90)

    session = SessionModel(
        title="Tournament Final",
        description="Championship final game",
        date_start=start_time,
        date_end=end_time,
        session_type=SessionType.on_site,
        capacity=20,
        instructor_id=tournament_semester_with_instructor.master_instructor_id,
        semester_id=tournament_semester_with_instructor.id,
        credit_cost=1,
        is_tournament_game=True,
        game_type="Final"
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    # Add 5 bookings
    for student in student_users[:5]:
        booking = Booking(
            user_id=student.id,
            session_id=session.id,
            status=BookingStatus.CONFIRMED
        )
        test_db.add(booking)

    test_db.commit()

    return session


@pytest.fixture
def instructor_assignment_request(
    test_db: Session,
    tournament_semester: Semester,
    instructor_user: User,
    admin_user: User
) -> InstructorAssignmentRequest:
    """
    Create a pending instructor assignment request.

    Admin has invited instructor, but instructor hasn't responded yet.
    """
    request = InstructorAssignmentRequest(
        semester_id=tournament_semester.id,
        instructor_id=instructor_user.id,
        requested_by=admin_user.id,
        status=AssignmentRequestStatus.PENDING,
        request_message=f"Please lead the '{tournament_semester.name}' tournament"
    )
    test_db.add(request)
    test_db.commit()
    test_db.refresh(request)
    return request


# ============================================================================
# UTILITY FIXTURES
# ============================================================================

@pytest.fixture
def today() -> date:
    """Current date for testing."""
    return date.today()


@pytest.fixture
def future_date() -> date:
    """Future date (30 days from now)."""
    return date.today() + timedelta(days=30)


@pytest.fixture
def past_date() -> date:
    """Past date (30 days ago)."""
    return date.today() - timedelta(days=30)
