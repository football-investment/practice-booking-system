"""
API test configuration - Uses PostgreSQL test database

Unlike the main conftest.py which uses SQLite for speed,
API tests use PostgreSQL to match production environment
and avoid enum type compatibility issues.
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from app.core.auth import create_access_token

# PostgreSQL test database URL
TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/internship_only_test"


@pytest.fixture(scope="function")
def test_db():
    """
    Create a fresh PostgreSQL test database for each test function.

    Uses a real PostgreSQL database to avoid SQLite enum type issues.
    Cleans up all tables after each test.
    """
    engine = create_engine(TEST_DATABASE_URL)

    # Drop all tables and recreate
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        # Clean up after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """
    FastAPI TestClient with test database dependency override.
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
def admin_token(admin_user: User) -> str:
    """Generate JWT token for admin user."""
    return create_access_token(data={"sub": admin_user.email})
