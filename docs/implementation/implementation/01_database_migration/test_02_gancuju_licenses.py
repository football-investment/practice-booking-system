"""
Test Suite for gancuju_licenses table
Tests:
1. Table exists
2. Can insert valid license
3. Auto-computed win_rate works correctly
4. CHECK constraints work (level ranges, competitions logic)
5. UNIQUE constraint works (one active license per user)
6. max_achieved_level auto-updates
7. Trigger updates updated_at
"""

import os
import psycopg2
from datetime import datetime

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def test_01_table_exists():
    """Test that gancuju_licenses table exists"""
    print("✓ Test 1: Table exists...")
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'gancuju_licenses'
        );
    """)

    exists = cur.fetchone()[0]
    assert exists, "❌ Table gancuju_licenses does not exist"

    cur.close()
    conn.close()
    print("  ✅ PASS: Table exists")

def test_02_insert_valid_license():
    """Test inserting a valid GānCuju license"""
    print("✓ Test 2: Insert valid license...")
    conn = get_connection()
    cur = conn.cursor()

    # Cleanup any existing licenses for user_id=2 (from previous tests)
    cur.execute("DELETE FROM gancuju_licenses WHERE user_id = 2")
    conn.commit()

    # Insert license with competition data
    cur.execute("""
        INSERT INTO gancuju_licenses
        (user_id, current_level, competitions_entered, competitions_won, teaching_hours)
        VALUES (2, 3, 10, 7, 25)
        RETURNING id, win_rate;
    """)

    license_id, win_rate = cur.fetchone()
    assert license_id is not None, "❌ Failed to insert license"

    conn.commit()
    cur.close()
    conn.close()
    print(f"  ✅ PASS: License created with ID={license_id}, win_rate={win_rate}%")
    return license_id

def test_03_auto_computed_win_rate():
    """Test that win_rate is auto-computed correctly"""
    print("✓ Test 3: Auto-computed win_rate...")
    conn = get_connection()
    cur = conn.cursor()

    # Test 1: Normal win rate calculation
    cur.execute("""
        SELECT competitions_entered, competitions_won, win_rate
        FROM gancuju_licenses
        WHERE user_id = 2
        LIMIT 1;
    """)

    entered, won, win_rate = cur.fetchone()
    expected_rate = (float(won) / float(entered) * 100) if entered > 0 else 0

    # Allow 0.01 tolerance for floating point
    assert abs(float(win_rate) - expected_rate) < 0.01, f"❌ win_rate mismatch: expected {expected_rate}, got {win_rate}"
    print(f"  ✅ PASS: win_rate correctly computed: {win_rate:.2f}%")

    # Test 2: Zero competitions case
    cur.execute("""
        INSERT INTO gancuju_licenses (user_id, competitions_entered, competitions_won)
        VALUES (3, 0, 0)
        RETURNING win_rate;
    """)
    zero_rate = cur.fetchone()[0]
    assert float(zero_rate) == 0.0, f"❌ win_rate should be 0 when no competitions: got {zero_rate}"
    print(f"  ✅ PASS: win_rate is 0% when no competitions")

    conn.commit()

    # Cleanup test license
    cur.execute("DELETE FROM gancuju_licenses WHERE user_id = 3")
    conn.commit()

    cur.close()
    conn.close()

def test_04_check_constraints():
    """Test CHECK constraints (level ranges, competitions logic)"""
    print("✓ Test 4: CHECK constraints...")
    conn = get_connection()
    cur = conn.cursor()

    # Test 1: Invalid current_level (0)
    try:
        cur.execute("""
            INSERT INTO gancuju_licenses (user_id, current_level)
            VALUES (4, 0);
        """)
        conn.commit()
        assert False, "❌ Should have failed: current_level = 0"
    except psycopg2.IntegrityError:
        conn.rollback()
        print("  ✅ PASS: current_level CHECK constraint works (1-8)")

    # Test 2: Invalid current_level (9)
    try:
        cur.execute("""
            INSERT INTO gancuju_licenses (user_id, current_level)
            VALUES (4, 9);
        """)
        conn.commit()
        assert False, "❌ Should have failed: current_level = 9"
    except psycopg2.IntegrityError:
        conn.rollback()
        print("  ✅ PASS: current_level max=8 constraint works")

    # Test 3: competitions_won > competitions_entered
    try:
        cur.execute("""
            INSERT INTO gancuju_licenses (user_id, competitions_entered, competitions_won)
            VALUES (4, 5, 10);
        """)
        conn.commit()
        assert False, "❌ Should have failed: won > entered"
    except psycopg2.IntegrityError:
        conn.rollback()
        print("  ✅ PASS: competitions logic CHECK constraint works")

    # Test 4: Negative teaching_hours
    try:
        cur.execute("""
            INSERT INTO gancuju_licenses (user_id, teaching_hours)
            VALUES (4, -10);
        """)
        conn.commit()
        assert False, "❌ Should have failed: negative teaching_hours"
    except psycopg2.IntegrityError:
        conn.rollback()
        print("  ✅ PASS: teaching_hours >= 0 constraint works")

    cur.close()
    conn.close()

def test_05_unique_active_license():
    """Test UNIQUE constraint: one active license per user"""
    print("✓ Test 5: UNIQUE active license per user...")
    conn = get_connection()
    cur = conn.cursor()

    # Try to insert second active license for user_id=2
    try:
        cur.execute("""
            INSERT INTO gancuju_licenses (user_id, is_active)
            VALUES (2, TRUE);
        """)
        conn.commit()
        assert False, "❌ Should have failed: duplicate active license"
    except psycopg2.IntegrityError:
        conn.rollback()
        print("  ✅ PASS: UNIQUE active license constraint works")

    # But can insert inactive license
    cur.execute("""
        INSERT INTO gancuju_licenses (user_id, is_active)
        VALUES (2, FALSE)
        RETURNING id;
    """)
    license_id = cur.fetchone()[0]
    conn.commit()
    print(f"  ✅ PASS: Can insert inactive license (ID={license_id})")

    # Cleanup
    cur.execute("DELETE FROM gancuju_licenses WHERE id = %s", (license_id,))
    conn.commit()

    cur.close()
    conn.close()

def test_06_max_achieved_level_trigger():
    """Test max_achieved_level auto-updates when current_level increases"""
    print("✓ Test 6: max_achieved_level trigger...")
    conn = get_connection()
    cur = conn.cursor()

    # Get current levels
    cur.execute("""
        SELECT current_level, max_achieved_level
        FROM gancuju_licenses
        WHERE user_id = 2;
    """)
    old_current, old_max = cur.fetchone()
    print(f"  Before: current={old_current}, max={old_max}")

    # Promote to higher level
    new_level = old_current + 1 if old_current < 8 else old_current
    cur.execute("""
        UPDATE gancuju_licenses
        SET current_level = %s
        WHERE user_id = 2
        RETURNING current_level, max_achieved_level;
    """, (new_level,))
    new_current, new_max = cur.fetchone()
    conn.commit()

    print(f"  After: current={new_current}, max={new_max}")

    # max should be >= current always
    assert new_max >= new_current, f"❌ max_achieved_level ({new_max}) should be >= current_level ({new_current})"
    print(f"  ✅ PASS: max_achieved_level auto-updates correctly")

    # Test demotion (current_level goes down, but max stays)
    if new_current > 1:
        demoted_level = new_current - 1
        cur.execute("""
            UPDATE gancuju_licenses
            SET current_level = %s
            WHERE user_id = 2
            RETURNING current_level, max_achieved_level;
        """, (demoted_level,))
        demoted_current, demoted_max = cur.fetchone()
        conn.commit()

        print(f"  After demotion: current={demoted_current}, max={demoted_max}")
        assert demoted_max == new_max, f"❌ max_achieved_level should not decrease on demotion"
        print(f"  ✅ PASS: max_achieved_level does not decrease")

    cur.close()
    conn.close()

def test_07_updated_at_trigger():
    """Test updated_at trigger auto-updates on UPDATE"""
    print("✓ Test 7: updated_at trigger...")
    conn = get_connection()
    cur = conn.cursor()

    # Get current updated_at
    cur.execute("SELECT updated_at FROM gancuju_licenses WHERE user_id = 2 LIMIT 1")
    old_updated_at = cur.fetchone()[0]

    import time
    time.sleep(1)  # Wait 1 second

    # Update a field
    cur.execute("""
        UPDATE gancuju_licenses
        SET sessions_attended = sessions_attended + 1
        WHERE user_id = 2
        RETURNING updated_at;
    """)
    new_updated_at = cur.fetchone()[0]
    conn.commit()

    assert new_updated_at > old_updated_at, "❌ updated_at not updated"

    cur.close()
    conn.close()
    print(f"  ✅ PASS: updated_at trigger works (old: {old_updated_at}, new: {new_updated_at})")

def cleanup():
    """Cleanup test data"""
    print("\n🧹 Cleanup...")
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM gancuju_licenses WHERE user_id = 2")
    conn.commit()

    cur.close()
    conn.close()
    print("  ✅ Cleanup complete")

if __name__ == "__main__":
    print("=" * 80)
    print("TEST SUITE: gancuju_licenses")
    print("=" * 80)

    try:
        test_01_table_exists()
        license_id = test_02_insert_valid_license()
        test_03_auto_computed_win_rate()
        test_04_check_constraints()
        test_05_unique_active_license()
        test_06_max_achieved_level_trigger()
        test_07_updated_at_trigger()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED (7/7)")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup()
