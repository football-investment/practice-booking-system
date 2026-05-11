#!/usr/bin/env python3
"""
Backfill: Skill Taxonomy Expansion 29 → 44

Adds the 15 new skill keys (Phase 3) to every existing UserLicense.football_skills
JSONB record that is missing them. Existing keys are NEVER overwritten.

New skill fields for each missing key:
    system_baseline  = 60.0  (SYSTEM_BASELINE — fixed EMA anchor)
    baseline         = 60.0  (backward-compat alias)
    current_level    = 60.0  (starting visible level)
    self_assessment  = 60.0  (no prior onboarding input → neutral baseline)
    total_delta      = 0.0
    tournament_delta = 0.0
    assessment_delta = 0.0
    assessment_count = 0
    tournament_count = 0
    last_updated     = ISO timestamp of this backfill run

Usage:
    # Dry run (default — shows what WOULD change, writes nothing):
    DATABASE_URL="postgresql://..." python scripts/backfill_skill_expansion_29_to_44.py

    # Apply changes:
    DATABASE_URL="postgresql://..." python scripts/backfill_skill_expansion_29_to_44.py --apply

Idempotency:
    Safe to run multiple times. If a skill key already exists in football_skills,
    it is skipped — existing values are never overwritten.
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.attributes import flag_modified
from app.config import settings
from app.models.license import UserLicense
from app.skills_config import get_all_skill_keys

# All 15 new keys introduced in Phase 3
NEW_SKILL_KEYS = [
    # outfield (8)
    "shooting", "technique", "creativity", "long_passing",
    "flair", "touch", "forward_runs", "throwing",
    # mental (6)
    "anticipation", "concentration", "decisions",
    "determination", "teamwork", "leadership",
    # physical (1)
    "work_rate",
]

# Value applied to each missing skill field
_SYSTEM_BASELINE = 60.0


def _new_skill_entry(now_iso: str) -> dict:
    return {
        "system_baseline":  _SYSTEM_BASELINE,
        "baseline":         _SYSTEM_BASELINE,
        "current_level":    _SYSTEM_BASELINE,
        "self_assessment":  _SYSTEM_BASELINE,
        "total_delta":      0.0,
        "tournament_delta": 0.0,
        "assessment_delta": 0.0,
        "assessment_count": 0,
        "tournament_count": 0,
        "last_updated":     now_iso,
    }


def run(apply: bool = False):
    all_keys = set(get_all_skill_keys())
    expected_count = len(all_keys)

    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    mode = "APPLY" if apply else "DRY-RUN"
    print(f"{'='*60}")
    print(f"  Skill Expansion Backfill 29 → 44  [{mode}]")
    print(f"  Expected skill count after: {expected_count}")
    print(f"  New keys to add: {len(NEW_SKILL_KEYS)}")
    print(f"{'='*60}\n")

    now_iso = datetime.now(timezone.utc).isoformat()
    new_entry = _new_skill_entry(now_iso)

    licenses = db.query(UserLicense).filter(
        UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
        UserLicense.football_skills.isnot(None),
    ).all()

    total = len(licenses)
    updated = 0
    skipped_complete = 0
    skipped_no_skills = 0

    for lic in licenses:
        fs = lic.football_skills
        if not isinstance(fs, dict):
            skipped_no_skills += 1
            print(f"  SKIP  license {lic.id} (user {lic.user_id}): football_skills is not a dict")
            continue

        missing = [k for k in NEW_SKILL_KEYS if k not in fs]
        if not missing:
            skipped_complete += 1
            continue

        print(f"  {'WRITE' if apply else 'WOULD ADD'}  license {lic.id} (user {lic.user_id}): +{len(missing)} keys → {missing}")

        if apply:
            for key in missing:
                # Flat-format records ({"skill": 70.0}) → upgrade to full dict format
                fs[key] = new_entry.copy()
            flag_modified(lic, "football_skills")
            updated += 1

    if apply and updated > 0:
        db.commit()
        print(f"\n{'='*60}")
        print(f"  COMMIT: {updated} licenses updated")
    elif not apply:
        would_update = total - skipped_complete - skipped_no_skills
        print(f"\n{'='*60}")
        print(f"  DRY-RUN complete — {would_update} licenses would be updated")
        print(f"  Run with --apply to write changes.")
    else:
        print(f"\n{'='*60}")
        print(f"  Nothing to do — all licenses already have {expected_count} skills.")

    print(f"\n  Summary:")
    print(f"    Total LFA_FOOTBALL_PLAYER licenses: {total}")
    print(f"    Already complete (skipped):         {skipped_complete}")
    print(f"    Invalid football_skills (skipped):  {skipped_no_skills}")
    if apply:
        print(f"    Updated:                            {updated}")
    else:
        print(f"    Would update:                       {total - skipped_complete - skipped_no_skills}")
    print(f"{'='*60}")

    db.close()
    return updated if apply else (total - skipped_complete - skipped_no_skills)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill 15 new skills into UserLicense.football_skills")
    parser.add_argument("--apply", action="store_true", help="Write changes to DB (default: dry-run)")
    args = parser.parse_args()
    run(apply=args.apply)
