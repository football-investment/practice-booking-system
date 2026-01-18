"""
Prepare database for tournament E2E tests

This script:
1. Cleans up old E2E test data
2. Seeds tournament types if missing
3. Verifies location and campus exist
4. Reports database state

Run before Playwright E2E tests to ensure clean state.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.semester import Semester
from app.models.tournament_type import TournamentType
from app.models.location import Location
from app.models.campus import Campus
from app.models.user import User


def cleanup_e2e_tournaments(db: Session):
    """Delete tournaments created by E2E tests"""
    print("\n🧹 Cleaning up E2E test tournaments...")

    # Find E2E tournaments (name contains 'E2E')
    e2e_tournaments = db.query(Semester).filter(
        Semester.name.like('%E2E%')
    ).all()

    if e2e_tournaments:
        print(f"   Found {len(e2e_tournaments)} E2E tournaments to delete:")
        for tournament in e2e_tournaments:
            print(f"   - {tournament.name} (ID: {tournament.id}, Status: {tournament.tournament_status})")

        # Delete them
        for tournament in e2e_tournaments:
            db.delete(tournament)

        db.commit()
        print(f"   ✅ Deleted {len(e2e_tournaments)} E2E tournaments")
    else:
        print("   ✅ No E2E tournaments found (database already clean)")


def seed_tournament_types(db: Session):
    """Seed tournament types if they don't exist"""
    print("\n🌱 Checking tournament types...")

    # Check if tournament types exist
    existing_types = db.query(TournamentType).all()

    if existing_types:
        print(f"   ✅ Found {len(existing_types)} tournament types:")
        for tt in existing_types:
            print(f"      - {tt.display_name} (code: {tt.code}, players: {tt.min_players}-{tt.max_players})")
        return

    # Seed knockout type
    print("   🌱 Seeding tournament types...")

    knockout = TournamentType(
        code="knockout",
        display_name="Single Elimination (Knockout)",
        description="Single-elimination bracket tournament where losers are eliminated",
        min_players=4,
        max_players=64,
        requires_power_of_two=True,
        session_duration_minutes=90,
        break_between_sessions_minutes=15,
        config={
            "format": "knockout",
            "seeding": "random",
            "phases": ["Quarterfinals", "Semifinals", "Finals"]
        }
    )

    db.add(knockout)
    db.commit()
    db.refresh(knockout)

    print(f"   ✅ Seeded tournament type: {knockout.display_name} (ID: {knockout.id})")


def verify_location_campus(db: Session):
    """Verify at least one location and campus exist"""
    print("\n🏫 Checking locations and campuses...")

    locations = db.query(Location).filter(Location.is_active == True).all()
    campuses = db.query(Campus).filter(Campus.is_active == True).all()

    if locations:
        print(f"   ✅ Found {len(locations)} active locations:")
        for loc in locations:
            print(f"      - {loc.name} (ID: {loc.id})")
    else:
        print("   ⚠️  No active locations found! E2E test may fail.")
        print("      Create at least one location via Admin Dashboard.")

    if campuses:
        print(f"   ✅ Found {len(campuses)} active campuses:")
        for campus in campuses:
            print(f"      - {campus.name} (ID: {campus.id}, Location: {campus.location_id})")
    else:
        print("   ⚠️  No active campuses found! E2E test may fail.")
        print("      Create at least one campus via Admin Dashboard.")


def verify_admin_user(db: Session):
    """Verify admin user exists"""
    print("\n👤 Checking admin user...")

    admin = db.query(User).filter(User.email == "admin@lfa.com").first()

    if admin:
        print(f"   ✅ Admin user found: {admin.email} (ID: {admin.id}, Role: {admin.role})")
    else:
        print("   ⚠️  Admin user 'admin@lfa.com' not found!")
        print("      E2E test login will fail.")


def main():
    """Main preparation script"""
    print("\n" + "="*80)
    print("🧪 TOURNAMENT E2E TEST DATABASE PREPARATION")
    print("="*80)

    db = SessionLocal()

    try:
        # Step 1: Cleanup
        cleanup_e2e_tournaments(db)

        # Step 2: Seed tournament types
        seed_tournament_types(db)

        # Step 3: Verify location/campus
        verify_location_campus(db)

        # Step 4: Verify admin user
        verify_admin_user(db)

        print("\n" + "="*80)
        print("✅ DATABASE PREPARATION COMPLETE")
        print("="*80)
        print("\nYou can now run:")
        print("  pytest tests/e2e/test_admin_create_tournament_refactored.py -v --headed")
        print("\n" + "="*80 + "\n")

    except Exception as e:
        print(f"\n❌ ERROR during preparation: {e}")
        db.rollback()
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
