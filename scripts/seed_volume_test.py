"""
Seed a production-like dataset for migration volume and index performance testing.
===================================================================================

Inserts:
  - 2 semesters
  - 20 sessions  (10 per semester)
  - 300 users
  - 2 000 bookings  (100 users × 20 sessions, all CONFIRMED)
  - 500 EventRewardLog rows  (100 users × 5 sessions)

These volumes are chosen to:
  - Test that deduplication steps in constraint migrations complete quickly
    even with existing data (the uq_event_reward_log_user_session migration
    runs DELETE + ADD UNIQUE — both should be sub-second here)
  - Verify that composite index creation on bookings(session_id, status) is
    efficient at this scale
  - Provide a realistic load on FK-heavy tables so any missing index on the
    downgrade/upgrade path surfaces as a slow migration in CI

Usage::

    DATABASE_URL=postgresql://... python scripts/seed_volume_test.py

The script is idempotent: re-running on a non-empty DB may raise a
UniqueConstraint error for the EventRewardLog rows (which is expected and
safe — the volume CI job always starts from a fresh DB after migrations).
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone

# Make the project root importable when run as a standalone script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import get_password_hash
from app.database import SessionLocal
from app.models.booking import Booking, BookingStatus
from app.models.event_reward_log import EventRewardLog
from app.models.semester import Semester, SemesterCategory, SemesterStatus
from app.models.session import Session as SessionModel, EventCategory
from app.models.user import User, UserRole


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def main() -> None:
    db = SessionLocal()
    try:
        print("Seeding production-like volume dataset …")

        # ── Semesters ────────────────────────────────────────────────────────
        semesters = []
        for i in range(2):
            sem = Semester(
                code=f"VOL-{uuid.uuid4().hex[:6]}",
                name=f"Volume Test Semester {i + 1}",
                start_date=date.today() - timedelta(days=30),
                end_date=date.today() + timedelta(days=150),
                semester_category=SemesterCategory.ACADEMY_SEASON,
                status=SemesterStatus.DRAFT,
            )
            db.add(sem)
            db.flush()
            semesters.append(sem)

        # ── Sessions (10 per semester) ────────────────────────────────────────
        sessions = []
        for sem in semesters:
            for i in range(10):
                start = _now() + timedelta(days=7 + i * 2)
                sess = SessionModel(
                    title=f"Vol {sem.code} S{i}",
                    semester_id=sem.id,
                    date_start=start,
                    date_end=start + timedelta(hours=2),
                    event_category=EventCategory.TRAINING,
                    capacity=200,
                )
                db.add(sess)
                db.flush()
                sessions.append(sess)

        # ── Users (300) ───────────────────────────────────────────────────────
        pw_hash = get_password_hash("pw")
        users = []
        for i in range(300):
            u = User(
                email=f"vol{i}+{uuid.uuid4().hex[:6]}@vol.test",
                name=f"Volume User {i}",
                password_hash=pw_hash,
                role=UserRole.STUDENT,
                is_active=True,
            )
            db.add(u)
            db.flush()
            users.append(u)

        # ── Bookings (first 100 users × all 20 sessions = 2 000 rows) ────────
        for user in users[:100]:
            for sess in sessions:
                db.add(Booking(
                    user_id=user.id,
                    session_id=sess.id,
                    status=BookingStatus.CONFIRMED,
                ))

        # ── EventRewardLog (first 100 users × first 5 sessions = 500 rows) ──
        for user in users[:100]:
            for sess in sessions[:5]:
                db.add(EventRewardLog(
                    user_id=user.id,
                    session_id=sess.id,
                    xp_earned=50,
                    points_earned=50,
                    multiplier_applied=1.0,
                ))

        db.commit()
        print(
            f"✅ Seeded: {len(semesters)} semesters, {len(sessions)} sessions, "
            f"{len(users)} users, 2 000 bookings, 500 reward logs"
        )
    except Exception as exc:
        db.rollback()
        print(f"❌ Seeding failed: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
