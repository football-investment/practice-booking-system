#!/usr/bin/env python3

import sys
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.session import Session as SessionModel

def update_live_session():
    db = SessionLocal()
    
    try:
        # Find the live session we created (ID 223)
        session = db.query(SessionModel).filter(SessionModel.id == 223).first()
        if not session:
            print("❌ Live session not found!")
            return
        
        print(f"✅ Found session: {session.title}")
        
        # Set new times - starts at 7:30 (7 minutes from now), ends at 8:30
        now = datetime.now(timezone.utc)
        session_start = now + timedelta(minutes=7)  # Start in 7 minutes (7:30)
        session_end = session_start + timedelta(hours=1)  # 1 hour session
        
        # Update the session times
        session.date_start = session_start
        session.date_end = session_end
        
        db.commit()
        
        print(f"✅ Updated session times:")
        print(f"   Start time: {session_start} (in 7 minutes)")
        print(f"   End time: {session_end}")
        print(f"   Current time: {now}")
        print(f"   Status: Upcoming (will be live in 7 minutes)")
        
        print("\n🎯 Session updated successfully!")
        print("   Session will now appear in 'Upcoming Sessions'")
        print("   Admin can manage participants without restrictions")
        
    except Exception as e:
        print(f"❌ Error updating session: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_live_session()