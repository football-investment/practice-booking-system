#!/usr/bin/env python3

import sys
import os
from datetime import datetime, timezone
from sqlalchemy.orm import Session

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.session import Session as SessionModel

def check_session_223():
    db = SessionLocal()
    
    try:
        # Find session 223
        session = db.query(SessionModel).filter(SessionModel.id == 223).first()
        if session:
            print(f"✅ Session 223 EXISTS:")
            print(f"   ID: {session.id}")
            print(f"   Title: {session.title}")
            print(f"   Start: {session.date_start}")
            print(f"   End: {session.date_end}")
            now_utc = datetime.now(timezone.utc)
            session_start_utc = session.date_start.replace(tzinfo=timezone.utc) if session.date_start.tzinfo is None else session.date_start
            print(f"   Status: {'Future' if session_start_utc > now_utc else 'Past/Current'}")
            print(f"   Time until start: {session_start_utc - now_utc}")
        else:
            print("❌ Session 223 NOT FOUND!")
        
        # Check first 5 sessions by start date
        sessions = db.query(SessionModel).order_by(SessionModel.date_start.asc()).limit(5).all()
        print(f"\n📅 First 5 sessions by date_start ASC:")
        for s in sessions:
            print(f"   ID: {s.id}, Start: {s.date_start}, Title: {s.title}")
        
        # Check total count
        total_sessions = db.query(SessionModel).count()
        print(f"\n📊 Total sessions in DB: {total_sessions}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_session_223()