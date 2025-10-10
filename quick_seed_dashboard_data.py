#!/usr/bin/env python3
"""
🚀 Quick Seed for Dashboard Data
Creates essential test data for student dashboard testing
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.semester import Semester
from app.models.session import Session, SessionMode
from app.models.booking import Booking, BookingStatus
from app.models.project import Project, ProjectEnrollment
from app.core.security import get_password_hash

def quick_seed():
    db = SessionLocal()

    try:
        print("🚀 Quick Dashboard Data Seed Starting...")

        # Check if we already have a semester
        semester = db.query(Semester).filter(Semester.is_active == True).first()
        if not semester:
            print("📅 Creating active semester...")
            semester = Semester(
                code="FALL-2025",
                name="Fall 2025 Academy",
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now() + timedelta(days=60),
                is_active=True
            )
            db.add(semester)
            db.commit()
            db.refresh(semester)
            print(f"✅ Semester created: {semester.name}")
        else:
            print(f"✅ Active semester exists: {semester.name}")

        # Check if we have a test student
        student = db.query(User).filter(
            User.email == "student@test.com",
            User.role == UserRole.STUDENT
        ).first()

        if not student:
            print("👤 Creating test student...")
            student = User(
                name="Test Student",
                email="student@test.com",
                password_hash=get_password_hash("password123"),
                role=UserRole.STUDENT,
                is_active=True
            )
            db.add(student)
            db.commit()
            db.refresh(student)
            print(f"✅ Student created: {student.email}")
        else:
            print(f"✅ Test student exists: {student.email}")

        # Check if we have an instructor
        instructor = db.query(User).filter(User.role == UserRole.INSTRUCTOR).first()
        if not instructor:
            print("🏃 Creating test instructor...")
            instructor = User(
                name="Coach Smith",
                email="coach@test.com",
                password_hash=get_password_hash("password123"),
                role=UserRole.INSTRUCTOR,
                is_active=True
            )
            db.add(instructor)
            db.commit()
            db.refresh(instructor)
            print(f"✅ Instructor created: {instructor.email}")
        else:
            print(f"✅ Instructor exists: {instructor.name}")

        # Create some sessions
        existing_sessions = db.query(Session).filter(
            Session.semester_id == semester.id
        ).count()

        if existing_sessions < 3:
            print("🏋️ Creating training sessions...")
            session_titles = [
                "Tactical Training",
                "Physical Conditioning",
                "Technical Skills Workshop"
            ]

            for i, title in enumerate(session_titles):
                session_date = datetime.now() + timedelta(days=i+1, hours=14)
                session = Session(
                    title=title,
                    description=f"Comprehensive {title.lower()} for academy students",
                    date_start=session_date,
                    date_end=session_date + timedelta(hours=2),
                    location="Training Ground A",
                    capacity=20,
                    instructor_id=instructor.id,
                    semester_id=semester.id,
                    mode=SessionMode.OFFLINE  # OFFLINE means in-person
                )
                db.add(session)

            db.commit()
            print(f"✅ Created {len(session_titles)} training sessions")
        else:
            print(f"✅ {existing_sessions} sessions exist for current semester")

        # Create sample bookings for the student
        existing_bookings = db.query(Booking).filter(
            Booking.user_id == student.id
        ).count()

        if existing_bookings < 5:
            print("📅 Creating sample bookings...")
            sessions = db.query(Session).filter(
                Session.semester_id == semester.id
            ).limit(3).all()

            for session in sessions[:2]:  # Book first 2 sessions
                booking = Booking(
                    user_id=student.id,
                    session_id=session.id,
                    status=BookingStatus.CONFIRMED
                )
                db.add(booking)

            db.commit()
            print(f"✅ Created sample bookings")
        else:
            print(f"✅ {existing_bookings} bookings exist for test student")

        # Create sample project
        existing_projects = db.query(Project).filter(
            Project.semester_id == semester.id
        ).count()

        if existing_projects < 1:
            print("🎯 Creating sample project...")
            project = Project(
                title="Advanced Football Tactics",
                description="Learn professional-level tactical awareness and game intelligence",
                semester_id=semester.id,
                instructor_id=instructor.id,
                max_participants=15,
                deadline=datetime.now() + timedelta(days=45)
            )
            db.add(project)
            db.commit()
            db.refresh(project)

            # Enroll student in project
            enrollment = ProjectEnrollment(
                user_id=student.id,
                project_id=project.id,
                enrolled_at=datetime.now()
            )
            db.add(enrollment)
            db.commit()
            print(f"✅ Project created and student enrolled")
        else:
            print(f"✅ {existing_projects} projects exist for current semester")

        print("\n" + "="*50)
        print("🎉 QUICK SEED COMPLETED SUCCESSFULLY!")
        print("="*50)
        print(f"\n📧 Test Student Login:")
        print(f"   Email: student@test.com")
        print(f"   Password: password123")
        print(f"\n🏃 Test Instructor Login:")
        print(f"   Email: {instructor.email}")
        print(f"   Password: password123")

    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    quick_seed()
