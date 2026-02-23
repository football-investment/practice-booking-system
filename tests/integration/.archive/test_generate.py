#!/usr/bin/env python3
"""Test semester generation endpoint"""

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

# Generate semesters
print("📋 Generating semesters...")
payload = {
    "year": 2026,
    "specialization": "LFA_PLAYER",
    "age_group": "PRE",
    "location_id": 1
}

print(f"Request payload: {json.dumps(payload, indent=2)}\n")

response = requests.post(
    f"{BASE_URL}/api/v1/admin/semesters/generate",
    headers={"Authorization": f"Bearer {token}"},
    json=payload
)

print(f"Response Status: {response.status_code}")
print(f"Response Body:")
try:
    print(json.dumps(response.json(), indent=2))
except:
    print(response.text)
