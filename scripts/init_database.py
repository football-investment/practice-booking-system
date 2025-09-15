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
        
        # Get Alex's ID
        cursor.execute("SELECT id FROM users WHERE email = ?", ("alex@example.com",))
        alex_id = cursor.fetchone()[0]
        
        # Get instructor ID
        cursor.execute("SELECT id FROM users WHERE email = ?", ("instructor@example.com",))
        instructor_id = cursor.fetchone()[0]
        
        sessions_data = [
            # PAST SESSION 1 - WITH ATTENDANCE (FOR FEEDBACK)
            {
                "title": "JavaScript Basics - COMPLETED",
                "description": "Introduction to JavaScript programming",
                "date_start": (datetime.now() - timedelta(days=3)).isoformat(),
                "date_end": (datetime.now() - timedelta(days=3, hours=-2)).isoformat(),
                "capacity": 20,
                "semester_id": semester_id,
                "group_id": group_id,
                "instructor_id": instructor_id,
                "mode": "offline",
                "location": "Room A101"
            },
            # PAST SESSION 2 - WITH ATTENDANCE (FOR FEEDBACK)
            {
                "title": "CSS Advanced Techniques",
                "description": "Advanced CSS styling techniques",
                "date_start": (datetime.now() - timedelta(days=7)).isoformat(),
                "date_end": (datetime.now() - timedelta(days=7, hours=-2)).isoformat(),
                "capacity": 20,
                "semester_id": semester_id,
                "group_id": group_id,
                "instructor_id": instructor_id,
                "mode": "offline",
                "location": "Room A102"
            },
            # FUTURE SESSIONS
            {
                "title": "React Fundamentals",
                "description": "Introduction to React.js",
                "date_start": (datetime.now() + timedelta(days=2)).isoformat(),
                "date_end": (datetime.now() + timedelta(days=2, hours=2)).isoformat(),
                "capacity": 20,
                "semester_id": semester_id,
                "group_id": group_id,
                "instructor_id": instructor_id,
                "mode": "offline",
                "location": "Room A103"
            },
            {
                "title": "Node.js Backend Development",
                "description": "Building APIs with Node.js",
                "date_start": (datetime.now() + timedelta(days=5)).isoformat(),
                "date_end": (datetime.now() + timedelta(days=5, hours=2)).isoformat(),
                "capacity": 20,
                "semester_id": semester_id,
                "group_id": group_id,
                "instructor_id": instructor_id,
                "mode": "offline",
                "location": "Room A104"
            }
        ]
        
        session_ids = []
        for session in sessions_data:
            cursor.execute(
                """INSERT INTO sessions (title, description, date_start, date_end, capacity, semester_id, group_id, instructor_id, mode, location, created_at, updated_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (session["title"], session["description"], session["date_start"], session["date_end"],
                 session["capacity"], session["semester_id"], session["group_id"], session["instructor_id"],
                 session["mode"], session["location"],
                 datetime.now().isoformat(), datetime.now().isoformat())
            )
            session_ids.append(cursor.lastrowid)
        print(f"✅ Created {len(sessions_data)} sessions")
        
        # 5. CREATE BOOKINGS FOR ALEX
        booking_ids = []
        for i, session_id in enumerate(session_ids):
            status = "confirmed"
            attended_status = "present" if i < 2 else None  # First 2 are past sessions with attendance
            
            cursor.execute(
                "INSERT INTO bookings (user_id, session_id, status, attended_status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (alex_id, session_id, status, attended_status, datetime.now().isoformat(), datetime.now().isoformat())
            )
            booking_ids.append(cursor.lastrowid)
        print(f"✅ Created {len(booking_ids)} bookings for Alex")
        
        # 6. CREATE ATTENDANCE RECORDS (CRITICAL!)
        for i in range(2):  # First 2 sessions are past with attendance
            cursor.execute(
                "INSERT INTO attendance (user_id, session_id, booking_id, status, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (alex_id, session_ids[i], booking_ids[i], "present", f"Test attendance for session {i+1}",
                 datetime.now().isoformat(), datetime.now().isoformat())
            )
        print("✅ Created attendance records")
        
        # 7. CREATE ONE FEEDBACK (to test "My Previous Feedback")
        cursor.execute(
            "INSERT INTO feedback (user_id, session_id, booking_id, rating, comment, session_quality, instructor_rating, would_recommend, is_anonymous, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (alex_id, session_ids[1], booking_ids[1], 4.5, "Great session! Very informative.", 5, 4, True, False,
             datetime.now().isoformat(), datetime.now().isoformat())
        )
        print("✅ Created sample feedback")
        
        conn.commit()
        conn.close()
        
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