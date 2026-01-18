"""
Session query operations
List, filter, recommendations, bookings, instructor sessions, calendar
"""
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from datetime import datetime, timezone

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User, UserRole
from .....models.session import Session as SessionTypel, SessionType
from .....models.booking import Booking, BookingStatus
from .....models.specialization import SpecializationType
from .....schemas.session import SessionList
from .....schemas.booking import BookingWithRelations, BookingList
from .....services.session_filter_service import SessionFilterService
from .....services.session_stats_aggregator import SessionStatsAggregator
from .....services.role_semester_filter_service import RoleSemesterFilterService
from .....services.session_response_builder import SessionResponseBuilder

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
    List sessions with pagination, filtering, and statistics.

    Architecture:
        - RoleSemesterFilterService: Handles role-based semester filtering
        - SessionFilterService: Handles specialization filtering
        - SessionStatsAggregator: Bulk-fetches booking/attendance/rating stats
        - SessionResponseBuilder: Constructs response with NULL handling

    Role-Based Logic:
        - Students: Current active semesters (multi-semester support)
        - Admin: All sessions (optionally filtered by semester_id)
        - Instructor: Semesters where assigned or PENDING requests

    Specialization:
        - INTERNSHIP: Simple target_specialization filtering
        - Other specializations: Intelligent keyword-based filtering

    Performance:
        - Query count: 5-7 (role-dependent)
        - N+1 problem eliminated: Bulk GROUP BY queries for stats
        - Response: SessionList with pre-aggregated statistics
    """
    # 1. Initialize query
    query = db.query(SessionTypel)

    # 2. Apply role-based semester filtering
    role_filter_service = RoleSemesterFilterService(db)
    query = role_filter_service.apply_role_semester_filter(query, current_user, semester_id)

    # 3. Apply specialization filtering
    if specialization_filter:
        filter_service = SessionFilterService(db)
        query = filter_service.apply_specialization_filter(query, current_user, include_mixed)

    # 4. Apply additional filters
    if group_id:
        query = query.filter(SessionTypel.group_id == group_id)
    if session_type:
        query = query.filter(SessionTypel.session_type == session_type)

    # 5. Get total count
    total = query.count()

    # 6. Pagination and ordering
    now_naive_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    offset = (page - 1) * size
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

    # 7. Fetch statistics (bulk queries, N+1 elimination)
    session_ids = [s.id for s in sessions]
    stats_aggregator = SessionStatsAggregator(db)
    stats = stats_aggregator.fetch_stats(session_ids)

    # 8. Build response
    response_builder = SessionResponseBuilder(db)
    return response_builder.build_response(sessions, stats, total, page, size)


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
