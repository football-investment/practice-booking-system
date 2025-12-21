#!/usr/bin/env python3
"""
Create Test Sessions and Students for Phased Testing
=====================================================

This script creates:
1. Multiple ON-SITE sessions with different start times to test booking/cancellation rules
2. Multiple test students for different scenarios

Booking Rules:
- Student can book up to 24 hours before event (with credit deduction)
- Cannot book after 24-hour deadline

Cancellation Rules:
- Can cancel up to 12 hours before event (full credit refund)
- Cannot cancel after 12-hour deadline

Session Scenarios:
1. Session in 48+ hours - Bookable ✅, Cancellable ✅
2. Session in 20 hours - Bookable ✅, NOT Cancellable ❌
3. Session in 10 hours - NOT Bookable ❌, NOT Cancellable ❌
4. Session in 2 hours - NOT Bookable ❌, NOT Cancellable ❌
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Optional

BASE_URL = "http://localhost:8000/api/v1"

# Test user credentials
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"

# Test student accounts to create
TEST_STUDENTS = [
    {
        "email": "student.early@test.com",
        "password": "test123",
        "name": "Early Booker Student",
        "scenario": "Books 48h before, cancels 36h before (both allowed)"
    },
    {
        "email": "student.late@test.com",
        "password": "test123",
        "name": "Late Booker Student",
        "scenario": "Books 20h before, tries to cancel 10h before (booking OK, cancel blocked)"
    },
    {
        "email": "student.toolate@test.com",
        "password": "test123",
        "name": "Too Late Student",
        "scenario": "Tries to book 10h before (booking blocked)"
    },
    {
        "email": "student.test1@test.com",
        "password": "test123",
        "name": "Test Student 1",
        "scenario": "General testing"
    }
]


def login(email: str, password: str) -> Optional[str]:
    """Login and get JWT token"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print(f"✅ Login successful: {email}")
            return token
        else:
            print(f"❌ Login failed for {email}: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Login error for {email}: {e}")
        return None


def create_student(admin_token: str, student_data: Dict) -> bool:
    """Create a test student account"""
    try:
        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {
            "email": student_data["email"],
            "password": student_data["password"],
            "name": student_data["name"],
            "role": "student",
            "specialization": "INTERNSHIP",
            "onboarding_completed": True,
            "date_of_birth": "2000-01-01",
            "is_active": True
        }

        response = requests.post(
            f"{BASE_URL}/users/",
            headers=headers,
            json=payload
        )

        if response.status_code in [200, 201]:
            print(f"✅ Created student: {student_data['email']}")
            print(f"   Scenario: {student_data['scenario']}")
            return True
        elif response.status_code == 400 and ("already exists" in response.text or "already registered" in response.text):
            print(f"ℹ️  Student already exists: {student_data['email']}")
            return True
        else:
            print(f"❌ Failed to create student {student_data['email']}: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating student {student_data['email']}: {e}")
        return False


def create_onsite_session(admin_token: str, hours_from_now: int, title_suffix: str) -> Optional[Dict]:
    """Create an ON-SITE session starting in X hours"""
    try:
        headers = {"Authorization": f"Bearer {admin_token}"}

        start_time = datetime.now() + timedelta(hours=hours_from_now)
        end_time = start_time + timedelta(hours=2)

        # Determine booking/cancellation status
        if hours_from_now >= 24:
            status = "✅ Bookable, ✅ Cancellable"
        elif hours_from_now >= 12:
            status = "✅ Bookable, ❌ NOT Cancellable"
        else:
            status = "❌ NOT Bookable, ❌ NOT Cancellable"

        session_data = {
            "title": f"Test ON-SITE Session - {title_suffix}",
            "description": f"Session starting in {hours_from_now} hours. {status}",
            "session_type": "on_site",
            "target_specialization": "INTERNSHIP",  # Required for filtering
            "date_start": start_time.isoformat(),
            "date_end": end_time.isoformat(),
            "location": "LFA Training Ground",
            "capacity": 20,
            "semester_id": 2,  # Using active semester ID
            "sport_type": "Football",
            "level": "All Levels",
            "instructor_name": "Test Instructor"
        }

        response = requests.post(
            f"{BASE_URL}/sessions/",
            headers=headers,
            json=session_data
        )

        if response.status_code in [200, 201]:
            session = response.json()
            print(f"✅ Created ON-SITE session (ID: {session.get('id')})")
            print(f"   Title: {session_data['title']}")
            print(f"   Start: {start_time.strftime('%Y-%m-%d %H:%M')} ({hours_from_now}h from now)")
            print(f"   Status: {status}")
            return session
        else:
            print(f"❌ Failed to create session: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating session: {e}")
        return None


def main():
    """Create test sessions and students"""
    print("=" * 80)
    print("🧪 Creating Test Sessions and Students for Phase 1 Testing")
    print("=" * 80)
    print()

    # Step 1: Login as admin
    print("📝 Step 1: Login as Admin")
    print("-" * 80)
    admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not admin_token:
        print("❌ Cannot continue without admin token!")
        return
    print()

    # Step 2: Create test students
    print("📝 Step 2: Create Test Students")
    print("-" * 80)
    students_created = 0
    for student in TEST_STUDENTS:
        if create_student(admin_token, student):
            students_created += 1
    print(f"✅ Created/verified {students_created}/{len(TEST_STUDENTS)} students")
    print()

    # Step 3: Create test sessions with different timing scenarios
    print("📝 Step 3: Create Test ON-SITE Sessions")
    print("-" * 80)
    sessions = []

    # Scenario 1: Session in 48 hours (Bookable ✅, Cancellable ✅)
    session1 = create_onsite_session(
        admin_token,
        hours_from_now=48,
        title_suffix="48h Future (Bookable + Cancellable)"
    )
    if session1:
        sessions.append(session1)
    print()

    # Scenario 2: Session in 30 hours (Bookable ✅, Cancellable ✅)
    session2 = create_onsite_session(
        admin_token,
        hours_from_now=30,
        title_suffix="30h Future (Bookable + Cancellable)"
    )
    if session2:
        sessions.append(session2)
    print()

    # Scenario 3: Session in 20 hours (Bookable ✅, NOT Cancellable ❌)
    session3 = create_onsite_session(
        admin_token,
        hours_from_now=20,
        title_suffix="20h Future (Bookable, NO Cancel)"
    )
    if session3:
        sessions.append(session3)
    print()

    # Scenario 4: Session in 10 hours (NOT Bookable ❌, NOT Cancellable ❌)
    session4 = create_onsite_session(
        admin_token,
        hours_from_now=10,
        title_suffix="10h Future (NO Booking, NO Cancel)"
    )
    if session4:
        sessions.append(session4)
    print()

    # Scenario 5: Session in 2 hours (NOT Bookable ❌, NOT Cancellable ❌)
    session5 = create_onsite_session(
        admin_token,
        hours_from_now=2,
        title_suffix="2h Future (NO Booking, NO Cancel)"
    )
    if session5:
        sessions.append(session5)
    print()

    # Summary
    print("=" * 80)
    print("✅ Test Data Creation Complete!")
    print("=" * 80)
    print(f"Students created: {students_created}/{len(TEST_STUDENTS)}")
    print(f"Sessions created: {len(sessions)}/5")
    print()
    print("📊 Session Summary:")
    for i, session in enumerate(sessions, 1):
        print(f"  {i}. ID {session.get('id')}: {session.get('title')}")
    print()
    print("🧪 You can now run the Student ON-SITE workflow tests!")
    print("   The first test (Browse ON-SITE Sessions) should now return these sessions.")
    print()
    print("🔗 Test URLs:")
    print(f"   Browse: {BASE_URL}/sessions?session_type=on_site")
    print(f"   Session Details: {BASE_URL}/sessions/{{session_id}}")
    print()
    print("👤 Test Student Logins:")
    for student in TEST_STUDENTS:
        print(f"   {student['email']} / {student['password']}")
        print(f"      → {student['scenario']}")
    print()


if __name__ == "__main__":
    main()
