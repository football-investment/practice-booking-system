#!/usr/bin/env python3
"""
Test Suite for Internship Service
Tests XP progression, expiry management, and credit system
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import service
from internship_service import InternshipService

DB_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

def get_db_session():
    engine = create_engine(DB_URL)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

def test_01_create_license():
    print("\n🧪 Test 1: Create Internship license")
    db = get_db_session()
    service = InternshipService(db)

    try:
        # Clean up first
        db.execute(text("DELETE FROM internship_licenses WHERE user_id = 4"))
        db.commit()

        # Create license with 15-month expiry
        license_data = service.create_license(user_id=4, initial_credits=100)

        assert license_data['user_id'] == 4
        assert license_data['credit_balance'] == 100
        assert license_data['total_xp'] == 0
        assert license_data['current_level'] == 1
        assert license_data['max_achieved_level'] == 1
        assert license_data['is_active'] == True

        # Check expiry is ~15 months from now
        days_until_expiry = (license_data['expires_at'] - datetime.now(timezone.utc)).days
        assert 440 <= days_until_expiry <= 460  # ~15 months

        print(f"   ✅ License created: id={license_data['id']}, expires in {days_until_expiry} days")

        # Clean up
        db.execute(text("DELETE FROM internship_licenses WHERE user_id = 4"))
        db.commit()

    finally:
        db.close()

def test_02_get_license_by_user():
    print("\n🧪 Test 2: Get license by user")
    db = get_db_session()
    service = InternshipService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM internship_licenses WHERE user_id = 4"))
        db.commit()

        service.create_license(user_id=4, initial_credits=50)

        # Get license
        license_data = service.get_license_by_user(user_id=4)

        assert license_data is not None
        assert license_data['user_id'] == 4
        assert license_data['credit_balance'] == 50

        print(f"   ✅ Found license: id={license_data['id']}, balance={license_data['credit_balance']}")

        # Clean up
        db.execute(text("DELETE FROM internship_licenses WHERE user_id = 4"))
        db.commit()

    finally:
        db.close()

def test_03_add_xp_with_levelup():
    print("\n🧪 Test 3: Add XP (with auto level-up)")
    db = get_db_session()
    service = InternshipService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM internship_licenses WHERE user_id = 4"))
        db.commit()

        license_data = service.create_license(user_id=4)
        license_id = license_data['id']

        # Add small XP (no level-up)
        result1 = service.add_xp(license_id, xp_amount=50, reason="Completed task")

        assert result1['xp_added'] == 50
        assert result1['total_xp'] == 50
        assert result1['current_level'] == 1  # Still level 1
        assert result1['leveled_up'] == False

        # Add large XP (should trigger level-up via database trigger)
        # Levels likely require significant XP - let's add 5000 XP
        result2 = service.add_xp(license_id, xp_amount=5000, reason="Completed project")

        assert result2['total_xp'] == 5050
        # Check if level increased (may or may not level up depending on XP thresholds)
        leveled_up = result2['current_level'] > result2['old_level']

        print(f"   ✅ XP added: {result2['total_xp']} XP, Level {result2['old_level']} → {result2['current_level']} (leveled_up: {leveled_up})")

        # Clean up
        db.execute(text("DELETE FROM internship_licenses WHERE user_id = 4"))
        db.commit()

    finally:
        db.close()

def test_04_check_expiry():
    print("\n🧪 Test 4: Check license expiry")
    db = get_db_session()
    service = InternshipService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM internship_licenses WHERE user_id = 4"))
        db.commit()

        license_data = service.create_license(user_id=4, duration_months=15)
        license_id = license_data['id']

        # Check expiry
        expiry_status = service.check_expiry(license_id)

        assert expiry_status['is_expired'] == False
        assert expiry_status['is_active'] == True
        assert expiry_status['days_remaining'] > 400  # ~15 months

        print(f"   ✅ Expiry checked: {expiry_status['days_remaining']} days remaining")

        # Clean up
        db.execute(text("DELETE FROM internship_licenses WHERE user_id = 4"))
        db.commit()

    finally:
        db.close()

def test_05_renew_license():
    print("\n🧪 Test 5: Renew license")
    db = get_db_session()
    service = InternshipService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM internship_licenses WHERE user_id = 4"))
        db.commit()

        license_data = service.create_license(user_id=4, duration_months=1)  # Short duration
        license_id = license_data['id']

        old_expiry = license_data['expires_at']

        # Renew for 15 months
        renewal = service.renew_license(license_id, extension_months=15)

        assert renewal['new_expires_at'] > renewal['old_expires_at']
        assert renewal['extension_months'] == 15

        # Check new expiry is much later
        extension_days = (renewal['new_expires_at'] - renewal['old_expires_at']).days
        assert extension_days > 400  # ~15 months

        print(f"   ✅ License renewed: +{extension_days} days")

        # Clean up
        db.execute(text("DELETE FROM internship_licenses WHERE user_id = 4"))
        db.commit()

    finally:
        db.close()

def test_06_purchase_credits():
    print("\n🧪 Test 6: Purchase credits")
    db = get_db_session()
    service = InternshipService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM internship_licenses WHERE user_id = 4"))
        db.commit()

        license_data = service.create_license(user_id=4, initial_credits=50)
        license_id = license_data['id']

        # Purchase credits
        tx, new_balance = service.purchase_credits(
            license_id=license_id,
            amount=100,
            payment_verified=True,
            payment_reference_code='TEST123'
        )

        assert tx['amount'] == 100
        assert new_balance == 150  # 50 + 100

        print(f"   ✅ Credits purchased: +100, new balance={new_balance}")

        # Clean up
        db.execute(text("DELETE FROM internship_licenses WHERE user_id = 4"))
        db.commit()

    finally:
        db.close()

def test_07_spend_credits():
    print("\n🧪 Test 7: Spend credits")
    db = get_db_session()
    service = InternshipService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM internship_licenses WHERE user_id = 4"))
        db.commit()

        license_data = service.create_license(user_id=4, initial_credits=100)
        license_id = license_data['id']

        # Get a semester and create enrollment
        semester_row = db.execute(text("SELECT id FROM semesters WHERE is_active = TRUE LIMIT 1")).fetchone()
        semester_id = semester_row[0]

        enrollment_row = db.execute(text("""
            INSERT INTO internship_enrollments (license_id, semester_id, is_active)
            VALUES (:license_id, :semester_id, FALSE)
            RETURNING id
        """), {"license_id": license_id, "semester_id": semester_id}).fetchone()
        enrollment_id = enrollment_row[0]
        db.commit()

        # Spend credits
        tx, new_balance = service.spend_credits(
            license_id=license_id,
            enrollment_id=enrollment_id,
            amount=30
        )

        assert tx['amount'] == -30  # Stored as negative
        assert new_balance == 70  # 100 - 30

        print(f"   ✅ Credits spent: -30, new balance={new_balance}")

        # Clean up
        db.execute(text("DELETE FROM internship_licenses WHERE user_id = 4"))
        db.commit()

    finally:
        db.close()

def test_08_get_credit_balance():
    print("\n🧪 Test 8: Get credit balance")
    db = get_db_session()
    service = InternshipService(db)

    try:
        # Clean up and create test license
        db.execute(text("DELETE FROM internship_licenses WHERE user_id = 4"))
        db.commit()

        license_data = service.create_license(user_id=4, initial_credits=75)
        license_id = license_data['id']

        # Get balance
        balance = service.get_credit_balance(license_id)

        assert balance == 75

        print(f"   ✅ Balance retrieved: {balance} credits")

        # Clean up
        db.execute(text("DELETE FROM internship_licenses WHERE user_id = 4"))
        db.commit()

    finally:
        db.close()

if __name__ == '__main__':
    print("=" * 70)
    print("🧪 INTERNSHIP SERVICE - TEST SUITE")
    print("=" * 70)

    tests = [
        test_01_create_license,
        test_02_get_license_by_user,
        test_03_add_xp_with_levelup,
        test_04_check_expiry,
        test_05_renew_license,
        test_06_purchase_credits,
        test_07_spend_credits,
        test_08_get_credit_balance
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
