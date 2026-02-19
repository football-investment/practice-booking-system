#!/usr/bin/env python3
"""
Create Sample Quiz Attempts for Testing XP and Gamification
"""

import sys
import os
from datetime import datetime, timezone, timedelta
import random

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db
from app.models import (
    User, UserRole, Quiz, QuizAttempt, QuizQuestion, 
    QuizAnswerOption, QuizUserAnswer, UserStats, UserAchievement, BadgeType
)

def create_quiz_attempts():
    """Create sample quiz attempts for testing"""
    db = next(get_db())
    
    try:
        print("🎮 Creating Sample Quiz Attempts for Gamification Testing")
        print("=" * 60)
        
        # Get test users and quizzes
        test_users = db.query(User).filter(
            User.email.in_([
                'alice.cooper@student.devstudio.com',
                'diana.ross@student.devstudio.com', 
                'eddie.murphy@student.devstudio.com',
                'george.clooney@student.devstudio.com',
                'helen.hunt@student.devstudio.com'
            ])
        ).all()
        
        quizzes = db.query(Quiz).all()
        
        print(f"👥 Found {len(test_users)} test users")
        print(f"📊 Found {len(quizzes)} quizzes")
        
        if not test_users or not quizzes:
            print("❌ Missing test users or quizzes!")
            return
        
        created_attempts = []
        now = datetime.now(timezone.utc)
        
        # Create quiz attempts with different performance levels
        for user in test_users:
            print(f"\n🎯 Creating attempts for {user.name}...")
            
            # Each user attempts 3-5 quizzes with different success rates
            user_quizzes = random.sample(quizzes, min(random.randint(3, 5), len(quizzes)))
            
            for quiz in user_quizzes:
                # Get quiz questions
                questions = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).all()
                
                if not questions:
                    continue
                
                # Create attempt
                attempt_time = now - timedelta(days=random.randint(1, 7), hours=random.randint(0, 23))
                completion_time = attempt_time + timedelta(minutes=random.randint(5, quiz.time_limit_minutes))
                
                # Simulate different performance levels based on quiz difficulty
                if quiz.difficulty.value == 'easy':
                    success_rate = random.uniform(0.7, 0.95)  # 70-95% for easy
                elif quiz.difficulty.value == 'medium':
                    success_rate = random.uniform(0.6, 0.85)  # 60-85% for medium
                else:  # hard
                    success_rate = random.uniform(0.45, 0.75)  # 45-75% for hard
                
                correct_answers = int(len(questions) * success_rate)
                total_questions = len(questions)
                score = (correct_answers / total_questions) * 100
                passed = score >= quiz.passing_score
                
                # Calculate XP awarded (full XP if passed, partial if not)
                xp_awarded = quiz.xp_reward if passed else int(quiz.xp_reward * 0.3)
                
                attempt = QuizAttempt(
                    user_id=user.id,
                    quiz_id=quiz.id,
                    started_at=attempt_time,
                    completed_at=completion_time,
                    time_spent_minutes=(completion_time - attempt_time).total_seconds() / 60,
                    score=score,
                    total_questions=total_questions,
                    correct_answers=correct_answers,
                    xp_awarded=xp_awarded,
                    passed=passed
                )
                
                db.add(attempt)
                db.flush()
                created_attempts.append(attempt)
                
                # Create user answers for each question
                correct_count = 0
                shuffled_questions = list(questions)
                random.shuffle(shuffled_questions)
                
                for i, question in enumerate(shuffled_questions):
                    # Get answer options
                    options = db.query(QuizAnswerOption).filter(
                        QuizAnswerOption.question_id == question.id
                    ).all()
                    
                    if not options:
                        continue
                    
                    # Determine if this answer should be correct based on target success rate
                    should_be_correct = correct_count < correct_answers
                    
                    if should_be_correct:
                        # Select correct answer
                        selected_option = next((opt for opt in options if opt.is_correct), options[0])
                        is_correct = True
                        correct_count += 1
                    else:
                        # Select random incorrect answer
                        incorrect_options = [opt for opt in options if not opt.is_correct]
                        selected_option = random.choice(incorrect_options) if incorrect_options else options[0]
                        is_correct = selected_option.is_correct
                        if is_correct:
                            correct_count += 1
                    
                    user_answer = QuizUserAnswer(
                        attempt_id=attempt.id,
                        question_id=question.id,
                        selected_option_id=selected_option.id,
                        is_correct=is_correct,
                        answered_at=attempt_time + timedelta(seconds=i*30)
                    )
                    db.add(user_answer)
                
                status_emoji = "✅" if passed else "❌"
                print(f"  {status_emoji} {quiz.title}: {score:.1f}% ({correct_answers}/{total_questions}) - {xp_awarded} XP")
        
        # Update user statistics based on attempts
        print(f"\n📊 Updating User Statistics...")
        
        for user in test_users:
            user_attempts = [a for a in created_attempts if a.user_id == user.id]
            
            total_xp = sum(a.xp_awarded for a in user_attempts)
            total_quizzes = len(user_attempts)
            passed_quizzes = sum(1 for a in user_attempts if a.passed)
            
            # Calculate level based on XP (every 100 XP = 1 level)
            level = min(int(total_xp / 100) + 1, 10)  # Cap at level 10
            
            # Check if user already has stats
            user_stats = db.query(UserStats).filter(UserStats.user_id == user.id).first()
            
            if user_stats:
                # Update existing stats
                user_stats.total_xp = total_xp
                user_stats.level = level
                user_stats.updated_at = now
            else:
                # Create new stats
                user_stats = UserStats(
                    user_id=user.id,
                    total_xp=total_xp,
                    level=level,
                    semesters_participated=1,
                    total_bookings=random.randint(5, 15),
                    total_attended=random.randint(3, 12),
                    total_cancelled=random.randint(0, 3),
                    attendance_rate=random.uniform(0.6, 0.95),
                    feedback_given=random.randint(1, 8),
                    average_rating_given=random.uniform(3.5, 5.0),
                    punctuality_score=random.uniform(0.7, 1.0),
                    created_at=now,
                    updated_at=now
                )
                db.add(user_stats)
            
            # Create achievement badges for high performers
            if passed_quizzes > 0:
                # First quiz completion badge
                existing_quiz_badge = db.query(UserAchievement).filter(
                    UserAchievement.user_id == user.id,
                    UserAchievement.badge_type == BadgeType.FIRST_QUIZ_COMPLETED.value
                ).first()
                
                if not existing_quiz_badge:
                    quiz_badge = UserAchievement(
                        user_id=user.id,
                        badge_type=BadgeType.FIRST_QUIZ_COMPLETED.value,
                        title="Quiz Master",
                        description="Completed your first quiz successfully",
                        icon="🧠",
                        earned_at=now
                    )
                    db.add(quiz_badge)
            
            if level >= 3:
                # Veteran student badge for level 3+
                existing_veteran_badge = db.query(UserAchievement).filter(
                    UserAchievement.user_id == user.id,
                    UserAchievement.badge_type == BadgeType.VETERAN_STUDENT.value
                ).first()
                
                if not existing_veteran_badge:
                    veteran_badge = UserAchievement(
                        user_id=user.id,
                        badge_type=BadgeType.VETERAN_STUDENT.value,
                        title="Experienced Player",
                        description="Reached level 3 through consistent performance",
                        icon="⭐",
                        earned_at=now
                    )
                    db.add(veteran_badge)
            
            print(f"  📈 {user.name}: Level {level}, {total_xp} XP, {passed_quizzes}/{total_quizzes} passed")
        
        # Commit all changes
        db.commit()
        
        # Final summary
        print("\n🎯 Quiz Attempts and Gamification System Ready!")
        print("=" * 50)
        print(f"🎮 Total Quiz Attempts: {len(created_attempts)}")
        print(f"✅ Successful Attempts: {sum(1 for a in created_attempts if a.passed)}")
        print(f"❌ Failed Attempts: {sum(1 for a in created_attempts if not a.passed)}")
        print(f"🎖️  Total XP Distributed: {sum(a.xp_awarded for a in created_attempts)}")
        
        print("\n🔍 Test Users Can Now See:")
        print("  - Quiz completion history")
        print("  - XP progress and level advancement")
        print("  - Performance statistics")
        print("  - Achievement badges")
        print("  - Leaderboard rankings")
        
        print("\n📱 Ready for comprehensive mobile testing!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating quiz attempts: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    create_quiz_attempts()