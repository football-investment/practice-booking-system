#!/usr/bin/env python3
"""Test assignment request filters"""

import requests
import json

BASE_URL = "http://localhost:8000"

# Login as admin
print("🔐 Logging in as admin...")
response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={"email": "admin@lfa.com", "password": "admin123"}
)

admin_token = response.json()["access_token"]
print(f"✅ Admin login successful\n")

# Create multiple assignment requests for different semesters
print("📨 Creating assignment requests for different semesters...")

requests_to_create = [
    {
        "semester_id": 154,  # 2026/LFA_PLAYER_PRE_M01
        "instructor_id": 3,
        "request_message": "LFA_PLAYER PRE request",
        "priority": 8
    },
    {
        "semester_id": 166,  # 2026/LFA_PLAYER_YOUTH_Q1
        "instructor_id": 3,
        "request_message": "LFA_PLAYER YOUTH request",
        "priority": 5
    }
]

for req in requests_to_create:
    response = requests.post(
        f"{BASE_URL}/api/v1/instructor-assignments/requests",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=req
    )
    if response.status_code == 201:
        print(f"  ✅ Created request for semester {req['semester_id']}")
    elif response.status_code == 409:
        print(f"  ⚠️  Request already exists for semester {req['semester_id']}")
    else:
        print(f"  ❌ Failed: {response.status_code} - {response.text}")

# Login as Grand Master
print("\n🔐 Logging in as Grand Master...")
response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={"email": "grandmaster@lfa.com", "password": "grandmaster123"}
)

if response.status_code != 200:
    print(f"❌ Login failed: {response.status_code}")
    print(response.json())
    exit(1)

instructor_token = response.json()["access_token"]
print(f"✅ Login successful\n")

# Test 1: No filters (get all)
print("📋 Test 1: Get ALL requests (no filters)")
response = requests.get(
    f"{BASE_URL}/api/v1/instructor-assignments/requests/instructor/3",
    headers={"Authorization": f"Bearer {instructor_token}"}
)
print(f"  Found {len(response.json())} requests\n")

# Test 2: Filter by status
print("📋 Test 2: Filter by status=PENDING")
response = requests.get(
    f"{BASE_URL}/api/v1/instructor-assignments/requests/instructor/3?status_filter=PENDING",
    headers={"Authorization": f"Bearer {instructor_token}"}
)
pending = response.json()
print(f"  Found {len(pending)} PENDING requests")
for req in pending:
    print(f"    - Request #{req['id']}: Semester {req['semester_id']}, Priority {req['priority']}")

# Test 3: Filter by age_group
print("\n📋 Test 3: Filter by age_group=PRE")
response = requests.get(
    f"{BASE_URL}/api/v1/instructor-assignments/requests/instructor/3?age_group=PRE",
    headers={"Authorization": f"Bearer {instructor_token}"}
)
pre_requests = response.json()
print(f"  Found {len(pre_requests)} PRE requests")
for req in pre_requests:
    print(f"    - Request #{req['id']}: {req['request_message']}")

# Test 4: Filter by specialization
print("\n📋 Test 4: Filter by specialization_type=LFA_PLAYER")
response = requests.get(
    f"{BASE_URL}/api/v1/instructor-assignments/requests/instructor/3?specialization_type=LFA_PLAYER",
    headers={"Authorization": f"Bearer {instructor_token}"}
)
lfa_requests = response.json()
print(f"  Found {len(lfa_requests)} LFA_PLAYER requests")

# Test 5: Filter by priority
print("\n📋 Test 5: Filter by priority_min=8 (high priority only)")
response = requests.get(
    f"{BASE_URL}/api/v1/instructor-assignments/requests/instructor/3?priority_min=8",
    headers={"Authorization": f"Bearer {instructor_token}"}
)
high_priority = response.json()
print(f"  Found {len(high_priority)} high-priority requests (≥8)")
for req in high_priority:
    print(f"    - Request #{req['id']}: Priority {req['priority']} - {req['request_message']}")

# Test 6: Combine filters
print("\n📋 Test 6: Combine filters (status=PENDING + age_group=PRE + priority_min=7)")
response = requests.get(
    f"{BASE_URL}/api/v1/instructor-assignments/requests/instructor/3?status_filter=PENDING&age_group=PRE&priority_min=7",
    headers={"Authorization": f"Bearer {instructor_token}"}
)
combined = response.json()
print(f"  Found {len(combined)} requests matching all filters")
for req in combined:
    print(f"    - Request #{req['id']}: {req['request_message']}, Priority {req['priority']}")

print("\n✅ All filter tests completed!")
