"""
Create E2E test tournament directly via SQL.

Bypasses unreliable Streamlit dropdown selectors by creating tournament
through direct database insertion.

This approach is preferred over UI automation when Streamlit dropdowns
are unreliable or slow.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import psycopg2

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def create_test_tournament():
    """Create OPEN_ASSIGNMENT tournament for E2E tests via SQL."""

    print("\n" + "=" * 70)
    print("🏆 E2E TEST TOURNAMENT CREATION (SQL)")
    print("=" * 70)

    # Connect to database
    try:
        conn = psycopg2.connect(
            dbname="lfa_intern_system",
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432"
        )
        cursor = conn.cursor()
        print("\n✅ Connected to database")
    except Exception as e:
        print(f"\n❌ Database connection failed: {e}")
        return False

    try:
        # Generate unique code
        timestamp = int(datetime.now().timestamp())
        code = f"E2E-OPEN-{timestamp}"

        # Calculate tournament date (7 days from now)
        tournament_date = datetime.now() + timedelta(days=7)

        print(f"\n📝 Creating tournament:")
        print(f"   Code: {code}")
        print(f"   Name: E2E Test Tournament - OPEN_ASSIGNMENT")
        print(f"   Date: {tournament_date.strftime('%Y-%m-%d')}")
        print(f"   Assignment Type: OPEN_ASSIGNMENT")
        print(f"   Max Players: 5")
        print(f"   Cost: 500 credits")
        print(f"   Instructor ID: 3 (Grandmaster)")

        # Insert tournament
        cursor.execute("""
            INSERT INTO semesters (
                code,
                name,
                specialization_type,
                start_date,
                end_date,
                is_active,
                created_at,
                updated_at,
                age_group,
                assignment_type,
                max_players,
                enrollment_cost,
                master_instructor_id,
                status,
                tournament_status,
                sessions_generated,
                reward_policy_name
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id
        """, (
            code,
            "E2E Test Tournament - OPEN_ASSIGNMENT",
            "LFA_FOOTBALL_PLAYER",
            tournament_date.date(),
            tournament_date.date(),
            True,
            datetime.now(),
            datetime.now(),
            "YOUTH",
            "OPEN_ASSIGNMENT",
            5,
            500,
            3,  # Grandmaster ID (created in reset_database_for_tests.py)
            "READY_FOR_ENROLLMENT",
            "OPEN_FOR_ENROLLMENT",
            False,
            "standard_tournament_rewards"
        ))

        tournament_id = cursor.fetchone()[0]
        conn.commit()

        print(f"\n✅ Tournament created successfully!")
        print(f"   ID: {tournament_id}")

        # Verify creation
        cursor.execute("""
            SELECT id, name, status, tournament_status, assignment_type,
                   max_players, enrollment_cost, master_instructor_id
            FROM semesters
            WHERE name LIKE '%E2E Test Tournament%'
            ORDER BY created_at DESC
            LIMIT 1
        """)

        result = cursor.fetchone()
        if result:
            print(f"\n🔍 Verification:")
            print(f"   ID: {result[0]}")
            print(f"   Name: {result[1]}")
            print(f"   Status: {result[2]}")
            print(f"   Tournament Status: {result[3]}")
            print(f"   Assignment Type: {result[4]}")
            print(f"   Max Players: {result[5]}")
            print(f"   Enrollment Cost: {result[6]} credits")
            print(f"   Instructor ID: {result[7]}")

        cursor.close()
        conn.close()

        print("\n" + "=" * 70)
        print("✅ TOURNAMENT CREATION COMPLETE")
        print("=" * 70)
        print()

        return True

    except Exception as e:
        print(f"\n❌ Failed to create tournament: {e}")
        conn.rollback()
        cursor.close()
        conn.close()
        return False


if __name__ == "__main__":
    success = create_test_tournament()
    sys.exit(0 if success else 1)
