#!/usr/bin/env python3
"""Reset Grand Master password via API"""

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
    print(f"❌ Admin login failed: {response.status_code}")
    print(response.json())
    exit(1)

admin_token = response.json()["access_token"]
print(f"✅ Admin login successful\n")

# Update Grand Master password
print("🔧 Updating Grand Master password...")
response = requests.post(
    f"{BASE_URL}/api/v1/users/3/reset-password",  # Grand Master user_id = 3
    headers={"Authorization": f"Bearer {admin_token}"},
    json={"new_password": "grandmaster123"}
)

print(f"Response Status: {response.status_code}")
if response.status_code == 200:
    print("✅ Password updated successfully\n")
else:
    print(f"❌ Failed to update password")
    print(response.text)
    exit(1)

# Test new password
print("🔐 Testing new password...")
response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={"email": "grandmaster@lfa.com", "password": "grandmaster123"}
)

if response.status_code == 200:
    print("✅ Login successful with new password!")
else:
    print(f"❌ Login failed: {response.status_code}")
    print(response.json())
