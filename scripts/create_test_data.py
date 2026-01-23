#!/usr/bin/env python3
"""
Test Data Creation Script for 1-Week Testing Period
Creates comprehensive test data for projects, quizzes, sessions and enrollments
"""

import sys
import os
import random
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import sessionmaker

# Add the project root to the path
from app.database import get_db
from app.models import (
    User, UserRole, Project, ProjectStatus, ProjectEnrollment, ProjectEnrollmentStatus,
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    Quiz, QuizQuestion, QuizAnswerOption, QuizAttempt, Session, Semester, Booking,
    Feedback, UserAchievement, UserStats, QuestionType,
    Message, Notification
)

def create_comprehensive_test_data():
    """Create comprehensive test data for 1-week testing period"""
    db = next(get_db())
    
    try:
        print("🚀 Creating Comprehensive Test Data for 1-Week Testing Period")
        print("=" * 65)
        
        # Get active semester (Fall 2025)
        active_semester = db.query(Semester).filter(Semester.is_active == True).first()
        if not active_semester:
            print("❌ No active semester found!")
            return
        
        print(f"📖 Using active semester: {active_semester.name} (ID: {active_semester.id})")
        
        # Get instructor and students
        instructors = db.query(User).filter(User.role == UserRole.INSTRUCTOR).all()
        students = db.query(User).filter(User.role == UserRole.STUDENT).all()
        
        if not instructors:
            print("❌ No instructors found!")
            return
        
        instructor = instructors[0]  # Use first instructor
        print(f"🎓 Using instructor: {instructor.name}")
        print(f"👥 Found {len(students)} student users")
        
        # Create Projects
        print("\n📁 Creating Test Projects...")
        
        # Get current time
        now = datetime.now(timezone.utc)
        
        projects_data = [
            {
                'title': 'Football Fundamentals 2025',
                'description': 'Learn the basic skills of football including passing, dribbling, and shooting. Perfect for beginners who want to master the fundamentals. Requirements: Basic fitness level, willingness to learn, football boots recommended.',
                'max_participants': 15,
                'difficulty': 'beginner',
                'xp_reward': 300
            },
            {
                'title': 'Advanced Tactics & Strategy',
                'description': 'Deep dive into modern football tactics, formations, and strategic thinking. Analyze professional games and develop tactical awareness. Requirements: Completed Football Fundamentals or equivalent experience.',
                'max_participants': 12,
                'difficulty': 'advanced',
                'xp_reward': 500
            },
            {
                'title': 'Goalkeeping Mastery',
                'description': 'Specialized training for aspiring goalkeepers. Learn positioning, shot-stopping, distribution, and mental aspects of goalkeeping. Requirements: Interest in goalkeeping, basic agility, goalkeeper gloves required.',
                'max_participants': 8,
                'difficulty': 'intermediate',
                'xp_reward': 400
            },
            {
                'title': 'Fitness & Conditioning',
                'description': 'Football-specific fitness program focusing on strength, endurance, speed, and injury prevention. Requirements: Medical clearance, basic fitness level.',
                'max_participants': 20,
                'difficulty': 'beginner',
                'xp_reward': 250
            },
            {
                'title': 'Youth Development Program',
                'description': 'Comprehensive development program for young players focusing on technical skills and character building. Requirements: Ages 14-18, parental consent, commitment to regular training.',
                'max_participants': 16,
                'difficulty': 'intermediate',
                'xp_reward': 350
            },
            {
                'title': 'Women\'s Football Excellence',
                'description': 'Dedicated program for women\'s football development, focusing on technical skills and tactical understanding. Requirements: Open to all skill levels, commitment to team environment.',
                'max_participants': 18,
                'difficulty': 'intermediate',
                'xp_reward': 350
            }
        ]
        
        created_projects = []
        for project_data in projects_data:
            # Create deadline in the future
            deadline = now + timedelta(days=60)  # 2 months from now
            
            project = Project(
                title=project_data['title'],
                description=project_data['description'],
                instructor_id=instructor.id,
                semester_id=active_semester.id,
                max_participants=project_data['max_participants'],
                difficulty=project_data['difficulty'],
                xp_reward=project_data['xp_reward'],
                deadline=deadline.date(),
                required_sessions=random.randint(6, 10),
                status=ProjectStatus.ACTIVE.value
            )
            db.add(project)
            db.flush()  # Get ID
            created_projects.append(project)
            print(f"  ✅ Created project: {project.title} (ID: {project.id})")
        
        # Create Project Enrollments (enroll students in various projects)
        print("\n👥 Creating Project Enrollments...")
        enrollment_count = 0
        for i, student in enumerate(students[:15]):  # Limit to first 15 students
            # Each student enrolls in 1-3 random projects
            num_projects = random.randint(1, 3)
            student_projects = random.sample(created_projects, num_projects)
            
            for project in student_projects:
                enrollment = ProjectEnrollment(
                    user_id=student.id,
                    project_id=project.id,
                    status=ProjectEnrollmentStatus.ACTIVE.value,
                    enrollment_status='approved',
                    quiz_passed=True,
                    completion_percentage=random.uniform(0.0, 75.0),
                    enrolled_at=datetime.now(timezone.utc)
                )
                db.add(enrollment)
                enrollment_count += 1
                
        print(f"  ✅ Created {enrollment_count} project enrollments")
        
        # Create Quizzes
        print("\n📝 Creating Test Quizzes...")
        quiz_data = [
            {
                'title': 'Football Rules & Regulations',
                'description': 'Test your knowledge of football rules, referee decisions, and game regulations.',
                'total_questions': 10,
                'passing_score': 70,
                'time_limit': 15,
                'questions': [
                    {
                        'question': 'How many players are on the field for each team during a football match?',
                        'options': ['10', '11', '12', '9'],
                        'correct_option': 1
                    },
                    {
                        'question': 'What is the duration of a standard football match?',
                        'options': ['80 minutes', '90 minutes', '100 minutes', '120 minutes'],
                        'correct_option': 1
                    },
                    {
                        'question': 'Which part of the body CANNOT be used to score a goal?',
                        'options': ['Head', 'Chest', 'Hand', 'Knee'],
                        'correct_option': 2
                    },
                    {
                        'question': 'What is the penalty area also known as?',
                        'options': ['Goal box', '18-yard box', 'Penalty box', 'All of the above'],
                        'correct_option': 3
                    },
                    {
                        'question': 'How many substitutions are allowed in a standard match?',
                        'options': ['3', '4', '5', '6'],
                        'correct_option': 2
                    },
                    {
                        'question': 'What happens when the ball completely crosses the sideline?',
                        'options': ['Corner kick', 'Goal kick', 'Throw-in', 'Free kick'],
                        'correct_option': 2
                    },
                    {
                        'question': 'What is the offside rule designed to prevent?',
                        'options': ['Rough play', 'Unfair advantage', 'Time wasting', 'Excessive celebration'],
                        'correct_option': 1
                    },
                    {
                        'question': 'Which card is shown for serious misconduct?',
                        'options': ['Yellow card', 'Red card', 'Blue card', 'Green card'],
                        'correct_option': 1
                    },
                    {
                        'question': 'What is the minimum number of players a team needs to continue a match?',
                        'options': ['9', '8', '7', '6'],
                        'correct_option': 2
                    },
                    {
                        'question': 'Who invented modern football?',
                        'options': ['Americans', 'Germans', 'English', 'Brazilians'],
                        'correct_option': 2
                    }
                ]
            },
            {
                'title': 'Football Tactics & Strategy',
                'description': 'Advanced quiz on football formations, tactical concepts, and strategic thinking.',
                'total_questions': 8,
                'passing_score': 75,
                'time_limit': 20,
                'questions': [
                    {
                        'question': 'What formation is known as "Total Football"?',
                        'options': ['4-4-2', '4-3-3', '3-5-2', '5-3-2'],
                        'correct_option': 1
                    },
                    {
                        'question': 'What does "pressing" mean in football?',
                        'options': ['Shooting hard', 'Defending aggressively', 'Passing quickly', 'Running fast'],
                        'correct_option': 1
                    },
                    {
                        'question': 'Which position is key in a 4-2-3-1 formation?',
                        'options': ['Centre-back', 'Attacking midfielder', 'Winger', 'Striker'],
                        'correct_option': 1
                    },
                    {
                        'question': 'What is a "false 9"?',
                        'options': ['Bad player', 'Deep-lying striker', 'Substitute', 'Injured player'],
                        'correct_option': 1
                    },
                    {
                        'question': 'What does "tiki-taka" refer to?',
                        'options': ['Fast breaks', 'Short passing style', 'Long balls', 'Physical play'],
                        'correct_option': 1
                    },
                    {
                        'question': 'What is the purpose of "parking the bus"?',
                        'options': ['Attack', 'Defend', 'Rest', 'Celebrate'],
                        'correct_option': 1
                    },
                    {
                        'question': 'Which team role controls the game tempo?',
                        'options': ['Striker', 'Midfielder', 'Defender', 'Goalkeeper'],
                        'correct_option': 1
                    },
                    {
                        'question': 'What is a "counter-attack"?',
                        'options': ['Defending', 'Quick transition to attack', 'Set piece', 'Substitution'],
                        'correct_option': 1
                    }
                ]
            },
            {
                'title': 'Physical Fitness & Training',
                'description': 'Quiz about football fitness, training methods, and injury prevention.',
                'total_questions': 6,
                'passing_score': 70,
                'time_limit': 12,
                'questions': [
                    {
                        'question': 'What type of training improves sprint speed?',
                        'options': ['Endurance', 'Plyometric', 'Flexibility', 'Balance'],
                        'correct_option': 1
                    },
                    {
                        'question': 'How long should a proper warm-up last?',
                        'options': ['5 minutes', '10-15 minutes', '30 minutes', '1 hour'],
                        'correct_option': 1
                    },
                    {
                        'question': 'What is most important for injury prevention?',
                        'options': ['Speed', 'Proper warm-up', 'Strength', 'Flexibility'],
                        'correct_option': 1
                    },
                    {
                        'question': 'When should you do static stretching?',
                        'options': ['Before training', 'After training', 'During training', 'Never'],
                        'correct_option': 1
                    },
                    {
                        'question': 'What improves agility the most?',
                        'options': ['Running', 'Ladder drills', 'Weight lifting', 'Swimming'],
                        'correct_option': 1
                    },
                    {
                        'question': 'How much water should you drink during training?',
                        'options': ['No water', 'Small sips regularly', 'Large amounts', 'Only after training'],
                        'correct_option': 1
                    }
                ]
            }
        ]
        
        created_quizzes = []
        for quiz_info in quiz_data:
            quiz = Quiz(
                title=quiz_info['title'],
                description=quiz_info['description'],
                instructor_id=instructor.id,
                semester_id=active_semester.id,
                total_questions=quiz_info['total_questions'],
                passing_score=quiz_info['passing_score'],
                time_limit=quiz_info['time_limit'],
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            db.add(quiz)
            db.flush()
            
            # Create questions for this quiz
            for q_data in quiz_info['questions']:
                question = QuizQuestion(
                    quiz_id=quiz.id,
                    question_text=q_data['question'],
                    question_type='multiple_choice',
                    points=10,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(question)
                db.flush()
                
                # Create options for this question
                for i, option_text in enumerate(q_data['options']):
                    option = QuizAnswerOption(
                        question_id=question.id,
                        option_text=option_text,
                        is_correct=(i == q_data['correct_option']),
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(option)
            
            created_quizzes.append(quiz)
            print(f"  ✅ Created quiz: {quiz.title} (ID: {quiz.id}, {quiz_info['total_questions']} questions)")
        
        # Create Sessions for the next week
        print("\n📅 Creating Test Sessions for Next Week...")
        now = datetime.now(timezone.utc)
        sessions_data = []
        
        # Create sessions for next 7 days
        for day in range(7):
            session_date = now + timedelta(days=day+1)
            
            # Morning session
            morning_start = session_date.replace(hour=9, minute=0, second=0, microsecond=0)
            morning_end = morning_start + timedelta(hours=2)
            
            sessions_data.append({
                'title': f'Morning Training - Day {day+1}',
                'description': f'Morning football training session focusing on technical skills and fitness. Date: {morning_start.strftime("%Y-%m-%d")}',
                'date_start': morning_start,
                'date_end': morning_end,
                'location': 'Main Training Ground',
                'capacity': 20
            })
            
            # Afternoon session (only on weekdays)
            if session_date.weekday() < 5:  # Monday to Friday
                afternoon_start = session_date.replace(hour=16, minute=0, second=0, microsecond=0)
                afternoon_end = afternoon_start + timedelta(hours=1, minutes=30)
                
                sessions_data.append({
                    'title': f'Tactical Training - Day {day+1}',
                    'description': f'Afternoon tactical training session focusing on game situations and strategy. Date: {afternoon_start.strftime("%Y-%m-%d")}',
                    'date_start': afternoon_start,
                    'date_end': afternoon_end,
                    'location': 'Tactical Field',
                    'capacity': 16
                })
        
        created_sessions = []
        for session_data in sessions_data:
            session = Session(
                title=session_data['title'],
                description=session_data['description'],
                instructor_id=instructor.id,
                semester_id=active_semester.id,
                date_start=session_data['date_start'],
                date_end=session_data['date_end'],
                location=session_data['location'],
                capacity=session_data['capacity'],
                current_bookings=0,
                created_at=datetime.now(timezone.utc)
            )
            db.add(session)
            db.flush()
            created_sessions.append(session)
            print(f"  ✅ Created session: {session.title} on {session.date_start.strftime('%Y-%m-%d %H:%M')}")
        
        # Create some bookings for sessions
        print("\n🎫 Creating Test Bookings...")
        booking_count = 0
        for session in created_sessions[:5]:  # Book first 5 sessions
            # Book 3-8 students randomly per session
            num_bookings = random.randint(3, min(8, len(students)))
            session_students = random.sample(students, num_bookings)
            
            for student in session_students:
                booking = Booking(
                    user_id=student.id,
                    session_id=session.id,
                    status='confirmed',
                    booking_date=datetime.now(timezone.utc),
                    created_at=datetime.now(timezone.utc)
                )
                db.add(booking)
                booking_count += 1
            
            # Update session booking count
            session.current_bookings = num_bookings
        
        print(f"  ✅ Created {booking_count} test bookings")
        
        # Create User Stats for students
        print("\n🏆 Creating User Statistics...")
        profile_count = 0
        for student in students:
            user_stats = UserStats(
                user_id=student.id,
                total_xp=random.randint(100, 1500),
                level=random.randint(1, 5),
                badges_earned=random.randint(0, 5),
                quizzes_completed=random.randint(0, 3),
                sessions_attended=random.randint(0, 8),
                projects_completed=random.randint(0, 2),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(user_stats)
            profile_count += 1
        
        print(f"  ✅ Created {profile_count} user statistics profiles")
        
        # Create some quiz attempts
        print("\n📊 Creating Quiz Attempts...")
        attempt_count = 0
        for quiz in created_quizzes:
            # Random students attempt each quiz
            attempting_students = random.sample(students, random.randint(3, 8))
            
            for student in attempting_students:
                attempt = QuizAttempt(
                    user_id=student.id,
                    quiz_id=quiz.id,
                    started_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 48)),
                    completed_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(0, 24)),
                    score=random.randint(60, 100),
                    time_spent_minutes=random.randint(5, quiz.time_limit),
                    passed=random.choice([True, True, False])  # 2/3 chance of passing
                )
                db.add(attempt)
                attempt_count += 1
        
        print(f"  ✅ Created {attempt_count} quiz attempts")
        
        # Commit all changes
        db.commit()
        
        # Final summary
        print("\n🎉 Test Data Creation Complete!")
        print("=" * 50)
        print(f"📁 Projects: {len(created_projects)}")
        print(f"📝 Quizzes: {len(created_quizzes)}")
        print(f"📅 Sessions: {len(created_sessions)}")
        print(f"👥 Project Enrollments: {enrollment_count}")
        print(f"🎫 Session Bookings: {booking_count}")
        print(f"🏆 User Statistics: {profile_count}")
        print(f"📊 Quiz Attempts: {attempt_count}")
        
        print("\n✅ Database is now ready for comprehensive 1-week testing!")
        print("🔍 Students can now:")
        print("  - View and join projects")
        print("  - Take quizzes and see results")
        print("  - Book training sessions")
        print("  - View gamification progress")
        print("  - Complete onboarding process")
        
    except Exception as e:
        print(f"❌ Error creating test data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_comprehensive_test_data()