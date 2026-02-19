"""
One-time script to backfill enrollment_id on existing tournament bookings

This script links existing tournament bookings to their corresponding SemesterEnrollment records.
It should be run ONCE after the enrollment_id column has been added to the bookings table.

Run with:
    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" python scripts/backfill_booking_enrollment_link.py
"""

import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.booking import Booking
from app.models.semester_enrollment import SemesterEnrollment
from app.models.session import Session as SessionModel


def backfill_enrollment_links():
    """Backfill enrollment_id on existing tournament bookings"""
    db: Session = SessionLocal()

    try:
        # Get all bookings for tournament sessions that don't have enrollment_id
        tournament_bookings = db.query(Booking).join(
            SessionModel, Booking.session_id == SessionModel.id
        ).filter(
            SessionModel.is_tournament_game == True,
            Booking.enrollment_id == None
        ).all()

        print(f"🔍 Found {len(tournament_bookings)} tournament bookings without enrollment_id")

        if not tournament_bookings:
            print("✅ All tournament bookings already have enrollment_id! Nothing to backfill.")
            return

        linked_count = 0
        no_enrollment_count = 0
        errors = []

        for booking in tournament_bookings:
            session = booking.session
            tournament_id = session.semester_id

            # Find matching enrollment
            enrollment = db.query(SemesterEnrollment).filter(
                SemesterEnrollment.user_id == booking.user_id,
                SemesterEnrollment.semester_id == tournament_id,
                SemesterEnrollment.is_active == True
            ).first()

            if enrollment:
                booking.enrollment_id = enrollment.id
                linked_count += 1
                print(f"✅ Linked booking {booking.id} → enrollment {enrollment.id} (user={booking.user_id}, tournament={tournament_id})")
            else:
                no_enrollment_count += 1
                error_msg = f"⚠️ No active enrollment found for booking {booking.id} (user={booking.user_id}, tournament={tournament_id})"
                print(error_msg)
                errors.append(error_msg)

        # Commit changes
        db.commit()

        # Summary
        print("\n" + "="*80)
        print("📊 BACKFILL SUMMARY")
        print("="*80)
        print(f"✅ Successfully linked: {linked_count} bookings")
        print(f"⚠️ No enrollment found: {no_enrollment_count} bookings")
        print(f"📝 Total processed: {len(tournament_bookings)} bookings")
        print("="*80)

        if errors:
            print("\n⚠️ BOOKINGS WITHOUT ENROLLMENTS:")
            for error in errors:
                print(f"   {error}")
            print("\nℹ️ These bookings may need manual review. They could be:")
            print("   - Bookings created before enrollment (shouldn't happen)")
            print("   - Enrollments that were deleted/deactivated")
            print("   - Data inconsistencies that need cleanup")

        if linked_count > 0:
            print(f"\n✅ Backfill complete! {linked_count} tournament bookings now linked to enrollments.")
        else:
            print("\n⚠️ No bookings were linked. Please review the warnings above.")

    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Starting enrollment_id backfill for tournament bookings...")
    print("="*80)
    backfill_enrollment_links()
