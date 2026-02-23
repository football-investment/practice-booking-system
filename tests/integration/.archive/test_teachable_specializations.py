#!/usr/bin/env python3
"""Test instructor teachable specializations endpoint"""

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

# Test new endpoint
print("📋 Testing GET /api/v1/licenses/instructor/3/teachable-specializations")
print("Expected: Based on COACH + INTERNSHIP + PLAYER licenses\n")

response = requests.get(
    f"{BASE_URL}/api/v1/licenses/instructor/3/teachable-specializations",
    headers={"Authorization": f"Bearer {token}"}
)

print(f"Response Status: {response.status_code}")

if response.status_code == 200:
    teachable_specs = response.json()
    print(f"\n✅ Teachable Specializations ({len(teachable_specs)} types):")
    for spec in teachable_specs:
        print(f"  - {spec}")

    print("\n📊 Analysis:")
    print(f"  COACH license → LFA_PLAYER_* types: {[s for s in teachable_specs if s.startswith('LFA_PLAYER_')]}")
    print(f"  INTERNSHIP license → INTERNSHIP: {'INTERNSHIP' in teachable_specs}")
    print(f"  PLAYER license → GANCUJU_PLAYER: {'GANCUJU_PLAYER' in teachable_specs}")
else:
    print(f"❌ Request failed: {response.status_code}")
    print(response.text)
