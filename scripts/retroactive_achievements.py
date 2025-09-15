#!/usr/bin/env python3
"""
Visszamenőleges Achievement Érvényesítő Script
==============================================

Ez a script visszamenőleg ellenőrzi és odaítéli az új achievement-eket
minden meglévő felhasználónak a már meglévő aktivitásaik alapján.

Futtatás:
    PYTHONPATH=. python3 scripts/retroactive_achievements.py

Ellenőrzött Achievement típusok:
- 🌟 Welcome Newcomer: Első aktivitás 24 órán belül (rugalmas értelmezés)
- 🧠 First Quiz Master: Első sikeres quiz teljesítés  
- 📝 Project Pioneer: Első projekt enrollment
- 🎯 Complete Journey: Quiz + enrollment kombinációk
"""

import sys
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db
from app.models.user import User, UserRole
from app.models.gamification import UserAchievement, BadgeType
from app.models.quiz import QuizAttempt
from app.models.project import ProjectEnrollment, ProjectEnrollmentStatus
from app.services.gamification import GamificationService
from sqlalchemy.orm import Session
from sqlalchemy import func


class RetroactiveAchievementProcessor:
    """Visszamenőleges achievement feldolgozó"""
    
    def __init__(self, db: Session):
        self.db = db
        self.gamification_service = GamificationService(db)
        self.stats = {
            'users_processed': 0,
            'achievements_awarded': 0,
            'xp_awarded': 0,
            'skipped_users': 0,
            'errors': 0
        }
    
    def process_all_users(self, dry_run: bool = False) -> Dict[str, Any]:
        """Feldolgozza az összes hallgatót visszamenőleg"""
        print("🔍 VISSZAMENŐLEGES ACHIEVEMENT ELLENŐRZÉS")
        print("=" * 50)
        print(f"Dry run mód: {'BE' if dry_run else 'KI'}")
        print()
        
        # Get all students
        students = self.db.query(User).filter(
            User.role == UserRole.STUDENT,
            User.is_active == True
        ).all()
        
        print(f"📊 Összesen {len(students)} aktív hallgató található")
        print()
        
        for student in students:
            try:
                self._process_single_user(student, dry_run)
                self.stats['users_processed'] += 1
            except Exception as e:
                print(f"❌ Hiba {student.name} feldolgozása közben: {e}")
                self.stats['errors'] += 1
        
        self._print_summary()
        return self.stats
    
    def _process_single_user(self, user: User, dry_run: bool):
        """Egyetlen felhasználó feldolgozása"""
        print(f"👤 Feldolgozás: {user.name} (ID: {user.id})")
        
        # Get existing achievements
        existing_achievements = self.db.query(UserAchievement).filter(
            UserAchievement.user_id == user.id
        ).all()
        existing_badge_types = {ach.badge_type for ach in existing_achievements}
        
        awarded_count = 0
        
        # 1. Welcome Newcomer Achievement
        awarded_count += self._check_welcome_newcomer(user, existing_badge_types, dry_run)
        
        # 2. First Quiz Master Achievement  
        awarded_count += self._check_first_quiz_master(user, existing_badge_types, dry_run)
        
        # 3. Project Pioneer Achievement
        awarded_count += self._check_project_pioneer(user, existing_badge_types, dry_run)
        
        # 4. Complete Journey Achievement
        awarded_count += self._check_complete_journey(user, existing_badge_types, dry_run)
        
        if awarded_count > 0:
            print(f"  ✅ {awarded_count} új achievement odaítélve")
        else:
            print(f"  ℹ️ Nincs új achievement (már megvannak vagy nem jogosult)")
            self.stats['skipped_users'] += 1
    
    def _check_welcome_newcomer(self, user: User, existing_badges: set, dry_run: bool) -> int:
        """Ellenőrzi a Welcome Newcomer achievement-et"""
        if BadgeType.NEWCOMER_WELCOME.value in existing_badges:
            return 0
            
        # Rugalmas értelmezés: ha van bármilyen aktivitása, jogosult
        has_activity = (
            self.db.query(QuizAttempt).filter(QuizAttempt.user_id == user.id).first() or
            self.db.query(ProjectEnrollment).filter(ProjectEnrollment.user_id == user.id).first()
        )
        
        if has_activity:
            if not dry_run:
                achievement = self.gamification_service.award_achievement(
                    user_id=user.id,
                    badge_type=BadgeType.NEWCOMER_WELCOME,
                    title="🌟 Welcome Newcomer",
                    description="Welcome to the learning journey!",
                    icon="🌟"
                )
                self.gamification_service.award_xp(user.id, 50, "Retroactive welcome achievement")
                print(f"    🌟 Welcome Newcomer (+50 XP)")
            else:
                print(f"    🌟 Welcome Newcomer (+50 XP) [DRY RUN]")
            
            self.stats['achievements_awarded'] += 1
            self.stats['xp_awarded'] += 50
            return 1
            
        return 0
    
    def _check_first_quiz_master(self, user: User, existing_badges: set, dry_run: bool) -> int:
        """Ellenőrzi a First Quiz Master achievement-et"""
        if BadgeType.FIRST_QUIZ_COMPLETED.value in existing_badges:
            return 0
            
        # Keresés első sikeres quiz-re
        first_passed_quiz = self.db.query(QuizAttempt).filter(
            QuizAttempt.user_id == user.id,
            QuizAttempt.passed == True
        ).order_by(QuizAttempt.completed_at).first()
        
        if first_passed_quiz:
            if not dry_run:
                achievement = self.gamification_service.award_achievement(
                    user_id=user.id,
                    badge_type=BadgeType.FIRST_QUIZ_COMPLETED,
                    title="🧠 First Quiz Master",
                    description="Completed your very first quiz successfully!",
                    icon="🧠"
                )
                self.gamification_service.award_xp(user.id, 100, "Retroactive first quiz achievement")
                print(f"    🧠 First Quiz Master (+100 XP)")
            else:
                print(f"    🧠 First Quiz Master (+100 XP) [DRY RUN]")
            
            self.stats['achievements_awarded'] += 1
            self.stats['xp_awarded'] += 100
            return 1
            
        return 0
    
    def _check_project_pioneer(self, user: User, existing_badges: set, dry_run: bool) -> int:
        """Ellenőrzi a Project Pioneer achievement-et"""
        if BadgeType.FIRST_PROJECT_ENROLLED.value in existing_badges:
            return 0
            
        # Keresés első aktív projekt enrollment-re
        first_enrollment = self.db.query(ProjectEnrollment).filter(
            ProjectEnrollment.user_id == user.id,
            ProjectEnrollment.status == ProjectEnrollmentStatus.ACTIVE.value
        ).order_by(ProjectEnrollment.enrolled_at).first()
        
        if first_enrollment:
            if not dry_run:
                achievement = self.gamification_service.award_achievement(
                    user_id=user.id,
                    badge_type=BadgeType.FIRST_PROJECT_ENROLLED,
                    title="📝 Project Pioneer", 
                    description="Successfully enrolled in your first project!",
                    icon="📝"
                )
                self.gamification_service.award_xp(user.id, 150, "Retroactive first project enrollment")
                print(f"    📝 Project Pioneer (+150 XP)")
            else:
                print(f"    📝 Project Pioneer (+150 XP) [DRY RUN]")
            
            self.stats['achievements_awarded'] += 1
            self.stats['xp_awarded'] += 150
            return 1
            
        return 0
    
    def _check_complete_journey(self, user: User, existing_badges: set, dry_run: bool) -> int:
        """Ellenőrzi a Complete Journey combo achievement-et"""
        if BadgeType.QUIZ_ENROLLMENT_COMBO.value in existing_badges:
            return 0
            
        # Keresés ugyanazon napon történt quiz és enrollment-re
        quiz_dates = self.db.query(
            func.date(QuizAttempt.completed_at).label('quiz_date')
        ).filter(
            QuizAttempt.user_id == user.id,
            QuizAttempt.passed == True
        ).subquery()
        
        enrollment_dates = self.db.query(
            func.date(ProjectEnrollment.enrolled_at).label('enrollment_date')
        ).filter(
            ProjectEnrollment.user_id == user.id,
            ProjectEnrollment.status == ProjectEnrollmentStatus.ACTIVE.value
        ).subquery()
        
        # Check for same-day occurrences
        same_day_activity = self.db.query(quiz_dates, enrollment_dates).filter(
            quiz_dates.c.quiz_date == enrollment_dates.c.enrollment_date
        ).first()
        
        if same_day_activity:
            if not dry_run:
                achievement = self.gamification_service.award_achievement(
                    user_id=user.id,
                    badge_type=BadgeType.QUIZ_ENROLLMENT_COMBO,
                    title="🎯 Complete Journey",
                    description="Completed quiz and enrolled in project on the same day!",
                    icon="🎯"
                )
                self.gamification_service.award_xp(user.id, 75, "Retroactive combo achievement")
                print(f"    🎯 Complete Journey (+75 XP)")
            else:
                print(f"    🎯 Complete Journey (+75 XP) [DRY RUN]")
            
            self.stats['achievements_awarded'] += 1
            self.stats['xp_awarded'] += 75
            return 1
            
        return 0
    
    def _print_summary(self):
        """Összegző statisztikák kiírása"""
        print("\n" + "=" * 50)
        print("📊 ÖSSZEGZŐ STATISZTIKÁK")
        print("=" * 50)
        print(f"👥 Feldolgozott felhasználók: {self.stats['users_processed']}")
        print(f"🏆 Odaítélt achievement-ek: {self.stats['achievements_awarded']}")
        print(f"⭐ Odaítélt XP összesen: {self.stats['xp_awarded']}")
        print(f"⏭️ Átugrott felhasználók: {self.stats['skipped_users']}")
        print(f"❌ Hibák: {self.stats['errors']}")
        print()
        
        if self.stats['achievements_awarded'] > 0:
            avg_xp = self.stats['xp_awarded'] / self.stats['achievements_awarded']
            print(f"📈 Átlagos XP/achievement: {avg_xp:.1f}")
        
        print("✅ Feldolgozás befejezve!")


def main():
    """Fő függvény"""
    print("🚀 VISSZAMENŐLEGES ACHIEVEMENT ÉRVÉNYESÍTŐ")
    print("=" * 60)
    print()
    
    # Confirm before processing
    response = input("Biztosan futtatni szeretnéd a visszamenőleges érvényesítést? (y/N): ")
    if response.lower() not in ['y', 'yes', 'igen', 'i']:
        print("❌ Megszakítva.")
        return
    
    # Ask for dry run
    dry_run_response = input("Dry run mód? (csak előnézet, nincs változtatás) (y/N): ")
    dry_run = dry_run_response.lower() in ['y', 'yes', 'igen', 'i']
    
    db = next(get_db())
    
    try:
        processor = RetroactiveAchievementProcessor(db)
        stats = processor.process_all_users(dry_run=dry_run)
        
        if not dry_run and stats['achievements_awarded'] > 0:
            print(f"\n🎉 Sikeresen feldolgozva! {stats['achievements_awarded']} új achievement odaítélve!")
        elif dry_run:
            print(f"\n🔍 Dry run befejezve. {stats.get('achievements_awarded', 0)} achievement lenne odaítélve.")
            
    except Exception as e:
        print(f"❌ Kritikus hiba: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()