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
    semester.status = SemesterStatus.READY_FOR_ENROLLMENT
    test_db.commit()
    test_db.refresh(semester)
    return semester


# ============================================================================
# Factory Fixtures (for tests that need dynamic data creation)
# ============================================================================

@pytest.fixture
def user_factory(test_db: Session):
    """
    Factory for creating test users with unique emails.

    Usage:
        user1 = user_factory(name="John", role=UserRole.STUDENT)
        user2 = user_factory(name="Jane", role=UserRole.INSTRUCTOR)
    """
    from app.models.user import User, UserRole
    from datetime import datetime
    import uuid

    def _create_user(
        name: str = "Test User",
        email: str = None,
        role: UserRole = UserRole.STUDENT,
        is_active: bool = True,
        date_of_birth: datetime = None,
        parental_consent: bool = True
    ):
        if email is None:
            email = f"user+{uuid.uuid4().hex[:8]}@test.com"
        if date_of_birth is None:
            date_of_birth = datetime(2000, 1, 1)

        user = User(
            name=name,
            email=email,
            password_hash="test_hash",
            role=role,
            is_active=is_active,
            date_of_birth=date_of_birth,
            parental_consent=parental_consent
        )
        test_db.add(user)
        test_db.flush()
        test_db.refresh(user)
        return user

    return _create_user


@pytest.fixture
def location_factory(test_db: Session):
    """
    Factory for creating test locations (cities).

    Usage:
        location1 = location_factory(city="Budapest")
        location2 = location_factory(city="Vienna", location_code="VIE")
    """
    from app.models.location import Location
    import uuid

    def _create_location(
        name: str = None,
        city: str = None,
        country: str = "Hungary",
        location_code: str = None,
        is_active: bool = True
    ):
        if city is None:
            city = f"Test City {uuid.uuid4().hex[:6]}"
        if name is None:
            name = city  # Use city as name
        if location_code is None:
            location_code = uuid.uuid4().hex[:3].upper()

        location = Location(
            name=name,
            city=city,
            country=country,
            location_code=location_code,
            is_active=is_active
        )
        test_db.add(location)
        test_db.flush()
        test_db.refresh(location)
        return location

    return _create_location


@pytest.fixture
def campus_factory(test_db: Session, location_factory):
    """
    Factory for creating test campuses.

    Usage:
        campus1 = campus_factory(name="Main Campus")
        campus2 = campus_factory(name="East Campus", venue="Stadium")
    """
    from app.models.campus import Campus
    import uuid

    def _create_campus(
        name: str = None,
        venue: str = "Test Venue",
        address: str = "123 Test St",
        is_active: bool = True,
        location_id: int = None
    ):
        if name is None:
            name = f"Test Campus {uuid.uuid4().hex[:6]}"

        # Create location if not provided
        if location_id is None:
            location = location_factory()
            location_id = location.id

        campus = Campus(
            name=name,
            location_id=location_id,
            venue=venue,
            address=address,
            is_active=is_active
        )
        test_db.add(campus)
        test_db.flush()
        test_db.refresh(campus)
        return campus

    return _create_campus


@pytest.fixture
def team_factory(test_db: Session):
    """
    Factory for creating test teams.

    Usage:
        team1 = team_factory(name="Team Alpha")
        team2 = team_factory(name="Team Beta", code="BETA")
    """
    from app.models.team import Team
    import uuid

    def _create_team(
        name: str = None,
        code: str = None,
        captain_user_id: int = None,
        specialization_type: str = None,
        is_active: bool = True
    ):
        if name is None:
            name = f"Test Team {uuid.uuid4().hex[:6]}"
        if code is None:
            code = f"T{uuid.uuid4().hex[:4].upper()}"

        team = Team(
            name=name,
            code=code,
            captain_user_id=captain_user_id,
            specialization_type=specialization_type,
            is_active=is_active
        )
        test_db.add(team)
        test_db.flush()
        test_db.refresh(team)
        return team

    return _create_team
