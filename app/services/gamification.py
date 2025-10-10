from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

from ..models.user import User
from ..models.gamification import UserAchievement, UserStats, BadgeType
from ..models.booking import Booking
from ..models.session import Session as SessionModel
from ..models.semester import Semester
from ..models.attendance import Attendance
from ..models.feedback import Feedback


class GamificationService:
    """Service to handle gamification logic and achievements"""
    
    def __init__(self, db: Session):
        self.db = db
        
    def get_or_create_user_stats(self, user_id: int) -> UserStats:
        """Get or create user statistics"""
        stats = self.db.query(UserStats).filter(UserStats.user_id == user_id).first()
        if not stats:
            stats = UserStats(user_id=user_id)
            self.db.add(stats)
            self.db.commit()
            self.db.refresh(stats)
        return stats
        
    def calculate_user_stats(self, user_id: int) -> UserStats:
        """Calculate and update comprehensive user statistics"""
        stats = self.get_or_create_user_stats(user_id)
        
        # Get all user bookings with session and semester info
        bookings_query = self.db.query(
            Booking, SessionModel, Semester
        ).join(
            SessionModel, Booking.session_id == SessionModel.id
        ).join(
            Semester, SessionModel.semester_id == Semester.id
        ).filter(
            Booking.user_id == user_id
        ).all()
        
        # Calculate semester participation
        unique_semesters = set()
        semester_dates = []
        total_bookings = 0
        total_attended = 0
        total_cancelled = 0
        
        for booking, session, semester in bookings_query:
            unique_semesters.add(semester.id)
            semester_dates.append(semester.start_date)
            total_bookings += 1
            
            if booking.status.value == 'cancelled':
                total_cancelled += 1
        
        # Calculate attendance from attendance table
        attendances = self.db.query(Attendance).filter(Attendance.user_id == user_id).count()
        total_attended = attendances
        
        # Calculate feedback given
        feedback_count = self.db.query(Feedback).filter(Feedback.user_id == user_id).count()
        avg_rating = self.db.query(func.avg(Feedback.rating)).filter(Feedback.user_id == user_id).scalar() or 0.0
        
        # Update statistics
        stats.semesters_participated = len(unique_semesters)
        stats.first_semester_date = min(semester_dates) if semester_dates else None
        stats.total_bookings = total_bookings
        stats.total_attended = total_attended
        stats.total_cancelled = total_cancelled
        stats.attendance_rate = (total_attended / total_bookings * 100) if total_bookings > 0 else 0.0
        stats.feedback_given = feedback_count
        stats.average_rating_given = float(avg_rating)
        
        # Calculate XP and level based on activity
        # Calculate XP from activities (but don't overwrite existing total_xp)
        activity_xp = (
            stats.semesters_participated * 500 +  # 500 XP per semester
            stats.total_attended * 50 +           # 50 XP per attendance
            stats.feedback_given * 25              # 25 XP per feedback
        )
        
        # Only update total_xp if it's less than activity_xp (preserves quiz XP and other sources)
        if stats.total_xp < activity_xp:
            stats.total_xp = activity_xp
            
        stats.level = max(1, stats.total_xp // 1000)  # Level up every 1000 XP
        
        stats.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        
        return stats
        
    def award_achievement(self, user_id: int, badge_type: BadgeType, title: str,
                         description: str, icon: str, semester_count: Optional[int] = None,
                         specialization_id: Optional[str] = None) -> UserAchievement:
        """
        Award an achievement to a user

        Args:
            user_id: User ID
            badge_type: Type of badge
            title: Achievement title
            description: Achievement description
            icon: Achievement icon (emoji)
            semester_count: Optional semester count
            specialization_id: Optional specialization (PLAYER/COACH/INTERNSHIP) for spec-specific achievements
        """
        # Check if user already has this achievement
        existing = self.db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.badge_type == badge_type.value,
            UserAchievement.specialization_id == specialization_id  # Include spec in uniqueness check
        ).first()

        if existing:
            return existing

        achievement = UserAchievement(
            user_id=user_id,
            badge_type=badge_type.value,
            title=title,
            description=description,
            icon=icon,
            semester_count=semester_count,
            specialization_id=specialization_id  # NEW: Add specialization
        )

        self.db.add(achievement)
        self.db.commit()
        self.db.refresh(achievement)

        return achievement
        
    def check_and_award_semester_achievements(self, user_id: int) -> List[UserAchievement]:
        """Check and award semester-based achievements"""
        stats = self.calculate_user_stats(user_id)
        achievements = []
        
        # Returning Student (2+ semesters)
        if stats.semesters_participated >= 2:
            achievement = self.award_achievement(
                user_id=user_id,
                badge_type=BadgeType.RETURNING_STUDENT,
                title="🔄 Returning Student",
                description=f"Participated in {stats.semesters_participated} semesters!",
                icon="🔄",
                semester_count=stats.semesters_participated
            )
            achievements.append(achievement)
            
        # Veteran Student (3+ semesters)
        if stats.semesters_participated >= 3:
            achievement = self.award_achievement(
                user_id=user_id,
                badge_type=BadgeType.VETERAN_STUDENT,
                title="🏅 Veteran Student",
                description=f"A seasoned learner with {stats.semesters_participated} semesters!",
                icon="🏅",
                semester_count=stats.semesters_participated
            )
            achievements.append(achievement)
            
        # Master Student (5+ semesters)
        if stats.semesters_participated >= 5:
            achievement = self.award_achievement(
                user_id=user_id,
                badge_type=BadgeType.MASTER_STUDENT,
                title="👑 Master Student",
                description=f"A true master with {stats.semesters_participated} semesters!",
                icon="👑",
                semester_count=stats.semesters_participated
            )
            achievements.append(achievement)
            
        # Attendance Star (80%+ attendance)
        if stats.attendance_rate >= 80.0 and stats.total_bookings >= 10:
            achievement = self.award_achievement(
                user_id=user_id,
                badge_type=BadgeType.ATTENDANCE_STAR,
                title="⭐ Attendance Star",
                description=f"Excellent {stats.attendance_rate:.1f}% attendance rate!",
                icon="⭐"
            )
            achievements.append(achievement)
            
        # Feedback Champion (10+ feedback given)
        if stats.feedback_given >= 10:
            achievement = self.award_achievement(
                user_id=user_id,
                badge_type=BadgeType.FEEDBACK_CHAMPION,
                title="💬 Feedback Champion",
                description=f"Provided {stats.feedback_given} valuable feedbacks!",
                icon="💬"
            )
            achievements.append(achievement)
            
        return achievements
        
    def get_user_gamification_data(self, user_id: int) -> Dict:
        """Get complete gamification data for a user"""
        stats = self.calculate_user_stats(user_id)
        self.check_and_award_semester_achievements(user_id)
        
        achievements = self.db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id
        ).order_by(UserAchievement.earned_at.desc()).all()
        
        # Get semester information for the user
        from ..models.booking import Booking
        user_semesters = self.db.query(Semester).join(
            SessionModel, Semester.id == SessionModel.semester_id
        ).join(
            Booking, SessionModel.id == Booking.session_id
        ).filter(Booking.user_id == user_id).distinct().order_by(Semester.start_date).all()
        
        # Get current semester (the latest one)
        current_semester = self.db.query(Semester).order_by(Semester.start_date.desc()).first()
        
        # Determine student status
        status = "📚 New Student"
        status_icon = "📚"
        if stats.semesters_participated >= 5:
            status = "👑 Master Student"
            status_icon = "👑"
        elif stats.semesters_participated >= 3:
            status = "🏅 Veteran Student" 
            status_icon = "🏅"
        elif stats.semesters_participated >= 2:
            status = "🔄 Returning Student"
            status_icon = "🔄"
            
        return {
            "stats": {
                "semesters_participated": stats.semesters_participated,
                "total_bookings": stats.total_bookings,
                "total_attended": stats.total_attended,
                "attendance_rate": stats.attendance_rate,
                "feedback_given": stats.feedback_given,
                "total_xp": stats.total_xp,
                "level": stats.level,
                "first_semester_date": stats.first_semester_date.isoformat() if stats.first_semester_date else None
            },
            "achievements": [
                {
                    "id": ach.id,
                    "title": ach.title,
                    "description": ach.description,
                    "icon": ach.icon,
                    "badge_type": ach.badge_type,
                    "earned_at": ach.earned_at.isoformat(),
                    "semester_count": ach.semester_count
                }
                for ach in achievements
            ],
            "status": {
                "title": status,
                "icon": status_icon,
                "is_returning": stats.semesters_participated >= 2
            },
            "next_level": {
                "current_xp": stats.total_xp,
                "next_level_xp": (stats.level + 1) * 1000,
                "progress_percentage": ((stats.total_xp % 1000) / 1000) * 100
            },
            "semesters": [
                {
                    "id": semester.id,
                    "name": semester.name,
                    "start_date": semester.start_date.isoformat() if semester.start_date else None,
                    "end_date": semester.end_date.isoformat() if semester.end_date else None
                }
                for semester in user_semesters
            ],
            "current_semester": {
                "id": current_semester.id,
                "name": current_semester.name,
                "start_date": current_semester.start_date.isoformat() if current_semester.start_date else None,
                "end_date": current_semester.end_date.isoformat() if current_semester.end_date else None
            } if current_semester else None
        }
    
    def award_xp(self, user_id: int, xp_amount: int, reason: str = "Quiz completion") -> UserStats:
        """Award XP to a user and update their stats"""
        stats = self.get_or_create_user_stats(user_id)
        
        # Add XP to existing total
        stats.total_xp = (stats.total_xp or 0) + xp_amount
        
        # Recalculate level
        new_level = max(1, stats.total_xp // 1000)
        
        # Check if level up occurred
        level_up = new_level > stats.level
        stats.level = new_level
        
        stats.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        
        # TODO: Could add notification/achievement for level up
        if level_up:
            print(f"🎉 User {user_id} leveled up to level {new_level}!")
        
        return stats

    def check_and_award_first_time_achievements(self, user_id: int) -> List[UserAchievement]:
        """Check and award first-time achievements for quiz completion"""
        from ..models.quiz import QuizAttempt
        
        achievements = []
        
        # First Quiz Achievement
        quiz_count = self.db.query(QuizAttempt).filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.passed == True
        ).count()
        
        if quiz_count == 1:  # Exactly first successful quiz
            achievement = self.award_achievement(
                user_id=user_id,
                badge_type=BadgeType.FIRST_QUIZ_COMPLETED,
                title="🧠 First Quiz Master",
                description="Completed your very first quiz successfully!",
                icon="🧠"
            )
            achievements.append(achievement)
            # Award bonus XP
            self.award_xp(user_id, 100, "First quiz completed")
            print(f"🎉 User {user_id} earned First Quiz Master achievement!")
        
        return achievements

    def check_first_project_enrollment(self, user_id: int, project_id: int) -> List[UserAchievement]:
        """Check for first project enrollment achievement"""
        from ..models.project import ProjectEnrollment, ProjectEnrollmentStatus
        
        achievements = []
        
        # Check if this is user's first project enrollment
        enrollment_count = self.db.query(ProjectEnrollment).filter(
            ProjectEnrollment.user_id == user_id,
            ProjectEnrollment.status == ProjectEnrollmentStatus.ACTIVE
        ).count()
        
        if enrollment_count == 1:  # First enrollment
            achievement = self.award_achievement(
                user_id=user_id,
                badge_type=BadgeType.FIRST_PROJECT_ENROLLED,
                title="📝 Project Pioneer", 
                description="Successfully enrolled in your first project!",
                icon="📝"
            )
            achievements.append(achievement)
            # Award bonus XP
            self.award_xp(user_id, 150, "First project enrollment")
            print(f"🎉 User {user_id} earned Project Pioneer achievement!")
            
            # Check for same-day combo achievement
            combo_achievements = self._check_quiz_enrollment_combo(user_id)
            achievements.extend(combo_achievements)
        
        return achievements

    def _check_quiz_enrollment_combo(self, user_id: int) -> List[UserAchievement]:
        """Check for quiz completion and project enrollment on the same day"""
        from ..models.quiz import QuizAttempt
        from ..models.project import ProjectEnrollment, ProjectEnrollmentStatus
        
        achievements = []
        today = datetime.now(timezone.utc).date()
        
        # Check if user has a successful quiz attempt today
        quiz_today = self.db.query(QuizAttempt).filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.passed == True,
            func.date(QuizAttempt.completed_at) == today
        ).first()
        
        # Check if user has a project enrollment today  
        enrollment_today = self.db.query(ProjectEnrollment).filter(
            ProjectEnrollment.user_id == user_id,
            ProjectEnrollment.status == ProjectEnrollmentStatus.ACTIVE,
            func.date(ProjectEnrollment.enrolled_at) == today
        ).first()
        
        if quiz_today and enrollment_today:
            # Check if combo achievement already exists
            existing_combo = self.db.query(UserAchievement).filter(
                UserAchievement.user_id == user_id,
                UserAchievement.badge_type == BadgeType.QUIZ_ENROLLMENT_COMBO.value
            ).first()
            
            if not existing_combo:
                achievement = self.award_achievement(
                    user_id=user_id,
                    badge_type=BadgeType.QUIZ_ENROLLMENT_COMBO,
                    title="🎯 Complete Journey",
                    description="Completed quiz and enrolled in project on the same day!",
                    icon="🎯"
                )
                achievements.append(achievement)
                # Award bonus XP
                self.award_xp(user_id, 75, "Quiz + enrollment combo")
                print(f"🎉 User {user_id} earned Complete Journey combo achievement!")
        
        return achievements

    def check_newcomer_welcome(self, user_id: int) -> List[UserAchievement]:
        """Check for newcomer welcome achievement"""
        achievements = []
        
        # Get user creation date
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return achievements
            
        # Check if user was created within last 24 hours
        now = datetime.now(timezone.utc)
        # Ensure both datetimes are timezone-aware for comparison
        user_created = user.created_at
        if user_created and user_created.tzinfo is None:
            user_created = user_created.replace(tzinfo=timezone.utc)
            
        if user_created and (now - user_created) <= timedelta(hours=24):
            # Check if welcome achievement already exists
            existing_welcome = self.db.query(UserAchievement).filter(
                UserAchievement.user_id == user_id,
                UserAchievement.badge_type == BadgeType.NEWCOMER_WELCOME.value
            ).first()
            
            if not existing_welcome:
                achievement = self.award_achievement(
                    user_id=user_id,
                    badge_type=BadgeType.NEWCOMER_WELCOME,
                    title="🌟 Welcome Newcomer",
                    description="Welcome to the learning journey!",
                    icon="🌟"
                )
                achievements.append(achievement)
                # Award bonus XP
                self.award_xp(user_id, 50, "Welcome newcomer")
                print(f"🎉 User {user_id} earned Welcome Newcomer achievement!")

        return achievements

    # ============================================
    # 🆕 SPECIALIZATION-AWARE ACHIEVEMENTS
    # ============================================

    def check_and_award_specialization_achievements(
        self,
        user_id: int,
        specialization_id: str
    ) -> List[UserAchievement]:
        """
        Check and award specialization-specific achievements based on user's progress

        Args:
            user_id: User ID
            specialization_id: PLAYER, COACH, or INTERNSHIP

        Returns:
            List of newly awarded achievements
        """
        from ..models.user_progress import SpecializationProgress

        # Get user's progress in this specialization
        progress = self.db.query(SpecializationProgress).filter(
            SpecializationProgress.student_id == user_id,
            SpecializationProgress.specialization_id == specialization_id
        ).first()

        if not progress:
            return []

        achievements = []

        # PLAYER-specific achievements
        if specialization_id == 'PLAYER':
            # Level-based achievements
            if progress.current_level >= 2:
                ach = self.award_achievement(
                    user_id=user_id,
                    badge_type=BadgeType.FIRST_LEVEL_UP,
                    title="⚽ First Belt Promotion",
                    description=f"Reached {progress.current_level} level as GanCuju Player!",
                    icon="⚽",
                    specialization_id='PLAYER'
                )
                achievements.append(ach)

            if progress.current_level >= 3:
                ach = self.award_achievement(
                    user_id=user_id,
                    badge_type=BadgeType.SKILL_MILESTONE,
                    title="🥋 Yellow Belt Warrior",
                    description="Achieved Rugalmas Nád level!",
                    icon="🥋",
                    specialization_id='PLAYER'
                )
                achievements.append(ach)

            if progress.current_level >= 5:
                ach = self.award_achievement(
                    user_id=user_id,
                    badge_type=BadgeType.ADVANCED_SKILL,
                    title="🏆 Technical Excellence",
                    description="Reached Erős Gyökér level!",
                    icon="🏆",
                    specialization_id='PLAYER'
                )
                achievements.append(ach)

            if progress.current_level >= 8:
                ach = self.award_achievement(
                    user_id=user_id,
                    badge_type=BadgeType.MASTER_LEVEL,
                    title="🐉 Sárkány Bölcsesség Master",
                    description="Achieved the highest GanCuju Player level!",
                    icon="🐉",
                    specialization_id='PLAYER'
                )
                achievements.append(ach)

            # Session-based achievements
            if progress.completed_sessions >= 5:
                ach = self.award_achievement(
                    user_id=user_id,
                    badge_type=BadgeType.PLAYER_DEDICATION,
                    title="⚡ Player Development",
                    description=f"Completed {progress.completed_sessions} player sessions!",
                    icon="⚡",
                    specialization_id='PLAYER'
                )
                achievements.append(ach)

        # COACH-specific achievements
        elif specialization_id == 'COACH':
            # Level-based achievements
            if progress.current_level >= 2:
                ach = self.award_achievement(
                    user_id=user_id,
                    badge_type=BadgeType.FIRST_LEVEL_UP,
                    title="👨‍🏫 First Coaching License",
                    description=f"Reached level {progress.current_level} as Coach!",
                    icon="👨‍🏫",
                    specialization_id='COACH'
                )
                achievements.append(ach)

            if progress.current_level >= 3:
                ach = self.award_achievement(
                    user_id=user_id,
                    badge_type=BadgeType.SKILL_MILESTONE,
                    title="🧠 Leadership Basics",
                    description="Achieved Youth Football Asszisztens level!",
                    icon="🧠",
                    specialization_id='COACH'
                )
                achievements.append(ach)

            if progress.current_level >= 5:
                ach = self.award_achievement(
                    user_id=user_id,
                    badge_type=BadgeType.ADVANCED_SKILL,
                    title="📋 Tactical Mind",
                    description="Reached Amateur Football Asszisztens level!",
                    icon="📋",
                    specialization_id='COACH'
                )
                achievements.append(ach)

            if progress.current_level >= 8:
                ach = self.award_achievement(
                    user_id=user_id,
                    badge_type=BadgeType.MASTER_LEVEL,
                    title="🏅 PRO Football Coach Master",
                    description="Achieved the highest coaching license!",
                    icon="🏅",
                    specialization_id='COACH'
                )
                achievements.append(ach)

            # Session-based achievements
            if progress.completed_sessions >= 5:
                ach = self.award_achievement(
                    user_id=user_id,
                    badge_type=BadgeType.COACH_DEDICATION,
                    title="♟️ Coach Development",
                    description=f"Completed {progress.completed_sessions} coaching sessions!",
                    icon="♟️",
                    specialization_id='COACH'
                )
                achievements.append(ach)

        # INTERNSHIP-specific achievements
        elif specialization_id == 'INTERNSHIP':
            # Level-based achievements
            if progress.current_level >= 2:
                ach = self.award_achievement(
                    user_id=user_id,
                    badge_type=BadgeType.FIRST_LEVEL_UP,
                    title="🚀 Startup Spirit",
                    description="Reached Growth Hacker level!",
                    icon="🚀",
                    specialization_id='INTERNSHIP'
                )
                achievements.append(ach)

            if progress.current_level >= 3:
                ach = self.award_achievement(
                    user_id=user_id,
                    badge_type=BadgeType.MASTER_LEVEL,
                    title="🎯 Startup Leader",
                    description="Achieved the highest internship level!",
                    icon="🎯",
                    specialization_id='INTERNSHIP'
                )
                achievements.append(ach)

            # Session/Project-based achievements
            if progress.completed_sessions >= 3:
                ach = self.award_achievement(
                    user_id=user_id,
                    badge_type=BadgeType.INTERNSHIP_DEDICATION,
                    title="💼 Professional Growth",
                    description=f"Completed {progress.completed_sessions} internship sessions!",
                    icon="💼",
                    specialization_id='INTERNSHIP'
                )
                achievements.append(ach)

            if progress.completed_projects >= 1:
                ach = self.award_achievement(
                    user_id=user_id,
                    badge_type=BadgeType.PROJECT_COMPLETE,
                    title="🌟 Real World Experience",
                    description="Completed your first internship project!",
                    icon="🌟",
                    specialization_id='INTERNSHIP'
                )
                achievements.append(ach)

        return achievements