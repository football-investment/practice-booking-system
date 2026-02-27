"""
Data export and system statistics endpoints
"""
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from datetime import datetime
import csv

from .....database import get_db
from .....models.user import User

from fastapi import Query
from sqlalchemy import func
from pydantic import BaseModel

from .....dependencies import get_current_admin_user
from .....models.semester import Semester
from .....models.session import Session as SessionTypel
from .....models.booking import Booking, BookingStatus
from .....models.attendance import Attendance, AttendanceStatus
from .....models.feedback import Feedback
from .....models.group import Group

router = APIRouter()

# Pydantic models for request/response
class ReportConfig(BaseModel):
    report_type: str
    filters: Optional[Dict[str, Any]] = {}
    format: Optional[str] = "json"

class ReportListItem(BaseModel):
    id: int
    name: str
    type: str
    description: str
    created_at: datetime

class ReportHistoryItem(BaseModel):
    id: int
    report_type: str
    created_at: datetime
    status: str
    file_path: Optional[str] = None



@router.get("/export/sessions")
def export_sessions_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    semester_id: int = Query(...)
) -> Response:
    """
    Export sessions data as CSV (Admin only)
    """
    # Check if semester exists
    semester = db.query(Semester).filter(Semester.id == semester_id).first()
    if not semester:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Semester not found"
        )
    
    # Get sessions with statistics
    sessions = db.query(SessionTypel).filter(SessionTypel.semester_id == semester_id).all()

    # OPTIMIZED: Batch fetch all statistics using GROUP BY (reduces 5N+1 queries to 4 queries)
    session_ids = [s.id for s in sessions]

    # Query 1: Booking statistics by session
    booking_stats = db.query(
        Booking.session_id,
        func.count(Booking.id).label('total_bookings'),
        func.sum(func.case((Booking.status == BookingStatus.CONFIRMED, 1), else_=0)).label('confirmed_bookings'),
        func.sum(func.case((Booking.status == BookingStatus.WAITLISTED, 1), else_=0)).label('waitlisted')
    ).filter(Booking.session_id.in_(session_ids)).group_by(Booking.session_id).all()

    booking_stats_map = {
        row.session_id: {
            'total_bookings': row.total_bookings or 0,
            'confirmed_bookings': row.confirmed_bookings or 0,
            'waitlisted': row.waitlisted or 0
        } for row in booking_stats
    }

    # Query 2: Attendance statistics by session
    attendance_stats = db.query(
        Attendance.session_id,
        func.count(Attendance.id).label('total_attendance'),
        func.sum(func.case((Attendance.status == AttendanceStatus.present, 1), else_=0)).label('present_attendance')
    ).filter(Attendance.session_id.in_(session_ids)).group_by(Attendance.session_id).all()

    attendance_stats_map = {
        row.session_id: {
            'present_attendance': row.present_attendance or 0
        } for row in attendance_stats
    }

    # Query 3: Feedback statistics by session
    feedback_stats = db.query(
        Feedback.session_id,
        func.avg(Feedback.rating).label('avg_rating')
    ).filter(Feedback.session_id.in_(session_ids)).group_by(Feedback.session_id).all()

    feedback_stats_map = {
        row.session_id: round(float(row.avg_rating), 2) if row.avg_rating else 0
        for row in feedback_stats
    }

    # Create CSV content
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'Session ID', 'Title', 'Date Start', 'Date End', 'Mode', 'Capacity',
        'Location', 'Meeting Link', 'Group', 'Instructor', 'Total Bookings',
        'Confirmed Bookings', 'Waitlisted', 'Present Attendance', 'Average Rating'
    ])

    # Write data (no queries in loop - all data pre-fetched)
    for session in sessions:
        booking_data = booking_stats_map.get(session.id, {'total_bookings': 0, 'confirmed_bookings': 0, 'waitlisted': 0})
        attendance_data = attendance_stats_map.get(session.id, {'present_attendance': 0})
        avg_rating = feedback_stats_map.get(session.id, 0)

        writer.writerow([
            session.id,
            session.title,
            session.date_start,
            session.date_end,
            session.session_type.value,
            session.capacity,
            session.location or '',
            session.meeting_link or '',
            session.group.name if session.group else '',
            session.instructor.name if session.instructor else '',
            booking_data['total_bookings'],
            booking_data['confirmed_bookings'],
            booking_data['waitlisted'],
            attendance_data['present_attendance'],
            avg_rating
        ])
    
    # Prepare response
    csv_content = output.getvalue()
    output.close()
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=sessions_{semester.code}_{semester_id}.csv"}
    )


@router.get("/system-stats")
def get_system_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Get system-wide statistics (Admin only)
    """
    # Basic counts
    total_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
    total_semesters = db.query(func.count(Semester.id)).scalar() or 0
    active_semesters = db.query(func.count(Semester.id)).filter(Semester.is_active == True).scalar() or 0
    total_sessions = db.query(func.count(SessionTypel.id)).scalar() or 0
    total_bookings = db.query(func.count(Booking.id)).scalar() or 0
    total_groups = db.query(func.count(Group.id)).scalar() or 0
    
    # User role breakdown
    user_roles = db.query(
        User.role,
        func.count(User.id)
    ).filter(User.is_active == True).group_by(User.role).all()
    
    role_breakdown = {}
    for role, count in user_roles:
        role_breakdown[role.value] = count
    
    # Booking status breakdown
    booking_statuses = db.query(
        Booking.status,
        func.count(Booking.id)
    ).group_by(Booking.status).all()
    
    booking_breakdown = {}
    for status, count in booking_statuses:
        booking_breakdown[status.value] = count
    
    # Session mode breakdown
    session_modes = db.query(
        SessionTypel.session_type,
        func.count(SessionTypel.id)
    ).group_by(SessionTypel.session_type).all()
    
    mode_breakdown = {}
    for mode, count in session_modes:
        mode_breakdown[mode.value] = count
    
    # Calculate utilization rates
    confirmed_bookings = db.query(func.count(Booking.id)).filter(
        Booking.status == BookingStatus.CONFIRMED
    ).scalar() or 0
    
    total_capacity = db.query(func.sum(SessionTypel.capacity)).scalar() or 0
    
    # Attendance statistics
    total_attendances = db.query(func.count(Attendance.id)).scalar() or 0
    present_attendances = db.query(func.count(Attendance.id)).filter(
        Attendance.status == AttendanceStatus.present
    ).scalar() or 0
    
    # Feedback statistics
    total_feedback = db.query(func.count(Feedback.id)).scalar() or 0
    average_rating = db.query(func.avg(Feedback.rating)).scalar()
    
    return {
        "system_overview": {
            "total_users": total_users,
            "total_semesters": total_semesters,
            "active_semesters": active_semesters,
            "total_sessions": total_sessions,
            "total_bookings": total_bookings,
            "total_groups": total_groups,
            "confirmed_bookings": confirmed_bookings,
            "total_capacity": total_capacity,
            "capacity_utilization": round(confirmed_bookings / max(total_capacity, 1) * 100, 2),
            "total_attendances": total_attendances,
            "present_attendances": present_attendances,
            "attendance_rate": round(present_attendances / max(total_attendances, 1) * 100, 2),
            "total_feedback": total_feedback,
            "average_rating": round(float(average_rating), 2) if average_rating else 0
        },
        "user_breakdown": role_breakdown,
        "booking_breakdown": booking_breakdown,
        "session_mode_breakdown": mode_breakdown
    }