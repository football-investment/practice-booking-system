#!/usr/bin/env python3
"""
Test Suite for internship_credit_transactions table
Tests all constraints, triggers, and indexes
"""

import psycopg2

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'lfa_intern_system',
    'user': 'postgres',
    'password': 'postgres'
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def run_sql_file(filepath):
    conn = get_connection()
    cur = conn.cursor()
    try:
        with open(filepath, 'r') as f:
            sql = f.read()
        cur.execute(sql)
        conn.commit()
        print(f"✅ Executed: {filepath}")
    except Exception as e:
        conn.rollback()
        print(f"❌ Error executing {filepath}: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def test_01_table_exists():
    print("\n🧪 Test 1: Table exists")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'internship_credit_transactions')")
        assert cur.fetchone()[0]
        print("   ✅ Table exists")
    finally:
        cur.close()
        conn.close()

def test_02_purchase_transaction():
    print("\n🧪 Test 2: PURCHASE transaction")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM internship_licenses WHERE is_active = TRUE LIMIT 1")
        license_id = cur.fetchone()[0]
        
        cur.execute("""
            INSERT INTO internship_credit_transactions (license_id, transaction_type, amount, payment_verified, payment_reference_code, description)
            VALUES (%s, 'PURCHASE', 100, TRUE, 'PAY12345', 'Bought 100 credits')
            RETURNING id, amount
        """, (license_id,))
        tx_id, amount = cur.fetchone()
        conn.commit()
        
        assert tx_id > 0
        assert amount == 100
        print(f"   ✅ PURCHASE transaction created: id={tx_id}, amount=+100")
    finally:
        cur.close()
        conn.close()

def test_03_spent_transaction():
    print("\n🧪 Test 3: SPENT transaction")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM internship_licenses WHERE is_active = TRUE LIMIT 1")
        license_id = cur.fetchone()[0]
        
        cur.execute("SELECT id FROM internship_enrollments WHERE is_active = TRUE LIMIT 1")
        enrollment_id = cur.fetchone()[0]
        
        cur.execute("""
            INSERT INTO internship_credit_transactions (license_id, enrollment_id, transaction_type, amount, description)
            VALUES (%s, %s, 'SPENT', -50, 'Spent on semester enrollment')
            RETURNING id, amount
        """, (license_id, enrollment_id))
        tx_id, amount = cur.fetchone()
        conn.commit()
        
        assert tx_id > 0
        assert amount == -50
        print(f"   ✅ SPENT transaction created: id={tx_id}, amount=-50")
    finally:
        cur.close()
        conn.close()

def test_04_check_constraints():
    print("\n🧪 Test 4: CHECK constraints")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM internship_licenses WHERE is_active = TRUE LIMIT 1")
        license_id = cur.fetchone()[0]
        
        # Test: PURCHASE with negative amount (should fail)
        try:
            cur.execute("INSERT INTO internship_credit_transactions (license_id, transaction_type, amount) VALUES (%s, 'PURCHASE', -10)", (license_id,))
            conn.commit()
            assert False, "Should reject PURCHASE with negative amount"
        except psycopg2.errors.CheckViolation:
            conn.rollback()
            print("   ✅ PURCHASE must have positive amount")
        
        # Test: SPENT without enrollment_id (should fail)
        try:
            cur.execute("INSERT INTO internship_credit_transactions (license_id, transaction_type, amount) VALUES (%s, 'SPENT', -10)", (license_id,))
            conn.commit()
            assert False, "Should reject SPENT without enrollment_id"
        except psycopg2.errors.CheckViolation:
            conn.rollback()
            print("   ✅ SPENT requires enrollment_id")
        
    finally:
        cur.close()
        conn.close()

def test_05_cascade_delete():
    print("\n🧪 Test 5: CASCADE DELETE")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO internship_licenses (user_id, total_xp, current_level, credit_balance, expires_at, is_active)
            VALUES (2, 0, 1, 0, NOW() + INTERVAL '15 months', FALSE)
            RETURNING id
        """)
        test_license_id = cur.fetchone()[0]
        
        cur.execute("INSERT INTO internship_credit_transactions (license_id, transaction_type, amount) VALUES (%s, 'PURCHASE', 100) RETURNING id", (test_license_id,))
        tx_id = cur.fetchone()[0]
        conn.commit()
        
        cur.execute("DELETE FROM internship_licenses WHERE id = %s", (test_license_id,))
        conn.commit()
        
        cur.execute("SELECT COUNT(*) FROM internship_credit_transactions WHERE id = %s", (tx_id,))
        count = cur.fetchone()[0]
        assert count == 0
        print("   ✅ CASCADE DELETE works")
    finally:
        cur.close()
        conn.close()

def test_06_indexes():
    print("\n🧪 Test 6: Indexes exist")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'internship_credit_transactions'")
        indexes = [row[0] for row in cur.fetchall()]
        
        required = ['internship_credit_transactions_pkey', 'idx_internship_credits_license', 'idx_internship_credits_type']
        for idx in required:
            assert idx in indexes, f"Missing: {idx}"
        print(f"   ✅ All required indexes exist")
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    print("=" * 60)
    print("🧪 INTERNSHIP CREDIT TRANSACTIONS - TEST SUITE")
    print("=" * 60)
    
    sql_file = '/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system/implementation/01_database_migration/14_create_internship_credits.sql'
    run_sql_file(sql_file)
    
    tests = [test_01_table_exists, test_02_purchase_transaction, test_03_spent_transaction, test_04_check_constraints, test_05_cascade_delete, test_06_indexes]
    
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"   ❌ TEST FAILED: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 60)
    
    if failed == 0:
        print("✅ ALL TESTS PASSED! 🎉")
    else:
        print(f"❌ {failed} TEST(S) FAILED")
        exit(1)
