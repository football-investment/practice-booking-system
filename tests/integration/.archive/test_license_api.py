#!/usr/bin/env python3
"""Test API license data display"""

import requests
import json

# Login
response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "admin@lfa.com", "password": "admin123"}
)
token = response.json()["access_token"]

# Get users
response = requests.get(
    "http://localhost:8000/api/v1/users/?limit=100",
    headers={"Authorization": f"Bearer {token}"}
)
data = response.json()
users = data.get('users', data) if isinstance(data, dict) else data

# Find Grandmaster
grandmaster = next((u for u in users if u.get('email') == 'grandmaster@lfa.com'), None)
if grandmaster:
    print("🔍 GRANDMASTER:")
    print(f"  Email: {grandmaster.get('email')}")
    print(f"  Licenses in API: {len(grandmaster.get('licenses', []))}")
    licenses = grandmaster.get('licenses', [])
    if licenses:
        print(f"  First 3 licenses: {licenses[:3]}")
        # Count by type
        license_counts = {}
        for lic in licenses:
            spec_type = lic.get('specialization_type', 'Unknown')
            license_counts[spec_type] = license_counts.get(spec_type, 0) + 1
        print(f"  License breakdown: {license_counts}")
    else:
        print("  ❌ NO LICENSES RETURNED!")
else:
    print("❌ Grandmaster NOT FOUND!")

print()

# Find P3T1K3
p3t1k3 = next((u for u in users if u.get('email') == 'p3t1k3@f1stteam.hu'), None)
if p3t1k3:
    print("🔍 P3T1K3:")
    print(f"  Email: {p3t1k3.get('email')}")
    print(f"  Licenses in API: {len(p3t1k3.get('licenses', []))}")
    licenses = p3t1k3.get('licenses', [])
    if licenses:
        print(f"  License details: {licenses}")
    else:
        print("  ❌ NO LICENSES RETURNED!")
else:
    print("❌ P3T1K3 NOT FOUND!")
