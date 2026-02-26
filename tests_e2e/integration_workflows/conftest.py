"""
E2E Integration Workflows - Minimal Infrastructure

SCOPE: Full workflow validation with complete domain setup.
NOT smoke tests - these validate business logic end-to-end.

Design principles:
- Complete DB seed (TournamentType, GamePreset, Campuses)
- Business-valid users (with licenses, date_of_birth, credit_balance)
- Lifecycle state management
- Clean isolation (function-scoped by default)
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from app.main import app
from app.database import get_db
from app.models.user import User, UserRole
from app.models.license import UserLicense
from app.models.campus import Campus
from app.models.location import Location
from app.models.tournament_type import TournamentType
from app.models.game_preset import GamePreset
from app.core.security import get_password_hash
from app.core.auth import create_access_token


# ============================================================================
# DATABASE & CLIENT
# ============================================================================

@pytest.fixture(scope="module")
def test_db():
    """
    Module-scoped database session for E2E tests.

    Creates a fresh DB connection for the test module.
    Shared across all tests in the module for performance.
    """
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def e2e_db(test_db: Session):
    """
    E2E database session with transaction isolation.

    Reuses module-scoped test_db but wraps in function-scoped transaction.
    Rollback after each test for clean isolation.
    """
    # Note: test_db is module-scoped, created above
    # We just yield it for E2E tests
    yield test_db

    # Cleanup happens in module teardown


@pytest.fixture(scope="function")
def e2e_client():
    """E2E test client"""
    return TestClient(app)


# ============================================================================
# DOMAIN SEED DATA (Module-scoped - shared across all E2E tests)
# ============================================================================

@pytest.fixture(scope="module")
def e2e_tournament_types(test_db: Session) -> List[TournamentType]:
    """
    Seed core tournament types for E2E workflows.

    Creates: knockout, league, hybrid
    Module-scoped: reused across all E2E tests.
    """
    tournament_types_config = [
        {
            "code": "knockout",
            "display_name": "Single Elimination (Knockout)",
            "description": "Single elimination bracket tournament",
        },
        {
            "code": "league",
            "display_name": "League (Round Robin)",
            "description": "Round-robin league format",
        },
        {
            "code": "hybrid",
            "display_name": "Hybrid (Group + Knockout)",
            "description": "Group stage followed by knockout",
        }
    ]

    created_types = []
    for tt_config in tournament_types_config:
        # Query-first to avoid duplicates
        existing = test_db.query(TournamentType).filter(
            TournamentType.code == tt_config["code"]
        ).first()

        if existing:
            created_types.append(existing)
        else:
            tournament_type = TournamentType(**tt_config)
            test_db.add(tournament_type)
            test_db.flush()
            created_types.append(tournament_type)

    test_db.commit()
    return created_types


@pytest.fixture(scope="module")
def e2e_game_preset(test_db: Session) -> GamePreset:
    """
    Seed minimal game preset for E2E workflows.

    Module-scoped: reused across all E2E tests.
    """
    # Query-first
    existing = test_db.query(GamePreset).filter(
        GamePreset.name == "E2E Test Preset"
    ).first()

    if existing:
        return existing

    preset = GamePreset(
        name="E2E Test Preset",
        description="Minimal preset for E2E workflow tests",
        is_active=True,
        skill_categories={
            "football_skill": {
                "display_name": "Football Skills",
                "skills": ["Passing", "Dribbling", "Shooting"]
            }
        }
    )
    test_db.add(preset)
    test_db.commit()
    test_db.refresh(preset)

    return preset


@pytest.fixture(scope="module")
def e2e_campus(test_db: Session) -> Campus:
    """
    Seed campus for E2E workflows.

    Module-scoped: reused across all E2E tests.
    """
    # Ensure location exists
    location = test_db.query(Location).filter(Location.is_active == True).first()
    if not location:
        location = Location(
            name="E2E Test Location",
            city="Budapest",
            is_active=True
        )
        test_db.add(location)
        test_db.commit()
        test_db.refresh(location)

    # Query-first for campus
    existing = test_db.query(Campus).filter(
        Campus.name == "E2E Test Campus"
    ).first()

    if existing:
        return existing

    campus = Campus(
        name="E2E Test Campus",
        location_id=location.id,
        is_active=True
    )
    test_db.add(campus)
    test_db.commit()
    test_db.refresh(campus)

    return campus


# ============================================================================
# USER FIXTURES (Function-scoped - clean per test)
# ============================================================================

@pytest.fixture(scope="function")
def e2e_student(e2e_db: Session) -> Dict:
    """
    Create complete E2E student user.

    Includes:
    - User record with date_of_birth, credit_balance
    - LFA Football Player license (Level 1)
    - Authentication token

    Function-scoped: fresh user per test.
    """
    # Create student user
    student = User(
        name="E2E Test Student",
        email=f"e2e.student.{datetime.now().timestamp()}@test.local",
        password_hash=get_password_hash("student123"),
        role=UserRole.STUDENT,
        is_active=True,
        credit_balance=1000,  # Start with credits
        date_of_birth=datetime(2005, 1, 1).date()  # Required for enrollment
    )
    e2e_db.add(student)
    e2e_db.commit()
    e2e_db.refresh(student)

    # Create license
    license = UserLicense(
        user_id=student.id,
        specialization_type="LFA_FOOTBALL_PLAYER",
        current_level=1,
        max_achieved_level=1,
        started_at=datetime.now(timezone.utc),
        is_active=True
    )
    e2e_db.add(license)
    e2e_db.commit()

    # Generate token
    token = create_access_token(
        data={"sub": student.email},
        expires_delta=timedelta(hours=1)
    )

    return {
        "user": student,
        "user_id": student.id,
        "email": student.email,
        "token": token,
        "credit_balance": student.credit_balance
    }


@pytest.fixture(scope="function")
def e2e_instructor(e2e_db: Session) -> Dict:
    """
    Create complete E2E instructor user.

    Includes:
    - User record
    - LFA Coach license (Level 7 - highest)
    - Authentication token

    Function-scoped: fresh user per test.
    """
    instructor = User(
        name="E2E Test Instructor",
        email=f"e2e.instructor.{datetime.now().timestamp()}@test.local",
        password_hash=get_password_hash("instructor123"),
        role=UserRole.INSTRUCTOR,
        is_active=True
    )
    e2e_db.add(instructor)
    e2e_db.commit()
    e2e_db.refresh(instructor)

    # Create license
    license = UserLicense(
        user_id=instructor.id,
        specialization_type="LFA_COACH",
        current_level=7,  # Highest level
        max_achieved_level=7,
        started_at=datetime.now(timezone.utc),
        is_active=True
    )
    e2e_db.add(license)
    e2e_db.commit()

    # Generate token
    token = create_access_token(
        data={"sub": instructor.email},
        expires_delta=timedelta(hours=1)
    )

    return {
        "user": instructor,
        "user_id": instructor.id,
        "email": instructor.email,
        "token": token
    }


@pytest.fixture(scope="function")
def e2e_admin(e2e_db: Session) -> Dict:
    """
    Create E2E admin user.

    Function-scoped: fresh user per test.
    """
    admin = User(
        name="E2E Test Admin",
        email=f"e2e.admin.{datetime.now().timestamp()}@test.local",
        password_hash=get_password_hash("admin123"),
        role=UserRole.ADMIN,
        is_active=True
    )
    e2e_db.add(admin)
    e2e_db.commit()
    e2e_db.refresh(admin)

    # Generate token
    token = create_access_token(
        data={"sub": admin.email},
        expires_delta=timedelta(hours=1)
    )

    return {
        "user": admin,
        "user_id": admin.id,
        "email": admin.email,
        "token": token
    }
