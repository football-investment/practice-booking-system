"""
Debug script to test authentication flow
"""
import requests
import json

# Step 1: Login
print("🔐 Step 1: Login as admin")
login_response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "admin@lfa.com", "password": "admin123"}
)
print(f"   Status: {login_response.status_code}")
if login_response.status_code == 200:
    token_data = login_response.json()
    access_token = token_data["access_token"]
    print(f"   Token: {access_token[:50]}...")
else:
    print(f"   ERROR: {login_response.text}")
    exit(1)

# Step 2: Test protected endpoint with token
print("\n🔐 Step 2: Test /tournaments/1202/sessions with Bearer token")
headers = {"Authorization": f"Bearer {access_token}"}
sessions_response = requests.get(
    "http://localhost:8000/api/v1/tournaments/1202/sessions",
    headers=headers
)
print(f"   Status: {sessions_response.status_code}")
if sessions_response.status_code == 200:
    sessions = sessions_response.json()
    print(f"   ✅ SUCCESS: Got {len(sessions)} sessions")
    if sessions:
        first = sessions[0]
        print(f"   First session has 'id': {'id' in first}")
        print(f"   First session has 'game_results': {'game_results' in first}")
else:
    print(f"   ❌ ERROR: {sessions_response.text}")
