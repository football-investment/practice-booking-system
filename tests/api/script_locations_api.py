#!/usr/bin/env python3
"""Test script to verify locations endpoint"""

import requests
import json

API_BASE = "http://localhost:8000/api/v1"

# Login
print("1. Logging in as admin...")
login_response = requests.post(
    f"{API_BASE}/auth/login",
    json={"email": "admin@lfa.com", "password": "admin123"}
)
print(f"Login status: {login_response.status_code}")
token = login_response.json().get("access_token")
print(f"Token: {token[:50]}...")

# Get locations
print("\n2. Fetching locations...")
headers = {"Authorization": f"Bearer {token}"}
locations_response = requests.get(
    f"{API_BASE}/admin/locations/",
    headers=headers
)
print(f"Locations status: {locations_response.status_code}")
print(f"Response: {json.dumps(locations_response.json(), indent=2)}")
