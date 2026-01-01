"""
Direct API test for tournament enrollment
To capture the full error response
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# 1. Login
print("🔐 Logging in...")
login_response = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": "k1sqx1@f1stteam.hu", "password": "YzL27aBfznkt"}
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    print(login_response.text)
    exit(1)

token = login_response.json()["access_token"]
print(f"✅ Login successful! Token: {token[:20]}...")

# 2. Enroll in tournament
print("\n🎯 Enrolling in tournament 215...")
enroll_response = requests.post(
    f"{BASE_URL}/tournaments/215/enroll",
    headers={"Authorization": f"Bearer {token}"}
)

print(f"\n📊 Response Status: {enroll_response.status_code}")
print(f"📊 Response Headers: {dict(enroll_response.headers)}")

try:
    response_json = enroll_response.json()
    print(f"\n📊 Response JSON:\n{json.dumps(response_json, indent=2)}")
except Exception as e:
    print(f"\n❌ Failed to parse JSON response!")
    print(f"Raw response text:\n{enroll_response.text}")

print(f"\n🔍 Full Response Object:")
print(f"   Status Code: {enroll_response.status_code}")
print(f"   Reason: {enroll_response.reason}")
print(f"   URL: {enroll_response.url}")
