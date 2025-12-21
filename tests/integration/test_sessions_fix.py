#!/usr/bin/env python3
"""
Quick test to verify SessionFilterService fix for INTERNSHIP users
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# Step 1: Login
print("=" * 80)
print("🔐 Logging in as junior.intern@lfa.com (INTERNSHIP specialization)...")
print("=" * 80)
login_response = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": "junior.intern@lfa.com", "password": "junior123"}
)
if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    print(login_response.text)
    exit(1)

token = login_response.json()["access_token"]
print("✅ Login successful!")
print()

# Step 2: Get ON-SITE sessions
print("=" * 80)
print("📋 Fetching ON-SITE sessions...")
print("=" * 80)
headers = {"Authorization": f"Bearer {token}"}
sessions_response = requests.get(
    f"{BASE_URL}/sessions/",
    headers=headers,
    params={"session_type": "on_site", "limit": 10}
)

print(f"Status Code: {sessions_response.status_code}")
print()

if sessions_response.status_code != 200:
    print(f"❌ Failed to fetch sessions")
    print(sessions_response.text)
    exit(1)

sessions_data = sessions_response.json()
print(f"✅ Successfully fetched sessions!")
print()

# Check response format
if isinstance(sessions_data, dict):
    # Paginated response
    sessions = sessions_data.get('items', sessions_data.get('data', []))
    total = sessions_data.get('total', len(sessions))
    print(f"📊 Response Format: Paginated")
    print(f"   Total: {total}")
    print(f"   Items in response: {len(sessions)}")
elif isinstance(sessions_data, list):
    # List response
    sessions = sessions_data
    print(f"📊 Response Format: List")
    print(f"   Total sessions: {len(sessions)}")
else:
    print(f"❌ Unexpected response format: {type(sessions_data)}")
    exit(1)

print()
print("=" * 80)
print("🎯 SESSION FILTERING TEST RESULTS")
print("=" * 80)

if len(sessions) == 0:
    print("❌ FAILED: No sessions returned!")
    print()
    print("🔍 Expected behavior:")
    print("   - INTERNSHIP user should see ON-SITE sessions with target_specialization=INTERNSHIP")
    print("   - SessionFilterService should be BYPASSED for INTERNSHIP users")
    print()
    print("🐛 Possible issues:")
    print("   1. No INTERNSHIP ON-SITE sessions in database")
    print("   2. SessionFilterService still filtering out sessions")
    print("   3. target_specialization filter not matching")
else:
    print(f"✅ SUCCESS: {len(sessions)} session(s) returned!")
    print()
    print("📋 Session Details:")
    for i, session in enumerate(sessions[:5], 1):
        print(f"\n   {i}. {session.get('title', 'N/A')}")
        print(f"      ID: {session.get('id')}")
        print(f"      Type: {session.get('session_type')}")
        print(f"      Specialization: {session.get('target_specialization', 'N/A')}")
        print(f"      Start: {session.get('date_start', 'N/A')}")

print()
print("=" * 80)
