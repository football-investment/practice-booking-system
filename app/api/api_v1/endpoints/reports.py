from typing import Any, Dict, List, Optional
import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from pydantic import BaseModel

from ....database import get_db
from ....dependencies import get_current_admin_user
from ....models.user import User
from ....models.semester import Semester
from ....models.session import Session as SessionModel
from ....models.booking import Booking, BookingStatus
from ....models.attendance import Attendance, AttendanceStatus
from ....models.feedback import Feedback
from ....models.group import Group

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


@router.get("/")
def list_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100)
) -> Any:
    """
    List all available reports (Admin only)
    """
    # Static list of available report types
    reports = [
        {
            "id": 1,
            "name": "Semester Summary Report",
            "type": "semester",
            "description": "Comprehensive semester statistics and analytics",
            "created_at": datetime.now()
        },
        {
            "id": 2,
            "name": "User Activity Report",
            "type": "user",
            "description": "Individual user participation and attendance data",
            "created_at": datetime.now()
        },
        {
            "id": 3,
            "name": "Session Utilization Report",
            "type": "session",
            "description": "Session booking patterns and capacity utilization",
            "created_at": datetime.now()
        },
        {
            "id": 4,
            "name": "System Statistics Report",
            "type": "system",
            "description": "Overall system usage and health metrics",
            "created_at": datetime.now()
        },
        {
            "id": 5,
            "name": "Attendance Analytics Report",
            "type": "attendance",
            "description": "Attendance patterns and trends analysis",
            "created_at": datetime.now()
        }
    ]
    
    # Apply pagination
    start = (page - 1) * size
    end = start + size
    paginated_reports = reports[start:end]
    
    return {
        "reports": paginated_reports,
        "total": len(reports),
        "page": page,
        "size": size,
        "pages": (len(reports) + size - 1) // size
    }


@router.post("/custom")
def create_custom_report(
    report_config: ReportConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Create custom report (Admin only)
    """
    # Validate report type
    valid_types = ["semester", "user", "session", "system", "attendance", "booking", "feedback"]
    if report_config.report_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid report type. Must be one of: {', '.join(valid_types)}"
        )
    
    # Generate report based on type
    report_data = {}
    
    if report_config.report_type == "semester":
        # Get semester data with filters
        semesters = db.query(Semester).all()
        report_data = {
            "type": "semester",
            "data": [{"id": s.id, "code": s.code, "name": s.name} for s in semesters]
        }
    
    elif report_config.report_type == "user":
        # Get user data with filters
        users_query = db.query(User).filter(User.is_active == True)
        if "role" in report_config.filters:
            users_query = users_query.filter(User.role == report_config.filters["role"])
        users = users_query.all()
        report_data = {
            "type": "user",
            "data": [{"id": u.id, "name": u.name, "email": u.email, "role": u.role.value} for u in users]
        }
    
    elif report_config.report_type == "session":
        # Get session data with filters
        sessions_query = db.query(SessionModel)
        if "semester_id" in report_config.filters:
            sessions_query = sessions_query.filter(SessionModel.semester_id == report_config.filters["semester_id"])
        sessions = sessions_query.all()
        report_data = {
            "type": "session",
            "data": [{"id": s.id, "title": s.title, "date_start": str(s.date_start)} for s in sessions]
        }
    
    else:
        # Default system report
        total_users = db.query(func.count(User.id)).scalar() or 0
        total_sessions = db.query(func.count(SessionModel.id)).scalar() or 0
        total_bookings = db.query(func.count(Booking.id)).scalar() or 0
        
        report_data = {
            "type": "system",
            "data": {
                "total_users": total_users,
                "total_sessions": total_sessions,
                "total_bookings": total_bookings
            }
        }
    
    return {
        "report_id": f"{report_config.report_type}_{int(datetime.now().timestamp())}",
        "status": "generated",
        "created_at": datetime.now(),
        "report_type": report_config.report_type,
        "filters": report_config.filters,
        "data": report_data
    }


@router.get("/history")
def get_report_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100)
) -> Any:
    """
    Get report generation history (Admin only)
    """
    # Mock history data - in a real system, this would come from a reports table
    history = [
        {
            "id": 1,
            "report_type": "semester",
            "created_at": datetime.now().replace(hour=10, minute=30),
            "status": "completed",
            "file_path": "/reports/semester_2024_1.csv"
        },
        {
            "id": 2,
            "report_type": "user",
            "created_at": datetime.now().replace(hour=9, minute=15),
            "status": "completed",
            "file_path": "/reports/user_activity_2024.json"
        },
        {
            "id": 3,
            "report_type": "system",
            "created_at": datetime.now().replace(hour=8, minute=0),
            "status": "completed",
            "file_path": "/reports/system_stats_2024.pdf"
        }
    ]
    
    # Apply pagination
    start = (page - 1) * size
    end = start + size
    paginated_history = history[start:end]
    
    return {
        "history": paginated_history,
        "total": len(history),
        "page": page,
        "size": size,
        "pages": (len(history) + size - 1) // size
    }


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
    total_sessions = db.query(func.count(SessionModel.id)).filter(SessionModel.semester_id == semester_id).scalar() or 0
    total_bookings = db.query(func.count(Booking.id)).join(SessionModel).filter(SessionModel.semester_id == semester_id).scalar() or 0
    confirmed_bookings = db.query(func.count(Booking.id)).join(SessionModel).filter(
        and_(SessionModel.semester_id == semester_id, Booking.status == BookingStatus.CONFIRMED)
    ).scalar() or 0
    
    # Attendance statistics
    total_attendance = db.query(func.count(Attendance.id)).join(SessionModel).filter(SessionModel.semester_id == semester_id).scalar() or 0
    present_attendance = db.query(func.count(Attendance.id)).join(SessionModel).filter(
        and_(SessionModel.semester_id == semester_id, Attendance.status == AttendanceStatus.PRESENT)
    ).scalar() or 0
    
    # Feedback statistics
    total_feedback = db.query(func.count(Feedback.id)).join(SessionModel).filter(SessionModel.semester_id == semester_id).scalar() or 0
    average_rating = db.query(func.avg(Feedback.rating)).join(SessionModel).filter(SessionModel.semester_id == semester_id).scalar()
    
    # User participation
    active_students = db.query(func.count(func.distinct(Booking.user_id))).join(SessionModel).filter(SessionModel.semester_id == semester_id).scalar() or 0
    
    # Session mode breakdown
    session_modes = db.query(
        SessionModel.mode,
        func.count(SessionModel.id)
    ).filter(SessionModel.semester_id == semester_id).group_by(SessionModel.mode).all()
    
    mode_breakdown = {mode: 0 for mode in SessionModel.__table__.columns.mode.type.enums}
    for mode, count in session_modes:
        mode_breakdown[mode.value] = count
    
    # Monthly breakdown
    monthly_stats = db.query(
        func.extract('month', SessionModel.date_start).label('month'),
        func.count(SessionModel.id).label('sessions'),
        func.count(func.distinct(Booking.id)).label('bookings')
    ).outerjoin(Booking).filter(SessionModel.semester_id == semester_id).group_by('month').all()
    
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
        and_(Attendance.user_id == user_id, Attendance.status == AttendanceStatus.PRESENT)
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
    ).outerjoin(SessionModel).outerjoin(Booking, Booking.session_id == SessionModel.id).outerjoin(
        Attendance, Attendance.session_id == SessionModel.id
    ).filter(
        and_(Booking.user_id == user_id, Attendance.user_id == user_id)
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
    sessions = db.query(SessionModel).filter(SessionModel.semester_id == semester_id).all()
    
    # Create CSV content
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Session ID', 'Title', 'Date Start', 'Date End', 'Mode', 'Capacity',
        'Location', 'Meeting Link', 'Group', 'Instructor', 'Total Bookings',
        'Confirmed Bookings', 'Waitlisted', 'Present Attendance', 'Average Rating'
    ])
    
    # Write data
    for session in sessions:
        total_bookings = db.query(func.count(Booking.id)).filter(Booking.session_id == session.id).scalar() or 0
        confirmed_bookings = db.query(func.count(Booking.id)).filter(
            and_(Booking.session_id == session.id, Booking.status == BookingStatus.CONFIRMED)
        ).scalar() or 0
        waitlisted = db.query(func.count(Booking.id)).filter(
            and_(Booking.session_id == session.id, Booking.status == BookingStatus.WAITLISTED)
        ).scalar() or 0
        present_attendance = db.query(func.count(Attendance.id)).filter(
            and_(Attendance.session_id == session.id, Attendance.status == AttendanceStatus.PRESENT)
        ).scalar() or 0
        avg_rating = db.query(func.avg(Feedback.rating)).filter(Feedback.session_id == session.id).scalar()
        
        writer.writerow([
            session.id,
            session.title,
            session.date_start,
            session.date_end,
            session.mode.value,
            session.capacity,
            session.location or '',
            session.meeting_link or '',
            session.group.name if session.group else '',
            session.instructor.name if session.instructor else '',
            total_bookings,
            confirmed_bookings,
            waitlisted,
            present_attendance,
            round(float(avg_rating), 2) if avg_rating else 0
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
    total_sessions = db.query(func.count(SessionModel.id)).scalar() or 0
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
        SessionModel.mode,
        func.count(SessionModel.id)
    ).group_by(SessionModel.mode).all()
    
    mode_breakdown = {}
    for mode, count in session_modes:
        mode_breakdown[mode.value] = count
    
    # Calculate utilization rates
    confirmed_bookings = db.query(func.count(Booking.id)).filter(
        Booking.status == BookingStatus.CONFIRMED
    ).scalar() or 0
    
    total_capacity = db.query(func.sum(SessionModel.capacity)).scalar() or 0
    
    # Attendance statistics
    total_attendances = db.query(func.count(Attendance.id)).scalar() or 0
    present_attendances = db.query(func.count(Attendance.id)).filter(
        Attendance.status == AttendanceStatus.PRESENT
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