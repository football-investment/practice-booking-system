"""
Quick test script to debug user creation API validation error
"""
import requests
import json
from datetime import datetime

API_BASE_URL = "http://localhost:8000"

# Get admin token
print("1. Getting admin token...")
login_response = requests.post(
    f"{API_BASE_URL}/api/v1/auth/login",
    json={"email": "admin@lfa.com", "password": "admin123"}
)
print(f"   Status: {login_response.status_code}")
if login_response.status_code != 200:
    print(f"   Error: {login_response.text}")
    exit(1)

admin_token = login_response.json()["access_token"]
print(f"   ✅ Token obtained")

# Try to create a user
print("\n2. Creating test user...")
timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
user_data = {
    "email": f"test_player_{timestamp}@test.com",
    "name": f"Test Player {timestamp}",
    "password": "TestPass123!",
    "role": "STUDENT",
    "date_of_birth": "2000-01-01T00:00:00",
    "specialization": "LFA_FOOTBALL_PLAYER"
}

print(f"   Payload: {json.dumps(user_data, indent=2)}")

create_response = requests.post(
    f"{API_BASE_URL}/api/v1/users",
    headers={"Authorization": f"Bearer {admin_token}"},
    json=user_data
)

print(f"\n   Status: {create_response.status_code}")
print(f"   Response: {create_response.text[:500]}")

if create_response.status_code == 422:
    print("\n   ❌ VALIDATION ERROR:")
    error_detail = create_response.json()
    print(f"   {json.dumps(error_detail, indent=2)}")
elif create_response.status_code == 200 or create_response.status_code == 201:
    print(f"\n   ✅ User created successfully!")
    user = create_response.json()
    print(f"   User ID: {user['id']}")
    print(f"   Email: {user['email']}")
else:
    print(f"\n   ⚠️  Unexpected status code: {create_response.status_code}")
    print(f"   Response: {create_response.text}")
