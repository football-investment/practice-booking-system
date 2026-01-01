#!/usr/bin/env python3
"""
Test script for cascade inactivation feature.
Tests that when a location is inactivated, all its campuses are also inactivated.
"""

import requests
import json

API_BASE = "http://localhost:8000/api/v1"

def login():
    """Login as admin and get access token"""
    response = requests.post(
        f"{API_BASE}/auth/login",
        json={"email": "admin@lfa.com", "password": "admin123"}
    )
    response.raise_for_status()
    return response.json()["access_token"]

def get_location(token, location_id):
    """Get location details"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE}/admin/locations/{location_id}", headers=headers)
    response.raise_for_status()
    return response.json()

def get_campuses(token, location_id):
    """Get all campuses for a location"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_BASE}/admin/locations/{location_id}/campuses",
        params={"include_inactive": True},
        headers=headers
    )
    response.raise_for_status()
    return response.json()

def update_location(token, location_id, data):
    """Update location"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.put(
        f"{API_BASE}/admin/locations/{location_id}",
        json=data,
        headers=headers
    )
    response.raise_for_status()
    return response.json()

def main():
    print("=" * 80)
    print("CASCADE INACTIVATION TEST")
    print("=" * 80)

    # Login
    print("\n1. Logging in as admin...")
    token = login()
    print("   ✅ Logged in successfully")

    # Get current status
    location_id = 10  # LFA - Mindszent
    print(f"\n2. Getting current status of location_id={location_id}...")
    location = get_location(token, location_id)
    campuses = get_campuses(token, location_id)

    print(f"\n   Location: {location['name']}")
    print(f"   Location Status: {'ACTIVE' if location['is_active'] else 'INACTIVE'}")
    print(f"   Number of Campuses: {len(campuses)}")
    print("\n   Campuses:")
    for campus in campuses:
        status = "ACTIVE" if campus['is_active'] else "INACTIVE"
        print(f"     - {campus['name']}: {status}")

    # Test 1: Activate location first (if inactive)
    if not location['is_active']:
        print("\n3. Activating location first...")
        updated_location = update_location(token, location_id, {"is_active": True})
        print(f"   ✅ Location activated: {updated_location['name']}")

        campuses_after_activate = get_campuses(token, location_id)
        print("\n   Campuses after activation:")
        for campus in campuses_after_activate:
            status = "ACTIVE" if campus['is_active'] else "INACTIVE"
            print(f"     - {campus['name']}: {status}")

    # Test 2: Inactivate location (CASCADE should inactivate all campuses)
    print("\n4. Inactivating location (testing CASCADE)...")
    updated_location = update_location(token, location_id, {"is_active": False})
    print(f"   ✅ Location inactivated: {updated_location['name']}")

    # Check campuses after inactivation
    print("\n5. Checking campuses after location inactivation...")
    campuses_after = get_campuses(token, location_id)

    all_inactive = True
    print("\n   Campuses after location inactivation:")
    for campus in campuses_after:
        status = "ACTIVE" if campus['is_active'] else "INACTIVE"
        symbol = "✅" if not campus['is_active'] else "❌"
        print(f"     {symbol} {campus['name']}: {status}")
        if campus['is_active']:
            all_inactive = False

    # Result
    print("\n" + "=" * 80)
    print("TEST RESULTS")
    print("=" * 80)
    if all_inactive:
        print("✅ CASCADE INACTIVATION WORKS! All campuses were automatically inactivated.")
    else:
        print("❌ CASCADE INACTIVATION FAILED! Some campuses are still active.")
        print("   Expected: All campuses should be INACTIVE when location is INACTIVE")
        print("   Actual: Some campuses are still ACTIVE")
    print("=" * 80)

if __name__ == "__main__":
    main()
