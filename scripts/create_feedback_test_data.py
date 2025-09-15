#!/usr/bin/env python3
"""
Create test data for feedback system testing
"""

import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.semester import Semester
from app.models.group import Group
from app.models.session import Session as SessionModel, SessionMode
from app.models.booking import Booking, BookingStatus
from app.models.attendance import Attendance, AttendanceStatus
from app.models.feedback import Feedback

def create_feedback_test_data():
    """Create comprehensive test data for feedback system"""
    
    print("🚀 CREATING FEEDBACK TEST DATA")
    print("=" * 50)
    
    try:
        db = SessionLocal()
        
        # Get Alex and Instructor
        alex_user = db.query(User).filter(User.email == "alex@example.com").first()
        instructor_user = db.query(User).filter(User.email == "instructor@example.com").first()
        
        if not alex_user or not instructor_user:
            print("❌ Alex or Instructor user not found. Run add_test_users.py first.")
            return False
            
        print(f"✅ Found Alex (ID: {alex_user.id}) and Instructor (ID: {instructor_user.id})")
        
        # 1. CREATE SEMESTER
        # Check if test semester exists
        existing_semester = db.query(Semester).filter(Semester.code == "2025_FALL").first()
        if existing_semester:
            semester = existing_semester
            print("ℹ️ Using existing semester")
        else:
            semester_start = datetime.now() - timedelta(days=60)
            semester_end = datetime.now() + timedelta(days=30)
            semester = Semester(
                name="Fall 2025",
                code="2025_FALL",
                start_date=semester_start.date(),
                end_date=semester_end.date(),
                is_active=True
            )
            db.add(semester)
            db.commit()
            print("✅ Created semester")
        
        # 2. CREATE GROUP
        existing_group = db.query(Group).filter(Group.name == "Web Development Fundamentals").first()
        if existing_group:
            group = existing_group
            print("ℹ️ Using existing group")
        else:
            group = Group(
                name="Web Development Fundamentals",
                description="Introduction to web development",
                semester_id=semester.id
            )
            db.add(group)
            db.commit()
            print("✅ Created group")
        
        # 3. CREATE SESSIONS
        sessions_data = [
            # PAST SESSION 1 - WITH ATTENDANCE (FOR FEEDBACK)
            {
                "title": "JavaScript Basics - COMPLETED",
                "description": "Introduction to JavaScript programming",
                "date_start": datetime.now() - timedelta(days=3),
                "date_end": datetime.now() - timedelta(days=3) + timedelta(hours=2),
                "capacity": 20,
                "mode": SessionMode.OFFLINE,
                "location": "Room A101"
            },
            # PAST SESSION 2 - WITH ATTENDANCE (FOR FEEDBACK)
            {
                "title": "CSS Advanced Techniques",
                "description": "Advanced CSS styling techniques",
                "date_start": datetime.now() - timedelta(days=7),
                "date_end": datetime.now() - timedelta(days=7) + timedelta(hours=2),
                "capacity": 20,
                "mode": SessionMode.OFFLINE,
                "location": "Room A102"
            },
            # FUTURE SESSIONS
            {
                "title": "React Fundamentals",
                "description": "Introduction to React.js",
                "date_start": datetime.now() + timedelta(days=2),
                "date_end": datetime.now() + timedelta(days=2) + timedelta(hours=2),
                "capacity": 20,
                "mode": SessionMode.OFFLINE,
                "location": "Room A103"
            },
            {
                "title": "Node.js Backend Development",
                "description": "Building APIs with Node.js",
                "date_start": datetime.now() + timedelta(days=5),
                "date_end": datetime.now() + timedelta(days=5) + timedelta(hours=2),
                "capacity": 20,
                "mode": SessionMode.OFFLINE,
                "location": "Room A104"
            }
        ]
        
        created_sessions = []
        for session_data in sessions_data:
            # Check if session already exists
            existing_session = db.query(SessionModel).filter(SessionModel.title == session_data["title"]).first()
            if existing_session:
                created_sessions.append(existing_session)
                print(f"ℹ️ Using existing session: {session_data['title']}")
            else:
                session = SessionModel(
                    title=session_data["title"],
                    description=session_data["description"],
                    date_start=session_data["date_start"],
                    date_end=session_data["date_end"],
                    capacity=session_data["capacity"],
                    semester_id=semester.id,
                    group_id=group.id,
                    instructor_id=instructor_user.id,
                    mode=session_data["mode"],
                    location=session_data["location"]
                )
                db.add(session)
                created_sessions.append(session)
                print(f"✅ Created session: {session_data['title']}")
        
        db.commit()
        print(f"✅ Sessions ready: {len(created_sessions)} sessions")
        
        # 4. CREATE BOOKINGS FOR ALEX
        created_bookings = []
        for i, session in enumerate(created_sessions):
            # Check if booking already exists
            existing_booking = db.query(Booking).filter(
                Booking.user_id == alex_user.id,
                Booking.session_id == session.id
            ).first()
            
            if existing_booking:
                created_bookings.append(existing_booking)
                print(f"ℹ️ Using existing booking for: {session.title}")
            else:
                status = BookingStatus.CONFIRMED
                attended_status = "present" if i < 2 else None  # First 2 are past sessions with attendance
                
                booking = Booking(
                    user_id=alex_user.id,
                    session_id=session.id,
                    status=status,
                    attended_status=attended_status
                )
                db.add(booking)
                created_bookings.append(booking)
                print(f"✅ Created booking for: {session.title}")
        
        db.commit()
        print(f"✅ Bookings ready: {len(created_bookings)} bookings for Alex")
        
        # 5. CREATE ATTENDANCE RECORDS (CRITICAL!)
        attendance_count = 0
        for i in range(2):  # First 2 sessions are past with attendance
            session = created_sessions[i]
            booking = created_bookings[i]
            
            # Check if attendance already exists
            existing_attendance = db.query(Attendance).filter(
                Attendance.user_id == alex_user.id,
                Attendance.session_id == session.id
            ).first()
            
            if existing_attendance:
                print(f"ℹ️ Attendance already exists for: {session.title}")
            else:
                attendance = Attendance(
                    user_id=alex_user.id,
                    session_id=session.id,
                    booking_id=booking.id,
                    status=AttendanceStatus.PRESENT,
                    notes=f"Test attendance for session {i+1}"
                )
                db.add(attendance)
                attendance_count += 1
                print(f"✅ Created attendance for: {session.title}")
        
        db.commit()
        print(f"✅ Attendance records: {attendance_count} new records")
        
        # 6. CREATE ONE FEEDBACK (to test "My Previous Feedback")
        session_for_feedback = created_sessions[1]  # CSS session
        booking_for_feedback = created_bookings[1]
        
        # Check if feedback already exists
        existing_feedback = db.query(Feedback).filter(
            Feedback.user_id == alex_user.id,
            Feedback.session_id == session_for_feedback.id
        ).first()
        
        if existing_feedback:
            print("ℹ️ Sample feedback already exists")
        else:
            feedback = Feedback(
                user_id=alex_user.id,
                session_id=session_for_feedback.id,
                rating=4.5,
                comment="Great session! Very informative.",
                is_anonymous=False
            )
            db.add(feedback)
            db.commit()
            print("✅ Created sample feedback")
        
        db.close()
        
        print("\n🎉 FEEDBACK TEST DATA COMPLETED!")
        print("=" * 50)
        print("📊 Test Data Summary:")
        print("- ✅ Semester: Fall 2025")
        print("- ✅ Group: Web Development Fundamentals")
        print("- ✅ 4 Sessions (2 past with attendance, 2 future)")
        print("- ✅ 4 Bookings for Alex")
        print("- ✅ 2 Attendance records (past sessions)")
        print("- ✅ 1 Sample feedback (CSS session)")
        print("\n🎯 EXPECTED RESULTS:")
        print("- Alex should see 1 session awaiting feedback (JavaScript Basics)")
        print("- Alex should see 1 previous feedback (CSS Advanced)")
        print("- Frontend feedback page should display correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create test data: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_feedback_test_data()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}")