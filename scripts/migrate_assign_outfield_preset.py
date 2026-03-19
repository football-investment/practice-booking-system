"""
Phase 4 Migration — Assign outfield_default preset to all GameConfigurations without a preset.

This migration:
  1. Verifies the outfield_default preset exists and has valid skill_config
  2. For every game_configuration with game_preset_id IS NULL:
     - Sets game_preset_id = <outfield_default.id>
     - Logs full detail: config_id, semester_id, tournament_name, reward_config status
  3. Warns on non-standard skill mapping counts (< or > 4 skills in reward_config)
  4. Is IDEMPOTENT: configs already having a preset are skipped with a log

Snapshot saved BEFORE running:
  scripts/migrations/snapshots/game_configs_pre_migration_2026_03_18.csv

Run:
  DATABASE_URL="..." python scripts/migrate_assign_outfield_preset.py
  (or rely on .env — the script loads it via app.database)
"""
import sys
import os
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session, joinedload
from app.database import SessionLocal
from app.models.game_preset import GamePreset
from app.models.game_configuration import GameConfiguration
from app.models.semester import Semester
from app.models.tournament_reward_config import TournamentRewardConfig as TournamentRewardConfigModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("migrate_assign_outfield_preset")

# ── Standard skill count for these seed tournaments (4 skills each) ──────────
_STANDARD_SKILL_COUNT = 4
_OUTFIELD_PRESET_CODE = "outfield_default"


def _get_tournament_type(db: Session, semester_id: int) -> str:
    """Best-effort: return tournament type info for logging."""
    try:
        from app.models.tournament_configuration import TournamentConfiguration
        tc = db.query(TournamentConfiguration).filter(
            TournamentConfiguration.semester_id == semester_id
        ).first()
        if tc:
            tt = tc.tournament_type
            if tt:
                return f"{tt.code} (scoring={tc.scoring_type})"
            return f"config_id={tc.id} scoring={tc.scoring_type}"
    except Exception:
        pass
    return "unknown"


def migrate(dry_run: bool = False) -> dict:
    db: Session = SessionLocal()
    results = {"migrated": 0, "skipped": 0, "warnings": 0, "errors": 0}

    try:
        print("=" * 70)
        print("Phase 4 Migration: Assign outfield_default preset to all configs")
        print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE'}")
        print("=" * 70)
        print()

        # ── Step 1: Verify preset exists and is valid ─────────────────────────
        preset = db.query(GamePreset).filter(
            GamePreset.code == _OUTFIELD_PRESET_CODE,
            GamePreset.is_active == True,
        ).first()

        if not preset:
            logger.error(
                "ABORT: preset '%s' not found or inactive. "
                "Run scripts/seed_game_presets.py first.",
                _OUTFIELD_PRESET_CODE,
            )
            sys.exit(1)

        if not preset.skills_tested or not preset.skill_weights:
            logger.error(
                "ABORT: preset '%s' (id=%d) has empty skill_config. "
                "Seed is corrupted — re-run scripts/seed_game_presets.py.",
                preset.code, preset.id,
            )
            sys.exit(1)

        print(f"✅ Preset verified: '{preset.code}' (id={preset.id})")
        print(f"   Skills ({len(preset.skills_tested)}): {', '.join(preset.skills_tested)}")
        print()

        # ── Step 2: Load all configs without preset ───────────────────────────
        configs_to_migrate = (
            db.query(GameConfiguration)
            .filter(GameConfiguration.game_preset_id == None)  # noqa: E711
            .order_by(GameConfiguration.id)
            .all()
        )

        configs_already_set = (
            db.query(GameConfiguration)
            .filter(GameConfiguration.game_preset_id != None)  # noqa: E711
            .count()
        )

        print(f"📋 GameConfiguration summary:")
        print(f"   To migrate (preset=NULL):  {len(configs_to_migrate)}")
        print(f"   Already set (skip):         {configs_already_set}")
        print()

        if not configs_to_migrate:
            print("✅ Nothing to migrate — all configs already have a preset.")
            return results

        # ── Step 3: Migrate each config ───────────────────────────────────────
        print("🔄 Processing configs:")
        print("-" * 70)

        for gc in configs_to_migrate:
            semester = db.query(Semester).filter(
                Semester.id == gc.semester_id
            ).first()

            if not semester:
                logger.error(
                    "  ❌ config_id=%d: semester_id=%d NOT FOUND — skipping",
                    gc.id, gc.semester_id,
                )
                results["errors"] += 1
                continue

            # ── Gather reward_config skill_mappings info ──────────────────────
            reward_cfg = db.query(TournamentRewardConfigModel).filter(
                TournamentRewardConfigModel.semester_id == semester.id
            ).first()

            skill_mappings_in_reward = 0
            reward_skills_sample = []
            if reward_cfg and reward_cfg.reward_config:
                mappings = reward_cfg.reward_config.get("skill_mappings", [])
                if isinstance(mappings, list):
                    skill_mappings_in_reward = len(mappings)
                    reward_skills_sample = [
                        m.get("skill", "?") for m in mappings[:3]
                    ]

            # ── Tournament type ───────────────────────────────────────────────
            tournament_type_str = _get_tournament_type(db, semester.id)

            # ── Non-standard skill mapping warning ────────────────────────────
            if skill_mappings_in_reward > 0 and skill_mappings_in_reward != _STANDARD_SKILL_COUNT:
                logger.warning(
                    "non_standard_skill_mapping_detected: config_id=%d semester_id=%d "
                    "name='%s' reward_config.skill_mappings=%d (expected %d). "
                    "Review before Phase 5 legacy removal.",
                    gc.id, semester.id, semester.name,
                    skill_mappings_in_reward, _STANDARD_SKILL_COUNT,
                )
                results["warnings"] += 1

            # ── Log the migration detail ──────────────────────────────────────
            skills_info = (
                f"{skill_mappings_in_reward} skills ({', '.join(reward_skills_sample)}...)"
                if reward_skills_sample else "none"
            )
            print(
                f"  {'[DRY]' if dry_run else '✅'} "
                f"config_id={gc.id:>4}  semester={semester.id:>6}  "
                f"status={semester.status!r:<12}  "
                f"type={tournament_type_str}"
            )
            print(
                f"       name='{semester.name}'"
            )
            print(
                f"       reward_config.skill_mappings: {skills_info}"
            )
            print(
                f"       → assigning preset_id={preset.id} ({preset.code})"
            )
            print()

            if not dry_run:
                gc.game_preset_id = preset.id
                db.add(gc)
                results["migrated"] += 1
            else:
                results["migrated"] += 1  # count as "would migrate"

        # ── Step 4: Commit ────────────────────────────────────────────────────
        if not dry_run:
            db.commit()
            print("-" * 70)
            print(f"✅ Committed to DB")
        else:
            db.rollback()
            print("-" * 70)
            print(f"[DRY RUN] No changes committed.")

        # ── Step 5: Post-migration verification ──────────────────────────────
        print()
        print("=" * 70)
        print("📊 POST-MIGRATION VERIFICATION")
        print("=" * 70)

        null_count = (
            db.query(GameConfiguration)
            .filter(GameConfiguration.game_preset_id == None)  # noqa: E711
            .count()
        )
        total_count = db.query(GameConfiguration).count()
        set_count = total_count - null_count

        print(f"  Total game_configurations:  {total_count}")
        print(f"  With preset (game_preset_id IS NOT NULL):  {set_count}")
        print(f"  Without preset (NULL):       {null_count}")
        print()

        if null_count == 0 and not dry_run:
            print("✅ SUCCESS: All game_configurations now have a preset assigned.")
            print("   → Safe to run Alembic NOT NULL migration.")
        elif dry_run:
            print(f"[DRY RUN] Would migrate {results['migrated']} configs.")
            print(f"   After migration, NULL count would be: {null_count - results['migrated']}")
        else:
            print(f"⚠️  WARNING: {null_count} configs still have NULL preset — investigate!")

        if results["warnings"] > 0:
            print()
            print(f"⚠️  {results['warnings']} non-standard skill mapping warning(s) logged above.")
            print("   Review these before Phase 5 legacy removal.")

        print()
        print(
            f"Summary: migrated={results['migrated']}  "
            f"skipped={results['skipped']}  "
            f"warnings={results['warnings']}  "
            f"errors={results['errors']}"
        )
        print()

    except Exception as e:
        db.rollback()
        logger.error("MIGRATION FAILED: %s", e)
        import traceback
        traceback.print_exc()
        results["errors"] += 1
        raise
    finally:
        db.close()

    return results


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    migrate(dry_run=dry_run)
