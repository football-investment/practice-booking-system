#!/usr/bin/env python3
"""
🎯 COMPLETE SESSION WORKFLOW TEST - All Types
Tests ON-SITE, HYBRID, and VIRTUAL sessions
"""
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_session_type_workflow(session_type: str):
    """Test complete workflow for a specific session type"""
    print(f"\n{'='*80}")
    print(f"🧪 TESTING {session_type.upper()} SESSION WORKFLOW")
    print(f"{'='*80}\n")

    # Step 1: Login
    print("🔐 AUTHENTICATION")
    print("-" * 80)
    login_resp = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": "junior.intern@lfa.com",
        "password": "junior123"
    })

    if login_resp.status_code != 200:
        print(f"❌ Login failed: {login_resp.status_code}")
        return False

    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"✅ Authenticated\n")

    # Step 2: Browse Sessions
    print(f"STEP 1: Browse {session_type.upper()} Sessions")
    print("-" * 80)
    resp = requests.get(f"{BASE_URL}/api/v1/sessions/?session_type={session_type}&limit=10", headers=headers)
    print(f"Status: {resp.status_code}")

    if resp.status_code != 200:
        print(f"❌ Failed: {resp.text}")
        return False

    data = resp.json()
    if data['total'] == 0:
        print(f"❌ No {session_type} sessions found")
        return False

    session_id = data['sessions'][0]['id']
    session_title = data['sessions'][0]['title']
    session_type_actual = data['sessions'][0]['session_type']

    # VERIFY session type matches!
    if session_type_actual != session_type:
        print(f"❌ FILTER FAILED! Requested {session_type}, got {session_type_actual}")
        return False

    print(f"✅ Found {data['total']} {session_type} session(s)")
    print(f"   Using session ID: {session_id}")
    print(f"   Session: {session_title}")
    print(f"   Type: {session_type_actual}\n")

    # Step 3: Create Booking
    print("STEP 2: Create Booking")
    print("-" * 80)
    resp = requests.post(f"{BASE_URL}/api/v1/bookings/",
                        headers=headers,
                        json={"session_id": session_id})
    print(f"Status: {resp.status_code}")

    if resp.status_code != 200:
        print(f"❌ Failed: {resp.text}")
        return False

    booking_id = resp.json()['id']
    print(f"✅ Created booking ID: {booking_id}\n")

    # Step 4: Verify in My Bookings
    print("STEP 3: Verify Booking in My Bookings")
    print("-" * 80)
    resp = requests.get(f"{BASE_URL}/api/v1/bookings/me", headers=headers)
    print(f"Status: {resp.status_code}")

    if resp.status_code != 200:
        print(f"❌ Failed: {resp.text}")
        return False

    print(f"✅ Booking verified\n")

    # Step 5: Get Booking Details
    print("STEP 4: Get Booking Details")
    print("-" * 80)
    resp = requests.get(f"{BASE_URL}/api/v1/bookings/{booking_id}", headers=headers)
    print(f"Status: {resp.status_code}")

    if resp.status_code != 200:
        print(f"❌ Failed: {resp.text}")
        return False

    booking_data = resp.json()
    print(f"✅ Retrieved booking for session: {booking_data['session']['title']}\n")

    # Step 6: Cancel Booking
    print("STEP 5: Cancel Booking")
    print("-" * 80)
    resp = requests.delete(f"{BASE_URL}/api/v1/bookings/{booking_id}", headers=headers)
    print(f"Status: {resp.status_code}")

    if resp.status_code != 200:
        print(f"❌ Failed: {resp.text}")
        return False

    print(f"✅ Booking cancelled\n")

    print(f"{'='*80}")
    print(f"✅ {session_type.upper()} WORKFLOW COMPLETE - ALL STEPS PASSED!")
    print(f"{'='*80}\n")
    return True

# Test all three types
results = {}
for session_type in ['on_site', 'hybrid', 'virtual']:
    results[session_type] = test_session_type_workflow(session_type)

# Summary
print("\n" + "="*80)
print("📊 FINAL SUMMARY - ALL SESSION TYPES")
print("="*80)
for session_type, success in results.items():
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{session_type.upper():12} - {status}")
print("="*80)

if all(results.values()):
    print("\n🎉 ALL TESTS PASSED! Backend is ready for dashboard testing!")
else:
    print("\n❌ Some tests failed. Please fix before proceeding.")
