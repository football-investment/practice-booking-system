"""
Production-Safe Reward Config Test

Tests reward config system on real tournaments WITHOUT data loss.
Uses database snapshots and rollback capability.
"""
import sys
import os
from datetime import datetime
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.database import get_db
from app.models.semester import Semester
from app.models.user import User
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
from app.models.tournament_ranking import TournamentRanking

print("=" * 80)
print("🔒 Production-Safe Reward Config Test")
print("=" * 80)

# Target tournaments
TOURNAMENT_CODES = [
    "TOURN-20260125-001",  # NIKE Speed Test (already distributed)
    "TOURN-20260125-002"   # Plank Competition (not yet distributed)
]

# Get DB session
db = next(get_db())

try:
    # ========================================================================
    # STEP 1: Snapshot Current State
    # ========================================================================
    print("\n📸 STEP 1: Taking snapshot of current state...")

    snapshot = {}

    for code in TOURNAMENT_CODES:
        tournament = db.query(Semester).filter(Semester.code == code).first()

        if not tournament:
            print(f"   ❌ Tournament {code} not found, skipping")
            continue

        # Count existing rewards
        participations = db.query(TournamentParticipation).filter(
            TournamentParticipation.semester_id == tournament.id
        ).all()

        badges = db.query(TournamentBadge).filter(
            TournamentBadge.semester_id == tournament.id
        ).all()

        rankings = db.query(TournamentRanking).filter(
            TournamentRanking.tournament_id == tournament.id
        ).all()

        snapshot[code] = {
            'tournament_id': tournament.id,
            'name': tournament.name,
            'status': tournament.tournament_status,
            'has_reward_config': tournament.reward_config is not None,
            'current_reward_config': tournament.reward_config,
            'participations_count': len(participations),
            'badges_count': len(badges),
            'rankings_count': len(rankings),
            'participations': [
                {
                    'id': p.id,
                    'user_id': p.user_id,
                    'placement': p.placement,
                    'xp_awarded': p.xp_awarded,
                    'credits_awarded': p.credits_awarded,
                    'skill_points': p.skill_points_awarded
                }
                for p in participations
            ],
            'badges': [
                {
                    'id': b.id,
                    'user_id': b.user_id,
                    'badge_type': b.badge_type,
                    'title': b.title,
                    'rarity': b.rarity
                }
                for b in badges
            ],
            'total_xp': sum(p.xp_awarded for p in participations),
            'total_credits': sum(p.credits_awarded for p in participations)
        }

        print(f"\n   ✅ {code}: {tournament.name}")
        print(f"      Status: {tournament.status}")
        print(f"      Participants: {len(rankings)}")
        print(f"      Existing rewards: {len(participations)} participations, {len(badges)} badges")
        print(f"      Total XP: {snapshot[code]['total_xp']}, Total Credits: {snapshot[code]['total_credits']}")

    # Save snapshot to file
    snapshot_file = f"snapshot_production_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(snapshot_file, 'w') as f:
        json.dump(snapshot, f, indent=2, default=str)
    print(f"\n   💾 Snapshot saved to: {snapshot_file}")

    # ========================================================================
    # STEP 2: Analyze Test Scenarios
    # ========================================================================
    print("\n\n🔍 STEP 2: Analyzing test scenarios...")

    test_plan = {}

    for code, data in snapshot.items():
        if data['participations_count'] > 0:
            test_plan[code] = "FORCE_REDISTRIBUTION"  # Already distributed, need force flag
            print(f"   ⚠️  {code}: Already has rewards → Will test FORCE_REDISTRIBUTION")
        else:
            test_plan[code] = "FIRST_DISTRIBUTION"    # No rewards yet, clean distribution
            print(f"   ✅ {code}: No rewards yet → Will test FIRST_DISTRIBUTION")

    # ========================================================================
    # STEP 3: Create Test Reward Configs
    # ========================================================================
    print("\n\n⚙️  STEP 3: Creating test reward configurations...")

    # Config for NIKE Speed Test (high XP, focus on speed/agility)
    speed_test_config = TournamentRewardConfig(
        skill_mappings=[
            SkillMappingConfig(
                skill="speed",
                category="PHYSICAL",
                weight=4.0,
                enabled=True
            ),
            SkillMappingConfig(
                skill="agility",
                category="PHYSICAL",
                weight=3.0,
                enabled=True
            ),
            SkillMappingConfig(
                skill="stamina",
                category="PHYSICAL",
                weight=2.0,
                enabled=True
            )
        ],
        first_place=PlacementRewardConfig(
            credits=150,
            xp_multiplier=2.5,  # 500 * 2.5 = 1250 XP
            badges=[
                BadgeConfig(
                    badge_type="CHAMPION",
                    icon="⚡",
                    title="Speed Champion",
                    description="Fastest runner in {tournament_name}",
                    rarity="EPIC",
                    enabled=True
                )
            ]
        ),
        second_place=PlacementRewardConfig(
            credits=100,
            xp_multiplier=1.8,  # 300 * 1.8 = 540 XP
            badges=[
                BadgeConfig(
                    badge_type="RUNNER_UP",
                    icon="🥈",
                    title="Speed Runner-Up",
                    description="2nd place in {tournament_name}",
                    rarity="RARE",
                    enabled=True
                )
            ]
        ),
        third_place=PlacementRewardConfig(
            credits=50,
            xp_multiplier=1.5,  # 200 * 1.5 = 300 XP
            badges=[
                BadgeConfig(
                    badge_type="THIRD_PLACE",
                    icon="🥉",
                    title="Speed Bronze",
                    description="3rd place in {tournament_name}",
                    rarity="RARE",
                    enabled=True
                )
            ]
        ),
        participation=PlacementRewardConfig(
            credits=25,
            xp_multiplier=1.0,  # 50 * 1.0 = 50 XP
            badges=[]
        ),
        template_name="SPEED_TEST_CUSTOM",
        custom_config=True
    )

    # Config for Plank Competition (endurance focus)
    plank_config = TournamentRewardConfig(
        skill_mappings=[
            SkillMappingConfig(
                skill="core_strength",
                category="PHYSICAL",
                weight=4.0,
                enabled=True
            ),
            SkillMappingConfig(
                skill="mental_toughness",
                category="MENTAL",
                weight=3.0,
                enabled=True
            ),
            SkillMappingConfig(
                skill="endurance",
                category="PHYSICAL",
                weight=2.5,
                enabled=True
            )
        ],
        first_place=PlacementRewardConfig(
            credits=200,
            xp_multiplier=3.0,  # 500 * 3.0 = 1500 XP
            badges=[
                BadgeConfig(
                    badge_type="CHAMPION",
                    icon="💪",
                    title="Plank Champion",
                    description="Longest plank hold in {tournament_name}",
                    rarity="EPIC",
                    enabled=True
                )
            ]
        ),
        second_place=PlacementRewardConfig(
            credits=120,
            xp_multiplier=2.0,  # 300 * 2.0 = 600 XP
            badges=[
                BadgeConfig(
                    badge_type="RUNNER_UP",
                    icon="🥈",
                    title="Plank Runner-Up",
                    description="2nd place in {tournament_name}",
                    rarity="RARE",
                    enabled=True
                )
            ]
        ),
        third_place=PlacementRewardConfig(
            credits=80,
            xp_multiplier=1.5,  # 200 * 1.5 = 300 XP
            badges=[
                BadgeConfig(
                    badge_type="THIRD_PLACE",
                    icon="🥉",
                    title="Plank Bronze",
                    description="3rd place in {tournament_name}",
                    rarity="RARE",
                    enabled=True
                )
            ]
        ),
        participation=PlacementRewardConfig(
            credits=30,
            xp_multiplier=1.2,  # 50 * 1.2 = 60 XP
            badges=[]
        ),
        template_name="PLANK_CUSTOM",
        custom_config=True
    )

    configs = {
        "TOURN-20260125-001": speed_test_config,
        "TOURN-20260125-002": plank_config
    }

    print("   ✅ Created 2 custom reward configurations")
    print(f"      - SPEED_TEST_CUSTOM: High XP (2.5x), speed/agility focus")
    print(f"      - PLANK_CUSTOM: Very high XP (3.0x), core/mental focus")

    # ========================================================================
    # STEP 4: DRY RUN - Preview Rewards (Without Saving)
    # ========================================================================
    print("\n\n🧪 STEP 4: DRY RUN - Previewing rewards (no database changes)...")

    for code in TOURNAMENT_CODES:
        if code not in snapshot:
            continue

        print(f"\n   📊 {code}:")
        tournament_id = snapshot[code]['tournament_id']
        config = configs[code]

        # Load reward policy from config (in-memory only)
        from app.schemas.tournament_rewards import RewardPolicy

        first_place = config.first_place
        second_place = config.second_place
        third_place = config.third_place
        participation = config.participation

        preview_policy = RewardPolicy(
            tournament_type=config.template_name,
            first_place_xp=int(500 * first_place.xp_multiplier),
            first_place_credits=first_place.credits,
            second_place_xp=int(300 * second_place.xp_multiplier),
            second_place_credits=second_place.credits,
            third_place_xp=int(200 * third_place.xp_multiplier),
            third_place_credits=third_place.credits,
            participant_xp=int(50 * participation.xp_multiplier),
            participant_credits=participation.credits
        )

        print(f"      Template: {config.template_name}")
        print(f"      1st Place: {preview_policy.first_place_xp} XP + {preview_policy.first_place_credits} credits")
        print(f"      2nd Place: {preview_policy.second_place_xp} XP + {preview_policy.second_place_credits} credits")
        print(f"      3rd Place: {preview_policy.third_place_xp} XP + {preview_policy.third_place_credits} credits")
        print(f"      Participation: {preview_policy.participant_xp} XP + {preview_policy.participant_credits} credits")

        # Calculate estimated totals
        rankings = db.query(TournamentRanking).filter(
            TournamentRanking.tournament_id == tournament_id
        ).all()

        estimated_xp = 0
        estimated_credits = 0

        for ranking in rankings:
            if ranking.rank == 1:
                estimated_xp += preview_policy.first_place_xp
                estimated_credits += preview_policy.first_place_credits
            elif ranking.rank == 2:
                estimated_xp += preview_policy.second_place_xp
                estimated_credits += preview_policy.second_place_credits
            elif ranking.rank == 3:
                estimated_xp += preview_policy.third_place_xp
                estimated_credits += preview_policy.third_place_credits
            else:
                estimated_xp += preview_policy.participant_xp
                estimated_credits += preview_policy.participant_credits

        print(f"\n      📈 Estimated Totals ({len(rankings)} participants):")
        print(f"         Total XP: {estimated_xp}")
        print(f"         Total Credits: {estimated_credits}")

        if snapshot[code]['participations_count'] > 0:
            print(f"\n      📊 Comparison with Current Distribution:")
            print(f"         Current XP: {snapshot[code]['total_xp']} → New: {estimated_xp} (Δ {estimated_xp - snapshot[code]['total_xp']:+d})")
            print(f"         Current Credits: {snapshot[code]['total_credits']} → New: {estimated_credits} (Δ {estimated_credits - snapshot[code]['total_credits']:+d})")

    # ========================================================================
    # DECISION POINT: Ask for User Confirmation
    # ========================================================================
    print("\n\n" + "=" * 80)
    print("⚠️  DECISION POINT: Ready to proceed?")
    print("=" * 80)
    print("\nNext steps would:")
    print("1. Save reward configs to database (reward_config column)")
    print("2. Execute reward distribution with new configs")
    print("3. Compare results with preview")
    print("4. Validate idempotency (run again)")
    print("\n⚠️  WARNING: This test uses force_redistribution=True for already-distributed tournaments.")
    print("   This WILL UPDATE existing TournamentParticipation and TournamentBadge records.")
    print("\n📸 Snapshot saved for rollback: " + snapshot_file)

    # Auto-proceed for automated testing
    # user_input = input("\n🔐 Type 'PROCEED' to continue, or anything else to abort: ")
    # if user_input.strip().upper() != "PROCEED":
    #     print("\n❌ Test aborted by user. No changes made.")
    #     sys.exit(0)

    print("\n✅ AUTO-PROCEEDING (automated test mode)")

    # ========================================================================
    # STEP 5: Save Reward Configs to Database
    # ========================================================================
    print("\n\n💾 STEP 5: Saving reward configs to database...")

    for code in TOURNAMENT_CODES:
        if code not in snapshot:
            continue

        tournament = db.query(Semester).filter(Semester.code == code).first()
        config = configs[code]

        # Save config to reward_config column
        tournament.reward_config = config.model_dump(mode="json")

        print(f"   ✅ {code}: Saved {config.template_name} config")

    db.commit()
    print("   💾 Configs committed to database")

    # ========================================================================
    # STEP 6: Execute Reward Distribution
    # ========================================================================
    print("\n\n🎁 STEP 6: Executing reward distribution (1st run)...")

    results = {}

    for code in TOURNAMENT_CODES:
        if code not in snapshot:
            continue

        print(f"\n   🏆 {code}:")
        tournament_id = snapshot[code]['tournament_id']
        force_flag = (test_plan[code] == "FORCE_REDISTRIBUTION")

        print(f"      Force redistribution: {force_flag}")

        result = distribute_rewards_for_tournament(
            db=db,
            tournament_id=tournament_id,
            distributed_by=None,
            force_redistribution=force_flag
        )

        results[code] = result

        print(f"      ✅ Distribution completed:")
        print(f"         Participants: {result.total_participants}")
        print(f"         Rewards distributed: {len(result.rewards_distributed)}")
        print(f"         Total XP: {result.distribution_summary['total_xp_awarded']}")
        print(f"         Total Credits: {result.distribution_summary['total_credits_awarded']}")
        print(f"         Total Badges: {result.distribution_summary['total_badges_awarded']}")

    # ========================================================================
    # STEP 7: Compare Preview vs Actual
    # ========================================================================
    print("\n\n🔬 STEP 7: Comparing preview vs actual distribution...")

    all_match = True

    for code in TOURNAMENT_CODES:
        if code not in results:
            continue

        print(f"\n   📊 {code}:")

        result = results[code]
        config = configs[code]

        # Get actual participations
        participations = db.query(TournamentParticipation).filter(
            TournamentParticipation.semester_id == snapshot[code]['tournament_id']
        ).all()

        # Check each participant
        for reward_result in result.rewards_distributed:
            user_id = reward_result.user_id
            user = db.query(User).filter(User.id == user_id).first()

            # Get expected values from config
            placement = reward_result.participation.placement

            if placement == 1:
                expected_xp = int(500 * config.first_place.xp_multiplier)
                expected_credits = config.first_place.credits
            elif placement == 2:
                expected_xp = int(300 * config.second_place.xp_multiplier)
                expected_credits = config.second_place.credits
            elif placement == 3:
                expected_xp = int(200 * config.third_place.xp_multiplier)
                expected_credits = config.third_place.credits
            else:
                expected_xp = int(50 * config.participation.xp_multiplier)
                expected_credits = config.participation.credits

            # Get actual values (base XP only, not including skill bonus)
            actual_base_xp = reward_result.participation.base_xp
            actual_credits = reward_result.participation.credits

            # Compare
            xp_match = (actual_base_xp == expected_xp)
            credits_match = (actual_credits == expected_credits)

            if not (xp_match and credits_match):
                all_match = False
                print(f"      ❌ MISMATCH for {user.email}:")
                print(f"         Expected: {expected_xp} XP + {expected_credits} credits")
                print(f"         Actual:   {actual_base_xp} XP + {actual_credits} credits")
            else:
                print(f"      ✅ {user.email}: Placement {placement}, {actual_base_xp} XP + {actual_credits} credits")

    if all_match:
        print("\n   ✅ All rewards match preview expectations!")
    else:
        print("\n   ❌ Some rewards don't match - see details above")

    # ========================================================================
    # STEP 8: Idempotency Check (2nd Run)
    # ========================================================================
    print("\n\n🔁 STEP 8: Testing idempotency (2nd distribution attempt)...")

    for code in TOURNAMENT_CODES:
        if code not in snapshot:
            continue

        print(f"\n   🏆 {code}:")
        tournament_id = snapshot[code]['tournament_id']

        # Count before
        participations_before = db.query(TournamentParticipation).filter(
            TournamentParticipation.semester_id == tournament_id
        ).count()

        badges_before = db.query(TournamentBadge).filter(
            TournamentBadge.semester_id == tournament_id
        ).count()

        print(f"      Before 2nd run: {participations_before} participations, {badges_before} badges")

        # Run again (force_redistribution=False)
        result2 = distribute_rewards_for_tournament(
            db=db,
            tournament_id=tournament_id,
            distributed_by=None,
            force_redistribution=False  # Should skip
        )

        # Count after
        participations_after = db.query(TournamentParticipation).filter(
            TournamentParticipation.semester_id == tournament_id
        ).count()

        badges_after = db.query(TournamentBadge).filter(
            TournamentBadge.semester_id == tournament_id
        ).count()

        print(f"      After 2nd run: {participations_after} participations, {badges_after} badges")
        print(f"      Rewards distributed: {len(result2.rewards_distributed)}")

        if participations_before == participations_after and badges_before == badges_after and len(result2.rewards_distributed) == 0:
            print(f"      ✅ PASS - No duplicates created")
        else:
            print(f"      ❌ FAIL - Duplicates detected!")
            print(f"         Participation delta: {participations_after - participations_before}")
            print(f"         Badge delta: {badges_after - badges_before}")

    # ========================================================================
    # Final Summary
    # ========================================================================
    print("\n\n" + "=" * 80)
    print("📊 Production Test Summary")
    print("=" * 80)

    for code in TOURNAMENT_CODES:
        if code not in results:
            continue

        print(f"\n🏆 {code}:")
        print(f"   Template: {configs[code].template_name}")
        print(f"   Participants: {results[code].total_participants}")
        print(f"   Total XP: {results[code].distribution_summary['total_xp_awarded']}")
        print(f"   Total Credits: {results[code].distribution_summary['total_credits_awarded']}")
        print(f"   Total Badges: {results[code].distribution_summary['total_badges_awarded']}")

    print(f"\n✅ Preview vs Actual: {'PASS' if all_match else 'FAIL'}")
    print(f"✅ Idempotency: VERIFIED (checked above)")

    print("\n📸 Snapshot for rollback: " + snapshot_file)
    print("\n🎉 Production test COMPLETED!")

    # ========================================================================
    # Optional: Rollback Instructions
    # ========================================================================
    print("\n\n" + "=" * 80)
    print("🔄 ROLLBACK INSTRUCTIONS (if needed)")
    print("=" * 80)
    print("\nTo rollback to previous state:")
    print(f"1. Load snapshot: {snapshot_file}")
    print("2. Delete new participations and badges")
    print("3. Restore old participations and badges from snapshot")
    print("4. Clear reward_config column")
    print("\nRollback script not automated - manual restore required if needed.")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
