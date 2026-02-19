#!/usr/bin/env python3
"""
Test Suite for lfa_player_enrollments table
Tests all constraints, triggers, and indexes
"""

import psycopg2
from datetime import datetime, timedelta

# Database connection
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
    """Execute SQL file"""
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
    """Test that lfa_player_enrollments table exists with correct columns"""
    print("\n🧪 Test 1: Table exists with correct structure")

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Check table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'lfa_player_enrollments'
            )
        """)
        assert cur.fetchone()[0], "Table does not exist"

        # Check all required columns exist
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'lfa_player_enrollments'
            ORDER BY ordinal_position
        """)
        columns = cur.fetchall()
        column_names = [col[0] for col in columns]

        required_columns = [
            'id', 'license_id', 'semester_id',
            'payment_verified', 'payment_proof_url', 'payment_reference_code',
            'is_active', 'created_at', 'updated_at'
        ]

        for col in required_columns:
            assert col in column_names, f"Missing column: {col}"

        print(f"   ✅ Table exists with {len(columns)} columns")
        print(f"   ✅ All required columns present: {', '.join(required_columns)}")

    finally:
        cur.close()
        conn.close()

def test_02_insert_enrollment():
    """Test inserting a valid enrollment"""
    print("\n🧪 Test 2: Insert valid enrollment")

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Get an existing license and semester
        cur.execute("SELECT id FROM lfa_player_licenses WHERE is_active = TRUE LIMIT 1")
        license_row = cur.fetchone()
        if not license_row:
            # Create a license for testing
            cur.execute("""
                INSERT INTO lfa_player_licenses (
                    user_id, age_group, credit_balance,
                    heading_avg, shooting_avg, crossing_avg,
                    passing_avg, dribbling_avg, ball_control_avg
                )
                VALUES (2, 'YOUTH', 100, 75.5, 80.0, 70.5, 85.0, 90.5, 88.0)
                RETURNING id
            """)
            license_id = cur.fetchone()[0]
        else:
            license_id = license_row[0]

        cur.execute("SELECT id FROM semesters WHERE is_active = TRUE LIMIT 1")
        semester_row = cur.fetchone()
        assert semester_row, "No active semester found"
        semester_id = semester_row[0]

        # Insert enrollment
        cur.execute("""
            INSERT INTO lfa_player_enrollments (
                license_id, semester_id,
                payment_verified, payment_proof_url, payment_reference_code
            )
            VALUES (%s, %s, TRUE, 'https://example.com/proof.jpg', 'PAY123456')
            RETURNING id, created_at, updated_at, is_active
        """, (license_id, semester_id))

        enrollment_id, created_at, updated_at, is_active = cur.fetchone()

        assert enrollment_id > 0
        assert is_active == True
        assert created_at is not None
        assert updated_at is not None

        conn.commit()
        print(f"   ✅ Enrollment created with id={enrollment_id}")
        print(f"   ✅ is_active defaults to TRUE")
        print(f"   ✅ Timestamps auto-populated: created_at={created_at}")

    finally:
        cur.close()
        conn.close()

def test_03_unique_active_constraint():
    """Test UNIQUE constraint: one active enrollment per license per semester"""
    print("\n🧪 Test 3: UNIQUE active enrollment constraint")

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Get existing enrollment
        cur.execute("""
            SELECT license_id, semester_id
            FROM lfa_player_enrollments
            WHERE is_active = TRUE
            LIMIT 1
        """)
        row = cur.fetchone()
        assert row, "No active enrollment found for testing"
        license_id, semester_id = row

        # Try to insert duplicate active enrollment
        try:
            cur.execute("""
                INSERT INTO lfa_player_enrollments (license_id, semester_id, is_active)
                VALUES (%s, %s, TRUE)
            """, (license_id, semester_id))
            conn.commit()
            assert False, "Should have raised UNIQUE constraint violation"
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            print(f"   ✅ UNIQUE constraint enforced: Cannot have duplicate active enrollment")

        # But inactive duplicate should be allowed
        cur.execute("""
            INSERT INTO lfa_player_enrollments (license_id, semester_id, is_active)
            VALUES (%s, %s, FALSE)
            RETURNING id
        """, (license_id, semester_id))
        inactive_id = cur.fetchone()[0]
        conn.commit()
        print(f"   ✅ Inactive duplicate allowed: id={inactive_id}")

    finally:
        cur.close()
        conn.close()

def test_04_check_constraints():
    """Test CHECK constraints on payment fields"""
    print("\n🧪 Test 4: CHECK constraints")

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Get a license and semester
        cur.execute("SELECT id FROM lfa_player_licenses WHERE is_active = TRUE LIMIT 1")
        license_id = cur.fetchone()[0]

        cur.execute("""
            SELECT id FROM semesters
            WHERE is_active = TRUE
            AND id NOT IN (
                SELECT semester_id FROM lfa_player_enrollments
                WHERE license_id = %s AND is_active = TRUE
            )
            LIMIT 1
        """, (license_id,))
        semester_id = cur.fetchone()[0]

        # Test invalid payment_proof_url (not http/https)
        try:
            cur.execute("""
                INSERT INTO lfa_player_enrollments (license_id, semester_id, payment_proof_url)
                VALUES (%s, %s, 'ftp://invalid.com/proof.jpg')
            """, (license_id, semester_id))
            conn.commit()
            assert False, "Should have rejected invalid payment_proof_url"
        except psycopg2.errors.CheckViolation:
            conn.rollback()
            print(f"   ✅ CHECK constraint enforced: payment_proof_url must be http/https")

        # Test invalid payment_reference_code (too short)
        try:
            cur.execute("""
                INSERT INTO lfa_player_enrollments (license_id, semester_id, payment_reference_code)
                VALUES (%s, %s, 'AB')
            """, (license_id, semester_id))
            conn.commit()
            assert False, "Should have rejected short payment_reference_code"
        except psycopg2.errors.CheckViolation:
            conn.rollback()
            print(f"   ✅ CHECK constraint enforced: payment_reference_code >= 3 chars")

    finally:
        cur.close()
        conn.close()

def test_05_foreign_key_cascade():
    """Test CASCADE DELETE on license and semester deletion"""
    print("\n🧪 Test 5: CASCADE DELETE")

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Create a test license (set is_active=FALSE to avoid UNIQUE constraint)
        cur.execute("""
            INSERT INTO lfa_player_licenses (
                user_id, age_group, credit_balance,
                heading_avg, shooting_avg, crossing_avg,
                passing_avg, dribbling_avg, ball_control_avg,
                is_active
            )
            VALUES (2, 'AMATEUR', 50, 60.0, 65.0, 70.0, 75.0, 80.0, 85.0, FALSE)
            RETURNING id
        """)
        test_license_id = cur.fetchone()[0]

        # Get a semester
        cur.execute("SELECT id FROM semesters WHERE is_active = TRUE LIMIT 1")
        semester_id = cur.fetchone()[0]

        # Create enrollment
        cur.execute("""
            INSERT INTO lfa_player_enrollments (license_id, semester_id)
            VALUES (%s, %s)
            RETURNING id
        """, (test_license_id, semester_id))
        enrollment_id = cur.fetchone()[0]
        conn.commit()

        # Delete license
        cur.execute("DELETE FROM lfa_player_licenses WHERE id = %s", (test_license_id,))
        conn.commit()

        # Check enrollment was cascade deleted
        cur.execute("SELECT COUNT(*) FROM lfa_player_enrollments WHERE id = %s", (enrollment_id,))
        count = cur.fetchone()[0]
        assert count == 0, "Enrollment should have been cascade deleted"

        print(f"   ✅ CASCADE DELETE works: enrollment deleted when license deleted")

    finally:
        cur.close()
        conn.close()

def test_06_updated_at_trigger():
    """Test that updated_at is automatically updated"""
    print("\n🧪 Test 6: Auto-update updated_at trigger")

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Get an enrollment
        cur.execute("""
            SELECT id, updated_at
            FROM lfa_player_enrollments
            WHERE is_active = TRUE
            LIMIT 1
        """)
        enrollment_id, old_updated_at = cur.fetchone()

        # Wait a moment
        import time
        time.sleep(0.1)

        # Update enrollment
        cur.execute("""
            UPDATE lfa_player_enrollments
            SET payment_verified = TRUE
            WHERE id = %s
            RETURNING updated_at
        """, (enrollment_id,))
        new_updated_at = cur.fetchone()[0]
        conn.commit()

        assert new_updated_at > old_updated_at, "updated_at should be auto-updated"
        print(f"   ✅ Trigger works: updated_at auto-updated from {old_updated_at} to {new_updated_at}")

    finally:
        cur.close()
        conn.close()

def test_07_indexes():
    """Test that required indexes exist"""
    print("\n🧪 Test 7: Indexes exist")

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'lfa_player_enrollments'
        """)
        indexes = [row[0] for row in cur.fetchall()]

        required_indexes = [
            'lfa_player_enrollments_pkey',  # Primary key
            'idx_lfa_player_enrollments_unique_active',
            'idx_lfa_player_enrollments_license',
            'idx_lfa_player_enrollments_semester',
            'idx_lfa_player_enrollments_verified'
        ]

        for idx in required_indexes:
            assert idx in indexes, f"Missing index: {idx}"

        print(f"   ✅ All {len(required_indexes)} required indexes exist")

    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    print("=" * 60)
    print("🧪 LFA PLAYER ENROLLMENTS TABLE - TEST SUITE")
    print("=" * 60)

    # Run SQL file first
    sql_file = '/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system/implementation/01_database_migration/05_create_lfa_player_enrollments.sql'
    run_sql_file(sql_file)

    # Run tests
    tests = [
        test_01_table_exists,
        test_02_insert_enrollment,
        test_03_unique_active_constraint,
        test_04_check_constraints,
        test_05_foreign_key_cascade,
        test_06_updated_at_trigger,
        test_07_indexes
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

    print("\n" + "=" * 60)
    print(f"📊 RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 60)

    if failed == 0:
        print("✅ ALL TESTS PASSED! 🎉")
    else:
        print(f"❌ {failed} TEST(S) FAILED")
        exit(1)
