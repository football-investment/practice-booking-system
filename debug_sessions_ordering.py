#!/usr/bin/env python3

import sys
import os
from datetime import datetime, timezone
from sqlalchemy.orm import Session

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.session import Session as SessionModel

def debug_sessions_ordering():
    db = SessionLocal()
    
    try:
        now = datetime.now(timezone.utc)
        print(f"Current time: {now}")
        
        # Test the exact same ordering as in the API
        sessions = db.query(SessionModel).order_by(
            (SessionModel.date_start > now).desc(),  # Future sessions first
            SessionModel.date_start.asc()            # Then by start time
        ).limit(10).all()
        
        print(f"\nFirst 10 sessions with API ordering:")
        session_223_found = False
        for i, session in enumerate(sessions):
            is_future = session.date_start.replace(tzinfo=timezone.utc) > now if session.date_start.tzinfo is None else session.date_start > now
            status = "🟢 FUTURE" if is_future else "🔴 PAST"
            print(f"   {i+1}. ID: {session.id}, Start: {session.date_start}, {status}, Title: {session.title}")
            
            if session.id == 223:
                session_223_found = True
                print(f"      🎯 >>> SESSION 223 FOUND AT POSITION {i+1}! <<<")
        
        if not session_223_found:
            print(f"\n❌ Session 223 NOT in first 10 results")
            
            # Find where session 223 is in the full list
            all_sessions = db.query(SessionModel).order_by(
                (SessionModel.date_start > now).desc(),
                SessionModel.date_start.asc()
            ).all()
            
            for i, session in enumerate(all_sessions):
                if session.id == 223:
                    print(f"🔍 Session 223 found at position: {i+1} out of {len(all_sessions)}")
                    break
        else:
            print(f"\n✅ Session 223 IS in first 10 results")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_sessions_ordering()