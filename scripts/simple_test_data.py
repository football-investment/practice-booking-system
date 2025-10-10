#!/usr/bin/env python3
"""
Simple Test Data Creation Script
Creates basic test data for projects and quizzes
"""

import sys
import os
from datetime import datetime, timedelta, timezone

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db
from app.models import (
    User, UserRole, Project, ProjectStatus, ProjectEnrollment, ProjectEnrollmentStatus,
    Quiz, QuizQuestion, QuizAnswerOption, QuizAttempt, Session, Semester,
    QuestionType, QuizCategory, QuizDifficulty
)

def create_simple_test_data():
    """Create simple test data"""
    db = next(get_db())
    
    try:
        print("🚀 Creating Simple Test Data")
        print("=" * 30)
        
        # Get active semester
        active_semester = db.query(Semester).filter(Semester.is_active == True).first()
        if not active_semester:
            print("❌ No active semester found!")
            return
        
        print(f"📖 Using semester: {active_semester.name}")
        
        # Get instructor and students
        instructor = db.query(User).filter(User.role == UserRole.INSTRUCTOR).first()
        students = db.query(User).filter(User.role == UserRole.STUDENT).limit(10).all()
        
        if not instructor:
            print("❌ No instructors found!")
            return
        
        print(f"🎓 Using instructor: {instructor.name}")
        print(f"👥 Found {len(students)} students")
        
        # Create 3 simple projects
        print("\n📁 Creating Projects...")
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(days=60)
        
        projects_data = [
            {
                'title': 'Football Fundamentals',
                'description': 'Learn basic football skills',
                'difficulty': 'beginner',
                'xp_reward': 300
            },
            {
                'title': 'Advanced Tactics',
                'description': 'Master football tactics and strategy',
                'difficulty': 'advanced', 
                'xp_reward': 500
            },
            {
                'title': 'Goalkeeping Mastery',
                'description': 'Specialized goalkeeper training',
                'difficulty': 'intermediate',
                'xp_reward': 400
            }
        ]
        
        created_projects = []
        for project_data in projects_data:
            project = Project(
                title=project_data['title'],
                description=project_data['description'],
                instructor_id=instructor.id,
                semester_id=active_semester.id,
                max_participants=15,
                difficulty=project_data['difficulty'],
                xp_reward=project_data['xp_reward'],
                deadline=deadline.date(),
                required_sessions=8,
                status=ProjectStatus.ACTIVE.value
            )
            db.add(project)
            db.flush()
            created_projects.append(project)
            print(f"  ✅ Created: {project.title}")
        
        # Enroll some students in projects
        print("\n👥 Creating Enrollments...")
        enrollment_count = 0
        for student in students[:6]:  # First 6 students
            for project in created_projects[:2]:  # First 2 projects
                enrollment = ProjectEnrollment(
                    user_id=student.id,
                    project_id=project.id,
                    status=ProjectEnrollmentStatus.ACTIVE.value,
                    enrollment_status='approved',
                    quiz_passed=True,
                    completion_percentage=25.0,
                    enrolled_at=now
                )
                db.add(enrollment)
                enrollment_count += 1
        
        print(f"  ✅ Created {enrollment_count} enrollments")
        
        # Create 2 simple quizzes
        print("\n📊 Creating Quizzes...")
        quizzes_data = [
            {
                'title': 'Football Rules Quiz',
                'description': 'Test your knowledge of football rules',
                'questions': [
                    {
                        'text': 'How many players are on the field for each team?',
                        'options': ['9', '10', '11', '12'],
                        'correct': 2
                    },
                    {
                        'text': 'What is offside?',
                        'options': ['Being behind the goal line', 'Being ahead of the last defender', 'Touching the ball with hands', 'Fouling an opponent'],
                        'correct': 1
                    }
                ]
            },
            {
                'title': 'Basic Tactics Quiz', 
                'description': 'Understanding football formations and tactics',
                'questions': [
                    {
                        'text': 'What does 4-4-2 formation mean?',
                        'options': ['4 defenders, 4 midfielders, 2 forwards', '4 goals, 4 assists, 2 cards', '4 minutes, 4 seconds, 2 hours', '4 teams, 4 games, 2 wins'],
                        'correct': 0
                    }
                ]
            }
        ]
        
        created_quizzes = []
        for quiz_data in quizzes_data:
            quiz = Quiz(
                title=quiz_data['title'],
                description=quiz_data['description'],
                category=QuizCategory.SPORTS_PHYSIOLOGY,
                difficulty=QuizDifficulty.EASY,
                passing_score=70.0,
                time_limit_minutes=15,
                xp_reward=100,
                is_active=True
            )
            db.add(quiz)
            db.flush()
            created_quizzes.append(quiz)
            
            # Add questions
            for q_data in quiz_data['questions']:
                question = QuizQuestion(
                    quiz_id=quiz.id,
                    question_text=q_data['text'],
                    question_type=QuestionType.MULTIPLE_CHOICE,
                    points=10,
                    order_index=0
                )
                db.add(question)
                db.flush()
                
                # Add options
                for i, option_text in enumerate(q_data['options']):
                    option = QuizAnswerOption(
                        question_id=question.id,
                        option_text=option_text,
                        is_correct=(i == q_data['correct']),
                        order_index=i
                    )
                    db.add(option)
            
            print(f"  ✅ Created quiz: {quiz.title}")
        
        # Commit all changes
        db.commit()
        
        print("\n✅ Simple test data creation completed!")
        print(f"📁 Projects: {len(created_projects)}")
        print(f"👥 Enrollments: {enrollment_count}")
        print(f"📊 Quizzes: {len(created_quizzes)}")
        
        print("\n🔍 Students can now:")
        print("  - View and enroll in projects")
        print("  - Take quizzes")
        print("  - See their progress")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating test data: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    create_simple_test_data()