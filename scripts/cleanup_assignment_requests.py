"""
Cleanup Script: Remove Instructor Assignment Requests

This script removes all instructor assignment requests (tournament applications)
while preserving:
- Instructors (users)
- Tournaments (semesters)
- All other data

Use this when too many instructors have applied and you want a clean slate.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.instructor_assignment import InstructorAssignmentRequest
from app.models.notification import Notification, NotificationType


def cleanup_assignment_requests(db: Session, dry_run: bool = True):
    """
    Remove all instructor assignment requests and related notifications.

    Args:
        db: Database session
        dry_run: If True, only show what would be deleted without actually deleting
    """
    print("=" * 70)
    print("CLEANUP: Instructor Assignment Requests")
    print("=" * 70)

    # Count assignment requests
    request_count = db.query(InstructorAssignmentRequest).count()
    print(f"\n📋 Found {request_count} assignment requests")

    # Count related notifications
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
    print(f"🔔 Found {notification_count} related notifications")

    if dry_run:
        print("\n" + "=" * 70)
        print("DRY RUN MODE - No changes will be made")
        print("=" * 70)
        print(f"\nWould delete:")
        print(f"  - {request_count} assignment requests")
        print(f"  - {notification_count} tournament notifications")
        print("\nRun with --execute flag to actually perform cleanup")
        return

    # Confirm deletion
    print("\n" + "=" * 70)
    print("⚠️  WARNING: This will DELETE data!")
    print("=" * 70)
    print(f"\nAbout to delete:")
    print(f"  - {request_count} assignment requests")
    print(f"  - {notification_count} tournament notifications")

    response = input("\nAre you sure you want to continue? Type 'YES' to confirm: ")

    if response != "YES":
        print("\n❌ Cleanup cancelled")
        return

    # Delete notifications first (foreign key constraint)
    print("\n🗑️  Deleting tournament notifications...")
    deleted_notifications = db.query(Notification).filter(
        Notification.type.in_(tournament_notification_types)
    ).delete(synchronize_session=False)
    print(f"✅ Deleted {deleted_notifications} notifications")

    # Delete assignment requests
    print("🗑️  Deleting assignment requests...")
    deleted_requests = db.query(InstructorAssignmentRequest).delete(synchronize_session=False)
    print(f"✅ Deleted {deleted_requests} assignment requests")

    # Commit changes
    db.commit()

    print("\n" + "=" * 70)
    print("✅ Cleanup completed successfully!")
    print("=" * 70)
    print(f"\nTotal deleted:")
    print(f"  - {deleted_requests} assignment requests")
    print(f"  - {deleted_notifications} tournament notifications")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Clean up instructor assignment requests")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the cleanup (default is dry-run)"
    )

    args = parser.parse_args()

    db = SessionLocal()
    try:
        cleanup_assignment_requests(db, dry_run=not args.execute)
    finally:
        db.close()


if __name__ == "__main__":
    main()
