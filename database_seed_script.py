#!/usr/bin/env python3
"""
🌱 DATABASE SEED SCRIPT - Analytics Test Data
Feltölti az adatbázist comprehensive test adatokkal minden analytics funkcióhoz
"""

import sys
import os
from datetime import datetime, timedelta, timezone
import random
from typing import List

# Add the project root to Python path
sys.path.append(os.getcwd())

from app.database import SessionLocal, engine
from app.models.user import User, UserRole
from app.models.semester import Semester
from app.models.group import Group
from app.models.session import Session, SessionMode
from app.models.booking import Booking, BookingStatus
from app.models.attendance import Attendance, AttendanceStatus
from app.models.feedback import Feedback
from app.core.security import get_password_hash

class DatabaseSeeder:
    def __init__(self):
        self.db = SessionLocal()
        self.users = []
        self.semesters = []
        self.groups = []
        self.sessions = []
        self.bookings = []
        self.attendances = []
        
    def seed_all(self):
        """Run complete database seeding"""
        print("🌱 DATABASE SEEDING STARTED")
        print("=" * 50)
        
        try:
            # Check if we already have data
            if self.db.query(User).count() > 5:
                print("Database already has data. Skipping seed.")
                return
                
            self.seed_users()
            self.seed_semesters()
            self.seed_groups()
            self.seed_sessions()
            self.seed_bookings()
            self.seed_attendance()
            self.seed_feedback()
            
            self.db.commit()
            print("\n🎉 DATABASE SEEDING COMPLETED SUCCESSFULLY!")
            self.print_summary()
            
        except Exception as e:
            print(f"❌ SEEDING ERROR: {e}")
            self.db.rollback()
            raise
        finally:
            self.db.close()
    
    def seed_users(self):
        """Create diverse user base"""
        print("👥 Creating users...")
        
        # Admin user (if not exists)
        admin_exists = self.db.query(User).filter(User.email == "admin@company.com").first()
        if not admin_exists:
            admin = User(
                name="System Administrator",
                email="admin@company.com",
                password_hash=get_password_hash("admin123"),
                role=UserRole.ADMIN,
                is_active=True
            )
            self.db.add(admin)
            self.users.append(admin)
        
        # Instructors
        instructors = [
            {"name": "Dr. John Smith", "email": "john.smith@company.com"},
            {"name": "Prof. Sarah Johnson", "email": "sarah.johnson@company.com"}, 
            {"name": "Dr. Mike Brown", "email": "mike.brown@company.com"},
        ]
        
        for instructor_data in instructors:
            instructor = User(
                name=instructor_data["name"],
                email=instructor_data["email"],
                password_hash=get_password_hash("instructor123"),
                role=UserRole.INSTRUCTOR,
                is_active=True
            )
            self.db.add(instructor)
            self.users.append(instructor)
        
        # Students (20 students for good test data)
        student_names = [
            "Alice Cooper", "Bob Dylan", "Charlie Parker", "Diana Ross",
            "Eddie Murphy", "Fiona Apple", "George Clooney", "Helen Hunt",
            "Ian McKellen", "Julia Roberts", "Kevin Spacey", "Laura Dern",
            "Morgan Freeman", "Nicole Kidman", "Oscar Isaac", "Penelope Cruz",
            "Quincy Jones", "Rachel Green", "Samuel Jackson", "Tina Turner"
        ]
        
        for i, name in enumerate(student_names):
            email = f"{name.lower().replace(' ', '.')}@student.com"
            student = User(
                name=name,
                email=email,
                password_hash=get_password_hash("student123"),
                role=UserRole.STUDENT,
                is_active=random.choice([True, True, True, False])  # 75% active
            )
            self.db.add(student)
            self.users.append(student)
        
        self.db.flush()  # Get IDs
        print(f"   ✅ Created {len(self.users)} users")
    
    def seed_semesters(self):
        """Create semesters"""
        print("📅 Creating semesters...")
        
        # Current semester
        current = Semester(
            code="2025S1",
            name="Spring 2025",
            start_date=datetime.now().date() - timedelta(days=30),
            end_date=datetime.now().date() + timedelta(days=60),
            is_active=True
        )
        
        # Previous semester  
        previous = Semester(
            code="2024F1", 
            name="Fall 2024",
            start_date=datetime.now().date() - timedelta(days=120),
            end_date=datetime.now().date() - timedelta(days=30),
            is_active=False
        )
        
        self.semesters = [current, previous]
        for semester in self.semesters:
            self.db.add(semester)
        
        self.db.flush()
        print(f"   ✅ Created {len(self.semesters)} semesters")
    
    def seed_groups(self):
        """Create groups"""
        print("👥 Creating groups...")
        
        group_names = ["Group A", "Group B", "Group C", "Advanced Group"]
        
        for semester in self.semesters:
            for group_name in group_names:
                group = Group(
                    name=f"{group_name} - {semester.code}",
                    description=f"Practice group {group_name} for {semester.name}",
                    semester_id=semester.id
                )
                self.db.add(group)
                self.groups.append(group)
        
        self.db.flush()
        print(f"   ✅ Created {len(self.groups)} groups")
    
    def seed_sessions(self):
        """Create practice sessions"""
        print("🏃‍♂️ Creating practice sessions...")
        
        # Get instructors
        instructors = [u for u in self.users if u.role == UserRole.INSTRUCTOR]
        
        session_titles = [
            "Morning Practice", "Evening Training", "Weekend Session",
            "Intensive Workshop", "Skills Development", "Team Building",
            "Advanced Techniques", "Beginner Friendly"
        ]
        
        for semester in self.semesters:
            semester_groups = [g for g in self.groups if g.semester_id == semester.id]
            
            # Create 3-4 sessions per group
            for group in semester_groups:
                session_count = random.randint(3, 4)
                
                for i in range(session_count):
                    # Sessions spread over the semester
                    base_date = semester.start_date + timedelta(days=i*7 + random.randint(0, 6))
                    start_time = datetime.combine(base_date, datetime.min.time()) + timedelta(
                        hours=random.randint(9, 17),
                        minutes=random.choice([0, 30])
                    )
                    
                    session = Session(
                        title=f"{random.choice(session_titles)} #{i+1}",
                        description=f"Practice session for {group.name}",
                        date_start=start_time,
                        date_end=start_time + timedelta(hours=random.choice([1, 1.5, 2])),
                        mode=random.choice([SessionMode.ONLINE, SessionMode.OFFLINE, SessionMode.HYBRID]),
                        capacity=random.randint(8, 16),
                        location="Training Room A" if random.choice([True, False]) else "Online",
                        meeting_link="https://zoom.us/meeting123" if random.choice([True, False]) else None,
                        semester_id=semester.id,
                        group_id=group.id,
                        instructor_id=random.choice(instructors).id if instructors else None
                    )
                    self.db.add(session)
                    self.sessions.append(session)
        
        self.db.flush()
        print(f"   ✅ Created {len(self.sessions)} practice sessions")
    
    def seed_bookings(self):
        """Create bookings with realistic patterns"""
        print("📝 Creating bookings...")
        
        students = [u for u in self.users if u.role == UserRole.STUDENT and u.is_active]
        
        for session in self.sessions:
            # Each session gets 60-90% of its capacity booked
            booking_count = int(session.capacity * random.uniform(0.6, 0.9))
            selected_students = random.sample(students, min(booking_count, len(students)))
            
            for student in selected_students:
                # Booking status distribution: 80% confirmed, 15% pending, 5% cancelled
                status_choice = random.choices(
                    [BookingStatus.CONFIRMED, BookingStatus.PENDING, BookingStatus.CANCELLED, BookingStatus.WAITLISTED],
                    weights=[80, 15, 4, 1]
                )[0]
                
                booking = Booking(
                    user_id=student.id,
                    session_id=session.id,
                    status=status_choice,
                    waitlist_position=random.randint(1, 5) if status_choice == BookingStatus.WAITLISTED else None,
                    notes="Automatically generated booking" if random.choice([True, False]) else None,
                    created_at=session.date_start - timedelta(days=random.randint(1, 14)),
                    cancelled_at=datetime.now(timezone.utc) if status_choice == BookingStatus.CANCELLED else None
                )
                self.db.add(booking)
                self.bookings.append(booking)
        
        self.db.flush()
        print(f"   ✅ Created {len(self.bookings)} bookings")
    
    def seed_attendance(self):
        """Create attendance records for confirmed bookings"""
        print("📊 Creating attendance records...")
        
        confirmed_bookings = [b for b in self.bookings if b.status == BookingStatus.CONFIRMED]
        
        for booking in confirmed_bookings:
            # Only create attendance for past sessions
            if booking.session.date_start < datetime.now():
                # 85% attendance rate (realistic)
                if random.random() < 0.85:
                    status = AttendanceStatus.PRESENT
                    check_in = booking.session.date_start + timedelta(minutes=random.randint(-5, 15))
                    check_out = booking.session.date_end + timedelta(minutes=random.randint(-10, 5))
                else:
                    # 10% absent, 5% late
                    status = random.choice([AttendanceStatus.ABSENT, AttendanceStatus.LATE])
                    check_in = booking.session.date_start + timedelta(minutes=random.randint(10, 30)) if status == AttendanceStatus.LATE else None
                    check_out = None if status == AttendanceStatus.ABSENT else booking.session.date_end
                
                attendance = Attendance(
                    user_id=booking.user_id,
                    session_id=booking.session_id,
                    booking_id=booking.id,
                    status=status,
                    check_in_time=check_in,
                    check_out_time=check_out,
                    notes="Auto-generated attendance record",
                    marked_by=booking.session.instructor_id
                )
                self.db.add(attendance)
                self.attendances.append(attendance)
        
        self.db.flush()
        print(f"   ✅ Created {len(self.attendances)} attendance records")
    
    def seed_feedback(self):
        """Create feedback from attended sessions"""
        print("💬 Creating feedback...")
        
        present_attendance = [a for a in self.attendances if a.status == AttendanceStatus.PRESENT]
        
        # 60% of attendees leave feedback
        feedback_attendance = random.sample(present_attendance, int(len(present_attendance) * 0.6))
        
        feedback_comments = [
            "Great session, very helpful!",
            "Could use more practical exercises.",
            "Instructor was excellent.",
            "Perfect difficulty level.",
            "Would recommend to others.",
            "Learned a lot today.",
            "Good pace and content.",
            "Enjoyed the interactive parts."
        ]
        
        for attendance in feedback_attendance:
            feedback = Feedback(
                user_id=attendance.user_id,
                session_id=attendance.session_id,
                rating=random.randint(3, 5),  # Mostly positive ratings
                comment=random.choice(feedback_comments),
                created_at=attendance.session.date_end + timedelta(hours=random.randint(1, 48))
            )
            self.db.add(feedback)
        
        print(f"   ✅ Created feedback records")
    
    def print_summary(self):
        """Print seeding summary"""
        print("\n📊 DATABASE SEEDING SUMMARY")
        print("=" * 30)
        print(f"Users: {len(self.users)}")
        print(f"Semesters: {len(self.semesters)}")  
        print(f"Groups: {len(self.groups)}")
        print(f"Sessions: {len(self.sessions)}")
        print(f"Bookings: {len(self.bookings)}")
        print(f"Attendance: {len(self.attendances)}")
        print()
        print("🎯 ANALYTICS READY!")
        print("All analytics endpoints now have rich data to display:")
        print("  • User statistics by role")
        print("  • Booking trends and status breakdown") 
        print("  • Session utilization rates")
        print("  • Attendance patterns and rates")
        print("  • Metrics across multiple time periods")
        print()
        print("🌐 TEST THE ANALYTICS:")
        print("  1. Start backend: uvicorn app.main:app --reload")
        print("  2. Start frontend: cd frontend && npm start")
        print("  3. Login: admin@company.com / admin123")
        print("  4. Visit Reports tab - should show rich charts!")


if __name__ == "__main__":
    print("🌱 STARTING DATABASE SEED FOR ANALYTICS TESTING")
    print()
    
    seeder = DatabaseSeeder()
    seeder.seed_all()