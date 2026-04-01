#!/usr/bin/env python3
"""
Test Suite for Coach Service
Tests certification levels, hours tracking, and expiry management
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import service
from coach_service import CoachService

DB_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

def get_db_session():
    engine = create_engine(DB_URL)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

def test_01_create_license():
    print("\n🧪 Test 1: Create Coach license")
    db = get_db_session()
    service = CoachService(db)

    try:
        # Clean up first
        db.execute(text("DELETE FROM coach_licenses WHERE user_id = 1"))
        db.commit()

        # Create license with 2-year expiry
        license_data = service.create_license(user_id=1, starting_level=1)

        assert license_data['user_id'] == 1
        assert license_data['current_level'] == 1
        assert license_data['max_achieved_level'] == 1
        assert license_data['theory_hours'] == 0
        assert license_data['practice_hours'] == 0
        assert license_data['is_expired'] == False
        assert license_data['is_active'] == True

        # Check expiry is ~2 years from now
        days_until_expiry = (license_data['expires_at'] - datetime.now(timezone.utc)).days
        assert 720 <= days_until_expiry <= 735  # ~2 years

        print(f"   ✅ License created: id={license_data['id']}, expires in {days_until_expiry} days")

        # Clean up
        db.execute(text("DELETE FROM coach_licenses WHERE user_id = 1"))
        db.commit()

    finally:
        db.close()

def test_02_get_license_by_user():
    print("\n🧪 Test 2: Get license by user")
    db = get_db_session()
    service = CoachService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM coach_licenses WHERE user_id = 1"))
        db.commit()

        service.create_license(user_id=1, starting_level=2)

        # Get license
        license_data = service.get_license_by_user(user_id=1)

        assert license_data is not None
        assert license_data['user_id'] == 1
        assert license_data['current_level'] == 2

        print(f"   ✅ Found license: id={license_data['id']}, level={license_data['current_level']}")

        # Clean up
        db.execute(text("DELETE FROM coach_licenses WHERE user_id = 1"))
        db.commit()

    finally:
        db.close()

def test_03_add_theory_hours():
    print("\n🧪 Test 3: Add theory hours")
    db = get_db_session()
    service = CoachService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM coach_licenses WHERE user_id = 1"))
        db.commit()

        license_data = service.create_license(user_id=1)
        license_id = license_data['id']

        # Add theory hours
        service.add_theory_hours(license_id, hours=10, description="Course module 1")
        service.add_theory_hours(license_id, hours=15, description="Course module 2")
        result = service.add_theory_hours(license_id, hours=5, description="Workshop")

        assert result['total_theory_hours'] == 30  # 10 + 15 + 5

        print(f"   ✅ Theory hours added: {result['total_theory_hours']} hours")

        # Clean up
        db.execute(text("DELETE FROM coach_licenses WHERE user_id = 1"))
        db.commit()

    finally:
        db.close()

def test_04_add_practice_hours():
    print("\n🧪 Test 4: Add practice hours")
    db = get_db_session()
    service = CoachService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM coach_licenses WHERE user_id = 1"))
        db.commit()

        license_data = service.create_license(user_id=1)
        license_id = license_data['id']

        # Add practice hours
        service.add_practice_hours(license_id, hours=20, description="Training session 1")
        service.add_practice_hours(license_id, hours=25, description="Training session 2")
        result = service.add_practice_hours(license_id, hours=15, description="Practice exam")

        assert result['total_practice_hours'] == 60  # 20 + 25 + 15

        print(f"   ✅ Practice hours added: {result['total_practice_hours']} hours")

        # Clean up
        db.execute(text("DELETE FROM coach_licenses WHERE user_id = 1"))
        db.commit()

    finally:
        db.close()

def test_05_check_expiry():
    print("\n🧪 Test 5: Check certification expiry")
    db = get_db_session()
    service = CoachService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM coach_licenses WHERE user_id = 1"))
        db.commit()

        license_data = service.create_license(user_id=1, duration_years=2)
        license_id = license_data['id']

        # Check expiry
        expiry_status = service.check_expiry(license_id)

        assert expiry_status['is_expired'] == False
        assert expiry_status['is_active'] == True
        assert expiry_status['days_remaining'] > 700  # ~2 years

        print(f"   ✅ Expiry checked: {expiry_status['days_remaining']} days remaining")

        # Clean up
        db.execute(text("DELETE FROM coach_licenses WHERE user_id = 1"))
        db.commit()

    finally:
        db.close()

def test_06_renew_certification():
    print("\n🧪 Test 6: Renew certification")
    db = get_db_session()
    service = CoachService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM coach_licenses WHERE user_id = 1"))
        db.commit()

        license_data = service.create_license(user_id=1, duration_years=1)  # Short duration
        license_id = license_data['id']

        # Renew for 2 years
        renewal = service.renew_certification(license_id, extension_years=2)

        assert renewal['new_expires_at'] > renewal['old_expires_at']
        assert renewal['extension_years'] == 2

        # Check new expiry is much later
        extension_days = (renewal['new_expires_at'] - renewal['old_expires_at']).days
        assert extension_days > 700  # ~2 years

        print(f"   ✅ Certification renewed: +{extension_days} days")

        # Clean up
        db.execute(text("DELETE FROM coach_licenses WHERE user_id = 1"))
        db.commit()

    finally:
        db.close()

def test_07_promote_level():
    print("\n🧪 Test 7: Promote certification level")
    db = get_db_session()
    service = CoachService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM coach_licenses WHERE user_id = 1"))
        db.commit()

        license_data = service.create_license(user_id=1, starting_level=1)
        license_id = license_data['id']

        # Promote from 1 to 2
        promotion = service.promote_level(license_id, reason="Completed certification exam")

        assert promotion['old_level'] == 1
        assert promotion['new_level'] == 2

        # Verify update
        updated = service.get_license_by_user(user_id=1)
        assert updated['current_level'] == 2
        assert updated['max_achieved_level'] == 2  # Should update via trigger

        print(f"   ✅ Level promoted: {promotion['old_level']} → {promotion['new_level']}")

        # Clean up
        db.execute(text("DELETE FROM coach_licenses WHERE user_id = 1"))
        db.commit()

    finally:
        db.close()

def test_08_get_license_stats():
    print("\n🧪 Test 8: Get license statistics")
    db = get_db_session()
    service = CoachService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM coach_licenses WHERE user_id = 1"))
        db.commit()

        license_data = service.create_license(user_id=1, starting_level=1)
        license_id = license_data['id']

        # Add some data
        service.promote_level(license_id)  # 1 -> 2
        service.promote_level(license_id)  # 2 -> 3
        service.add_theory_hours(license_id, hours=25)
        service.add_practice_hours(license_id, hours=40)

        # Get stats
        stats = service.get_license_stats(license_id)

        assert stats['current_level'] == 3
        assert stats['max_achieved_level'] == 3
        assert stats['theory_hours'] == 25
        assert stats['practice_hours'] == 40
        assert stats['total_hours'] == 65
        assert stats['is_expired'] == False

        print(f"   ✅ Stats retrieved: Level {stats['current_level']}, {stats['total_hours']} total hours")

        # Clean up
        db.execute(text("DELETE FROM coach_licenses WHERE user_id = 1"))
        db.commit()

    finally:
        db.close()

def test_09_full_level_progression():
    print("\n🧪 Test 9: Full level progression (1 → 8)")
    db = get_db_session()
    service = CoachService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM coach_licenses WHERE user_id = 1"))
        db.commit()

        license_data = service.create_license(user_id=1, starting_level=1)
        license_id = license_data['id']

        # Promote through all levels
        for expected_level in range(2, 9):  # 2, 3, 4, 5, 6, 7, 8
            promotion = service.promote_level(license_id)
            assert promotion['new_level'] == expected_level

        # Verify final level
        final = service.get_license_by_user(user_id=1)
        assert final['current_level'] == 8
        assert final['max_achieved_level'] == 8

        # Try promoting level 8 (should fail)
        try:
            service.promote_level(license_id)
            assert False, "Should not be able to promote level 8"
        except ValueError as e:
            assert "maximum certification level" in str(e)

        print(f"   ✅ Full progression complete: 1 → 8 (7 promotions)")

        # Clean up
        db.execute(text("DELETE FROM coach_licenses WHERE user_id = 1"))
        db.commit()

    finally:
        db.close()

if __name__ == '__main__':
    print("=" * 70)
    print("🧪 COACH SERVICE - TEST SUITE")
    print("=" * 70)

    tests = [
        test_01_create_license,
        test_02_get_license_by_user,
        test_03_add_theory_hours,
        test_04_add_practice_hours,
        test_05_check_expiry,
        test_06_renew_certification,
        test_07_promote_level,
        test_08_get_license_stats,
        test_09_full_level_progression
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"   ❌ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"📊 RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 70)

    if failed == 0:
        print("✅ ALL TESTS PASSED! 🎉")
        sys.exit(0)
    else:
        print(f"❌ {failed} TEST(S) FAILED")
        sys.exit(1)
