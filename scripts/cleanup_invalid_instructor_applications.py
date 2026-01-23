"""
Cleanup Invalid Instructor Applications

Deletes instructor applications to OPEN_ASSIGNMENT tournaments.
These applications should never have been allowed.

OPEN_ASSIGNMENT tournaments use direct assignment, not applications.
"""

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"


def main():
    print("="*80)
    print("CLEANUP INVALID INSTRUCTOR APPLICATIONS")
    print("="*80)

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Find all instructor applications to OPEN_ASSIGNMENT tournaments
        cur.execute("""
            SELECT
                iar.id as application_id,
                iar.instructor_id,
                u.name as instructor_name,
                u.email as instructor_email,
                iar.semester_id as tournament_id,
                s.name as tournament_name,
                s.assignment_type,
                iar.status as application_status,
                iar.created_at
            FROM instructor_assignment_requests iar
            JOIN semesters s ON iar.semester_id = s.id
            JOIN users u ON iar.instructor_id = u.id
            WHERE s.assignment_type = 'OPEN_ASSIGNMENT'
            ORDER BY iar.created_at DESC
        """)

        invalid_applications = cur.fetchall()

        if not invalid_applications:
            print("\n✅ No invalid applications found!")
            print("   All instructor applications are valid.")
            return

        print(f"\n⚠️  Found {len(invalid_applications)} INVALID applications to OPEN_ASSIGNMENT tournaments:\n")

        for app in invalid_applications:
            print(f"   Application ID: {app['application_id']}")
            print(f"   Instructor: {app['instructor_name']} ({app['instructor_email']})")
            print(f"   Tournament: {app['tournament_name']} (ID: {app['tournament_id']})")
            print(f"   Assignment Type: {app['assignment_type']}")
            print(f"   Status: {app['application_status']}")
            print(f"   Created: {app['created_at']}")
            print()

        # Delete invalid applications (auto-confirm)
        print(f"\n🗑️  Deleting {len(invalid_applications)} invalid applications...")

        cur.execute("""
            DELETE FROM instructor_assignment_requests
            WHERE id IN (
                SELECT iar.id
                FROM instructor_assignment_requests iar
                JOIN semesters s ON iar.semester_id = s.id
                WHERE s.assignment_type = 'OPEN_ASSIGNMENT'
            )
        """)

        deleted_count = cur.rowcount
        conn.commit()

        print(f"✅ Deleted {deleted_count} invalid instructor applications")

        # Summary
        print("\n" + "="*80)
        print("✅ CLEANUP COMPLETE")
        print("="*80)
        print(f"\n📊 Summary:")
        print(f"   - Invalid applications found: {len(invalid_applications)}")
        print(f"   - Applications deleted: {deleted_count}")
        print()
        print("💡 Going forward:")
        print("   - OPEN_ASSIGNMENT tournaments: Admin directly assigns instructor")
        print("   - APPLICATION_BASED tournaments: Instructors can apply")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
