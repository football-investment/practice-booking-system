#!/usr/bin/env python3

import sys
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.user import User
from app.models.session import Session as SessionModel, SessionMode
from app.models.booking import Booking, BookingStatus
from app.models.semester import Semester
from app.models.group import Group

def create_live_session():
    db = SessionLocal()
    
    try:
        # Find Alex Johnson
        user = db.query(User).filter(User.email == "alex.johnson@student.devstudio.com").first()
        if not user:
            print("❌ Alex Johnson user not found!")
            return
        
        print(f"✅ Found user: {user.name} ({user.email})")
        
        # Get current semester
        current_semester = db.query(Semester).filter(Semester.is_active == True).first()
        if not current_semester:
            print("❌ No active semester found!")
            return
            
        print(f"✅ Found active semester: {current_semester.name}")
        
        # Create current time and session times
        now = datetime.now(timezone.utc)
        session_start = now - timedelta(minutes=15)  # Started 15 minutes ago
        session_end = now + timedelta(minutes=45)    # Ends in 45 minutes
        
        # Create a live session
        live_session = SessionModel(
            title="Live Football Training Session",
            description="Current live training session for testing live check-in functionality",
            date_start=session_start,
            date_end=session_end,
            mode=SessionMode.OFFLINE,
            capacity=20,
            location="Main Football Field",
            sport_type="Football",
            level="Intermediate",
            instructor_name="Coach Martinez",
            semester_id=current_semester.id
        )
        
        db.add(live_session)
        db.flush()  # Get the session ID
        
        print(f"✅ Created live session: {live_session.title}")
        print(f"   Session ID: {live_session.id}")
        print(f"   Start time: {session_start}")
        print(f"   End time: {session_end}")
        print(f"   Current time: {now}")
        
        # Create a confirmed booking for Alex
        booking = Booking(
            user_id=user.id,
            session_id=live_session.id,
            status=BookingStatus.CONFIRMED,
            notes="Live session for testing check-in"
        )
        
        db.add(booking)
        db.commit()
        
        print(f"✅ Created confirmed booking for Alex Johnson")
        print(f"   Booking ID: {booking.id}")
        print(f"   Status: {booking.status.value}")
        
        print("\n🎯 Live session created successfully!")
        print("   Alex can now test the live check-in functionality")
        
    except Exception as e:
        print(f"❌ Error creating live session: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_live_session()