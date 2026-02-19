"""
SessionStatsAggregator Service

Responsibility:
    Efficiently fetches booking, attendance, and rating statistics for multiple
    sessions in bulk using GROUP BY queries. Eliminates N+1 query problem.

Architecture:
    - Single service with 3 bulk queries
    - Returns pre-aggregated stats as dictionaries for O(1) lookup
    - Used by list_sessions endpoint to avoid per-session queries

Performance:
    - 3 queries total (regardless of session count)
    - O(n) time complexity for n sessions
    - O(n) space complexity for result dictionaries

Complexity Target: B (6) - 3 queries + dict construction
"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from ..models.booking import Booking, BookingStatus
from ..models.attendance import Attendance
from ..models.feedback import Feedback


class SessionStatsAggregator:
    """
    Service for bulk-fetching session statistics.

    Optimizes database access by using GROUP BY queries instead of
    individual queries per session (N+1 problem elimination).
    """

    def __init__(self, db: Session):
        """
        Initialize stats aggregator.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def fetch_stats(self, session_ids: List[int]) -> Dict[str, Dict]:
        """
        Bulk fetch booking, attendance, and rating stats for sessions.

        Args:
            session_ids: List of session IDs to fetch stats for

        Returns:
            Dictionary with three keys:
            {
                'bookings': {session_id: {total, confirmed, waitlisted}},
                'attendance': {session_id: count},
                'ratings': {session_id: avg_rating or None}
            }

        Complexity: B (6) - 3 bulk queries + 3 dict constructions
        """
        if not session_ids:
            return {
                'bookings': {},
                'attendance': {},
                'ratings': {}
            }

        booking_stats = self._fetch_booking_stats(session_ids)
        attendance_stats = self._fetch_attendance_stats(session_ids)
        rating_stats = self._fetch_rating_stats(session_ids)

        return {
            'bookings': booking_stats,
            'attendance': attendance_stats,
            'ratings': rating_stats
        }

    def _fetch_booking_stats(self, session_ids: List[int]) -> Dict[int, Dict]:
        """
        Fetch booking statistics (total, confirmed, waitlisted) per session.

        Args:
            session_ids: List of session IDs

        Returns:
            {session_id: {total: int, confirmed: int, waitlisted: int}}

        Complexity: A (3) - single GROUP BY query + dict comprehension
        """
        booking_stats_query = self.db.query(
            Booking.session_id,
            func.count(Booking.id).label('total_bookings'),
            func.sum(
                case((Booking.status == BookingStatus.CONFIRMED, 1), else_=0)
            ).label('confirmed'),
            func.sum(
                case((Booking.status == BookingStatus.WAITLISTED, 1), else_=0)
            ).label('waitlisted')
        ).filter(
            Booking.session_id.in_(session_ids)
        ).group_by(Booking.session_id).all()

        # Create lookup dict for O(1) access
        return {
            stat.session_id: {
                'total': stat.total_bookings,
                'confirmed': stat.confirmed,
                'waitlisted': stat.waitlisted
            } for stat in booking_stats_query
        }

    def _fetch_attendance_stats(self, session_ids: List[int]) -> Dict[int, int]:
        """
        Fetch attendance count per session.

        Args:
            session_ids: List of session IDs

        Returns:
            {session_id: attendance_count}

        Complexity: A (2) - single GROUP BY query + dict comprehension
        """
        attendance_stats_query = self.db.query(
            Attendance.session_id,
            func.count(Attendance.id).label('count')
        ).filter(
            Attendance.session_id.in_(session_ids)
        ).group_by(Attendance.session_id).all()

        return {
            stat.session_id: stat.count
            for stat in attendance_stats_query
        }

    def _fetch_rating_stats(self, session_ids: List[int]) -> Dict[int, Optional[float]]:
        """
        Fetch average rating per session.

        Args:
            session_ids: List of session IDs

        Returns:
            {session_id: avg_rating or None}

        Complexity: A (2) - single GROUP BY query + dict comprehension
        """
        rating_stats_query = self.db.query(
            Feedback.session_id,
            func.avg(Feedback.rating).label('avg_rating')
        ).filter(
            Feedback.session_id.in_(session_ids)
        ).group_by(Feedback.session_id).all()

        return {
            stat.session_id: float(stat.avg_rating) if stat.avg_rating else None
            for stat in rating_stats_query
        }
