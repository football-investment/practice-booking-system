#!/usr/bin/env python3
"""
Test Suite for LFA Player Service
Tests all business logic methods
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import service
from lfa_player_service import LFAPlayerService

DB_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

def get_db_session():
    engine = create_engine(DB_URL)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

def test_01_create_license():
    print("\n🧪 Test 1: Create LFA Player license")
    db = get_db_session()
    service = LFAPlayerService(db)

    try:
        # Clean up first
        db.execute(text("DELETE FROM lfa_player_licenses WHERE user_id = 2"))
        db.commit()

        # Create license
        license_data = service.create_license(
            user_id=2,
            age_group='YOUTH',
            initial_credits=100,
            initial_skills={
                'heading_avg': 75.0,
                'shooting_avg': 80.0,
                'crossing_avg': 70.0,
                'passing_avg': 85.0,
                'dribbling_avg': 90.0,
                'ball_control_avg': 88.0
            }
        )

        assert license_data['user_id'] == 2
        assert license_data['age_group'] == 'YOUTH'
        assert license_data['credit_balance'] == 100
        assert abs(license_data['overall_avg'] - 81.33) < 0.1  # Average of 6 skills

        print(f"   ✅ License created: id={license_data['id']}, overall_avg={license_data['overall_avg']:.2f}")

        # Clean up
        db.execute(text("DELETE FROM lfa_player_licenses WHERE user_id = 2"))
        db.commit()

    finally:
        db.close()

def test_02_get_license_by_user():
    print("\n🧪 Test 2: Get license by user")
    db = get_db_session()
    service = LFAPlayerService(db)

    try:
        # Get existing license (from integration tests)
        license_data = service.get_license_by_user(user_id=2)

        if license_data:
            assert 'id' in license_data
            assert 'overall_avg' in license_data
            assert 'skills' in license_data
            print(f"   ✅ Found license: id={license_data['id']}, overall={license_data['overall_avg']:.2f}")
        else:
            print("   ⚠️  No active license found for user_id=2")

    finally:
        db.close()

def test_03_update_skill():
    print("\n🧪 Test 3: Update skill average")
    db = get_db_session()
    service = LFAPlayerService(db)

    try:
        # Clean up first
        db.execute(text("DELETE FROM lfa_player_licenses WHERE user_id = 2"))
        db.commit()

        # Create test license
        license_data = service.create_license(
            user_id=2,
            age_group='AMATEUR',
            initial_skills={'heading_avg': 50.0, 'shooting_avg': 50.0}
        )
        license_id = license_data['id']

        # Update shooting skill
        updated = service.update_skill_avg(license_id, 'shooting', 90.0)

        assert updated['new_avg'] == 90.0
        # overall_avg should auto-update: (50+90+0+0+0+0)/6 = 23.33
        assert abs(updated['overall_avg'] - 23.33) < 0.1

        print(f"   ✅ Skill updated: shooting=90.0, new_overall={updated['overall_avg']:.2f}")

        # Clean up
        db.execute(text("DELETE FROM lfa_player_licenses WHERE user_id = 2"))
        db.commit()

    finally:
        db.close()

def test_04_purchase_credits():
    print("\n🧪 Test 4: Purchase credits")
    db = get_db_session()
    service = LFAPlayerService(db)

    try:
        # Clean up first
        db.execute(text("DELETE FROM lfa_player_licenses WHERE user_id = 2"))
        db.commit()

        # Create test license
        license_data = service.create_license(user_id=2, age_group='PRO', initial_credits=50)
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

        print(f"   ✅ Credits purchased: +100, new_balance={new_balance}")

        # Clean up
        db.execute(text("DELETE FROM lfa_player_licenses WHERE user_id = 2"))
        db.commit()

    finally:
        db.close()

def test_05_spend_credits():
    print("\n🧪 Test 5: Spend credits")
    db = get_db_session()
    service = LFAPlayerService(db)

    try:
        # Clean up first
        db.execute(text("DELETE FROM lfa_player_licenses WHERE user_id = 2"))
        db.commit()

        # Create test license and enrollment
        license_data = service.create_license(user_id=2, age_group='YOUTH', initial_credits=100)
        license_id = license_data['id']

        # Get a semester
        semester_row = db.execute(text("SELECT id FROM semesters WHERE is_active = TRUE LIMIT 1")).fetchone()
        semester_id = semester_row[0]

        # Create enrollment
        enrollment_row = db.execute(text("""
            INSERT INTO lfa_player_enrollments (license_id, semester_id, is_active)
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

        print(f"   ✅ Credits spent: -30, new_balance={new_balance}")

        # Clean up
        db.execute(text("DELETE FROM lfa_player_licenses WHERE user_id = 2"))
        db.commit()

    finally:
        db.close()

def test_06_get_balance():
    print("\n🧪 Test 6: Get credit balance")
    db = get_db_session()
    service = LFAPlayerService(db)

    try:
        # Clean up first
        db.execute(text("DELETE FROM lfa_player_licenses WHERE user_id = 2"))
        db.commit()

        # Create test license
        license_data = service.create_license(user_id=2, age_group='AMATEUR', initial_credits=75)
        license_id = license_data['id']

        # Get balance
        balance = service.get_credit_balance(license_id)

        assert balance == 75

        print(f"   ✅ Balance retrieved: {balance}")

        # Clean up
        db.execute(text("DELETE FROM lfa_player_licenses WHERE user_id = 2"))
        db.commit()

    finally:
        db.close()

def test_07_transaction_history():
    print("\n🧪 Test 7: Get transaction history")
    db = get_db_session()
    service = LFAPlayerService(db)

    try:
        # Clean up first
        db.execute(text("DELETE FROM lfa_player_licenses WHERE user_id = 2"))
        db.commit()

        # Create test license
        license_data = service.create_license(user_id=2, age_group='PRO', initial_credits=100)
        license_id = license_data['id']

        # Make some transactions
        service.purchase_credits(license_id, 50, payment_verified=True)
        service.purchase_credits(license_id, 25, payment_verified=False)

        # Get history
        history = service.get_transaction_history(license_id, limit=10)

        assert len(history) == 2
        assert history[0]['transaction_type'] == 'PURCHASE'  # Newest first
        assert history[0]['amount'] == 25

        print(f"   ✅ Transaction history retrieved: {len(history)} transactions")

        # Clean up
        db.execute(text("DELETE FROM lfa_player_licenses WHERE user_id = 2"))
        db.commit()

    finally:
        db.close()

if __name__ == '__main__':
    print("=" * 70)
    print("🧪 LFA PLAYER SERVICE - TEST SUITE")
    print("=" * 70)

    tests = [
        test_01_create_license,
        test_02_get_license_by_user,
        test_03_update_skill,
        test_04_purchase_credits,
        test_05_spend_credits,
        test_06_get_balance,
        test_07_transaction_history
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
