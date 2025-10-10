from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from ....services.session_filter_service import SessionFilterService

from ....database import get_db
from ....dependencies import get_current_user, get_current_admin_or_instructor_user
from ....models.user import User
from ....models.session import Session as SessionModel, SessionMode
from ....models.booking import Booking, BookingStatus
from ....models.attendance import Attendance
from ....models.feedback import Feedback
from ....schemas.session import (
    Session as SessionSchema, SessionCreate, SessionUpdate,
    SessionWithStats, SessionList
)
from ....schemas.booking import (
    BookingWithRelations, BookingList
)

router = APIRouter()


@router.post("/", response_model=SessionSchema)
def create_session(
    session_data: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_instructor_user)
) -> Any:
    """
    Create new session (Admin/Instructor only)
    """
    session = SessionModel(**session_data.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session


@router.get("/", response_model=SessionList)
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    semester_id: Optional[int] = Query(None),
    group_id: Optional[int] = Query(None),
    mode: Optional[SessionMode] = Query(None),
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
    query = db.query(SessionModel)
    
    # Apply role-based semester filtering
    from ....models.semester import Semester
    from ....models.user import UserRole
    
    if current_user.role == UserRole.STUDENT:
        # 🌐 CRITICAL: Cross-semester logic for Mbappé (LFA Testing)
        if current_user.email == "mbappe@lfa.com":
            # Mbappé gets access to ALL sessions across ALL semesters
            print(f"🌐 Cross-semester access granted for {current_user.name} (LFA Testing)")
            # No semester restriction for Mbappé - only apply semester_id filter if explicitly requested
            if semester_id:
                query = query.filter(SessionModel.semester_id == semester_id)
                print(f"🎯 Mbappé filtering by specific semester: {semester_id}")
            else:
                print("🌐 Mbappé accessing ALL sessions across ALL semesters")
        else:
            # Regular students see sessions from all current active semesters with intelligent filtering
            if not semester_id:
                # Get all current active semesters (including parallel tracks)
                from datetime import date
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
                    query = query.filter(SessionModel.semester_id.in_(semester_ids))
                    print(f"Student seeing sessions from {len(current_semesters)} current semesters: {[s.name for s in current_semesters]}")
                else:
                    # Fallback: if no current semesters by date, show most recent semesters
                    recent_semesters = db.query(Semester).filter(
                        Semester.is_active == True
                    ).order_by(Semester.id.desc()).limit(3).all()
                    if recent_semesters:
                        semester_ids = [s.id for s in recent_semesters]
                        query = query.filter(SessionModel.semester_id.in_(semester_ids))
                        print(f"Fallback: Student seeing sessions from {len(recent_semesters)} recent semesters")
            else:
                # Allow filtering by specific semester for students
                query = query.filter(SessionModel.semester_id == semester_id)
    else:
        # Admin/Instructor can see all sessions or filter by semester
        if semester_id:
            query = query.filter(SessionModel.semester_id == semester_id)
    
    # 🎓 NEW: Apply specialization filtering (CRITICAL: Preserves Mbappé logic)
    if specialization_filter and current_user.role == UserRole.STUDENT and current_user.has_specialization:
        # Only apply specialization filtering to students who have a specialization
        # ⚠️ CRITICAL: This preserves Mbappé cross-semester access since he's already handled above
        
        specialization_conditions = []
        
        # Sessions with no specific target (accessible to all)
        specialization_conditions.append(SessionModel.target_specialization.is_(None))
        
        # Sessions matching user's specialization
        specialization_conditions.append(SessionModel.target_specialization == current_user.specialization)
        
        # Mixed specialization sessions (if include_mixed is True)
        if include_mixed:
            specialization_conditions.append(SessionModel.mixed_specialization == True)
        
        query = query.filter(or_(*specialization_conditions))
        
        print(f"🎓 Specialization filtering applied for {current_user.name}: {current_user.specialization.value}")
    
    # Apply other filters
    if group_id:
        query = query.filter(SessionModel.group_id == group_id)
    if mode:
        query = query.filter(SessionModel.mode == mode)
    
    # Get total count
    total = query.count()
    
    # Apply pagination with ordering (future sessions first, then by start date)
    from datetime import datetime, timezone
    
    # Get current time in UTC and convert to naive for DB comparison
    # All datetime objects in DB are stored as naive UTC
    now_utc = datetime.now(timezone.utc)
    now_naive_utc = now_utc.replace(tzinfo=None)
    
    offset = (page - 1) * size
    
    # Apply intelligent filtering for students, standard ordering for others
    if current_user.role == UserRole.STUDENT:
        # Use SessionFilterService for intelligent session filtering
        filter_service = SessionFilterService(db)
        # Get ordered query
        ordered_query = query.order_by(
            (SessionModel.date_start > now_naive_utc).desc(),  # Future sessions first
            SessionModel.date_start.asc()                      # Then by start time (earliest future first)
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
            (SessionModel.date_start > now_naive_utc).desc(),  # Future sessions first
            SessionModel.date_start.asc()                      # Then by start time (earliest future first)
        ).offset(offset).limit(size).all()
    
    # Add statistics
    session_stats = []
    for session in sessions:
        booking_count = db.query(func.count(Booking.id)).filter(Booking.session_id == session.id).scalar() or 0
        confirmed_bookings = db.query(func.count(Booking.id)).filter(
            and_(Booking.session_id == session.id, Booking.status == BookingStatus.CONFIRMED)
        ).scalar() or 0
        waitlist_count = db.query(func.count(Booking.id)).filter(
            and_(Booking.session_id == session.id, Booking.status == BookingStatus.WAITLISTED)
        ).scalar() or 0
        attendance_count = db.query(func.count(Attendance.id)).filter(Attendance.session_id == session.id).scalar() or 0
        avg_rating = db.query(func.avg(Feedback.rating)).filter(Feedback.session_id == session.id).scalar()
        
        session_stats.append(SessionWithStats(
            **session.__dict__,
            semester=session.semester,
            group=session.group,
            instructor=session.instructor,
            booking_count=booking_count,
            confirmed_bookings=confirmed_bookings,
            current_bookings=confirmed_bookings,  # FIXED: Map confirmed_bookings to current_bookings for frontend
            waitlist_count=waitlist_count,
            attendance_count=attendance_count,
            average_rating=float(avg_rating) if avg_rating else None
        ))
    
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
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    query = db.query(Booking).filter(Booking.session_id == session_id)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    bookings = query.offset(offset).limit(size).all()
    
    # Convert to response schema
    booking_responses = []
    for booking in bookings:
        booking_responses.append(BookingWithRelations(
            **booking.__dict__,
            user=booking.user,
            session=booking.session
        ))
    
    return BookingList(
        bookings=booking_responses,
        total=total,
        page=page,
        size=size
    )


@router.get("/{session_id}", response_model=SessionWithStats)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get session by ID with statistics
    """
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Calculate statistics
    booking_count = db.query(func.count(Booking.id)).filter(Booking.session_id == session.id).scalar() or 0
    confirmed_bookings = db.query(func.count(Booking.id)).filter(
        and_(Booking.session_id == session.id, Booking.status == BookingStatus.CONFIRMED)
    ).scalar() or 0
    waitlist_count = db.query(func.count(Booking.id)).filter(
        and_(Booking.session_id == session.id, Booking.status == BookingStatus.WAITLISTED)
    ).scalar() or 0
    attendance_count = db.query(func.count(Attendance.id)).filter(Attendance.session_id == session.id).scalar() or 0
    avg_rating = db.query(func.avg(Feedback.rating)).filter(Feedback.session_id == session.id).scalar()
    
    return SessionWithStats(
        **session.__dict__,
        semester=session.semester,
        group=session.group,
        instructor=session.instructor,
        booking_count=booking_count,
        confirmed_bookings=confirmed_bookings,
        current_bookings=confirmed_bookings,  # FIXED: Map confirmed_bookings to current_bookings for frontend
        waitlist_count=waitlist_count,
        attendance_count=attendance_count,
        average_rating=float(avg_rating) if avg_rating else None
    )


@router.patch("/{session_id}", response_model=SessionSchema)
def update_session(
    session_id: int,
    session_update: SessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_instructor_user)
) -> Any:
    """
    Update session (Admin/Instructor only)
    """
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Update fields
    update_data = session_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(session, field, value)
    
    db.commit()
    db.refresh(session)
    
    return session


@router.delete("/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_instructor_user)
) -> Any:
    """
    Delete session (Admin/Instructor only)
    """
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check if there are any bookings for this session
    booking_count = db.query(func.count(Booking.id)).filter(Booking.session_id == session_id).scalar()
    if booking_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete session with existing bookings"
        )
    
    db.delete(session)
    db.commit()
    
    return {"message": "Session deleted successfully"}


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
    query = db.query(SessionModel).filter(SessionModel.instructor_id == current_user.id).order_by(SessionModel.date_start.desc())
    
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