"""
Apply historical tournament skill deltas for Kylian Mbappé
"""
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.skill_progression_service import SkillProgressionService
from app.models.license import UserLicense

# Database connection
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def apply_kylian_tournament_deltas():
    """Apply tournament skill deltas for Kylian Mbappé (user_id=13)"""
    db = Session()

    try:
        # Get Kylian's active license
        license = db.query(UserLicense).filter(
            UserLicense.user_id == 13,
            UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
            UserLicense.is_active == True
        ).first()

        if not license:
            print("❌ No active license found for Kylian")
            return

        print(f"✅ Found license {license.id} for Kylian")
        print(f"📊 Current football_skills: {license.football_skills}")

        # Initialize skill service
        skill_service = SkillProgressionService(db)

        # Apply tournament participations manually
        tournament_participations = [
            {"id": 2, "skill_points": {"speed": 5.7, "agility": 4.3}},
            {"id": 15, "skill_points": {"stamina": 10.0}}
        ]

        for participation in tournament_participations:
            print(f"\n🏆 Applying tournament participation {participation['id']}...")

            # Manually apply deltas (simulating what should have happened)
            for skill_name, raw_points in participation["skill_points"].items():
                delta = skill_service._calculate_delta(raw_points, source="tournament")
                print(f"  • {skill_name}: {raw_points} raw → {delta} delta")

                license.football_skills = skill_service._apply_skill_delta(
                    license.football_skills or {},
                    skill_name,
                    delta,
                    source="tournament"
                )

        # Save changes
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(license, 'football_skills')
        db.commit()

        print(f"\n✅ Updated football_skills: {license.football_skills}")
        print("\n🎯 Skill deltas applied successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    apply_kylian_tournament_deltas()
