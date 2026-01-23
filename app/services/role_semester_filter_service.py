"""
RoleSemesterFilterService

Responsibility:
    Applies role-based semester filtering to session queries.
    Handles student (with Mbappé LFA Testing override), admin, and instructor logic.

Critical Edge Cases:
    - Mbappé cross-semester override: ALL sessions across ALL semesters
    - Multi-semester support: Concurrent semester tracks for students
    - Instructor PENDING requests: Show semesters with pending assignments

Architecture:
    - Main method delegates to role-specific private methods
    - Student logic: D21 → B7 (Mbappé + multi-semester)
    - Instructor logic: C15 → B7 (PENDING subquery)
    - Admin logic: A2 → A1 (simple filter)

Complexity Target: B (8) for main dispatcher
"""

from typing import Optional
from sqlalchemy.orm import Session as DBSession, Query
from sqlalchemy import and_, or_
from datetime import date

from ..models.user import User, UserRole
from ..models.semester import Semester
from ..models.session import Session as SessionTypel


class RoleSemesterFilterService:
    """
    Service for applying role-based semester filtering to session queries.

    Preserves all edge cases including Mbappé LFA Testing override
    and multi-semester support for concurrent tracks.
    """

    def __init__(self, db: DBSession):
        """
        Initialize role semester filter service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def apply_role_semester_filter(
        self,
        query: Query,
        user: User,
        semester_id: Optional[int]
    ) -> Query:
        """
        Apply role-based semester filtering.

        Delegates to role-specific methods based on user role.
        Handles student (with Mbappé override), admin, and instructor logic.

        Args:
            query: Base SQLAlchemy query for sessions
            user: Current user with role
            semester_id: Optional explicit semester filter

        Returns:
            Filtered query

        Complexity: B (8) - 3 role branches + Mbappé edge case
        """
        if user.role == UserRole.STUDENT:
            return self._filter_student_semesters(query, user, semester_id)
        elif user.role == UserRole.ADMIN:
            return self._filter_admin_semesters(query, semester_id)
        elif user.role == UserRole.INSTRUCTOR:
            return self._filter_instructor_semesters(query, user, semester_id)

        # Fallback: no filtering
        return query

    def _filter_student_semesters(
        self,
        query: Query,
        user: User,
        semester_id: Optional[int]
    ) -> Query:
        """
        Apply student semester filtering.

        🌐 CRITICAL: Mbappé (LFA Testing) override preserved 1:1
        - Mbappé gets ALL sessions across ALL semesters
        - Regular students see current active semesters (multi-semester support)
        - Fallback to recent semesters if no current ones

        Args:
            query: Base query
            user: Student user
            semester_id: Optional explicit semester filter

        Returns:
            Filtered query

        Complexity: B (7) - Mbappé check + multi-semester logic + fallback
        """
        # 🌐 CRITICAL: Cross-semester logic for Mbappé (LFA Testing)
        # This logic is UNCHANGED from original implementation
        if user.email == "mbappe@lfa.com":
            # Mbappé gets access to ALL sessions across ALL semesters
            print(f"🌐 Cross-semester access granted for {user.name} (LFA Testing)")

            # Only apply semester_id filter if explicitly requested
            if semester_id:
                query = query.filter_by(semester_id=semester_id)
                print(f"🎯 Mbappé filtering by specific semester: {semester_id}")
            else:
                print("🌐 Mbappé accessing ALL sessions across ALL semesters")

            return query

        # Regular students: show sessions from all current active semesters
        if not semester_id:
            # Get all current active semesters (including parallel tracks)
            today = date.today()

            current_semesters = self.db.query(Semester).filter(
                and_(
                    Semester.start_date <= today,
                    Semester.end_date >= today,
                    Semester.is_active == True
                )
            ).all()

            if current_semesters:
                semester_ids = [s.id for s in current_semesters]
                query = query.filter(SessionTypel.semester_id.in_(semester_ids))
                print(f"Student seeing sessions from {len(current_semesters)} current semesters: {[s.name for s in current_semesters]}")
            else:
                # Fallback: if no current semesters by date, show most recent semesters
                recent_semesters = self.db.query(Semester).filter(
                    Semester.is_active == True
                ).order_by(Semester.id.desc()).limit(3).all()

                if recent_semesters:
                    semester_ids = [s.id for s in recent_semesters]
                    query = query.filter(SessionTypel.semester_id.in_(semester_ids))
                    print(f"Fallback: Student seeing sessions from {len(recent_semesters)} recent semesters")
        else:
            # Allow filtering by specific semester for students
            query = query.filter_by(semester_id=semester_id)

        return query

    def _filter_admin_semesters(
        self,
        query: Query,
        semester_id: Optional[int]
    ) -> Query:
        """
        Apply admin semester filtering.

        Admin sees all sessions, optionally filtered by semester_id.

        Args:
            query: Base query
            semester_id: Optional explicit semester filter

        Returns:
            Filtered query

        Complexity: A (1) - simple conditional filter
        """
        if semester_id:
            query = query.filter_by(semester_id=semester_id)

        return query

    def _filter_instructor_semesters(
        self,
        query: Query,
        user: User,
        semester_id: Optional[int]
    ) -> Query:
        """
        Apply instructor semester filtering.

        Instructor sees sessions from semesters where:
        1. They are assigned as master instructor (ACCEPTED)
        2. They have a PENDING assignment request

        ⚠️ CRITICAL: PENDING logic remains explicit (not implicit)

        Args:
            query: Base query
            user: Instructor user
            semester_id: Optional explicit semester filter

        Returns:
            Filtered query with JOIN

        Complexity: B (7) - subquery + JOIN + OR condition + optional filter
        """
        from ..models.instructor_assignment import (
            InstructorAssignmentRequest,
            AssignmentRequestStatus
        )

        # Subquery for PENDING request semester IDs
        pending_semester_ids = self.db.query(
            InstructorAssignmentRequest.semester_id
        ).filter(
            InstructorAssignmentRequest.instructor_id == user.id,
            InstructorAssignmentRequest.status == AssignmentRequestStatus.PENDING
        ).subquery()

        # Join with Semester and filter
        query = query.join(Semester, SessionTypel.semester_id == Semester.id)

        query = query.filter(
            or_(
                Semester.master_instructor_id == user.id,  # ACCEPTED
                Semester.id.in_(pending_semester_ids)       # PENDING
            )
        )

        # Optional: semester_id filter still works
        if semester_id:
            query = query.filter_by(semester_id=semester_id)

        return query
