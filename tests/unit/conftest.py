"""
Unit Test Fixtures

Imports fixtures from integration tests to allow unit tests to use
the postgres_db fixture.
"""

import pytest
from sqlalchemy.orm import Session

from app.database import SessionLocal


@pytest.fixture(scope="function")
def postgres_db():
    """
    PostgreSQL database session for unit tests.

    Scope: function (each test gets fresh session, but same DB)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
