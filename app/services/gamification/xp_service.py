"""
XP Service - Experience Points Management

Handles all XP calculation, awarding, and stat updates.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
from typing import Optional

from ...models.gamification import UserStats
from ...models.attendance import Attendance
from ...models.session import Session as SessionType
from ...models.semester import Semester
from ...models.booking import Booking
from ...models.feedback import Feedback

from .utils import get_or_create_user_stats


def award_attendance_xp(
    db: Session,
    attendance_id: int,
    quiz_score_percent: Optional[float] = None
) -> int:
    """
    Award XP based on session type, instructor evaluation, and quiz performance
    
    Returns total XP awarded
    """
    attendance = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not attendance:
        return 0

    session = db.query(SessionType).filter(SessionType.id == attendance.session_id).first()
    if not session:
        return 0

    if attendance.xp_earned > 0:
        return attendance.xp_earned

    base_xp = 50
    instructor_xp = 0
    quiz_xp = 0

    # Instructor evaluation XP
    instructor_feedback = db.query(Feedback).filter(
        Feedback.session_id == session.id,
        Feedback.user_id == attendance.user_id
    ).first()

    if instructor_feedback and hasattr(instructor_feedback, 'performance_rating'):
        instructor_xp = instructor_feedback.performance_rating * 10
    elif instructor_feedback and hasattr(instructor_feedback, 'rating'):
        instructor_xp = instructor_feedback.rating * 10

    # Quiz XP for HYBRID/VIRTUAL sessions
    session_type = session.sport_type.upper() if hasattr(session.sport_type, 'upper') else str(session.sport_type).upper()

    if session_type in ["HYBRID", "VIRTUAL"]:
        from ...models.quiz import SessionQuiz, QuizAttempt
        session_quiz = db.query(SessionQuiz).filter(
            SessionQuiz.session_id == session.id,
            SessionQuiz.is_required == True
        ).first()

        if session_quiz:
            if quiz_score_percent is None:
                best_attempt = db.query(QuizAttempt).filter(
                    QuizAttempt.user_id == attendance.user_id,
                    QuizAttempt.quiz_id == session_quiz.quiz_id,
                    QuizAttempt.completed_at.isnot(None)
                ).order_by(QuizAttempt.score.desc()).first()

                if best_attempt:
                    quiz_score_percent = best_attempt.score

            if quiz_score_percent is not None:
                if quiz_score_percent >= 90:
                    quiz_xp = 150
                elif quiz_score_percent >= 70:
                    quiz_xp = 75

    xp_earned = base_xp + instructor_xp + quiz_xp

    attendance.xp_earned = xp_earned

    stats = get_or_create_user_stats(db, attendance.user_id)
    stats.total_xp += xp_earned
    stats.level = max(1, (stats.total_xp // 500) + 1)
    stats.updated_at = datetime.now(timezone.utc)
    db.commit()

    return xp_earned


def calculate_user_stats(db: Session, user_id: int) -> UserStats:
    """Calculate and update comprehensive user statistics"""
    stats = get_or_create_user_stats(db, user_id)

    bookings_query = db.query(
        Booking, SessionType, Semester
    ).join(
        SessionType, Booking.session_id == SessionType.id
    ).join(
        Semester, SessionType.semester_id == Semester.id
    ).filter(
        Booking.user_id == user_id
    ).all()

    unique_semesters = set()
    semester_dates = []
    total_bookings = 0
    total_cancelled = 0

    for booking, session, semester in bookings_query:
        unique_semesters.add(semester.id)
        semester_dates.append(semester.start_date)
        total_bookings += 1

        if booking.status.value == 'cancelled':
            total_cancelled += 1

    attendances = db.query(Attendance).filter(Attendance.user_id == user_id).count()
    feedback_count = db.query(Feedback).filter(Feedback.user_id == user_id).count()
    avg_rating = db.query(func.avg(Feedback.rating)).filter(Feedback.user_id == user_id).scalar() or 0.0

    attendance_xp = db.query(func.sum(Attendance.xp_earned)).filter(
        Attendance.user_id == user_id
    ).scalar() or 0

    stats.semesters_participated = len(unique_semesters)
    stats.first_semester_date = min(semester_dates) if semester_dates else None
    stats.total_bookings = total_bookings
    stats.total_attended = attendances
    stats.total_cancelled = total_cancelled
    stats.attendance_rate = (attendances / total_bookings * 100) if total_bookings > 0 else 0.0
    stats.feedback_given = feedback_count
    stats.average_rating_given = float(avg_rating)

    if attendance_xp > 0:
        stats.total_xp = max(stats.total_xp, attendance_xp)

    stats.level = max(1, (stats.total_xp // 500) + 1)
    stats.updated_at = datetime.now(timezone.utc)
    db.commit()

    return stats


def award_xp(db: Session, user_id: int, xp_amount: int, reason: str = "Quiz completion") -> UserStats:
    """Award XP to a user and update their stats"""
    # Update UserStats for gamification
    stats = get_or_create_user_stats(db, user_id)

    stats.total_xp = (stats.total_xp or 0) + xp_amount
    new_level = max(1, stats.total_xp // 1000)
    level_up = new_level > stats.level
    stats.level = new_level
    stats.updated_at = datetime.now(timezone.utc)

    # Also update User.xp_balance (primary XP balance)
    from ...models.user import User
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.xp_balance = (user.xp_balance or 0) + xp_amount

    db.commit()

    if level_up:
        print(f"🎉 User {user_id} leveled up to level {new_level}!")

    return stats
