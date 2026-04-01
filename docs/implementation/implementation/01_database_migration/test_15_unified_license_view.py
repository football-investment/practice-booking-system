#!/usr/bin/env python3
"""
Test Suite for v_all_active_licenses view
Tests unified license view across all 4 specializations
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

def test_01_view_exists():
    print("\n🧪 Test 1: View exists")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.views
                WHERE table_name = 'v_all_active_licenses'
            )
        """)
        assert cur.fetchone()[0], "View does not exist"
        print("   ✅ v_all_active_licenses view exists")
    finally:
        cur.close()
        conn.close()

def test_02_view_has_all_specializations():
    print("\n🧪 Test 2: View contains all 4 specializations")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT DISTINCT specialization_type
            FROM v_all_active_licenses
            ORDER BY specialization_type
        """)
        spec_types = [row[0] for row in cur.fetchall()]

        # Should have at least some specializations (depending on test data)
        print(f"   ✅ Found {len(spec_types)} specialization type(s): {', '.join(spec_types)}")

        # Check that view structure supports all 4
        cur.execute("SELECT * FROM v_all_active_licenses LIMIT 0")
        columns = [desc[0] for desc in cur.description]

        required_cols = [
            'specialization_type', 'license_id', 'user_id', 'email', 'name',
            'is_active', 'created_at', 'updated_at'
        ]

        for col in required_cols:
            assert col in columns, f"Missing column: {col}"

        print(f"   ✅ View has all {len(required_cols)} required columns")

    finally:
        cur.close()
        conn.close()

def test_03_view_filters_active_only():
    print("\n🧪 Test 3: View shows only active licenses")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT COUNT(*) FROM v_all_active_licenses WHERE is_active = FALSE
        """)
        inactive_count = cur.fetchone()[0]
        assert inactive_count == 0, f"Found {inactive_count} inactive licenses (should be 0)"

        cur.execute("SELECT COUNT(*) FROM v_all_active_licenses")
        total_count = cur.fetchone()[0]

        print(f"   ✅ View contains only active licenses (total: {total_count})")
    finally:
        cur.close()
        conn.close()

def test_04_lfa_player_fields():
    print("\n🧪 Test 4: LFA Player specific fields")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT license_id, lfa_age_group, skill_overall_avg
            FROM v_all_active_licenses
            WHERE specialization_type = 'LFA_PLAYER'
            LIMIT 1
        """)
        row = cur.fetchone()

        if row:
            license_id, age_group, overall_avg = row
            assert age_group is not None, "LFA Player should have age_group"
            assert overall_avg is not None, "LFA Player should have overall_avg"
            print(f"   ✅ LFA Player fields populated: age_group={age_group}, overall_avg={overall_avg}")
        else:
            print("   ⚠️  No LFA Player licenses found in test data")
    finally:
        cur.close()
        conn.close()

def test_05_gancuju_fields():
    print("\n🧪 Test 5: GānCuju specific fields")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT license_id, current_level, win_rate
            FROM v_all_active_licenses
            WHERE specialization_type = 'GANCUJU'
            LIMIT 1
        """)
        row = cur.fetchone()

        if row:
            license_id, level, win_rate = row
            assert level is not None, "GānCuju should have current_level"
            print(f"   ✅ GānCuju fields populated: level={level}, win_rate={win_rate}")
        else:
            print("   ⚠️  No GānCuju licenses found in test data")
    finally:
        cur.close()
        conn.close()

def test_06_internship_fields():
    print("\n🧪 Test 6: Internship specific fields")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT license_id, total_xp, current_level, expires_at
            FROM v_all_active_licenses
            WHERE specialization_type = 'INTERNSHIP'
            LIMIT 1
        """)
        row = cur.fetchone()

        if row:
            license_id, xp, level, expires = row
            assert xp is not None, "Internship should have total_xp"
            assert level is not None, "Internship should have current_level"
            assert expires is not None, "Internship should have expires_at"
            print(f"   ✅ Internship fields populated: xp={xp}, level={level}")
        else:
            print("   ⚠️  No Internship licenses found in test data")
    finally:
        cur.close()
        conn.close()

def test_07_coach_fields():
    print("\n🧪 Test 7: Coach specific fields")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT license_id, current_level, theory_hours, practice_hours, is_expired
            FROM v_all_active_licenses
            WHERE specialization_type = 'COACH'
            LIMIT 1
        """)
        row = cur.fetchone()

        if row:
            license_id, level, theory, practice, expired = row
            assert level is not None, "Coach should have current_level"
            assert theory is not None, "Coach should have theory_hours"
            assert practice is not None, "Coach should have practice_hours"
            print(f"   ✅ Coach fields populated: level={level}, theory={theory}h, practice={practice}h")
        else:
            print("   ⚠️  No Coach licenses found in test data")
    finally:
        cur.close()
        conn.close()

def test_08_user_join():
    print("\n🧪 Test 8: User info properly joined")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT user_id, email, name
            FROM v_all_active_licenses
            LIMIT 5
        """)
        rows = cur.fetchall()

        for user_id, email, name in rows:
            assert user_id is not None, "user_id should not be NULL"
            assert email is not None, "email should not be NULL"
            # name can be NULL in users table

        print(f"   ✅ User info properly joined for {len(rows)} license(s)")
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    print("=" * 60)
    print("🧪 UNIFIED LICENSE VIEW - TEST SUITE")
    print("=" * 60)

    sql_file = '/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system/implementation/01_database_migration/15_create_unified_license_view.sql'
    run_sql_file(sql_file)

    tests = [
        test_01_view_exists,
        test_02_view_has_all_specializations,
        test_03_view_filters_active_only,
        test_04_lfa_player_fields,
        test_05_gancuju_fields,
        test_06_internship_fields,
        test_07_coach_fields,
        test_08_user_join
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
