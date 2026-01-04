"""
Session query operations
List, filter, recommendations, bookings, instructor sessions, calendar
"""
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, case
from datetime import datetime, date, timezone

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User, UserRole
from .....models.semester import Semester
from .....models.session import Session as SessionTypel, SessionType
from .....models.booking import Booking, BookingStatus
from .....models.attendance import Attendance
from .....models.feedback import Feedback
from .....models.specialization import SpecializationType
from .....schemas.session import SessionWithStats, SessionList
from .....schemas.booking import BookingWithRelations, BookingList
from .....services.session_filter_service import SessionFilterService

router = APIRouter()


@router.get("/", response_model=SessionList)
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    semester_id: Optional[int] = Query(None),
    group_id: Optional[int] = Query(None),
    session_type: Optional[SessionType] = Query(None, description="Filter by session type (on_site, hybrid, virtual)"),
    # 🎓 NEW: Specialization filtering parameters
    specialization_filter: bool = Query(True, description="Filter by user's specialization"),
    include_mixed: bool = Query(True, description="Include mixed specialization sessions")
) -> Any:
    """
    List sessions with pagination and filtering
    For students: Show sessions from all current active semesters (based on date range)
    For admin/instructor: Show all sessions or filtered by semester_id

    Multi-semester support: When multiple semesters run concurrently (e.g., different
    tracks of Fall 2025), students will see sessions from all active semesters.
    This ensures visibility when users enroll in second semester or concurrent programs.
    """
    query = db.query(SessionTypel)

    # Apply role-based semester filtering
    if current_user.role == UserRole.STUDENT:
        # 🌐 CRITICAL: Cross-semester logic for Mbappé (LFA Testing)
        if current_user.email == "mbappe@lfa.com":
            # Mbappé gets access to ALL sessions across ALL semesters
            print(f"🌐 Cross-semester access granted for {current_user.name} (LFA Testing)")
            # No semester restriction for Mbappé - only apply semester_id filter if explicitly requested
            if semester_id:
                query = query.filter(SessionTypel.semester_id == semester_id)
                print(f"🎯 Mbappé filtering by specific semester: {semester_id}")
            else:
                print("🌐 Mbappé accessing ALL sessions across ALL semesters")
        else:
            # Regular students see sessions from all current active semesters with intelligent filtering
            if not semester_id:
                # Get all current active semesters (including parallel tracks)
                today = date.today()

                current_semesters = db.query(Semester).filter(
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
                    recent_semesters = db.query(Semester).filter(
                        Semester.is_active == True
                    ).order_by(Semester.id.desc()).limit(3).all()
                    if recent_semesters:
                        semester_ids = [s.id for s in recent_semesters]
                        query = query.filter(SessionTypel.semester_id.in_(semester_ids))
                        print(f"Fallback: Student seeing sessions from {len(recent_semesters)} recent semesters")
            else:
                # Allow filtering by specific semester for students
                query = query.filter(SessionTypel.semester_id == semester_id)
    elif current_user.role == UserRole.ADMIN:
        # Admin sees all sessions
        if semester_id:
            query = query.filter(SessionTypel.semester_id == semester_id)

    elif current_user.role == UserRole.INSTRUCTOR:
        # Instructor sees sessions from semesters where:
        # 1. They are assigned as master instructor (ACCEPTED)
        # 2. They have a PENDING assignment request
        from .....models.instructor_assignment import InstructorAssignmentRequest, AssignmentRequestStatus

        # Subquery for PENDING request semester IDs
        pending_semester_ids = db.query(InstructorAssignmentRequest.semester_id).filter(
            InstructorAssignmentRequest.instructor_id == current_user.id,
            InstructorAssignmentRequest.status == AssignmentRequestStatus.PENDING
        ).subquery()

        # Join with Semester and filter
        query = query.join(Semester, SessionTypel.semester_id == Semester.id)
        query = query.filter(
            or_(
                Semester.master_instructor_id == current_user.id,  # ACCEPTED
                Semester.id.in_(pending_semester_ids)              # PENDING
            )
        )

        # Optional: semester_id filter still works
        if semester_id:
            query = query.filter(SessionTypel.semester_id == semester_id)

    # 🎓 NEW: Apply specialization filtering (CRITICAL: Preserves Mbappé logic)
    # FIX: Only apply to STUDENTS with specialization - skip for admin/instructor
    if specialization_filter and current_user.role == UserRole.STUDENT and hasattr(current_user, 'has_specialization') and current_user.has_specialization:
        # Only apply specialization filtering to students who have a specialization
        # ⚠️ CRITICAL: This preserves Mbappé cross-semester access since he's already handled above

        specialization_conditions = []

        # Sessions with no specific target (accessible to all)
        specialization_conditions.append(SessionTypel.target_specialization.is_(None))

        # Sessions matching user's specialization
        if current_user.specialization:
            specialization_conditions.append(SessionTypel.target_specialization == current_user.specialization)

        # Mixed specialization sessions (if include_mixed is True)
        if include_mixed:
            specialization_conditions.append(SessionTypel.mixed_specialization == True)

        query = query.filter(or_(*specialization_conditions))

        if current_user.specialization:
            print(f"🎓 Specialization filtering applied for {current_user.name}: {current_user.specialization.value}")

    # Apply other filters
    if group_id:
        query = query.filter(SessionTypel.group_id == group_id)
    if session_type:
        query = query.filter(SessionTypel.session_type == session_type)

    # Get total count
    total = query.count()

    # Apply pagination with ordering (future sessions first, then by start date)
    # Get current time in UTC and convert to naive for DB comparison
    # All datetime objects in DB are stored as naive UTC
    now_utc = datetime.now(timezone.utc)
    now_naive_utc = now_utc.replace(tzinfo=None)

    offset = (page - 1) * size

    # Apply intelligent filtering for students, standard ordering for others
    if current_user.role == UserRole.STUDENT:
        # INTERNSHIP users use target_specialization filtering only (already applied above)
        # Other specializations use SessionFilterService for keyword-based filtering
        if current_user.specialization == SpecializationType.INTERNSHIP:
            # INTERNSHIP users: Use simple ordering, target_specialization filter already applied
            sessions = query.order_by(
                (SessionTypel.date_start > now_naive_utc).desc(),  # Future sessions first
                SessionTypel.date_start.asc()                      # Then by start time
            ).offset(offset).limit(size).all()
        else:
            # Other specializations: Use SessionFilterService for intelligent filtering
            filter_service = SessionFilterService(db)
            # Get ordered query
            ordered_query = query.order_by(
                (SessionTypel.date_start > now_naive_utc).desc(),  # Future sessions first
                SessionTypel.date_start.asc()                      # Then by start time (earliest future first)
            )
            # Apply intelligent filtering with pagination consideration
            filtered_sessions = filter_service.get_relevant_sessions_for_user(
                current_user,
                ordered_query,
                limit=size * 2  # Get more sessions to ensure enough after filtering
            )
            # Apply manual pagination to filtered results
            sessions = filtered_sessions[offset:offset + size]
    else:
        # Standard ordering and pagination for admin/instructor users
        sessions = query.order_by(
            (SessionTypel.date_start > now_naive_utc).desc(),  # Future sessions first
            SessionTypel.date_start.asc()                      # Then by start time (earliest future first)
        ).offset(offset).limit(size).all()

    # 🚀 PERFORMANCE OPTIMIZATION: Pre-fetch all stats with JOIN queries (eliminates N+1 problem)
    session_ids = [s.id for s in sessions]

    # Fetch booking stats in a single query using GROUP BY
    booking_stats_query = db.query(
        Booking.session_id,
        func.count(Booking.id).label('total_bookings'),
        func.sum(case((Booking.status == BookingStatus.CONFIRMED, 1), else_=0)).label('confirmed'),
        func.sum(case((Booking.status == BookingStatus.WAITLISTED, 1), else_=0)).label('waitlisted')
    ).filter(Booking.session_id.in_(session_ids)).group_by(Booking.session_id).all()

    # Create lookup dict for O(1) access
    booking_stats_dict = {
        stat.session_id: {
            'total': stat.total_bookings,
            'confirmed': stat.confirmed,
            'waitlisted': stat.waitlisted
        } for stat in booking_stats_query
    }

    # Fetch attendance stats in a single query
    attendance_stats_query = db.query(
        Attendance.session_id,
        func.count(Attendance.id).label('count')
    ).filter(Attendance.session_id.in_(session_ids)).group_by(Attendance.session_id).all()

    attendance_stats_dict = {stat.session_id: stat.count for stat in attendance_stats_query}

    # Fetch rating stats in a single query
    rating_stats_query = db.query(
        Feedback.session_id,
        func.avg(Feedback.rating).label('avg_rating')
    ).filter(Feedback.session_id.in_(session_ids)).group_by(Feedback.session_id).all()

    rating_stats_dict = {stat.session_id: float(stat.avg_rating) if stat.avg_rating else None for stat in rating_stats_query}

    # Add statistics
    session_stats = []
    for session in sessions:
        # Get stats from pre-fetched dicts (O(1) lookup)
        booking_stats = booking_stats_dict.get(session.id, {'total': 0, 'confirmed': 0, 'waitlisted': 0})
        booking_count = booking_stats['total']
        confirmed_bookings = booking_stats['confirmed']
        waitlist_count = booking_stats['waitlisted']
        attendance_count = attendance_stats_dict.get(session.id, 0)
        avg_rating = rating_stats_dict.get(session.id, None)

        # FIX: Build session data explicitly to handle NULL values
        session_data = {
            "id": session.id,
            "title": session.title,
            "description": session.description or "",
            "date_start": session.date_start,
            "date_end": session.date_end,
            "session_type": session.session_type,
            "capacity": session.capacity if session.capacity is not None else 0,  # FIX: Handle NULL
            "credit_cost": session.credit_cost if session.credit_cost is not None else 1,  # FIX: Include credit_cost from database
            "location": session.location,
            "meeting_link": session.meeting_link,
            "sport_type": session.sport_type,
            "level": session.level,
            "instructor_name": session.instructor_name,
            "semester_id": session.semester_id,
            "group_id": session.group_id,
            "instructor_id": session.instructor_id,
            "created_at": session.created_at or session.date_start,  # FIX: Handle NULL created_at
            "updated_at": session.updated_at,
            "target_specialization": session.target_specialization,
            "mixed_specialization": session.mixed_specialization if hasattr(session, 'mixed_specialization') else False,
            "is_tournament_game": session.is_tournament_game if hasattr(session, 'is_tournament_game') else False,  # 🏆 Tournament game flag
            "game_type": session.game_type if hasattr(session, 'game_type') else None,  # 🏆 Tournament game type
            "semester": session.semester,
            "group": session.group,
            "instructor": session.instructor,
            "booking_count": booking_count,
            "confirmed_bookings": confirmed_bookings,
            "current_bookings": confirmed_bookings,
            "waitlist_count": waitlist_count,
            "attendance_count": attendance_count,
            "average_rating": float(avg_rating) if avg_rating else None
        }

        session_stats.append(SessionWithStats(**session_data))

    return SessionList(
        sessions=session_stats,
        total=total,
        page=page,
        size=size
    )


@router.get("/recommendations")
def get_session_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get personalized session recommendations and filtering summary for current user
    """
    filter_service = SessionFilterService(db)
    recommendations_summary = filter_service.get_session_recommendations_summary(current_user)

    return {
        "user_profile": recommendations_summary,
        "message": "Session filtering is personalized based on your projects and interests"
    }


@router.get("/{session_id}/bookings", response_model=BookingList)
def get_session_bookings(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100)
) -> Any:
    """
    Get bookings for a session (Admin/Instructor only)
    """
    # Check if session exists
    session = db.query(SessionTypel).filter(SessionTypel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    query = db.query(Booking).filter(Booking.session_id == session_id)

    # Get total count
    total = query.count()

    # OPTIMIZED: Eager load relationships to avoid N+1 query pattern
    query = query.options(
        joinedload(Booking.user),
        joinedload(Booking.session)
    )

    # Apply pagination
    offset = (page - 1) * size
    bookings = query.offset(offset).limit(size).all()

    # Convert to response schema
    booking_responses = []
    for booking in bookings:
        # Use model_dump() to properly serialize the Pydantic model with relationships
        booking_data = {
            **{k: v for k, v in booking.__dict__.items() if not k.startswith('_')},
            'user': booking.user,
            'session': booking.session
        }
        booking_responses.append(BookingWithRelations(**booking_data))

    return BookingList(
        bookings=booking_responses,
        total=total,
        page=page,
        size=size
    )


@router.get("/instructor/my")
def get_instructor_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100)
) -> Any:
    """
    Get sessions for current instructor
    """
    # Verify user is instructor
    if current_user.role.value != 'instructor':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Instructor role required."
        )

    # Query sessions assigned to this instructor
    query = db.query(SessionTypel).filter(SessionTypel.instructor_id == current_user.id).order_by(SessionTypel.date_start.desc())

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * size
    sessions = query.offset(offset).limit(size).all()

    # Return simple response for now
    session_list = []
    for session in sessions:
        # Get booking count
        booking_count = db.query(func.count(Booking.id)).filter(
            and_(
                Booking.session_id == session.id,
                Booking.status == BookingStatus.CONFIRMED
            )
        ).scalar() or 0

        session_dict = {
            'id': session.id,
            'title': session.title,
            'description': session.description,
            'date_start': session.date_start.isoformat(),
            'date_end': session.date_end.isoformat(),
            'location': session.location,
            'capacity': session.capacity,
            'instructor_id': session.instructor_id,
            'level': session.level,
            'sport_type': session.sport_type,
            'current_bookings': booking_count,
            'created_at': session.created_at.isoformat(),
        }
        session_list.append(session_dict)

    return {
        'sessions': session_list,
        'total': total,
        'page': page,
        'size': size
    }


@router.get("/calendar")
def get_calendar_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """
    Get all sessions formatted for FullCalendar
    Returns simplified session data for calendar display
    """
    # Get all sessions
    sessions = db.query(SessionTypel).order_by(SessionTypel.date_start.asc()).all()

    # Format for FullCalendar
    calendar_events = []
    for session in sessions:
        calendar_events.append({
            'id': session.id,
            'title': session.title,
            'description': session.description,
            'date_start': session.date_start.isoformat() if session.date_start else None,
            'date_end': session.date_end.isoformat() if session.date_end else None,
            'session_type': session.session_type.value if session.session_type else 'on_site',
            'location': session.location,
            'capacity': session.capacity
        })

    return calendar_events
