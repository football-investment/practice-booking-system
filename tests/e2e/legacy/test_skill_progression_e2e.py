"""
Skill Progression V2 - Database-Level E2E Test

Test Setup:
- 8 test users with onboarding baseline skills
- 3 FREE tournaments with different skill selections
- Various placements (1st, middle, last)
- 3-4 different skills tested

Test Goals:
✅ Verify positive skill changes (winners)
✅ Verify negative skill changes (losers)
✅ Verify sequential tournament effects
✅ Track baseline → current → delta progression
✅ Confirm skills actually change in database during tournaments
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.user import User
from app.models.license import UserLicense
from app.models.semester import Semester
from app.models.tournament_achievement import TournamentParticipation
from app.services import skill_progression_service
from app.skills_config import SKILL_CATEGORIES
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
import json

# Pre-hashed password for test users (bcrypt hash of "test123")
DUMMY_PASSWORD_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7QNx5bPTnu"

# Build complete skill list from skills_config (29 skills)
ALL_SKILL_KEYS = []
for category in SKILL_CATEGORIES:
    for skill in category["skills"]:
        ALL_SKILL_KEYS.append(skill["key"])

db = SessionLocal()

print("=" * 100)
print("🧪 SKILL PROGRESSION V2 - DATABASE-LEVEL E2E TEST")
print("=" * 100)

# ============================================================================
# TEST DATA SETUP
# ============================================================================

TEST_USERS = [
    {"email": "e2e.player1@test.com", "name": "E2E Player 1", "baseline_sprint_speed": 60, "baseline_agility": 55, "baseline_stamina": 70, "baseline_ball_control": 65},
    {"email": "e2e.player2@test.com", "name": "E2E Player 2", "baseline_sprint_speed": 50, "baseline_agility": 60, "baseline_stamina": 55, "baseline_ball_control": 70},
    {"email": "e2e.player3@test.com", "name": "E2E Player 3", "baseline_sprint_speed": 70, "baseline_agility": 65, "baseline_stamina": 60, "baseline_ball_control": 55},
    {"email": "e2e.player4@test.com", "name": "E2E Player 4", "baseline_sprint_speed": 55, "baseline_agility": 70, "baseline_stamina": 65, "baseline_ball_control": 60},
    {"email": "e2e.player5@test.com", "name": "E2E Player 5", "baseline_sprint_speed": 65, "baseline_agility": 55, "baseline_stamina": 70, "baseline_ball_control": 50},
    {"email": "e2e.player6@test.com", "name": "E2E Player 6", "baseline_sprint_speed": 60, "baseline_agility": 65, "baseline_stamina": 50, "baseline_ball_control": 70},
    {"email": "e2e.player7@test.com", "name": "E2E Player 7", "baseline_sprint_speed": 70, "baseline_agility": 60, "baseline_stamina": 55, "baseline_ball_control": 65},
    {"email": "e2e.player8@test.com", "name": "E2E Player 8", "baseline_sprint_speed": 55, "baseline_agility": 50, "baseline_stamina": 60, "baseline_ball_control": 55},
]

TOURNAMENT_CONFIGS = [
    {
        "name": "E2E Test Tournament 1 - Sprint Speed & Agility",
        "skills": ["sprint_speed", "agility"],
        "placements": [1, 2, 3, 4, 5, 6, 7, 8],  # Perfect order
    },
    {
        "name": "E2E Test Tournament 2 - Stamina & Ball Control",
        "skills": ["stamina", "ball_control"],
        "placements": [8, 7, 6, 5, 4, 3, 2, 1],  # Reverse order
    },
    {
        "name": "E2E Test Tournament 3 - Mixed Skills",
        "skills": ["sprint_speed", "stamina", "ball_control"],
        "placements": [1, 8, 2, 7, 3, 6, 4, 5],  # Mixed order
    },
]

print("\n📋 TEST SETUP:")
print(f"  Users: {len(TEST_USERS)}")
print(f"  Tournaments: {len(TOURNAMENT_CONFIGS)}")
print(f"  Skills tested: sprint_speed, agility, stamina, ball_control (4 skills)")

# ============================================================================
# CLEANUP EXISTING TEST DATA
# ============================================================================

print("\n🧹 CLEANING UP EXISTING TEST DATA...")

for test_user in TEST_USERS:
    user = db.query(User).filter(User.email == test_user["email"]).first()
    if user:
        # Delete participations
        db.query(TournamentParticipation).filter(TournamentParticipation.user_id == user.id).delete()
        # Delete license
        db.query(UserLicense).filter(UserLicense.user_id == user.id).delete()
        # Delete user
        db.delete(user)

# Delete test tournaments
db.query(Semester).filter(Semester.name.like("E2E Test Tournament%")).delete()

db.commit()
print("  ✓ Cleaned up existing test data")

# ============================================================================
# CREATE TEST USERS WITH BASELINE SKILLS
# ============================================================================

print("\n👥 CREATING TEST USERS WITH BASELINE SKILLS...")

test_user_objects = []

for test_user_data in TEST_USERS:
    # Create user
    user = User(
        email=test_user_data["email"],
        name=test_user_data["name"],
        password_hash=DUMMY_PASSWORD_HASH,
        is_active=True
    )
    db.add(user)
    db.flush()

    # ✅ INITIALIZE ALL 29 SKILLS from skills_config to avoid DEFAULT_BASELINE fallback
    # This ensures baseline values match test expectations exactly
    baseline_skills = {}

    # Set test-specific skills (using REAL skill names from skills_config)
    test_skill_values = {
        "sprint_speed": test_user_data["baseline_sprint_speed"],
        "agility": test_user_data["baseline_agility"],
        "stamina": test_user_data["baseline_stamina"],
        "ball_control": test_user_data["baseline_ball_control"],
    }

    # Initialize ALL skills: use test values where specified, otherwise default to 50.0
    for skill_key in ALL_SKILL_KEYS:
        baseline_skills[skill_key] = test_skill_values.get(skill_key, 50.0)

    license = UserLicense(
        user_id=user.id,
        specialization_type="LFA_FOOTBALL_PLAYER",
        is_active=True,
        onboarding_completed=True,
        started_at=datetime.now(timezone.utc),
        football_skills=baseline_skills  # BASELINE STORED HERE (all 29 skills initialized)
    )
    db.add(license)
    db.flush()

    test_user_objects.append({
        "user": user,
        "license": license,
        "baseline": test_skill_values  # Store only test-specific values for validation
    })

    print(f"  ✓ Created: {user.name} (ID: {user.id})")
    print(f"    Baseline (test skills): Sprint Speed={test_skill_values['sprint_speed']}, Agility={test_skill_values['agility']}, "
          f"Stamina={test_skill_values['stamina']}, Ball Control={test_skill_values['ball_control']}")
    print(f"    Total skills initialized: {len(baseline_skills)} (all from skills_config)")

db.commit()

# ============================================================================
# CREATE FREE TOURNAMENTS WITH SKILL CONFIGURATIONS
# ============================================================================

print("\n🏆 CREATING FREE TOURNAMENTS...")

tournament_objects = []
start_date = datetime.now(timezone.utc) - timedelta(days=30)

for idx, tournament_config in enumerate(TOURNAMENT_CONFIGS):
    # Build reward_config with selected skills
    skill_mappings = []
    for skill in tournament_config["skills"]:
        skill_mappings.append({
            "skill": skill,
            "weight": 1.0,
            "category": "OUTFIELD" if skill in ["speed", "agility", "ball_control"] else "PHYSICAL",
            "enabled": True
        })

    reward_config = {
        "skill_mappings": skill_mappings,
        "first_place": {
            "badges": [],
            "credits": 0,
            "xp_multiplier": 1.0
        },
        "second_place": {
            "badges": [],
            "credits": 0,
            "xp_multiplier": 1.0
        },
        "third_place": {
            "badges": [],
            "credits": 0,
            "xp_multiplier": 1.0
        },
        "top_25_percent": {
            "badges": [],
            "credits": 0,
            "xp_multiplier": 1.0
        },
        "participation": {
            "badges": [],
            "credits": 0,
            "xp_multiplier": 1.0
        },
        "template_name": "Free",
        "custom_config": False
    }

    tournament = Semester(
        name=tournament_config["name"],
        code=f"E2E-TEST-{idx+1}",
        specialization_type="LFA_FOOTBALL_PLAYER",
        tournament_type="FREE",
        start_date=start_date + timedelta(days=idx*10),
        end_date=start_date + timedelta(days=idx*10 + 7),
        is_active=False,
        status="COMPLETED",
        tournament_status="COMPLETED",
        reward_config=reward_config
    )
    db.add(tournament)
    db.flush()

    tournament_objects.append({
        "tournament": tournament,
        "config": tournament_config
    })

    print(f"  ✓ Created: {tournament.name} (ID: {tournament.id})")
    print(f"    Skills: {', '.join(tournament_config['skills'])}")

db.commit()

# ============================================================================
# CREATE TOURNAMENT PARTICIPATIONS
# ============================================================================

print("\n📊 CREATING TOURNAMENT PARTICIPATIONS...")

for tournament_data in tournament_objects:
    tournament = tournament_data["tournament"]
    placements = tournament_data["config"]["placements"]

    print(f"\n  Tournament: {tournament.name}")

    for idx, user_data in enumerate(test_user_objects):
        user = user_data["user"]
        placement = placements[idx]

        participation = TournamentParticipation(
            user_id=user.id,
            semester_id=tournament.id,
            placement=placement,
            achieved_at=tournament.end_date
        )
        db.add(participation)

        print(f"    {user.name}: Placement {placement}")

db.commit()

# ============================================================================
# VERIFY SKILL CHANGES - DATABASE LEVEL
# ============================================================================

print("\n" + "=" * 100)
print("📈 VERIFYING SKILL PROGRESSION FROM DATABASE")
print("=" * 100)

for user_data in test_user_objects:
    user = user_data["user"]
    baseline = user_data["baseline"]

    print(f"\n{'=' * 100}")
    print(f"👤 {user.name} (ID: {user.id})")
    print(f"{'=' * 100}")

    # Get tournament history
    participations = (
        db.query(TournamentParticipation)
        .filter(TournamentParticipation.user_id == user.id)
        .order_by(TournamentParticipation.achieved_at.asc())
        .all()
    )

    print(f"\n🏆 TOURNAMENT HISTORY ({len(participations)} tournaments):")
    for i, part in enumerate(participations, 1):
        tournament = part.tournament
        skills = [m["skill"] for m in tournament.reward_config.get("skill_mappings", []) if m.get("enabled")]
        print(f"  {i}. {tournament.name}")
        print(f"     Placement: {part.placement}/8")
        print(f"     Skills: {', '.join(skills)}")

    # Calculate skill profile using V2 system
    profile = skill_progression_service.get_skill_profile(db, user.id)
    skills_data = profile.get("skills", {})

    print(f"\n📊 SKILL PROGRESSION RESULTS:")
    print(f"{'Skill':<20} {'Baseline':<12} {'Current':<12} {'Delta':<12} {'Status':<15} {'Tournaments'}")
    print("-" * 100)

    for skill_name in ["sprint_speed", "agility", "stamina", "ball_control"]:
        skill_info = skills_data.get(skill_name, {})
        baseline_value = skill_info.get("baseline", 0.0)
        current_value = skill_info.get("current_level", 0.0)
        delta = skill_info.get("total_delta", 0.0)
        tournament_count = skill_info.get("tournament_count", 0)

        # Status emoji
        if delta > 0:
            status = "✅ INCREASED"
            delta_display = f"+{delta:.1f}"
        elif delta < 0:
            status = "❌ DECREASED"
            delta_display = f"{delta:.1f}"
        else:
            status = "➖ UNCHANGED"
            delta_display = "0.0"

        print(f"{skill_name:<20} {baseline_value:<12.1f} {current_value:<12.1f} {delta_display:<12} {status:<15} {tournament_count}")

    print(f"\n💡 Average Level: {profile.get('average_level', 0.0):.1f}/100")

# ============================================================================
# SUMMARY STATISTICS
# ============================================================================

print("\n" + "=" * 100)
print("📊 E2E TEST SUMMARY")
print("=" * 100)

# Count positive/negative/unchanged skills
positive_changes = 0
negative_changes = 0
unchanged = 0

for user_data in test_user_objects:
    user = user_data["user"]
    profile = skill_progression_service.get_skill_profile(db, user.id)
    skills_data = profile.get("skills", {})

    for skill_name in ["sprint_speed", "agility", "stamina", "ball_control"]:
        delta = skills_data.get(skill_name, {}).get("total_delta", 0.0)
        if delta > 0:
            positive_changes += 1
        elif delta < 0:
            negative_changes += 1
        else:
            unchanged += 1

print(f"\n✅ Skills INCREASED (positive delta): {positive_changes}")
print(f"❌ Skills DECREASED (negative delta): {negative_changes}")
print(f"➖ Skills UNCHANGED (no tournaments): {unchanged}")

total_skills_tested = positive_changes + negative_changes + unchanged
print(f"\n📈 Total Skills Tested: {total_skills_tested}")
print(f"   Users: {len(test_user_objects)}")
print(f"   Tournaments: {len(tournament_objects)}")
print(f"   Skills per User: 4 (speed, agility, stamina, ball_control)")

# ============================================================================
# EXAMPLE: DETAILED SKILL EVOLUTION TRACKING
# ============================================================================

print("\n" + "=" * 100)
print("🔍 EXAMPLE: DETAILED SKILL EVOLUTION TRACKING")
print("=" * 100)

# Track first user's sprint_speed skill across all tournaments
example_user = test_user_objects[0]
user = example_user["user"]
baseline_sprint_speed = example_user["baseline"]["sprint_speed"]

print(f"\n👤 Tracking: {user.name} - Sprint Speed Skill")
print(f"📊 Baseline (Onboarding): {baseline_sprint_speed:.1f}")

participations = (
    db.query(TournamentParticipation)
    .filter(TournamentParticipation.user_id == user.id)
    .order_by(TournamentParticipation.achieved_at.asc())
    .all()
)

current_sprint_speed = baseline_sprint_speed
tournament_count_for_sprint_speed = 0

print(f"\n{'Tournament':<40} {'Placement':<12} {'Sprint Speed Tested?':<20} {'Old Value':<12} {'New Value':<12} {'Delta'}")
print("-" * 130)

for part in participations:
    tournament = part.tournament
    placement = part.placement
    total_players = 8

    # Check if sprint_speed was tested
    tournament_skills = [m["skill"] for m in tournament.reward_config.get("skill_mappings", []) if m.get("enabled")]
    sprint_speed_tested = "sprint_speed" in tournament_skills

    old_value = current_sprint_speed

    if sprint_speed_tested:
        tournament_count_for_sprint_speed += 1
        new_value = skill_progression_service.calculate_skill_value_from_placement(
            baseline=baseline_sprint_speed,
            placement=placement,
            total_players=total_players,
            tournament_count=tournament_count_for_sprint_speed
        )
        delta = new_value - old_value
        delta_display = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
        current_sprint_speed = new_value

        print(f"{tournament.name:<40} {f'{placement}/8':<12} {'✅ YES':<20} {old_value:<12.1f} {new_value:<12.1f} {delta_display}")
    else:
        print(f"{tournament.name:<40} {f'{placement}/8':<12} {'❌ NO':<20} {old_value:<12.1f} {'-':<12} {'-'}")

final_delta = current_sprint_speed - baseline_sprint_speed
final_delta_display = f"+{final_delta:.1f}" if final_delta >= 0 else f"{final_delta:.1f}"

print(f"\n📈 FINAL RESULT:")
print(f"   Baseline: {baseline_sprint_speed:.1f}")
print(f"   Current:  {current_sprint_speed:.1f}")
print(f"   Delta:    {final_delta_display}")
print(f"   Tournaments Affecting Sprint Speed: {tournament_count_for_sprint_speed}")

# ============================================================================
# VALIDATION CHECKS
# ============================================================================

print("\n" + "=" * 100)
print("✅ VALIDATION CHECKS")
print("=" * 100)

checks_passed = 0
checks_failed = 0

# Check 1: All users have profiles
print("\n1️⃣ Check: All 8 users have skill profiles")
for user_data in test_user_objects:
    user = user_data["user"]
    profile = skill_progression_service.get_skill_profile(db, user.id)
    if profile and profile.get("skills"):
        print(f"   ✅ {user.name}: Profile found")
        checks_passed += 1
    else:
        print(f"   ❌ {user.name}: Profile missing")
        checks_failed += 1

# Check 2: At least one skill increased
print("\n2️⃣ Check: At least one skill INCREASED (positive delta)")
if positive_changes > 0:
    print(f"   ✅ Found {positive_changes} skill increases")
    checks_passed += 1
else:
    print(f"   ❌ No skill increases found")
    checks_failed += 1

# Check 3: At least one skill decreased
print("\n3️⃣ Check: At least one skill DECREASED (negative delta)")
if negative_changes > 0:
    print(f"   ✅ Found {negative_changes} skill decreases")
    checks_passed += 1
else:
    print(f"   ❌ No skill decreases found")
    checks_failed += 1

# Check 4: Baselines match onboarding
print("\n4️⃣ Check: Baselines match onboarding data")
baselines_match = True
for user_data in test_user_objects:
    user = user_data["user"]
    expected_baseline = user_data["baseline"]
    profile = skill_progression_service.get_skill_profile(db, user.id)
    skills_data = profile.get("skills", {})

    for skill_name, expected_value in expected_baseline.items():
        actual_value = skills_data.get(skill_name, {}).get("baseline", 0.0)
        if abs(actual_value - expected_value) > 0.1:
            print(f"   ❌ {user.name} - {skill_name}: expected {expected_value}, got {actual_value}")
            baselines_match = False
            checks_failed += 1

if baselines_match:
    print(f"   ✅ All baselines match onboarding data")
    checks_passed += 1

# Check 5: Sequential tournaments work
print("\n5️⃣ Check: Sequential tournaments affect skills correctly")
sequential_works = True
for user_data in test_user_objects:
    user = user_data["user"]
    profile = skill_progression_service.get_skill_profile(db, user.id)
    skills_data = profile.get("skills", {})

    # Check that skills with tournament_count > 0 have non-zero deltas
    for skill_name in ["sprint_speed", "agility", "stamina", "ball_control"]:
        tournament_count = skills_data.get(skill_name, {}).get("tournament_count", 0)
        delta = skills_data.get(skill_name, {}).get("total_delta", 0.0)

        if tournament_count > 0 and delta == 0.0:
            print(f"   ❌ {user.name} - {skill_name}: {tournament_count} tournaments but delta = 0")
            sequential_works = False
            checks_failed += 1

if sequential_works:
    print(f"   ✅ Sequential tournaments work correctly")
    checks_passed += 1

# Final validation summary
print(f"\n{'=' * 100}")
print(f"🎯 VALIDATION SUMMARY:")
print(f"   ✅ Checks Passed: {checks_passed}")
print(f"   ❌ Checks Failed: {checks_failed}")

if checks_failed == 0:
    print(f"\n🎉 ALL CHECKS PASSED! Skill Progression V2 is working correctly at database level.")
else:
    print(f"\n⚠️  Some checks failed. Review test output above.")

# ============================================================================
# CLEANUP (OPTIONAL)
# ============================================================================

print("\n" + "=" * 100)
cleanup = input("\n🧹 Clean up test data? (y/n): ").strip().lower()

if cleanup == 'y':
    print("\n🧹 CLEANING UP TEST DATA...")

    for test_user in TEST_USERS:
        user = db.query(User).filter(User.email == test_user["email"]).first()
        if user:
            db.query(TournamentParticipation).filter(TournamentParticipation.user_id == user.id).delete()
            db.query(UserLicense).filter(UserLicense.user_id == user.id).delete()
            db.delete(user)

    db.query(Semester).filter(Semester.name.like("E2E Test Tournament%")).delete()

    db.commit()
    print("  ✓ Test data cleaned up")
else:
    print("\n  ℹ️  Test data kept for manual inspection")

db.close()
print("\n✅ E2E Test completed!")
print("=" * 100)
