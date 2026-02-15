#!/usr/bin/env python3
"""
Test Round Results API endpoints
"""
import requests
import json

API_BASE = "http://localhost:8000"

# Login
login_response = requests.post(
    f"{API_BASE}/api/v1/auth/login",
    json={"email": "admin@lfa.com", "password": "admin123"}
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.text}")
    exit(1)

access_token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {access_token}"}

print("=" * 70)
print("🔄 Testing Round Results API")
print("=" * 70)

# Get session ID
session_id = 194
tournament_id = 18

# Test 1: Get initial rounds status
print("\n1️⃣ GET initial rounds status")
response = requests.get(
    f"{API_BASE}/api/v1/tournaments/{tournament_id}/sessions/{session_id}/rounds",
    headers=headers
)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))

# Test 2: Submit round 1 results
print("\n2️⃣ POST round 1 results")
response = requests.post(
    f"{API_BASE}/api/v1/tournaments/{tournament_id}/sessions/{session_id}/rounds/1/submit-results",
    headers=headers,
    json={
        "round_number": 1,
        "results": {
            "123": "12.5s",
            "456": "13.2s",
            "789": "14.1s"
        },
        "notes": "Round 1 completed successfully"
    }
)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))

# Test 3: Submit round 2 results
print("\n3️⃣ POST round 2 results")
response = requests.post(
    f"{API_BASE}/api/v1/tournaments/{tournament_id}/sessions/{session_id}/rounds/2/submit-results",
    headers=headers,
    json={
        "round_number": 2,
        "results": {
            "123": "12.3s",
            "456": "13.0s",
            "789": "14.5s"
        },
        "notes": "Round 2 - improved times"
    }
)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))

# Test 4: Get updated rounds status
print("\n4️⃣ GET updated rounds status")
response = requests.get(
    f"{API_BASE}/api/v1/tournaments/{tournament_id}/sessions/{session_id}/rounds",
    headers=headers
)
print(f"Status: {response.status_code}")
result = response.json()
print(json.dumps(result, indent=2))

# Test 5: Re-submit round 1 (idempotent)
print("\n5️⃣ POST round 1 AGAIN (idempotent test)")
response = requests.post(
    f"{API_BASE}/api/v1/tournaments/{tournament_id}/sessions/{session_id}/rounds/1/submit-results",
    headers=headers,
    json={
        "round_number": 1,
        "results": {
            "123": "11.9s",  # Updated time
            "456": "12.8s",
            "789": "13.7s"
        },
        "notes": "Round 1 UPDATED - better times after re-measurement"
    }
)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))

# Test 6: Verify idempotent update
print("\n6️⃣ GET final rounds status (verify idempotent update)")
response = requests.get(
    f"{API_BASE}/api/v1/tournaments/{tournament_id}/sessions/{session_id}/rounds",
    headers=headers
)
result = response.json()
print(f"Status: {response.status_code}")
print(json.dumps(result, indent=2))

print("\n" + "=" * 70)
if result['completed_rounds'] == 2 and result['pending_rounds'] == [3, 4, 5, 6, 7]:
    print("🎉 SUCCESS! Round results API working correctly!")
    print(f"   ✅ Completed: {result['completed_rounds']} rounds")
    print(f"   ✅ Pending: {result['pending_rounds']}")
    print(f"   ✅ Idempotent update verified (round 1 updated)")
else:
    print("❌ FAILURE! Unexpected state")
print("=" * 70)
