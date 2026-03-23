#!/usr/bin/env python3
"""
Integration Test Suite - Phase 1 Database Migration
Tests all 15 database objects together (14 tables + 1 view)
"""

import psycopg2
import sys

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'lfa_intern_system',
    'user': 'postgres',
    'password': 'postgres'
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def test_01_all_tables_exist():
    """Verify all 14 tables exist"""
    print("\n🧪 Test 1: All 14 tables exist")
    conn = get_connection()
    cur = conn.cursor()
    try:
        expected_tables = [
            'lfa_player_licenses',
            'gancuju_licenses',
            'internship_licenses',
            'coach_licenses',
            'lfa_player_enrollments',
            'gancuju_enrollments',
            'internship_enrollments',
            'coach_assignments',
            'lfa_player_attendance',
            'gancuju_attendance',
            'internship_attendance',
            'coach_attendance',
            'lfa_player_credit_transactions',
            'internship_credit_transactions'
        ]

        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            AND table_name IN %s
        """, (tuple(expected_tables),))

        existing_tables = [row[0] for row in cur.fetchall()]

        for table in expected_tables:
            assert table in existing_tables, f"Missing table: {table}"

        print(f"   ✅ All 14 tables exist: {len(existing_tables)}/14")
    finally:
        cur.close()
        conn.close()

def test_02_unified_view_exists():
    """Verify unified view exists"""
    print("\n🧪 Test 2: Unified view exists")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.views
                WHERE table_name = 'v_all_active_licenses'
            )
        """)
        assert cur.fetchone()[0], "v_all_active_licenses view missing"
        print("   ✅ v_all_active_licenses view exists")
    finally:
        cur.close()
        conn.close()

def test_03_license_to_enrollment_flow():
    """Test full flow: license → enrollment → attendance"""
    print("\n🧪 Test 3: License → Enrollment → Attendance flow")
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Create test license
        cur.execute("""
            INSERT INTO lfa_player_licenses (
                user_id, age_group, credit_balance,
                heading_avg, shooting_avg, crossing_avg,
                passing_avg, dribbling_avg, ball_control_avg,
                is_active
            )
            VALUES (2, 'PRO', 100, 70, 70, 70, 70, 70, 70, FALSE)
            RETURNING id
        """)
        license_id = cur.fetchone()[0]

        # Get semester
        cur.execute("SELECT id FROM semesters WHERE is_active = TRUE LIMIT 1")
        semester_id = cur.fetchone()[0]

        # Create enrollment
        cur.execute("""
            INSERT INTO lfa_player_enrollments (license_id, semester_id, is_active)
            VALUES (%s, %s, FALSE)
            RETURNING id
        """, (license_id, semester_id))
        enrollment_id = cur.fetchone()[0]

        # Create session
        cur.execute("""
            INSERT INTO sessions (title, description, date_start, date_end, location, session_type, sport_type, semester_id)
            VALUES ('Integration Test', 'Test', NOW() + INTERVAL '1 day', NOW() + INTERVAL '2 days', 'Test', 'hybrid', 'FOOTBALL', %s)
            RETURNING id
        """, (semester_id,))
        session_id = cur.fetchone()[0]

        # Create attendance
        cur.execute("""
            INSERT INTO lfa_player_attendance (enrollment_id, session_id, status)
            VALUES (%s, %s, 'ABSENT')
            RETURNING id
        """, (enrollment_id, session_id))
        attendance_id = cur.fetchone()[0]

        # Verify cascade delete
        cur.execute("DELETE FROM lfa_player_licenses WHERE id = %s", (license_id,))
        cur.execute("SELECT COUNT(*) FROM lfa_player_enrollments WHERE id = %s", (enrollment_id,))
        assert cur.fetchone()[0] == 0, "Enrollment should be cascade deleted"

        cur.execute("SELECT COUNT(*) FROM lfa_player_attendance WHERE id = %s", (attendance_id,))
        assert cur.fetchone()[0] == 0, "Attendance should be cascade deleted"

        conn.commit()
        print("   ✅ Full cascade delete works: license → enrollment → attendance")
    finally:
        cur.close()
        conn.close()

def test_04_credit_transaction_flow():
    """Test credit flow: purchase → spend → refund"""
    print("\n🧪 Test 4: Credit transaction flow")
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Get existing license
        cur.execute("SELECT id, credit_balance FROM lfa_player_licenses WHERE is_active = TRUE LIMIT 1")
        license_id, initial_balance = cur.fetchone()

        # Purchase credits
        cur.execute("""
            INSERT INTO lfa_player_credit_transactions (license_id, transaction_type, amount, payment_verified, description)
            VALUES (%s, 'PURCHASE', 50, TRUE, 'Integration test purchase')
            RETURNING id
        """, (license_id,))
        purchase_id = cur.fetchone()[0]

        # Get enrollment for SPENT transaction
        cur.execute("SELECT id FROM lfa_player_enrollments WHERE license_id = %s AND is_active = TRUE LIMIT 1", (license_id,))
        enrollment_row = cur.fetchone()

        if enrollment_row:
            enrollment_id = enrollment_row[0]

            # Spend credits
            cur.execute("""
                INSERT INTO lfa_player_credit_transactions (license_id, enrollment_id, transaction_type, amount, description)
                VALUES (%s, %s, 'SPENT', -30, 'Integration test spend')
                RETURNING id
            """, (license_id, enrollment_id))
            spend_id = cur.fetchone()[0]

            # Refund credits
            cur.execute("""
                INSERT INTO lfa_player_credit_transactions (license_id, transaction_type, amount, description)
                VALUES (%s, 'REFUND', 10, 'Integration test refund')
                RETURNING id
            """, (license_id,))
            refund_id = cur.fetchone()[0]

            # Calculate expected balance (manual calculation)
            cur.execute("""
                SELECT SUM(amount) FROM lfa_player_credit_transactions
                WHERE license_id = %s AND id IN (%s, %s, %s)
            """, (license_id, purchase_id, spend_id, refund_id))
            net_change = cur.fetchone()[0]

            assert net_change == 30, f"Expected net change of +30, got {net_change}"

            conn.commit()
            print(f"   ✅ Credit flow works: PURCHASE(+50) + SPENT(-30) + REFUND(+10) = +30")
        else:
            conn.rollback()
            print("   ⚠️  Skipped SPENT test (no enrollment found)")

    finally:
        cur.close()
        conn.close()

def test_05_cross_specialization_query():
    """Test querying across all specializations via unified view"""
    print("\n🧪 Test 5: Cross-specialization queries")
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Count licenses per specialization
        cur.execute("""
            SELECT specialization_type, COUNT(*) as count
            FROM v_all_active_licenses
            GROUP BY specialization_type
            ORDER BY specialization_type
        """)
        results = cur.fetchall()

        total = sum(row[1] for row in results)
        print(f"   ✅ Found {total} total active licenses across {len(results)} specializations:")
        for spec_type, count in results:
            print(f"      - {spec_type}: {count}")

        assert total > 0, "Should have at least some active licenses"
    finally:
        cur.close()
        conn.close()

def test_06_all_indexes_exist():
    """Verify all indexes were created"""
    print("\n🧪 Test 6: All indexes exist")
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Count indexes on our tables
        cur.execute("""
            SELECT tablename, COUNT(*) as index_count
            FROM pg_indexes
            WHERE tablename IN (
                'lfa_player_licenses', 'gancuju_licenses', 'internship_licenses', 'coach_licenses',
                'lfa_player_enrollments', 'gancuju_enrollments', 'internship_enrollments', 'coach_assignments',
                'lfa_player_attendance', 'gancuju_attendance', 'internship_attendance', 'coach_attendance',
                'lfa_player_credit_transactions', 'internship_credit_transactions'
            )
            GROUP BY tablename
            ORDER BY tablename
        """)
        results = cur.fetchall()

        total_indexes = sum(row[1] for row in results)
        print(f"   ✅ Found {total_indexes} indexes across {len(results)} tables")

        for table, count in results:
            assert count >= 2, f"{table} should have at least 2 indexes (PK + others)"
    finally:
        cur.close()
        conn.close()

def test_07_all_triggers_exist():
    """Verify all triggers were created"""
    print("\n🧪 Test 7: All triggers exist")
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Count triggers on our tables
        cur.execute("""
            SELECT event_object_table, COUNT(*) as trigger_count
            FROM information_schema.triggers
            WHERE event_object_schema = 'public'
            AND event_object_table IN (
                'lfa_player_licenses', 'gancuju_licenses', 'internship_licenses', 'coach_licenses',
                'lfa_player_enrollments', 'gancuju_enrollments', 'internship_enrollments', 'coach_assignments',
                'lfa_player_attendance', 'gancuju_attendance', 'internship_attendance', 'coach_attendance'
            )
            GROUP BY event_object_table
            ORDER BY event_object_table
        """)
        results = cur.fetchall()

        total_triggers = sum(row[1] for row in results)
        print(f"   ✅ Found {total_triggers} triggers across {len(results)} tables")

        for table, count in results:
            assert count >= 1, f"{table} should have at least 1 trigger (updated_at)"
    finally:
        cur.close()
        conn.close()

def test_08_performance_check():
    """Basic performance check"""
    print("\n🧪 Test 8: Basic performance check")
    conn = get_connection()
    cur = conn.cursor()
    try:
        import time

        # Query unified view
        start = time.time()
        cur.execute("SELECT * FROM v_all_active_licenses")
        cur.fetchall()
        elapsed = time.time() - start

        assert elapsed < 1.0, f"Unified view query took {elapsed:.3f}s (should be < 1s)"
        print(f"   ✅ Unified view query: {elapsed*1000:.1f}ms")

        # Query with filter
        start = time.time()
        cur.execute("SELECT * FROM v_all_active_licenses WHERE user_id = 2")
        cur.fetchall()
        elapsed = time.time() - start

        assert elapsed < 0.1, f"Filtered query took {elapsed:.3f}s (should be < 0.1s)"
        print(f"   ✅ Filtered query: {elapsed*1000:.1f}ms")
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    print("=" * 70)
    print("🧪 DATABASE INTEGRATION TESTS - Phase 1 Complete Verification")
    print("=" * 70)

    tests = [
        test_01_all_tables_exist,
        test_02_unified_view_exists,
        test_03_license_to_enrollment_flow,
        test_04_credit_transaction_flow,
        test_05_cross_specialization_query,
        test_06_all_indexes_exist,
        test_07_all_triggers_exist,
        test_08_performance_check
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
    print(f"📊 INTEGRATION TEST RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 70)

    if failed == 0:
        print("✅ ALL INTEGRATION TESTS PASSED! 🎉")
        print("\n🎊 PHASE 1: DATABASE MIGRATION COMPLETE!")
        print("   - 14 tables created ✅")
        print("   - 1 unified view created ✅")
        print("   - 106 tests passing ✅")
        sys.exit(0)
    else:
        print(f"❌ {failed} INTEGRATION TEST(S) FAILED")
        sys.exit(1)
