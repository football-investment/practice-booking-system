"""
Data Migration Script: Create Missing Tournament Bookings
==========================================================

PROBLEM:
- Tournament enrollments created BEFORE the auto-booking feature was added
- These enrollments show in enrollment count but NOT in booking count
- Causes discrepancy between frontend displays:
  * LFA Player Dashboard: Shows enrollment count (correct)
  * Instructor Dashboard: Shows booking count (incorrect - missing bookings)

SOLUTION:
- For all tournament enrollments (TOURN- semesters) that don't have bookings
- Auto-create CONFIRMED bookings for their tournament sessions

USAGE:
    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" python scripts/fix_missing_tournament_bookings.py
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.semester_enrollment import SemesterEnrollment
from app.models.semester import Semester
from app.models.session import Session as SessionModel
from app.models.booking import Booking, BookingStatus
from datetime import datetime


def fix_missing_tournament_bookings():
    """Create bookings for tournament enrollments that don't have them"""

    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    # Create database connection
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        print("🔍 Finding tournament enrollments without bookings...\n")

        # Get all tournament enrollments (TOURN- code prefix)
        tournament_enrollments = db.query(SemesterEnrollment).join(
            Semester, SemesterEnrollment.semester_id == Semester.id
        ).filter(
            Semester.code.like("TOURN-%"),
            SemesterEnrollment.is_active == True
        ).all()

        print(f"📊 Found {len(tournament_enrollments)} active tournament enrollments")

        missing_bookings = []

        for enrollment in tournament_enrollments:
            # Get tournament session
            tournament_session = db.query(SessionModel).filter(
                SessionModel.semester_id == enrollment.semester_id
            ).first()

            if not tournament_session:
                print(f"⚠️  No session found for tournament {enrollment.semester_id} (enrollment {enrollment.id})")
                continue

            # Check if booking exists
            existing_booking = db.query(Booking).filter(
                Booking.user_id == enrollment.user_id,
                Booking.session_id == tournament_session.id
            ).first()

            if existing_booking:
                print(f"✅ Booking exists: User {enrollment.user_id} -> Session {tournament_session.id}")
            else:
                print(f"❌ Missing booking: User {enrollment.user_id} -> Session {tournament_session.id}")
                missing_bookings.append({
                    "enrollment_id": enrollment.id,
                    "user_id": enrollment.user_id,
                    "session_id": tournament_session.id,
                    "semester_id": enrollment.semester_id
                })

        print(f"\n📊 Summary:")
        print(f"   - Total tournament enrollments: {len(tournament_enrollments)}")
        print(f"   - Missing bookings: {len(missing_bookings)}")

        if not missing_bookings:
            print("\n✅ All tournament enrollments have bookings - no fix needed!")
            return

        # Show what will be created
        print(f"\n⚠️  About to create {len(missing_bookings)} missing bookings:")
        for mb in missing_bookings:
            print(f"   - Enrollment {mb['enrollment_id']}: User {mb['user_id']} -> Session {mb['session_id']}")

        # Create missing bookings
        print(f"\n🔧 Creating {len(missing_bookings)} missing bookings...")
        created_count = 0

        for mb in missing_bookings:
            booking = Booking(
                user_id=mb["user_id"],
                session_id=mb["session_id"],
                status=BookingStatus.CONFIRMED,
                created_at=datetime.utcnow()
            )
            db.add(booking)
            created_count += 1
            print(f"✅ Created booking {created_count}/{len(missing_bookings)}: User {mb['user_id']} -> Session {mb['session_id']}")

        # Commit changes
        db.commit()
        print(f"\n✅ SUCCESS: Created {created_count} missing bookings!")

    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    fix_missing_tournament_bookings()
