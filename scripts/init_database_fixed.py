#!/usr/bin/env python3
"""
Complete database initialization with test data for feedback testing
"""

import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.database import engine, SessionLocal
from app.models.user import User, UserRole
from app.models.semester import Semester
from app.models.group import Group
from app.models.session import Session as SessionModel, SessionMode
from app.models.booking import Booking, BookingStatus
from app.models.attendance import Attendance, AttendanceStatus
from app.models.feedback import Feedback

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def init_complete_database():
    """Initialize database with all required test data"""
    
    print("🚀 INITIALIZING COMPLETE DATABASE")
    print("=" * 50)
    
    try:
        # Create database session
        db = SessionLocal()
        
        # Clear all existing data (in correct order due to foreign keys)
        tables = ['feedback', 'attendance', 'bookings', 'sessions', 'groups', 'semesters', 'users']
        for table in tables:
            try:
                db.execute(text(f"DELETE FROM {table}"))
                print(f"✅ Cleared {table} table")
            except Exception as e:
                print(f"ℹ️ Table {table} issue: {e}")
        
        db.commit()
        
        # 1. CREATE USERS
        users_data = [
            {"email": "admin@yourcompany.com", "password": "admin123", "name": "Admin User", "role": UserRole.ADMIN},
            {"email": "alex@example.com", "password": "password123", "name": "Alex Smith", "role": UserRole.STUDENT},
            {"email": "maria@example.com", "password": "password123", "name": "Maria Garcia", "role": UserRole.STUDENT},
            {"email": "instructor@example.com", "password": "instructor123", "name": "Dr. Johnson", "role": UserRole.INSTRUCTOR}
        ]
        
        created_users = {}
        for user_data in users_data:
            user = User(
                email=user_data["email"],
                password_hash=hash_password(user_data["password"]),
                name=user_data["name"],
                role=user_data["role"],
                is_active=True
            )
            db.add(user)
            created_users[user_data["role"]] = user
        
        db.commit()
        print(f"✅ Created {len(users_data)} users")
        
        # 2. CREATE SEMESTER
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
        print("✅ Created active semester")
        
        # 3. CREATE GROUP
        group = Group(
            name="Web Development Fundamentals",
            description="Introduction to web development",
            semester_id=semester.id,
            max_capacity=25
        )
        db.add(group)
        db.commit()
        print("✅ Created group")
        
        # 4. CREATE SESSIONS (CRITICAL FOR FEEDBACK TESTING)
        alex_user = created_users[UserRole.STUDENT]  # This is Alex
        instructor_user = created_users[UserRole.INSTRUCTOR]
        
        sessions_data = [
            # PAST SESSION 1 - WITH ATTENDANCE (FOR FEEDBACK)
            {
                "title": "Advanced Football Training",
                "description": "Tactical drills, match preparation, and advanced techniques for experienced players",
                "date_start": datetime.now() - timedelta(days=3),
                "date_end": datetime.now() - timedelta(days=3) + timedelta(minutes=90),
                "capacity": 20,
                "mode": SessionMode.OFFLINE,
                "location": "Field A - Sports Complex",
                "instructor": "Coach Martinez",
                "sport_type": "Football",
                "level": "Advanced"
            },
            # PAST SESSION 2 - WITH ATTENDANCE (FOR FEEDBACK)
            {
                "title": "Beginner Basketball Fundamentals",
                "description": "Basic skills, shooting techniques, and court positioning for new players",
                "date_start": datetime.now() - timedelta(days=7),
                "date_end": datetime.now() - timedelta(days=7) + timedelta(minutes=60),
                "capacity": 12,
                "mode": SessionMode.OFFLINE,
                "location": "Indoor Court 2",
                "instructor": "Coach Johnson",
                "sport_type": "Basketball",
                "level": "Beginner"
            },
            # FUTURE SESSIONS
            {
                "title": "Intermediate Tennis Clinic",
                "description": "Serve technique, volleys, and match tactics for developing players",
                "date_start": datetime.now() + timedelta(days=2),
                "date_end": datetime.now() + timedelta(days=2) + timedelta(minutes=75),
                "capacity": 8,
                "mode": SessionMode.OFFLINE,
                "location": "Tennis Courts 1-3",
                "instructor": "Pro Williams",
                "sport_type": "Tennis",
                "level": "Intermediate"
            },
            {
                "title": "Swimming Stroke Development",
                "description": "Technique refinement for freestyle, backstroke, and breaststroke",
                "date_start": datetime.now() + timedelta(days=5),
                "date_end": datetime.now() + timedelta(days=5) + timedelta(minutes=60),
                "capacity": 15,
                "mode": SessionMode.OFFLINE,
                "location": "Olympic Pool",
                "instructor": "Coach Davis",
                "sport_type": "Swimming",
                "level": "All Levels"
            },
            {
                "title": "Advanced Boxing Training",
                "description": "Heavy bag work, sparring preparation, and combat conditioning",
                "date_start": datetime.now() + timedelta(days=8),
                "date_end": datetime.now() + timedelta(days=8) + timedelta(minutes=120),
                "capacity": 10,
                "mode": SessionMode.OFFLINE,
                "location": "Boxing Gym",
                "instructor": "Coach Thompson",
                "sport_type": "Boxing",
                "level": "Advanced"
            }
        ]
        
        created_sessions = []
        for session_data in sessions_data:
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
        
        db.commit()
        print(f"✅ Created {len(sessions_data)} sessions")
        
        # 5. CREATE BOOKINGS FOR ALEX
        created_bookings = []
        for i, session in enumerate(created_sessions):
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
        
        db.commit()
        print(f"✅ Created {len(created_bookings)} bookings for Alex")
        
        # 6. CREATE ATTENDANCE RECORDS (CRITICAL!)
        for i in range(2):  # First 2 sessions are past with attendance
            attendance = Attendance(
                user_id=alex_user.id,
                session_id=created_sessions[i].id,
                booking_id=created_bookings[i].id,
                status=AttendanceStatus.PRESENT,
                notes=f"Test attendance for session {i+1}"
            )
            db.add(attendance)
        
        db.commit()
        print("✅ Created attendance records")
        
        # 7. CREATE ONE FEEDBACK (to test "My Previous Feedback")
        feedback = Feedback(
            user_id=alex_user.id,
            session_id=created_sessions[1].id,
            booking_id=created_bookings[1].id,
            rating=4.5,
            comment="Great session! Very informative.",
            session_quality=5,
            instructor_rating=4,
            would_recommend=True,
            is_anonymous=False
        )
        db.add(feedback)
        db.commit()
        print("✅ Created sample feedback")
        
        db.close()
        
        print("\n🎉 DATABASE INITIALIZATION COMPLETED!")
        print("=" * 50)
        print("📊 Created Test Data:")
        print("- 4 Users (admin, alex, maria, instructor)")
        print("- 1 Active semester")
        print("- 1 Group") 
        print("- 4 Sessions (2 past with attendance, 2 future)")
        print("- 4 Bookings for Alex")
        print("- 2 Attendance records (for past sessions)")
        print("- 1 Sample feedback")
        print("\n🎯 EXPECTED BEHAVIOR:")
        print("- Alex should see 1 session awaiting feedback")
        print("- Alex should see 1 previous feedback")
        print("- Login should work for all test users")
        
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_complete_database()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}")