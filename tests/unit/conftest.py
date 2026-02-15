"""
Unit Test Fixtures

Provides transactional database fixtures with automatic rollback.
Ensures test isolation - no test pollutes database state for others.

Uses nested transactions (SAVEPOINT) to allow test code to commit
while still rolling back all changes at teardown.
"""

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from app.database import engine


@pytest.fixture(scope="function")
def postgres_db():
    """
    PostgreSQL database session with transactional rollback.

    Each test gets a fresh transactional session. All changes made
    during the test are automatically rolled back at teardown.

    Uses nested transactions (SAVEPOINT) pattern to allow test code
    to call db.commit() without breaking isolation.

    How it works:
        1. Outer transaction begins (will be rolled back)
        2. Nested SAVEPOINT transaction begins
        3. Test executes - can commit (only commits SAVEPOINT)
        4. After commit, new SAVEPOINT automatically created
        5. Outer transaction rollback at teardown (undo everything)

    This ensures complete test isolation - no database pollution.
    """
    # Create connection and start outer transaction
    connection = engine.connect()
    transaction = connection.begin()

    # Create session bound to this connection
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestSessionLocal()

    # Start nested transaction (SAVEPOINT)
    nested = connection.begin_nested()

    # When test code calls session.commit(), it only commits the SAVEPOINT
    # This event listener automatically creates a new SAVEPOINT afterward
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            # Restart the SAVEPOINT
            session.begin_nested()

    try:
        yield session
    finally:
        session.close()

        # Rollback outer transaction (undo all changes from test)
        if transaction.is_active:
            transaction.rollback()

        connection.close()


@pytest.fixture
def test_db(postgres_db: Session):
    """
    Alias for postgres_db fixture for backward compatibility.

    Many tests were written expecting 'test_db' fixture.
    This provides that interface while delegating to postgres_db.
    """
    return postgres_db


# ============================================================================
# Tournament Test Fixtures
# ============================================================================

@pytest.fixture
def tournament_date():
    """
    Fixture providing a future tournament date.

    Returns a date 7 days in the future to avoid date-based validation issues.
    """
    from datetime import date, timedelta
    return date.today() + timedelta(days=7)


@pytest.fixture
def tournament_semester(test_db: Session, tournament_date):
    """
    Fixture providing a pre-created tournament semester.

    Creates a basic tournament semester with required fields.
    All changes rolled back after test completion.
    """
    from app.services.tournament.core import create_tournament_semester
    from app.models.specialization import SpecializationType

    semester = create_tournament_semester(
        db=test_db,
        tournament_date=tournament_date,
        name="Test Tournament",
        specialization_type=SpecializationType.LFA_PLAYER_YOUTH
    )
    return semester


@pytest.fixture
def tournament_sessions(test_db: Session, tournament_semester, tournament_date):
    """
    Fixture providing pre-created tournament sessions.

    Creates 3 tournament sessions for the tournament semester.
    All changes rolled back after test completion.
    """
    from app.services.tournament.core import create_tournament_sessions

    session_configs = [
        {"time": "10:00", "title": "Morning Session", "capacity": 20},
        {"time": "12:00", "title": "Afternoon Session", "capacity": 20},
        {"time": "14:00", "title": "Evening Session", "capacity": 20},
    ]

    sessions = create_tournament_sessions(
        db=test_db,
        semester_id=tournament_semester.id,
        session_configs=session_configs,
        tournament_date=tournament_date
    )
    return sessions


@pytest.fixture
def tournament_session_with_bookings(test_db: Session, tournament_semester, tournament_date):
    """
    Fixture providing a tournament session with pre-created bookings.

    Creates 1 session with 5 confirmed bookings.
    All changes rolled back after test completion.
    """
    from app.services.tournament.core import create_tournament_sessions
    from app.models.booking import Booking, BookingStatus
    from app.models.user import User, UserRole
    import uuid

    # Create session
    session_configs = [{"time": "10:00", "title": "Test Session", "capacity": 20}]
    sessions = create_tournament_sessions(
        db=test_db,
        semester_id=tournament_semester.id,
        session_configs=session_configs,
        tournament_date=tournament_date
    )
    session = sessions[0]

    # Create 5 test users and bookings
    for i in range(5):
        user = User(
            email=f"testuser{i}+{uuid.uuid4().hex[:8]}@test.com",
            name=f"Test User {i}",
            password_hash="test_hash",
            role=UserRole.STUDENT
        )
        test_db.add(user)
        test_db.flush()

        booking = Booking(
            session_id=session.id,
            user_id=user.id,
            status=BookingStatus.CONFIRMED
        )
        test_db.add(booking)

    test_db.commit()
    return session


@pytest.fixture
def student_user(test_db: Session):
    """
    Fixture providing a test student user.

    Creates a basic student user for enrollment tests.
    All changes rolled back after test completion.
    """
    from app.models.user import User, UserRole
    import uuid

    user = User(
        email=f"student+{uuid.uuid4().hex[:8]}@test.com",
        name="Test Student",
        password_hash="test_hash",
        role=UserRole.STUDENT
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def tournament_semester_with_instructor(test_db: Session, tournament_date):
    """
    Fixture providing a tournament semester with assigned instructor.

    Creates a tournament with master instructor assigned (READY status).
    All changes rolled back after test completion.
    """
    from app.services.tournament.core import create_tournament_semester
    from app.models.specialization import SpecializationType
    from app.models.user import User, UserRole
    from app.models.semester import SemesterStatus
    import uuid

    # Create instructor user
    instructor = User(
        email=f"instructor+{uuid.uuid4().hex[:8]}@test.com",
        name="Test Instructor",
        password_hash="test_hash",
        role=UserRole.INSTRUCTOR
    )
    test_db.add(instructor)
    test_db.flush()

    # Create tournament
    semester = create_tournament_semester(
        db=test_db,
        tournament_date=tournament_date,
        name="Ready Tournament",
        specialization_type=SpecializationType.LFA_PLAYER_YOUTH
    )

    # Assign instructor
    semester.master_instructor_id = instructor.id
    semester.status = SemesterStatus.READY
    test_db.commit()
    test_db.refresh(semester)
    return semester
