"""
Tournament Repository

Provides centralized data access for tournament (Semester) entities.
Eliminates 20+ duplicated tournament fetch patterns across endpoints.

Usage:
    from app.repositories import TournamentRepository

    repo = TournamentRepository(db)
    tournament = repo.get_or_404(tournament_id)
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List

from ..models.semester import Semester
from ..models.semester_enrollment import SemesterEnrollment
from ..models.session import Session as SessionModel


class TournamentRepository:
    """
    Repository for tournament (Semester) data access.

    Eliminates duplicated queries in:
    - instructor_assignment.py (7 occurrences)
    - lifecycle.py (5 occurrences)
    - match_results.py (4 occurrences)
    - instructor.py (3 occurrences)
    - enroll.py (2 occurrences)
    - And 10+ more files
    """

    def __init__(self, db: Session):
        """
        Initialize repository with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_or_404(
        self,
        tournament_id: int,
        error_detail: Optional[str] = None
    ) -> Semester:
        """
        Get tournament by ID or raise 404.

        Args:
            tournament_id: Tournament ID to fetch
            error_detail: Optional custom error message

        Returns:
            Semester instance

        Raises:
            HTTPException(404): If tournament not found

        Example:
            >>> repo = TournamentRepository(db)
            >>> tournament = repo.get_or_404(123)
        """
        tournament = self.db.query(Semester).filter(
            Semester.id == tournament_id
        ).first()

        if not tournament:
            detail = error_detail or f"Tournament {tournament_id} not found"
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail
            )

        return tournament

    def get_with_enrollments(self, tournament_id: int) -> Semester:
        """
        Get tournament with enrollments eagerly loaded.

        Args:
            tournament_id: Tournament ID to fetch

        Returns:
            Semester instance with semester_enrollments loaded

        Raises:
            HTTPException(404): If tournament not found

        Example:
            >>> tournament = repo.get_with_enrollments(123)
            >>> for enrollment in tournament.semester_enrollments:
            ...     print(enrollment.user_id)
        """
        tournament = self.db.query(Semester).options(
            joinedload(Semester.semester_enrollments)
        ).filter(Semester.id == tournament_id).first()

        if not tournament:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tournament {tournament_id} not found"
            )

        return tournament

    def get_with_sessions(self, tournament_id: int) -> Semester:
        """
        Get tournament with sessions eagerly loaded.

        Args:
            tournament_id: Tournament ID to fetch

        Returns:
            Semester instance with sessions loaded

        Raises:
            HTTPException(404): If tournament not found

        Example:
            >>> tournament = repo.get_with_sessions(123)
            >>> for session in tournament.sessions:
            ...     print(session.session_date)
        """
        tournament = self.db.query(Semester).options(
            joinedload(Semester.sessions)
        ).filter(Semester.id == tournament_id).first()

        if not tournament:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tournament {tournament_id} not found"
            )

        return tournament

    def get_with_full_details(self, tournament_id: int) -> Semester:
        """
        Get tournament with all relations eagerly loaded.

        Loads:
        - semester_enrollments
        - sessions
        - campus
        - location

        Args:
            tournament_id: Tournament ID to fetch

        Returns:
            Semester instance with all relations loaded

        Raises:
            HTTPException(404): If tournament not found
        """
        tournament = self.db.query(Semester).options(
            joinedload(Semester.semester_enrollments),
            joinedload(Semester.sessions),
            joinedload(Semester.campus),
            joinedload(Semester.location)
        ).filter(Semester.id == tournament_id).first()

        if not tournament:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tournament {tournament_id} not found"
            )

        return tournament

    def get_optional(self, tournament_id: int) -> Optional[Semester]:
        """
        Get tournament by ID, returning None if not found.

        Args:
            tournament_id: Tournament ID to fetch

        Returns:
            Semester instance or None if not found

        Example:
            >>> tournament = repo.get_optional(123)
            >>> if tournament:
            ...     print(tournament.name)
        """
        return self.db.query(Semester).filter(
            Semester.id == tournament_id
        ).first()

    def get_active_tournaments(
        self,
        campus_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Semester]:
        """
        Get list of active tournaments.

        Args:
            campus_id: Optional campus ID to filter by
            limit: Maximum number of results (default: 100)

        Returns:
            List of active Semester instances
        """
        query = self.db.query(Semester).filter(
            Semester.is_active == True
        )

        if campus_id:
            query = query.filter(Semester.campus_id == campus_id)

        return query.order_by(Semester.start_date.desc()).limit(limit).all()

    def get_tournaments_by_status(
        self,
        tournament_status: str,
        campus_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Semester]:
        """
        Get tournaments by status.

        Args:
            tournament_status: Tournament status (DRAFT, IN_PROGRESS, etc.)
            campus_id: Optional campus ID to filter by
            limit: Maximum number of results

        Returns:
            List of Semester instances matching status
        """
        query = self.db.query(Semester).filter(
            Semester.tournament_status == tournament_status
        )

        if campus_id:
            query = query.filter(Semester.campus_id == campus_id)

        return query.order_by(Semester.created_at.desc()).limit(limit).all()

    def exists(self, tournament_id: int) -> bool:
        """
        Check if tournament exists.

        Args:
            tournament_id: Tournament ID to check

        Returns:
            True if tournament exists, False otherwise

        Example:
            >>> if repo.exists(123):
            ...     print("Tournament exists")
        """
        return self.db.query(Semester).filter(
            Semester.id == tournament_id
        ).count() > 0

    def delete(self, tournament_id: int) -> None:
        """
        Delete tournament by ID.

        Args:
            tournament_id: Tournament ID to delete

        Raises:
            HTTPException(404): If tournament not found
        """
        tournament = self.get_or_404(tournament_id)
        self.db.delete(tournament)
        self.db.commit()

    def update(self, tournament: Semester) -> Semester:
        """
        Update tournament in database.

        Args:
            tournament: Semester instance with updated fields

        Returns:
            Updated Semester instance
        """
        self.db.add(tournament)
        self.db.commit()
        self.db.refresh(tournament)
        return tournament


# Export main class
__all__ = ["TournamentRepository"]
