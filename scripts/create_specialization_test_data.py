#!/usr/bin/env python3
"""
Create enhanced test data with specialization support for frontend testing.
This script creates sessions and projects with various specialization configurations.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from app.database import get_db
from app.models import Session as SessionModel, Project, User, Semester, UserRole
from app.models.specialization import SpecializationType

def create_test_data():
    """Create enhanced test data with specialization support."""
    db = next(get_db())
    
    try:
        print("🎯 Creating specialization test data...")
        
        # Get current semester and instructor
        current_semester = db.query(Semester).filter(Semester.is_active == True).first()
        if not current_semester:
            current_semester = db.query(Semester).order_by(Semester.id.desc()).first()
        
        instructor = db.query(User).filter(User.role == UserRole.INSTRUCTOR).first()
        if not instructor:
            print("❌ No instructor found! Please create an instructor first.")
            return
        
        print(f"📚 Using semester: {current_semester.name} (ID: {current_semester.id})")
        print(f"👨‍🏫 Using instructor: {instructor.name} (ID: {instructor.id})")
        
        # Create sessions with different specialization configurations
        sessions_data = [
            {
                'title': 'Player Technical Skills Training',
                'description': 'Advanced ball control, passing, and shooting techniques for players',
                'sport_type': 'football',
                'level': 'intermediate',
                'target_specialization': SpecializationType.PLAYER,
                'mixed_specialization': False,
                'location': 'Field A',
                'capacity': 16
            },
            {
                'title': 'Coaching Methodology Workshop',
                'description': 'Session planning, player psychology, and tactical analysis for coaches',
                'sport_type': 'programming',
                'level': 'advanced',
                'target_specialization': SpecializationType.COACH,
                'mixed_specialization': False,
                'location': 'Conference Room',
                'capacity': 12
            },
            {
                'title': 'Mixed Training: Strategy & Practice',
                'description': 'Combined session where coaches and players work together on tactics',
                'sport_type': 'football',
                'level': 'all levels',
                'target_specialization': None,
                'mixed_specialization': True,
                'location': 'Main Field',
                'capacity': 20
            },
            {
                'title': 'Player Fitness & Conditioning',
                'description': 'Physical preparation and endurance training for competitive players',
                'sport_type': 'fitness',
                'level': 'intermediate',
                'target_specialization': SpecializationType.PLAYER,
                'mixed_specialization': False,
                'location': 'Gym',
                'capacity': 14
            },
            {
                'title': 'Coach Education: Youth Development',
                'description': 'Specialized techniques for working with young players',
                'sport_type': 'programming',
                'level': 'beginner',
                'target_specialization': SpecializationType.COACH,
                'mixed_specialization': False,
                'location': 'Classroom B',
                'capacity': 10
            },
            {
                'title': 'General Football Skills (Open)',
                'description': 'Basic football skills open to all participants',
                'sport_type': 'football',
                'level': 'beginner',
                'target_specialization': None,
                'mixed_specialization': False,
                'location': 'Field B',
                'capacity': 18
            }
        ]
        
        created_sessions = []
        base_date = datetime.now() + timedelta(days=7)  # Start sessions next week
        
        for i, session_data in enumerate(sessions_data):
            # Stagger sessions over the next few weeks
            session_date = base_date + timedelta(days=i*2, hours=10+i)  # Different times
            
            session = SessionModel(
                title=session_data['title'],
                description=session_data['description'],
                instructor_id=instructor.id,
                semester_id=current_semester.id,
                date_start=session_date,
                date_end=session_date + timedelta(hours=1, minutes=30),
                capacity=session_data['capacity'],
                location=session_data['location'],
                sport_type=session_data['sport_type'],
                level=session_data['level'],
                target_specialization=session_data['target_specialization'],
                mixed_specialization=session_data['mixed_specialization']
            )
            
            db.add(session)
            created_sessions.append(session)
            
        # Create projects with specialization support
        projects_data = [
            {
                'title': 'Player Performance Analytics',
                'description': 'Analysis of individual player statistics and improvement areas',
                'target_specialization': SpecializationType.PLAYER,
                'mixed_specialization': False,
                'max_participants': 8,
                'xp_reward': 150,
                'required_sessions': 6,
                'difficulty': 'intermediate'
            },
            {
                'title': 'Coaching Certification Program',
                'description': 'Complete certification pathway for aspiring football coaches',
                'target_specialization': SpecializationType.COACH,
                'mixed_specialization': False,
                'max_participants': 6,
                'xp_reward': 200,
                'required_sessions': 8,
                'difficulty': 'advanced'
            },
            {
                'title': 'Team Building & Communication',
                'description': 'Joint project focusing on team dynamics and leadership',
                'target_specialization': None,
                'mixed_specialization': True,
                'max_participants': 12,
                'xp_reward': 120,
                'required_sessions': 4,
                'difficulty': 'beginner'
            },
            {
                'title': 'Youth Player Development',
                'description': 'Specialized training methods for young football talent',
                'target_specialization': SpecializationType.PLAYER,
                'mixed_specialization': False,
                'max_participants': 10,
                'xp_reward': 180,
                'required_sessions': 7,
                'difficulty': 'intermediate'
            },
            {
                'title': 'Strategic Game Analysis',
                'description': 'Advanced tactical analysis and game planning techniques',
                'target_specialization': SpecializationType.COACH,
                'mixed_specialization': False,
                'max_participants': 8,
                'xp_reward': 250,
                'required_sessions': 10,
                'difficulty': 'advanced'
            }
        ]
        
        created_projects = []
        
        for project_data in projects_data:
            project = Project(
                title=project_data['title'],
                description=project_data['description'],
                instructor_id=instructor.id,
                semester_id=current_semester.id,
                target_specialization=project_data['target_specialization'],
                mixed_specialization=project_data['mixed_specialization'],
                max_participants=project_data['max_participants'],
                xp_reward=project_data['xp_reward'],
                required_sessions=project_data['required_sessions'],
                difficulty=project_data['difficulty'],
                deadline=datetime.now() + timedelta(days=60),  # 2 months from now
                status='active'
            )
            
            db.add(project)
            created_projects.append(project)
        
        # Commit all changes
        db.commit()
        
        print(f"✅ Created {len(created_sessions)} specialized sessions:")
        for session in created_sessions:
            spec_info = ""
            if session.target_specialization:
                spec_info = f" (🎯 {session.target_specialization.value})"
            elif session.mixed_specialization:
                spec_info = " (🤝 Mixed)"
            else:
                spec_info = " (👥 Open)"
            print(f"  • {session.title}{spec_info}")
        
        print(f"\n✅ Created {len(created_projects)} specialized projects:")
        for project in created_projects:
            spec_info = ""
            if project.target_specialization:
                spec_info = f" (🎯 {project.target_specialization.value})"
            elif project.mixed_specialization:
                spec_info = " (🤝 Mixed)"
            else:
                spec_info = " (👥 Open)"
            print(f"  • {project.title}{spec_info}")
        
        print(f"\n🎉 Specialization test data creation complete!")
        print(f"📍 All sessions and projects are assigned to {instructor.name}")
        print(f"📅 Sessions scheduled starting from {base_date.strftime('%Y-%m-%d %H:%M')}")
        
    except Exception as e:
        print(f"❌ Error creating test data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_test_data()