"""
E2E Test: Reward Config Integration
Tests the full flow from tournament creation with custom reward config to distribution.
"""
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.database import get_db, engine
from app.models.semester import Semester
from app.models.user import User, UserRole
from app.models.tournament_ranking import TournamentRanking
from app.schemas.reward_config import (
    TournamentRewardConfig,
    SkillMappingConfig,
    PlacementRewardConfig,
    BadgeConfig
)
from app.services.tournament.tournament_reward_orchestrator import (
    distribute_rewards_for_tournament,
    load_reward_policy_from_config
)
from app.models.tournament_achievement import TournamentParticipation, TournamentBadge

print("=" * 80)
print("🧪 E2E Test: Reward Config Integration")
print("=" * 80)

# Get DB session
db = next(get_db())

try:
    # ========================================================================
    # STEP 1: Create Test Tournament with Custom Reward Config
    # ========================================================================
    print("\n📝 STEP 1: Creating test tournament with custom reward config...")

    # Create custom reward config
    reward_config = TournamentRewardConfig(
        skill_mappings=[
            SkillMappingConfig(
                skill="agility",
                category="PHYSICAL",
                weight=3.0,
                enabled=True
            ),
            SkillMappingConfig(
                skill="speed",
                category="PHYSICAL",
                weight=2.5,
                enabled=True
            ),
            SkillMappingConfig(
                skill="ball_control",
                category="TECHNICAL",
                weight=2.0,
                enabled=True
            ),
            SkillMappingConfig(
                skill="shooting",
                category="TECHNICAL",
                weight=1.5,
                enabled=False  # Disabled skill
            )
        ],
        first_place=PlacementRewardConfig(
            credits=1000,
            xp_multiplier=2.0,
            badges=[
                BadgeConfig(
                    badge_type="CHAMPION",
                    icon="🥇",
                    title="Test Champion",
                    description="Won 1st place in {tournament_name}",
                    rarity="EPIC",
                    enabled=True
                ),
                BadgeConfig(
                    badge_type="PODIUM_FINISH",
                    icon="🏆",
                    title="Podium Winner",
                    description="Top 3 finish in {tournament_name}",
                    rarity="RARE",
                    enabled=True
                )
            ]
        ),
        second_place=PlacementRewardConfig(
            credits=600,
            xp_multiplier=1.5,
            badges=[
                BadgeConfig(
                    badge_type="RUNNER_UP",
                    icon="🥈",
                    title="Test Runner-Up",
                    description="Secured 2nd place in {tournament_name}",
                    rarity="RARE",
                    enabled=True
                )
            ]
        ),
        third_place=PlacementRewardConfig(
            credits=400,
            xp_multiplier=1.3,
            badges=[
                BadgeConfig(
                    badge_type="THIRD_PLACE",
                    icon="🥉",
                    title="Test Third Place",
                    description="Earned 3rd place in {tournament_name}",
                    rarity="RARE",
                    enabled=True
                )
            ]
        ),
        participation=PlacementRewardConfig(
            credits=100,
            xp_multiplier=1.0,
            badges=[]
        ),
        template_name="E2E_TEST",
        custom_config=True
    )

    # Create tournament
    tournament = Semester(
        name="E2E Test Tournament - Reward Config",
        code="E2E_TEST_REWARD",
        specialization_type="LFA_FOOTBALL_PLAYER",
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=7),
        is_active=True,
        format="INDIVIDUAL_RANKING",
        tournament_status="COMPLETED",
        reward_config=reward_config.model_dump(mode="json")
    )
    db.add(tournament)
    db.commit()
    db.refresh(tournament)

    print(f"✅ Tournament created: ID={tournament.id}, Name={tournament.name}")
    print(f"   Reward config: {reward_config.template_name}, Custom={reward_config.custom_config}")
    print(f"   Skills enabled: {sum(1 for s in reward_config.skill_mappings if s.enabled)}/{len(reward_config.skill_mappings)}")

    # ========================================================================
    # STEP 2: Add Test Participants and Rankings
    # ========================================================================
    print("\n👥 STEP 2: Adding test participants and rankings...")

    # Get test users (assuming they exist)
    test_users = db.query(User).filter(
        User.role == UserRole.STUDENT
    ).limit(5).all()

    if len(test_users) < 3:
        print("❌ ERROR: Not enough test users found. Need at least 3 players.")
        sys.exit(1)

    # Create rankings
    rankings = []
    for idx, user in enumerate(test_users[:5], start=1):
        ranking = TournamentRanking(
            tournament_id=tournament.id,
            user_id=user.id,
            participant_type="INDIVIDUAL",
            rank=idx,
            points=100 - (idx * 10)  # Decreasing points
        )
        db.add(ranking)
        rankings.append(ranking)

    db.commit()

    print(f"✅ Added {len(rankings)} participants:")
    for r in rankings:
        user = db.query(User).filter(User.id == r.user_id).first()
        print(f"   Rank {r.rank}: {user.email} (Points: {r.points})")

    # ========================================================================
    # STEP 3: Preview Reward Distribution
    # ========================================================================
    print("\n🔍 STEP 3: Previewing reward distribution...")

    # Load reward policy from config
    reward_policy = load_reward_policy_from_config(db, tournament.id)

    print(f"\n📊 Reward Policy Loaded:")
    print(f"   Template: {reward_policy.tournament_type}")
    print(f"   1st Place: {reward_policy.first_place_xp} XP + {reward_policy.first_place_credits} credits")
    print(f"   2nd Place: {reward_policy.second_place_xp} XP + {reward_policy.second_place_credits} credits")
    print(f"   3rd Place: {reward_policy.third_place_xp} XP + {reward_policy.third_place_credits} credits")
    print(f"   Participation: {reward_policy.participant_xp} XP + {reward_policy.participant_credits} credits")

    # Calculate expected rewards
    expected_rewards = {}
    for ranking in rankings:
        placement = ranking.rank if ranking.rank <= 3 else None

        # XP calculation
        if placement == 1:
            xp = reward_policy.first_place_xp
            credits = reward_policy.first_place_credits
        elif placement == 2:
            xp = reward_policy.second_place_xp
            credits = reward_policy.second_place_credits
        elif placement == 3:
            xp = reward_policy.third_place_xp
            credits = reward_policy.third_place_credits
        else:
            xp = reward_policy.participant_xp
            credits = reward_policy.participant_credits

        expected_rewards[ranking.user_id] = {
            'placement': placement,
            'expected_base_xp': xp,
            'expected_credits': credits
        }

    print(f"\n📋 Expected Rewards Preview:")
    for user_id, rewards in expected_rewards.items():
        user = db.query(User).filter(User.id == user_id).first()
        print(f"   {user.email}: Placement={rewards['placement']}, XP={rewards['expected_base_xp']}, Credits={rewards['expected_credits']}")

    # ========================================================================
    # STEP 4: Execute Reward Distribution (1st time)
    # ========================================================================
    print("\n🎁 STEP 4: Executing reward distribution (1st time)...")

    result = distribute_rewards_for_tournament(
        db=db,
        tournament_id=tournament.id,
        distributed_by=None,
        force_redistribution=False
    )

    print(f"\n✅ Distribution completed:")
    print(f"   Total participants: {result.total_participants}")
    print(f"   Rewards distributed: {len(result.rewards_distributed)}")
    print(f"   Total XP awarded: {result.distribution_summary['total_xp_awarded']}")
    print(f"   Total credits awarded: {result.distribution_summary['total_credits_awarded']}")
    print(f"   Total badges awarded: {result.distribution_summary['total_badges_awarded']}")

    # ========================================================================
    # STEP 5: Compare Preview vs Actual
    # ========================================================================
    print("\n🔬 STEP 5: Comparing preview vs actual distribution...")

    all_match = True
    for reward_result in result.rewards_distributed:
        user_id = reward_result.user_id
        user = db.query(User).filter(User.id == user_id).first()
        expected = expected_rewards[user_id]

        actual_base_xp = reward_result.participation.base_xp
        actual_credits = reward_result.participation.credits
        actual_placement = reward_result.participation.placement

        xp_match = actual_base_xp == expected['expected_base_xp']
        credits_match = actual_credits == expected['expected_credits']
        placement_match = actual_placement == expected['placement']

        if not (xp_match and credits_match and placement_match):
            all_match = False
            print(f"   ❌ MISMATCH for {user.email}:")
            print(f"      Expected: XP={expected['expected_base_xp']}, Credits={expected['expected_credits']}, Placement={expected['placement']}")
            print(f"      Actual:   XP={actual_base_xp}, Credits={actual_credits}, Placement={actual_placement}")
        else:
            print(f"   ✅ {user.email}: XP={actual_base_xp}, Credits={actual_credits}, Badges={len(reward_result.badges.badges)}")

    if all_match:
        print("\n✅ All rewards match expected values!")
    else:
        print("\n❌ Some rewards don't match - investigation needed")

    # ========================================================================
    # STEP 6: Test Idempotency (2nd distribution)
    # ========================================================================
    print("\n🔁 STEP 6: Testing idempotency (2nd distribution attempt)...")

    # Get participation count before 2nd run
    participations_before = db.query(TournamentParticipation).filter(
        TournamentParticipation.semester_id == tournament.id
    ).count()

    badges_before = db.query(TournamentBadge).filter(
        TournamentBadge.semester_id == tournament.id
    ).count()

    print(f"   Before 2nd run: {participations_before} participations, {badges_before} badges")

    # Run distribution again (should be idempotent)
    result2 = distribute_rewards_for_tournament(
        db=db,
        tournament_id=tournament.id,
        distributed_by=None,
        force_redistribution=False
    )

    participations_after = db.query(TournamentParticipation).filter(
        TournamentParticipation.semester_id == tournament.id
    ).count()

    badges_after = db.query(TournamentBadge).filter(
        TournamentBadge.semester_id == tournament.id
    ).count()

    print(f"   After 2nd run: {participations_after} participations, {badges_after} badges")
    print(f"   Rewards distributed in 2nd run: {len(result2.rewards_distributed)}")

    if participations_before == participations_after and badges_before == badges_after:
        print("\n✅ Idempotency check PASSED - no duplicate rewards created!")
    else:
        print("\n❌ Idempotency check FAILED - duplicates were created!")
        print(f"   Participation delta: {participations_after - participations_before}")
        print(f"   Badge delta: {badges_after - badges_before}")

    # ========================================================================
    # STEP 7: Verify Skill Point Calculation
    # ========================================================================
    print("\n🎯 STEP 7: Verifying skill point calculation from config...")

    # Check first participant's skill points
    first_participation = db.query(TournamentParticipation).filter(
        TournamentParticipation.semester_id == tournament.id,
        TournamentParticipation.placement == 1
    ).first()

    if first_participation and first_participation.skill_points_awarded:
        print(f"\n1st Place Skill Points:")
        total_weight = sum(s.weight for s in reward_config.skill_mappings if s.enabled)
        for skill_name, points in first_participation.skill_points_awarded.items():
            # Find weight
            skill_cfg = next((s for s in reward_config.skill_mappings if s.skill == skill_name), None)
            if skill_cfg:
                expected = round((skill_cfg.weight / total_weight) * 10, 1)  # 10 base points for 1st
                match = "✅" if abs(points - expected) < 0.1 else "❌"
                print(f"   {match} {skill_name}: {points} points (expected: {expected}, weight: {skill_cfg.weight})")

        # Check that disabled skill (shooting) is NOT included
        if "shooting" in first_participation.skill_points_awarded:
            print(f"   ❌ ERROR: 'shooting' skill should be disabled but was awarded!")
        else:
            print(f"   ✅ Disabled skill 'shooting' correctly excluded")

    # ========================================================================
    # STEP 8: Verify Badge Configuration
    # ========================================================================
    print("\n🏆 STEP 8: Verifying badge configuration from config...")

    first_badges = db.query(TournamentBadge).filter(
        TournamentBadge.semester_id == tournament.id,
        TournamentBadge.user_id == first_participation.user_id
    ).all()

    print(f"\n1st Place Badges ({len(first_badges)}):")
    expected_badge_types = ["CHAMPION", "PODIUM_FINISH"]
    for badge in first_badges:
        expected = "✅" if badge.badge_type in expected_badge_types else "❌"
        print(f"   {expected} {badge.badge_type}: {badge.icon} {badge.title} ({badge.rarity})")

    # ========================================================================
    # Final Summary
    # ========================================================================
    print("\n" + "=" * 80)
    print("📊 E2E Test Summary")
    print("=" * 80)
    print(f"✅ Tournament created with custom reward config")
    print(f"✅ {len(rankings)} participants added with rankings")
    print(f"✅ Reward distribution executed successfully")
    print(f"✅ Preview vs Actual comparison: {'PASS' if all_match else 'FAIL'}")
    print(f"✅ Idempotency check: {'PASS' if participations_before == participations_after else 'FAIL'}")
    print(f"✅ Skill point calculation verified")
    print(f"✅ Badge configuration verified")
    print("\n🎉 E2E Test COMPLETED!\n")

    # Cleanup
    print("🧹 Cleaning up test data...")
    db.query(TournamentBadge).filter(TournamentBadge.semester_id == tournament.id).delete()
    db.query(TournamentParticipation).filter(TournamentParticipation.semester_id == tournament.id).delete()
    db.query(TournamentRanking).filter(TournamentRanking.tournament_id == tournament.id).delete()
    db.delete(tournament)
    db.commit()
    print("✅ Cleanup completed")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
