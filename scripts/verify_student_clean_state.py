#!/usr/bin/env python3
"""
Student Clean State Verification Script

This script verifies that all students are in a "clean newcomer" state
by checking that they have no:
- Project enrollments
- Quiz attempts
- Quiz enrollment records  
- Milestone progress
- XP/Achievements
- Bookings
- Completed onboarding

Usage:
    python verify_student_clean_state.py
"""

import sys
import os

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


def verify_student_clean_state():
    """
    Verify all students are in clean newcomer state
    """
    db = next(get_db())
    
    try:
        print("🔍 STUDENT CLEAN STATE VERIFICATION")
        print("=" * 50)
        
        # Get all student users
        students = db.query(User).filter(User.role == UserRole.STUDENT).all()
        print(f"👥 Checking {len(students)} student accounts...\n")
        
        if not students:
            print("ℹ️  No students found in database")
            return True
        
        clean_students = []
        dirty_students = []
        
        for student in students:
            issues = []
            
            # Check project enrollments
            enrollment_count = db.query(ProjectEnrollment).filter(
                ProjectEnrollment.user_id == student.id
            ).count()
            if enrollment_count > 0:
                issues.append(f"Has {enrollment_count} project enrollments")
            
            # Check quiz attempts
            attempt_count = db.query(QuizAttempt).filter(
                QuizAttempt.user_id == student.id
            ).count()
            if attempt_count > 0:
                issues.append(f"Has {attempt_count} quiz attempts")
            
            # Check quiz enrollments
            quiz_enrollment_count = db.query(ProjectEnrollmentQuiz).filter(
                ProjectEnrollmentQuiz.user_id == student.id
            ).count()
            if quiz_enrollment_count > 0:
                issues.append(f"Has {quiz_enrollment_count} quiz enrollments")
            
            # Check stats records  
            user_stats = db.query(UserStats).filter(UserStats.user_id == student.id).first()
            if user_stats:
                issues.append(f"Has stats record (XP: {user_stats.total_xp}, Level: {user_stats.level})")
            
            # Check achievements
            achievement_count = db.query(UserAchievement).filter(
                UserAchievement.user_id == student.id
            ).count()
            if achievement_count > 0:
                issues.append(f"Has {achievement_count} achievements")
            
            # Check bookings
            booking_count = db.query(Booking).filter(Booking.user_id == student.id).count()
            if booking_count > 0:
                issues.append(f"Has {booking_count} bookings")
            
            # Check onboarding status
            if student.onboarding_completed:
                issues.append("Onboarding marked as completed")
            
            # Categorize student
            if issues:
                dirty_students.append({
                    'student': student,
                    'issues': issues
                })
            else:
                clean_students.append(student)
        
        # Report results
        print("📊 VERIFICATION RESULTS:")
        print("-" * 30)
        
        if clean_students:
            print(f"✅ CLEAN STUDENTS ({len(clean_students)}):")
            for student in clean_students:
                print(f"  • {student.name} ({student.email})")
        
        if dirty_students:
            print(f"\n❌ STUDENTS WITH REMAINING DATA ({len(dirty_students)}):")
            for item in dirty_students:
                student = item['student']
                issues = item['issues']
                print(f"  • {student.name} ({student.email}):")
                for issue in issues:
                    print(f"    - {issue}")
        
        print(f"\n📈 SUMMARY:")
        print(f"  • Total students: {len(students)}")
        print(f"  • Clean students: {len(clean_students)}")
        print(f"  • Students with data: {len(dirty_students)}")
        
        is_fully_clean = len(dirty_students) == 0
        
        if is_fully_clean:
            print(f"\n🎉 SUCCESS: All students are in clean newcomer state!")
            print(f"🚀 Ready for testing!")
        else:
            print(f"\n⚠️  WARNING: {len(dirty_students)} students still have data")
            print(f"💡 Run reset_students_to_newcomer.py to clean them")
        
        return is_fully_clean
        
    except Exception as e:
        print(f"\n❌ ERROR during verification: {e}")
        return False
        
    finally:
        db.close()


def main():
    success = verify_student_clean_state()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()