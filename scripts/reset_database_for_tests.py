"""
Database Reset Script for E2E Tests

Drops and recreates the lfa_intern_system database with only essential users:
- Admin (id=1): admin@lfa.com
- Grandmaster (id=3): grandmaster@lfa.com with 21 licenses

Usage:
    python scripts/reset_database_for_tests.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import subprocess
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Import Base for create_all
from app.database import Base

# Import models
from app.models.user import User, UserRole, SpecializationType
from app.models.license import UserLicense
from app.models.location import Location, LocationType
from app.models.campus import Campus

# Import password hashing
from app.core.security import get_password_hash

# Database config
DB_NAME = "lfa_intern_system"
DB_USER = "postgres"
DB_PASSWORD = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"

# Admin/System database URL (for dropping/creating databases)
ADMIN_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres"

# Target database URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def drop_database():
    """Drop the lfa_intern_system database if it exists"""
    print(f"\n{'='*80}")
    print("STEP 1: Dropping existing database")
    print('='*80)

    engine = create_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")

    with engine.connect() as conn:
        # Terminate all connections to the database
        conn.execute(text(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{DB_NAME}'
            AND pid <> pg_backend_pid();
        """))

        # Drop database
        conn.execute(text(f"DROP DATABASE IF EXISTS {DB_NAME};"))
        print(f"✅ Database '{DB_NAME}' dropped successfully")

    engine.dispose()


def create_database():
    """Create a fresh lfa_intern_system database"""
    print(f"\n{'='*80}")
    print("STEP 2: Creating fresh database")
    print('='*80)

    engine = create_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")

    with engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE {DB_NAME};"))
        print(f"✅ Database '{DB_NAME}' created successfully")

    engine.dispose()


def create_schema():
    """Create database schema using SQLAlchemy models"""
    print(f"\n{'='*80}")
    print("STEP 3: Creating database schema")
    print('='*80)

    try:
        engine = create_engine(DATABASE_URL)

        # Create all tables from models
        Base.metadata.create_all(bind=engine)

        print("✅ Database schema created successfully")

        engine.dispose()

    except Exception as e:
        print(f"❌ Error creating schema: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def seed_admin_user(session: Session):
    """Create admin user (id=1)"""
    print("\n📝 Creating Admin user...")

    admin = User(
        id=1,
        email="admin@lfa.com",
        password_hash=get_password_hash("admin123"),
        name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
        credit_balance=0,
        onboarding_completed=True,
        date_of_birth=datetime(1990, 1, 1),
        created_at=datetime.utcnow(),
        created_by=1  # Self-created
    )

    session.add(admin)
    session.flush()

    print(f"  ✅ Admin created: {admin.email} (id={admin.id})")


def seed_grandmaster_user(session: Session):
    """Create grandmaster user (id=3) with 21 licenses"""
    print("\n📝 Creating Grandmaster user...")

    grandmaster = User(
        id=3,
        email="grandmaster@lfa.com",
        password_hash=get_password_hash("GrandMaster2026!"),
        name="Grand Master",
        role=UserRole.INSTRUCTOR,
        is_active=True,
        credit_balance=5000,
        onboarding_completed=True,
        date_of_birth=datetime(1985, 1, 1),
        created_at=datetime.utcnow(),
        created_by=1  # Created by admin
    )

    session.add(grandmaster)
    session.flush()

    print(f"  ✅ Grandmaster created: {grandmaster.email} (id={grandmaster.id}, credits={grandmaster.credit_balance})")

    # Create 21 licenses
    print("\n📝 Creating Grandmaster licenses...")

    licenses_to_create = [
        # PLAYER (Gancuju Player): Levels 1-8
        *[("PLAYER", level) for level in range(1, 9)],
        # COACH (LFA Coach): Levels 1-8
        *[("COACH", level) for level in range(1, 9)],
        # INTERNSHIP: Levels 1-5
        *[("INTERNSHIP", level) for level in range(1, 6)],
    ]

    for spec_type, level in licenses_to_create:
        license = UserLicense(
            user_id=grandmaster.id,
            specialization_type=spec_type,  # Now it's a string
            current_level=level,
            max_achieved_level=level,
            is_active=True,
            payment_verified=True,
            onboarding_completed=True,
            started_at=datetime.utcnow(),
            payment_verified_at=datetime.utcnow()
        )
        session.add(license)

    session.flush()

    # Count licenses per type
    license_counts = {}
    for spec_type, _ in licenses_to_create:
        license_counts[spec_type] = license_counts.get(spec_type, 0) + 1

    print(f"  ✅ Created {len(licenses_to_create)} licenses:")
    for spec_type, count in license_counts.items():
        print(f"     - {spec_type}: {count} licenses")


def seed_location_and_campus(session: Session):
    """Create test location and campus for tournament generation"""
    print("\n📝 Creating Test Location and Campus...")

    # Create Location (id=1)
    location = Location(
        id=1,
        name="Test City Center",
        city="Budapest",
        postal_code="1011",
        country="Hungary",
        address="Test Address 123",
        location_type=LocationType.CENTER,  # Can host all tournament types
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    session.add(location)
    session.flush()

    print(f"  ✅ Location created: {location.city} (id={location.id}, type={location.location_type.value})")

    # Create Campus (id=1)
    campus = Campus(
        id=1,
        location_id=location.id,
        name="Main Test Campus",
        venue="Test Sports Complex",
        address="Test Sports Street 1",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    session.add(campus)
    session.flush()

    print(f"  ✅ Campus created: {campus.name} (id={campus.id}, location={location.city})")


def seed_data():
    """Seed admin and grandmaster users with licenses"""
    print(f"\n{'='*80}")
    print("STEP 4: Seeding essential users and test data")
    print('='*80)

    engine = create_engine(DATABASE_URL)

    with Session(engine) as session:
        try:
            # Create admin
            seed_admin_user(session)

            # Create grandmaster with licenses
            seed_grandmaster_user(session)

            # Create test location and campus
            seed_location_and_campus(session)

            # Commit all changes
            session.commit()
            print("\n✅ All users, licenses, and test data seeded successfully")

        except Exception as e:
            session.rollback()
            print(f"\n❌ Error seeding data: {e}")
            raise

    engine.dispose()


def fix_sequences():
    """Fix PostgreSQL sequences after manual ID insertion"""
    print(f"\n{'='*80}")
    print("STEP 5: Fixing PostgreSQL sequences")
    print('='*80)

    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Fix users_id_seq - set to max(id) + 1
        conn.execute(text("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));"))
        print("  ✅ Fixed users_id_seq")

        # Fix user_licenses_id_seq if needed
        conn.execute(text("SELECT setval('user_licenses_id_seq', (SELECT COALESCE(MAX(id), 1) FROM user_licenses));"))
        print("  ✅ Fixed user_licenses_id_seq")

        conn.commit()

    engine.dispose()


def verify_database():
    """Verify database state"""
    print(f"\n{'='*80}")
    print("STEP 6: Verifying database state")
    print('='*80)

    engine = create_engine(DATABASE_URL)

    with Session(engine) as session:
        # Check admin
        admin = session.query(User).filter_by(id=1, email="admin@lfa.com").first()
        if admin:
            print(f"\n✅ Admin verified:")
            print(f"   - Email: {admin.email}")
            print(f"   - Role: {admin.role.value}")
            print(f"   - Credits: {admin.credit_balance}")
        else:
            print("\n❌ Admin user not found!")
            return False

        # Check grandmaster
        grandmaster = session.query(User).filter_by(id=3, email="grandmaster@lfa.com").first()
        if grandmaster:
            print(f"\n✅ Grandmaster verified:")
            print(f"   - Email: {grandmaster.email}")
            print(f"   - Role: {grandmaster.role.value}")
            print(f"   - Credits: {grandmaster.credit_balance}")

            # Check licenses
            licenses = session.query(UserLicense).filter_by(user_id=grandmaster.id).all()
            print(f"\n✅ Grandmaster licenses: {len(licenses)} total")

            # Group by specialization type
            license_groups = {}
            for license in licenses:
                spec_type = license.specialization_type  # It's already a string
                if spec_type not in license_groups:
                    license_groups[spec_type] = []
                license_groups[spec_type].append(license.current_level)

            for spec_type, levels in sorted(license_groups.items()):
                print(f"   - {spec_type}: Levels {sorted(levels)}")

            if len(licenses) != 21:
                print(f"\n⚠️  WARNING: Expected 21 licenses, found {len(licenses)}")
        else:
            print("\n❌ Grandmaster user not found!")
            return False

        # Check no other users
        total_users = session.query(User).count()
        if total_users == 2:
            print(f"\n✅ Database clean: Only 2 users (admin + grandmaster)")
        else:
            print(f"\n⚠️  WARNING: Found {total_users} users (expected 2)")

        # Check location and campus
        location = session.query(Location).filter_by(id=1).first()
        if location:
            print(f"\n✅ Location verified:")
            print(f"   - City: {location.city}")
            print(f"   - Type: {location.location_type.value}")
            print(f"   - Active: {location.is_active}")
        else:
            print("\n❌ Location (id=1) not found!")
            return False

        campus = session.query(Campus).filter_by(id=1).first()
        if campus:
            print(f"\n✅ Campus verified:")
            print(f"   - Name: {campus.name}")
            print(f"   - Location: {location.city}")
            print(f"   - Active: {campus.is_active}")
        else:
            print("\n❌ Campus (id=1) not found!")
            return False

    engine.dispose()
    return True


def main():
    """Main execution"""
    print("\n" + "="*80)
    print("DATABASE RESET FOR E2E TESTS")
    print("="*80)
    print(f"\nTarget Database: {DB_NAME}")
    print(f"Database URL: {DATABASE_URL}")

    try:
        # Step 1: Drop existing database
        drop_database()

        # Step 2: Create fresh database
        create_database()

        # Step 3: Create schema
        create_schema()

        # Step 4: Seed essential data
        seed_data()

        # Step 5: Fix sequences
        fix_sequences()

        # Step 6: Verify
        if verify_database():
            print("\n" + "="*80)
            print("✅ DATABASE RESET COMPLETE!")
            print("="*80)
            print("\n📝 Summary:")
            print("   - Database: lfa_intern_system (fresh)")
            print("   - Admin: admin@lfa.com (password: admin123)")
            print("   - Grandmaster: grandmaster@lfa.com (password: GrandMaster2026!)")
            print("   - Grandmaster licenses: 21 (all active)")
            print("   - Test Location: Budapest (id=1, CENTER type)")
            print("   - Test Campus: Main Test Campus (id=1)")
            print("\n🎯 Ready for E2E tests!")
            return 0
        else:
            print("\n❌ Database verification failed!")
            return 1

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
