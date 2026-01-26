"""
Backfill tournament skill deltas for ALL players
Applies historical tournament rewards to player skill profiles
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.skill_progression_service import SkillProgressionService
from app.models.license import UserLicense
from app.models.user import User

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def backfill_all_tournament_skills():
    """Apply tournament skill deltas for all players"""
    db = Session()

    try:
        # Get all players with tournament participations
        query = text("""
            SELECT DISTINCT ON (tp.user_id)
                tp.user_id,
                u.email,
                ul.id as license_id
            FROM tournament_participations tp
            JOIN users u ON tp.user_id = u.id
            JOIN user_licenses ul ON ul.user_id = u.id
            WHERE ul.specialization_type = 'LFA_FOOTBALL_PLAYER'
              AND ul.is_active = true
            ORDER BY tp.user_id
        """)

        players = db.execute(query).fetchall()

        print(f"🔍 Found {len(players)} players with tournament history\n")

        skill_service = SkillProgressionService(db)

        for player in players:
            user_id = player.user_id
            email = player.email
            license_id = player.license_id

            print(f"👤 Processing {email} (license {license_id})...")

            # Get license
            license = db.query(UserLicense).filter(UserLicense.id == license_id).first()

            if not license:
                print(f"  ❌ License not found, skipping")
                continue

            # Get all tournament participations for this user
            participations_query = text("""
                SELECT id, semester_id, skill_points_awarded, achieved_at
                FROM tournament_participations
                WHERE user_id = :user_id
                ORDER BY achieved_at ASC
            """)

            participations = db.execute(
                participations_query,
                {"user_id": user_id}
            ).fetchall()

            if not participations:
                print(f"  ℹ️  No tournament participations, skipping")
                continue

            print(f"  🏆 Found {len(participations)} tournament participation(s)")

            # Ensure football_skills exists (even if empty)
            if license.football_skills is None:
                license.football_skills = {}
                print(f"  📋 Initialized empty skill profile")

            # Apply each tournament's skill deltas
            for participation in participations:
                skill_points = participation.skill_points_awarded

                if not skill_points:
                    print(f"    • Tournament {participation.semester_id}: No skill points")
                    continue

                print(f"    • Tournament {participation.semester_id}: {skill_points}")

                # Apply deltas for each skill
                for skill_name, raw_points in skill_points.items():
                    delta = skill_service._calculate_delta(raw_points, source="tournament")

                    license.football_skills = skill_service._apply_skill_delta(
                        license.football_skills,
                        skill_name,
                        delta,
                        source="tournament"
                    )

                    print(f"      → {skill_name}: {raw_points} raw → +{delta} delta")

            # Save changes
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(license, 'football_skills')
            db.commit()

            print(f"  ✅ Applied tournament deltas successfully\n")

        print(f"🎯 Backfill complete for {len(players)} players!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    backfill_all_tournament_skills()
