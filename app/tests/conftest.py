import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure we're in testing mode before importing app
os.environ["TESTING"] = "true"

from ..main import app
from ..database import get_db, Base
from ..models.user import User, UserRole
from ..core.security import get_password_hash
from ..config import settings

# Create test database - Use PostgreSQL for compatibility with production
# PostgreSQL supports all schema features (CHECK constraints, array types, etc.)
# Use a separate test database to avoid conflicts with development data
# Respect DATABASE_URL from environment (for CI), fallback to local test DB
SQLALCHEMY_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/test_tournament_enrollment"
)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine"""
    # In CI: migrations + seeding already ran - don't drop tables!
    # In local: assume migrations have been run (alembic upgrade head)
    # Only create tables if they don't exist (for local dev convenience)
    if not os.environ.get("CI"):  # Only in local dev
        Base.metadata.create_all(bind=engine, checkfirst=True)
    yield engine
    # Don't drop tables in CI - preserve for debugging


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create test database session"""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create test client"""
    # Verify testing mode is enabled
    assert settings.TESTING == True, "Tests should run with TESTING=True"
    assert settings.ENABLE_RATE_LIMITING == False, "Rate limiting should be disabled during testing"
    
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session):
    """Create test admin user"""
    user = User(
        name="Admin User",
        email="admin@test.com",
        password_hash=get_password_hash("admin123"),
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def instructor_user(db_session):
    """Create test instructor user"""
    user = User(
        name="Instructor User",
        email="instructor@test.com",
        password_hash=get_password_hash("instructor123"),
        role=UserRole.INSTRUCTOR,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def student_user(db_session):
    """Create test student user"""
    user = User(
        name="Student User",
        email="student@test.com",
        password_hash=get_password_hash("student123"),
        role=UserRole.STUDENT,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def student_users(db_session):
    """Create test student users (4 students for cancellation tests)"""
    users = []
    for i in range(1, 5):
        user = User(
            name=f"Student User {i}",
            email=f"student{i}@test.com",
            password_hash=get_password_hash(f"student{i}23"),
            role=UserRole.STUDENT,
            is_active=True,
            onboarding_completed=True
        )
        db_session.add(user)
        users.append(user)

    db_session.commit()
    for user in users:
        db_session.refresh(user)
    return users


@pytest.fixture
def admin_token(client, admin_user):
    """Get access token for admin user"""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "admin123"}
    )
    return response.json()["access_token"]


@pytest.fixture
def instructor_token(client, instructor_user):
    """Get access token for instructor user"""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "instructor@test.com", "password": "instructor123"}
    )
    return response.json()["access_token"]


@pytest.fixture
def student_token(client, student_user):
    """Get access token for student user"""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "student@test.com", "password": "student123"}
    )
    return response.json()["access_token"]