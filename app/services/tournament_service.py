"""
Tournament Service - Backward Compatibility Layer

DEPRECATED: This module is kept for backward compatibility only.
Please use the new modular structure instead:

    from app.services.tournament import (
        create_tournament_semester,
        create_tournament_sessions,
        get_tournament_summary,
        delete_tournament,
        send_instructor_request,
        accept_instructor_request,
        decline_instructor_request,
        auto_book_students,
    )

Or import the entire tournament service package:

    from app.services import tournament

New structure:
- app.services.tournament.core: CRUD operations
- app.services.tournament.validation: Validation logic
- app.services.tournament.instructor_service: Instructor assignment
- app.services.tournament.enrollment_service: Enrollment logic

This class re-exports all functions as static methods to maintain backward compatibility
with existing code that uses TournamentService.function_name() syntax.
"""
from datetime import date
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

# Import from new modular structure
from app.services.tournament.core import (
    create_tournament_semester as _create_tournament_semester,
    create_tournament_sessions as _create_tournament_sessions,
    get_tournament_summary as _get_tournament_summary,
    delete_tournament as _delete_tournament,
)

from app.services.tournament.instructor_service import (
    send_instructor_request as _send_instructor_request,
    accept_instructor_request as _accept_instructor_request,
    decline_instructor_request as _decline_instructor_request,
)

from app.services.tournament.enrollment_service import (
    auto_book_students as _auto_book_students,
)

from app.models.semester import Semester
from app.models.session import Session as SessionModel
from app.models.instructor_assignment import InstructorAssignmentRequest
from app.models.specialization import SpecializationType


class TournamentService:
    """
    DEPRECATED: Backward compatibility wrapper for tournament functions.

    This class maintains the old TournamentService.method() API by delegating
    to the new modular structure.

    Migration Guide:
    ----------------
    OLD:
        from app.services.tournament_service import TournamentService
        semester = TournamentService.create_tournament_semester(db, ...)

    NEW:
        from app.services.tournament import create_tournament_semester
        semester = create_tournament_semester(db, ...)

    Or:
        from app.services import tournament
        semester = tournament.create_tournament_semester(db, ...)
    """

    # ========================================================================
    # CORE CRUD OPERATIONS
    # ========================================================================

    @staticmethod
    def create_tournament_semester(
        db: Session,
        tournament_date: date,
        name: str,
        specialization_type: SpecializationType,
        campus_id: Optional[int] = None,
        location_id: Optional[int] = None,
        age_group: Optional[str] = None,
        reward_policy_name: str = "default"
    ) -> Semester:
        """DEPRECATED: Use app.services.tournament.create_tournament_semester instead"""
        return _create_tournament_semester(
            db, tournament_date, name, specialization_type,
            campus_id, location_id, age_group, reward_policy_name
        )

    @staticmethod
    def create_tournament_sessions(
        db: Session,
        semester_id: int,
        session_configs: List[Dict[str, Any]],
        tournament_date: date
    ) -> List[SessionModel]:
        """DEPRECATED: Use app.services.tournament.create_tournament_sessions instead"""
        return _create_tournament_sessions(db, semester_id, session_configs, tournament_date)

    @staticmethod
    def get_tournament_summary(db: Session, semester_id: int) -> Dict[str, Any]:
        """DEPRECATED: Use app.services.tournament.get_tournament_summary instead"""
        return _get_tournament_summary(db, semester_id)

    @staticmethod
    def delete_tournament(db: Session, semester_id: int) -> bool:
        """DEPRECATED: Use app.services.tournament.delete_tournament instead"""
        return _delete_tournament(db, semester_id)

    # ========================================================================
    # INSTRUCTOR ASSIGNMENT
    # ========================================================================

    @staticmethod
    def send_instructor_request(
        db: Session,
        semester_id: int,
        instructor_id: int,
        requested_by_admin_id: int,
        message: Optional[str] = None
    ) -> InstructorAssignmentRequest:
        """DEPRECATED: Use app.services.tournament.send_instructor_request instead"""
        return _send_instructor_request(
            db, semester_id, instructor_id, requested_by_admin_id, message
        )

    @staticmethod
    def accept_instructor_request(
        db: Session,
        request_id: int,
        instructor_id: int
    ) -> Semester:
        """DEPRECATED: Use app.services.tournament.accept_instructor_request instead"""
        return _accept_instructor_request(db, request_id, instructor_id)

    @staticmethod
    def decline_instructor_request(
        db: Session,
        request_id: int,
        instructor_id: int,
        reason: Optional[str] = None
    ) -> InstructorAssignmentRequest:
        """DEPRECATED: Use app.services.tournament.decline_instructor_request instead"""
        return _decline_instructor_request(db, request_id, instructor_id, reason)

    # ========================================================================
    # ENROLLMENT
    # ========================================================================

    @staticmethod
    def auto_book_students(
        db: Session,
        session_ids: List[int],
        capacity_percentage: int = 70
    ) -> Dict[int, List[int]]:
        """DEPRECATED: Use app.services.tournament.auto_book_students instead"""
        return _auto_book_students(db, session_ids, capacity_percentage)
