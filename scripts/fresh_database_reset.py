#!/usr/bin/env python3
"""
🔄 FRESH DATABASE RESET SCRIPT
Teljes adatbázis reset és clean seed teszteléshez
"""

import sys
import os
from datetime import datetime, timedelta, timezone
import random
import json

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
from app.models import *
from app.core.security import get_password_hash
import subprocess

class FreshDatabaseReset:
    def __init__(self):
        self.db = SessionLocal()
        
    def reset_database(self):
        """Drop all tables and recreate fresh"""
        print("🗑️  Dropping all tables...")
        
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        
        # Recreate all tables
        print("📊 Creating fresh tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Fresh database created!")
        
    def create_test_users(self):
        """Create clean test users with newcomer status"""
        print("👥 Creating test users...")
        
        # Admin user
        admin = User(
            name="System Admin",
            email="admin@devstudio.com",
            password_hash=get_password_hash("admin123"),
            role=UserRole.ADMIN,
            is_active=True,
            onboarding_completed=True
        )
        self.db.add(admin)
        
        # Instructor users
        instructors = [
            {
                "name": "Dr. Sarah Johnson",
                "email": "sarah.johnson@instructor.com",
                "password": "instructor123"
            },
            {
                "name": "Coach Mark Wilson", 
                "email": "mark.wilson@instructor.com",
                "password": "instructor123"
            }
        ]
        
        for inst_data in instructors:
            instructor = User(
                name=inst_data["name"],
                email=inst_data["email"],
                password_hash=get_password_hash(inst_data["password"]),
                role=UserRole.INSTRUCTOR,
                is_active=True,
                onboarding_completed=True
            )
            self.db.add(instructor)
            
        # Test students with different onboarding states
        test_students = [
            {
                "name": "Alex Newcomer",
                "email": "alex.newcomer@student.com",
                "password": "student123",
                "onboarding_completed": False,  # Fresh newcomer
                "phone": None,
                "emergency_contact": None,
                "nickname": None
            },
            {
                "name": "Emma Fresh",
                "email": "emma.fresh@student.com", 
                "password": "student123",
                "onboarding_completed": True,   # ✅ Completed onboarding for E2E tests
                "phone": "+36301234567",
                "emergency_contact": "John Fresh (+36301234568)",
                "nickname": "emma_f"
            },
            {
                "name": "Mike Starter",
                "email": "mike.starter@student.com",
                "password": "student123",
                "onboarding_completed": False,  # Fresh newcomer
                "phone": None,
                "emergency_contact": None,
                "nickname": None
            }
        ]
        
        for student_data in test_students:
            student = User(
                name=student_data["name"],
                email=student_data["email"],
                password_hash=get_password_hash(student_data["password"]),
                role=UserRole.STUDENT,
                is_active=True,
                onboarding_completed=student_data["onboarding_completed"],
                phone=student_data["phone"],
                emergency_contact=student_data["emergency_contact"],
                nickname=student_data["nickname"],
                interests=None  # Empty interests for testing
            )
            self.db.add(student)
            
        self.db.commit()
        print("✅ Test users created!")
        
    def create_semesters_and_projects(self):
        """Create clean semester structure"""
        print("📅 Creating semesters and projects...")
        
        # Current semester
        current_semester = Semester(
            code="2025/1",
            name="Fall 2025",
            start_date=datetime(2025, 9, 1),
            end_date=datetime(2025, 12, 20),
            is_active=True
        )
        self.db.add(current_semester)
        self.db.commit()
        self.db.refresh(current_semester)
        
        # Get instructors
        instructors = self.db.query(User).filter(User.role == UserRole.INSTRUCTOR).all()
        
        # Create diverse projects for testing
        projects = [
            {
                "title": "Football Basics",
                "description": "Introduction to football fundamentals",
                "max_participants": 20,
                "difficulty": "beginner"
            },
            {
                "title": "Advanced Tennis Techniques", 
                "description": "Professional tennis skill development",
                "max_participants": 12,
                "difficulty": "advanced"
            },
            {
                "title": "Swimming Competition Prep",
                "description": "Competitive swimming training program", 
                "max_participants": 15,
                "difficulty": "intermediate"
            }
        ]
        
        for i, proj_data in enumerate(projects):
            project = Project(
                title=proj_data["title"],
                description=proj_data["description"],
                semester_id=current_semester.id,
                instructor_id=instructors[i % len(instructors)].id,
                max_participants=proj_data["max_participants"],
                status="active",
                difficulty=proj_data["difficulty"]
            )
            self.db.add(project)
            
        self.db.commit()
        print("✅ Projects created!")
        
    def create_clean_sessions(self):
        """Create future sessions for testing"""
        print("🏃 Creating clean future sessions...")
        
        instructors = self.db.query(User).filter(User.role == UserRole.INSTRUCTOR).all()
        current_semester = self.db.query(Semester).filter(Semester.is_active == True).first()
        
        # Create sessions for next 30 days
        base_date = datetime.now() + timedelta(days=1)
        
        session_templates = [
            {"title": "Morning Football Training", "sport": "Football", "level": "Beginner"},
            {"title": "Advanced Tennis Session", "sport": "Tennis", "level": "Advanced"}, 
            {"title": "Swimming Technique Class", "sport": "Swimming", "level": "Intermediate"},
            {"title": "Evening Football Practice", "sport": "Football", "level": "All Levels"}
        ]
        
        for day in range(30):
            session_date = base_date + timedelta(days=day)
            
            # Skip weekends for some variety
            if session_date.weekday() < 5:  # Monday-Friday
                for template in session_templates[:2]:  # 2 sessions per day
                    session = Session(
                        title=template["title"],
                        description=f"Clean test session - {template['sport']}",
                        instructor_id=random.choice(instructors).id,
                        semester_id=current_semester.id,
                        date_start=session_date.replace(hour=random.randint(9, 16)),
                        date_end=session_date.replace(hour=random.randint(17, 19)),
                        capacity=random.randint(10, 25),
                        location=f"Gym {random.randint(1, 3)}",
                        sport_type=template["sport"],
                        level=template["level"]
                    )
                    self.db.add(session)
                    
        self.db.commit()
        print("✅ Clean sessions created!")
        
    def run_fresh_reset(self):
        """Execute complete fresh reset"""
        print("🚀 Starting fresh database reset...\n")
        
        try:
            self.reset_database()
            self.create_test_users()
            self.create_semesters_and_projects()
            self.create_clean_sessions()
            
            print("\n🎉 FRESH DATABASE RESET COMPLETE!")
            print("\n📋 TEST ACCOUNTS:")
            print("Admin: admin@devstudio.com / admin123")
            print("Instructor: sarah.johnson@instructor.com / instructor123") 
            print("Fresh Student (no onboarding): alex.newcomer@student.com / student123")
            print("E2E Test Student (onboarding complete): emma.fresh@student.com / student123")
            print("Fresh Student (no onboarding): mike.starter@student.com / student123")
            print("\n✅ Ready for clean testing!")
            
        except Exception as e:
            print(f"❌ Error during reset: {e}")
            self.db.rollback()
            raise
        finally:
            self.db.close()

if __name__ == "__main__":
    reset = FreshDatabaseReset()
    reset.run_fresh_reset()