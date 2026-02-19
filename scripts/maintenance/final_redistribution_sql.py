"""
Final re-distribution using direct SQL updates
"""
import os
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Semester, TournamentParticipation
from app.schemas.reward_config import TournamentRewardConfig

print("=" * 80)
print("FINAL REWARD RE-DISTRIBUTION (SQL)")
print("=" * 80)

db = next(get_db())

# Tournament IDs and expected configs
tournaments = [
    {
        "id": 18,
        "code": "TOURN-20260125-001",
        "name": "NIKE Speed Test",
        "expected_skills": ["speed", "agility"]
    },
    {
        "id": 19,
        "code": "TOURN-20260125-002",
        "name": "Plank Competition",
        "expected_skills": ["stamina"]
    }
]

for tourn_info in tournaments:
    print(f"\n🏆 {tourn_info['name']} ({tourn_info['code']})")
    print("-" * 80)

    # Get tournament
    tournament = db.query(Semester).filter(Semester.id == tourn_info['id']).first()
    if not tournament:
        print(f"❌ Tournament not found")
        continue

    # Parse reward_config
    try:
        config = TournamentRewardConfig(**tournament.reward_config)
        is_valid, error_msg = config.validate_enabled_skills()

        if not is_valid:
            print(f"❌ Invalid skill configuration: {error_msg}")
            continue

        print(f"✅ Valid reward_config:")
        for skill in config.enabled_skills:
            print(f"   - {skill.skill} (weight: {skill.weight}x, category: {skill.category})")

        # Verify expected skills
        enabled_skill_names = [s.skill for s in config.enabled_skills]
        if set(enabled_skill_names) != set(tourn_info['expected_skills']):
            print(f"⚠️  Warning: Expected skills {tourn_info['expected_skills']}, got {enabled_skill_names}")

    except Exception as e:
        print(f"❌ Failed to parse reward_config: {e}")
        continue

    # Get participations
    participations = db.query(TournamentParticipation).filter(
        TournamentParticipation.semester_id == tournament.id
    ).order_by(TournamentParticipation.placement).all()

    print(f"\n📊 Processing {len(participations)} participants:")

    total_credits = 0
    total_xp = 0
    skill_totals = {}

    for participation in participations:
        placement = participation.placement

        # Calculate rewards based on placement
        credits = 0
        xp_mult = 1.0

        if placement == 1:
            credits = config.first_place.credits
            xp_mult = config.first_place.xp_multiplier
            base_skill_points = 10.0
        elif placement == 2:
            credits = config.second_place.credits
            xp_mult = config.second_place.xp_multiplier
            base_skill_points = 7.0
        elif placement == 3:
            credits = config.third_place.credits
            xp_mult = config.third_place.xp_multiplier
            base_skill_points = 5.0
        else:
            credits = config.participation.credits
            xp_mult = config.participation.xp_multiplier
            base_skill_points = 1.0

        # Calculate XP
        base_xp = 100
        xp_awarded = int(base_xp * xp_mult)

        # Calculate skill points (weighted distribution)
        total_weight = sum(s.weight for s in config.enabled_skills)
        skill_points = {}
        for skill in config.enabled_skills:
            skill_proportion = skill.weight / total_weight
            points = base_skill_points * skill_proportion
            skill_points[skill.skill] = round(points, 1)

        # Update participation
        participation.credits_awarded = credits
        participation.xp_awarded = xp_awarded
        participation.skill_points_awarded = skill_points

        # Track totals
        total_credits += credits
        total_xp += xp_awarded
        for skill_name, points in skill_points.items():
            skill_totals[skill_name] = skill_totals.get(skill_name, 0) + points

        print(f"   Placement {placement or 'N/A':2s}: {credits:5d} credits | {xp_awarded:5d} XP | {skill_points}")

    # Commit
    db.commit()

    print(f"\n✅ Re-distribution complete!")
    print(f"   Total credits: {total_credits}")
    print(f"   Total XP: {total_xp}")
    print(f"\n   📊 Skill Points Breakdown:")
    for skill, points in sorted(skill_totals.items()):
        print(f"      {skill}: {points:.1f} points")

db.close()

print("\n" + "=" * 80)
print("✅ ALL TOURNAMENTS RE-DISTRIBUTED")
print("=" * 80)
