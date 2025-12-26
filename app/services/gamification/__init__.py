"""
Gamification Service - Modular Architecture

Handles XP, badges, achievements, and leaderboards.

PUBLIC API - Import from this module:
    from app.services.gamification import GamificationService
"""

from sqlalchemy.orm import Session

# Import submodules
from . import utils, xp_service, badge_service, leaderboard_service, achievement_service


# Backward-compatible wrapper class
class GamificationService:
    """
    Unified gamification service interface

    Provides backward compatibility while delegating to specialized modules.
    """

    def __init__(self, db: Session):
        self.db = db

    # ============================================================================
    # UTILS
    # ============================================================================
    def get_or_create_user_stats(self, user_id: int):
        """Get or create user statistics"""
        return utils.get_or_create_user_stats(self.db, user_id)

    # ============================================================================
    # XP SERVICE
    # ============================================================================
    def award_attendance_xp(self, attendance_id: int, quiz_score_percent: float = None) -> int:
        """Award XP based on session type, instructor evaluation, and quiz performance"""
        return xp_service.award_attendance_xp(self.db, attendance_id, quiz_score_percent)

    def calculate_user_stats(self, user_id: int):
        """Calculate and update comprehensive user statistics"""
        return xp_service.calculate_user_stats(self.db, user_id)

    def award_xp(self, user_id: int, xp_amount: int, reason: str = "Quiz completion"):
        """Award XP to a user and update their stats"""
        return xp_service.award_xp(self.db, user_id, xp_amount, reason)

    # ============================================================================
    # BADGE SERVICE
    # ============================================================================
    def award_achievement(self, user_id: int, badge_type, title: str,
                         description: str, icon: str, semester_count: int = None,
                         specialization_id: str = None):
        """Award an achievement to a user"""
        return badge_service.award_achievement(
            self.db, user_id, badge_type, title, description, icon,
            semester_count, specialization_id
        )

    def check_and_award_semester_achievements(self, user_id: int):
        """Check and award semester-based achievements"""
        return badge_service.check_and_award_semester_achievements(self.db, user_id)

    def check_and_award_first_time_achievements(self, user_id: int):
        """Check and award first-time achievements for quiz completion"""
        return badge_service.check_and_award_first_time_achievements(self.db, user_id)

    def check_first_project_enrollment(self, user_id: int, project_id: int):
        """Check for first project enrollment achievement"""
        return badge_service.check_first_project_enrollment(self.db, user_id, project_id)

    def check_newcomer_welcome(self, user_id: int):
        """Check for newcomer welcome achievement (first quiz + first project same day)"""
        return badge_service.check_newcomer_welcome(self.db, user_id)

    def check_and_award_specialization_achievements(self, user_id: int, specialization_id: str):
        """Check and award specialization-specific achievements"""
        return badge_service.check_and_award_specialization_achievements(
            self.db, user_id, specialization_id
        )

    def check_and_unlock_achievements(self, user_id: int, trigger_action: str, context: dict = None):
        """Check and unlock achievements based on user action (NEW achievement system)"""
        return badge_service.check_and_unlock_achievements(
            self.db, user_id, trigger_action, context
        )

    # ============================================================================
    # LEADERBOARD SERVICE
    # ============================================================================
    def get_leaderboard(self, limit: int = 10):
        """Get top users by XP"""
        return leaderboard_service.get_leaderboard(self.db, limit)

    def get_user_rank(self, user_id: int):
        """Get user's rank on leaderboard"""
        return leaderboard_service.get_user_rank(self.db, user_id)

    # ============================================================================
    # ACHIEVEMENT SERVICE
    # ============================================================================
    def get_user_gamification_data(self, user_id: int):
        """Get complete gamification data for a user"""
        return achievement_service.get_user_gamification_data(self.db, user_id)


# Public API exports
__all__ = [
    'GamificationService',
    'utils',
    'xp_service',
    'badge_service',
    'leaderboard_service',
    'achievement_service'
]
