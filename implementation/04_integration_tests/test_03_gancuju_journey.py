"""
Phase 4 - Task 2: GānCuju End-to-End Journey Test

Tests the complete GānCuju user journey from license creation
to level progression and teaching hours tracking.

Journey Steps:
1. Create GānCuju license at level 1
2. Record competition (win)
3. Promote to higher level
4. Record teaching hours
5. Win more competitions (track win rate)
6. Promote to max level
7. Verify final state

Author: LFA Development Team
Date: 2025-12-09
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import service
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../02_backend_services')))
from gancuju_service import GanCujuService


def get_db_session():
    """Get database session"""
    return SessionLocal()


def cleanup_test_data():
    """Clean up test data before running tests"""
    db = get_db_session()
    try:
        db.execute(text("DELETE FROM gancuju_licenses WHERE user_id = 2"))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"⚠️  Cleanup warning: {e}")
    finally:
        db.close()


print("=" * 70)
print("🥋 GĀNCUJU END-TO-END JOURNEY TEST")
print("=" * 70)
print()

cleanup_test_data()
db = get_db_session()
service = GanCujuService(db)

try:
    print("📋 JOURNEY STEPS:")
    print("-" * 70)

    # ========================================================================
    # STEP 1: Create GānCuju License at Level 1
    # ========================================================================
    print("\n🔹 STEP 1: Create GānCuju License")
    print("-" * 70)

    license_data = service.create_license(
        user_id=2,
        starting_level=1
    )

    print(f"   ✅ License created: ID {license_data['id']}")
    print(f"   ✅ Starting level: {license_data['current_level']}")
    print(f"   ✅ Max achieved level: {license_data['max_achieved_level']}")
    print(f"   ✅ Competitions entered: {license_data['competitions_entered']}")

    assert license_data['current_level'] == 1
    assert license_data['max_achieved_level'] == 1
    assert license_data['competitions_entered'] == 0

    license_id = license_data['id']

    # ========================================================================
    # STEP 2: Record First Competition (WIN)
    # ========================================================================
    print("\n🔹 STEP 2: Record First Competition (Win)")
    print("-" * 70)

    comp1 = service.record_competition(
        license_id=license_id,
        won=True
    )

    print(f"   ✅ Competition recorded: Win")
    print(f"   ✅ Competitions entered: {comp1['competitions_entered']}")
    print(f"   ✅ Competitions won: {comp1['competitions_won']}")
    print(f"   ✅ Win rate: {comp1['win_rate']:.1%}")

    assert comp1['competitions_entered'] == 1
    assert comp1['competitions_won'] == 1
    assert abs(float(comp1['win_rate']) - 100.0) < 0.1  # 100%

    # ========================================================================
    # STEP 3: Promote to Level 2
    # ========================================================================
    print("\n🔹 STEP 3: Promote to Level 2")
    print("-" * 70)

    promoted = service.promote_level(license_id)

    print(f"   ✅ Promoted from level {promoted['old_level']} to {promoted['new_level']}")

    assert promoted['old_level'] == 1
    assert promoted['new_level'] == 2

    # Verify max_achieved_level updated via trigger
    after_promote = service.get_license_by_user(2)
    assert after_promote['max_achieved_level'] == 2
    print(f"   ✅ Max achieved level: {after_promote['max_achieved_level']}")

    # ========================================================================
    # STEP 4: Record Teaching Hours
    # ========================================================================
    print("\n🔹 STEP 4: Record Teaching Hours")
    print("-" * 70)

    teaching1 = service.record_teaching_hours(
        license_id=license_id,
        hours=10
    )

    print(f"   ✅ Added 10 teaching hours")
    print(f"   ✅ Total teaching hours: {teaching1['total_teaching_hours']}")

    assert teaching1['hours_added'] == 10
    assert teaching1['total_teaching_hours'] == 10

    # Add more teaching hours
    teaching2 = service.record_teaching_hours(
        license_id=license_id,
        hours=15
    )

    print(f"   ✅ Added additional 15 teaching hours")
    print(f"   ✅ Total teaching hours: {teaching2['total_teaching_hours']}")

    assert teaching2['total_teaching_hours'] == 25

    # ========================================================================
    # STEP 5: Record More Competitions (Mix of Wins/Losses)
    # ========================================================================
    print("\n🔹 STEP 5: Record More Competitions")
    print("-" * 70)

    # Win
    service.record_competition(license_id, won=True)
    print(f"   ✅ Competition 2: Win")

    # Loss
    service.record_competition(license_id, won=False)
    print(f"   ✅ Competition 3: Loss")

    # Win
    service.record_competition(license_id, won=True)
    print(f"   ✅ Competition 4: Win")

    # Get current state
    current = service.get_license_by_user(2)

    print(f"\n   📊 Competition Statistics:")
    print(f"      • Total entered: {current['competitions_entered']}")
    print(f"      • Total won: {current['competitions_won']}")
    print(f"      • Win rate: {current['win_rate']:.1%}")

    assert current['competitions_entered'] == 4
    assert current['competitions_won'] == 3  # 3 wins out of 4
    assert abs(float(current['win_rate']) - 75.0) < 0.1  # 75%

    # ========================================================================
    # STEP 6: Promote to Higher Levels
    # ========================================================================
    print("\n🔹 STEP 6: Promote to Higher Levels")
    print("-" * 70)

    # Promote to level 3
    service.promote_level(license_id)
    print(f"   ✅ Promoted to level 3")

    # Promote to level 4
    service.promote_level(license_id)
    print(f"   ✅ Promoted to level 4")

    # Promote to level 5
    service.promote_level(license_id)
    print(f"   ✅ Promoted to level 5")

    current_level = service.get_license_by_user(2)
    print(f"\n   🎯 Current level: {current_level['current_level']}")
    print(f"   🏆 Max achieved level: {current_level['max_achieved_level']}")

    assert current_level['current_level'] == 5
    assert current_level['max_achieved_level'] == 5

    # ========================================================================
    # STEP 7: Verify Final State
    # ========================================================================
    print("\n🔹 STEP 7: Verify Final State")
    print("-" * 70)

    final_license = service.get_license_by_user(2)

    print(f"   📊 Final License State:")
    print(f"      • License ID: {final_license['id']}")
    print(f"      • User ID: {final_license['user_id']}")
    print(f"      • Current Level: {final_license['current_level']}")
    print(f"      • Max Achieved Level: {final_license['max_achieved_level']}")
    print(f"      • Competitions Entered: {final_license['competitions_entered']}")
    print(f"      • Competitions Won: {final_license['competitions_won']}")
    print(f"      • Win Rate: {final_license['win_rate']:.1%}")
    print(f"      • Teaching Hours: {final_license['teaching_hours']}")
    print(f"      • Active: {final_license['is_active']}")

    assert final_license['id'] == license_id
    assert final_license['user_id'] == 2
    assert final_license['current_level'] == 5
    assert final_license['max_achieved_level'] == 5
    assert final_license['competitions_entered'] == 4
    assert final_license['competitions_won'] == 3
    assert abs(float(final_license['win_rate']) - 75.0) < 0.1  # 75%
    assert final_license['teaching_hours'] == 25
    assert final_license['is_active'] == True

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 70)
    print("✅ GĀNCUJU JOURNEY COMPLETE!")
    print("=" * 70)
    print()
    print("📊 Journey Summary:")
    print(f"   • License created: ✅")
    print(f"   • Level progression: ✅ (1 → 5)")
    print(f"   • Competitions tracked: ✅ (4 total, 3 wins)")
    print(f"   • Win rate computed: ✅ (75%)")
    print(f"   • Teaching hours tracked: ✅ (25 hours)")
    print(f"   • Max level tracking: ✅ (Level 5)")
    print()
    print("🎯 All assertions passed!")
    print("🎯 GānCuju system working end-to-end!")
    print()
    print("=" * 70)

except AssertionError as e:
    print(f"\n❌ ASSERTION FAILED: {e}")
    raise
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    raise
finally:
    db.close()
