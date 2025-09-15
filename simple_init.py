#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Próbáljuk meg különböző módokon importálni
    print("Trying to import database components...")
    
    from app.database import engine, SessionLocal, Base
    print("✅ Successfully imported from app.database")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    try:
        from app.database import engine, SessionLocal
        from app.models.base import Base
        print("✅ Successfully imported Base from app.models.base")
    except ImportError as e2:
        print(f"❌ Second import error: {e2}")
        sys.exit(1)

# Create tables
print("Creating database tables...")
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created!")
except Exception as e:
    print(f"❌ Error creating tables: {e}")
    sys.exit(1)

print("🎯 Basic database structure created. Now check if login works:")
print("curl -X POST 'http://localhost:8000/api/v1/auth/login' -H 'Content-Type: application/json' -d '{\"email\": \"admin@yourcompany.com\", \"password\": \"admin123\"}'")
