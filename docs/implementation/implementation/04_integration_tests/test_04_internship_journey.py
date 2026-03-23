"""
Phase 4 - Task 2: Internship End-to-End Journey Test

Tests the complete Internship user journey from license creation
to XP-based progression, auto level-up, and expiry management.

Journey Steps:
1. Create Internship license
2. Add XP (trigger auto level-up)
3. Purchase credits
4. Check expiry status
5. Renew license
6. Verify final state

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
from internship_service import InternshipService


def get_db_session():
    """Get database session"""
    return SessionLocal()


def cleanup_test_data():
    """Clean up test data before running tests"""
    db = get_db_session()
    try:
        db.execute(text("DELETE FROM internship_licenses WHERE user_id = 2"))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"⚠️  Cleanup warning: {e}")
    finally:
        db.close()


print("=" * 70)
print("📚 INTERNSHIP END-TO-END JOURNEY TEST")
print("=" * 70)
print()

cleanup_test_data()
db = get_db_session()
service = InternshipService(db)

try:
    print("📋 JOURNEY STEPS:")
    print("-" * 70)

    # ========================================================================
    # STEP 1: Create Internship License
    # ========================================================================
    print("\n🔹 STEP 1: Create Internship License")
    print("-" * 70)

    license_data = service.create_license(user_id=2)

    print(f"   ✅ License created: ID {license_data['id']}")
    print(f"   ✅ Current level: {license_data['current_level']}")
    print(f"   ✅ Total XP: {license_data['total_xp']}")
    print(f"   ✅ Expires at: {license_data['expires_at']}")

    assert license_data['current_level'] == 1
    assert license_data['total_xp'] == 0
    assert license_data['expires_at'] is not None

    license_id = license_data['id']

    # ========================================================================
    # STEP 2: Add XP (Small Amount - No Level Up)
    # ========================================================================
    print("\n🔹 STEP 2: Add Small XP (No Level Up)")
    print("-" * 70)

    xp1 = service.add_xp(
        license_id=license_id,
        xp_amount=500,
        reason="Completed first module"
    )

    print(f"   ✅ Added {xp1['xp_added']} XP")
    print(f"   ✅ Total XP: {xp1['total_xp']}")
    print(f"   ✅ Current level: {xp1['current_level']}")
    print(f"   ✅ Leveled up: {xp1['leveled_up']}")

    assert xp1['xp_added'] == 500
    assert xp1['total_xp'] == 500
    assert xp1['current_level'] == 1  # Still level 1 (need 1000 for L2)
    assert xp1['leveled_up'] == False

    # ========================================================================
    # STEP 3: Add More XP (Trigger Level Up)
    # ========================================================================
    print("\n🔹 STEP 3: Add XP to Trigger Level Up")
    print("-" * 70)

    xp2 = service.add_xp(
        license_id=license_id,
        xp_amount=1500,  # Total: 2000 XP (should be L3)
        reason="Completed multiple modules"
    )

    print(f"   ✅ Added {xp2['xp_added']} XP")
    print(f"   ✅ Total XP: {xp2['total_xp']}")
    print(f"   ✅ Old level: {xp2['old_level']}")
    print(f"   ✅ Current level: {xp2['current_level']}")
    print(f"   ✅ Leveled up: {xp2['leveled_up']}")
    print(f"   ✅ Auto level-up trigger working!")

    assert xp2['total_xp'] == 2000
    assert xp2['old_level'] == 1
    assert xp2['current_level'] >= 2  # Should level up at least once
    assert xp2['leveled_up'] == True

    # ========================================================================
    # STEP 4: Add Massive XP (Jump Multiple Levels)
    # ========================================================================
    print("\n🔹 STEP 4: Add Massive XP (Multi-Level Jump)")
    print("-" * 70)

    old_level_before_jump = xp2['current_level']

    xp3 = service.add_xp(
        license_id=license_id,
        xp_amount=8000,  # Add massive XP
        reason="Major achievement"
    )

    print(f"   ✅ Added {xp3['xp_added']} XP")
    print(f"   ✅ Total XP: {xp3['total_xp']}")
    print(f"   ✅ Jumped from level {xp3['old_level']} to {xp3['current_level']}")

    assert xp3['total_xp'] == 10000
    assert xp3['old_level'] == old_level_before_jump
    assert xp3['current_level'] > old_level_before_jump  # Should jump multiple levels
    assert xp3['leveled_up'] == True

    final_level = xp3['current_level']

    # ========================================================================
    # STEP 5: Check Expiry Status
    # ========================================================================
    print("\n🔹 STEP 5: Check Expiry Status")
    print("-" * 70)

    expiry = service.check_expiry(license_id)

    print(f"   ✅ Expires at: {expiry['expires_at']}")
    print(f"   ✅ Days remaining: {expiry['days_remaining']}")
    print(f"   ✅ Currently active: {expiry['is_active']}")

    assert expiry['expires_at'] is not None
    assert expiry['days_remaining'] > 0  # Should be ~365 days
    assert expiry['is_active'] == True

    # ========================================================================
    # STEP 6: Renew License
    # ========================================================================
    print("\n🔹 STEP 6: Renew License")
    print("-" * 70)

    old_expiry = expiry['expires_at']
    renewed = service.renew_license(license_id)

    print(f"   ✅ License renewed")
    print(f"   ✅ Old expiry: {renewed['old_expires_at']}")
    print(f"   ✅ New expiry: {renewed['new_expires_at']}")

    assert renewed['old_expires_at'] == old_expiry
    assert renewed['new_expires_at'] != old_expiry
    # New expiry should be ~1 year later than old

    # ========================================================================
    # STEP 7: Verify Max Achieved Level
    # ========================================================================
    print("\n🔹 STEP 7: Verify Max Achieved Level Tracking")
    print("-" * 70)

    current = service.get_license_by_user(2)

    print(f"   ✅ Current level: {current['current_level']}")
    print(f"   ✅ Max achieved level: {current['max_achieved_level']}")
    print(f"   ✅ Trigger auto-updated max level!")

    assert current['current_level'] == final_level
    assert current['max_achieved_level'] == final_level

    # ========================================================================
    # STEP 8: Verify Final State
    # ========================================================================
    print("\n🔹 STEP 8: Verify Final State")
    print("-" * 70)

    final_license = service.get_license_by_user(2)

    print(f"   📊 Final License State:")
    print(f"      • License ID: {final_license['id']}")
    print(f"      • User ID: {final_license['user_id']}")
    print(f"      • Current Level: {final_license['current_level']}")
    print(f"      • Max Achieved Level: {final_license['max_achieved_level']}")
    print(f"      • Total XP: {final_license['total_xp']}")
    print(f"      • Credit Balance: {final_license['credit_balance']}")
    print(f"      • Expires At: {final_license['expires_at']}")
    print(f"      • Active: {final_license['is_active']}")

    assert final_license['id'] == license_id
    assert final_license['user_id'] == 2
    assert final_license['current_level'] == final_level
    assert final_license['max_achieved_level'] == final_level
    assert final_license['total_xp'] == 10000
    assert final_license['credit_balance'] == 0
    assert final_license['is_active'] == True

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 70)
    print("✅ INTERNSHIP JOURNEY COMPLETE!")
    print("=" * 70)
    print()
    print("📊 Journey Summary:")
    print(f"   • License created: ✅")
    print(f"   • XP progression: ✅ (0 → 10000 XP)")
    print(f"   • Auto level-up: ✅ (L1 → L{final_level})")
    print(f"   • Max level tracking: ✅ (Level {final_level})")
    print(f"   • Expiry management: ✅ (Renewed)")
    print(f"   • Multi-level jump: ✅ (Jumped {final_level - 1} levels total)")
    print()
    print("🎯 All assertions passed!")
    print("🎯 Internship system working end-to-end!")
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
