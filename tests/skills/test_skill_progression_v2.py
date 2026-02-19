"""
Test Skill Progression V2 - Placement-Based System

Test cases:
1. Player finishes 1st → Skills should INCREASE
2. Player finishes last → Skills should DECREASE
3. Multiple tournaments → Weighted average changes
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.user import User
from app.models.license import UserLicense
from app.models.tournament_achievement import TournamentParticipation
from app.services import skill_progression_service

db = SessionLocal()

# Test with existing tournament player (Kylian Mbappé)
user_email = "kylian.mbappe@f1rstteam.hu"
user = db.query(User).filter(User.email == user_email).first()

if not user:
    print(f"❌ User {user_email} not found")
    db.close()
    exit(1)

print(f"🔍 Testing Skill Progression V2 for: {user.name} ({user.email})")
print("=" * 80)

# Get active license
license = db.query(UserLicense).filter(
    UserLicense.user_id == user.id,
    UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
    UserLicense.is_active == True
).first()

# Get baseline skills from UserLicense.football_skills
print("\n📊 BASELINE SKILLS (from UserLicense.football_skills):")
baseline_skills = skill_progression_service.get_baseline_skills(db, user.id)
if baseline_skills:
    sample_skills = list(baseline_skills.items())[:5]  # Show first 5 skills
    for skill_name, baseline_value in sample_skills:
        print(f"  {skill_name}: {baseline_value}")
else:
    print("  ❌ No baseline skills found (onboarding not completed)")

# Get tournament participations
participations = (
    db.query(TournamentParticipation)
    .filter(TournamentParticipation.user_id == user.id)
    .order_by(TournamentParticipation.achieved_at.asc())
    .all()
)

print(f"\n🏆 TOURNAMENT HISTORY: {len(participations)} tournaments")
for i, part in enumerate(participations, 1):
    tournament = part.tournament
    if tournament:
        print(f"  {i}. {tournament.name}: Placement {part.placement or 'N/A'}")

# Calculate skill profile using NEW V2 system
print("\n⚡ CALCULATING SKILL PROFILE (V2 - Placement-Based)...")
profile = skill_progression_service.get_skill_profile(db, user.id)

skills = profile.get("skills", {})
average_level = profile.get("average_level", 0.0)
total_tournaments = profile.get("total_tournaments", 0)

print(f"\n📈 RESULTS:")
print(f"  Average Level: {average_level:.1f}/100")
print(f"  Total Tournaments: {total_tournaments}")

# Show skills with changes (both positive and negative)
skills_with_changes = {
    name: data for name, data in skills.items()
    if data.get("total_delta", 0.0) != 0
}

if skills_with_changes:
    print(f"\n🔄 SKILLS WITH CHANGES ({len(skills_with_changes)} skills):")

    # Sort by absolute delta (largest changes first)
    sorted_skills = sorted(
        skills_with_changes.items(),
        key=lambda x: abs(x[1].get("total_delta", 0.0)),
        reverse=True
    )

    for skill_name, skill_data in sorted_skills[:10]:  # Show top 10
        baseline = skill_data.get("baseline", 0.0)
        current = skill_data.get("current_level", 0.0)
        delta = skill_data.get("total_delta", 0.0)
        tournament_count = skill_data.get("tournament_count", 0)
        tier = skill_data.get("tier", "BEGINNER")
        tier_emoji = skill_data.get("tier_emoji", "")

        # Color-coded delta display
        if delta > 0:
            delta_display = f"+{delta:.1f} ✅"
            status = "IMPROVED"
        elif delta < 0:
            delta_display = f"{delta:.1f} ❌"
            status = "DECLINED"
        else:
            delta_display = f"{delta:.1f} ➖"
            status = "NO CHANGE"

        print(f"\n  {tier_emoji} {skill_name.replace('_', ' ').title()} ({tier})")
        print(f"    Baseline: {baseline:.1f}")
        print(f"    Current:  {current:.1f}")
        print(f"    Delta:    {delta_display} ({status})")
        print(f"    Tournaments: {tournament_count}")
else:
    print("\n  ℹ️  No skill changes yet (no tournament participation or no skills selected)")

# Show skills WITHOUT changes (baseline only)
skills_without_changes = {
    name: data for name, data in skills.items()
    if data.get("total_delta", 0.0) == 0
}

if skills_without_changes:
    print(f"\n📋 BASELINE SKILLS (no tournament data): {len(skills_without_changes)} skills")

print("\n" + "=" * 80)
print("✅ Test completed!")

# Test the core formula
print("\n🧪 FORMULA TEST:")
print("=" * 80)

test_cases = [
    {"baseline": 70, "placement": 1, "total": 10, "count": 1, "desc": "1st place (1st tournament)"},
    {"baseline": 70, "placement": 10, "total": 10, "count": 1, "desc": "Last place (1st tournament)"},
    {"baseline": 70, "placement": 1, "total": 10, "count": 3, "desc": "1st place (3rd tournament)"},
    {"baseline": 70, "placement": 10, "total": 10, "count": 3, "desc": "Last place (3rd tournament)"},
    {"baseline": 50, "placement": 5, "total": 10, "count": 2, "desc": "Middle place (2nd tournament)"},
]

for case in test_cases:
    result = skill_progression_service.calculate_skill_value_from_placement(
        baseline=case["baseline"],
        placement=case["placement"],
        total_players=case["total"],
        tournament_count=case["count"]
    )
    delta = result - case["baseline"]
    delta_sign = "+" if delta >= 0 else ""

    print(f"\n{case['desc']}:")
    print(f"  Baseline: {case['baseline']:.1f}")
    print(f"  Result:   {result:.1f} ({delta_sign}{delta:.1f})")

db.close()
print("\n✅ All tests completed!")
