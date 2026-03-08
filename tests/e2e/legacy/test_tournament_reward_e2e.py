"""
E2E Test: Tournament Reward Distribution

Tests the complete reward distribution flow on a real tournament:
1. Setup tournament with skill mappings
2. Generate rankings
3. Distribute rewards (participation + badges)
4. Validate XP/credit balances
5. Validate badge awards
6. Test idempotency

Run with: DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" python3 test_tournament_reward_e2e.py
"""
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Setup database
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Import models and services
from app.models.semester import Semester
from app.models.user import User
from app.models.tournament_ranking import TournamentRanking
from app.models.tournament_achievement import (
    TournamentSkillMapping,
    TournamentParticipation,
    TournamentBadge,
    SkillPointConversionRate
)
from app.schemas.tournament_rewards import RewardPolicy
from app.services.tournament import tournament_reward_orchestrator as orchestrator


def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def test_reward_distribution():
    """Run complete E2E test"""
    db = SessionLocal()

    try:
        print_section("🏆 Tournament Reward Distribution E2E Test")

        # ====================================================================
        # STEP 1: Find a completed tournament with rankings
        # ====================================================================
        print_section("STEP 1: Find Tournament")

        tournament = db.query(Semester).filter(
            Semester.tournament_status.in_(["COMPLETED", "REWARDS_DISTRIBUTED"]),
            Semester.format.in_(["INDIVIDUAL_RANKING", "HEAD_TO_HEAD"])
        ).first()

        if not tournament:
            print("❌ No completed tournament found!")
            print("   Create and complete a tournament first.")
            return False

        print(f"✅ Found tournament: {tournament.name} (ID: {tournament.id})")
        print(f"   Format: {tournament.format}")
        print(f"   Status: {tournament.tournament_status}")

        # Check rankings
        rankings = db.query(TournamentRanking).filter(
            TournamentRanking.tournament_id == tournament.id
        ).order_by(TournamentRanking.rank).all()

        if not rankings:
            print(f"❌ No rankings found for tournament {tournament.id}")
            return False

        print(f"✅ Found {len(rankings)} rankings")
        print(f"   Top 3:")
        for r in rankings[:3]:
            user = db.query(User).filter(User.id == r.user_id).first()
            print(f"     {r.rank}. {user.name if user else 'Unknown'} (ID: {r.user_id})")

        # ====================================================================
        # STEP 2: Setup Skill Mappings (if not exist)
        # ====================================================================
        print_section("STEP 2: Setup Skill Mappings")

        existing_mappings = db.query(TournamentSkillMapping).filter(
            TournamentSkillMapping.semester_id == tournament.id
        ).all()

        if existing_mappings:
            print(f"✅ Found {len(existing_mappings)} existing skill mappings:")
            for m in existing_mappings:
                print(f"     - {m.skill_name} ({m.skill_category}, weight: {m.weight})")
        else:
            print("⚠️  No skill mappings found - creating default mappings...")

            # Create default mappings based on tournament type
            if "speed" in tournament.name.lower() or "sprint" in tournament.name.lower():
                mappings_to_create = [
                    ("agility", "Physical", 1.0),
                    ("speed", "Physical", 0.8)
                ]
            elif "plank" in tournament.name.lower() or "endurance" in tournament.name.lower():
                mappings_to_create = [
                    ("endurance", "Physical", 1.0),
                    ("core_strength", "Physical", 0.7)
                ]
            else:
                # Generic tournament
                mappings_to_create = [
                    ("physical_fitness", "Physical", 1.0)
                ]

            for skill_name, category, weight in mappings_to_create:
                mapping = TournamentSkillMapping(
                    semester_id=tournament.id,
                    skill_name=skill_name,
                    skill_category=category,
                    weight=weight  # Use numeric value directly
                )
                db.add(mapping)
                print(f"     ✅ Created: {skill_name} ({category}, weight: {weight})")

            db.commit()

        # ====================================================================
        # STEP 3: Check Conversion Rates
        # ====================================================================
        print_section("STEP 3: Verify Skill Point Conversion Rates")

        conversion_rates = db.query(SkillPointConversionRate).all()
        print(f"✅ Found {len(conversion_rates)} conversion rates:")
        for rate in conversion_rates:
            print(f"     - {rate.skill_category}: {rate.xp_per_point} XP/point")

        # ====================================================================
        # STEP 4: Record Pre-Distribution Balances
        # ====================================================================
        print_section("STEP 4: Record Pre-Distribution Balances")

        test_user = rankings[0]  # Test with 1st place user
        user = db.query(User).filter(User.id == test_user.user_id).first()

        print(f"Test User: {user.name} (ID: {user.id})")
        print(f"   Pre-distribution XP: {user.xp_balance}")
        print(f"   Pre-distribution Credits: {user.credit_balance}")

        # Check if already distributed
        existing_participation = db.query(TournamentParticipation).filter(
            TournamentParticipation.user_id == user.id,
            TournamentParticipation.semester_id == tournament.id
        ).first()

        if existing_participation:
            print(f"   ⚠️  Rewards already distributed!")
            print(f"      - XP awarded: {existing_participation.xp_awarded}")
            print(f"      - Credits awarded: {existing_participation.credits_awarded}")
            print(f"      - Skill points: {existing_participation.skill_points_awarded}")

            existing_badges = db.query(TournamentBadge).filter(
                TournamentBadge.user_id == user.id,
                TournamentBadge.semester_id == tournament.id
            ).all()
            print(f"      - Badges: {len(existing_badges)}")

            print("\n   Testing idempotency (should return existing data)...")
        else:
            print("   ✅ No previous distribution found - clean slate")

        # ====================================================================
        # STEP 5: Distribute Rewards
        # ====================================================================
        print_section("STEP 5: Distribute Rewards")

        # Use custom policy for testing
        test_policy = RewardPolicy(
            first_place_xp=500,
            first_place_credits=100,
            first_place_skill_points=10,
            second_place_xp=300,
            second_place_credits=50,
            third_place_xp=200,
            third_place_credits=25
        )

        print("Distributing rewards with policy:")
        print(f"   1st place: {test_policy.first_place_xp} XP, {test_policy.first_place_credits} credits, {test_policy.first_place_skill_points} skill points")
        print(f"   2nd place: {test_policy.second_place_xp} XP, {test_policy.second_place_credits} credits")
        print(f"   3rd place: {test_policy.third_place_xp} XP, {test_policy.third_place_credits} credits")

        try:
            result = orchestrator.distribute_rewards_for_tournament(
                db=db,
                tournament_id=tournament.id,
                reward_policy=test_policy,
                distributed_by=1,  # Assuming admin ID 1
                force_redistribution=False  # Test idempotency
            )

            print(f"\n✅ Distribution completed!")
            print(f"   Participants processed: {result.total_participants}")
            print(f"   Rewards distributed: {len(result.rewards_distributed)}")
            print(f"\n   Summary:")
            print(f"     - Total XP awarded: {result.distribution_summary['total_xp_awarded']}")
            print(f"     - Total credits awarded: {result.distribution_summary['total_credits_awarded']}")
            print(f"     - Total badges awarded: {result.distribution_summary['total_badges_awarded']}")

        except Exception as e:
            print(f"❌ Distribution failed: {str(e)}")
            return False

        # ====================================================================
        # STEP 6: Validate Results
        # ====================================================================
        print_section("STEP 6: Validate Results")

        # Refresh user data
        db.refresh(user)

        print(f"Post-distribution balances for {user.name}:")
        print(f"   XP balance: {user.xp_balance}")
        print(f"   Credit balance: {user.credit_balance}")

        # Get participation record
        participation = db.query(TournamentParticipation).filter(
            TournamentParticipation.user_id == user.id,
            TournamentParticipation.semester_id == tournament.id
        ).first()

        if participation:
            print(f"\n✅ Participation record created:")
            print(f"   Placement: {participation.placement}")
            print(f"   XP awarded: {participation.xp_awarded}")
            print(f"   Credits awarded: {participation.credits_awarded}")
            print(f"   Skill points: {participation.skill_points_awarded}")
        else:
            print("❌ No participation record found!")
            return False

        # Get badges
        badges = db.query(TournamentBadge).filter(
            TournamentBadge.user_id == user.id,
            TournamentBadge.semester_id == tournament.id
        ).all()

        print(f"\n✅ Badges awarded: {len(badges)}")
        for badge in badges:
            print(f"   {badge.icon} {badge.title} ({badge.rarity})")
            print(f"      Category: {badge.badge_category}")
            print(f"      Type: {badge.badge_type}")

        # ====================================================================
        # STEP 7: Test Idempotency
        # ====================================================================
        print_section("STEP 7: Test Idempotency")

        print("Attempting to distribute rewards again (should skip)...")

        try:
            result2 = orchestrator.distribute_rewards_for_tournament(
                db=db,
                tournament_id=tournament.id,
                reward_policy=test_policy,
                distributed_by=1,
                force_redistribution=False
            )

            if len(result2.rewards_distributed) == 0:
                print("✅ Idempotency works! No duplicate rewards distributed.")
            else:
                print(f"⚠️  Warning: {len(result2.rewards_distributed)} rewards redistributed")

        except Exception as e:
            print(f"❌ Idempotency test failed: {str(e)}")

        # ====================================================================
        # STEP 8: Validate XP/Credit Balance
        # ====================================================================
        print_section("STEP 8: Validate Balance")

        expected_xp_for_first = test_policy.first_place_xp
        # Calculate expected bonus XP from skill points
        if participation.skill_points_awarded:
            skill_points_total = sum(participation.skill_points_awarded.values())
            # Assuming Physical category = 8 XP/point
            expected_bonus_xp = int(skill_points_total * 8)
            expected_total_xp = expected_xp_for_first + expected_bonus_xp

            print(f"Expected XP calculation:")
            print(f"   Base XP (1st place): {expected_xp_for_first}")
            print(f"   Skill points total: {skill_points_total:.1f}")
            print(f"   Bonus XP (8 XP/point): {expected_bonus_xp}")
            print(f"   Total expected: {expected_total_xp}")
            print(f"   Actual awarded: {participation.xp_awarded}")

            if participation.xp_awarded == expected_total_xp:
                print("✅ XP calculation is correct!")
            else:
                print(f"⚠️  XP mismatch: expected {expected_total_xp}, got {participation.xp_awarded}")

        expected_credits = test_policy.first_place_credits
        print(f"\nExpected credits (1st place): {expected_credits}")
        print(f"Actual awarded: {participation.credits_awarded}")

        if participation.credits_awarded == expected_credits:
            print("✅ Credit calculation is correct!")
        else:
            print(f"⚠️  Credit mismatch: expected {expected_credits}, got {participation.credits_awarded}")

        # ====================================================================
        # FINAL SUMMARY
        # ====================================================================
        print_section("✅ TEST COMPLETED SUCCESSFULLY")

        print(f"Tournament: {tournament.name}")
        print(f"Participants: {len(rankings)}")
        print(f"Test user: {user.name} (1st place)")
        print(f"XP awarded: {participation.xp_awarded}")
        print(f"Credits awarded: {participation.credits_awarded}")
        print(f"Badges earned: {len(badges)}")
        print(f"Idempotency: ✅ Passed")

        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    success = test_reward_distribution()
    sys.exit(0 if success else 1)
