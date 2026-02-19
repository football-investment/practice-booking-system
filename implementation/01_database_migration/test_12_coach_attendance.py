#!/usr/bin/env python3
"""
Test Suite for coach_attendance table
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
    """Test that coach_attendance table exists with correct columns"""
    print("\n🧪 Test 1: Table exists with correct structure")

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Check table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'coach_attendance'
            )
        """)
        assert cur.fetchone()[0], "Table does not exist"

        # Check all required columns exist
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'coach_attendance'
            ORDER BY ordinal_position
        """)
        columns = cur.fetchall()
        column_names = [col[0] for col in columns]

        required_columns = [
            'id', 'enrollment_id', 'session_id',
            'status', 'checked_in_at', 'checked_in_by',
            'theory_hours_earned', 'practice_hours_earned', 'notes', 'created_at', 'updated_at'
        ]

        for col in required_columns:
            assert col in column_names, f"Missing column: {col}"

        print(f"   ✅ Table exists with {len(columns)} columns")
        print(f"   ✅ All required columns present")

    finally:
        cur.close()
        conn.close()

def test_02_insert_attendance():
    """Test inserting a valid attendance record"""
    print("\n🧪 Test 2: Insert valid attendance")

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Get an existing enrollment and session
        cur.execute("SELECT id FROM coach_assignments WHERE is_active = TRUE LIMIT 1")
        enrollment_id = cur.fetchone()[0]

        cur.execute("SELECT id FROM sessions WHERE date_start > NOW() LIMIT 1")
        session_row = cur.fetchone()
        if not session_row:
            # Create a test session
            cur.execute("SELECT id FROM semesters WHERE is_active = TRUE LIMIT 1")
            semester_id_test = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO sessions (title, description, date_start, date_end, location, session_type, sport_type, semester_id)
                VALUES ('Test Session', 'Test', NOW() + INTERVAL '1 day', NOW() + INTERVAL '2 days', 'Test Location', 'hybrid', 'FOOTBALL', %s)
                RETURNING id
            """, (semester_id_test,))
            session_id = cur.fetchone()[0]
        else:
            session_id = session_row[0]

        # Insert PRESENT attendance
        cur.execute("""
            INSERT INTO coach_attendance (
                enrollment_id, session_id, status, checked_in_at, theory_hours_earned, practice_hours_earned
            )
            VALUES (%s, %s, 'PRESENT', NOW(), 2.0, 3.5)
            RETURNING id, status, theory_hours_earned, practice_hours_earned
        """, (enrollment_id, session_id))

        attendance_id, status, theory_hrs, practice_hrs = cur.fetchone()

        assert attendance_id > 0
        assert status == 'PRESENT'
        assert float(theory_hrs) == 2.0
        assert float(practice_hrs) == 3.5

        conn.commit()
        print(f"   ✅ Attendance created with id={attendance_id}")
        print(f"   ✅ Status=PRESENT, Theory=2.0hrs, Practice=3.5hrs")

    finally:
        cur.close()
        conn.close()

def test_03_unique_constraint():
    """Test UNIQUE constraint: one attendance record per enrollment per session"""
    print("\n🧪 Test 3: UNIQUE constraint")

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Get existing attendance
        cur.execute("""
            SELECT enrollment_id, session_id
            FROM coach_attendance
            LIMIT 1
        """)
        enrollment_id, session_id = cur.fetchone()

        # Try to insert duplicate
        try:
            cur.execute("""
                INSERT INTO coach_attendance (enrollment_id, session_id, status)
                VALUES (%s, %s, 'ABSENT')
            """, (enrollment_id, session_id))
            conn.commit()
            assert False, "Should have raised UNIQUE constraint violation"
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            print(f"   ✅ UNIQUE constraint enforced: Cannot have duplicate attendance")

    finally:
        cur.close()
        conn.close()

def test_04_check_constraints():
    """Test CHECK constraints"""
    print("\n🧪 Test 4: CHECK constraints")

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Get enrollment and new session
        cur.execute("SELECT id FROM coach_assignments WHERE is_active = TRUE LIMIT 1")
        enrollment_id = cur.fetchone()[0]

        cur.execute("SELECT id FROM semesters WHERE is_active = TRUE LIMIT 1")
        semester_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO sessions (title, description, date_start, date_end, location, session_type, sport_type, semester_id)
            VALUES ('Test2', 'Test', NOW() + INTERVAL '3 days', NOW() + INTERVAL '4 days', 'Test', 'hybrid', 'FOOTBALL', %s)
            RETURNING id
        """, (semester_id,))
        session_id = cur.fetchone()[0]
        conn.commit()

        # Test invalid status
        try:
            cur.execute("""
                INSERT INTO coach_attendance (enrollment_id, session_id, status)
                VALUES (%s, %s, 'INVALID')
            """, (enrollment_id, session_id))
            conn.commit()
            assert False, "Should have rejected invalid status"
        except psycopg2.errors.CheckViolation:
            conn.rollback()
            print(f"   ✅ CHECK constraint enforced: status must be PRESENT/ABSENT/LATE/EXCUSED")

        # Test PRESENT without checked_in_at (should fail)
        try:
            cur.execute("""
                INSERT INTO coach_attendance (enrollment_id, session_id, status, checked_in_at)
                VALUES (%s, %s, 'PRESENT', NULL)
            """, (enrollment_id, session_id))
            conn.commit()
            assert False, "Should have rejected PRESENT without checked_in_at"
        except psycopg2.errors.CheckViolation:
            conn.rollback()
            print(f"   ✅ CHECK constraint enforced: PRESENT requires checked_in_at")

    finally:
        cur.close()
        conn.close()

def test_05_cascade_delete():
    """Test CASCADE DELETE"""
    print("\n🧪 Test 5: CASCADE DELETE")

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Create test enrollment
        cur.execute("SELECT id FROM coach_licenses WHERE is_active = TRUE LIMIT 1")
        license_id = cur.fetchone()[0]

        cur.execute("SELECT id FROM semesters WHERE is_active = TRUE LIMIT 1")
        semester_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO coach_assignments (license_id, semester_id, is_active)
            VALUES (%s, %s, FALSE)
            RETURNING id
        """, (license_id, semester_id))
        test_enrollment_id = cur.fetchone()[0]

        cur.execute("SELECT id FROM semesters WHERE is_active = TRUE LIMIT 1")
        semester_id2 = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO sessions (title, description, date_start, date_end, location, session_type, sport_type, semester_id)
            VALUES ('Test3', 'Test', NOW() + INTERVAL '5 days', NOW() + INTERVAL '6 days', 'Test', 'hybrid', 'FOOTBALL', %s)
            RETURNING id
        """, (semester_id2,))
        test_session_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO coach_attendance (enrollment_id, session_id, status)
            VALUES (%s, %s, 'ABSENT')
            RETURNING id
        """, (test_enrollment_id, test_session_id))
        attendance_id = cur.fetchone()[0]
        conn.commit()

        # Delete enrollment
        cur.execute("DELETE FROM coach_assignments WHERE id = %s", (test_enrollment_id,))
        conn.commit()

        # Check attendance was cascade deleted
        cur.execute("SELECT COUNT(*) FROM coach_attendance WHERE id = %s", (attendance_id,))
        count = cur.fetchone()[0]
        assert count == 0, "Attendance should have been cascade deleted"

        print(f"   ✅ CASCADE DELETE works")

    finally:
        cur.close()
        conn.close()

def test_06_updated_at_trigger():
    """Test that updated_at is automatically updated"""
    print("\n🧪 Test 6: Auto-update updated_at trigger")

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Get an attendance
        cur.execute("""
            SELECT id, updated_at
            FROM coach_attendance
            LIMIT 1
        """)
        attendance_id, old_updated_at = cur.fetchone()

        # Wait a moment
        import time
        time.sleep(0.1)

        # Update attendance
        cur.execute("""
            UPDATE coach_attendance
            SET theory_hours_earned = 5.0
            WHERE id = %s
            RETURNING updated_at
        """, (attendance_id,))
        new_updated_at = cur.fetchone()[0]
        conn.commit()

        assert new_updated_at > old_updated_at, "updated_at should be auto-updated"
        print(f"   ✅ Trigger works: updated_at auto-updated")

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
            WHERE tablename = 'coach_attendance'
        """)
        indexes = [row[0] for row in cur.fetchall()]

        required_indexes = [
            'coach_attendance_pkey',
            'idx_coach_attendance_unique',
            'idx_coach_attendance_enrollment',
            'idx_coach_attendance_session',
            'idx_coach_attendance_status',
            'idx_coach_attendance_present'
        ]

        for idx in required_indexes:
            assert idx in indexes, f"Missing index: {idx}"

        print(f"   ✅ All {len(required_indexes)} required indexes exist")

    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    print("=" * 60)
    print("🧪 COACH ATTENDANCE TABLE - TEST SUITE")
    print("=" * 60)

    # Run SQL file first
    sql_file = '/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system/implementation/01_database_migration/12_create_coach_attendance.sql'
    run_sql_file(sql_file)

    # Run tests
    tests = [
        test_01_table_exists,
        test_02_insert_attendance,
        test_03_unique_constraint,
        test_04_check_constraints,
        test_05_cascade_delete,
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
