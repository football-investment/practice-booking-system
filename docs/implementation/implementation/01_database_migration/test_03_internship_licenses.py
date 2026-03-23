"""
Test Suite for internship_licenses table
Tests:
1. Table exists
2. Can insert valid license
3. Auto level-up trigger works (XP thresholds)
4. CHECK constraints work (level ranges, credit_balance, XP)
5. UNIQUE constraint works (one active license per user)
6. max_achieved_level auto-updates
7. Expiry check works (auto-deactivate)
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
    """Test that internship_licenses table exists"""
    print("✓ Test 1: Table exists...")
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'internship_licenses'
        );
    """)

    exists = cur.fetchone()[0]
    assert exists, "❌ Table internship_licenses does not exist"

    cur.close()
    conn.close()
    print("  ✅ PASS: Table exists")

def test_02_insert_valid_license():
    """Test inserting a valid Internship license"""
    print("✓ Test 2: Insert valid license...")
    conn = get_connection()
    cur = conn.cursor()

    # Cleanup any existing licenses for user_id=2 (from previous tests)
    cur.execute("DELETE FROM internship_licenses WHERE user_id = 2")
    conn.commit()

    # 15 months from now
    expires_at = datetime.now() + timedelta(days=450)

    # Insert license with initial XP
    cur.execute("""
        INSERT INTO internship_licenses
        (user_id, credit_balance, total_xp, expires_at)
        VALUES (2, 100, 1500, %s)
        RETURNING id, current_level;
    """, (expires_at,))

    license_id, current_level = cur.fetchone()
    assert license_id is not None, "❌ Failed to insert license"

    conn.commit()
    cur.close()
    conn.close()
    print(f"  ✅ PASS: License created with ID={license_id}, level={current_level}")
    return license_id

def test_03_auto_levelup_trigger():
    """Test auto level-up when XP crosses thresholds"""
    print("✓ Test 3: Auto level-up trigger...")
    conn = get_connection()
    cur = conn.cursor()

    # XP Thresholds: L1=0, L2=1000, L3=2500, L4=4500, L5=7000, L6=10000, L7=13500, L8=17500
    test_cases = [
        (500, 1),    # Below L2 threshold
        (1000, 2),   # Exactly L2 threshold
        (1200, 2),   # Above L2, below L3
        (2500, 3),   # Exactly L3 threshold
        (4500, 4),   # L4 threshold
        (7000, 5),   # L5 threshold
        (10000, 6),  # L6 threshold
        (13500, 7),  # L7 threshold
        (17500, 8),  # L8 threshold
        (22500, 8),  # Max XP, still L8
    ]

    for xp, expected_level in test_cases:
        cur.execute("""
            UPDATE internship_licenses
            SET total_xp = %s
            WHERE user_id = 2
            RETURNING current_level;
        """, (xp,))
        actual_level = cur.fetchone()[0]
        conn.commit()

        assert actual_level == expected_level, f"❌ XP={xp}: expected L{expected_level}, got L{actual_level}"
        print(f"  ✅ XP={xp:5d} → Level {actual_level} (expected {expected_level})")

    print("  ✅ PASS: Auto level-up trigger works correctly")

    cur.close()
    conn.close()

def test_04_check_constraints():
    """Test CHECK constraints (level ranges, credit_balance, XP)"""
    print("✓ Test 4: CHECK constraints...")
    conn = get_connection()
    cur = conn.cursor()

    expires_at = datetime.now() + timedelta(days=450)

    # Test 1: Invalid current_level (9 - above max)
    # Note: current_level=0 would be auto-corrected by trigger to level 1 (XP=0)
    # So we test an invalid level that's ABOVE the max (9)
    try:
        # Disable trigger temporarily for this test
        cur.execute("ALTER TABLE internship_licenses DISABLE TRIGGER trg_internship_licenses_auto_levelup")
        cur.execute("""
            INSERT INTO internship_licenses (user_id, current_level, expires_at)
            VALUES (3, 9, %s);
        """, (expires_at,))
        conn.commit()
        assert False, "❌ Should have failed: current_level = 9"
    except psycopg2.IntegrityError:
        conn.rollback()
        print("  ✅ PASS: current_level CHECK constraint works (1-8)")
    finally:
        # Re-enable trigger
        cur.execute("ALTER TABLE internship_licenses ENABLE TRIGGER trg_internship_licenses_auto_levelup")
        conn.commit()

    # Test 2: Negative total_xp
    try:
        cur.execute("""
            INSERT INTO internship_licenses (user_id, total_xp, expires_at)
            VALUES (3, -100, %s);
        """, (expires_at,))
        conn.commit()
        assert False, "❌ Should have failed: negative total_xp"
    except psycopg2.IntegrityError:
        conn.rollback()
        print("  ✅ PASS: total_xp >= 0 CHECK constraint works")

    # Test 3: Negative credit_balance
    try:
        cur.execute("""
            INSERT INTO internship_licenses (user_id, credit_balance, expires_at)
            VALUES (3, -50, %s);
        """, (expires_at,))
        conn.commit()
        assert False, "❌ Should have failed: negative credit_balance"
    except psycopg2.IntegrityError:
        conn.rollback()
        print("  ✅ PASS: credit_balance >= 0 CHECK constraint works")

    # Test 4: Missing expires_at (NOT NULL)
    try:
        cur.execute("""
            INSERT INTO internship_licenses (user_id)
            VALUES (3);
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

    expires_at = datetime.now() + timedelta(days=450)

    # Try to insert second active license for user_id=2
    try:
        cur.execute("""
            INSERT INTO internship_licenses (user_id, is_active, expires_at)
            VALUES (2, TRUE, %s);
        """, (expires_at,))
        conn.commit()
        assert False, "❌ Should have failed: duplicate active license"
    except psycopg2.IntegrityError:
        conn.rollback()
        print("  ✅ PASS: UNIQUE active license constraint works")

    # But can insert inactive license
    cur.execute("""
        INSERT INTO internship_licenses (user_id, is_active, expires_at)
        VALUES (2, FALSE, %s)
        RETURNING id;
    """, (expires_at,))
    license_id = cur.fetchone()[0]
    conn.commit()
    print(f"  ✅ PASS: Can insert inactive license (ID={license_id})")

    # Cleanup
    cur.execute("DELETE FROM internship_licenses WHERE id = %s", (license_id,))
    conn.commit()

    cur.close()
    conn.close()

def test_06_max_achieved_level_trigger():
    """Test max_achieved_level auto-updates when current_level increases"""
    print("✓ Test 6: max_achieved_level trigger...")
    conn = get_connection()
    cur = conn.cursor()

    # Get current max_achieved_level (might be 8 from previous test)
    cur.execute("SELECT max_achieved_level FROM internship_licenses WHERE user_id = 2")
    previous_max = cur.fetchone()[0]
    print(f"  Previous max_achieved_level: {previous_max}")

    # Set XP to L5 (7000 XP)
    cur.execute("""
        UPDATE internship_licenses
        SET total_xp = 7000
        WHERE user_id = 2
        RETURNING current_level, max_achieved_level;
    """)
    current, max_level = cur.fetchone()
    conn.commit()
    print(f"  At L5: current={current}, max={max_level}")

    assert max_level >= current, f"❌ max should be >= current"
    # max should be either previous_max or current (whichever is higher)
    expected_max = max(previous_max, current)
    assert max_level == expected_max, f"❌ max should be {expected_max}"
    print(f"  ✅ max_achieved_level is correctly {max_level} (>= current {current})")

    # Demote to L3 (2600 XP)
    cur.execute("""
        UPDATE internship_licenses
        SET total_xp = 2600
        WHERE user_id = 2
        RETURNING current_level, max_achieved_level;
    """)
    demoted_current, demoted_max = cur.fetchone()
    conn.commit()
    print(f"  After demotion: current={demoted_current}, max={demoted_max}")

    assert demoted_current == 3, f"❌ current should be 3"
    assert demoted_max >= max_level, f"❌ max should not decrease (was {max_level})"
    print(f"  ✅ PASS: max_achieved_level does not decrease on demotion")

    cur.close()
    conn.close()

def test_07_expiry_check():
    """Test auto-deactivation when license expires"""
    print("✓ Test 7: Expiry check trigger...")
    conn = get_connection()
    cur = conn.cursor()

    # Create license that already expired
    expired_date = datetime.now() - timedelta(days=1)

    cur.execute("""
        INSERT INTO internship_licenses (user_id, expires_at, is_active)
        VALUES (3, %s, TRUE)
        RETURNING id, is_active;
    """, (expired_date,))

    license_id, is_active = cur.fetchone()
    conn.commit()

    # Should have been auto-deactivated
    assert is_active == False, f"❌ Expired license should be auto-deactivated"
    print(f"  ✅ PASS: Expired license auto-deactivated (ID={license_id})")

    # Cleanup
    cur.execute("DELETE FROM internship_licenses WHERE id = %s", (license_id,))
    conn.commit()

    cur.close()
    conn.close()

def test_08_updated_at_trigger():
    """Test updated_at trigger auto-updates on UPDATE"""
    print("✓ Test 8: updated_at trigger...")
    conn = get_connection()
    cur = conn.cursor()

    # Get current updated_at
    cur.execute("SELECT updated_at FROM internship_licenses WHERE user_id = 2 LIMIT 1")
    old_updated_at = cur.fetchone()[0]

    import time
    time.sleep(1)  # Wait 1 second

    # Update a field
    cur.execute("""
        UPDATE internship_licenses
        SET sessions_completed = sessions_completed + 1
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

    cur.execute("DELETE FROM internship_licenses WHERE user_id IN (2, 3)")
    conn.commit()

    cur.close()
    conn.close()
    print("  ✅ Cleanup complete")

if __name__ == "__main__":
    print("=" * 80)
    print("TEST SUITE: internship_licenses")
    print("=" * 80)

    try:
        test_01_table_exists()
        license_id = test_02_insert_valid_license()
        test_03_auto_levelup_trigger()
        test_04_check_constraints()
        test_05_unique_active_license()
        test_06_max_achieved_level_trigger()
        test_07_expiry_check()
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
