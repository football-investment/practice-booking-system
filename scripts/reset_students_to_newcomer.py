#!/usr/bin/env python3
"""
Student Status Reset Script - "Clean Slate" for Testing

This script resets ALL students to a "newcomer" status by:
1. Clearing all project enrollments 
2. Clearing all quiz attempts and results
3. Clearing quiz enrollment records
4. Resetting gamification data (XP, achievements)
5. Resetting onboarding status to incomplete
6. Clearing any progress tracking data

Usage:
    python reset_students_to_newcomer.py [--dry-run] [--confirm]
"""

import sys
import os
from datetime import datetime, timezone
import argparse

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import get_db
from app.models.user import User, UserRole
from app.models.project import (
    ProjectEnrollment, 
    ProjectEnrollmentQuiz, 
    ProjectMilestoneProgress
)
from app.models.quiz import QuizAttempt, QuizUserAnswer
from app.models.gamification import UserStats, UserAchievement
from app.models.booking import Booking


def reset_students_to_newcomer(dry_run=False, auto_confirm=False):
    """
    Reset all students to newcomer status for clean testing
    """
    db = next(get_db())
    
    try:
        print("🔄 STUDENT STATUS RESET - Clean Slate for Testing")
        print("=" * 60)
        
        # Get all student users
        students = db.query(User).filter(User.role == UserRole.STUDENT).all()
        print(f"📊 Found {len(students)} student accounts to reset")
        
        if not students:
            print("ℹ️  No students found in database")
            return
            
        # Show what will be affected
        print("\n📋 Data that will be CLEARED:")
        print("  ❌ All project enrollments")
        print("  ❌ All quiz attempts and answers")
        print("  ❌ All quiz enrollment records")
        print("  ❌ All milestone progress")
        print("  ❌ All XP and achievements")
        print("  ❌ All bookings")
        print("  🔄 Onboarding status reset to incomplete")
        
        print(f"\n👥 Students affected:")
        for student in students:
            print(f"  • {student.name} ({student.email})")
            
        if dry_run:
            print("\n🔍 DRY RUN MODE - No changes will be made")
            return perform_dry_run_analysis(db, students)
            
        # Confirmation prompt
        if not auto_confirm:
            print(f"\n⚠️  WARNING: This will PERMANENTLY DELETE all student progress data!")
            print(f"⚠️  This action CANNOT be undone!")
            confirm = input(f"\n❓ Are you sure you want to reset {len(students)} students? (type 'RESET' to confirm): ")
            if confirm != 'RESET':
                print("❌ Operation cancelled")
                return False
        
        print(f"\n🚀 Starting student reset process...")
        
        # Track what we're deleting
        stats = {
            'project_enrollments': 0,
            'quiz_attempts': 0,
            'quiz_answers': 0,
            'quiz_enrollments': 0,
            'milestone_progress': 0,
            'user_xp': 0,
            'user_achievements': 0,
            'bookings': 0,
            'students_reset': 0
        }
        
        for student in students:
            print(f"\n👤 Processing {student.name}...")
            
            # 1. Clear project enrollments
            enrollments = db.query(ProjectEnrollment).filter(
                ProjectEnrollment.user_id == student.id
            ).all()
            for enrollment in enrollments:
                db.delete(enrollment)
                stats['project_enrollments'] += 1
            
            # 2. Clear milestone progress
            milestone_progress = db.query(ProjectMilestoneProgress).filter(
                ProjectMilestoneProgress.enrollment_id.in_(
                    db.query(ProjectEnrollment.id).filter(
                        ProjectEnrollment.user_id == student.id
                    ).subquery()
                )
            ).all()
            for progress in milestone_progress:
                db.delete(progress)
                stats['milestone_progress'] += 1
            
            # 3. Clear quiz attempts and answers
            quiz_attempts = db.query(QuizAttempt).filter(
                QuizAttempt.user_id == student.id
            ).all()
            
            for attempt in quiz_attempts:
                # Delete quiz answers first (foreign key dependency)
                answers = db.query(QuizUserAnswer).filter(
                    QuizUserAnswer.attempt_id == attempt.id
                ).all()
                for answer in answers:
                    db.delete(answer)
                    stats['quiz_answers'] += 1
                
                # Delete the attempt
                db.delete(attempt)
                stats['quiz_attempts'] += 1
            
            # 4. Clear quiz enrollment records
            quiz_enrollments = db.query(ProjectEnrollmentQuiz).filter(
                ProjectEnrollmentQuiz.user_id == student.id
            ).all()
            for quiz_enrollment in quiz_enrollments:
                db.delete(quiz_enrollment)
                stats['quiz_enrollments'] += 1
            
            # 5. Clear stats and achievements (DELETE UserStats to make user newcomer)
            user_stats = db.query(UserStats).filter(UserStats.user_id == student.id).first()
            if user_stats:
                db.delete(user_stats)  # This makes the user a NEWCOMER
                stats['user_xp'] += 1
                
            user_achievements = db.query(UserAchievement).filter(
                UserAchievement.user_id == student.id
            ).all()
            for achievement in user_achievements:
                db.delete(achievement)
                stats['user_achievements'] += 1
            
            # 6. Clear bookings
            bookings = db.query(Booking).filter(Booking.user_id == student.id).all()
            for booking in bookings:
                db.delete(booking)
                stats['bookings'] += 1
            
            # 7. Reset user onboarding status
            student.onboarding_completed = False
            stats['students_reset'] += 1
            
            print(f"  ✅ {student.name} reset to newcomer status")
        
        # Commit all changes
        db.commit()
        
        print(f"\n🎉 RESET COMPLETE!")
        print("📊 Summary of cleared data:")
        for key, count in stats.items():
            if count > 0:
                print(f"  • {key.replace('_', ' ').title()}: {count}")
        
        print(f"\n✅ All {len(students)} students are now in 'newcomer' status")
        print("🔄 Ready for clean testing!")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR during reset: {e}")
        print("🔄 Database rolled back - no changes made")
        return False
        
    finally:
        db.close()


def perform_dry_run_analysis(db, students):
    """
    Analyze what would be deleted without actually deleting
    """
    print(f"\n🔍 DRY RUN ANALYSIS:")
    
    total_stats = {
        'project_enrollments': 0,
        'quiz_attempts': 0,
        'quiz_answers': 0,
        'quiz_enrollments': 0,
        'milestone_progress': 0,
        'user_xp': 0,
        'user_achievements': 0,
        'bookings': 0
    }
    
    for student in students:
        print(f"\n👤 {student.name} ({student.email}):")
        
        # Count project enrollments
        enrollment_count = db.query(ProjectEnrollment).filter(
            ProjectEnrollment.user_id == student.id
        ).count()
        print(f"  • Project enrollments: {enrollment_count}")
        total_stats['project_enrollments'] += enrollment_count
        
        # Count quiz attempts
        attempt_count = db.query(QuizAttempt).filter(
            QuizAttempt.user_id == student.id
        ).count()
        print(f"  • Quiz attempts: {attempt_count}")
        total_stats['quiz_attempts'] += attempt_count
        
        # Count quiz answers
        answer_count = db.query(QuizUserAnswer).join(QuizAttempt).filter(
            QuizAttempt.user_id == student.id
        ).count()
        print(f"  • Quiz answers: {answer_count}")
        total_stats['quiz_answers'] += answer_count
        
        # Count quiz enrollments
        quiz_enrollment_count = db.query(ProjectEnrollmentQuiz).filter(
            ProjectEnrollmentQuiz.user_id == student.id
        ).count()
        print(f"  • Quiz enrollments: {quiz_enrollment_count}")
        total_stats['quiz_enrollments'] += quiz_enrollment_count
        
        # Count stats records
        stats_count = 1 if db.query(UserStats).filter(UserStats.user_id == student.id).first() else 0
        print(f"  • Stats records: {stats_count}")
        total_stats['user_xp'] += stats_count
        
        # Count achievements
        achievement_count = db.query(UserAchievement).filter(
            UserAchievement.user_id == student.id
        ).count()
        print(f"  • Achievements: {achievement_count}")
        total_stats['user_achievements'] += achievement_count
        
        # Count bookings
        booking_count = db.query(Booking).filter(Booking.user_id == student.id).count()
        print(f"  • Bookings: {booking_count}")
        total_stats['bookings'] += booking_count
        
        # Onboarding status
        print(f"  • Onboarding completed: {student.onboarding_completed}")
    
    print(f"\n📊 TOTAL RECORDS TO BE DELETED:")
    for key, count in total_stats.items():
        if count > 0:
            print(f"  • {key.replace('_', ' ').title()}: {count}")
    
    total_records = sum(total_stats.values())
    print(f"\n📈 Total database records affected: {total_records}")
    print(f"👥 Students to reset: {len(students)}")


def main():
    parser = argparse.ArgumentParser(
        description='Reset all students to newcomer status for testing'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show what would be deleted without making changes'
    )
    parser.add_argument(
        '--confirm', 
        action='store_true',
        help='Skip confirmation prompt (dangerous!)'
    )
    
    args = parser.parse_args()
    
    if args.confirm and args.dry_run:
        print("❌ Cannot use --confirm with --dry-run")
        sys.exit(1)
    
    success = reset_students_to_newcomer(
        dry_run=args.dry_run,
        auto_confirm=args.confirm
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()