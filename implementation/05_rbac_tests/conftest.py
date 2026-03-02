#!/usr/bin/env python3
"""
RBAC Testing Fixtures - User Creation and JWT Token Management
"""

import sys
import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from typing import Dict

# Import app components
from app.main import app
from app.models.user import User, UserRole
from app.core.auth import create_access_token
from app.database import get_db

from jose import jwt
from app.config import settings
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

DB_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

def get_db_session():
    """Get database session for testing"""
    engine = create_engine(DB_URL)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


# =============================================================================
# USER CREATION FIXTURES
# =============================================================================

@pytest.fixture(scope="function")
def db():
    """Database session fixture"""
    session = get_db_session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def test_users(db: Session):
    """
    Create test users with different roles for RBAC testing

    Returns:
        dict: {
            'admin': User object with ADMIN role,
            'instructor': User object with INSTRUCTOR role,
            'student1': User object with STUDENT role,
            'student2': User object with STUDENT role
        }
    """
    # Clean up any existing test users and their dependencies
    # First delete all dependent records (attendance -> bookings -> sessions, then licenses, then users)
    db.execute(text("""
        DELETE FROM attendance WHERE user_id IN (
            SELECT id FROM users WHERE email IN (
                'admin.rbac@test.com', 'instructor.rbac@test.com',
                'student1.rbac@test.com', 'student2.rbac@test.com'
            )
        )
    """))
    db.execute(text("""
        DELETE FROM bookings WHERE user_id IN (
            SELECT id FROM users WHERE email IN (
                'admin.rbac@test.com', 'instructor.rbac@test.com',
                'student1.rbac@test.com', 'student2.rbac@test.com'
            )
        )
    """))
    db.execute(text("""
        DELETE FROM sessions WHERE instructor_id IN (
            SELECT id FROM users WHERE email IN (
                'admin.rbac@test.com', 'instructor.rbac@test.com',
                'student1.rbac@test.com', 'student2.rbac@test.com'
            )
        )
    """))
    db.execute(text("""
        DELETE FROM lfa_player_licenses WHERE user_id IN (
            SELECT id FROM users WHERE email IN (
                'admin.rbac@test.com', 'instructor.rbac@test.com',
                'student1.rbac@test.com', 'student2.rbac@test.com'
            )
        )
    """))
    db.execute(text("""
        DELETE FROM gancuju_licenses WHERE user_id IN (
            SELECT id FROM users WHERE email IN (
                'admin.rbac@test.com', 'instructor.rbac@test.com',
                'student1.rbac@test.com', 'student2.rbac@test.com'
            )
        )
    """))
    db.execute(text("""
        DELETE FROM internship_licenses WHERE user_id IN (
            SELECT id FROM users WHERE email IN (
                'admin.rbac@test.com', 'instructor.rbac@test.com',
                'student1.rbac@test.com', 'student2.rbac@test.com'
            )
        )
    """))
    db.execute(text("""
        DELETE FROM coach_licenses WHERE user_id IN (
            SELECT id FROM users WHERE email IN (
                'admin.rbac@test.com', 'instructor.rbac@test.com',
                'student1.rbac@test.com', 'student2.rbac@test.com'
            )
        )
    """))
    # Now safe to delete users
    db.execute(text("""
        DELETE FROM users WHERE email IN (
            'admin.rbac@test.com',
            'instructor.rbac@test.com',
            'student1.rbac@test.com',
            'student2.rbac@test.com'
        )
    """))
    db.commit()

    # Create admin user
    admin = User(
        email="admin.rbac@test.com",
        name="Admin Test User",
        password_hash="$2b$12$dummy_hashed_password",  # Dummy hash
        role=UserRole.ADMIN,
        is_active=True,
        onboarding_completed=True,
        created_at=datetime.utcnow()
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    # Create instructor user
    instructor = User(
        email="instructor.rbac@test.com",
        name="Instructor Test User",
        password_hash="$2b$12$dummy_hashed_password",
        role=UserRole.INSTRUCTOR,
        is_active=True,
        onboarding_completed=True,
        created_at=datetime.utcnow()
    )
    db.add(instructor)
    db.commit()
    db.refresh(instructor)

    # Create student1
    student1 = User(
        email="student1.rbac@test.com",
        name="Student 1 Test User",
        password_hash="$2b$12$dummy_hashed_password",
        role=UserRole.STUDENT,
        is_active=True,
        onboarding_completed=True,
        specialization="LFA_PLAYER_YOUTH",
        created_at=datetime.utcnow()
    )
    db.add(student1)
    db.commit()
    db.refresh(student1)

    # Create student2
    student2 = User(
        email="student2.rbac@test.com",
        name="Student 2 Test User",
        password_hash="$2b$12$dummy_hashed_password",
        role=UserRole.STUDENT,
        is_active=True,
        onboarding_completed=True,
        specialization="GANCUJU_PLAYER",
        created_at=datetime.utcnow()
    )
    db.add(student2)
    db.commit()
    db.refresh(student2)

    users = {
        'admin': admin,
        'instructor': instructor,
        'student1': student1,
        'student2': student2
    }

    yield users

    # Cleanup after test
    db.execute(text("""
        DELETE FROM users WHERE email IN (
            'admin.rbac@test.com',
            'instructor.rbac@test.com',
            'student1.rbac@test.com',
            'student2.rbac@test.com'
        )
    """))
    db.commit()


# =============================================================================
# JWT TOKEN FIXTURES
# =============================================================================

def get_auth_headers(user: User) -> Dict[str, str]:
    """
    Generate JWT authorization headers for a user

    Args:
        user: User object to generate token for

    Returns:
        dict: {"Authorization": "Bearer <token>"}
    """
    token = create_access_token(data={"sub": user.email})
    return {"Authorization": f"Bearer {token}"}


def get_expired_token(user: User) -> str:
    """
    Generate an EXPIRED JWT token for testing token expiry

    Args:
        user: User object

    Returns:
        str: Expired JWT token
    """
    expire = datetime.utcnow() - timedelta(hours=24)  # Expired 24 hours ago
    to_encode = {
        "sub": user.email,
        "exp": expire
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def get_forged_token(fake_email: str, fake_role: str) -> str:
    """
    Generate a FORGED JWT token with fake role (for testing security)

    Args:
        fake_email: Email to put in token
        fake_role: Role to claim (e.g., "admin")

    Returns:
        str: Forged JWT token (will fail signature validation)
    """
    expire = datetime.utcnow() + timedelta(hours=1)
    to_encode = {
        "sub": fake_email,
        "role": fake_role,
        "exp": expire
    }

    # Use WRONG secret key (forged)
    forged_jwt = jwt.encode(
        to_encode,
        "FAKE_SECRET_KEY_12345",
        algorithm="HS256"
    )
    return forged_jwt


@pytest.fixture(scope="function")
def auth_headers(test_users):
    """
    Generate auth headers for all test users

    Returns:
        dict: {
            'admin': {"Authorization": "Bearer <admin_token>"},
            'instructor': {"Authorization": "Bearer <instructor_token>"},
            'student1': {"Authorization": "Bearer <student1_token>"},
            'student2': {"Authorization": "Bearer <student2_token>"}
        }
    """
    return {
        'admin': get_auth_headers(test_users['admin']),
        'instructor': get_auth_headers(test_users['instructor']),
        'student1': get_auth_headers(test_users['student1']),
        'student2': get_auth_headers(test_users['student2'])
    }


# =============================================================================
# API CLIENT FIXTURE
# =============================================================================

@pytest.fixture(scope="function")
def client(db: Session):
    """
    FastAPI TestClient for making API requests
    Overrides the app's database dependency to use the test database

    Returns:
        TestClient: FastAPI test client
    """
    # Override the get_db dependency to use our test database
    def override_get_db():
        try:
            yield db
        finally:
            pass  # Session managed by db fixture

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    yield client

    # Clean up override
    app.dependency_overrides.clear()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def cleanup_test_licenses(db: Session, user_id: int):
    """
    Clean up all licenses for a test user

    Args:
        db: Database session
        user_id: User ID to clean up
    """
    db.execute(text(f"DELETE FROM lfa_player_licenses WHERE user_id = {user_id}"))
    db.execute(text(f"DELETE FROM gancuju_licenses WHERE user_id = {user_id}"))
    db.execute(text(f"DELETE FROM internship_licenses WHERE user_id = {user_id}"))
    db.execute(text(f"DELETE FROM coach_licenses WHERE user_id = {user_id}"))
    db.commit()


def create_test_license(db: Session, user_id: int, spec_type: str):
    """
    Helper to create a test license for RBAC testing

    Args:
        db: Database session
        user_id: User ID
        spec_type: 'lfa_player', 'gancuju', 'internship', or 'coach'

    Returns:
        int: License ID
    """
    if spec_type == 'lfa_player':
        result = db.execute(text(f"""
            INSERT INTO lfa_player_licenses (user_id, age_group, is_active)
            VALUES ({user_id}, 'YOUTH', true)
            RETURNING id
        """))
    elif spec_type == 'gancuju':
        result = db.execute(text(f"""
            INSERT INTO gancuju_licenses (user_id, current_level, is_active)
            VALUES ({user_id}, 1, true)
            RETURNING id
        """))
    elif spec_type == 'internship':
        result = db.execute(text(f"""
            INSERT INTO internship_licenses (user_id, current_level, total_xp, expires_at, is_active)
            VALUES ({user_id}, 1, 0, NOW() + INTERVAL '1 year', true)
            RETURNING id
        """))
    elif spec_type == 'coach':
        result = db.execute(text(f"""
            INSERT INTO coach_licenses (user_id, current_level, expires_at, is_active)
            VALUES ({user_id}, 1, NOW() + INTERVAL '2 years', true)
            RETURNING id
        """))
    else:
        raise ValueError(f"Unknown spec_type: {spec_type}")

    db.commit()
    license_id = result.fetchone()[0]
    return license_id


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================

def pytest_configure(config):
    """Pytest configuration"""
    print("\n" + "="*70)
    print("🔒 RBAC TESTING SUITE - Role-Based Access Control Validation")
    print("="*70)
    print("Testing security permissions for:")
    print("  👑 ADMIN - Full system access")
    print("  👨‍🏫 INSTRUCTOR - Teaching operations")
    print("  👨‍🎓 STUDENT - Own data only")
    print("="*70 + "\n")
