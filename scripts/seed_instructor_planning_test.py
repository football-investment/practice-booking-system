"""
Instructor Planning — Testable Tournament Setup
================================================
Sets up tournament 7088 "F1rst LFA Cup (U18)" for live end-to-end testing
of the new two-phase instructor planning feature.

What this script does
---------------------
1. Creates Pálya 2 (campus 15) so we have 2 parallel pitches
2. Creates "Test Field Instructor 2" — a 3rd instructor user
3. Resets tournament 7088 to a clean, testable state:
   - start_date / end_date → today
   - status = ONGOING
   - tournament_status = ENROLLMENT_OPEN
   - master_instructor_id = 7477 (Grand Master)
4. Updates TournamentConfiguration: parallel_fields = 2
5. (Re-)generates 8 on-site match sessions spread across both pitches
6. Pre-populates the instructor roster:
   - MASTER slot  : Grand Master           (id=7477)
   - FIELD slot 1 : Smoke Test Instructor   (id=724)  → Pálya 1 (id=37)
   - FIELD slot 2 : Test Field Instructor 2 (new id)  → Pálya 2 (new id)

After running
-------------
Visit: http://localhost:8000/admin/tournaments/7088/edit
  → section-instructors shows 3 slots, all PLANNED
  → test checkin / absent / fallback plan via UI
  → 8 sessions exist → fallback shows reassignment map

Idempotent: re-running adjusts without duplicating.
"""

import os
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

# ── make sure project root is on path ────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/lfa_intern_system")

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.semester import Semester, SemesterStatus
from app.models.session import Session as SessionModel, SessionType
from app.models.pitch import Pitch
from app.models.campus import Campus
from app.models.tournament_configuration import TournamentConfiguration
from app.models.tournament_instructor_slot import (
    TournamentInstructorSlot, SlotRole, SlotStatus,
)

# ── Constants ────────────────────────────────────────────────────────────────
TOURNAMENT_ID     = 7088
CAMPUS_ID         = 15
MASTER_ID         = 7477   # Grand Master
FIELD_INSTRUCTOR1 = 724    # Smoke Test Instructor
PITCH1_ID         = 37     # Pálya 1 (already exists)
TODAY             = date.today()
NOW_BP            = datetime.now(ZoneInfo("Europe/Budapest")).replace(tzinfo=None)


def _upsert_pitch2(db: Session) -> Pitch:
    """Return existing Pálya 2 or create it."""
    existing = db.query(Pitch).filter(
        Pitch.campus_id == CAMPUS_ID,
        Pitch.name == "Pálya 2",
    ).first()
    if existing:
        print(f"  ♻️  Pálya 2 already exists (id={existing.id})")
        return existing
    pitch = Pitch(
        name="Pálya 2",
        pitch_number=2,
        campus_id=CAMPUS_ID,
        is_active=True,
    )
    db.add(pitch)
    db.flush()
    print(f"  ✅ Created Pálya 2 (id={pitch.id})")
    return pitch


def _upsert_field_instructor2(db: Session) -> User:
    """Return existing test instructor or create one."""
    existing = db.query(User).filter(
        User.email == "test.field.instructor2@lfa.com"
    ).first()
    if existing:
        print(f"  ♻️  Test Field Instructor 2 already exists (id={existing.id})")
        return existing
    user = User(
        name="Test Field Instructor 2",
        email="test.field.instructor2@lfa.com",
        password_hash="$2b$12$placeholder_not_for_login",
        role=UserRole.INSTRUCTOR,
        is_active=True,
        onboarding_completed=True,
    )
    db.add(user)
    db.flush()
    print(f"  ✅ Created Test Field Instructor 2 (id={user.id})")
    return user


def _reset_tournament(db: Session) -> Semester:
    """Set tournament to ENROLLMENT_OPEN state with today's date."""
    t = db.query(Semester).filter(Semester.id == TOURNAMENT_ID).first()
    if not t:
        print(f"  ❌ Tournament {TOURNAMENT_ID} not found — run the app first")
        sys.exit(1)
    t.start_date = TODAY
    t.end_date   = TODAY
    t.status     = SemesterStatus.ONGOING
    t.tournament_status = "ENROLLMENT_OPEN"
    t.master_instructor_id = MASTER_ID
    t.campus_id  = CAMPUS_ID
    db.flush()
    print(f"  ✅ Tournament {TOURNAMENT_ID}: status=ONGOING, t_status=ENROLLMENT_OPEN, date={TODAY}, master={MASTER_ID}")
    return t


def _set_parallel_fields(db: Session, n: int) -> None:
    cfg = db.query(TournamentConfiguration).filter(
        TournamentConfiguration.semester_id == TOURNAMENT_ID
    ).first()
    if cfg:
        cfg.parallel_fields = n
        db.flush()
        print(f"  ✅ parallel_fields → {n}")


def _recreate_sessions(db: Session, pitch1_id: int, pitch2_id: int,
                       instructor1_id: int, instructor2_id: int) -> int:
    """
    Drop existing auto-generated sessions and create 8 fresh ones
    (4 per pitch / per field instructor).
    """
    deleted = db.query(SessionModel).filter(
        SessionModel.semester_id == TOURNAMENT_ID,
    ).delete(synchronize_session=False)
    if deleted:
        print(f"  🗑️  Removed {deleted} old sessions")

    sessions = []
    base_start = NOW_BP.replace(hour=9, minute=0, second=0, microsecond=0)
    slot_min = 45   # match duration
    break_min = 10  # gap between matches

    for round_idx in range(4):
        offset_min = round_idx * (slot_min + break_min)
        s_start = base_start + timedelta(minutes=offset_min)
        s_end   = s_start + timedelta(minutes=slot_min)

        for pitch_id, instr_id, pitch_label in [
            (pitch1_id,  instructor1_id, "P1"),
            (pitch2_id,  instructor2_id, "P2"),
        ]:
            sess = SessionModel(
                title=f"F1rst Cup — {pitch_label} Round {round_idx + 1}",
                semester_id=TOURNAMENT_ID,
                session_type=SessionType.on_site,
                date_start=s_start,
                date_end=s_end,
                instructor_id=instr_id,
                campus_id=CAMPUS_ID,
                pitch_id=pitch_id,
                auto_generated=True,
                tournament_round=round_idx + 1,
            )
            sessions.append(sess)

    db.add_all(sessions)
    db.flush()
    print(f"  ✅ Created {len(sessions)} sessions ({len(sessions)//2} rounds × 2 pitches)")
    return len(sessions)


def _upsert_instructor_slots(db: Session, pitch1_id: int, pitch2_id: int,
                              instructor2_id: int) -> None:
    """
    Create MASTER + 2 FIELD slots, skip if already present.
    """
    def _existing(instructor_id: int) -> bool:
        return db.query(TournamentInstructorSlot).filter(
            TournamentInstructorSlot.semester_id == TOURNAMENT_ID,
            TournamentInstructorSlot.instructor_id == instructor_id,
        ).first() is not None

    # Remove ALL existing slots first (clean slate for test)
    deleted = db.query(TournamentInstructorSlot).filter(
        TournamentInstructorSlot.semester_id == TOURNAMENT_ID,
    ).delete(synchronize_session=False)
    if deleted:
        print(f"  🗑️  Removed {deleted} old instructor slots")

    slots = [
        TournamentInstructorSlot(
            semester_id=TOURNAMENT_ID,
            instructor_id=MASTER_ID,
            role=SlotRole.MASTER.value,
            pitch_id=None,
            status=SlotStatus.PLANNED.value,
            assigned_by=2,   # admin user id=2
        ),
        TournamentInstructorSlot(
            semester_id=TOURNAMENT_ID,
            instructor_id=FIELD_INSTRUCTOR1,
            role=SlotRole.FIELD.value,
            pitch_id=pitch1_id,
            status=SlotStatus.PLANNED.value,
            assigned_by=2,
            notes="Smoke Test Instructor → Pálya 1",
        ),
        TournamentInstructorSlot(
            semester_id=TOURNAMENT_ID,
            instructor_id=instructor2_id,
            role=SlotRole.FIELD.value,
            pitch_id=pitch2_id,
            status=SlotStatus.PLANNED.value,
            assigned_by=2,
            notes="Test Field Instructor 2 → Pálya 2",
        ),
    ]
    db.add_all(slots)
    db.flush()
    print(f"  ✅ Created 3 instructor slots: 1 MASTER + 2 FIELD")


def main() -> None:
    print("\n🏟️  Instructor Planning — Test Environment Setup")
    print("=" * 55)

    db = SessionLocal()
    try:
        print("\n[1] Pitches")
        pitch2 = _upsert_pitch2(db)

        print("\n[2] Instructors")
        instructor2 = _upsert_field_instructor2(db)

        print("\n[3] Tournament state")
        _reset_tournament(db)
        _set_parallel_fields(db, 2)

        print("\n[4] Sessions")
        n_sess = _recreate_sessions(
            db,
            pitch1_id=PITCH1_ID,
            pitch2_id=pitch2.id,
            instructor1_id=FIELD_INSTRUCTOR1,
            instructor2_id=instructor2.id,
        )

        print("\n[5] Instructor roster")
        _upsert_instructor_slots(
            db,
            pitch1_id=PITCH1_ID,
            pitch2_id=pitch2.id,
            instructor2_id=instructor2.id,
        )

        db.commit()

        print("\n" + "=" * 55)
        print("✅  Setup complete!")
        print()
        print(f"   🌐  http://localhost:8000/admin/tournaments/{TOURNAMENT_ID}/edit")
        print()
        print("   Tesztelési forgatókönyvek:")
        print("   ┌─────────────────────────────────────────────────┐")
        print("   │ 1. section-instructors → 3 slot látható (PLANNED)│")
        print("   │ 2. Grand Master → Check-in gomb                 │")
        print("   │ 3. Smoke Test Instructor → Absent jelölés        │")
        print("   │ 4. Fallback panel megjelenik                     │")
        print("   │ 5. Fallback terv betöltése → 4 session átrendezés│")
        print("   │ 6. Fallback alkalmazása → parallel_fields=1      │")
        print("   └─────────────────────────────────────────────────┘")
        print()
        print(f"   Részletek:")
        print(f"   - Torna:        #{TOURNAMENT_ID} F1rst LFA Cup (U18)")
        print(f"   - Dátum:        {TODAY} (ma)")
        print(f"   - Státusz:      ONGOING / ENROLLMENT_OPEN")
        print(f"   - Master:       Grand Master (id={MASTER_ID})")
        print(f"   - FIELD slot 1: Smoke Test Instructor (id={FIELD_INSTRUCTOR1}) → Pálya 1 (id={PITCH1_ID})")
        print(f"   - FIELD slot 2: Test Field Instructor 2 (id={instructor2.id}) → Pálya 2 (id={pitch2.id})")
        print(f"   - Sessions:     {n_sess} db (4 kör × 2 pálya)")

    except Exception as e:
        db.rollback()
        print(f"\n❌  Error: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
