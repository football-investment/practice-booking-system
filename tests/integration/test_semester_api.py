#!/usr/bin/env python3
"""Test semester API endpoint with role-based filtering"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_semester_list():
    # Login as admin
    print("🔐 Logging in as admin...")
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": "admin@lfa.com", "password": "admin123"}
    )

    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        print(response.json())
        return

    token = response.json()["access_token"]
    print(f"✅ Login successful")

    # Get semester list
    print("\n📋 Fetching semester list as ADMIN...")
    response = requests.get(
        f"{BASE_URL}/api/v1/semesters/",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code != 200:
        print(f"❌ Request failed: {response.status_code}")
        print(response.json())
        return

    data = response.json()
    print(f"✅ Request successful")
    print(f"\n📊 Results:")
    print(f"   Total semesters: {data['total']}")

    # Count by status
    status_counts = {}
    for sem in data['semesters']:
        status = sem.get('status', 'UNKNOWN')
        status_counts[status] = status_counts.get(status, 0) + 1

    print(f"\n   Status breakdown:")
    for status, count in sorted(status_counts.items()):
        status_emoji = {
            "DRAFT": "📝",
            "SEEKING_INSTRUCTOR": "🔍",
            "INSTRUCTOR_ASSIGNED": "👨‍🏫",
            "READY_FOR_ENROLLMENT": "✅",
            "ONGOING": "🎓",
            "COMPLETED": "✔️",
            "CANCELLED": "❌"
        }.get(status, '❓')
        print(f"     {status_emoji} {status}: {count}")

    if data['semesters']:
        print(f"\n   First 15 semesters:")
        for sem in data['semesters'][:15]:
            status_emoji = {
                "DRAFT": "📝",
                "SEEKING_INSTRUCTOR": "🔍",
                "INSTRUCTOR_ASSIGNED": "👨‍🏫",
                "READY_FOR_ENROLLMENT": "✅",
                "ONGOING": "🎓",
                "COMPLETED": "✔️",
                "CANCELLED": "❌"
            }.get(sem.get('status'), '❓')

            instructor = f"Instructor: {sem.get('master_instructor_id', 'None')}" if sem.get('master_instructor_id') else "No instructor"
            sessions = f"{sem.get('total_sessions', 0)} sessions"

            print(f"   {status_emoji} {sem['code']:30} | Status: {sem.get('status', 'N/A'):20} | {instructor:20} | {sessions}")
    else:
        print("   ⚠️ No semesters returned!")

if __name__ == "__main__":
    test_semester_list()
