"""
audit_campus_assignments.py

One-time (and repeatable) data quality audit:
  Find CAMP and TOURNAMENT semesters that have no campus_id assigned.

Domain rule: "A CAMP or TOURNAMENT cannot exist without a Campus."
  - campus_id is the physical venue (edzőpálya)
  - location_id is the city — not specific enough for operations

Usage:
  python scripts/audit_campus_assignments.py

Exit codes:
  0 — no violations found (safe to proceed with DB constraint migration)
  1 — violations found (fix required before migration)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.semester import Semester, SemesterCategory, SemesterStatus
from app.models.location import Location
from app.models.campus import Campus


def _status_priority(status_val: str) -> int:
    """Lower = more urgent to fix."""
    urgent = {"DRAFT", "SEEKING_INSTRUCTOR", "INSTRUCTOR_ASSIGNED", "READY_FOR_ENROLLMENT", "ONGOING"}
    return 0 if status_val in urgent else 1


def run_audit() -> int:
    db = SessionLocal()
    try:
        # --- Query: CAMP + TOURNAMENT with campus_id = NULL ----------------------
        violations = (
            db.query(Semester)
            .filter(
                Semester.semester_category.in_([
                    SemesterCategory.CAMP,
                    SemesterCategory.TOURNAMENT,
                ]),
                Semester.campus_id.is_(None),
            )
            .order_by(Semester.semester_category, Semester.status, Semester.id)
            .all()
        )

        if not violations:
            print("✅ CAMPUS ASSIGNMENT AUDIT PASSED")
            print("   No CAMP or TOURNAMENT records found without campus_id.")
            print("   Safe to apply DB CHECK constraint.")
            return 0

        # --- Load supporting data -----------------------------------------------
        loc_ids = {v.location_id for v in violations if v.location_id}
        location_map: dict[int, Location] = {}
        campus_options: dict[int, list[Campus]] = {}

        if loc_ids:
            locs = db.query(Location).filter(Location.id.in_(loc_ids)).all()
            location_map = {l.id: l for l in locs}
            campuses = db.query(Campus).filter(Campus.location_id.in_(loc_ids)).all()
            for c in campuses:
                campus_options.setdefault(c.location_id, []).append(c)

        # --- Report ---------------------------------------------------------------
        print("=" * 70)
        print("⚠️  CAMPUS ASSIGNMENT AUDIT — VIOLATIONS FOUND")
        print("=" * 70)
        print(f"   Found {len(violations)} CAMP/TOURNAMENT event(s) without campus_id\n")

        active_count = 0
        historical_count = 0

        for v in sorted(violations, key=lambda x: _status_priority(
                x.status.value if x.status else "")):

            status_val = v.status.value if v.status else "UNKNOWN"
            cat_val = v.semester_category.value if v.semester_category else "UNKNOWN"
            is_historical = status_val in ("CANCELLED", "COMPLETED")

            if is_historical:
                historical_count += 1
                urgency = "LOW PRIORITY"
                urgency_icon = "⬇️"
            else:
                active_count += 1
                urgency = "ACTION REQUIRED"
                urgency_icon = "🔴"

            print(f"  {urgency_icon} [{urgency}]")
            print(f"     ID          : {v.id}")
            print(f"     Code        : {v.code}")
            print(f"     Name        : {v.name}")
            print(f"     Category    : {cat_val}")
            print(f"     Status      : {status_val}")
            print(f"     Created     : {v.created_at.strftime('%Y-%m-%d') if v.created_at else '—'}")

            if v.location_id and v.location_id in location_map:
                loc = location_map[v.location_id]
                print(f"     Location    : {loc.city} ({loc.location_type.value}) [id={loc.id}]")
                options = campus_options.get(v.location_id, [])
                if options:
                    print(f"     Fix option  : Assign to one of these campuses:")
                    for c in options:
                        status_label = "✅ active" if c.is_active else "❌ inactive"
                        print(f"                   - {c.name} [id={c.id}] {status_label}")
                    print(f"                   → python scripts/fix_campus_assignments.py {v.id} <campus_id>")
                    print(f"                   → OR: /admin/events/{cat_val.lower()}s/{v.id}/edit")
                else:
                    print(f"     Fix option  : ⚠️ No campuses exist for location {loc.city} — add campus first")
            elif v.location_id:
                print(f"     Location    : [id={v.location_id}] (location not found — may be deleted)")
                print(f"     Fix option  : ⚠️ ORPHANED — location missing, manual review required")
            else:
                print(f"     Location    : None (no location set either)")
                print(f"     Fix option  : ⚠️ ORPHANED — no location, no campus")
                print(f"                   → Consider: delete if unused, or assign location + campus")

            print()

        # --- Summary --------------------------------------------------------------
        print("-" * 70)
        print("SUMMARY")
        print(f"  Total violations   : {len(violations)}")
        print(f"  Active (urgent)    : {active_count}  ← must fix before DB constraint")
        print(f"  Historical         : {historical_count}  ← low priority")
        print()
        print("NEXT STEPS")
        if active_count > 0:
            print("  1. Fix all active violations (assign campus_id via edit form or script)")
            print("  2. Re-run this audit: python scripts/audit_campus_assignments.py")
            print("  3. When output shows ✅ PASSED → apply Alembic migration:")
            print("     alembic upgrade chk_camp_tournament_requires_campus")
        else:
            print("  All active violations resolved.")
            print(f"  {historical_count} historical records remain (CANCELLED/COMPLETED) — OK to proceed.")
            print("  Apply DB CHECK constraint when ready:")
            print("     alembic upgrade chk_camp_tournament_requires_campus")
        print("=" * 70)

        return 1

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(run_audit())
