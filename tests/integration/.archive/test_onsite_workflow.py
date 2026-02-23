#!/usr/bin/env python3
"""
🎯 ON-SITE SESSION COMPLETE WORKFLOW TEST
==========================================

Tests the full student journey for ON-SITE sessions:
1. Browse ON-SITE Sessions
2. Get Session Details
3. Create Booking
4. Verify Booking
5. Get Booking Details
6. Cancel Booking
7. Verify Cancellation
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

def print_step(step_num, title):
    print(f"\n{'='*80}")
    print(f"STEP {step_num}: {title}")
    print(f"{'='*80}")

def print_result(success, message):
    emoji = "✅" if success else "❌"
    print(f"{emoji} {message}")

# Login
print("="*80)
print("🔐 AUTHENTICATION")
print("="*80)
login_response = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": "junior.intern@lfa.com", "password": "junior123"}
)
if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    exit(1)

token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print_result(True, "Authenticated as junior.intern@lfa.com (INTERNSHIP)")

# Test data
session_id = None
booking_id = None

# STEP 1: Browse ON-SITE Sessions
print_step(1, "Browse ON-SITE Sessions")
response = requests.get(
    f"{BASE_URL}/sessions/",
    headers=headers,
    params={"session_type": "on_site", "limit": 10}
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    sessions = data.get('sessions', [])
    print_result(len(sessions) > 0, f"Found {len(sessions)} sessions")
    if len(sessions) > 0:
        session_id = sessions[0]['id']
        print(f"   Using session ID: {session_id}")
        print(f"   Session: {sessions[0]['title']}")
else:
    print_result(False, f"Failed with status {response.status_code}")
    print(f"Response: {response.text}")

# STEP 2: Get Session Details
print_step(2, "Get Session Details")
if session_id:
    response = requests.get(
        f"{BASE_URL}/sessions/{session_id}",
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        session = response.json()
        print_result(True, f"Retrieved session: {session.get('title')}")
        print(f"   Capacity: {session.get('capacity')}")
        print(f"   Current bookings: {session.get('current_bookings', 0)}")
    else:
        print_result(False, f"Failed with status {response.status_code}")
        print(f"Response: {response.text}")
else:
    print_result(False, "Skipped - no session_id")

# STEP 3: Create Booking
print_step(3, "Create Booking")
if session_id:
    response = requests.post(
        f"{BASE_URL}/bookings/",
        headers=headers,
        json={"session_id": session_id}
    )
    print(f"Status: {response.status_code}")
    if response.status_code in [200, 201]:
        booking = response.json()
        booking_id = booking.get('id')
        print_result(True, f"Created booking ID: {booking_id}")
        print(f"   Status: {booking.get('status')}")
    else:
        print_result(False, f"Failed with status {response.status_code}")
        print(f"Response: {response.text}")
else:
    print_result(False, "Skipped - no session_id")

# STEP 4: Verify Booking in My Bookings
print_step(4, "Verify Booking in My Bookings")
response = requests.get(
    f"{BASE_URL}/bookings/me",
    headers=headers
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    bookings = response.json()
    if isinstance(bookings, list):
        found = any(b.get('id') == booking_id for b in bookings if booking_id)
        print_result(found or len(bookings) > 0, f"Found {len(bookings)} booking(s)")
    elif isinstance(bookings, dict):
        items = bookings.get('bookings', bookings.get('items', []))
        found = any(b.get('id') == booking_id for b in items if booking_id)
        print_result(found or len(items) > 0, f"Found {len(items)} booking(s)")
else:
    print_result(False, f"Failed with status {response.status_code}")
    print(f"Response: {response.text}")

# STEP 5: Get Booking Details
print_step(5, "Get Booking Details")
if booking_id:
    response = requests.get(
        f"{BASE_URL}/bookings/{booking_id}",
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        booking = response.json()
        print_result(True, f"Retrieved booking for session: {booking.get('session', {}).get('title', 'N/A')}")
    else:
        print_result(False, f"Failed with status {response.status_code}")
        print(f"Response: {response.text}")
else:
    print_result(False, "Skipped - no booking_id")

# STEP 6: Cancel Booking
print_step(6, "Cancel Booking")
if booking_id:
    response = requests.delete(
        f"{BASE_URL}/bookings/{booking_id}",
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code in [200, 204]:
        print_result(True, "Booking cancelled successfully")
    else:
        print_result(False, f"Failed with status {response.status_code}")
        print(f"Response: {response.text}")
else:
    print_result(False, "Skipped - no booking_id")

# STEP 7: Verify Cancellation
print_step(7, "Verify Cancellation")
response = requests.get(
    f"{BASE_URL}/bookings/me",
    headers=headers
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    bookings = response.json()
    if isinstance(bookings, list):
        found = any(b.get('id') == booking_id for b in bookings if booking_id)
        print_result(not found, f"Booking removed (found {len(bookings)} remaining)")
    elif isinstance(bookings, dict):
        items = bookings.get('bookings', bookings.get('items', []))
        found = any(b.get('id') == booking_id for b in items if booking_id)
        print_result(not found, f"Booking removed (found {len(items)} remaining)")
else:
    print_result(False, f"Failed with status {response.status_code}")

print("\n" + "="*80)
print("🏁 ON-SITE WORKFLOW TEST COMPLETE")
print("="*80)
