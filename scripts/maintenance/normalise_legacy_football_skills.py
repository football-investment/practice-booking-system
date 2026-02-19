"""
Legacy data migration — normalise pre-hardening football_skills records

Ticket: LEGACY-DEBT-001
Tracking: validate_skill_pipeline.py INV-S02/INV-S04 warnings

Background
----------
The 2026-02-19 concurrency hardening sprint (Phase B) identified two categories
of legacy data written by pre-hardening code:

  1. Float-format skill entries:
       football_skills["passing"] = 75.3   ← bare float (V1 / assessment-only)
     Target: {"baseline": 75.3, "current_level": 75.3, "tournament_delta": 0.0, ...}

  2. Out-of-bounds current_level values (< 40.0):
     Written by old code before the EMA 40.0 floor was enforced.
     Target: clamp to max(40.0, current_level).

This script normalises both in a single idempotent pass.

After running:
  - validate_skill_pipeline.py INV-S04 warnings → 0
  - validate_skill_pipeline.py INV-S02 float rate → drops toward 0%
    (residual float entries will be promoted by Step 1.5 on next tournament finalization)

Usage
-----
  # Dry-run (no writes):
  python scripts/maintenance/normalise_legacy_football_skills.py

  # Apply (writes to DB):
  python scripts/maintenance/normalise_legacy_football_skills.py --apply

  # Limit to specific users (for staged rollout):
  python scripts/maintenance/normalise_legacy_football_skills.py --apply --user-ids 4,5,6,14

Safety guarantees
-----------------
  - Runs inside a single transaction; on any error → full rollback
  - --apply flag required for writes (default: dry-run)
  - FOR UPDATE acquired on each UserLicense before mutation (serialises with
    concurrent tournament finalizations that also hold FOR UPDATE on the same row)
  - Idempotent: running twice produces the same result
  - Does NOT touch `baseline` for dict-format entries (onboarding data preserved)
  - Does NOT modify records where skills_last_updated_at >= 2026-02-19 (already
    normalised by the hardened Step 1.5 path)
"""
from __future__ import annotations

import sys
import os
import argparse
import json
from datetime import datetime, timezone
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

parser = argparse.ArgumentParser(description="Normalise legacy football_skills records")
parser.add_argument("--apply",    action="store_true",
                    help="Write changes to DB (default: dry-run)")
parser.add_argument("--user-ids", type=str, default=None,
                    help="Comma-separated user IDs to limit scope (default: all)")
args = parser.parse_args()

MIN_LEVEL   = 40.0
MAX_LEVEL   = 99.0
DEFAULT_VAL = 50.0
HARDENING_DATE = datetime(2026, 2, 19, tzinfo=timezone.utc)
RUN_AT = datetime.now(tz=timezone.utc)

DRY_RUN = not args.apply
user_id_filter: Optional[list[int]] = (
    [int(x.strip()) for x in args.user_ids.split(",")]
    if args.user_ids else None
)

mode_label = "DRY-RUN" if DRY_RUN else "APPLY"
print("=" * 65)
print(f"LEGACY FOOTBALL_SKILLS NORMALISATION  [{mode_label}]")
print(f"Run at : {RUN_AT.strftime('%Y-%m-%d %H:%M:%S UTC')}")
print(f"Scope  : {'user_ids=' + str(user_id_filter) if user_id_filter else 'ALL users'}")
print("=" * 65)

from app.database import SessionLocal
from app.models.license import UserLicense
from sqlalchemy.orm.attributes import flag_modified


def _normalise_entry(skill_name: str, val, existing_baseline: Optional[float]) -> dict:
    """
    Return a dict-format skill entry from any input format.

    If val is already a dict:
      - Clamp current_level to [40, 99]
      - Preserve all other fields
    If val is a scalar (float/int):
      - Promote to dict with baseline = current_level = clamp(float(val), 40, 99)
    """
    if isinstance(val, dict):
        cl = val.get("current_level")
        try:
            cl_f = float(cl) if cl is not None else DEFAULT_VAL
        except (TypeError, ValueError):
            cl_f = DEFAULT_VAL
        clamped = max(MIN_LEVEL, min(MAX_LEVEL, cl_f))
        if clamped != cl_f:
            return {**val, "current_level": clamped}
        return val  # no change needed
    else:
        try:
            scalar = float(val) if val is not None else DEFAULT_VAL
        except (TypeError, ValueError):
            scalar = DEFAULT_VAL
        clamped = max(MIN_LEVEL, min(MAX_LEVEL, scalar))
        baseline = existing_baseline if existing_baseline is not None else clamped
        return {
            "baseline":        baseline,
            "current_level":   clamped,
            "tournament_delta": 0.0,
            "total_delta":     round(clamped - baseline, 1),
            "tournament_count": 0,
            "normalised_at":   RUN_AT.isoformat(),
        }


def _already_normalised(skills: dict) -> bool:
    """Return True if all entries are already valid dict-format with clamped current_level."""
    for k, v in skills.items():
        if not isinstance(v, dict):
            return False
        cl = v.get("current_level")
        try:
            cl_f = float(cl) if cl is not None else None
        except (TypeError, ValueError):
            return False
        if cl_f is None or cl_f < MIN_LEVEL or cl_f > MAX_LEVEL:
            return False
    return True


db = SessionLocal()
try:
    query = db.query(UserLicense).filter(
        UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
        UserLicense.is_active == True,
        UserLicense.football_skills.isnot(None),
    )
    if user_id_filter:
        query = query.filter(UserLicense.user_id.in_(user_id_filter))

    # Load candidates (no FOR UPDATE yet — we do it per-row below)
    candidates = query.all()
    print(f"\nFound {len(candidates)} active LFA_FOOTBALL_PLAYER license(s) with skills.\n")

    changed_count     = 0
    already_ok_count  = 0
    skipped_hardened  = 0
    float_promoted    = 0
    level_clamped     = 0
    error_count       = 0

    for lic in candidates:
        skills = lic.football_skills
        if not isinstance(skills, dict) or not skills:
            continue

        # Skip licenses already normalised by the hardened Step 1.5 path
        last_updated = lic.skills_last_updated_at
        if last_updated:
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=timezone.utc)
            if last_updated >= HARDENING_DATE and _already_normalised(skills):
                skipped_hardened += 1
                continue

        if _already_normalised(skills):
            already_ok_count += 1
            continue

        # Build normalised copy
        updated = {}
        row_float_promoted = 0
        row_level_clamped  = 0
        for sk, val in skills.items():
            existing_baseline = None
            if isinstance(val, dict):
                try:
                    existing_baseline = float(val.get("baseline", DEFAULT_VAL))
                except (TypeError, ValueError):
                    existing_baseline = DEFAULT_VAL
            new_val = _normalise_entry(sk, val, existing_baseline)
            if new_val is not val and new_val != val:
                if not isinstance(val, dict):
                    row_float_promoted += 1
                elif new_val.get("current_level") != val.get("current_level"):
                    row_level_clamped += 1
            updated[sk] = new_val

        float_promoted += row_float_promoted
        level_clamped  += row_level_clamped

        print(
            f"  license_id={lic.id}  user_id={lic.user_id}  "
            f"float→dict={row_float_promoted}  clamped={row_level_clamped}"
            + ("  [DRY-RUN: no write]" if DRY_RUN else "")
        )

        if not DRY_RUN:
            try:
                # Re-fetch with FOR UPDATE — serialises with concurrent tournament Step 1.5
                locked = (
                    db.query(UserLicense)
                    .filter(UserLicense.id == lic.id)
                    .with_for_update()
                    .first()
                )
                if locked is None:
                    print(f"    ⚠️  license_id={lic.id} disappeared — skipping")
                    continue

                # Re-normalise from locked row (may differ from candidate snapshot)
                skills_locked = locked.football_skills or {}
                updated_locked = {}
                for sk, val in skills_locked.items():
                    existing_baseline = None
                    if isinstance(val, dict):
                        try:
                            existing_baseline = float(val.get("baseline", DEFAULT_VAL))
                        except (TypeError, ValueError):
                            existing_baseline = DEFAULT_VAL
                    updated_locked[sk] = _normalise_entry(sk, val, existing_baseline)

                locked.football_skills = updated_locked
                locked.skills_last_updated_at = RUN_AT
                flag_modified(locked, "football_skills")
                changed_count += 1

            except Exception as exc:
                print(f"    ❌ ERROR on license_id={lic.id}: {exc}")
                error_count += 1
        else:
            changed_count += 1

    if not DRY_RUN:
        if error_count == 0:
            db.commit()
            print(f"\n✅ Transaction committed.")
        else:
            db.rollback()
            print(f"\n❌ {error_count} error(s) — transaction rolled back.")
            sys.exit(1)

except Exception as exc:
    db.rollback()
    print(f"\n❌ Unexpected error — transaction rolled back: {exc}")
    raise
finally:
    db.close()

print("\n" + "=" * 65)
print(f"Summary [{mode_label}]")
print(f"  Licenses processed          : {changed_count}")
print(f"  Already normalised (skipped): {already_ok_count}")
print(f"  Already hardened  (skipped) : {skipped_hardened}")
print(f"  Float entries promoted      : {float_promoted}")
print(f"  current_level values clamped: {level_clamped}")
if error_count:
    print(f"  Errors                      : {error_count}")
print("=" * 65)

if DRY_RUN:
    print("\n⚠️  DRY-RUN mode — no changes written. Re-run with --apply to apply.")
else:
    print(f"\n✅ Done. Run validate_skill_pipeline.py to confirm 0 legacy warnings.")
