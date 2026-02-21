#!/usr/bin/env python3
"""
CI Unit Test Minimal Fixtures

QUICK STABILIZATION ONLY - creates minimal seed data for unit tests
that hard-code user_id=1 and user_license_id=1.

TODO: Refactor tests to use proper pytest fixtures instead of hardcoded IDs.
See: tests/unit/conftest.py for fixture examples (student_user, etc.)

This script is a CI stabilization hack, not a proper solution.
"""
import sys
import os
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.user import User, UserRole
from app.models.user_license import UserLicense, LicenseType
from app.models.user_progress import Specialization
from app.core.security import get_password_hash


def seed_minimal_fixtures(db: Session):
    """Create minimal user and license fixtures for unit tests"""

    print("🌱 Seeding minimal CI test fixtures...")

    # Check if user_id=1 already exists
    existing_user = db.query(User).filter(User.id == 1).first()
    if existing_user:
        print("✅ user_id=1 already exists, skipping user creation")
    else:
        # Create user with ID=1 (expected by test_credit_service, test_xp_transaction_service, etc.)
        test_user = User(
            id=1,  # Explicit ID
            name="CI Test User",
            email="citest@test.com",
            password_hash=get_password_hash("test123"),
            role=UserRole.STUDENT,
            is_active=True,
            date_of_birth=datetime(2000, 1, 1),
            parental_consent=True
        )
        db.add(test_user)
        print("✅ Created user_id=1 (CI Test User)")

    # Check if user_license_id=1 already exists
    existing_license = db.query(UserLicense).filter(UserLicense.id == 1).first()
    if existing_license:
        print("✅ user_license_id=1 already exists, skipping license creation")
    else:
        # Create specialization if needed
        spec = db.query(Specialization).filter(Specialization.id == "LFA_PLAYER_YOUTH").first()
        if not spec:
            spec = Specialization(id="LFA_PLAYER_YOUTH", is_active=True)
            db.add(spec)
            db.flush()

        # Create user_license with ID=1 (expected by test_credit_service)
        test_license = UserLicense(
            id=1,  # Explicit ID
            user_id=1,
            specialization_id="LFA_PLAYER_YOUTH",
            license_type=LicenseType.ACTIVE,
            start_date=date.today(),
            is_active=True
        )
        db.add(test_license)
        print("✅ Created user_license_id=1 (LFA_PLAYER_YOUTH)")

    db.commit()
    print("✅ CI minimal fixtures seeded successfully!")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_minimal_fixtures(db)
    except Exception as e:
        print(f"❌ Seed failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()
