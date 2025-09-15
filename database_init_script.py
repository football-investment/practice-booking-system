#!/usr/bin/env python3
"""
Database Initialization Script
Creates all database tables and initial data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal
from app.models import Base
from app.models.user import User
from app.models.semester import Semester  
from app.models.group import Group
from app.models.session import Session
from app.models.booking import Booking
from app.models.attendance import Attendance
from app.models.feedback import Feedback
from app.core.auth import hash_password
from datetime import datetime, timedelta

def init_database():
    """Initialize database with tables and sample data"""
    
    print("🚀 DATABASE INITIALIZATION STARTING")
    print("=" * 50)
    
    # 1. Create all tables
    print("📊 Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
    
    # 2. Create database session
    db = SessionLocal()
    
    try:
        # 3. Create admin user
        print("👤 Creating admin user...")
        admin_user = db.query(User).filter(User.email == "admin@yourcompany.com").first()
        if not admin_user:
            admin_user = User(
                email="admin@yourcompany.com",
                password_hash=hash_password("admin123"),
                full_name="Admin User",
                role="admin"
            )
            db.add(admin_user)
            print("✅ Admin user created: admin@yourcompany.com / admin123")
        else:
            print("ℹ️ Admin user already exists")
        
        # 4. Create student users
        print("👥 Creating student users...")
        students = [
            {"email": "alex@example.com", "name": "Alex Smith", "password": "password123"},
            {"email": "maria@example.com", "name": "Maria Garcia", "password": "password123"},
            {"email": "john@example.com", "name": "John Doe", "password": "password123"},
        ]
        
        for student_data in students:
            existing_user = db.query(User).filter(User.email == student_data["email"]).first()
            if not existing_user:
                user = User(
                    email=student_data["email"],
                    password_hash=hash_password(student_data["password"]),
                    full_name=student_data["name"],
                    role="student"
                )
                db.add(user)
                print(f"✅ Student created: {student_data['email']} / {student_data['password']}")
            else:
                print(f"ℹ️ Student already exists: {student_data['email']}")
        
        # 5. Create instructor user
        print("🏫 Creating instructor user...")
        instructor = db.query(User).filter(User.email == "instructor@example.com").first()
        if not instructor:
            instructor = User(
                email="instructor@example.com",
                password_hash=hash_password("instructor123"),
                full_name="Dr. Johnson",
                role="instructor"
            )
            db.add(instructor)
            print("✅ Instructor created: instructor@example.com / instructor123")
        else:
            print("ℹ️ Instructor already exists")
        
        # 6. Create semester
        print("📅 Creating current semester...")
        current_semester = db.query(Semester).filter(Semester.is_active == True).first()
        if not current_semester:
            current_semester = Semester(
                name="Fall 2025",
                code="2025_FALL",
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now() + timedelta(days=60),
                is_active=True
            )
            db.add(current_semester)
            db.commit()  # Commit to get ID
            print("✅ Active semester created: Fall 2025")
        else:
            print("ℹ️ Active semester already exists")
        
        # 7. Create group
        print("👥 Creating student group...")
        group = db.query(Group).filter(Group.semester_id == current_semester.id).first()
        if not group:
            group = Group(
                name="Web Development Fundamentals",
                description="Introduction to web development",
                semester_id=current_semester.id,
                max_capacity=25
            )
            db.add(group)
            db.commit()  # Commit to get ID
            print("✅ Group created: Web Development Fundamentals")
        else:
            print("ℹ️ Group already exists")
        
        # 8. Create sample sessions
        print("📚 Creating sample sessions...")
        
        # Past session for feedback testing
        past_session = Session(
            title="JavaScript Basics - Completed",
            description="Introduction to JavaScript programming",
            date_start=datetime.now() - timedelta(days=3, hours=2),
            date_end=datetime.now() - timedelta(days=3, hours=1),
            capacity=20,
            group_id=group.id,
            mode="on_site",
            location="Room A101"
        )
        db.add(past_session)
        
        # Future sessions
        future_sessions = []
        for i in range(5):
            future_session = Session(
                title=f"Web Development Session {i+1}",
                description=f"Session {i+1} content",
                date_start=datetime.now() + timedelta(days=i+1, hours=10),
                date_end=datetime.now() + timedelta(days=i+1, hours=12),
                capacity=20,
                group_id=group.id,
                mode="on_site",
                location=f"Room A{101+i}"
            )
            db.add(future_session)
            future_sessions.append(future_session)
        
        db.commit()  # Commit sessions to get IDs
        print("✅ Sample sessions created (1 past, 5 future)")
        
        # 9. Create bookings for Alex
        print("📝 Creating bookings for Alex...")
        alex = db.query(User).filter(User.email == "alex@example.com").first()
        if alex:
            # Booking for past session
            past_booking = Booking(
                user_id=alex.id,
                session_id=past_session.id,
                status="confirmed"
            )
            db.add(past_booking)
            
            # Bookings for future sessions
            for session in future_sessions[:3]:  # Only first 3 future sessions
                booking = Booking(
                    user_id=alex.id,
                    session_id=session.id,
                    status="confirmed"
                )
                db.add(booking)
            
            db.commit()  # Commit bookings to get IDs
            print("✅ Bookings created for Alex (1 past, 3 future)")
            
            # 10. Create attendance for past session
            print("✅ Creating attendance for past session...")
            from app.models.attendance import Attendance, AttendanceStatus
            
            attendance = Attendance(
                user_id=alex.id,
                session_id=past_session.id,
                booking_id=past_booking.id,
                status=AttendanceStatus.PRESENT,
                notes="Feedback test attendance"
            )
            db.add(attendance)
            
            # Update booking attended status
            past_booking.attended_status = "present"
            
            db.commit()
            print("✅ Attendance recorded for Alex (present)")
        
        # Final commit
        db.commit()
        print("")
        print("🎉 DATABASE INITIALIZATION COMPLETED!")
        print("=" * 50)
        print("📊 Summary:")
        print("- ✅ All database tables created")
        print("- ✅ Admin user: admin@yourcompany.com / admin123")
        print("- ✅ Alex student: alex@example.com / password123")
        print("- ✅ Instructor: instructor@example.com / instructor123")
        print("- ✅ Active semester: Fall 2025")
        print("- ✅ Sample group and sessions created")
        print("- ✅ Alex has bookings and attendance")
        print("")
        print("🎯 READY FOR FEEDBACK TESTING!")
        print("Alex should now see 'Sessions Awaiting Feedback'")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = init_database()
    if success:
        print("\n🚀 You can now test the application!")
        print("Frontend: http://localhost:3000")
        print("Backend API: http://localhost:8000/docs")
    else:
        print("\n❌ Initialization failed. Check the error messages above.")
        sys.exit(1)