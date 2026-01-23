"""
Integration Test Fixtures

Provides PostgreSQL database fixtures for integration testing.
"""

import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal, get_db
from app.models.user import User
from app.core.security import get_password_hash


# ============================================================================
# POSTGRESQL DATABASE FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def postgres_db():
    """
    Use REAL PostgreSQL database for integration testing.

    ⚠️ WARNING: Data persists after tests!
    - Writes to actual PostgreSQL database
    - Users created will be visible in Admin Dashboard
    - Requires manual cleanup between runs

    Purpose: Controlled test data seeding for UI validation
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def postgres_client(postgres_db):
    """
    FastAPI TestClient with PostgreSQL database.

    Unlike the regular `client` fixture (which uses SQLite in-memory),
    this client writes to the real PostgreSQL database.
    """
    def override_get_db():
        try:
            yield postgres_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def postgres_admin_user(postgres_db: Session) -> User:
    """
    Get or create admin user in PostgreSQL database.

    Reuses existing admin@lfa.com if it exists, otherwise creates it.
    """
    # Check if admin already exists
    admin = postgres_db.query(User).filter(User.email == "admin@lfa.com").first()

    if admin:
        return admin

    # Create new admin user
    admin = User(
        email="admin@lfa.com",
        password_hash=get_password_hash("admin123"),
        name="Admin User",
        first_name="Admin",
        last_name="User",
        nickname="Admin",
        phone="+36201234567",
        role="ADMIN",
        is_active=True,
        credit_balance=0
    )
    postgres_db.add(admin)
    postgres_db.commit()
    postgres_db.refresh(admin)

    return admin


@pytest.fixture(scope="session")
def postgres_admin_token(postgres_client: TestClient, postgres_admin_user: User) -> str:
    """
    Get admin authentication token for PostgreSQL-based tests.
    """
    response = postgres_client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@lfa.com",
            "password": "admin123"
        }
    )
    assert response.status_code == 200
    return response.json()["access_token"]
