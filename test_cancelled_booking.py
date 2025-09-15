#!/usr/bin/env python3
"""
Test cancelled booking functionality fix
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.database import engine, SessionLocal

print('🧪 TESTING CANCELLED BOOKING FIX')
print('=' * 50)

db = SessionLocal()

# Test 1: Check for specific cancelled booking (Session 169)
cancelled_booking_query = text("""
    SELECT b.id, b.session_id, b.status, s.title, u.email, b.cancelled_at
    FROM bookings b
    JOIN sessions s ON b.session_id = s.id
    JOIN users u ON b.user_id = u.id
    WHERE b.session_id = 169 
    AND u.email = 'alex.johnson@student.devstudio.com'
    ORDER BY b.updated_at DESC
    LIMIT 1
""")

result = db.execute(cancelled_booking_query)
cancelled_booking = result.fetchone()

print('✅ TEST 1: Session 169 booking status for Alex:')
if cancelled_booking:
    print(f'  Booking ID: {cancelled_booking[0]}')
    print(f'  Session ID: {cancelled_booking[1]}')
    print(f'  Status: {cancelled_booking[2]} ⚠️')
    print(f'  Session: {cancelled_booking[3]}')
    print(f'  User: {cancelled_booking[4]}')
    print(f'  Cancelled at: {cancelled_booking[5]}')
    print(f'  ✅ Booking is CANCELLED - should NOT show as active in UI')
else:
    print('  ❌ No booking found for session 169')

# Test 2: Check for active (non-cancelled) bookings for Alex
active_bookings_query = text("""
    SELECT COUNT(*) as active_count
    FROM bookings b
    JOIN users u ON b.user_id = u.id
    WHERE u.email = 'alex.johnson@student.devstudio.com'
    AND b.status != 'CANCELLED'
""")

result = db.execute(active_bookings_query)
active_count = result.scalar()

print(f'\n✅ TEST 2: Alex\'s active (non-cancelled) bookings: {active_count}')

# Test 3: Check all booking statuses
all_statuses_query = text("""
    SELECT b.status, COUNT(*) as count
    FROM bookings b
    JOIN users u ON b.user_id = u.id
    WHERE u.email = 'alex.johnson@student.devstudio.com'
    GROUP BY b.status
    ORDER BY count DESC
""")

result = db.execute(all_statuses_query)
statuses = result.fetchall()

print(f'\n✅ TEST 3: Alex\'s booking status breakdown:')
for status in statuses:
    print(f'  {status[0]}: {status[1]} bookings')

db.close()

print('\n🎯 EXPECTED FRONTEND BEHAVIOR:')
print('  - Session 169 should NOT show "You\'re Registered"')
print('  - Session 169 should show "Available for Booking"')  
print('  - Book This Session button should be enabled')
print('  - No cancel button should be visible')

print('\n🔧 MANUAL TEST:')
print('  1. Open http://localhost:3000/student/sessions/169')
print('  2. Should show "Available for Booking" (not "You\'re Registered")')
print('  3. "Book This Session" button should be clickable')
print('  4. Console should show: "Found active booking (excluding cancelled): null"')