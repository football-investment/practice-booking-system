#!/usr/bin/env python3

import sys
import os
from datetime import datetime, timezone
from sqlalchemy.orm import Session

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.session import Session as SessionModel

def find_session_223():
    db = SessionLocal()
    
    try:
        now_utc = datetime.now(timezone.utc)
        now_naive = now_utc.replace(tzinfo=None)
        
        print(f"Looking for session 223 in sorted list...")
        print(f"Current time: {now_naive}")
        
        # Get ALL sessions with the exact same ordering as API
        all_sessions = db.query(SessionModel).order_by(
            (SessionModel.date_start > now_naive).desc(),  
            SessionModel.date_start.asc()                  
        ).all()
        
        print(f"\nAll {len(all_sessions)} sessions:")
        found_position = None
        
        for i, session in enumerate(all_sessions):
            is_future = session.date_start > now_naive
            status = "🟢 FUTURE" if is_future else "🔴 PAST"
            
            if session.id == 223:
                found_position = i + 1
                print(f"   {i+1}. ID: {session.id}, Start: {session.date_start}, {status}, Title: {session.title} <<<< SESSION 223 HERE!")
            else:
                # Only show first 10 and around session 223
                if i < 10 or (found_position and abs(i + 1 - found_position) <= 2):
                    print(f"   {i+1}. ID: {session.id}, Start: {session.date_start}, {status}, Title: {session.title}")
                elif i == 10 and (not found_position or found_position > 15):
                    print("   ... (showing only relevant sessions)")
        
        if found_position:
            print(f"\n🎯 Session 223 is at position {found_position} out of {len(all_sessions)}")
            print(f"   Will {'appear' if found_position <= 50 else 'NOT appear'} in first 50 results")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    find_session_223()