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
import json
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Import Base for create_all
from app.database import Base

# Import models
from app.models.user import User, UserRole, SpecializationType
from app.models.license import UserLicense
from app.models.tournament_type import TournamentType
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
    """Create base database schema using SQLAlchemy models + manual table creation"""
    print(f"\n{'='*80}")
    print("STEP 3: Creating base database schema")
    print('='*80)

    try:
        engine = create_engine(DATABASE_URL)

        # Create all tables from models
        Base.metadata.create_all(bind=engine)

        # NOTE: tournament_status_history table is now in models (TournamentStatusHistory)
        # No need for manual creation anymore

        print("✅ Base database schema created successfully")
        print("   (including tournament_status_history table)")

        engine.dispose()

    except Exception as e:
        print(f"❌ Error creating schema: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_alembic_migrations():
    """
    Apply Alembic migrations to database.

    Strategy:
    1. Stamp database to mark base schema as created (skip ALTER migrations on existing tables)
    2. Run remaining migrations (like tournament_status_history table creation)
    """
    print(f"\n{'='*80}")
    print("STEP 3b: Running Alembic migrations")
    print('='*80)

    try:
        # Set DATABASE_URL environment variable for Alembic
        env = os.environ.copy()
        env['DATABASE_URL'] = DATABASE_URL

        # Stamp to HEAD to mark all migrations as applied
        # Since Base.metadata.create_all() creates the complete schema (including tournament_status),
        # we stamp to head to avoid re-running migrations
        print("  Stamping database to mark all migrations as applied...")
        stamp_result = subprocess.run(
            ['venv/bin/alembic', 'stamp', 'head'],
            cwd=project_root,
            env=env,
            capture_output=True,
            text=True
        )

        if stamp_result.returncode != 0:
            print(f"❌ Alembic stamp failed:")
            print(stamp_result.stderr)
            sys.exit(1)

        print("✅ Alembic migrations marked as applied (stamped to head)")

    except Exception as e:
        print(f"❌ Error running Alembic migrations: {e}")
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
        # LFA_FOOTBALL_PLAYER: Levels 1-8
        *[("LFA_FOOTBALL_PLAYER", level) for level in range(1, 9)],
        # LFA_COACH: Levels 1-8
        *[("LFA_COACH", level) for level in range(1, 9)],
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
    """Create test locations and campuses in different countries for tournament generation"""
    print("\n📝 Creating Test Locations and Campuses (3 countries)...")

    # Define 3 locations in different countries
    locations_data = [
        {
            'id': 1,
            'name': 'Budapest Center',
            'city': 'Budapest',
            'postal_code': '1011',
            'country': 'Hungary',
            'country_code': 'HU',
            'location_code': 'BDPST',
            'address': 'Váci utca 123',
            'location_type': LocationType.CENTER
        },
        {
            'id': 2,
            'name': 'Vienna Academy',
            'city': 'Vienna',
            'postal_code': '1010',
            'country': 'Austria',
            'country_code': 'AT',
            'location_code': 'VIE',
            'address': 'Stephansplatz 1',
            'location_type': LocationType.CENTER
        },
        {
            'id': 3,
            'name': 'Bratislava Training Center',
            'city': 'Bratislava',
            'postal_code': '81101',
            'country': 'Slovakia',
            'country_code': 'SK',
            'location_code': 'BTS',
            'address': 'Hviezdoslavovo námestie 1',
            'location_type': LocationType.PARTNER
        }
    ]

    # Create locations and campuses
    for loc_data in locations_data:
        location = Location(
            id=loc_data['id'],
            name=loc_data['name'],
            city=loc_data['city'],
            postal_code=loc_data['postal_code'],
            country=loc_data['country'],
            country_code=loc_data['country_code'],
            location_code=loc_data['location_code'],
            address=loc_data['address'],
            location_type=loc_data['location_type'],
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(location)
        session.flush()

        # Build flag manually
        flag = chr(ord(location.country_code[0]) + 127397) + chr(ord(location.country_code[1]) + 127397) if location.country_code and len(location.country_code) == 2 else "🌍"
        print(f"  ✅ Location created: {flag} {location.country_code} - {location.location_code} - {location.city} (id={location.id})")

        # Create campus for this location
        campus = Campus(
            id=loc_data['id'],  # Same ID as location for simplicity
            location_id=location.id,
            name=f"{location.city} Main Campus",
            venue=f"{location.city} Sports Complex",
            address=f"{location.city} Sports Street 1",
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


def seed_tournament_types():
    """Seed tournament_types table with pre-defined configurations"""
    print(f"\n{'='*80}")
    print("STEP 4b: Seeding tournament types")
    print('='*80)

    engine = create_engine(DATABASE_URL)

    with Session(engine) as session:
        try:
            # Check if already seeded
            existing_count = session.query(TournamentType).count()
            if existing_count > 0:
                print(f"  ℹ️  {existing_count} tournament types already exist, skipping seed")
                return

            # Load configurations
            tournament_configs = [
                'league.json',
                'knockout.json',
                'group_knockout.json',
                'swiss.json'
            ]

            created_count = 0

            for config_file in tournament_configs:
                try:
                    config_path = os.path.join(
                        os.path.dirname(__file__),
                        '..',
                        'app',
                        'tournament_types',
                        config_file
                    )

                    with open(config_path, 'r') as f:
                        config = json.load(f)

                    tournament_type = TournamentType(
                        code=config['code'],
                        display_name=config['display_name'],
                        description=config['description'],
                        min_players=config['min_players'],
                        max_players=config.get('max_players'),
                        requires_power_of_two=config['requires_power_of_two'],
                        session_duration_minutes=config['session_duration_minutes'],
                        break_between_sessions_minutes=config['break_between_sessions_minutes'],
                        config=config
                    )

                    session.add(tournament_type)
                    created_count += 1
                    print(f"  ✅ Created: {tournament_type.display_name} ({tournament_type.code})")

                except FileNotFoundError:
                    print(f"  ❌ ERROR: Config file not found: {config_file}")
                except json.JSONDecodeError as e:
                    print(f"  ❌ ERROR: Invalid JSON in {config_file}: {e}")

            # Commit all changes
            session.commit()
            print(f"\n✅ Tournament types seeded: {created_count} types created")

        except Exception as e:
            session.rollback()
            print(f"\n❌ Error seeding tournament types: {e}")
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

        # Check locations and campuses (should have 3)
        locations = session.query(Location).all()
        campuses = session.query(Campus).all()

        if len(locations) == 3 and len(campuses) == 3:
            print(f"\n✅ Locations verified: {len(locations)} locations")
            for loc in locations:
                flag = chr(ord(loc.country_code[0]) + 127397) + chr(ord(loc.country_code[1]) + 127397) if loc.country_code and len(loc.country_code) == 2 else "🌍"
                print(f"   - {flag} {loc.country_code} - {loc.location_code} - {loc.city} ({loc.location_type.value})")

            print(f"\n✅ Campuses verified: {len(campuses)} campuses")
            for camp in campuses:
                print(f"   - {camp.name}")
        else:
            print(f"\n❌ Expected 3 locations and 3 campuses, found {len(locations)} locations and {len(campuses)} campuses")
            return False

        # Check tournament_status_history table exists
        result = session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'tournament_status_history'
            );
        """))
        table_exists = result.scalar()

        if table_exists:
            print(f"\n✅ Tournament status history table verified")
        else:
            print("\n❌ Tournament status history table not found!")
            return False

        # Check tournament types
        tournament_types_count = session.query(TournamentType).count()
        if tournament_types_count > 0:
            print(f"\n✅ Tournament types verified: {tournament_types_count} types available")
            for tt in session.query(TournamentType).all():
                print(f"   - {tt.display_name} ({tt.code})")
        else:
            print("\n❌ No tournament types found!")
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

        # Step 3b: Run Alembic migrations
        run_alembic_migrations()

        # Step 4: Seed essential data
        seed_data()

        # Step 4b: Seed tournament types
        seed_tournament_types()

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
            print("   - Test Locations: 3 (Budapest/HU, Vienna/AT, Bratislava/SK)")
            print("   - Test Campuses: 3 (one per location)")
            print(f"   - Tournament types: 4 (league, knockout, group_knockout, swiss)")
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
