"""
SessionResponseBuilder Service

Responsibility:
    Constructs SessionList response objects with pre-aggregated statistics.
    Handles NULL value edge cases and includes tournament-specific flags.

Critical Requirements:
    - NULL handling: capacity, credit_cost, created_at, mixed_specialization
    - Tournament flags: is_tournament_game, game_type (must be included)
    - Stats integration: booking, attendance, rating from aggregator
    - Schema validation: SessionWithStats Pydantic model

Architecture:
    - build_response(): Main method, constructs SessionList
    - _build_session_data(): Private method, constructs single session dict
    - No queries, no lazy loading, pure transformation logic

Complexity Target: B (7) for main method
"""

from typing import Dict, List, Any
from sqlalchemy.orm import Session as DBSession

from ..models.session import Session as SessionTypel
from ..schemas.session import SessionWithStats, SessionList


class SessionResponseBuilder:
    """
    Service for building SessionList responses with statistics.

    Transforms raw session objects and pre-aggregated stats into
    SessionWithStats response objects with proper NULL handling.
    """

    def __init__(self, db: DBSession):
        """
        Initialize response builder.

        Args:
            db: SQLAlchemy database session (not used, kept for consistency)
        """
        self.db = db

    def build_response(
        self,
        sessions: List[SessionTypel],
        stats: Dict[str, Dict],
        total: int,
        page: int,
        size: int
    ) -> SessionList:
        """
        Build SessionList response with pre-aggregated statistics.

        Args:
            sessions: List of Session ORM objects
            stats: Pre-aggregated stats from SessionStatsAggregator
                   {
                       'bookings': {session_id: {total, confirmed, waitlisted}},
                       'attendance': {session_id: count},
                       'ratings': {session_id: avg_rating}
                   }
            total: Total count of sessions (for pagination)
            page: Current page number
            size: Page size

        Returns:
            SessionList with SessionWithStats objects

        Complexity: B (7) - iteration + dict lookup + schema construction
        """
        session_stats = []

        for session in sessions:
            session_data = self._build_session_data(session, stats)
            session_stats.append(SessionWithStats(**session_data))

        return SessionList(
            sessions=session_stats,
            total=total,
            page=page,
            size=size
        )

    def _build_session_data(
        self,
        session: SessionTypel,
        stats: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """
        Build session data dictionary with stats and NULL handling.

        ⚠️ CRITICAL: NULL handling preserved 1:1 from original implementation
        - capacity: NULL → 0
        - credit_cost: NULL → 1
        - created_at: NULL → date_start
        - mixed_specialization: missing attribute → False
        - is_tournament_game: missing attribute → False
        - game_type: missing attribute → None

        Args:
            session: Session ORM object
            stats: Pre-aggregated stats dictionaries

        Returns:
            Dictionary with all SessionWithStats fields

        Complexity: A (5) - field mapping + NULL checks + dict lookups
        """
        # Get stats from pre-fetched dicts (O(1) lookup)
        booking_stats = stats['bookings'].get(
            session.id,
            {'total': 0, 'confirmed': 0, 'waitlisted': 0}
        )
        attendance_count = stats['attendance'].get(session.id, 0)
        avg_rating = stats['ratings'].get(session.id, None)

        # Build session data with NULL handling
        return {
            "id": session.id,
            "title": session.title,
            "description": session.description or "",
            "date_start": session.date_start,
            "date_end": session.date_end,
            "session_type": session.session_type,
            # NULL handling: capacity
            "capacity": session.capacity if session.capacity is not None else 0,
            # NULL handling: credit_cost
            "credit_cost": session.credit_cost if session.credit_cost is not None else 1,
            "location": session.location,
            "meeting_link": session.meeting_link,
            "sport_type": session.sport_type,
            "level": session.level,
            "instructor_name": session.instructor_name,
            "semester_id": session.semester_id,
            "group_id": session.group_id,
            "instructor_id": session.instructor_id,
            "campus_id": session.campus_id,  # 🏟️ Multi-campus support
            # NULL handling: created_at
            "created_at": session.created_at or session.date_start,
            "updated_at": session.updated_at,
            "target_specialization": session.target_specialization,
            # NULL handling: mixed_specialization (missing attribute)
            "mixed_specialization": (
                session.mixed_specialization
                if hasattr(session, 'mixed_specialization')
                else False
            ),
            # Tournament flags (must be included)
            "is_tournament_game": (
                session.is_tournament_game
                if hasattr(session, 'is_tournament_game')
                else False
            ),
            "game_type": (
                session.game_type
                if hasattr(session, 'game_type')
                else None
            ),
            # Relationships (eagerly loaded)
            "semester": session.semester,
            "group": session.group,
            "instructor": session.instructor,
            # Pre-aggregated stats
            "booking_count": booking_stats['total'],
            "confirmed_bookings": booking_stats['confirmed'],
            "current_bookings": booking_stats['confirmed'],  # Alias
            "waitlist_count": booking_stats['waitlisted'],
            "attendance_count": attendance_count,
            "average_rating": float(avg_rating) if avg_rating else None
        }
