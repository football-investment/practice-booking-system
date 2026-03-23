"""
Fix report_* test users so they can log into the app.

Actions:
1. Set a real bcrypt password ("Player1234!")
2. Set user.specialization = LFA_FOOTBALL_PLAYER (required for /skills/data)
3. Recalculate skill_points_awarded + skill_rating_delta for each existing participation
4. Propagate EMA deltas to FootballSkillAssessment rows

Run: python scripts/seed_report_users_login.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.license import UserLicense
from app.models.specialization import SpecializationType
from app.models.tournament_achievement import TournamentParticipation
from app.models.semester import Semester
from app.services.tournament.tournament_participation_service import (
    calculate_skill_points_for_placement,
    record_tournament_participation,
)
from app.core.security import get_password_hash

PASSWORD = "Player1234!"
TARGET_EMAILS = [
    "report_940c5c73@t.com",   # P1-P940c  (1st, participant, 3rd)
    "report_7b85cdfa@t.com",   # P2-P7b85  (2nd, 1st, participant)
    "report_490c3e64@t.com",   # P3-P490c  (3rd, 2nd, 1st)
    "report_9ab12d42@t.com",   # P4-P9ab1  (participant, 3rd, 2nd)
]


def main():
    db = SessionLocal()
    try:
        hashed = get_password_hash(PASSWORD)
        print(f"Password hash computed. Updating {len(TARGET_EMAILS)} users…\n")

        for email in TARGET_EMAILS:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                print(f"  SKIP {email} — not found in DB")
                continue

            # 1. Fix password
            user.password_hash = hashed

            # 2. Fix specialization (needed for /progress and /skills routing)
            user.specialization = SpecializationType.LFA_FOOTBALL_PLAYER

            # 3. Fix license started_at (must not be NULL)
            license = db.query(UserLicense).filter(
                UserLicense.user_id == user.id,
                UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
            ).first()
            if license and license.started_at is None:
                from datetime import datetime, timezone
                license.started_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

            db.flush()

            # 4. Recalculate skill data for each participation
            participations = (
                db.query(TournamentParticipation)
                .filter(TournamentParticipation.user_id == user.id)
                .order_by(TournamentParticipation.achieved_at)
                .all()
            )

            print(f"  {email} (id={user.id}) — {len(participations)} tournaments")
            for tp in participations:
                sem = db.query(Semester).filter(Semester.id == tp.semester_id).first()
                sem_name = sem.name if sem else f"T#{tp.semester_id}"

                # Calculate skill points for this placement
                skill_pts = calculate_skill_points_for_placement(db, tp.semester_id, tp.placement)

                # Force-reset skill_rating_delta so record_tournament_participation recomputes it
                tp.skill_rating_delta = None
                db.flush()

                # Recalculate via service (updates skill_points_awarded, skill_rating_delta, assessments)
                record_tournament_participation(
                    db=db,
                    user_id=user.id,
                    tournament_id=tp.semester_id,
                    placement=tp.placement,
                    skill_points=skill_pts,
                    base_xp=0,    # don't double-award XP
                    credits=0,    # don't double-award credits
                )
                total_pts = round(sum(skill_pts.values()), 1)
                print(f"    [{sem_name}] placement={tp.placement} → {total_pts} skill pts, skills={list(skill_pts.keys())[:3]}…")

        db.commit()
        print("\n✅ Done. Users can now log in with:")
        for email in TARGET_EMAILS:
            print(f"   email: {email}   password: {PASSWORD}")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
