"""
Tournament Core Service - CRUD operations for tournaments

This module contains core business logic for tournament creation, session management,
and basic CRUD operations. Extracted from the monolithic tournament_service.py
for better maintainability.

Functions:
    - create_tournament_semester: Create a 1-day tournament semester
    - create_tournament_sessions: Create multiple sessions for a tournament
    - get_tournament_summary: Get summary statistics for a tournament
    - delete_tournament: Delete a tournament and all associated data
"""

from datetime import date, datetime, time, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.semester import Semester, SemesterStatus
from app.models.session import Session as SessionModel, SessionType
from app.models.booking import Booking
from app.models.specialization import SpecializationType
from app.services.tournament.reward_policy_loader import load_policy, RewardPolicyError


def create_tournament_semester(
    db: Session,
    tournament_date: date,
    name: str,
    specialization_type: SpecializationType,
    campus_id: Optional[int] = None,
    location_id: Optional[int] = None,
    age_group: Optional[str] = None,
    reward_policy_name: str = "default",
    # 🎯 NEW: Explicit business attributes (DOMAIN GAP RESOLUTION)
    assignment_type: str = "APPLICATION_BASED",
    max_players: Optional[int] = None,
    enrollment_cost: int = 500,
    instructor_id: Optional[int] = None
) -> Semester:
    """
    Create a 1-day semester for tournament (Admin only)

    IMPORTANT: Tournament behavior depends on assignment_type:
    - OPEN_ASSIGNMENT: instructor_id required, tournament immediately READY_FOR_ENROLLMENT
    - APPLICATION_BASED: instructor_id should be None, tournament starts as SEEKING_INSTRUCTOR

    Args:
        db: Database session
        tournament_date: Date of tournament (start_date == end_date)
        name: Tournament name (e.g., "Holiday Football Cup")
        specialization_type: Specialization type for the tournament
        campus_id: Optional campus ID (preferred - most specific location)
        location_id: Optional location ID (fallback if campus not specified)
        age_group: Optional age group
        reward_policy_name: Name of reward policy to use (default: "default")
        assignment_type: Instructor assignment strategy (OPEN_ASSIGNMENT | APPLICATION_BASED)
        max_players: Maximum tournament participants (explicit capacity)
        enrollment_cost: Enrollment fee in credits (explicit pricing)
        instructor_id: Instructor ID (required for OPEN_ASSIGNMENT, None for APPLICATION_BASED)

    Returns:
        Created semester object with appropriate status based on assignment_type

    Raises:
        RewardPolicyError: If reward policy cannot be loaded
        ValueError: If instructor_id is not None at creation
    """
    # ⚠️ BUSINESS LOGIC: instructor_id must be None at creation
    # Instructor assignment happens AFTER via Tournament Management:
    # - OPEN_ASSIGNMENT: Admin invites specific instructor (invitation flow)
    # - APPLICATION_BASED: Instructors apply, admin selects one
    if instructor_id is not None:
        raise ValueError(
            "instructor_id must be None at tournament creation. "
            "Instructor assignment happens AFTER creation via Tournament Management."
        )

    # Generate code: TOURN-YYYYMMDD-XXX (e.g., TOURN-20260113-001)
    # Multiple tournaments can exist on the same date, so we need a sequence number
    date_prefix = f"TOURN-{tournament_date.strftime('%Y%m%d')}"

    # Find existing tournaments on this date
    existing_tournaments = db.query(Semester).filter(
        Semester.code.like(f"{date_prefix}%")
    ).count()

    # Generate unique code with sequence number
    sequence_num = existing_tournaments + 1
    code = f"{date_prefix}-{sequence_num:03d}"

    # Load and snapshot the reward policy
    reward_policy = load_policy(reward_policy_name)

    # ⚠️ BUSINESS LOGIC: ALL tournaments start as SEEKING_INSTRUCTOR
    # Status transitions:
    # - OPEN_ASSIGNMENT: Admin invites instructor → instructor accepts → READY_FOR_ENROLLMENT
    # - APPLICATION_BASED: Instructors apply → admin selects → instructor accepts → READY_FOR_ENROLLMENT
    status = SemesterStatus.SEEKING_INSTRUCTOR
    tournament_status = "SEEKING_INSTRUCTOR"

    semester = Semester(
        code=code,
        name=name,
        start_date=tournament_date,
        end_date=tournament_date,  # 1-day tournament
        is_active=True,
        status=status,
        tournament_status=tournament_status,
        master_instructor_id=None,  # ⚠️ ALWAYS None at creation
        specialization_type=specialization_type.value if hasattr(specialization_type, 'value') else specialization_type,
        age_group=age_group,
        campus_id=campus_id,
        location_id=location_id,
        reward_policy_name=reward_policy_name,
        reward_policy_snapshot=reward_policy,  # Immutable snapshot of policy
        # 🎯 NEW: Explicit business attributes
        assignment_type=assignment_type,
        max_players=max_players,
        enrollment_cost=enrollment_cost
    )

    db.add(semester)
    db.commit()
    db.refresh(semester)

    return semester


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
            instructor_id=None,  # No instructor yet - will be assigned via semester
            semester_id=semester_id,
            credit_cost=config.get("credit_cost", 1),
            # Tournament game fields
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


def get_tournament_summary(db: Session, semester_id: int) -> Dict[str, Any]:
    """
    Get summary of tournament

    Args:
        db: Database session
        semester_id: Tournament semester ID

    Returns:
        Dictionary with tournament summary including:
        - id, tournament_id, semester_id
        - code, name, date
        - status, specialization_type, age_group
        - location_id, campus_id
        - session_count, total_capacity, total_bookings
        - fill_percentage
        - sessions list with details
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
        "id": semester.id,
        "tournament_id": semester.id,
        "semester_id": semester.id,
        "code": semester.code,
        "name": semester.name,
        "start_date": semester.start_date.isoformat(),
        "date": semester.start_date.isoformat(),
        "status": semester.status.value if semester.status else None,
        "specialization_type": semester.specialization_type,
        "age_group": semester.age_group,
        "location_id": semester.location_id,
        "campus_id": semester.campus_id,
        "reward_policy_name": semester.reward_policy_name,
        "reward_policy_snapshot": semester.reward_policy_snapshot,
        "session_count": len(sessions),
        "sessions_count": len(sessions),
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
