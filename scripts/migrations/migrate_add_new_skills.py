"""
Add 30 new skills to existing players with baseline=50.0
Existing 6 skills (heading, shooting, passing, ball_control, defending, stamina) remain unchanged.
"""
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.license import UserLicense
from app.skills_config import get_all_skill_keys, DEFAULT_SKILL_BASELINE
from app.services.skill_progression_service import SkillProgressionService

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


def add_new_skills_to_existing_players():
    """
    Add 30 new skills to existing players with baseline=50.0
    Preserve existing 6 skills (heading, shooting, passing, ball_control, defending, stamina)
    """
    db = Session()

    try:
        # Get all active player licenses with football_skills
        licenses = db.query(UserLicense).filter(
            UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
            UserLicense.is_active == True,
            UserLicense.football_skills.isnot(None)
        ).all()

        print(f"🔍 Found {len(licenses)} active player licenses with existing skill data\n")

        # Get all expected skill keys (36 total)
        all_skill_keys = set(get_all_skill_keys())
        print(f"📋 Expected skills: {len(all_skill_keys)} total")
        print(f"   Skills: {sorted(all_skill_keys)}\n")

        migrated_count = 0
        skill_service = SkillProgressionService(db)

        for license in licenses:
            # Get user email for logging
            user_email = license.user.email if license.user else f"user_{license.user_id}"

            print(f"👤 Processing {user_email} (license {license.id})...")

            # Ensure new format
            existing_skills = skill_service._ensure_new_format(license.football_skills or {})

            # Find missing skills
            existing_skill_keys = set(existing_skills.keys())
            missing_skills = all_skill_keys - existing_skill_keys

            if not missing_skills:
                print(f"   ✅ All {len(all_skill_keys)} skills already present")
                print()
                continue

            print(f"   📊 Current: {len(existing_skill_keys)} skills")
            print(f"   ➕ Adding: {len(missing_skills)} missing skills")

            # Add missing skills with baseline=50.0
            for skill_key in sorted(missing_skills):
                existing_skills[skill_key] = {
                    "current_level": DEFAULT_SKILL_BASELINE,
                    "baseline": DEFAULT_SKILL_BASELINE,
                    "total_delta": 0.0,
                    "tournament_delta": 0.0,
                    "assessment_delta": 0.0,
                    "last_updated": datetime.now().isoformat(),
                    "assessment_count": 0,
                    "tournament_count": 0
                }
                print(f"      + {skill_key}: {DEFAULT_SKILL_BASELINE}")

            # Save updated skills
            license.football_skills = existing_skills
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(license, 'football_skills')

            migrated_count += 1
            print(f"   ✅ Added {len(missing_skills)} skills → Total: {len(existing_skills)} skills")
            print()

        db.commit()
        print(f"🎯 Migration complete! Updated {migrated_count} licenses")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 70)
    print("MIGRATION: Add 30 new skills to existing players")
    print("=" * 70)
    print()
    print("This script will:")
    print("  1. Find all active LFA Football Player licenses")
    print("  2. Check which skills are missing (out of 36 total)")
    print("  3. Add missing skills with baseline=50.0")
    print("  4. Preserve existing skill data (baseline, deltas, counts)")
    print()
    print("=" * 70)
    print()

    add_new_skills_to_existing_players()
