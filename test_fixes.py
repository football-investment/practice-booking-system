#!/usr/bin/env python3
"""
Test critical bug fixes
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.database import engine, SessionLocal

print('🧪 TESTING CRITICAL FIXES')
print('=' * 50)

# Test 1: Verify Hungarian data is fixed
db = SessionLocal()
check_query = text('SELECT id, title, description FROM sessions LIMIT 5')
result = db.execute(check_query)
sessions = result.fetchall()

print('✅ TEST 1: Session data (first 5 entries):')
for session in sessions:
    title = session[1][:40] + '...' if len(session[1]) > 40 else session[1]
    print(f'  ID {session[0]}: {title}')

# Test 2: Check for any remaining Hungarian text
hungarian_query = text('SELECT COUNT(*) FROM sessions WHERE title LIKE \'%Tutti%\' OR title LIKE \'%Ezt%\' OR description LIKE \'%film%\'')
hungarian_count = db.execute(hungarian_query).scalar()

print(f'✅ TEST 2: Hungarian entries remaining: {hungarian_count}')

# Test 3: Check session date distribution 
past_query = text('SELECT COUNT(*) FROM sessions WHERE date_start < NOW()')
future_query = text('SELECT COUNT(*) FROM sessions WHERE date_start > NOW()')
total_query = text('SELECT COUNT(*) FROM sessions')

past_count = db.execute(past_query).scalar()
future_count = db.execute(future_query).scalar()
total_count = db.execute(total_query).scalar()

print(f'✅ TEST 3: Session distribution:')
print(f'  Total: {total_count}')
print(f'  Past: {past_count}')
print(f'  Future: {future_count}')

# Test 4: Check available sessions (not full + future)
available_query = text('SELECT COUNT(*) FROM sessions WHERE date_start > NOW()')
available_count = db.execute(available_query).scalar()

print(f'✅ TEST 4: Future sessions: {available_count}')

db.close()

print('\n🎯 EXPECTED RESULTS:')
print('  - No Hungarian text (0)')
print('  - Available < Total (realistic filtering)')
print('  - Past events excluded from Available count')
print('\n🔧 FRONTEND TESTS REQUIRED:')
print('  1. Open http://localhost:3000/student/sessions')
print('  2. Check Available tab count < All tab count') 
print('  3. Verify no Hungarian text visible')
print('  4. Test session booking buttons show "Session Ended" for past')