#!/usr/bin/env python3
"""Test assignment request POST endpoint"""

import requests
import json

BASE_URL = "http://localhost:8000"

# Login as admin
print("🔐 Logging in as admin...")
response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={"email": "admin@lfa.com", "password": "admin123"}
)

if response.status_code != 200:
    print(f"❌ Login failed: {response.status_code}")
    print(response.json())
    exit(1)

token = response.json()["access_token"]
print(f"✅ Login successful\n")

# Send assignment request
print("📨 Sending assignment request...")
payload = {
    "semester_id": 154,  # 2026/LFA_PLAYER_PRE_M01
    "instructor_id": 3,  # Grand Master
    "request_message": "Manual test request from Python script",
    "priority": 5
}

print(f"Request payload: {json.dumps(payload, indent=2)}\n")

response = requests.post(
    f"{BASE_URL}/api/v1/instructor-assignments/requests",
    headers={"Authorization": f"Bearer {token}"},
    json=payload,
    timeout=10
)

print(f"Response Status: {response.status_code}")
print(f"Response Body:")
try:
    print(json.dumps(response.json(), indent=2))
except:
    print(response.text)
