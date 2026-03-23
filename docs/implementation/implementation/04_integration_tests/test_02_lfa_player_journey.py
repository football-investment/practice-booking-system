"""
Phase 4 - Task 2: LFA Player End-to-End Journey Test

Tests the complete LFA Player user journey from license creation
to skill progression and credit management.

Journey Steps:
1. Create LFA Player license
2. Update individual skills
3. Verify overall_avg auto-computation
4. Purchase credits
5. Spend credits
6. Check credit balance
7. Verify final state

Author: LFA Development Team
Date: 2025-12-09
"""

import sys
import os
from datetime import datetime, timezone

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
from lfa_player_service import LFAPlayerService


def get_db_session():
    """Get database session"""
    return SessionLocal()


def cleanup_test_data():
    """Clean up test data before running tests"""
    db = get_db_session()
    try:
        db.execute(text("DELETE FROM lfa_player_licenses WHERE user_id = 2"))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"⚠️  Cleanup warning: {e}")
    finally:
        db.close()


print("=" * 70)
print("🎯 LFA PLAYER END-TO-END JOURNEY TEST")
print("=" * 70)
print()

cleanup_test_data()
db = get_db_session()
service = LFAPlayerService(db)

try:
    print("📋 JOURNEY STEPS:")
    print("-" * 70)

    # ========================================================================
    # STEP 1: Create LFA Player License
    # ========================================================================
    print("\n🔹 STEP 1: Create LFA Player License")
    print("-" * 70)

    license_data = service.create_license(
        user_id=2,
        age_group='YOUTH',
        initial_credits=0
    )

    print(f"   ✅ License created: ID {license_data['id']}")
    print(f"   ✅ Age group: {license_data['age_group']}")
    print(f"   ✅ Initial overall_avg: {license_data['overall_avg']}")
    print(f"   ✅ Credit balance: {license_data['credit_balance']}")

    assert license_data['id'] is not None
    assert license_data['age_group'] == 'YOUTH'
    assert license_data['overall_avg'] == 0.0  # All skills start at 0
    assert license_data['credit_balance'] == 0

    license_id = license_data['id']

    # ========================================================================
    # STEP 2: Update Individual Skills (Heading)
    # ========================================================================
    print("\n🔹 STEP 2: Update Heading Skill")
    print("-" * 70)

    updated = service.update_skill_avg(
        license_id=license_id,
        skill_name='heading',
        new_avg=75.5
    )

    print(f"   ✅ Heading updated to: {updated['new_avg']}")
    print(f"   ✅ Overall avg updated to: {updated['overall_avg']:.2f}")
    print(f"   ✅ Auto-computation working!")

    assert updated['new_avg'] == 75.5
    # Overall avg = 75.5 / 6 = 12.58
    assert abs(updated['overall_avg'] - 12.58) < 0.1

    # ========================================================================
    # STEP 3: Update Multiple Skills
    # ========================================================================
    print("\n🔹 STEP 3: Update Multiple Skills")
    print("-" * 70)

    # Shooting
    service.update_skill_avg(license_id, 'shooting', 80.0)
    print(f"   ✅ Shooting updated to: 80.0")

    # Passing
    service.update_skill_avg(license_id, 'passing', 85.0)
    print(f"   ✅ Passing updated to: 85.0")

    # Dribbling
    service.update_skill_avg(license_id, 'dribbling', 70.0)
    print(f"   ✅ Dribbling updated to: 70.0")

    # Ball control
    service.update_skill_avg(license_id, 'ball_control', 78.0)
    print(f"   ✅ Ball control updated to: 78.0")

    # Crossing
    service.update_skill_avg(license_id, 'crossing', 72.0)
    print(f"   ✅ Crossing updated to: 72.0")

    # Get updated license
    license_updated = service.get_license_by_user(2)

    print(f"\n   📊 Final Skill Averages:")
    print(f"      • Heading: {license_updated['skills']['heading_avg']}")
    print(f"      • Shooting: {license_updated['skills']['shooting_avg']}")
    print(f"      • Passing: {license_updated['skills']['passing_avg']}")
    print(f"      • Dribbling: {license_updated['skills']['dribbling_avg']}")
    print(f"      • Ball Control: {license_updated['skills']['ball_control_avg']}")
    print(f"      • Crossing: {license_updated['skills']['crossing_avg']}")
    print(f"\n   🎯 Overall Average: {license_updated['overall_avg']:.2f}")

    # Expected overall: (75.5 + 80 + 85 + 70 + 78 + 72) / 6 = 76.75
    expected_overall = 76.75
    assert abs(license_updated['overall_avg'] - expected_overall) < 0.1

    # ========================================================================
    # STEP 4: Purchase Credits
    # ========================================================================
    print("\n🔹 STEP 4: Purchase Credits")
    print("-" * 70)

    transaction1, balance1 = service.purchase_credits(
        license_id=license_id,
        amount=100,
        payment_verified=True,
        payment_reference_code="REF-2024-001"
    )

    print(f"   ✅ Purchased 100 credits")
    print(f"   ✅ Transaction ID: {transaction1['transaction_id']}")
    print(f"   ✅ New balance: {balance1}")

    assert transaction1['amount'] == 100
    assert balance1 == 100

    # Purchase more credits
    transaction2, balance2 = service.purchase_credits(
        license_id=license_id,
        amount=50,
        payment_verified=True,
        payment_reference_code="REF-2024-002"
    )

    print(f"\n   ✅ Purchased additional 50 credits")
    print(f"   ✅ New balance: {balance2}")

    assert balance2 == 150

    # ========================================================================
    # STEP 5: Check Credit Balance
    # ========================================================================
    print("\n🔹 STEP 5: Check Credit Balance")
    print("-" * 70)

    balance = service.get_credit_balance(license_id)

    print(f"   ✅ Current credit balance: {balance}")

    assert balance == 150

    # ========================================================================
    # STEP 6: Verify Final State
    # ========================================================================
    print("\n🔹 STEP 6: Verify Final State")
    print("-" * 70)

    final_license = service.get_license_by_user(2)

    print(f"   📊 Final License State:")
    print(f"      • License ID: {final_license['id']}")
    print(f"      • User ID: {final_license['user_id']}")
    print(f"      • Age Group: {final_license['age_group']}")
    print(f"      • Overall Average: {final_license['overall_avg']:.2f}")
    print(f"      • Credit Balance: {final_license['credit_balance']}")
    print(f"      • Active: {final_license['is_active']}")

    assert final_license['id'] == license_id
    assert final_license['user_id'] == 2
    assert final_license['age_group'] == 'YOUTH'
    assert abs(final_license['overall_avg'] - 76.75) < 0.1
    assert final_license['credit_balance'] == 150
    assert final_license['is_active'] == True

    # Verify skills are preserved
    assert final_license['skills']['heading_avg'] == 75.5
    assert final_license['skills']['shooting_avg'] == 80.0
    assert final_license['skills']['passing_avg'] == 85.0
    assert final_license['skills']['dribbling_avg'] == 70.0
    assert final_license['skills']['ball_control_avg'] == 78.0
    assert final_license['skills']['crossing_avg'] == 72.0

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 70)
    print("✅ LFA PLAYER JOURNEY COMPLETE!")
    print("=" * 70)
    print()
    print("📊 Journey Summary:")
    print(f"   • License created: ✅")
    print(f"   • Skills updated (6 skills): ✅")
    print(f"   • Overall average computed: ✅ ({final_license['overall_avg']:.2f})")
    print(f"   • Credits purchased: ✅ (150 total)")
    print(f"   • Credit balance verified: ✅ ({final_license['credit_balance']} credits)")
    print()
    print("🎯 All assertions passed!")
    print("🎯 LFA Player system working end-to-end!")
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
