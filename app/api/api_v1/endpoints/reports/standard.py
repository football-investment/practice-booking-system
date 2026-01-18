"""
Standard report generation endpoints
"""
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from .....database import get_db
from .....models.user import User

from fastapi import Query
from sqlalchemy import func
from pydantic import BaseModel

from .....dependencies import get_current_admin_user
from .....models.semester import Semester
from .....models.session import Session as SessionTypel
from .....models.booking import Booking

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
        sessions_query = db.query(SessionTypel)
        if "semester_id" in report_config.filters:
            sessions_query = sessions_query.filter(SessionTypel.semester_id == report_config.filters["semester_id"])
        sessions = sessions_query.all()
        report_data = {
            "type": "session",
            "data": [{"id": s.id, "title": s.title, "date_start": str(s.date_start)} for s in sessions]
        }
    
    else:
        # Default system report
        total_users = db.query(func.count(User.id)).scalar() or 0
        total_sessions = db.query(func.count(SessionTypel.id)).scalar() or 0
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
