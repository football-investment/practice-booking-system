"""
Cleanup Script: Remove All Tournaments

This script removes all tournaments (semesters with tournament_status) and related data:
- Tournament enrollments
- Tournament team enrollments
- Tournament rankings
- Tournament rewards
- Tournament stats
- Tournament status history
- Instructor assignment requests
- Related notifications

Use this to clean up test tournaments and start fresh.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal
from app.models.semester import Semester
from app.models.notification import Notification, NotificationType


def cleanup_tournaments(db: Session, dry_run: bool = True, force: bool = False):
    """
    Remove all tournaments and related data.

    Args:
        db: Database session
        dry_run: If True, only show what would be deleted without actually deleting
        force: If True, skip confirmation prompt
    """
    print("=" * 70)
    print("CLEANUP: All Tournaments and Related Data")
    print("=" * 70)

    # Count tournaments
    tournament_count = db.query(Semester).filter(
        Semester.tournament_status.isnot(None)
    ).count()

    print(f"\n📋 Found {tournament_count} tournaments to delete")

    if tournament_count == 0:
        print("\n✅ No tournaments found - database is clean!")
        return

    # Get sample tournament names
    sample_tournaments = db.query(Semester).filter(
        Semester.tournament_status.isnot(None)
    ).limit(10).all()

    print(f"\n📝 Sample tournaments (first 10):")
    for t in sample_tournaments:
        print(f"   • {t.name} (ID: {t.id}, Status: {t.tournament_status})")

    if tournament_count > 10:
        print(f"   ... and {tournament_count - 10} more")

    # Count related data (will be auto-deleted by CASCADE)
    count_queries = {
        "Tournament enrollments": "SELECT COUNT(*) FROM semester_enrollments WHERE semester_id IN (SELECT id FROM semesters WHERE tournament_status IS NOT NULL)",
        "Tournament team enrollments": "SELECT COUNT(*) FROM tournament_team_enrollments WHERE semester_id IN (SELECT id FROM semesters WHERE tournament_status IS NOT NULL)",
        "Tournament rankings": "SELECT COUNT(*) FROM tournament_rankings WHERE tournament_id IN (SELECT id FROM semesters WHERE tournament_status IS NOT NULL)",
        "Tournament rewards": "SELECT COUNT(*) FROM tournament_rewards WHERE tournament_id IN (SELECT id FROM semesters WHERE tournament_status IS NOT NULL)",
        "Tournament stats": "SELECT COUNT(*) FROM tournament_stats WHERE tournament_id IN (SELECT id FROM semesters WHERE tournament_status IS NOT NULL)",
        "Tournament status history": "SELECT COUNT(*) FROM tournament_status_history WHERE tournament_id IN (SELECT id FROM semesters WHERE tournament_status IS NOT NULL)",
        "Instructor assignment requests": "SELECT COUNT(*) FROM instructor_assignment_requests WHERE semester_id IN (SELECT id FROM semesters WHERE tournament_status IS NOT NULL)",
    }

    print(f"\n🔗 Related data (will be auto-deleted by CASCADE):")
    for label, query in count_queries.items():
        result = db.execute(text(query)).scalar()
        if result > 0:
            print(f"   • {label}: {result}")

    # Count tournament notifications
    tournament_notification_types = [
        NotificationType.TOURNAMENT_APPLICATION_APPROVED,
        NotificationType.TOURNAMENT_APPLICATION_REJECTED,
        NotificationType.TOURNAMENT_DIRECT_INVITATION,
        NotificationType.TOURNAMENT_INSTRUCTOR_ACCEPTED,
        NotificationType.TOURNAMENT_INSTRUCTOR_DECLINED
    ]

    notification_count = db.query(Notification).filter(
        Notification.type.in_(tournament_notification_types)
    ).count()

    if notification_count > 0:
        print(f"   • Tournament notifications: {notification_count}")

    if dry_run:
        print("\n" + "=" * 70)
        print("DRY RUN MODE - No changes will be made")
        print("=" * 70)
        print(f"\nWould delete:")
        print(f"  • {tournament_count} tournaments")
        print(f"  • All related enrollments, rankings, rewards, stats, etc. (CASCADE)")
        if notification_count > 0:
            print(f"  • {notification_count} tournament notifications")
        print("\nRun with --execute flag to actually perform cleanup")
        return

    # Confirm deletion
    if not force:
        print("\n" + "=" * 70)
        print("⚠️  WARNING: This will DELETE all tournament data!")
        print("=" * 70)
        print(f"\nAbout to delete:")
        print(f"  • {tournament_count} tournaments")
        print(f"  • All related enrollments, rankings, rewards, stats, etc. (CASCADE)")
        if notification_count > 0:
            print(f"  • {notification_count} tournament notifications")

        response = input("\nAre you sure you want to continue? Type 'YES' to confirm: ")

        if response != "YES":
            print("\n❌ Cleanup cancelled")
            return
    else:
        print("\n" + "=" * 70)
        print("⚠️  FORCE MODE - Deleting without confirmation")
        print("=" * 70)

    # Delete tournament notifications first
    if notification_count > 0:
        print(f"\n🗑️  Deleting {notification_count} tournament notifications...")
        deleted_notifications = db.query(Notification).filter(
            Notification.type.in_(tournament_notification_types)
        ).delete(synchronize_session=False)
        print(f"✅ Deleted {deleted_notifications} notifications")

    # Delete tournaments (CASCADE will handle related data)
    print(f"🗑️  Deleting {tournament_count} tournaments...")
    print("   (This will also delete all related enrollments, rankings, etc. via CASCADE)")

    deleted_tournaments = db.query(Semester).filter(
        Semester.tournament_status.isnot(None)
    ).delete(synchronize_session=False)

    print(f"✅ Deleted {deleted_tournaments} tournaments")

    # Commit changes
    db.commit()

    print("\n" + "=" * 70)
    print("✅ Cleanup completed successfully!")
    print("=" * 70)
    print(f"\nTotal deleted:")
    print(f"  • {deleted_tournaments} tournaments")
    if notification_count > 0:
        print(f"  • {deleted_notifications} notifications")
    print(f"  • All related data deleted via CASCADE")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Clean up all tournaments")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the cleanup (default is dry-run)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt (use with --execute)"
    )

    args = parser.parse_args()

    db = SessionLocal()
    try:
        cleanup_tournaments(db, dry_run=not args.execute, force=args.force)
    finally:
        db.close()


if __name__ == "__main__":
    main()
