"""
Leaderboard Service - User Rankings and Leaderboards

Handles leaderboard generation and user rank calculation based on XP.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional

from ...models.user import User
from ...models.gamification import UserStats


def get_leaderboard(db: Session, limit: int = 10) -> List[Dict]:
    """
    Get top users by XP for leaderboard

    Args:
        db: Database session
        limit: Maximum number of users to return (default: 10)

    Returns:
        List of dictionaries containing:
            - rank: Position on leaderboard (1-based)
            - user_id: User ID
            - username: User's username
            - full_name: User's full name
            - total_xp: Total XP earned
            - level: Current level
            - attendance_rate: Attendance percentage
            - semesters_participated: Number of semesters
    """
    # Query top users by XP
    leaderboard_query = db.query(
        UserStats,
        User
    ).join(
        User, UserStats.user_id == User.id
    ).filter(
        UserStats.total_xp > 0  # Only include users with XP
    ).order_by(
        UserStats.total_xp.desc()
    ).limit(limit).all()

    # Build leaderboard data
    leaderboard = []
    for rank, (stats, user) in enumerate(leaderboard_query, start=1):
        leaderboard.append({
            "rank": rank,
            "user_id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "total_xp": stats.total_xp,
            "level": stats.level,
            "attendance_rate": round(stats.attendance_rate, 1),
            "semesters_participated": stats.semesters_participated
        })

    return leaderboard


def get_user_rank(db: Session, user_id: int) -> Optional[Dict]:
    """
    Get user's rank on the leaderboard

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Dictionary containing:
            - rank: User's position on leaderboard (1-based)
            - user_id: User ID
            - username: User's username
            - total_xp: Total XP earned
            - level: Current level
            - total_users: Total number of users with XP
            - percentile: User's percentile rank (0-100)
        Or None if user not found or has no XP
    """
    # Get user stats
    user_stats = db.query(UserStats).filter(
        UserStats.user_id == user_id
    ).first()

    if not user_stats or user_stats.total_xp == 0:
        return None

    # Get user info
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    # Calculate rank using subquery
    # Count how many users have MORE XP than this user
    users_above = db.query(UserStats).filter(
        UserStats.total_xp > user_stats.total_xp
    ).count()

    rank = users_above + 1

    # Get total users with XP
    total_users = db.query(UserStats).filter(
        UserStats.total_xp > 0
    ).count()

    # Calculate percentile (higher is better)
    # If rank is 1 out of 100, percentile is 99 (top 1%)
    percentile = 0.0
    if total_users > 1:
        percentile = ((total_users - rank) / (total_users - 1)) * 100

    return {
        "rank": rank,
        "user_id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "total_xp": user_stats.total_xp,
        "level": user_stats.level,
        "total_users": total_users,
        "percentile": round(percentile, 1)
    }


def get_semester_leaderboard(
    db: Session,
    semester_id: int,
    limit: int = 10
) -> List[Dict]:
    """
    Get leaderboard for a specific semester

    Args:
        db: Database session
        semester_id: Semester ID
        limit: Maximum number of users to return

    Returns:
        List of users ranked by attendance and XP for that semester
    """
    from ...models.booking import Booking
    from ...models.session import Session as SessionType
    from ...models.attendance import Attendance

    # Query users with activity in this semester
    semester_stats = db.query(
        User.id,
        User.username,
        User.full_name,
        func.count(Booking.id).label('bookings'),
        func.count(Attendance.id).label('attended'),
        func.sum(Attendance.xp_earned).label('semester_xp')
    ).select_from(User).join(
        Booking, Booking.user_id == User.id
    ).join(
        SessionType, Booking.session_id == SessionType.id
    ).outerjoin(
        Attendance,
        (Attendance.user_id == User.id) & (Attendance.session_id == SessionType.id)
    ).filter(
        SessionType.semester_id == semester_id
    ).group_by(
        User.id, User.username, User.full_name
    ).order_by(
        func.coalesce(func.sum(Attendance.xp_earned), 0).desc()
    ).limit(limit).all()

    # Build leaderboard
    leaderboard = []
    for rank, stats in enumerate(semester_stats, start=1):
        attendance_rate = 0.0
        if stats.bookings > 0:
            attendance_rate = (stats.attended / stats.bookings) * 100

        leaderboard.append({
            "rank": rank,
            "user_id": stats.id,
            "username": stats.username,
            "full_name": stats.full_name,
            "bookings": stats.bookings,
            "attended": stats.attended,
            "attendance_rate": round(attendance_rate, 1),
            "semester_xp": stats.semester_xp or 0
        })

    return leaderboard


def get_specialization_leaderboard(
    db: Session,
    specialization_id: str,
    limit: int = 10
) -> List[Dict]:
    """
    Get leaderboard for a specific specialization (PLAYER/COACH/INTERNSHIP)

    Args:
        db: Database session
        specialization_id: Specialization ID (PLAYER, COACH, INTERNSHIP)
        limit: Maximum number of users to return

    Returns:
        List of users ranked by level and progress in that specialization
    """
    from ...models.user_progress import SpecializationProgress

    # Query users with progress in this specialization
    progress_query = db.query(
        SpecializationProgress,
        User
    ).join(
        User, SpecializationProgress.student_id == User.id
    ).filter(
        SpecializationProgress.specialization_id == specialization_id
    ).order_by(
        SpecializationProgress.current_level.desc(),
        SpecializationProgress.completed_sessions.desc()
    ).limit(limit).all()

    # Build leaderboard
    leaderboard = []
    for rank, (progress, user) in enumerate(progress_query, start=1):
        leaderboard.append({
            "rank": rank,
            "user_id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "current_level": progress.current_level,
            "completed_sessions": progress.completed_sessions,
            "specialization_id": specialization_id
        })

    return leaderboard
