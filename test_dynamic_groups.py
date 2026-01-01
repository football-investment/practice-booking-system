#!/usr/bin/env python3
"""
Test Dynamic Session Group Assignment

Workflow:
1. Create a session
2. Book 7 students
3. Mark 6 students as PRESENT (1 absent)
4. Auto-assign groups → should create 2 groups of 3 (not 4-4)
5. Verify group assignments
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def login(email: str, password: str):
    """Login and get access token"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        print(f"✅ Logged in as {email}")
        return token
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.json())
        return None

def create_test_session(token):
    """Create a test session for group assignment"""
    headers = {"Authorization": f"Bearer {token}"}

    # Use an existing semester (ID 203 from database)
    semester_id = 203

    # Create session (within semester dates: 2025-01-01 to 2025-01-26)
    # Marco (admin) will be the instructor for testing
    session_data = {
        "title": "Dynamic Group Test Session",
        "description": "Testing dynamic group assignment at session start",
        "date_start": "2025-01-15T16:00:00",
        "date_end": "2025-01-15T17:00:00",
        "session_type": "on_site",
        "capacity": 8,  # 2 instructors × 4 students
        "location": "Budapest Test Field",
        "semester_id": semester_id,
        "instructor_id": 2949,  # Marco Bellini (admin)
        "credit_cost": 1
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/sessions",
        json=session_data,
        headers=headers
    )

    if response.status_code in [200, 201]:
        session = response.json()
        print(f"✅ Created session: {session['title']} (ID: {session['id']})")
        return session['id']
    else:
        print(f"❌ Failed to create session: {response.status_code}")
        print(response.json())
        return None

def mark_attendance_direct(session_id, student_ids, status="PRESENT"):
    """Mark students as PRESENT/ABSENT via direct database insert"""
    import subprocess

    for student_id in student_ids:
        cmd = f"""PGDATABASE=lfa_intern_system psql -U postgres -h localhost -c "
        INSERT INTO attendance (session_id, user_id, status, created_at, updated_at)
        VALUES ({session_id}, {student_id}, '{status}', NOW(), NOW())
        ON CONFLICT DO NOTHING;"
        """

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✅ Marked student {student_id} as {status}")
        else:
            print(f"  ❌ Failed to mark student {student_id}: {result.stderr}")

def auto_assign_groups(token, session_id):
    """Trigger auto-assign algorithm"""
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.post(
        f"{BASE_URL}/api/v1/session-groups/auto-assign",
        json={"session_id": session_id},
        headers=headers
    )

    print(f"\n{'='*60}")
    print(f"AUTO-ASSIGN RESULT: {response.status_code}")
    print(f"{'='*60}")

    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Groups Created:")
        print(f"Total Students: {result['total_students']}")
        print(f"Total Instructors: {result['total_instructors']}")
        print(f"\nGroups:")
        for group in result['groups']:
            print(f"  Group {group['group_number']}: {group['instructor_name']}")
            print(f"    Students ({group['student_count']}): {', '.join(group['students'])}")
        return result
    else:
        print(f"\n❌ Auto-assign failed:")
        print(json.dumps(response.json(), indent=2))
        return None

def get_session_groups(token, session_id):
    """Get group summary"""
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(
        f"{BASE_URL}/api/v1/session-groups/{session_id}",
        headers=headers
    )

    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Failed to get groups: {response.status_code}")
        return None

def main():
    print("\n" + "="*60)
    print("DYNAMIC SESSION GROUP ASSIGNMENT TEST")
    print("="*60)
    print("Scenario: 2 instructors, 7 bookings, 6 present")
    print("Expected: 2 groups × 3 students (not 4-4)")
    print("="*60)

    # Login as admin/instructor
    token = login("marco.bellini@lfa.com", "admin123")
    if not token:
        return

    # Create test session
    print("\n[STEP 1] Creating test session...")
    session_id = create_test_session(token)
    if not session_id:
        return

    # Use real student IDs from database
    print("\n[STEP 2] Using real student IDs...")
    student_ids = [2931, 2937, 2, 2938, 2943, 2944, 2934]

    # Mark 6 students as PRESENT (student 7 is absent)
    print("\n[STEP 3] Marking attendance (6 present, 1 absent)...")
    present_students = student_ids[:6]  # Students 1-6
    absent_students = [student_ids[6]]  # Student 7

    mark_attendance_direct(session_id, present_students, "present")
    mark_attendance_direct(session_id, absent_students, "absent")

    # Auto-assign groups
    print("\n[STEP 4] Auto-assigning groups based on attendance...")
    result = auto_assign_groups(token, session_id)

    if result:
        print("\n" + "="*60)
        print("TEST VALIDATION")
        print("="*60)

        # Validate results
        total_students = result['total_students']
        total_groups = len(result['groups'])

        print(f"✅ Test 1: Total students = 6? {total_students == 6}")
        print(f"✅ Test 2: Groups created = 2? {total_groups == 2}")

        # Check group sizes
        group_sizes = [g['student_count'] for g in result['groups']]
        print(f"✅ Test 3: Group sizes = [3, 3]? {group_sizes == [3, 3]}")

        # Verify no student ID 7 (absent) in groups
        all_assigned = []
        for g in result['groups']:
            all_assigned.extend(g['student_ids'])

        print(f"✅ Test 4: Absent student (7) not in groups? {7 not in all_assigned}")
        print(f"✅ Test 5: All present students assigned? {set(present_students) == set(all_assigned)}")

        print("\n" + "="*60)
        if total_students == 6 and total_groups == 2 and group_sizes == [3, 3]:
            print("✅ ALL TESTS PASSED - Dynamic group assignment working!")
        else:
            print("❌ SOME TESTS FAILED - Check implementation")
        print("="*60)

if __name__ == "__main__":
    main()
