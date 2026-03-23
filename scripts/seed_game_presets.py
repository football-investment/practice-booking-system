"""
Seed Game Presets — source of truth for skill definitions.

Every preset defines:
  - which skills are assessed (skills_tested)
  - relative skill weights (skill_weights)
  - game metadata (category, min_players, difficulty)

Design principles:
  - NO hardcoded skills anywhere else in the codebase
  - If skill not in preset → that skill does NOT exist for that game
  - Admin can edit/extend any preset via /admin/game-presets
  - NO fallbacks — preset is the single source of truth

Idempotent: skips existing codes, only inserts missing ones.
Run: DATABASE_URL="..." python scripts/seed_game_presets.py
"""
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.game_preset import GamePreset


# ── Preset definitions ─────────────────────────────────────────────────────────
#
# skill_weights are relative multipliers — they do NOT need to sum to any fixed
# value. Higher weight = this skill is more strongly affected by this game type.
#
# Skills must use keys from app/skills_config.py (canonical system keys).
#
PRESETS = [
    {
        "code": "outfield_default",
        "name": "Outfield Football (Default)",
        "description": (
            "Baseline template for standard outfield football tournaments and training sessions. "
            "Covers core technical, mental, and physical skills for any field position. "
            "Admin can adjust weights or add skills for specific game variants."
        ),
        "is_recommended": True,
        "is_locked": False,
        "game_config": {
            "version": "1.0",
            "metadata": {
                "game_category": "FOOTBALL",
                "difficulty_level": "intermediate",
                "min_players": 4,
                "recommended_player_count": {"min": 8, "max": 32},
            },
            "skill_config": {
                # Skills actively assessed in this game type.
                # Order matters for UI display (most impactful first).
                "skills_tested": [
                    "ball_control",       # technical — core reception quality
                    "dribbling",          # technical — 1v1 dominance
                    "finishing",          # technical — goal conversion
                    "passing",            # technical — ball distribution
                    "vision",             # mental — reading the game
                    "positioning_off",    # mental — off-ball movement
                    "sprint_speed",       # physical — pace
                    "agility",            # physical — quick direction change
                    "stamina",            # physical — endurance
                ],
                # Relative multipliers: how strongly this game type
                # affects each skill's progression.
                # Higher = more impact on that skill per session/tournament.
                "skill_weights": {
                    "ball_control":    1.2,
                    "dribbling":       1.5,   # most visible in 1v1 game situations
                    "finishing":       1.4,   # goals are primary metric
                    "passing":         1.3,
                    "vision":          1.1,
                    "positioning_off": 1.1,
                    "sprint_speed":    1.0,
                    "agility":         1.0,
                    "stamina":         0.9,
                },
            },
            # format_config: override ranking/session structure (future use)
            "format_config": {},
            # simulation_config: variation/distribution params (future use)
            "simulation_config": {},
        },
    },
    {
        "code": "passing_focus",
        "name": "Passing & Vision Focus",
        "description": (
            "Specialised preset for passing-intensive game formats (possession, rondo, positional play). "
            "Vision and passing weighted highest; finishing is deprioritised. "
            "Ideal for score_based or time_based tournaments emphasising ball circulation."
        ),
        "is_recommended": False,
        "is_locked": False,
        "game_config": {
            "version": "1.0",
            "metadata": {
                "game_category": "FOOTBALL",
                "difficulty_level": "intermediate",
                "min_players": 4,
                "recommended_player_count": {"min": 6, "max": 24},
            },
            "skill_config": {
                "skills_tested": [
                    "passing",
                    "vision",
                    "ball_control",
                    "positioning_off",
                    "agility",
                    "stamina",
                ],
                "skill_weights": {
                    "passing":         1.8,
                    "vision":          1.6,
                    "ball_control":    1.4,
                    "positioning_off": 1.3,
                    "agility":         1.0,
                    "stamina":         0.8,
                },
            },
            "format_config": {},
            "simulation_config": {},
        },
    },
    {
        "code": "shooting_focus",
        "name": "Finishing & Shooting Focus",
        "description": (
            "Goal-conversion focused preset for shooting drills, finishing tournaments, and 1v1 formats. "
            "Finishing and sprint speed weighted highest; vision is deprioritised. "
            "Ideal for score_based tournaments where goals are the primary metric."
        ),
        "is_recommended": False,
        "is_locked": False,
        "game_config": {
            "version": "1.0",
            "metadata": {
                "game_category": "FOOTBALL",
                "difficulty_level": "intermediate",
                "min_players": 4,
                "recommended_player_count": {"min": 6, "max": 20},
            },
            "skill_config": {
                "skills_tested": [
                    "finishing",
                    "sprint_speed",
                    "dribbling",
                    "ball_control",
                    "agility",
                    "positioning_off",
                ],
                "skill_weights": {
                    "finishing":       2.0,
                    "sprint_speed":    1.6,
                    "dribbling":       1.5,
                    "ball_control":    1.2,
                    "agility":         1.1,
                    "positioning_off": 0.9,
                },
            },
            "format_config": {},
            "simulation_config": {},
        },
    },
]


def seed_game_presets():
    db: Session = SessionLocal()
    try:
        print("🎮 Seeding game presets (idempotent)...")
        print("=" * 70)

        created = 0
        skipped = 0

        for defn in PRESETS:
            existing = db.query(GamePreset).filter(
                GamePreset.code == defn["code"]
            ).first()

            if existing:
                print(f"⏭️  Already exists: {existing.name!r} ({existing.code})")
                skipped += 1
                continue

            preset = GamePreset(
                code=defn["code"],
                name=defn["name"],
                description=defn.get("description"),
                game_config=defn["game_config"],
                is_active=True,
                is_recommended=defn.get("is_recommended", False),
                is_locked=defn.get("is_locked", False),
            )
            db.add(preset)
            db.flush()
            print(f"✅ Created: {preset.name!r} ({preset.code}) id={preset.id}")
            created += 1

        db.commit()

        print()
        print("=" * 70)
        print(f"✅ Created: {created}  |  ⏭️  Skipped: {skipped}")
        print()

        # ── Summary: show all presets + their skill config ──────────────────
        all_presets = db.query(GamePreset).order_by(GamePreset.id).all()
        print(f"📋 GAME PRESETS IN DB ({len(all_presets)} total):")
        print()

        for p in all_presets:
            rec = "⭐ recommended" if p.is_recommended else ""
            lck = "🔒 locked" if p.is_locked else ""
            act = "✅ active" if p.is_active else "❌ inactive"
            tags = "  ".join(filter(None, [act, rec, lck]))
            print(f"  [{p.id}] {p.code}  —  {p.name}")
            print(f"       {tags}")

            skills = p.skills_tested       # via property: skill_config.skills_tested
            weights = p.skill_weights      # via property: skill_config.skill_weights

            if skills:
                print(f"       Skills assessed ({len(skills)}):")
                for sk in skills:
                    w = weights.get(sk, 1.0)
                    bar = "█" * int(w * 4)
                    print(f"         {sk:<22} weight={w:.1f}  {bar}")
            else:
                print("       ⚠️  skill_config.skills_tested is EMPTY — preset cannot drive skill assessment!")
            print()

        # ── How to read from code ─────────────────────────────────────────────
        print("📖 Code access pattern:")
        print("   preset = tournament.game_config_obj.game_preset")
        print("   preset.skills_tested   →", all_presets[0].skills_tested if all_presets else [])
        print("   preset.skill_weights   →", json.dumps(all_presets[0].skill_weights, indent=None) if all_presets else {})
        print("   preset.game_category   →", all_presets[0].game_category if all_presets else "—")
        print("   preset.difficulty_level →", all_presets[0].difficulty_level if all_presets else "—")
        print()
        print("   min_players guard (session_generator.py):")
        print("   →", all_presets[0].game_config.get("metadata", {}).get("min_players") if all_presets else "—")

    except Exception as e:
        db.rollback()
        print(f"\n❌ SEED FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_game_presets()
