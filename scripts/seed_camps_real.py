#!/usr/bin/env python3
"""
Minimal real-data seed for camp admin validation.

Usage:
    python scripts/seed_camps_real.py

Design: ADDITIVE + IDEMPOTENT
  - Uses location_code / semester code to detect existing records
  - Safe to run on any DB state (no truncation, no data loss)
  - Uses real Hungarian location names and meaningful camp data

Result dataset:
  2 Locations  :  Budapest (CENTER)  ·  Debrecen (PARTNER)
  3 Campuses   :  2 × Budapest  ·  1 × Debrecen
  3 Camps      :  PRE (Budapest, READY) · YOUTH (Budapest, DRAFT) · GánCuju (Debrecen, INSTRUCTOR_ASSIGNED)
"""
import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models.location import Location, LocationType
from app.models.campus import Campus
from app.models.semester import Semester, SemesterStatus, SemesterCategory
from app.models.user import User, UserRole


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_or_create_location(db, location_code: str, city: str, **kwargs) -> Location:
    # city has a UNIQUE constraint — use as primary lookup key
    loc = db.query(Location).filter(Location.city == city).first()
    if not loc:
        loc = Location(location_code=location_code, city=city, **kwargs)
        db.add(loc)
        db.flush()
        print(f"   ✓ Created: {loc.city} ({loc.location_type.value})")
    else:
        print(f"   → Reuse:   {loc.city} ({loc.location_type.value}) id={loc.id}")
    return loc


def _get_or_create_campus(db, location_id: int, name: str, **kwargs) -> Campus:
    cam = db.query(Campus).filter(
        Campus.location_id == location_id, Campus.name == name
    ).first()
    if not cam:
        cam = Campus(location_id=location_id, name=name, **kwargs)
        db.add(cam)
        db.flush()
        print(f"   ✓ Created: {name}")
    else:
        print(f"   → Reuse:   {name} id={cam.id}")
    return cam


def _get_or_create_camp(db, code: str, **kwargs) -> Semester:
    camp = db.query(Semester).filter(Semester.code == code).first()
    if not camp:
        camp = Semester(
            code=code,
            semester_category=SemesterCategory.CAMP,
            **kwargs,
        )
        db.add(camp)
        db.flush()
        print(f"   ✓ Created: {camp.name}")
    else:
        print(f"   → Reuse:   {camp.name} id={camp.id}")
    return camp


# ── main seed ─────────────────────────────────────────────────────────────────

def seed():
    db = SessionLocal()
    try:
        today = date.today()

        # ── 1. Locations ──────────────────────────────────────────────────────
        print("\n📍 Locations…")
        budapest = _get_or_create_location(
            db,
            location_code="BUD",
            city="Budapest",
            name="LFA Budapest Education Center",
            country="Hungary",
            country_code="HU",
            postal_code="1146",
            address="Istvánmezei út 1-3, Budapest",
            location_type=LocationType.CENTER,
            is_active=True,
        )
        debrecen = _get_or_create_location(
            db,
            location_code="DEB",
            city="Debrecen",
            name="LFA Debrecen Partner",
            country="Hungary",
            country_code="HU",
            postal_code="4031",
            address="Oláh Gábor u. 5, Debrecen",
            location_type=LocationType.PARTNER,
            is_active=True,
        )

        # ── 2. Campuses ───────────────────────────────────────────────────────
        print("\n🏫 Campuses…")
        buda_zuglo = _get_or_create_campus(
            db,
            budapest.id,
            "LFA Akadémia Budapest (Zugló)",
            venue="Főépület + kültéri pályák",
            address="Istvánmezei út 1-3, 1146 Budapest",
            is_active=True,
        )
        buda_kelenfold = _get_or_create_campus(
            db,
            budapest.id,
            "LFA Edzőközpont Kelenföld",
            venue="Beltéri csarnok, 3 pálya",
            address="Szerémi út 4, 1117 Budapest",
            is_active=True,
        )
        debr_stadion = _get_or_create_campus(
            db,
            debrecen.id,
            "Debrecen Football Club Stadion",
            venue="DFC főpálya + edzőpályák",
            address="Oláh Gábor u. 5, 4031 Debrecen",
            is_active=True,
        )

        # ── 3. Look up first active instructor ────────────────────────────────
        first_instructor = (
            db.query(User)
            .filter(User.role == UserRole.INSTRUCTOR, User.is_active == True)
            .order_by(User.id)
            .first()
        )
        instructor_id = first_instructor.id if first_instructor else None
        if instructor_id:
            print(f"\n👤 Master instructor: {first_instructor.name} (id={instructor_id})")
        else:
            print("\n👤 No active instructor found — master_instructor_id = NULL")

        # ── 4. CAMP semesters ─────────────────────────────────────────────────
        print("\n⛺ Camps…")

        # C1: Budapest CENTER — PRE — READY_FOR_ENROLLMENT
        c1 = _get_or_create_camp(
            db,
            code="CAMP-NYTABOR-PRE-BUD-2026",
            name="LFA Nyári Tábor 2026 – PRE",
            status=SemesterStatus.READY_FOR_ENROLLMENT,
            age_group="PRE",
            specialization_type="LFA_PLAYER_PRE",
            theme="Nyári Futball Intenzív",
            focus_description=(
                "5-13 éves korosztály számára tervezett intenzív nyári tábor. "
                "Alapkészségek fejlesztése játékos, versenyszerű formában."
            ),
            location_id=budapest.id,
            campus_id=buda_zuglo.id,
            start_date=today + timedelta(days=45),
            end_date=today + timedelta(days=52),
            enrollment_cost=800,
            master_instructor_id=instructor_id,
        )

        # C2: Budapest CENTER — YOUTH — DRAFT (no instructor yet)
        c2 = _get_or_create_camp(
            db,
            code="CAMP-ELITE-YOUTH-BUD-2026-Q3",
            name="LFA Elite Youth Camp Q3 2026",
            status=SemesterStatus.DRAFT,
            age_group="YOUTH",
            specialization_type="LFA_PLAYER_YOUTH",
            theme="Elite Performance Q3",
            focus_description=(
                "14-18 éves versenyzők számára tervezett fejlesztési tábor. "
                "Taktika, erőnlét és páros technikai edzések kombinációja."
            ),
            location_id=budapest.id,
            campus_id=buda_kelenfold.id,
            start_date=today + timedelta(days=90),
            end_date=today + timedelta(days=97),
            enrollment_cost=1200,
            master_instructor_id=None,  # DRAFT — instructor not yet assigned
        )

        # C3: Debrecen PARTNER — GánCuju — INSTRUCTOR_ASSIGNED (mixed age)
        c3 = _get_or_create_camp(
            db,
            code="CAMP-GANCUJU-DEBR-2026",
            name="GánCuju Nyári Intenzív 2026",
            status=SemesterStatus.INSTRUCTOR_ASSIGNED,
            age_group=None,  # korosztálytól független
            specialization_type="GANCUJU_PLAYER",
            theme="Nyári GánCuju Intenzív",
            focus_description=(
                "Tradicionális kínai labdarúgás alapjai. Korosztálytól független, "
                "minden szinten bevezető intenzív tábor Debrecenben."
            ),
            location_id=debrecen.id,
            campus_id=debr_stadion.id,
            start_date=today + timedelta(days=30),
            end_date=today + timedelta(days=37),
            enrollment_cost=600,
            master_instructor_id=instructor_id,
        )

        db.commit()

        # ── Summary ───────────────────────────────────────────────────────────
        print(f"\n✅ Seed complete!")
        print(f"   Locations  : Budapest CENTER (id={budapest.id}) · Debrecen PARTNER (id={debrecen.id})")
        print(f"   Campuses   : Zugló · Kelenföld · DFC Stadion")
        print(f"   Camps      :")
        print(f"     {c1.name}  [{c1.status.value}]  id={c1.id}")
        print(f"     {c2.name}  [{c2.status.value}]  id={c2.id}")
        print(f"     {c3.name}  [{c3.status.value}]  id={c3.id}")
        print(f"\n   → http://localhost:8000/admin/events")
        print(f"   → http://localhost:8000/admin/camps")
        print(f"   → http://localhost:8000/admin/camps/{c1.id}/edit")
        print(f"   → http://localhost:8000/admin/camps/{c2.id}/edit")
        print(f"   → http://localhost:8000/admin/camps/{c3.id}/edit")

    except Exception as exc:
        db.rollback()
        import traceback
        print(f"\n❌ Seed failed: {exc}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
