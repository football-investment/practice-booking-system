#!/usr/bin/env python3
"""Test campus filtering by location"""
import requests
import json

API_BASE = "http://localhost:8000/api/v1"

# Login
print("1. Logging in as admin...")
login_response = requests.post(
    f"{API_BASE}/auth/login",
    json={"email": "admin@lfa.com", "password": "admin123"}
)
token = login_response.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

# Get all campuses (unfiltered)
print("\n2. All campuses (unfiltered):")
all_campuses_response = requests.get(f"{API_BASE}/admin/campuses", headers=headers)
all_campuses = all_campuses_response.json()
print(f"Total campuses: {len(all_campuses)}")
for c in all_campuses:
    print(f"  - {c['name']} (ID: {c['id']}, Location ID: {c['location_id']})")

# Test each location
print("\n3. Testing location filtering:")
for location_id in [1, 2, 3, 4]:
    print(f"\n  Location {location_id}:")
    url = f"{API_BASE}/admin/locations/{location_id}/campuses"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        campuses = response.json()
        print(f"    Found {len(campuses)} campus(es):")
        for c in campuses:
            print(f"      - {c['name']} (ID: {c['id']})")
    else:
        print(f"    Error {response.status_code}: {response.text}")
