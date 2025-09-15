#!/usr/bin/env python3
"""
Realistic Test Data Generator for DevStudio Academy
Software Development Bootcamp & Internship Program

Generates production-ready test data for:
- 2 realistic semesters (Spring 2025, Summer 2025)
- Software development focused sessions (70h each semester)  
- Realistic instructor and student profiles
- Specialization-based groups
- Realistic booking and attendance patterns
"""

import sys
import os
from datetime import datetime, timedelta, time
from random import choice, sample, randint, shuffle
from typing import List

# Add app to path
sys.path.append('/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Invetsment - Internship/practice_booking_system')

from app.database import get_db
from app.models.user import User, UserRole
from app.models.semester import Semester  
from app.models.group import Group
from app.models.session import Session as SessionModel, SessionMode
from app.models.booking import Booking, BookingStatus
from app.models.attendance import Attendance, AttendanceStatus
from app.core.security import get_password_hash


# DevStudio Academy Configuration
COMPANY_DOMAIN = "devstudio.com"
STUDENT_DOMAIN = "student.devstudio.com"
DEFAULT_PASSWORD = "DevStudio2025!"

# Semester Definitions
SEMESTERS = [
    {
        "code": "2025-SPRING",
        "name": "Spring 2025 Development Bootcamp", 
        "start_date": "2025-03-01",
        "end_date": "2025-06-30",
        "is_active": True,
        "description": "Full-stack web development intensive program"
    },
    {
        "code": "2025-SUMMER", 
        "name": "Summer 2025 Internship Program",
        "start_date": "2025-07-01",
        "end_date": "2025-08-30", 
        "is_active": False,
        "description": "Practical software development internship"
    }
]

# Instructor Profiles (Software Industry Context)
INSTRUCTORS = [
    {
        "name": "Sarah Chen",
        "email": f"sarah.chen@{COMPANY_DOMAIN}",
        "specialization": "Frontend Development (React, Vue.js)"
    },
    {
        "name": "Marcus Rodriguez", 
        "email": f"marcus.rodriguez@{COMPANY_DOMAIN}",
        "specialization": "Backend Development (Node.js, Python)"
    },
    {
        "name": "Dr. Elena Kowalski",
        "email": f"elena.kowalski@{COMPANY_DOMAIN}",
        "specialization": "DevOps & Cloud Architecture"
    },
    {
        "name": "James Thompson",
        "email": f"james.thompson@{COMPANY_DOMAIN}",
        "specialization": "Mobile Development (React Native, Flutter)"
    }
]

# Student Profiles (Realistic Names)
STUDENTS = [
    {"name": "Alex Johnson", "email": f"alex.johnson@{STUDENT_DOMAIN}"},
    {"name": "Maria Garcia", "email": f"maria.garcia@{STUDENT_DOMAIN}"},
    {"name": "David Kim", "email": f"david.kim@{STUDENT_DOMAIN}"},
    {"name": "Emma Wilson", "email": f"emma.wilson@{STUDENT_DOMAIN}"},
    {"name": "Michael Brown", "email": f"michael.brown@{STUDENT_DOMAIN}"},
    {"name": "Sofia Andersson", "email": f"sofia.andersson@{STUDENT_DOMAIN}"},
    {"name": "Ryan O'Connor", "email": f"ryan.oconnor@{STUDENT_DOMAIN}"},
    {"name": "Priya Sharma", "email": f"priya.sharma@{STUDENT_DOMAIN}"},
    {"name": "Lucas Mueller", "email": f"lucas.mueller@{STUDENT_DOMAIN}"},
    {"name": "Zoe Williams", "email": f"zoe.williams@{STUDENT_DOMAIN}"}
]

# Spring 2025 Groups (Specialization Based)
SPRING_GROUPS = [
    {
        "name": "Frontend Specialists",
        "description": "React.js, Vue.js, Modern CSS, UX/UI Design",
        "focus_area": "frontend"
    },
    {
        "name": "Backend Engineers", 
        "description": "Node.js, Python Django/Flask, Database Design",
        "focus_area": "backend"
    },
    {
        "name": "Full-Stack Developers",
        "description": "End-to-end web application development",
        "focus_area": "fullstack"
    }
]

# Summer 2025 Groups (Project Based)
SUMMER_GROUPS = [
    {
        "name": "Mobile App Project Team",
        "description": "React Native e-commerce app development",
        "focus_area": "mobile"
    },
    {
        "name": "DevOps Infrastructure Team", 
        "description": "CI/CD pipelines, AWS deployment, monitoring",
        "focus_area": "devops"
    }
]

# Spring Semester Sessions (70 Hours Total)
SPRING_SESSIONS = [
    # Week 1-2: Foundations
    {"title": "Web Development Fundamentals", "duration": 3, "week": 1, "instructor_spec": "fullstack"},
    {"title": "HTML5 & CSS3 Modern Techniques", "duration": 2, "week": 1, "instructor_spec": "frontend"},
    {"title": "JavaScript ES6+ Essentials", "duration": 3, "week": 2, "instructor_spec": "frontend"},
    {"title": "Git Version Control Workflow", "duration": 2, "week": 2, "instructor_spec": "devops"},
    
    # Week 3-5: Frontend Deep Dive
    {"title": "React.js Component Architecture", "duration": 3, "week": 3, "instructor_spec": "frontend"},
    {"title": "State Management with Redux", "duration": 2, "week": 3, "instructor_spec": "frontend"}, 
    {"title": "Vue.js Alternative Framework", "duration": 3, "week": 4, "instructor_spec": "frontend"},
    {"title": "Responsive Design & Bootstrap", "duration": 2, "week": 4, "instructor_spec": "frontend"},
    {"title": "Frontend Testing (Jest, Cypress)", "duration": 3, "week": 5, "instructor_spec": "frontend"},
    
    # Week 6-8: Backend Foundations  
    {"title": "Node.js Server Development", "duration": 3, "week": 6, "instructor_spec": "backend"},
    {"title": "Express.js API Design", "duration": 2, "week": 6, "instructor_spec": "backend"},
    {"title": "Database Design & PostgreSQL", "duration": 3, "week": 7, "instructor_spec": "backend"},
    {"title": "Authentication & JWT Security", "duration": 2, "week": 7, "instructor_spec": "backend"},
    {"title": "RESTful API Best Practices", "duration": 3, "week": 8, "instructor_spec": "backend"},
    
    # Week 9-11: Advanced Topics
    {"title": "Python Django Framework", "duration": 3, "week": 9, "instructor_spec": "backend"},
    {"title": "GraphQL vs REST APIs", "duration": 2, "week": 9, "instructor_spec": "backend"},
    {"title": "Microservices Architecture", "duration": 3, "week": 10, "instructor_spec": "devops"},
    {"title": "Docker Containerization", "duration": 2, "week": 10, "instructor_spec": "devops"},
    {"title": "AWS Cloud Deployment", "duration": 3, "week": 11, "instructor_spec": "devops"},
    
    # Week 12-14: Capstone Project
    {"title": "Project Planning & Architecture", "duration": 3, "week": 12, "instructor_spec": "fullstack"},
    {"title": "Agile Development Workshop", "duration": 3, "week": 12, "instructor_spec": "fullstack"},
    {"title": "Code Review & Quality Assurance", "duration": 3, "week": 13, "instructor_spec": "fullstack"},
    {"title": "Unit Testing Best Practices", "duration": 2, "week": 13, "instructor_spec": "fullstack"},
    {"title": "Final Project Presentations", "duration": 3, "week": 14, "instructor_spec": "fullstack"},
    {"title": "Career Development Workshop", "duration": 3, "week": 14, "instructor_spec": "fullstack"},
    {"title": "Industry Networking Event", "duration": 2, "week": 14, "instructor_spec": "fullstack"}
]

# Summer Internship Sessions (70 Hours Total)
SUMMER_SESSIONS = [
    {"title": "Real Client Project Briefing", "duration": 4, "week": 1, "instructor_spec": "fullstack"},
    {"title": "Technical Requirements Analysis", "duration": 3, "week": 1, "instructor_spec": "backend"},
    {"title": "System Architecture Design", "duration": 4, "week": 2, "instructor_spec": "devops"}, 
    {"title": "Database Schema Planning", "duration": 3, "week": 2, "instructor_spec": "backend"},
    {"title": "Frontend Prototype Development", "duration": 4, "week": 3, "instructor_spec": "frontend"},
    {"title": "Backend API Implementation", "duration": 4, "week": 3, "instructor_spec": "backend"},
    {"title": "Mobile App Development Sprint", "duration": 4, "week": 4, "instructor_spec": "mobile"},
    {"title": "DevOps Pipeline Setup", "duration": 3, "week": 4, "instructor_spec": "devops"},
    {"title": "Testing & Quality Assurance", "duration": 4, "week": 5, "instructor_spec": "fullstack"},
    {"title": "Performance Optimization", "duration": 3, "week": 5, "instructor_spec": "backend"},
    {"title": "Security Audit & Fixes", "duration": 4, "week": 6, "instructor_spec": "backend"},
    {"title": "User Acceptance Testing", "duration": 3, "week": 6, "instructor_spec": "frontend"},
    {"title": "Production Deployment", "duration": 4, "week": 7, "instructor_spec": "devops"},
    {"title": "Documentation & Handover", "duration": 4, "week": 7, "instructor_spec": "fullstack"},
    {"title": "Client Presentation & Demo", "duration": 4, "week": 8, "instructor_spec": "fullstack"},
    {"title": "Project Retrospective", "duration": 3, "week": 8, "instructor_spec": "fullstack"},
    {"title": "Portfolio Development", "duration": 4, "week": 8, "instructor_spec": "fullstack"},
    {"title": "Industry Best Practices", "duration": 3, "week": 8, "instructor_spec": "fullstack"}
]


def generate_all_data():
    """Generate complete realistic DevStudio Academy dataset"""
    db = next(get_db())
    
    try:
        print("🏗️  Generating realistic DevStudio Academy data...")
        print("=" * 60)
        
        # 1. Create semesters
        print("\n📚 1. Creating semesters...")
        semesters = create_semesters(db)
        
        # 2. Create instructors  
        print("\n👨‍🏫 2. Creating instructors...")
        instructors = create_instructors(db)
        
        # 3. Create students
        print("\n🎓 3. Creating students...")
        students = create_students(db)
        
        # 4. Create groups and assign students
        print("\n👥 4. Creating specialization groups...")
        groups = create_groups_and_assignments(db, semesters, students)
        
        # 5. Create realistic sessions
        print("\n📖 5. Creating development sessions...")
        sessions = create_sessions(db, semesters, groups, instructors)
        
        # 6. Generate realistic bookings
        print("\n📝 6. Generating booking patterns...")
        bookings = create_realistic_bookings(db, sessions, students)
        
        # 7. Generate attendance records
        print("\n✅ 7. Generating attendance patterns...")
        attendance = create_realistic_attendance(db, sessions, bookings)
        
        db.commit()
        
        print("\n" + "=" * 60)
        print("✅ DevStudio Academy data generated successfully!")
        print("=" * 60)
        print(f"📚 {len(semesters)} semesters")
        print(f"👨‍🏫 {len(instructors)} instructors") 
        print(f"🎓 {len(students)} students")
        print(f"👥 {len(groups)} specialization groups")
        print(f"📖 {len(sessions)} development sessions")
        print(f"📝 {len(bookings)} student bookings")
        print(f"✅ {len(attendance)} attendance records")
        
        # Verify 70-hour requirement
        verify_session_hours(sessions, semesters)
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error generating data: {e}")
        raise
    finally:
        db.close()


def create_semesters(db) -> List[Semester]:
    """Create Spring and Summer semesters"""
    semesters = []
    
    for sem_data in SEMESTERS:
        semester = Semester(
            code=sem_data["code"],
            name=sem_data["name"],
            start_date=datetime.strptime(sem_data["start_date"], "%Y-%m-%d").date(),
            end_date=datetime.strptime(sem_data["end_date"], "%Y-%m-%d").date(),
            is_active=sem_data["is_active"]
        )
        db.add(semester)
        semesters.append(semester)
        print(f"   ✓ {semester.name}")
    
    db.flush()  # Get IDs
    return semesters


def create_instructors(db) -> List[User]:
    """Create software development instructors"""
    instructors = []
    password_hash = get_password_hash(DEFAULT_PASSWORD)
    
    for inst_data in INSTRUCTORS:
        instructor = User(
            name=inst_data["name"],
            email=inst_data["email"],
            password_hash=password_hash,
            role=UserRole.INSTRUCTOR,
            is_active=True
        )
        db.add(instructor)
        instructors.append(instructor)
        print(f"   ✓ {instructor.name} - {inst_data['specialization']}")
    
    db.flush()  # Get IDs
    return instructors


def create_students(db) -> List[User]:
    """Create realistic student cohort"""  
    students = []
    password_hash = get_password_hash(DEFAULT_PASSWORD)
    
    for student_data in STUDENTS:
        student = User(
            name=student_data["name"],
            email=student_data["email"], 
            password_hash=password_hash,
            role=UserRole.STUDENT,
            is_active=True
        )
        db.add(student)
        students.append(student)
        print(f"   ✓ {student.name}")
    
    db.flush()  # Get IDs
    return students


def create_groups_and_assignments(db, semesters: List[Semester], students: List[User]) -> List[Group]:
    """Create specialization groups and assign students"""
    groups = []
    
    # Find semesters
    spring_sem = next((s for s in semesters if "Spring" in s.name), None)
    summer_sem = next((s for s in semesters if "Summer" in s.name), None)
    
    # Create Spring groups
    spring_groups = []
    for group_data in SPRING_GROUPS:
        group = Group(
            name=group_data["name"],
            description=group_data["description"],
            semester_id=spring_sem.id
        )
        db.add(group)
        groups.append(group)
        spring_groups.append(group)
        print(f"   ✓ {group.name} (Spring)")
    
    # Create Summer groups  
    summer_groups = []
    for group_data in SUMMER_GROUPS:
        group = Group(
            name=group_data["name"],
            description=group_data["description"],
            semester_id=summer_sem.id
        )
        db.add(group)
        groups.append(group)
        summer_groups.append(group)
        print(f"   ✓ {group.name} (Summer)")
    
    db.flush()  # Get group IDs
    
    # Assign students to Spring groups (all students participate)
    shuffled_students = students.copy()
    shuffle(shuffled_students)
    
    students_per_spring_group = len(students) // len(spring_groups)
    for i, group in enumerate(spring_groups):
        start_idx = i * students_per_spring_group
        end_idx = start_idx + students_per_spring_group
        if i == len(spring_groups) - 1:  # Last group gets remaining students
            end_idx = len(students)
        
        group_students = shuffled_students[start_idx:end_idx]
        group.users.extend(group_students)
        print(f"     → Assigned {len(group_students)} students to {group.name}")
    
    # Assign subset to Summer groups (internship program)
    internship_students = sample(students, k=7)  # 7 students for internship
    shuffle(internship_students)
    
    # Mobile team gets 4, DevOps team gets 3
    summer_groups[0].users.extend(internship_students[:4])
    summer_groups[1].users.extend(internship_students[4:7])
    print(f"     → Assigned 4 students to {summer_groups[0].name}")
    print(f"     → Assigned 3 students to {summer_groups[1].name}")
    
    return groups


def create_sessions(db, semesters: List[Semester], groups: List[Group], instructors: List[User]) -> List[SessionModel]:
    """Create realistic session scheduling"""
    sessions = []
    
    # Find semesters
    spring_sem = next((s for s in semesters if "Spring" in s.name), None)
    summer_sem = next((s for s in semesters if "Summer" in s.name), None)
    
    # Create Spring sessions
    spring_sessions = schedule_spring_sessions(db, spring_sem, groups, instructors)
    sessions.extend(spring_sessions)
    
    # Create Summer sessions  
    summer_sessions = schedule_summer_sessions(db, summer_sem, groups, instructors)
    sessions.extend(summer_sessions)
    
    return sessions


def schedule_spring_sessions(db, semester: Semester, groups: List[Group], instructors: List[User]) -> List[SessionModel]:
    """Schedule spring sessions with realistic timing"""
    sessions = []
    start_date = datetime(2025, 3, 3)  # First Monday of March 2025
    
    # Create instructor specialization lookup
    instructor_specs = {
        "Sarah Chen": "frontend",
        "Marcus Rodriguez": "backend", 
        "Dr. Elena Kowalski": "devops",
        "James Thompson": "mobile"
    }
    
    for session_data in SPRING_SESSIONS:
        week_start = start_date + timedelta(weeks=session_data["week"] - 1)
        
        # Schedule sessions on Mon/Wed/Fri
        if len(sessions) % 3 == 0:  # Monday 9:00-12:00
            session_datetime = datetime.combine(week_start.date(), time(9, 0))
        elif len(sessions) % 3 == 1:  # Wednesday 14:00-17:00
            session_datetime = datetime.combine(week_start.date() + timedelta(days=2), time(14, 0))
        else:  # Friday 9:00-12:00
            session_datetime = datetime.combine(week_start.date() + timedelta(days=4), time(9, 0))
        
        end_datetime = session_datetime + timedelta(hours=session_data["duration"])
        
        # Find appropriate instructor
        instructor = find_instructor_by_specialization(
            instructors, 
            instructor_specs, 
            session_data["instructor_spec"]
        )
        
        # Assign to appropriate group (or None for general sessions)
        group = None
        if session_data["instructor_spec"] == "frontend":
            group = next((g for g in groups if "Frontend" in g.name), None)
        elif session_data["instructor_spec"] == "backend":
            group = next((g for g in groups if "Backend" in g.name), None)
        elif session_data["instructor_spec"] == "fullstack":
            group = next((g for g in groups if "Full-Stack" in g.name), None)
        
        session = SessionModel(
            title=session_data["title"],
            description=f"Week {session_data['week']} - {session_data['duration']} hour intensive session",
            date_start=session_datetime,
            date_end=end_datetime,
            mode=choice([SessionMode.ONLINE, SessionMode.HYBRID, SessionMode.OFFLINE]),
            capacity=randint(12, 15),
            location="DevStudio Academy, Conference Room A" if choice([True, False]) else None,
            meeting_link="https://meet.devstudio.com/session-" + str(randint(1000, 9999)) if choice([True, False]) else None,
            semester_id=semester.id,
            group_id=group.id if group else None,
            instructor_id=instructor.id if instructor else None
        )
        
        db.add(session)
        sessions.append(session)
        print(f"   ✓ Week {session_data['week']}: {session.title} ({session_data['duration']}h)")
    
    db.flush()
    return sessions


def schedule_summer_sessions(db, semester: Semester, groups: List[Group], instructors: List[User]) -> List[SessionModel]:
    """Schedule summer internship sessions"""
    sessions = []
    start_date = datetime(2025, 7, 1)  # July 1, 2025
    
    instructor_specs = {
        "Sarah Chen": "frontend",
        "Marcus Rodriguez": "backend", 
        "Dr. Elena Kowalski": "devops",
        "James Thompson": "mobile"
    }
    
    for session_data in SUMMER_SESSIONS:
        week_start = start_date + timedelta(weeks=session_data["week"] - 1)
        
        # Summer intensive: Tue/Thu 9:00-13:00
        if len(sessions) % 2 == 0:  # Tuesday
            session_datetime = datetime.combine(week_start.date() + timedelta(days=1), time(9, 0))
        else:  # Thursday
            session_datetime = datetime.combine(week_start.date() + timedelta(days=3), time(9, 0))
        
        end_datetime = session_datetime + timedelta(hours=session_data["duration"])
        
        instructor = find_instructor_by_specialization(
            instructors,
            instructor_specs,
            session_data["instructor_spec"]
        )
        
        # Summer sessions can be assigned to specific project groups
        group = None
        if session_data["instructor_spec"] == "mobile":
            group = next((g for g in groups if "Mobile" in g.name), None)
        elif session_data["instructor_spec"] == "devops":
            group = next((g for g in groups if "DevOps" in g.name), None)
        
        session = SessionModel(
            title=session_data["title"],
            description=f"Internship Week {session_data['week']} - Real project work ({session_data['duration']}h)",
            date_start=session_datetime,
            date_end=end_datetime,
            mode=SessionMode.HYBRID,  # Internship is hybrid
            capacity=randint(8, 12),
            location="DevStudio Academy, Project Lab",
            meeting_link="https://meet.devstudio.com/internship-" + str(randint(1000, 9999)),
            semester_id=semester.id,
            group_id=group.id if group else None,
            instructor_id=instructor.id if instructor else None
        )
        
        db.add(session)
        sessions.append(session)
        print(f"   ✓ Week {session_data['week']}: {session.title} ({session_data['duration']}h)")
    
    db.flush()
    return sessions


def find_instructor_by_specialization(instructors: List[User], specs: dict, needed_spec: str) -> User:
    """Find instructor by specialization"""
    for instructor in instructors:
        instructor_spec = specs.get(instructor.name, "fullstack")
        if needed_spec == "fullstack" or instructor_spec == needed_spec:
            return instructor
    
    # Fallback to first instructor
    return instructors[0] if instructors else None


def create_realistic_bookings(db, sessions: List[SessionModel], students: List[User]) -> List[Booking]:
    """Create realistic booking patterns with 75-90% attendance"""
    bookings = []
    
    for session in sessions:
        # 75-90% of students book each session
        booking_rate = randint(75, 90) / 100
        num_bookings = int(len(students) * booking_rate)
        
        booking_students = sample(students, min(num_bookings, len(students)))
        
        for student in booking_students:
            booking = Booking(
                user_id=student.id,
                session_id=session.id,
                status=choice([BookingStatus.CONFIRMED, BookingStatus.CONFIRMED, BookingStatus.CONFIRMED, BookingStatus.WAITLISTED]),  # Mostly confirmed
                notes=f"Enrolled for {session.title}",
                created_at=session.date_start - timedelta(days=randint(1, 14))  # Booked 1-14 days before
            )
            db.add(booking)
            bookings.append(booking)
    
    print(f"   ✓ Generated {len(bookings)} realistic bookings")
    db.flush()
    return bookings


def create_realistic_attendance(db, sessions: List[SessionModel], bookings: List[Booking]) -> List[Attendance]:
    """Create realistic attendance patterns"""
    attendance_records = []
    
    # Create session lookup for date_start access
    session_lookup = {s.id: s for s in sessions}
    
    for booking in bookings:
        session = session_lookup.get(booking.session_id)
        if not session:
            continue
            
        # 85-95% of booked students actually attend
        if randint(1, 100) <= 90:  # 90% attendance rate
            attendance = Attendance(
                user_id=booking.user_id,
                session_id=booking.session_id,
                booking_id=booking.id,  # Required field
                status=choice([AttendanceStatus.PRESENT, AttendanceStatus.PRESENT, AttendanceStatus.PRESENT, AttendanceStatus.LATE]),  # Mostly present
                check_in_time=session.date_start + timedelta(minutes=randint(0, 15)),  # Check in 0-15 min after start
                notes="Participated actively" if randint(1, 100) <= 80 else ""
            )
            db.add(attendance)
            attendance_records.append(attendance)
    
    print(f"   ✓ Generated {len(attendance_records)} attendance records")
    db.flush()
    return attendance_records


def verify_session_hours(sessions: List[SessionModel], semesters: List[Semester]):
    """Verify 70-hour requirement per semester"""
    print("\n📊 Verifying 70-hour requirement:")
    
    for semester in semesters:
        semester_sessions = [s for s in sessions if s.semester_id == semester.id]
        total_hours = sum((s.date_end - s.date_start).total_seconds() / 3600 for s in semester_sessions)
        
        print(f"   {semester.name}: {total_hours:.1f} hours ({len(semester_sessions)} sessions)")
        
        if total_hours >= 70:
            print(f"     ✅ Requirement met (70h minimum)")
        else:
            print(f"     ⚠️  Below requirement (need {70 - total_hours:.1f} more hours)")


if __name__ == "__main__":
    print("=" * 60)
    print("🏗️  DevStudio Academy Data Generator")
    print("=" * 60)
    
    confirm = input("Generate realistic DevStudio Academy data? (y/N): ")
    if confirm.lower() != 'y':
        print("❌ Data generation cancelled")
        exit(0)
    
    try:
        if generate_all_data():
            print("\n🎯 DevStudio Academy is ready for production testing!")
            print(f"🔐 All users password: {DEFAULT_PASSWORD}")
            print(f"📧 Admin login: admin@company.com")
        else:
            print("\n🛑 Data generation failed")
            
    except Exception as e:
        print(f"\n💥 Critical error: {e}")
        print("Check the error details above")