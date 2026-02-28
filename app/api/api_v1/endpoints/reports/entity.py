"""
Entity-specific report endpoints (semester, user)
"""
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from .....database import get_db
from .....models.user import User

from sqlalchemy import func, and_
from pydantic import BaseModel

from .....dependencies import get_current_admin_user
from .....models.semester import Semester
from .....models.session import Session as SessionTypel
from .....models.booking import Booking, BookingStatus
from .....models.attendance import Attendance, AttendanceStatus
from .....models.feedback import Feedback

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



@router.get("/semester/{semester_id}")
def get_semester_report(
    semester_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Get comprehensive semester report (Admin only)
    """
    # Check if semester exists
    semester = db.query(Semester).filter(Semester.id == semester_id).first()
    if not semester:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Semester not found"
        )
    
    # Basic statistics
    total_sessions = db.query(func.count(SessionTypel.id)).filter(SessionTypel.semester_id == semester_id).scalar() or 0
    total_bookings = db.query(func.count(Booking.id)).join(SessionTypel).filter(SessionTypel.semester_id == semester_id).scalar() or 0
    confirmed_bookings = db.query(func.count(Booking.id)).join(SessionTypel).filter(
        and_(SessionTypel.semester_id == semester_id, Booking.status == BookingStatus.CONFIRMED)
    ).scalar() or 0
    
    # Attendance statistics
    total_attendance = db.query(func.count(Attendance.id)).join(SessionTypel).filter(SessionTypel.semester_id == semester_id).scalar() or 0
    present_attendance = db.query(func.count(Attendance.id)).join(SessionTypel).filter(
        and_(SessionTypel.semester_id == semester_id, Attendance.status == AttendanceStatus.present)
    ).scalar() or 0
    
    # Feedback statistics
    total_feedback = db.query(func.count(Feedback.id)).join(SessionTypel).filter(SessionTypel.semester_id == semester_id).scalar() or 0
    average_rating = db.query(func.avg(Feedback.rating)).join(SessionTypel).filter(SessionTypel.semester_id == semester_id).scalar()
    
    # User participation
    active_students = db.query(func.count(func.distinct(Booking.user_id))).join(SessionTypel).filter(SessionTypel.semester_id == semester_id).scalar() or 0
    
    # Session mode breakdown
    session_modes = db.query(
        SessionTypel.session_type,
        func.count(SessionTypel.id)
    ).filter(SessionTypel.semester_id == semester_id).group_by(SessionTypel.session_type).all()

    mode_breakdown = {mode: 0 for mode in SessionTypel.__table__.columns.session_type.type.enums}
    for mode, count in session_modes:
        mode_breakdown[mode.value] = count
    
    # Monthly breakdown
    monthly_stats = db.query(
        func.extract('month', SessionTypel.date_start).label('month'),
        func.count(SessionTypel.id).label('sessions'),
        func.count(func.distinct(Booking.id)).label('bookings')
    ).outerjoin(Booking).filter(SessionTypel.semester_id == semester_id).group_by('month').all()
    
    monthly_breakdown = []
    for month, sessions, bookings in monthly_stats:
        monthly_breakdown.append({
            "month": int(month) if month else 0,
            "sessions": sessions or 0,
            "bookings": bookings or 0
        })
    
    return {
        "semester": {
            "id": semester.id,
            "code": semester.code,
            "name": semester.name,
            "start_date": semester.start_date,
            "end_date": semester.end_date
        },
        "overview": {
            "total_sessions": total_sessions,
            "total_bookings": total_bookings,
            "confirmed_bookings": confirmed_bookings,
            "booking_rate": round(confirmed_bookings / max(total_bookings, 1) * 100, 2),
            "total_attendance": total_attendance,
            "present_attendance": present_attendance,
            "attendance_rate": round(present_attendance / max(total_attendance, 1) * 100, 2),
            "total_feedback": total_feedback,
            "average_rating": round(float(average_rating), 2) if average_rating else 0,
            "active_students": active_students
        },
        "session_modes": mode_breakdown,
        "monthly_breakdown": monthly_breakdown
    }


@router.get("/user/{user_id}")
def get_user_report(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Get user participation report (Admin only)
    """
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Booking statistics
    total_bookings = db.query(func.count(Booking.id)).filter(Booking.user_id == user_id).scalar() or 0
    confirmed_bookings = db.query(func.count(Booking.id)).filter(
        and_(Booking.user_id == user_id, Booking.status == BookingStatus.CONFIRMED)
    ).scalar() or 0
    cancelled_bookings = db.query(func.count(Booking.id)).filter(
        and_(Booking.user_id == user_id, Booking.status == BookingStatus.CANCELLED)
    ).scalar() or 0
    
    # Attendance statistics
    total_sessions_attended = db.query(func.count(Attendance.id)).filter(Attendance.user_id == user_id).scalar() or 0
    present_sessions = db.query(func.count(Attendance.id)).filter(
        and_(Attendance.user_id == user_id, Attendance.status == AttendanceStatus.present)
    ).scalar() or 0
    
    # Feedback statistics
    feedback_given = db.query(func.count(Feedback.id)).filter(Feedback.user_id == user_id).scalar() or 0
    average_rating_given = db.query(func.avg(Feedback.rating)).filter(Feedback.user_id == user_id).scalar()
    
    # Semester breakdown
    semester_stats = db.query(
        Semester.id,
        Semester.code,
        Semester.name,
        func.count(func.distinct(Booking.id)).label('bookings'),
        func.count(func.distinct(Attendance.id)).label('attendances')
    ).outerjoin(
        SessionTypel, SessionTypel.semester_id == Semester.id
    ).outerjoin(
        Booking, and_(Booking.session_id == SessionTypel.id, Booking.user_id == user_id)
    ).outerjoin(
        Attendance, and_(Attendance.session_id == SessionTypel.id, Attendance.user_id == user_id)
    ).group_by(Semester.id, Semester.code, Semester.name).all()
    
    semester_breakdown = []
    for semester_id, code, name, bookings, attendances in semester_stats:
        semester_breakdown.append({
            "semester_id": semester_id,
            "semester_code": code,
            "semester_name": name,
            "bookings": bookings or 0,
            "attendances": attendances or 0
        })
    
    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role.value
        },
        "booking_statistics": {
            "total_bookings": total_bookings,
            "confirmed_bookings": confirmed_bookings,
            "cancelled_bookings": cancelled_bookings,
            "confirmation_rate": round(confirmed_bookings / max(total_bookings, 1) * 100, 2)
        },
        "attendance_statistics": {
            "total_sessions_attended": total_sessions_attended,
            "present_sessions": present_sessions,
            "attendance_rate": round(present_sessions / max(total_sessions_attended, 1) * 100, 2)
        },
        "feedback_statistics": {
            "feedback_given": feedback_given,
            "average_rating_given": round(float(average_rating_given), 2) if average_rating_given else 0
        },
        "semester_breakdown": semester_breakdown
    }


