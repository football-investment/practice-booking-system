"""
Final re-distribution for TOURN-20260125-001 and TOURN-20260125-002
using the updated reward configs with valid skills.
"""
import os
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Semester, TournamentParticipation, User
from app.services.tournament.tournament_participation_service import (
    calculate_credits_for_placement,
    calculate_xp_for_placement,
    calculate_skill_points_for_placement
)
from app.schemas.reward_config import TournamentRewardConfig

print("=" * 80)
print("FINAL REWARD RE-DISTRIBUTION")
print("=" * 80)

db = next(get_db())

# Tournament codes
tournament_codes = ['TOURN-20260125-001', 'TOURN-20260125-002']

for code in tournament_codes:
    print(f"\n🏆 Processing {code}")
    print("-" * 80)

    # Get tournament
    tournament = db.query(Semester).filter(Semester.code == code).first()
    if not tournament:
        print(f"❌ Tournament {code} not found")
        continue

    # Verify reward_config
    if not tournament.reward_config:
        print(f"❌ No reward_config found for {code}")
        continue

    try:
        config = TournamentRewardConfig(**tournament.reward_config)
        is_valid, error_msg = config.validate_enabled_skills()

        if not is_valid:
            print(f"❌ Invalid skill configuration: {error_msg}")
            continue

        print(f"✅ Valid reward_config with {len(config.enabled_skills)} enabled skills:")
        for skill in config.enabled_skills:
            print(f"   - {skill.skill} (weight: {skill.weight}x)")

    except Exception as e:
        print(f"❌ Failed to parse reward_config: {e}")
        continue

    # Get all participations
    participations = db.query(TournamentParticipation).filter(
        TournamentParticipation.semester_id == tournament.id
    ).all()

    print(f"\n📊 Found {len(participations)} participants")

    # Delete old participations and recalculate
    total_credits = 0
    total_xp = 0
    skill_totals = {}

    for participation in participations:
        user = db.query(User).filter(User.id == participation.user_id).first()
        if not user:
            continue

        placement = participation.placement

        # Calculate new rewards using V2 services
        credits = calculate_credits_for_placement(db, tournament.id, placement)
        xp_mult = calculate_xp_for_placement(db, tournament.id, placement)
        skill_points = calculate_skill_points_for_placement(db, tournament.id, placement)

        # Calculate XP (assuming base XP = 100)
        base_xp = 100
        xp_awarded = int(base_xp * xp_mult)

        # Update participation
        participation.credits_awarded = credits
        participation.xp_awarded = xp_awarded
        participation.skill_points_awarded = skill_points

        # Track totals
        total_credits += credits
        total_xp += xp_awarded

        for skill_name, points in skill_points.items():
            skill_totals[skill_name] = skill_totals.get(skill_name, 0) + points

        print(f"   {user.email[:20]:20s} | Placement: {placement or 'N/A':3s} | Credits: {credits:5d} | XP: {xp_awarded:5d} | Skills: {skill_points}")

    # Commit changes
    db.commit()

    print(f"\n✅ Re-distribution complete!")
    print(f"   Total credits awarded: {total_credits}")
    print(f"   Total XP awarded: {total_xp}")
    print(f"\n   📊 Skill Points Breakdown:")
    for skill, points in skill_totals.items():
        print(f"      {skill}: {points:.1f} points")

db.close()

print("\n" + "=" * 80)
print("✅ ALL TOURNAMENTS RE-DISTRIBUTED")
print("=" * 80)
