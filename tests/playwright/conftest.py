"""
E2E Test Configuration

Playwright tests use built-in fixtures (page, browser, context, etc.)
Custom viewport size configured for better visibility.
JSON-based test data fixtures for predictable, maintainable test data.
"""

import pytest
from fixtures.data_loader import TestDataLoader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """
    Configure browser context with custom viewport size.

    Sets viewport to 1920x1080 for better element visibility in headed mode.
    """
    return {
        **browser_context_args,
        "viewport": {
            "width": 1920,
            "height": 1080,
        }
    }


@pytest.fixture(scope="session")
def test_data():
    """
    Load test data from JSON fixtures.

    Provides centralized access to test users, locations, tournaments, etc.

    Usage:
        def test_something(test_data):
            admin = test_data.get_admin()
            player = test_data.get_player(email="player1@example.com")
            tournament = test_data.get_tournament(assignment_type="APPLICATION_BASED")
    """
    return TestDataLoader(fixture_name="seed_data")


@pytest.fixture(scope="function")
def admin_credentials(test_data):
    """Get admin login credentials"""
    admin = test_data.get_admin()
    return {
        "email": admin["email"],
        "password": admin["password"]
    }


@pytest.fixture(scope="function")
def instructor_credentials(test_data):
    """Get grandmaster instructor credentials"""
    instructor = test_data.get_instructor()
    return {
        "email": instructor["email"],
        "password": instructor["password"]
    }


@pytest.fixture(scope="function")
def player_credentials(test_data):
    """Get first player credentials"""
    player = test_data.get_player(index=0)
    return {
        "email": player["email"],
        "password": player["password"]
    }


@pytest.fixture(scope="function")
def db():
    """Database session fixture for direct database verification"""
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
