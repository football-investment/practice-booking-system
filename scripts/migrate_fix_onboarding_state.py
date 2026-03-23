"""
One-time migration: fix UserLicenses in invalid UNLOCKED+enrolled state.

Context:
  Before the onboarding guard was added to the tournament enrollment endpoints,
  students could enroll in tournaments without completing onboarding. This left
  some UserLicense records with onboarding_completed=False even though the user
  has SemesterEnrollment records linked to that license — an impossible state.

  This script sets onboarding_completed=True for every UserLicense that has
  at least one SemesterEnrollment, restoring the invariant:
    "if you enrolled, you are effectively onboarded"

Usage:
  Dry run (shows count, no writes):
    python scripts/migrate_fix_onboarding_state.py --dry-run

  Live run:
    python scripts/migrate_fix_onboarding_state.py

Safe to run multiple times (idempotent).
"""
import sys
import os
from datetime import datetime, timezone

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models.license import UserLicense
from app.models.semester_enrollment import SemesterEnrollment


def main(dry_run: bool) -> None:
    db = SessionLocal()
    try:
        # Find all licenses where onboarding_completed=False but a linked enrollment exists
        affected = (
            db.query(UserLicense)
            .filter(UserLicense.onboarding_completed == False)  # noqa: E712
            .filter(
                db.query(SemesterEnrollment)
                .filter(SemesterEnrollment.user_license_id == UserLicense.id)
                .exists()
            )
            .all()
        )

        print(f"Found {len(affected)} UserLicense record(s) in invalid state")
        for lic in affected:
            print(
                f"  license_id={lic.id} user_id={lic.user_id} "
                f"spec={lic.specialization_type} "
                f"onboarding_completed={lic.onboarding_completed} "
                f"football_skills={'SET' if lic.football_skills else 'NULL'}"
            )

        if dry_run:
            print("\n[DRY RUN] No changes written. Re-run without --dry-run to apply.")
            return

        if not affected:
            print("Nothing to fix.")
            return

        now = datetime.now(timezone.utc)
        for lic in affected:
            lic.onboarding_completed = True
            lic.onboarding_completed_at = now

        db.commit()
        print(f"\nFixed {len(affected)} record(s). onboarding_completed=True set.")

    finally:
        db.close()


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
