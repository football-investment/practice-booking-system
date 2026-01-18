from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

from ..models.user import User
from ..models.gamification import UserAchievement, UserStats, BadgeType
from ..models.booking import Booking
from ..models.session import Session as SessionTypel
from ..models.semester import Semester
from ..models.attendance import Attendance
from ..models.feedback import Feedback
from ..models.achievement import Achievement, AchievementCategory
from ..models.audit_log import AuditLog, AuditAction
from ..models.license import UserLicense

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

    def award_attendance_xp(self, attendance_id: int, quiz_score_percent: float = None) -> int:
        """
        Award XP based on session type, instructor evaluation, and quiz performance

        🔒 RULE #6: INTELLIGENT XP CALCULATION
        ======================================

        XP Calculation Strategy:
        1. Base XP (50 XP) - For attendance (check-in)
        2. Instructor Evaluation XP (0-50 XP) - Based on 1-5 rating (10 XP per star)
        3. Quiz XP (0-150 XP) - Only for HYBRID/VIRTUAL sessions
           - Excellent (>90%): +150 XP
           - Pass (70-90%): +75 XP
           - Fail (<70%): +0 XP

        Session Type Maximums:
        - ONSITE: 50 (base) + 50 (instructor) = 100 XP max
        - HYBRID: 50 (base) + 50 (instructor) + 150 (quiz) = 250 XP max
        - VIRTUAL: 50 (base) + 50 (instructor) + 150 (quiz) = 250 XP max

        Args:
            attendance_id: Attendance record ID
            quiz_score_percent: Quiz score percentage (0-100), None if no quiz

        Returns:
            int: Total XP awarded
        """
        # Get attendance with session info
        attendance = self.db.query(Attendance).filter(Attendance.id == attendance_id).first()
        if not attendance:
            return 0

        session = self.db.query(SessionTypel).filter(SessionTypel.id == attendance.session_id).first()
        if not session:
            return 0

        # Check if XP already awarded
        if attendance.xp_earned > 0:
            return attendance.xp_earned

        # 🔒 RULE #6: INTELLIGENT XP CALCULATION
        # =======================================

        # STEP 1: Base XP (50 XP for attendance/check-in)
        base_xp = 50

        # STEP 2: Instructor Evaluation XP (0-50 XP)
        instructor_xp = 0
        instructor_feedback = self.db.query(Feedback).filter(
            Feedback.session_id == session.id,
            Feedback.user_id == attendance.user_id
        ).first()

        if instructor_feedback and hasattr(instructor_feedback, 'performance_rating'):
            # Rating: 1-5 stars → 10-50 XP (10 XP per star)
            instructor_xp = instructor_feedback.performance_rating * 10
        elif instructor_feedback and hasattr(instructor_feedback, 'rating'):
            # Fallback to general rating if performance_rating doesn't exist
            instructor_xp = instructor_feedback.rating * 10

        # STEP 3: Quiz XP (0-150 XP) - Only for HYBRID/VIRTUAL sessions
        quiz_xp = 0
        session_type = session.sport_type.upper() if hasattr(session.sport_type, 'upper') else str(session.sport_type).upper()

        if session_type in ["HYBRID", "VIRTUAL"]:
            # Check if session has required quiz
            session_quiz = self.db.query(SessionQuiz).filter(
                SessionQuiz.session_id == session.id,
                SessionQuiz.is_required == True
            ).first()

            if session_quiz:
                # Look up best quiz attempt
                if quiz_score_percent is None:
                    best_attempt = self.db.query(QuizAttempt).filter(
                        QuizAttempt.user_id == attendance.user_id,
                        QuizAttempt.quiz_id == session_quiz.quiz_id,
                        QuizAttempt.completed_at.isnot(None)
                    ).order_by(QuizAttempt.score.desc()).first()

                    if best_attempt:
                        quiz_score_percent = best_attempt.score

                # Calculate quiz XP based on performance
                if quiz_score_percent is not None:
                    if quiz_score_percent >= 90:
                        quiz_xp = 150  # Excellent
                    elif quiz_score_percent >= 70:
                        quiz_xp = 75   # Pass
                    else:
                        quiz_xp = 0    # Fail - no quiz XP

        # STEP 4: Calculate total XP
        xp_earned = base_xp + instructor_xp + quiz_xp

        print(f"🎯 Session: {session.title} | Type: {session_type}")
        print(f"   Base XP: {base_xp} | Instructor XP: {instructor_xp} | Quiz XP: {quiz_xp}")
        print(f"   Total Earned: {xp_earned} XP")

        # Save XP to attendance record
        attendance.xp_earned = xp_earned

        # Add XP to user stats
        stats = self.get_or_create_user_stats(attendance.user_id)
        stats.total_xp += xp_earned

        # Update level: Level = floor(Total_XP / 500) + 1
        stats.level = max(1, (stats.total_xp // 500) + 1)

        stats.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        print(f"   Total XP: {stats.total_xp}, Level: {stats.level}")

        return xp_earned
        
    def calculate_user_stats(self, user_id: int) -> UserStats:
        """Calculate and update comprehensive user statistics"""
        stats = self.get_or_create_user_stats(user_id)
        
        # Get all user bookings with session and semester info
        bookings_query = self.db.query(
            Booking, SessionTypel, Semester
        ).join(
            SessionTypel, Booking.session_id == SessionTypel.id
        ).join(
            Semester, SessionTypel.semester_id == Semester.id
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

        # Calculate XP from attendance records (NEW: Session-based XP)
        attendance_xp = self.db.query(func.sum(Attendance.xp_earned)).filter(
            Attendance.user_id == user_id
        ).scalar() or 0

        # Update statistics
        stats.semesters_participated = len(unique_semesters)
        stats.first_semester_date = min(semester_dates) if semester_dates else None
        stats.total_bookings = total_bookings
        stats.total_attended = total_attended
        stats.total_cancelled = total_cancelled
        stats.attendance_rate = (total_attended / total_bookings * 100) if total_bookings > 0 else 0.0
        stats.feedback_given = feedback_count
        stats.average_rating_given = float(avg_rating)

        # NEW XP System: Use actual XP earned from attendance
        # Preserve any existing XP (e.g., from quizzes, achievements)
        if attendance_xp > 0:
            # Set total_xp to attendance XP (attendance XP is the main source)
            # This will be the baseline, quiz/achievement bonuses add on top
            stats.total_xp = max(stats.total_xp, attendance_xp)

        # Update level: Level = floor(Total_XP / 500) + 1
        stats.level = max(1, (stats.total_xp // 500) + 1)
        
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
        user_semesters = self.db.query(Semester).join(
            SessionTypel, Semester.id == SessionTypel.semester_id
        ).join(
            Booking, SessionTypel.id == Booking.session_id
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

    # ============================================
    # 🆕 NEW ACHIEVEMENT SYSTEM (from achievements table)
    # ============================================

    def check_and_unlock_achievements(
        self,
        user_id: int,
        trigger_action: str,
        context: dict = None
    ) -> List[Achievement]:
        """
        Check and unlock achievements based on user action.

        This is the NEW achievement system that uses the achievements table.

        Args:
            user_id: User ID
            trigger_action: Action that triggered check (e.g., "login", "complete_quiz")
            context: Additional context (e.g., {"score": 100, "level": 2})

        Returns:
            List of newly unlocked Achievement objects

        Example:
            service.check_and_unlock_achievements(
                user_id=1,
                trigger_action="login"
            )
        """
        unlocked_achievements = []

        # Get all active achievements
        all_achievements = self.db.query(Achievement).filter(
            Achievement.is_active == True
        ).all()

        # Get user's existing achievements
        user_achievements = self.db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id.isnot(None)  # Only check new-style achievements
        ).all()

        existing_achievement_ids = {ua.achievement_id for ua in user_achievements}

        # Check each achievement
        for achievement in all_achievements:
            # Skip if already unlocked
            if achievement.id in existing_achievement_ids:
                continue

            # Check if requirements met
            if self._check_achievement_requirements(
                user_id, achievement, trigger_action, context or {}
            ):
                # Unlock achievement
                user_achievement = UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement.id,
                    badge_type=achievement.code,  # Use code as badge_type for compatibility
                    title=achievement.name,
                    description=achievement.description,
                    icon=achievement.icon,
                    earned_at=datetime.now(timezone.utc)
                )
                self.db.add(user_achievement)

                # Award XP
                if achievement.xp_reward > 0:
                    self.award_xp(
                        user_id,
                        achievement.xp_reward,
                        f"Achievement: {achievement.name}"
                    )

                unlocked_achievements.append(achievement)

        # Commit if we unlocked anything
        if unlocked_achievements:
            self.db.commit()

            # Refresh to get relationships
            for achievement in unlocked_achievements:
                self.db.refresh(achievement)

        return unlocked_achievements

    def _check_achievement_requirements(
        self,
        user_id: int,
        achievement: Achievement,
        trigger_action: str,
        context: dict
    ) -> bool:
        """
        Check if achievement requirements are met.

        Args:
            user_id: User ID
            achievement: Achievement to check
            trigger_action: Action that triggered check
            context: Additional context data

        Returns:
            True if requirements met, False otherwise
        """
        requirements = achievement.requirements or {}
        required_action = requirements.get("action")

        # Action doesn't match requirement
        if required_action and required_action != trigger_action:
            return False

        # Check count-based requirements (e.g., "complete 5 quizzes")
        if "count" in requirements:
            required_count = requirements["count"]
            actual_count = self._get_user_action_count(user_id, trigger_action)

            return actual_count >= required_count

        # Check level-based requirements (e.g., "reach level 5")
        if "level" in requirements:
            required_level = requirements["level"]

            # Check from context first (just-in-time level change)
            if context.get("level") == required_level:
                return True

            # Query user's maximum level across all specializations
            max_level = self.db.query(
                func.max(UserLicense.current_level)
            ).filter(
                UserLicense.user_id == user_id
            ).scalar()

            return max_level >= required_level if max_level else False

        # Check score-based requirements (e.g., "perfect score")
        if "min_score" in requirements:
            required_score = requirements["min_score"]
            actual_score = context.get("score", 0)

            return actual_score >= required_score

        # Check specialization count (e.g., "have 2+ specializations")
        if "specialization_count" in requirements:
            required_count = requirements["specialization_count"]

            specialization_count = self.db.query(
                func.count(func.distinct(UserLicense.specialization_type))
            ).filter(
                UserLicense.user_id == user_id
            ).scalar()

            return specialization_count >= required_count if specialization_count else False

        # Default: if no specific requirements, consider met
        return True

    def _get_user_action_count(self, user_id: int, action: str) -> int:
        """
        Get count of specific action for user from audit logs.

        Args:
            user_id: User ID
            action: Action to count (e.g., "login", "complete_quiz")

        Returns:
            Count of times user performed this action
        """
        # Map achievement action to audit log action
        action_mapping = {
            "login": AuditAction.LOGIN,
            "complete_quiz": AuditAction.QUIZ_SUBMITTED,
            "select_specialization": AuditAction.SPECIALIZATION_SELECTED,
            "license_earned": AuditAction.LICENSE_ISSUED,
            "project_enroll": AuditAction.PROJECT_ENROLLED,
            "project_complete": AuditAction.PROJECT_MILESTONE_COMPLETED,
            "quiz_perfect_score": AuditAction.QUIZ_SUBMITTED  # Will check score in context
        }

        audit_action = action_mapping.get(action)

        # If no mapping found, return 0
        if not audit_action:
            return 0

        # Count occurrences in audit log
        count = self.db.query(AuditLog).filter(
            AuditLog.user_id == user_id,
            AuditLog.action == audit_action
        ).count()

        return count