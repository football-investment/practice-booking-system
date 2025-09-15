#!/usr/bin/env python3
"""
Add enhanced fields to Session model for better UI display
"""

import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.database import engine, SessionLocal

def enhance_session_model():
    """Add new fields to sessions table for better UI"""
    
    print("🚀 ENHANCING SESSION MODEL")
    print("=" * 50)
    
    try:
        # Create database session
        db = SessionLocal()
        
        # Add new columns if they don't exist
        enhancements = [
            "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS sport_type VARCHAR(100) DEFAULT 'General'",
            "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS level VARCHAR(50) DEFAULT 'All Levels'",
            "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS instructor_name VARCHAR(200)"
        ]
        
        for sql in enhancements:
            try:
                db.execute(text(sql))
                print(f"✅ {sql}")
            except Exception as e:
                print(f"ℹ️ Column may already exist: {e}")
        
        db.commit()
        
        # Update existing sessions with enhanced data
        update_queries = [
            "UPDATE sessions SET sport_type = 'Football', level = 'Advanced', instructor_name = 'Coach Martinez' WHERE title LIKE '%Football%'",
            "UPDATE sessions SET sport_type = 'Basketball', level = 'Beginner', instructor_name = 'Coach Johnson' WHERE title LIKE '%Basketball%'", 
            "UPDATE sessions SET sport_type = 'Tennis', level = 'Intermediate', instructor_name = 'Pro Williams' WHERE title LIKE '%Tennis%'",
            "UPDATE sessions SET sport_type = 'Swimming', level = 'All Levels', instructor_name = 'Coach Davis' WHERE title LIKE '%Swimming%'",
            "UPDATE sessions SET sport_type = 'Boxing', level = 'Advanced', instructor_name = 'Coach Thompson' WHERE title LIKE '%Boxing%'",
            "UPDATE sessions SET sport_type = 'Programming', level = 'Beginner', instructor_name = 'Dr. Johnson' WHERE title LIKE '%JavaScript%'",
            "UPDATE sessions SET sport_type = 'Programming', level = 'Intermediate', instructor_name = 'Dr. Johnson' WHERE title LIKE '%CSS%'",
            "UPDATE sessions SET sport_type = 'Programming', level = 'Intermediate', instructor_name = 'Dr. Johnson' WHERE title LIKE '%React%'",
            "UPDATE sessions SET sport_type = 'Programming', level = 'Advanced', instructor_name = 'Dr. Johnson' WHERE title LIKE '%Node%'"
        ]
        
        for sql in update_queries:
            try:
                db.execute(text(sql))
                print(f"✅ Updated session data")
            except Exception as e:
                print(f"ℹ️ Update issue: {e}")
        
        db.commit()
        db.close()
        
        print("\n🎉 SESSION MODEL ENHANCEMENT COMPLETED!")
        return True
        
    except Exception as e:
        print(f"❌ Enhancement failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = enhance_session_model()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}")