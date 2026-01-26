#!/usr/bin/env python3
"""
Test skill profile API endpoint
"""
import requests
import json

BASE_URL = "http://localhost:8000"

# Login
print("🔐 Logging in...")
login_response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={"email": "kylian.mbappe@f1rstteam.hu", "password": "Mbappe2026!"}
)
login_response.raise_for_status()
token = login_response.json()["access_token"]
print(f"✅ Logged in successfully")

# Get skill profile
print("\n📊 Fetching skill profile...")
headers = {"Authorization": f"Bearer {token}"}
skill_response = requests.get(
    f"{BASE_URL}/api/v1/progression/skill-profile",
    headers=headers
)

print(f"Status Code: {skill_response.status_code}")
print(f"\n📋 Response:")
print(json.dumps(skill_response.json(), indent=2))
