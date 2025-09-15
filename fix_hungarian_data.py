#!/usr/bin/env python3
"""
Fix Hungarian test data in PostgreSQL database
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.database import engine, SessionLocal

def fix_hungarian_data():
    """Fix Hungarian data in sessions table"""
    
    print("🚨 FIXING HUNGARIAN TEST DATA")
    print("=" * 50)
    
    try:
        # Create database session
        db = SessionLocal()
        
        # Check for Hungarian entries
        check_query = text("""
            SELECT id, title, description FROM sessions 
            WHERE title LIKE '%Tutti%' 
            OR title LIKE '%Ezt%' 
            OR description LIKE '%film%'
            OR description LIKE '%leírás%'
        """)
        
        result = db.execute(check_query)
        entries = result.fetchall()
        
        print(f"Found {len(entries)} Hungarian entries:")
        for entry in entries:
            print(f"  ID: {entry[0]}, Title: {entry[1]}, Description: {entry[2][:50]}...")
        
        if len(entries) == 0:
            print("✅ No Hungarian data found - already clean!")
            return True
        
        # Fix Hungarian entries with professional English data
        fix_queries = [
            text("""
                UPDATE sessions 
                SET title = 'Advanced Football Training',
                    description = 'Tactical drills, match preparation, and advanced techniques for experienced players',
                    sport_type = 'Football',
                    level = 'Advanced',
                    instructor_name = 'Coach Martinez'
                WHERE title LIKE '%Tutti%' OR title LIKE '%Ezt%'
            """),
            
            text("""
                UPDATE sessions 
                SET title = 'Beginner Basketball Fundamentals',
                    description = 'Basic skills, shooting techniques, and court positioning for new players',
                    sport_type = 'Basketball', 
                    level = 'Beginner',
                    instructor_name = 'Coach Johnson'
                WHERE description LIKE '%film%' OR description LIKE '%leírás%'
            """),
            
            # Additional fallback fix for any remaining Hungarian text
            text("""
                UPDATE sessions 
                SET title = 'Intermediate Tennis Clinic',
                    description = 'Serve technique, volleys, and match tactics for developing players',
                    sport_type = 'Tennis',
                    level = 'Intermediate',
                    instructor_name = 'Pro Williams'
                WHERE title LIKE '%játszd%' OR description LIKE '%játszd%'
            """)
        ]
        
        for query in fix_queries:
            result = db.execute(query)
            print(f"✅ Fixed {result.rowcount} entries")
        
        db.commit()
        
        # Verify fix
        verify_result = db.execute(check_query)
        remaining = verify_result.fetchall()
        
        if len(remaining) == 0:
            print("🎉 SUCCESS - All Hungarian data fixed!")
        else:
            print(f"⚠️ WARNING - {len(remaining)} Hungarian entries still remain")
            for entry in remaining:
                print(f"  Remaining: {entry[1]}")
        
        db.close()
        return len(remaining) == 0
        
    except Exception as e:
        print(f"❌ Fix failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_hungarian_data()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}")