#!/usr/bin/env python3
"""
Complete test of booking functionality after all fixes
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.database import engine, SessionLocal

print('🧪 COMPLETE BOOKING FUNCTIONALITY TEST')
print('=' * 50)

db = SessionLocal()

# Test 1: Verify cancelled booking exists but should be ignored
cancelled_booking_query = text("""
    SELECT b.id, b.session_id, b.status, b.user_id, u.email
    FROM bookings b
    JOIN users u ON b.user_id = u.id
    WHERE b.session_id = 169 
    AND u.email = 'alex.johnson@student.devstudio.com'
    AND b.status = 'CANCELLED'
""")

result = db.execute(cancelled_booking_query)
cancelled_booking = result.fetchone()

print('✅ TEST 1: Cancelled booking verification:')
if cancelled_booking:
    print(f'  ✅ Found cancelled booking ID {cancelled_booking[0]} for session 169')
    print(f'  ✅ Status: {cancelled_booking[2]} - should be IGNORED by both frontend and backend')
else:
    print('  ❌ No cancelled booking found - test may not be valid')

# Test 2: Check if user has any ACTIVE bookings for session 169
active_booking_query = text("""
    SELECT b.id, b.session_id, b.status
    FROM bookings b
    JOIN users u ON b.user_id = u.id
    WHERE b.session_id = 169 
    AND u.email = 'alex.johnson@student.devstudio.com'
    AND b.status != 'CANCELLED'
""")

result = db.execute(active_booking_query)
active_booking = result.fetchone()

print(f'\n✅ TEST 2: Active booking check for session 169:')
if active_booking:
    print(f'  ❌ Found active booking ID {active_booking[0]} - this would block new booking')
    print(f'  ❌ Status: {active_booking[2]}')
else:
    print('  ✅ No active bookings found - user should be able to book')

# Test 3: Check session capacity and availability
session_check_query = text("""
    SELECT s.id, s.title, s.capacity, s.date_start,
           COUNT(b.id) FILTER (WHERE b.status = 'CONFIRMED') as confirmed_bookings
    FROM sessions s
    LEFT JOIN bookings b ON s.id = b.session_id
    WHERE s.id = 169
    GROUP BY s.id, s.title, s.capacity, s.date_start
""")

result = db.execute(session_check_query)
session_info = result.fetchone()

print(f'\n✅ TEST 3: Session 169 availability:')
if session_info:
    print(f'  Session: {session_info[1]}')
    print(f'  Capacity: {session_info[2]}')
    print(f'  Confirmed bookings: {session_info[4]}')
    print(f'  Start: {session_info[3]}')
    
    if session_info[4] < session_info[2]:
        print(f'  ✅ Available spots: {session_info[2] - session_info[4]}')
    else:
        print('  ❌ Session is full')

db.close()

print('\n🎯 EXPECTED RESULTS:')
print('  Frontend console should show:')
print('    - "Session ID we are looking for: 169"')
print('    - "Found active booking (excluding cancelled): null" (or undefined)')
print('    - "All bookings for this session: [cancelled booking array]"')
print()
print('  Backend should:')
print('    - NOT find active bookings (cancelled excluded)')
print('    - Allow new booking to proceed')
print('    - Return HTTP 201 (not HTTP 400)')

print('\n🔧 MANUAL TEST STEPS:')
print('  1. Open http://localhost:3000/student/sessions/169')
print('  2. Should show "Available for Booking"')
print('  3. Click "Book This Session"')
print('  4. Should show success message')
print('  5. Should NOT show HTTP 400 error')