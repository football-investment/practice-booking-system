#!/usr/bin/env python3
"""
Detailed test to inspect response structure
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# Login
login_response = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": "junior.intern@lfa.com", "password": "junior123"}
)
token = login_response.json()["access_token"]

# Get sessions
headers = {"Authorization": f"Bearer {token}"}
sessions_response = requests.get(
    f"{BASE_URL}/sessions/",
    headers=headers,
    params={"session_type": "on_site", "limit": 10}
)

print("=" * 80)
print("RAW RESPONSE JSON:")
print("=" * 80)
response_json = sessions_response.json()
print(json.dumps(response_json, indent=2))
print()
print("=" * 80)
print("KEYS IN RESPONSE:")
print("=" * 80)
print(list(response_json.keys()))
print()
print("=" * 80)
print("ANALYSIS:")
print("=" * 80)
print(f"Total: {response_json.get('total')}")
print(f"Page: {response_json.get('page')}")
print(f"Size: {response_json.get('size')}")
print(f"Sessions key: {'sessions' in response_json}")
if 'sessions' in response_json:
    print(f"Sessions length: {len(response_json['sessions'])}")
    print(f"Sessions content: {response_json['sessions']}")
print("=" * 80)
