"""
Tournament Service - Business logic for one-day tournament creation

Provides functionality to create one-day tournaments with:
- 1-day semester (admin creates)
- Multiple sessions within the day
- Master instructor assignment (required before activation)
- Auto-booking of students (optional)
- Flexible capacity management

Workflow:
1. Admin creates tournament semester → status: SEEKING_INSTRUCTOR
2. Admin assigns master instructor → status: READY_FOR_ENROLLMENT
3. Students can register/book sessions
4. Master instructor leads on-site check-in and group assignments
"""
from datetime import date, datetime, time, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.semester import Semester, SemesterStatus
from app.models.session import Session as SessionModel, SessionType
from app.models.booking import Booking, BookingStatus
from app.models.user import User, UserRole
from app.models.specialization import SpecializationType
from app.models.instructor_assignment import InstructorAssignmentRequest, AssignmentRequestStatus


class TournamentService:
    """Service for creating and managing one-day tournaments"""

    @staticmethod
    def create_tournament_semester(
        db: Session,
        tournament_date: date,
        name: str,
        specialization_type: SpecializationType,
        campus_id: Optional[int] = None,
        location_id: Optional[int] = None,
        age_group: Optional[str] = None
    ) -> Semester:
        """
        Create a 1-day semester for tournament (Admin only)

        IMPORTANT: Tournament is created WITHOUT master instructor.
        Status is SEEKING_INSTRUCTOR - admin must assign instructor to activate.

        Args:
            db: Database session
            tournament_date: Date of tournament (start_date == end_date)
            name: Tournament name (e.g., "Holiday Football Cup")
            specialization_type: Specialization type for the tournament
            campus_id: Optional campus ID (preferred - most specific location)
            location_id: Optional location ID (fallback if campus not specified)
            age_group: Optional age group

        Returns:
            Created semester object with status SEEKING_INSTRUCTOR
        """
        # Generate code: TOURN-YYYYMMDD (e.g., TOURN-20251227)
        code = f"TOURN-{tournament_date.strftime('%Y%m%d')}"

        semester = Semester(
            code=code,
            name=name,
            start_date=tournament_date,
            end_date=tournament_date,  # 1-day tournament
            is_active=True,
            status=SemesterStatus.SEEKING_INSTRUCTOR,  # ✅ Tournament needs master instructor
            master_instructor_id=None,  # No instructor yet - admin assigns later
            specialization_type=specialization_type.value if hasattr(specialization_type, 'value') else specialization_type,
            age_group=age_group,
            campus_id=campus_id,  # ✅ NEW: Campus support
            location_id=location_id
        )

        db.add(semester)
        db.commit()
        db.refresh(semester)

        return semester

    @staticmethod
    def create_tournament_sessions(
        db: Session,
        semester_id: int,
        session_configs: List[Dict[str, Any]],
        tournament_date: date
    ) -> List[SessionModel]:
        """
        Create multiple sessions for tournament (Admin only)

        IMPORTANT: Sessions are created WITHOUT instructor assignment.
        Sessions will inherit master_instructor_id from semester when assigned.

        Args:
            db: Database session
            semester_id: Tournament semester ID
            session_configs: List of session configurations, each with:
                - time: str (e.g., "09:00")
                - duration_minutes: int (default: 90)
                - title: str
                - capacity: int (default: 20)
                - credit_cost: int (default: 1)
                - game_type: str (optional, user-defined game type)
            tournament_date: Date of tournament

        Returns:
            List of created session objects
        """
        created_sessions = []

        for config in session_configs:
            # Parse time
            session_time = datetime.strptime(config["time"], "%H:%M").time()
            start_datetime = datetime.combine(tournament_date, session_time)

            duration = config.get("duration_minutes", 90)
            end_datetime = start_datetime + timedelta(minutes=duration)

            session = SessionModel(
                title=config["title"],
                description=config.get("description", ""),
                date_start=start_datetime,
                date_end=end_datetime,
                session_type=SessionType.on_site,  # Tournaments are typically on-site
                capacity=config.get("capacity", 20),
                instructor_id=None,  # ✅ No instructor yet - will be assigned via semester
                semester_id=semester_id,
                credit_cost=config.get("credit_cost", 1),
                # 🏆 Tournament game fields
                is_tournament_game=True,  # Mark as tournament game
                game_type=config.get("game_type")  # User-defined game type (optional)
            )

            db.add(session)
            created_sessions.append(session)

        db.commit()

        # Refresh all sessions to get IDs
        for session in created_sessions:
            db.refresh(session)

        return created_sessions

    @staticmethod
    def send_instructor_request(
        db: Session,
        semester_id: int,
        instructor_id: int,
        requested_by_admin_id: int,
        message: Optional[str] = None
    ) -> InstructorAssignmentRequest:
        """
        Send assignment request to instructor (grandmaster) for tournament

        IMPORTANT: This creates a PENDING request. Tournament activates only when
        instructor ACCEPTS the request.

        Workflow:
        1. Admin sends request → Status: PENDING
        2. Instructor accepts → Tournament status: READY_FOR_ENROLLMENT
        3. Instructor declines → Tournament status: SEEKING_INSTRUCTOR (stays)

        Args:
            db: Database session
            semester_id: Tournament semester ID
            instructor_id: Grandmaster instructor ID to invite
            requested_by_admin_id: Admin user ID sending the request
            message: Optional message to instructor

        Returns:
            Created InstructorAssignmentRequest object

        Raises:
            ValueError: If semester not found, instructor invalid, or duplicate request
        """
        # Get semester
        semester = db.query(Semester).filter(Semester.id == semester_id).first()
        if not semester:
            raise ValueError(f"Tournament semester {semester_id} not found")

        # Verify current status
        if semester.status != SemesterStatus.SEEKING_INSTRUCTOR:
            raise ValueError(
                f"Tournament status must be SEEKING_INSTRUCTOR, currently: {semester.status}"
            )

        # Verify instructor exists and is instructor role
        instructor = db.query(User).filter(User.id == instructor_id).first()
        if not instructor:
            raise ValueError(f"Instructor {instructor_id} not found")

        if instructor.role != UserRole.INSTRUCTOR:
            raise ValueError(f"User {instructor_id} is not an instructor")

        # Check for existing pending request
        existing_request = db.query(InstructorAssignmentRequest).filter(
            and_(
                InstructorAssignmentRequest.semester_id == semester_id,
                InstructorAssignmentRequest.status == AssignmentRequestStatus.PENDING
            )
        ).first()

        if existing_request:
            raise ValueError(
                f"Pending request already exists for this tournament (Request ID: {existing_request.id})"
            )

        # Create assignment request
        assignment_request = InstructorAssignmentRequest(
            semester_id=semester_id,
            instructor_id=instructor_id,
            requested_by=requested_by_admin_id,
            status=AssignmentRequestStatus.PENDING,
            request_message=message or f"Please lead the '{semester.name}' tournament on {semester.start_date}"
        )

        db.add(assignment_request)
        db.commit()
        db.refresh(assignment_request)

        return assignment_request

    @staticmethod
    def accept_instructor_request(
        db: Session,
        request_id: int,
        instructor_id: int
    ) -> Semester:
        """
        Instructor accepts tournament assignment request

        IMPORTANT: This activates the tournament by changing status to READY_FOR_ENROLLMENT.

        Args:
            db: Database session
            request_id: Assignment request ID
            instructor_id: Instructor ID (must match request)

        Returns:
            Updated semester object

        Raises:
            ValueError: If request not found, unauthorized, or invalid status
        """
        # Get request
        assignment_request = db.query(InstructorAssignmentRequest).filter(
            InstructorAssignmentRequest.id == request_id
        ).first()

        if not assignment_request:
            raise ValueError(f"Assignment request {request_id} not found")

        # Verify instructor matches
        if assignment_request.instructor_id != instructor_id:
            raise ValueError("You are not authorized to accept this request")

        # Verify request status
        if assignment_request.status != AssignmentRequestStatus.PENDING:
            raise ValueError(
                f"Request status must be PENDING, currently: {assignment_request.status}"
            )

        # Get semester
        semester = db.query(Semester).filter(
            Semester.id == assignment_request.semester_id
        ).first()

        if not semester:
            raise ValueError(f"Tournament semester not found")

        # Accept request
        assignment_request.status = AssignmentRequestStatus.ACCEPTED
        assignment_request.responded_at = datetime.now()

        # Assign instructor to semester and activate
        semester.master_instructor_id = instructor_id
        semester.status = SemesterStatus.READY_FOR_ENROLLMENT

        # Assign to all sessions
        sessions = db.query(SessionModel).filter(
            SessionModel.semester_id == semester.id
        ).all()
        for session in sessions:
            session.instructor_id = instructor_id

        db.commit()
        db.refresh(semester)

        return semester

    @staticmethod
    def decline_instructor_request(
        db: Session,
        request_id: int,
        instructor_id: int,
        reason: Optional[str] = None
    ) -> InstructorAssignmentRequest:
        """
        Instructor declines tournament assignment request

        Tournament remains in SEEKING_INSTRUCTOR status. Admin can send new request.

        Args:
            db: Database session
            request_id: Assignment request ID
            instructor_id: Instructor ID (must match request)
            reason: Optional reason for declining

        Returns:
            Updated InstructorAssignmentRequest object

        Raises:
            ValueError: If request not found, unauthorized, or invalid status
        """
        # Get request
        assignment_request = db.query(InstructorAssignmentRequest).filter(
            InstructorAssignmentRequest.id == request_id
        ).first()

        if not assignment_request:
            raise ValueError(f"Assignment request {request_id} not found")

        # Verify instructor matches
        if assignment_request.instructor_id != instructor_id:
            raise ValueError("You are not authorized to decline this request")

        # Verify request status
        if assignment_request.status != AssignmentRequestStatus.PENDING:
            raise ValueError(
                f"Request status must be PENDING, currently: {assignment_request.status}"
            )

        # Decline request
        assignment_request.status = AssignmentRequestStatus.DECLINED
        assignment_request.responded_at = datetime.now()
        if reason:
            assignment_request.response_message = reason

        db.commit()
        db.refresh(assignment_request)

        return assignment_request

    @staticmethod
    def auto_book_students(
        db: Session,
        session_ids: List[int],
        capacity_percentage: int = 70
    ) -> Dict[int, List[int]]:
        """
        Auto-book students for tournament sessions

        Args:
            db: Database session
            session_ids: List of session IDs to book
            capacity_percentage: Percentage of capacity to fill (default: 70%)

        Returns:
            Dict mapping session_id -> list of booked user_ids
        """
        bookings_map = {}

        # Get all active students
        students = db.query(User).filter(
            and_(
                User.role == UserRole.STUDENT,
                User.is_active == True
            )
        ).all()

        if not students:
            return bookings_map

        for session_id in session_ids:
            session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            if not session:
                continue

            # Calculate target bookings
            target_bookings = int(session.capacity * (capacity_percentage / 100))
            target_bookings = min(target_bookings, len(students))

            # Book first N students
            booked_user_ids = []
            for i in range(target_bookings):
                student = students[i % len(students)]  # Cycle through students

                booking = Booking(
                    user_id=student.id,
                    session_id=session_id,
                    status=BookingStatus.CONFIRMED
                )
                db.add(booking)
                booked_user_ids.append(student.id)

            bookings_map[session_id] = booked_user_ids

        db.commit()
        return bookings_map

    @staticmethod
    def get_tournament_summary(db: Session, semester_id: int) -> Dict[str, Any]:
        """
        Get summary of tournament

        Args:
            db: Database session
            semester_id: Tournament semester ID

        Returns:
            Dictionary with tournament summary
        """
        semester = db.query(Semester).filter(Semester.id == semester_id).first()
        if not semester:
            return {}

        sessions = db.query(SessionModel).filter(SessionModel.semester_id == semester_id).all()

        total_capacity = sum(s.capacity for s in sessions)
        total_bookings = db.query(Booking).filter(
            Booking.session_id.in_([s.id for s in sessions])
        ).count()

        return {
            "id": semester.id,  # ✅ Added for frontend compatibility
            "tournament_id": semester.id,  # ✅ Added for frontend compatibility
            "semester_id": semester.id,
            "code": semester.code,  # ✅ Added tournament code
            "name": semester.name,
            "start_date": semester.start_date.isoformat(),  # ✅ Added for frontend
            "date": semester.start_date.isoformat(),
            "status": semester.status.value if semester.status else None,  # ✅ Added tournament status
            "specialization_type": semester.specialization_type,  # ✅ Added specialization
            "age_group": semester.age_group,  # ✅ Added age group
            "location_id": semester.location_id,  # ✅ Added location_id
            "campus_id": semester.campus_id,  # ✅ Added campus_id
            "session_count": len(sessions),
            "sessions_count": len(sessions),  # ✅ Added for frontend compatibility
            "sessions": [
                {
                    "id": s.id,
                    "title": s.title,
                    "time": s.date_start.strftime("%H:%M"),
                    "capacity": s.capacity,
                    "bookings": db.query(Booking).filter(Booking.session_id == s.id).count()
                }
                for s in sessions
            ],
            "total_capacity": total_capacity,
            "total_bookings": total_bookings,
            "fill_percentage": round((total_bookings / total_capacity * 100) if total_capacity > 0 else 0, 1)
        }

    @staticmethod
    def delete_tournament(db: Session, semester_id: int) -> bool:
        """
        Delete tournament and all associated sessions/bookings

        Args:
            db: Database session
            semester_id: Tournament semester ID

        Returns:
            True if deleted successfully
        """
        semester = db.query(Semester).filter(Semester.id == semester_id).first()
        if not semester:
            return False

        # Cascade delete will handle sessions and bookings
        db.delete(semester)
        db.commit()

        return True
