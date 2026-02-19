#!/usr/bin/env python3
"""
Test Suite for GānCuju Service
Tests level progression system (1-8) and competition tracking
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import service
from gancuju_service import GanCujuService

DB_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

def get_db_session():
    engine = create_engine(DB_URL)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

def test_01_create_license():
    print("\n🧪 Test 1: Create GānCuju license")
    db = get_db_session()
    service = GanCujuService(db)

    try:
        # Clean up first
        db.execute(text("DELETE FROM gancuju_licenses WHERE user_id = 3"))
        db.commit()

        # Create license starting at level 1
        license_data = service.create_license(user_id=3, starting_level=1)

        assert license_data['user_id'] == 3
        assert license_data['current_level'] == 1
        assert license_data['max_achieved_level'] == 1
        assert license_data['competitions_entered'] == 0
        assert license_data['competitions_won'] == 0
        assert license_data['teaching_hours'] == 0
        assert license_data['win_rate'] == 0.0

        print(f"   ✅ License created: id={license_data['id']}, level={license_data['current_level']}")

        # Clean up
        db.execute(text("DELETE FROM gancuju_licenses WHERE user_id = 3"))
        db.commit()

    finally:
        db.close()

def test_02_get_license_by_user():
    print("\n🧪 Test 2: Get license by user")
    db = get_db_session()
    service = GanCujuService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM gancuju_licenses WHERE user_id = 3"))
        db.commit()

        service.create_license(user_id=3, starting_level=2)

        # Get license
        license_data = service.get_license_by_user(user_id=3)

        assert license_data is not None
        assert license_data['user_id'] == 3
        assert license_data['current_level'] == 2

        print(f"   ✅ Found license: id={license_data['id']}, level={license_data['current_level']}")

        # Clean up
        db.execute(text("DELETE FROM gancuju_licenses WHERE user_id = 3"))
        db.commit()

    finally:
        db.close()

def test_03_promote_level():
    print("\n🧪 Test 3: Promote level")
    db = get_db_session()
    service = GanCujuService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM gancuju_licenses WHERE user_id = 3"))
        db.commit()

        license_data = service.create_license(user_id=3, starting_level=1)
        license_id = license_data['id']

        # Promote from 1 to 2
        promotion = service.promote_level(license_id, reason="Test promotion")

        assert promotion['old_level'] == 1
        assert promotion['new_level'] == 2

        # Verify update
        updated = service.get_license_by_user(user_id=3)
        assert updated['current_level'] == 2
        assert updated['max_achieved_level'] == 2  # Should update via trigger

        print(f"   ✅ Level promoted: {promotion['old_level']} → {promotion['new_level']}")

        # Clean up
        db.execute(text("DELETE FROM gancuju_licenses WHERE user_id = 3"))
        db.commit()

    finally:
        db.close()

def test_04_demote_level():
    print("\n🧪 Test 4: Demote level")
    db = get_db_session()
    service = GanCujuService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM gancuju_licenses WHERE user_id = 3"))
        db.commit()

        license_data = service.create_license(user_id=3, starting_level=5)
        license_id = license_data['id']

        # Demote from 5 to 4
        demotion = service.demote_level(license_id, reason="Test demotion")

        assert demotion['old_level'] == 5
        assert demotion['new_level'] == 4

        # Verify update
        updated = service.get_license_by_user(user_id=3)
        assert updated['current_level'] == 4

        print(f"   ✅ Level demoted: {demotion['old_level']} → {demotion['new_level']}")

        # Clean up
        db.execute(text("DELETE FROM gancuju_licenses WHERE user_id = 3"))
        db.commit()

    finally:
        db.close()

def test_05_record_competitions():
    print("\n🧪 Test 5: Record competition results")
    db = get_db_session()
    service = GanCujuService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM gancuju_licenses WHERE user_id = 3"))
        db.commit()

        license_data = service.create_license(user_id=3, starting_level=3)
        license_id = license_data['id']

        # Record 3 wins and 2 losses (5 total)
        service.record_competition(license_id, won=True, competition_name="Tournament 1")
        service.record_competition(license_id, won=True, competition_name="Tournament 2")
        service.record_competition(license_id, won=False, competition_name="Tournament 3")
        service.record_competition(license_id, won=True, competition_name="Tournament 4")
        result = service.record_competition(license_id, won=False, competition_name="Tournament 5")

        assert result['competitions_won'] == 3
        assert result['competitions_entered'] == 5
        assert result['win_rate'] == 60.0  # 3/5 = 60%

        print(f"   ✅ Competitions recorded: {result['competitions_won']}/{result['competitions_entered']} (win rate: {result['win_rate']}%)")

        # Clean up
        db.execute(text("DELETE FROM gancuju_licenses WHERE user_id = 3"))
        db.commit()

    finally:
        db.close()

def test_06_record_teaching_hours():
    print("\n🧪 Test 6: Record teaching hours")
    db = get_db_session()
    service = GanCujuService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM gancuju_licenses WHERE user_id = 3"))
        db.commit()

        license_data = service.create_license(user_id=3, starting_level=6)
        license_id = license_data['id']

        # Record teaching hours (integers)
        service.record_teaching_hours(license_id, hours=5, description="Beginner class")
        service.record_teaching_hours(license_id, hours=3, description="Advanced class")
        result = service.record_teaching_hours(license_id, hours=2, description="Private lesson")

        assert result['total_teaching_hours'] == 10  # 5 + 3 + 2

        print(f"   ✅ Teaching hours recorded: {result['total_teaching_hours']} hours")

        # Clean up
        db.execute(text("DELETE FROM gancuju_licenses WHERE user_id = 3"))
        db.commit()

    finally:
        db.close()

def test_07_license_stats():
    print("\n🧪 Test 7: Get license statistics")
    db = get_db_session()
    service = GanCujuService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM gancuju_licenses WHERE user_id = 3"))
        db.commit()

        license_data = service.create_license(user_id=3, starting_level=1)
        license_id = license_data['id']

        # Add some data
        service.promote_level(license_id)  # 1 -> 2
        service.promote_level(license_id)  # 2 -> 3
        service.record_competition(license_id, won=True)
        service.record_competition(license_id, won=True)
        service.record_competition(license_id, won=False)
        service.record_teaching_hours(license_id, hours=5)

        # Get stats
        stats = service.get_license_stats(license_id)

        assert stats['current_level'] == 3
        assert stats['max_achieved_level'] == 3
        assert stats['competitions_entered'] == 3
        assert stats['competitions_won'] == 2
        assert abs(float(stats['win_rate']) - 66.67) < 0.1
        assert stats['teaching_hours'] == 5

        print(f"   ✅ Stats retrieved: Level {stats['current_level']}, Win Rate {stats['win_rate']:.1f}%")

        # Clean up
        db.execute(text("DELETE FROM gancuju_licenses WHERE user_id = 3"))
        db.commit()

    finally:
        db.close()

def test_08_full_level_progression():
    print("\n🧪 Test 8: Full level progression (1 → 8)")
    db = get_db_session()
    service = GanCujuService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM gancuju_licenses WHERE user_id = 3"))
        db.commit()

        license_data = service.create_license(user_id=3, starting_level=1)
        license_id = license_data['id']

        # Promote through all levels
        for expected_level in range(2, 9):  # 2, 3, 4, 5, 6, 7, 8
            promotion = service.promote_level(license_id)
            assert promotion['new_level'] == expected_level

        # Verify final level
        final = service.get_license_by_user(user_id=3)
        assert final['current_level'] == 8
        assert final['max_achieved_level'] == 8

        # Try promoting level 8 (should fail)
        try:
            service.promote_level(license_id)
            assert False, "Should not be able to promote level 8"
        except ValueError as e:
            assert "maximum level" in str(e)

        print(f"   ✅ Full progression complete: 1 → 8 (7 promotions)")

        # Clean up
        db.execute(text("DELETE FROM gancuju_licenses WHERE user_id = 3"))
        db.commit()

    finally:
        db.close()

if __name__ == '__main__':
    print("=" * 70)
    print("🧪 GĀNCUJU SERVICE - TEST SUITE")
    print("=" * 70)

    tests = [
        test_01_create_license,
        test_02_get_license_by_user,
        test_03_promote_level,
        test_04_demote_level,
        test_05_record_competitions,
        test_06_record_teaching_hours,
        test_07_license_stats,
        test_08_full_level_progression
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
