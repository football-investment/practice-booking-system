"""
Phase 4 - Task 2: Coach End-to-End Journey Test

Tests the complete Coach certification journey from license creation
to theory/practice hours accumulation, level promotion, and renewal.

Journey Steps:
1. Create Coach license
2. Add theory hours
3. Add practice hours
4. Promote certification level
5. Check expiry status
6. Renew certification
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
from coach_service import CoachService


def get_db_session():
    """Get database session"""
    return SessionLocal()


def cleanup_test_data():
    """Clean up test data before running tests"""
    db = get_db_session()
    try:
        db.execute(text("DELETE FROM coach_licenses WHERE user_id = 2"))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"⚠️  Cleanup warning: {e}")
    finally:
        db.close()


print("=" * 70)
print("👨‍🏫 COACH END-TO-END JOURNEY TEST")
print("=" * 70)
print()

cleanup_test_data()
db = get_db_session()
service = CoachService(db)

try:
    print("📋 JOURNEY STEPS:")
    print("-" * 70)

    # ========================================================================
    # STEP 1: Create Coach License
    # ========================================================================
    print("\n🔹 STEP 1: Create Coach License")
    print("-" * 70)

    license_data = service.create_license(user_id=2)

    print(f"   ✅ License created: ID {license_data['id']}")
    print(f"   ✅ Current level: {license_data['current_level']}")
    print(f"   ✅ Theory hours: {license_data['theory_hours']}")
    print(f"   ✅ Practice hours: {license_data['practice_hours']}")
    print(f"   ✅ Expires at: {license_data['expires_at']}")

    assert license_data['current_level'] == 1
    assert license_data['theory_hours'] == 0
    assert license_data['practice_hours'] == 0
    assert license_data['expires_at'] is not None

    license_id = license_data['id']

    # ========================================================================
    # STEP 2: Add Theory Hours
    # ========================================================================
    print("\n🔹 STEP 2: Add Theory Hours")
    print("-" * 70)

    theory1 = service.add_theory_hours(
        license_id=license_id,
        hours=20
    )

    print(f"   ✅ Added {theory1['hours_added']} theory hours")
    print(f"   ✅ Total theory hours: {theory1['total_theory_hours']}")

    assert theory1['hours_added'] == 20
    assert theory1['total_theory_hours'] == 20

    # Add more theory hours
    theory2 = service.add_theory_hours(
        license_id=license_id,
        hours=30
    )

    print(f"   ✅ Added additional {theory2['hours_added']} theory hours")
    print(f"   ✅ Total theory hours: {theory2['total_theory_hours']}")

    assert theory2['total_theory_hours'] == 50

    # ========================================================================
    # STEP 3: Add Practice Hours
    # ========================================================================
    print("\n🔹 STEP 3: Add Practice Hours")
    print("-" * 70)

    practice1 = service.add_practice_hours(
        license_id=license_id,
        hours=15
    )

    print(f"   ✅ Added {practice1['hours_added']} practice hours")
    print(f"   ✅ Total practice hours: {practice1['total_practice_hours']}")

    assert practice1['hours_added'] == 15
    assert practice1['total_practice_hours'] == 15

    # Add more practice hours
    practice2 = service.add_practice_hours(
        license_id=license_id,
        hours=25
    )

    print(f"   ✅ Added additional {practice2['hours_added']} practice hours")
    print(f"   ✅ Total practice hours: {practice2['total_practice_hours']}")

    assert practice2['total_practice_hours'] == 40

    # ========================================================================
    # STEP 4: Verify Hours Accumulation
    # ========================================================================
    print("\n🔹 STEP 4: Verify Hours Accumulation")
    print("-" * 70)

    current = service.get_license_by_user(2)

    print(f"   📊 Current Hours:")
    print(f"      • Theory hours: {current['theory_hours']}")
    print(f"      • Practice hours: {current['practice_hours']}")
    print(f"      • Total hours: {current['theory_hours'] + current['practice_hours']}")

    assert current['theory_hours'] == 50
    assert current['practice_hours'] == 40
    assert current['theory_hours'] + current['practice_hours'] == 90

    # ========================================================================
    # STEP 5: Promote Certification Level
    # ========================================================================
    print("\n🔹 STEP 5: Promote Certification Level")
    print("-" * 70)

    promoted1 = service.promote_level(license_id)

    print(f"   ✅ Promoted from level {promoted1['old_level']} to {promoted1['new_level']}")

    assert promoted1['old_level'] == 1
    assert promoted1['new_level'] == 2

    # Promote again
    promoted2 = service.promote_level(license_id)
    print(f"   ✅ Promoted to level {promoted2['new_level']}")

    assert promoted2['new_level'] == 3

    # Promote to level 4
    promoted3 = service.promote_level(license_id)
    print(f"   ✅ Promoted to level {promoted3['new_level']}")

    assert promoted3['new_level'] == 4

    final_level = promoted3['new_level']

    # ========================================================================
    # STEP 6: Check Expiry Status
    # ========================================================================
    print("\n🔹 STEP 6: Check Expiry Status")
    print("-" * 70)

    expiry = service.check_expiry(license_id)

    print(f"   ✅ Expires at: {expiry['expires_at']}")
    print(f"   ✅ Days remaining: {expiry['days_remaining']}")
    print(f"   ✅ Is expired: {expiry['is_expired']}")

    assert expiry['expires_at'] is not None
    assert expiry['days_remaining'] > 0  # Should be ~730 days (2 years)
    assert expiry['is_expired'] == False

    # ========================================================================
    # STEP 7: Renew Certification
    # ========================================================================
    print("\n🔹 STEP 7: Renew Certification")
    print("-" * 70)

    old_expiry = expiry['expires_at']
    renewed = service.renew_certification(license_id)

    print(f"   ✅ Certification renewed")
    print(f"   ✅ Old expiry: {renewed['old_expires_at']}")
    print(f"   ✅ New expiry: {renewed['new_expires_at']}")

    assert renewed['old_expires_at'] == old_expiry
    assert renewed['new_expires_at'] != old_expiry

    # ========================================================================
    # STEP 8: Verify Max Achieved Level
    # ========================================================================
    print("\n🔹 STEP 8: Verify Max Achieved Level Tracking")
    print("-" * 70)

    current = service.get_license_by_user(2)

    print(f"   ✅ Current level: {current['current_level']}")
    print(f"   ✅ Max achieved level: {current['max_achieved_level']}")
    print(f"   ✅ Trigger auto-updated max level!")

    assert current['current_level'] == final_level
    assert current['max_achieved_level'] == final_level

    # ========================================================================
    # STEP 9: Verify Final State
    # ========================================================================
    print("\n🔹 STEP 9: Verify Final State")
    print("-" * 70)

    final_license = service.get_license_by_user(2)

    print(f"   📊 Final License State:")
    print(f"      • License ID: {final_license['id']}")
    print(f"      • User ID: {final_license['user_id']}")
    print(f"      • Current Level: {final_license['current_level']}")
    print(f"      • Max Achieved Level: {final_license['max_achieved_level']}")
    print(f"      • Theory Hours: {final_license['theory_hours']}")
    print(f"      • Practice Hours: {final_license['practice_hours']}")
    print(f"      • Total Hours: {final_license['theory_hours'] + final_license['practice_hours']}")
    print(f"      • Expires At: {final_license['expires_at']}")
    print(f"      • Is Expired: {final_license['is_expired']}")
    print(f"      • Active: {final_license['is_active']}")

    assert final_license['id'] == license_id
    assert final_license['user_id'] == 2
    assert final_license['current_level'] == final_level
    assert final_license['max_achieved_level'] == final_level
    assert final_license['theory_hours'] == 50
    assert final_license['practice_hours'] == 40
    assert final_license['is_expired'] == False
    assert final_license['is_active'] == True

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 70)
    print("✅ COACH JOURNEY COMPLETE!")
    print("=" * 70)
    print()
    print("📊 Journey Summary:")
    print(f"   • License created: ✅")
    print(f"   • Theory hours accumulated: ✅ (50 hours)")
    print(f"   • Practice hours accumulated: ✅ (40 hours)")
    print(f"   • Level progression: ✅ (L1 → L{final_level})")
    print(f"   • Max level tracking: ✅ (Level {final_level})")
    print(f"   • Expiry management: ✅ (Renewed)")
    print(f"   • Total training hours: ✅ (90 hours)")
    print()
    print("🎯 All assertions passed!")
    print("🎯 Coach certification system working end-to-end!")
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
