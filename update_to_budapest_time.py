#!/usr/bin/env python3

import sys
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.session import Session as SessionModel

def update_to_budapest_time():
    db = SessionLocal()
    
    try:
        # Find session 223
        session = db.query(SessionModel).filter(SessionModel.id == 223).first()
        if not session:
            print("❌ Session 223 not found!")
            return
        
        print(f"✅ Found session: {session.title}")
        
        # Current time in UTC
        now_utc = datetime.now(timezone.utc)
        
        # Budapest is UTC+1 in winter, UTC+2 in summer (CET/CEST)
        # September is CEST (UTC+2), so 9:00 AM Budapest = 7:00 AM UTC
        budapest_9am_utc = now_utc.replace(hour=7, minute=0, second=0, microsecond=0)
        
        # If it's already past 7:00 AM today, schedule for tomorrow
        if budapest_9am_utc <= now_utc:
            budapest_9am_utc = budapest_9am_utc + timedelta(days=1)
        
        session_start = budapest_9am_utc
        session_end = session_start + timedelta(hours=1)  # 1 hour duration
        
        print(f"Current time UTC: {now_utc}")
        print(f"New start time UTC: {session_start} (9:00 AM Budapest)")
        print(f"New end time UTC: {session_end} (10:00 AM Budapest)")
        
        # Update session times (store as naive UTC in database)
        session.date_start = session_start.replace(tzinfo=None)
        session.date_end = session_end.replace(tzinfo=None)
        
        db.commit()
        
        print(f"✅ Session 223 updated to Budapest time!")
        print(f"   Start: {session.date_start} UTC (9:00 AM Budapest)")
        print(f"   End: {session.date_end} UTC (10:00 AM Budapest)")
        
        time_until = session_start - now_utc
        if time_until.total_seconds() > 0:
            print(f"   Starts in: {time_until}")
        else:
            print(f"   Started {-time_until} ago")
        
    except Exception as e:
        print(f"❌ Error updating session: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_to_budapest_time()