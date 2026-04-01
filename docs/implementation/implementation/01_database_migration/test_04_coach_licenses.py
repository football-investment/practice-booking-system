"""
Test Suite for coach_licenses table
Tests:
1. Table exists
2. Can insert valid license
3. is_expired flag auto-updates based on expires_at
4. CHECK constraints work (level ranges, hours >= 0)
5. UNIQUE constraint works (one active license per user)
6. max_achieved_level auto-updates
7. Expired licenses auto-deactivate
8. Trigger updates updated_at
"""

import os
import psycopg2
from datetime import datetime, timedelta

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def test_01_table_exists():
    """Test that coach_licenses table exists"""
    print("✓ Test 1: Table exists...")
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'coach_licenses'
        );
    """)

    exists = cur.fetchone()[0]
    assert exists, "❌ Table coach_licenses does not exist"

    cur.close()
    conn.close()
    print("  ✅ PASS: Table exists")

def test_02_insert_valid_license():
    """Test inserting a valid Coach license"""
    print("✓ Test 2: Insert valid license...")
    conn = get_connection()
    cur = conn.cursor()

    # Cleanup any existing licenses for user_id=2 (from previous tests)
    cur.execute("DELETE FROM coach_licenses WHERE user_id = 2")
    conn.commit()

    # 2 years from now (valid license)
    expires_at = datetime.now() + timedelta(days=730)

    # Insert license
    cur.execute("""
        INSERT INTO coach_licenses
        (user_id, current_level, theory_hours, practice_hours, expires_at)
        VALUES (2, 2, 40, 60, %s)
        RETURNING id, is_expired;
    """, (expires_at,))

    license_id, is_expired = cur.fetchone()
    assert license_id is not None, "❌ Failed to insert license"
    assert is_expired == False, "❌ is_expired should be False for future expiry date"

    conn.commit()
    cur.close()
    conn.close()
    print(f"  ✅ PASS: License created with ID={license_id}, is_expired={is_expired}")
    return license_id

def test_03_is_expired_trigger():
    """Test is_expired flag auto-updates based on expires_at"""
    print("✓ Test 3: is_expired trigger...")
    conn = get_connection()
    cur = conn.cursor()

    # Test 1: Future expiry date (should NOT be expired)
    future_expiry = datetime.now() + timedelta(days=730)
    cur.execute("""
        INSERT INTO coach_licenses (user_id, expires_at)
        VALUES (3, %s)
        RETURNING id, is_expired;
    """, (future_expiry,))
    license_id, is_expired = cur.fetchone()
    conn.commit()
    assert is_expired == False, f"❌ Future expiry should not be expired"
    print(f"  ✅ Future expiry: is_expired={is_expired} (correct)")

    # Test 2: Past expiry date (should BE expired)
    past_expiry = datetime.now() - timedelta(days=1)
    cur.execute("""
        UPDATE coach_licenses
        SET expires_at = %s
        WHERE id = %s
        RETURNING is_expired, is_active;
    """, (past_expiry, license_id))
    is_expired, is_active = cur.fetchone()
    conn.commit()
    assert is_expired == True, f"❌ Past expiry should be expired"
    assert is_active == False, f"❌ Expired license should be deactivated"
    print(f"  ✅ Past expiry: is_expired={is_expired}, is_active={is_active} (correct)")

    # Cleanup
    cur.execute("DELETE FROM coach_licenses WHERE id = %s", (license_id,))
    conn.commit()

    cur.close()
    conn.close()

def test_04_check_constraints():
    """Test CHECK constraints (level ranges, hours >= 0)"""
    print("✓ Test 4: CHECK constraints...")
    conn = get_connection()
    cur = conn.cursor()

    expires_at = datetime.now() + timedelta(days=730)

    # Test 1: Invalid current_level (9)
    try:
        cur.execute("""
            INSERT INTO coach_licenses (user_id, current_level, expires_at)
            VALUES (4, 9, %s);
        """, (expires_at,))
        conn.commit()
        assert False, "❌ Should have failed: current_level = 9"
    except psycopg2.IntegrityError:
        conn.rollback()
        print("  ✅ PASS: current_level CHECK constraint works (1-8)")

    # Test 2: Invalid current_level (0)
    try:
        cur.execute("""
            INSERT INTO coach_licenses (user_id, current_level, expires_at)
            VALUES (4, 0, %s);
        """, (expires_at,))
        conn.commit()
        assert False, "❌ Should have failed: current_level = 0"
    except psycopg2.IntegrityError:
        conn.rollback()
        print("  ✅ PASS: current_level min=1 constraint works")

    # Test 3: Negative theory_hours
    try:
        cur.execute("""
            INSERT INTO coach_licenses (user_id, theory_hours, expires_at)
            VALUES (4, -10, %s);
        """, (expires_at,))
        conn.commit()
        assert False, "❌ Should have failed: negative theory_hours"
    except psycopg2.IntegrityError:
        conn.rollback()
        print("  ✅ PASS: theory_hours >= 0 constraint works")

    # Test 4: Negative practice_hours
    try:
        cur.execute("""
            INSERT INTO coach_licenses (user_id, practice_hours, expires_at)
            VALUES (4, -10, %s);
        """, (expires_at,))
        conn.commit()
        assert False, "❌ Should have failed: negative practice_hours"
    except psycopg2.IntegrityError:
        conn.rollback()
        print("  ✅ PASS: practice_hours >= 0 constraint works")

    # Test 5: Missing expires_at (NOT NULL)
    try:
        cur.execute("""
            INSERT INTO coach_licenses (user_id)
            VALUES (4);
        """)
        conn.commit()
        assert False, "❌ Should have failed: NULL expires_at"
    except psycopg2.IntegrityError:
        conn.rollback()
        print("  ✅ PASS: expires_at NOT NULL constraint works")

    cur.close()
    conn.close()

def test_05_unique_active_license():
    """Test UNIQUE constraint: one active license per user"""
    print("✓ Test 5: UNIQUE active license per user...")
    conn = get_connection()
    cur = conn.cursor()

    expires_at = datetime.now() + timedelta(days=730)

    # Try to insert second active license for user_id=2
    try:
        cur.execute("""
            INSERT INTO coach_licenses (user_id, is_active, expires_at)
            VALUES (2, TRUE, %s);
        """, (expires_at,))
        conn.commit()
        assert False, "❌ Should have failed: duplicate active license"
    except psycopg2.IntegrityError:
        conn.rollback()
        print("  ✅ PASS: UNIQUE active license constraint works")

    # But can insert inactive license
    cur.execute("""
        INSERT INTO coach_licenses (user_id, is_active, expires_at)
        VALUES (2, FALSE, %s)
        RETURNING id;
    """, (expires_at,))
    license_id = cur.fetchone()[0]
    conn.commit()
    print(f"  ✅ PASS: Can insert inactive license (ID={license_id})")

    # Cleanup
    cur.execute("DELETE FROM coach_licenses WHERE id = %s", (license_id,))
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
        FROM coach_licenses
        WHERE user_id = 2;
    """)
    old_current, old_max = cur.fetchone()
    print(f"  Before: current={old_current}, max={old_max}")

    # Promote to higher level
    new_level = min(old_current + 2, 8)  # Promote 2 levels (or to max 8)
    cur.execute("""
        UPDATE coach_licenses
        SET current_level = %s
        WHERE user_id = 2
        RETURNING current_level, max_achieved_level;
    """, (new_level,))
    new_current, new_max = cur.fetchone()
    conn.commit()

    print(f"  After promotion: current={new_current}, max={new_max}")

    # max should be >= current always
    assert new_max >= new_current, f"❌ max_achieved_level ({new_max}) should be >= current_level ({new_current})"
    assert new_max >= old_max, f"❌ max should not decrease"
    print(f"  ✅ PASS: max_achieved_level auto-updates correctly")

    # Test demotion (current_level goes down, but max stays)
    if new_current > 1:
        demoted_level = new_current - 1
        cur.execute("""
            UPDATE coach_licenses
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

def test_07_expiry_auto_deactivate():
    """Test auto-deactivation when license expires"""
    print("✓ Test 7: Expiry auto-deactivate...")
    conn = get_connection()
    cur = conn.cursor()

    # Create license that already expired
    expired_date = datetime.now() - timedelta(days=1)

    cur.execute("""
        INSERT INTO coach_licenses (user_id, expires_at, is_active)
        VALUES (4, %s, TRUE)
        RETURNING id, is_expired, is_active;
    """, (expired_date,))

    license_id, is_expired, is_active = cur.fetchone()
    conn.commit()

    # Should have been auto-deactivated
    assert is_expired == True, f"❌ is_expired should be True"
    assert is_active == False, f"❌ Expired license should be auto-deactivated"
    print(f"  ✅ PASS: Expired license auto-deactivated (ID={license_id})")

    # Cleanup
    cur.execute("DELETE FROM coach_licenses WHERE id = %s", (license_id,))
    conn.commit()

    cur.close()
    conn.close()

def test_08_updated_at_trigger():
    """Test updated_at trigger auto-updates on UPDATE"""
    print("✓ Test 8: updated_at trigger...")
    conn = get_connection()
    cur = conn.cursor()

    # Get current updated_at
    cur.execute("SELECT updated_at FROM coach_licenses WHERE user_id = 2 LIMIT 1")
    old_updated_at = cur.fetchone()[0]

    import time
    time.sleep(1)  # Wait 1 second

    # Update a field
    cur.execute("""
        UPDATE coach_licenses
        SET theory_hours = theory_hours + 10
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

    cur.execute("DELETE FROM coach_licenses WHERE user_id IN (2, 3, 4)")
    conn.commit()

    cur.close()
    conn.close()
    print("  ✅ Cleanup complete")

if __name__ == "__main__":
    print("=" * 80)
    print("TEST SUITE: coach_licenses")
    print("=" * 80)

    try:
        test_01_table_exists()
        license_id = test_02_insert_valid_license()
        test_03_is_expired_trigger()
        test_04_check_constraints()
        test_05_unique_active_license()
        test_06_max_achieved_level_trigger()
        test_07_expiry_auto_deactivate()
        test_08_updated_at_trigger()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED (8/8)")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup()
