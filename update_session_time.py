#!/usr/bin/env python3

import sys
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.session import Session as SessionModel

def update_session_time():
    db = SessionLocal()
    
    try:
        # Find session 223
        session = db.query(SessionModel).filter(SessionModel.id == 223).first()
        if not session:
            print("❌ Session 223 not found!")
            return
        
        print(f"✅ Found session: {session.title}")
        
        # Current time and new session time (7:45 - 8 minutes from now)
        now_utc = datetime.now(timezone.utc)
        
        # Set to 7:45 (8 minutes from current time which should be around 7:37)
        session_start = now_utc + timedelta(minutes=8)
        session_start = session_start.replace(minute=45, second=0, microsecond=0)  # Exactly 7:45
        session_end = session_start + timedelta(hours=1)  # 1 hour duration
        
        print(f"Current time: {now_utc}")
        print(f"New start time: {session_start}")
        print(f"New end time: {session_end}")
        
        # Update session times (store as naive UTC in database)
        session.date_start = session_start.replace(tzinfo=None)
        session.date_end = session_end.replace(tzinfo=None)
        
        db.commit()
        
        print(f"✅ Session 223 updated successfully!")
        print(f"   Start: {session.date_start} (UTC, stored as naive)")
        print(f"   End: {session.date_end} (UTC, stored as naive)")
        print(f"   Starts in: {session_start - now_utc}")
        
        print("\n🎯 Session will be LIVE in ~8 minutes at 7:45!")
        
    except Exception as e:
        print(f"❌ Error updating session: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_session_time()