#!/usr/bin/env python3
"""
Create Sessions and Events for 1-Week Testing Period
"""

import sys
import os
from datetime import datetime, timedelta, timezone

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db
from app.models import User, UserRole, Session, Semester, Booking, BookingStatus

def create_sessions_and_events():
    """Create sessions and events for testing"""
    db = next(get_db())
    
    try:
        print("🚀 Creating Training Sessions and Events")
        print("=" * 40)
        
        # Get active semester and instructor
        active_semester = db.query(Semester).filter(Semester.is_active == True).first()
        instructor = db.query(User).filter(User.role == UserRole.INSTRUCTOR).first()
        students = db.query(User).filter(User.role == UserRole.STUDENT).limit(15).all()
        
        if not active_semester or not instructor:
            print("❌ Missing semester or instructor!")
            return
        
        print(f"📖 Using semester: {active_semester.name}")
        print(f"🎓 Using instructor: {instructor.name}")
        print(f"👥 Found {len(students)} students for bookings")
        
        # Create sessions for the next 10 days
        print("\n📅 Creating Training Sessions...")
        now = datetime.now(timezone.utc)
        sessions_data = []
        
        # Different types of sessions
        session_types = [
            {"title": "Morning Football Training", "time": 9, "duration": 2, "capacity": 20},
            {"title": "Afternoon Skills Session", "time": 15, "duration": 1.5, "capacity": 15},
            {"title": "Evening Fitness Training", "time": 18, "duration": 1, "capacity": 25},
            {"title": "Weekend Tournament Prep", "time": 10, "duration": 3, "capacity": 18},
            {"title": "Goalkeeping Specialist Session", "time": 14, "duration": 1.5, "capacity": 8}
        ]
        
        created_sessions = []
        for i in range(10):  # Next 10 days
            session_date = now + timedelta(days=i+1)
            
            # 2-3 sessions per day
            day_sessions = 2 if i < 5 else 3  # More sessions on weekdays
            
            for j in range(day_sessions):
                session_type = session_types[j % len(session_types)]
                
                start_time = session_date.replace(
                    hour=session_type["time"], 
                    minute=0, 
                    second=0, 
                    microsecond=0
                )
                end_time = start_time + timedelta(hours=session_type["duration"])
                
                session = Session(
                    title=session_type["title"],
                    description=f"Professional football training session focusing on skill development and team coordination. All skill levels welcome!",
                    instructor_id=instructor.id,
                    semester_id=active_semester.id,
                    date_start=start_time,
                    date_end=end_time,
                    capacity=session_type["capacity"],
                    location=f"Training Field {j+1}"
                )
                db.add(session)
                created_sessions.append(session)
        
        # Commit sessions first
        db.commit()
        print(f"  ✅ Created {len(created_sessions)} training sessions")
        
        # Create some bookings for students
        print("\n🎫 Creating Student Bookings...")
        booking_count = 0
        
        for session in created_sessions[:15]:  # Book first 15 sessions
            # 60-80% capacity booking
            num_bookings = int(session.capacity * 0.7)  # 70% booking rate
            session_students = students[:num_bookings] if num_bookings <= len(students) else students
            
            for student in session_students:
                booking = Booking(
                    user_id=student.id,
                    session_id=session.id,
                    status=BookingStatus.CONFIRMED,
                    created_at=now - timedelta(hours=2)  # Booked 2 hours ago
                )
                db.add(booking)
                booking_count += 1
        
        # Commit all changes
        db.commit()
        print(f"  ✅ Created {booking_count} student bookings")
        
        # Summary
        print("\n✅ Sessions and Events Creation Complete!")
        print("=" * 45)
        print(f"📅 Training Sessions: {len(created_sessions)}")
        print(f"🎫 Student Bookings: {booking_count}")
        print(f"📍 Locations: Training Field 1-3")
        print(f"⏰ Time Range: Next 10 days")
        
        print("\n🔍 Students can now:")
        print("  - Browse and book training sessions")
        print("  - See their booking history")
        print("  - View session details and capacity")
        print("  - Cancel bookings if needed")
        
        # Show next few sessions
        print("\n📋 Next Few Sessions:")
        for session in created_sessions[:5]:
            print(f"  • {session.date_start.strftime('%Y-%m-%d %H:%M')} - {session.title}")
            print(f"    Location: {session.location}, Capacity: {session.capacity}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating sessions: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    create_sessions_and_events()