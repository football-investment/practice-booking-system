"""
Migrate onboarding skill baselines from motivation_scores to football_skills
"""
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.license import UserLicense

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Skill mapping from onboarding names to standard names
SKILL_MAPPING = {
    "heading": "heading",
    "shooting": "shooting",
    "passing": "passing",
    "dribbling": "ball_control",  # Map dribbling → ball_control
    "defending": "defending",
    "physical": "stamina"  # Map physical → stamina
}

def migrate_onboarding_to_football_skills():
    """Copy initial_self_assessment from motivation_scores to football_skills"""
    db = Session()

    try:
        # Get all active player licenses with motivation_scores
        licenses = db.query(UserLicense).filter(
            UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
            UserLicense.is_active == True,
            UserLicense.motivation_scores.isnot(None)
        ).all()

        print(f"🔍 Found {len(licenses)} active player licenses\n")

        migrated_count = 0

        for license in licenses:
            motivation = license.motivation_scores or {}
            initial_assessment = motivation.get("initial_self_assessment")

            if not initial_assessment:
                print(f"⏭️  License {license.id}: No initial_self_assessment, skipping")
                continue

            # Get user email for logging
            user_email = license.user.email if license.user else f"user_{license.user_id}"

            print(f"👤 Processing {user_email} (license {license.id})...")
            print(f"   Initial assessment: {initial_assessment}")

            # Convert onboarding skills to football_skills format
            # Multiply by 10 to convert 1-10 scale to 10-100 scale
            football_skills_baseline = {}

            for onboarding_name, value in initial_assessment.items():
                standard_name = SKILL_MAPPING.get(onboarding_name)

                if standard_name:
                    # Convert 1-10 scale to 10-100 scale
                    baseline_value = float(value * 10)
                    football_skills_baseline[standard_name] = baseline_value
                    print(f"   • {onboarding_name} ({value}/10) → {standard_name}: {baseline_value}")

            # Merge baseline into existing football_skills
            existing_skills = license.football_skills or {}

            # Ensure new format
            from app.services.skill_progression_service import SkillProgressionService
            skill_service = SkillProgressionService(db)
            existing_skills = skill_service._ensure_new_format(existing_skills)

            # Add baseline skills that don't exist yet
            added_count = 0
            for skill_name, baseline_value in football_skills_baseline.items():
                if skill_name not in existing_skills:
                    # Skill missing - add baseline
                    existing_skills[skill_name] = {
                        "current_level": baseline_value,
                        "baseline": baseline_value,
                        "total_delta": 0.0,
                        "tournament_delta": 0.0,
                        "assessment_delta": 0.0,
                        "last_updated": datetime.now().isoformat(),
                        "assessment_count": 0,
                        "tournament_count": 0
                    }
                    print(f"   + Added missing skill: {skill_name} = {baseline_value}")
                    added_count += 1

            if added_count > 0:
                license.football_skills = existing_skills
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(license, 'football_skills')
                print(f"   ✅ Added {added_count} missing baseline skills")
                migrated_count += 1
            else:
                print(f"   ⏭️  All baseline skills already present")

            print()

        db.commit()
        print(f"🎯 Migration complete! Migrated {migrated_count} licenses")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_onboarding_to_football_skills()
