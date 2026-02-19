#!/usr/bin/env python3
"""
Seed Star Players - Loads from tests/e2e/test_users.json

Reads all entries from star_users[] and inserts them into the DB.
Idempotent: existing users are skipped (ON CONFLICT).
Writes db_id back to test_users.json after successful insert.

Usage:
    DATABASE_URL="postgresql://..." python scripts/seed_star_players.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.attributes import flag_modified
from app.config import settings
from app.models.user import User
from app.models.license import UserLicense
from app.models.xp_transaction import XPTransaction  # noqa: F401 — required for relationship
from app.core.security import get_password_hash

TEST_USERS_JSON = project_root / "tests" / "e2e" / "test_users.json"

# Position → all 29 skill values (0-100 scale, matching app/skills_config.py)
# Categories: outfield(11), set_pieces(3), mental(8), physical(7)
POSITION_SKILLS = {
    "STRIKER": {
        # outfield
        "ball_control":   85, "dribbling":     80, "finishing":      95,
        "shot_power":     90, "long_shots":    80, "volleys":        78,
        "crossing":       55, "passing":       70, "heading":        82,
        "tackle":         30, "marking":       25,
        # set_pieces
        "free_kicks":     72, "corners":       55, "penalties":      88,
        # mental
        "positioning_off": 90, "positioning_def": 35, "vision":        72,
        "aggression":     75, "reactions":     82, "composure":      80,
        "consistency":    78, "tactical_awareness": 72,
        # physical
        "acceleration":   88, "sprint_speed":  90, "agility":        82,
        "jumping":        80, "strength":      78, "stamina":        80,
        "balance":        78,
    },
    "MIDFIELDER": {
        # outfield
        "ball_control":   85, "dribbling":     80, "finishing":      68,
        "shot_power":     70, "long_shots":    72, "volleys":        65,
        "crossing":       75, "passing":       92, "heading":        68,
        "tackle":         72, "marking":       70,
        # set_pieces
        "free_kicks":     75, "corners":       72, "penalties":      72,
        # mental
        "positioning_off": 82, "positioning_def": 78, "vision":        90,
        "aggression":     72, "reactions":     80, "composure":      85,
        "consistency":    85, "tactical_awareness": 90,
        # physical
        "acceleration":   78, "sprint_speed":  75, "agility":        80,
        "jumping":        70, "strength":      72, "stamina":        90,
        "balance":        80,
    },
    "DEFENDER": {
        # outfield
        "ball_control":   72, "dribbling":     60, "finishing":      45,
        "shot_power":     65, "long_shots":    58, "volleys":        50,
        "crossing":       62, "passing":       75, "heading":        85,
        "tackle":         92, "marking":       90,
        # set_pieces
        "free_kicks":     60, "corners":       62, "penalties":      65,
        # mental
        "positioning_off": 55, "positioning_def": 92, "vision":        75,
        "aggression":     85, "reactions":     82, "composure":      82,
        "consistency":    85, "tactical_awareness": 85,
        # physical
        "acceleration":   75, "sprint_speed":  72, "agility":        72,
        "jumping":        85, "strength":      88, "stamina":        85,
        "balance":        78,
    },
    "GOALKEEPER": {
        # outfield
        "ball_control":   65, "dribbling":     45, "finishing":      35,
        "shot_power":     55, "long_shots":    50, "volleys":        40,
        "crossing":       48, "passing":       68, "heading":        65,
        "tackle":         50, "marking":       55,
        # set_pieces
        "free_kicks":     50, "corners":       48, "penalties":      60,
        # mental
        "positioning_off": 55, "positioning_def": 90, "vision":        78,
        "aggression":     72, "reactions":     92, "composure":      88,
        "consistency":    85, "tactical_awareness": 82,
        # physical
        "acceleration":   68, "sprint_speed":  65, "agility":        80,
        "jumping":        88, "strength":      82, "stamina":        78,
        "balance":        85,
    },
}


def _load_json():
    with open(TEST_USERS_JSON, encoding="utf-8") as f:
        return json.load(f)


def _write_db_ids(id_map: dict):
    """Write db_ids back to test_users.json for star_users section."""
    data = _load_json()
    for user in data["star_users"]:
        if user["email"] in id_map:
            user["db_id"] = id_map[user["email"]]
    with open(TEST_USERS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"   ✅ db_ids written back to test_users.json ({len(id_map)} entries)")


def create_star_players():
    data = _load_json()
    star_users = data["star_users"]

    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    print("🌟 ═══════════════════════════════════════════════════════")
    print(f"🌟 STAR PLAYERS SEED  ({len(star_users)} players from test_users.json)")
    print("🌟 ═══════════════════════════════════════════════════════\n")

    created, skipped = 0, 0
    id_map = {}

    try:
        for p in star_users:
            email = p["email"]

            existing = db.query(User).filter(User.email == email).first()
            if existing:
                print(f"⚠️  {p['first_name']} {p['last_name']} ({email}) already exists — SKIPPED")
                id_map[email] = existing.id
                # Fix up license if previously seeded with missing fields
                existing_license = db.query(UserLicense).filter(
                    UserLicense.user_id == existing.id,
                    UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER"
                ).first()
                if existing_license and (
                    not existing_license.payment_verified or
                    existing_license.average_motivation_score is None
                ):
                    existing_license.payment_verified = True
                    if existing_license.payment_verified_at is None:
                        existing_license.payment_verified_at = datetime.now(timezone.utc)
                    if existing_license.average_motivation_score is None:
                        fix_skills = p.get("skills") or POSITION_SKILLS.get(p["position"], POSITION_SKILLS["MIDFIELDER"])
                        existing_license.average_motivation_score = round(sum(fix_skills.values()) / len(fix_skills), 1)
                        existing_license.motivation_last_assessed_at = datetime.now(timezone.utc)
                        existing_license.motivation_assessed_by = existing.id
                    db.commit()
                    print(f"   🔧 License fixed (payment_verified + assessment fields)")
                skipped += 1
                continue

            skills = p.get("skills") or POSITION_SKILLS.get(p["position"], POSITION_SKILLS["MIDFIELDER"])
            avg_skill = round(sum(skills.values()) / len(skills), 1)

            # Build engine-compatible football_skills structure
            now_iso = datetime.now(timezone.utc).isoformat()
            football_skills = {
                skill_key: {
                    "current_level": float(value),
                    "baseline": float(value),
                    "total_delta": 0.0,
                    "tournament_delta": 0.0,
                    "assessment_delta": 0.0,
                    "last_updated": now_iso,
                    "assessment_count": 0,
                    "tournament_count": 0,
                }
                for skill_key, value in skills.items()
            }

            user = User(
                email=email,
                password_hash=get_password_hash(p["password"]),
                name=f"{p['first_name']} {p['last_name']}",
                first_name=p["first_name"],
                last_name=p["last_name"],
                nickname=p["nickname"],
                role="STUDENT",
                is_active=True,
                date_of_birth=datetime.strptime(p["date_of_birth"], "%Y-%m-%d").date(),
                phone=p["phone"],
                street_address=p["street_address"],
                city=p["city"],
                postal_code=p["postal_code"],
                country=p["country"],
                nationality=p.get("nationality"),
                gender=p.get("gender"),
                specialization="LFA_FOOTBALL_PLAYER",
                onboarding_completed=True,
                credit_balance=p.get("credits", 1000),
                xp_balance=p.get("xp", 0),
                created_at=datetime.now(timezone.utc),
            )
            db.add(user)
            db.flush()

            motivation_data = {
                "position": p["position"],
                "goals": p["goals"],
                "initial_self_assessment": skills,
                "average_skill_level": avg_skill,
                "onboarding_completed_at": datetime.now(timezone.utc).isoformat(),
            }

            license_ = UserLicense(
                user_id=user.id,
                specialization_type="LFA_FOOTBALL_PLAYER",
                current_level=1,
                max_achieved_level=1,
                is_active=True,
                onboarding_completed=True,
                onboarding_completed_at=datetime.now(timezone.utc),
                started_at=datetime.now(timezone.utc),
                payment_verified=True,
                payment_verified_at=datetime.now(timezone.utc),
                motivation_scores=motivation_data,
                football_skills=football_skills,
                average_motivation_score=avg_skill,
                motivation_last_assessed_at=datetime.now(timezone.utc),
                motivation_assessed_by=user.id,
            )
            db.add(license_)
            db.flush()
            flag_modified(license_, "football_skills")
            flag_modified(license_, "motivation_scores")
            db.commit()

            id_map[email] = user.id
            created += 1

            print(f"✅ {p['first_name']} {p['last_name']}")
            print(f"   📧 {email}  🔑 {p['password']}")
            print(f"   ⚽ {p['position']}  💰 {p.get('credits', 1000)} credits  ⭐ {p.get('xp', 0)} XP  📊 avg skill: {avg_skill}")

        print(f"\n🌟 ═══════════════════════════════════════════════════════")
        print(f"✅ Created: {created}  ⚠️  Skipped: {skipped}")
        print(f"🌟 ═══════════════════════════════════════════════════════")

        _write_db_ids(id_map)

    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    create_star_players()
