#!/usr/bin/env python3
"""Test instructor accepting assignment request"""

import requests
import json

BASE_URL = "http://localhost:8000"

# Login as Grand Master
print("🔐 Logging in as Grand Master...")
response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={"email": "grandmaster@lfa.com", "password": "grandmaster123"}
)

if response.status_code != 200:
    print(f"❌ Login failed: {response.status_code}")
    print(response.json())
    exit(1)

token = response.json()["access_token"]
print(f"✅ Login successful\n")

# Accept assignment request #3
print("✅ Accepting assignment request #3...")
response = requests.patch(
    f"{BASE_URL}/api/v1/instructor-assignments/requests/3/accept",
    headers={"Authorization": f"Bearer {token}"},
    json={"response_message": "I accept this assignment!"},
    timeout=10
)

print(f"Response Status: {response.status_code}")
print(f"Response Body:")
try:
    data = response.json()
    print(json.dumps(data, indent=2))

    if response.status_code == 200:
        print(f"\n✅ Request accepted successfully!")
        print(f"   Status: {data['status']}")
        print(f"   Responded at: {data['responded_at']}")
        print(f"   Response message: {data['response_message']}")
    else:
        print(f"\n❌ Failed to accept request")
except:
    print(response.text)

# Check semester master_instructor_id
if response.status_code == 200:
    print(f"\n🔍 Checking semester 154 master_instructor_id...")

    # Login as admin to check semester
    admin_response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": "admin@lfa.com", "password": "admin123"}
    )

    admin_token = admin_response.json()["access_token"]

    # Get semester details
    semester_response = requests.get(
        f"{BASE_URL}/api/v1/semesters/154",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    if semester_response.status_code == 200:
        semester = semester_response.json()
        print(f"   master_instructor_id: {semester.get('master_instructor_id')}")

        if semester.get('master_instructor_id') == 3:
            print(f"   ✅ Semester correctly assigned to Grand Master (user_id=3)")
        else:
            print(f"   ❌ Semester NOT assigned to Grand Master")
    else:
        print(f"   ❌ Failed to fetch semester: {semester_response.status_code}")
