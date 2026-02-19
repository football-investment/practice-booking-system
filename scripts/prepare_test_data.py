"""
Prepare test data for Phase 7 testing

Sets up clean state with test users, locations, and availability data
"""

import os
import sys
from datetime import datetime, timedelta

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.user import User
from app.models.location import Location
from app.models.instructor_assignment import LocationMasterInstructor, InstructorAvailabilityWindow
from app.models.semester import Semester, SemesterStatus


def clean_test_state(db: Session):
    """Remove existing test data to start fresh"""
    print("🧹 Cleaning existing test data...")

    # Delete existing master instructor contracts for test locations
    test_location_ids = [1, 2, 3]  # Budapest, Budaörs, Pécs

    deleted_masters = db.query(LocationMasterInstructor).filter(
        LocationMasterInstructor.location_id.in_(test_location_ids)
    ).delete(synchronize_session=False)

    print(f"   Deleted {deleted_masters} existing master contracts")

    # Reset semesters to DRAFT status
    updated_semesters = db.query(Semester).filter(
        Semester.location_city.in_(['Budapest', 'Budaörs', 'Pécs'])
    ).update({
        'status': SemesterStatus.DRAFT,
        'master_instructor_id': None
    }, synchronize_session=False)

    print(f"   Reset {updated_semesters} semesters to DRAFT")

    db.commit()
    print("✅ Clean state established")


def verify_test_users(db: Session):
    """Verify test users exist and get their IDs"""
    print("\n👥 Verifying test users...")

    # Admin user
    admin = db.query(User).filter(User.role == 'ADMIN').first()
    if not admin:
        print("   ❌ No admin user found!")
        return None
    print(f"   ✅ Admin user: {admin.email} (ID: {admin.id})")

    # Instructors
    instructors = db.query(User).filter(User.role == 'INSTRUCTOR').limit(5).all()
    if not instructors:
        print("   ❌ No instructor users found!")
        return None

    print(f"   ✅ Found {len(instructors)} instructor users:")
    for instr in instructors:
        print(f"      - {instr.name or instr.email} (ID: {instr.id})")

    return {
        'admin_id': admin.id,
        'admin_email': admin.email,
        'instructors': [{'id': i.id, 'email': i.email, 'name': i.name} for i in instructors]
    }


def create_availability_data(db: Session, instructor_ids: list):
    """Create availability data for test instructors"""
    print("\n📅 Creating availability data for 2026...")

    # Delete existing 2026 availability
    db.query(InstructorAvailabilityWindow).filter(
        InstructorAvailabilityWindow.year == 2026,
        InstructorAvailabilityWindow.instructor_id.in_(instructor_ids)
    ).delete(synchronize_session=False)

    # Create availability patterns
    availability_patterns = [
        {'quarters': ['Q1', 'Q2', 'Q3', 'Q4'], 'desc': 'Full year'},  # First instructor
        {'quarters': ['Q1', 'Q2', 'Q3'], 'desc': 'Q1-Q3 (75% match)'},  # Second
        {'quarters': ['Q1', 'Q2'], 'desc': 'Q1-Q2 (50% match)'},  # Third
        {'quarters': ['Q1', 'Q2', 'Q3', 'Q4'], 'desc': 'Full year'},  # Fourth
        {'quarters': ['Q2', 'Q3', 'Q4'], 'desc': 'Q2-Q4 (75% match)'},  # Fifth
    ]

    for i, instructor_id in enumerate(instructor_ids[:5]):
        pattern = availability_patterns[i % len(availability_patterns)]

        # Create one record for each quarter (database structure requires separate records)
        for quarter in pattern['quarters']:
            availability = InstructorAvailabilityWindow(
                instructor_id=instructor_id,
                year=2026,
                time_period=quarter,
                is_available=True,
                notes=f"Test availability - {pattern['desc']}"
            )
            db.add(availability)

        print(f"   ✅ Created availability for instructor {instructor_id}: {pattern['quarters']}")

    db.commit()
    print("✅ Availability data created")


def verify_locations(db: Session):
    """Verify test locations exist"""
    print("\n📍 Verifying test locations...")

    test_locations = ['Budapest', 'Budaörs', 'Pécs']
    locations = {}

    for city in test_locations:
        location = db.query(Location).filter(Location.city == city).first()
        if location:
            locations[city] = location.id
            print(f"   ✅ {city}: ID {location.id}")
        else:
            print(f"   ❌ Location not found: {city}")

    return locations


def verify_semesters(db: Session):
    """Verify semesters exist for test locations"""
    print("\n📚 Verifying semesters...")

    test_cities = ['Budapest', 'Budaörs', 'Pécs']

    for city in test_cities:
        semesters = db.query(Semester).filter(
            Semester.location_city == city,
            Semester.status == SemesterStatus.DRAFT
        ).count()
        print(f"   ✅ {city}: {semesters} DRAFT semesters")

    return True


def print_test_summary(users, locations):
    """Print summary of test data setup"""
    print("\n" + "="*60)
    print("🎯 TEST DATA READY FOR PHASE 7")
    print("="*60)

    print("\n📋 Quick Reference:")
    print(f"\nAdmin User:")
    print(f"  Email: {users['admin_email']}")
    print(f"  ID: {users['admin_id']}")

    print(f"\nTest Instructors (with 2026 availability):")
    for i, instr in enumerate(users['instructors'][:5], 1):
        print(f"  {i}. {instr['name'] or instr['email']} (ID: {instr['id']})")

    print(f"\nTest Locations:")
    for city, loc_id in locations.items():
        print(f"  - {city}: ID {loc_id}")

    print("\n✅ Ready for Test Suite 1.1: Happy Path - Direct Hire")
    print("\nNext steps:")
    print("1. Login to Streamlit as Admin")
    print("2. Navigate to Budapest location")
    print("3. Click 'Direct Hire' tab")
    print("4. Follow Test Suite 1.1 steps")
    print("\n" + "="*60)


def main():
    """Main test data preparation"""
    print("🚀 Preparing test data for Phase 7 testing...\n")

    db = SessionLocal()

    try:
        # Step 1: Clean existing test data
        clean_test_state(db)

        # Step 2: Verify users
        users = verify_test_users(db)
        if not users:
            print("\n❌ Failed to verify users. Please check database.")
            return

        # Step 3: Verify locations
        locations = verify_locations(db)
        if not locations:
            print("\n❌ Failed to verify locations. Please check database.")
            return

        # Step 4: Create availability data
        instructor_ids = [i['id'] for i in users['instructors']]
        create_availability_data(db, instructor_ids)

        # Step 5: Verify semesters
        verify_semesters(db)

        # Step 6: Print summary
        print_test_summary(users, locations)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
