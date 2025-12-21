#!/usr/bin/env python3
"""Test instructor can see assignment requests"""

import requests
import json

BASE_URL = "http://localhost:8000"

# Login as Grand Master instructor
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

# Get instructor ID from token (Grand Master is user_id=3)
instructor_id = 3

# Fetch assignment requests
print(f"📋 Fetching assignment requests for instructor {instructor_id}...")
response = requests.get(
    f"{BASE_URL}/api/v1/instructor-assignments/requests/instructor/{instructor_id}",
    headers={"Authorization": f"Bearer {token}"},
    timeout=10
)

print(f"Response Status: {response.status_code}")
print(f"Response Body:")
try:
    data = response.json()
    print(json.dumps(data, indent=2))

    if data:
        print(f"\n✅ Found {len(data)} request(s)")
        for req in data:
            print(f"\n📨 Request #{req['id']}:")
            print(f"   Semester ID: {req['semester_id']}")
            print(f"   Status: {req['status']}")
            print(f"   Message: {req['request_message']}")
            print(f"   Priority: {req['priority']}")
    else:
        print("\n⚠️ No requests found")
except:
    print(response.text)
