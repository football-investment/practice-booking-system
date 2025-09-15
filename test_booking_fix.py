#!/usr/bin/env python3
"""
Test booking functionality fixes
"""

import sys
import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.database import engine, SessionLocal

print('🧪 TESTING BOOKING FIXES')
print('=' * 50)

# Test 1: Check if we have future sessions available for booking
db = SessionLocal()

future_sessions_query = text("""
    SELECT s.id, s.title, s.date_start, s.capacity,
           COALESCE(COUNT(b.id), 0) as current_bookings
    FROM sessions s
    LEFT JOIN bookings b ON s.id = b.session_id AND b.status = 'CONFIRMED'
    WHERE s.date_start > NOW() 
    GROUP BY s.id, s.title, s.date_start, s.capacity
    ORDER BY s.date_start 
    LIMIT 3
""")

result = db.execute(future_sessions_query)
future_sessions = result.fetchall()

print('✅ TEST 1: Future sessions available for booking:')
for session in future_sessions:
    availability = "AVAILABLE" if session[4] < session[3] else "FULL"
    print(f'  ID {session[0]}: {session[1][:30]}... | Start: {session[2]} | {session[4]}/{session[3]} | {availability}')

if len(future_sessions) == 0:
    print('  ❌ No future sessions found! Creating test session...')
    # Create a test session for tomorrow
    from datetime import datetime, timedelta
    tomorrow = datetime.now() + timedelta(days=1)
    
    create_session_query = text("""
        INSERT INTO sessions (title, description, date_start, date_end, capacity, semester_id, location, sport_type, level, instructor_name, mode)
        VALUES ('Test Booking Session', 'Session for testing booking functionality', :start_date, :end_date, 5, 18, 'Test Location', 'Testing', 'All Levels', 'Test Instructor', 'offline')
        RETURNING id, title, date_start
    """)
    
    end_time = tomorrow + timedelta(hours=2)
    result = db.execute(create_session_query, {
        'start_date': tomorrow,
        'end_date': end_time
    })
    new_session = result.fetchone()
    db.commit()
    print(f'  ✅ Created test session: ID {new_session[0]} - {new_session[1]} at {new_session[2]}')

# Test 2: Check for existing user bookings
user_bookings_query = text("""
    SELECT b.id, b.session_id, s.title, b.status, b.created_at
    FROM bookings b
    JOIN sessions s ON b.session_id = s.id
    JOIN users u ON b.user_id = u.id
    WHERE u.email = 'alex.johnson@student.devstudio.com'
    ORDER BY b.created_at DESC
    LIMIT 5
""")

result = db.execute(user_bookings_query)
user_bookings = result.fetchall()

print(f'\n✅ TEST 2: Alex\'s recent bookings ({len(user_bookings)} found):')
for booking in user_bookings:
    print(f'  Booking #{booking[0]}: Session {booking[1]} - {booking[2][:30]}... | Status: {booking[3]} | Created: {booking[4]}')

db.close()

print('\n🎯 EXPECTED RESULTS:')
print('  - Future sessions available for booking')
print('  - User bookings properly tracked')
print('  - No TypeError in frontend console')
print('  - No HTTP 400 errors during booking')

print('\n🔧 MANUAL TESTS REQUIRED:')
print('  1. Open http://localhost:3000/student/sessions')
print('  2. Click on a future session to view details')
print('  3. Try booking the session')
print('  4. Check browser console for no TypeError')
print('  5. Verify booking success message')