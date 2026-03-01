"""
Session Attendance API Endpoints (PHASE 4 - P0)
==============================================

Session-specific attendance operations - mark, confirm, change requests.
Reuses business logic from web routes with clean JSON API interface.
"""
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User, UserRole
from .....models.session import Session as SessionModel
from .....models.booking import Booking
from .....models.attendance import Attendance, AttendanceStatus, ConfirmationStatus
from .....services.audit_service import AuditService
from .....models.audit_log import AuditAction


router = APIRouter()


# ============================================================================
# Request/Response Schemas
# ============================================================================

class MarkAttendanceRequest(BaseModel):
    """Request to mark attendance"""
    student_id: int = Field(..., description="Student user ID")
    status: str = Field(..., description="Attendance status: present, absent, late, excused")
    notes: Optional[str] = Field(None, description="Optional notes")


class MarkAttendanceResponse(BaseModel):
    """Response from marking attendance"""
    success: bool
    message: str
    attendance_id: int
    student_id: int
    status: str
    change_requested: bool = Field(False, description="True if change request created instead of direct update")


class ConfirmAttendanceRequest(BaseModel):
    """Student confirms their attendance"""
    student_id: int = Field(..., description="Student user ID (for verification)")


class ConfirmAttendanceResponse(BaseModel):
    """Response from confirming attendance"""
    success: bool
    message: str
    attendance_id: int
    confirmed_at: datetime


class HandleChangeRequestRequest(BaseModel):
    """Handle instructor's attendance change request"""
    student_id: int = Field(..., description="Student user ID")
    action: str = Field(..., description="approve or reject")
    reason: Optional[str] = Field(None, description="Reason for approval/rejection")


class HandleChangeRequestResponse(BaseModel):
    """Response from handling change request"""
    success: bool
    message: str
    attendance_id: int
    action: str
    final_status: str


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/{session_id}/attendance/mark", response_model=MarkAttendanceResponse)
def mark_attendance(
    session_id: int,
    data: MarkAttendanceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Mark attendance for a student (Instructor only)

    **Business Logic** (from web route):
    - Only instructor who owns the session can mark attendance
    - Can only mark from 15 min before start until session end
    - If attendance already confirmed → creates change request instead
    - Otherwise → updates attendance directly

    **Permissions:** INSTRUCTOR role required
    """
    # Verify instructor role
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can mark attendance"
        )

    # Get session
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Verify instructor owns session
    if session.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your session"
        )

    # Check time window (15 min before start until end)
    budapest_tz = ZoneInfo("Europe/Budapest")
    now = datetime.now(budapest_tz)

    session_start = session.date_start
    session_end = session.date_end
    if session_start.tzinfo is None:
        session_start = session_start.replace(tzinfo=budapest_tz)
    if session_end.tzinfo is None:
        session_end = session_end.replace(tzinfo=budapest_tz)

    if (session_start - timedelta(minutes=15)) > now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot mark attendance more than 15 minutes before session start"
        )

    if now > session_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot mark attendance after session has ended"
        )

    # Verify student is enrolled
    booking = db.query(Booking).filter(
        Booking.session_id == session_id,
        Booking.user_id == data.student_id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not enrolled in this session"
        )

    # Convert status string to enum
    try:
        attendance_status = AttendanceStatus[data.status.lower()]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {data.status}. Valid values: present, absent, late, excused"
        )

    # Check if attendance already exists
    attendance = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.user_id == data.student_id
    ).first()

    change_requested = False

    if attendance:
        # If already confirmed → create change request
        if attendance.confirmation_status == ConfirmationStatus.confirmed:
            attendance.pending_change_to = attendance_status.value
            attendance.change_requested_by = current_user.id
            attendance.change_requested_at = datetime.now(timezone.utc)
            attendance.change_request_reason = data.notes
            change_requested = True
            message = f"Change request created (from {attendance.status.value} to {attendance_status.value}) - awaiting student approval"
        else:
            # Not confirmed yet → direct update
            attendance.status = attendance_status
            if data.notes:
                attendance.notes = data.notes
            message = "Attendance updated"

        db.commit()
        db.refresh(attendance)
    else:
        # Create new attendance
        attendance = Attendance(
            session_id=session_id,
            user_id=data.student_id,
            status=attendance_status,
            check_in_time=datetime.now(timezone.utc) if attendance_status == AttendanceStatus.present else None,
            notes=data.notes or ""
        )
        db.add(attendance)
        db.commit()
        db.refresh(attendance)
        message = "Attendance marked"

    # Audit log
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.UPDATE if attendance.id else AuditAction.USER_CREATED,
        user_id=current_user.id,
        resource_type="attendance",
        resource_id=attendance.id,
        details={
            "session_id": session_id,
            "student_id": data.student_id,
            "status": data.status,
            "change_requested": change_requested
        }
    )

    return MarkAttendanceResponse(
        success=True,
        message=message,
        attendance_id=attendance.id,
        student_id=data.student_id,
        status=attendance.status.value,
        change_requested=change_requested
    )


@router.post("/{session_id}/attendance/confirm", response_model=ConfirmAttendanceResponse)
def confirm_attendance(
    session_id: int,
    data: ConfirmAttendanceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Student confirms their attendance

    **Business Logic** (from web route):
    - Student confirms instructor's attendance marking
    - Sets confirmation_status to CONFIRMED
    - Records student confirmation timestamp

    **Permissions:** STUDENT role or owner
    """
    # Verify user is the student
    if current_user.id != data.student_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only confirm your own attendance"
        )

    # Get attendance record
    attendance = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.user_id == data.student_id
    ).first()

    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found"
        )

    # Confirm attendance
    attendance.confirmation_status = ConfirmationStatus.confirmed
    attendance.student_confirmed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(attendance)

    # Audit log
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.UPDATE,
        user_id=current_user.id,
        resource_type="attendance",
        resource_id=attendance.id,
        details={
            "session_id": session_id,
            "action": "confirmed"
        }
    )

    return ConfirmAttendanceResponse(
        success=True,
        message="Attendance confirmed",
        attendance_id=attendance.id,
        confirmed_at=attendance.student_confirmed_at
    )


@router.post("/{session_id}/attendance/change-request", response_model=HandleChangeRequestResponse)
def handle_change_request(
    session_id: int,
    data: HandleChangeRequestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Handle instructor's attendance change request (Student decision)

    **Business Logic** (from web route):
    - Student approves or rejects instructor's change request
    - If approved → updates attendance status
    - If rejected → clears pending change

    **Permissions:** STUDENT role or owner
    """
    # Verify user is the student
    if current_user.id != data.student_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only handle your own change requests"
        )

    # Get attendance record
    attendance = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.user_id == data.student_id
    ).first()

    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found"
        )

    # Check if there's a pending change
    if not attendance.pending_change_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending change request"
        )

    final_status = attendance.status.value

    if data.action.lower() == "approve":
        # Apply the change
        attendance.status = AttendanceStatus[attendance.pending_change_to]
        final_status = attendance.status.value
        message = f"Change request approved - status updated to {final_status}"
    elif data.action.lower() == "reject":
        # Reject the change
        message = f"Change request rejected - status remains {final_status}"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Use 'approve' or 'reject'"
        )

    # Clear change request fields
    attendance.pending_change_to = None
    attendance.change_requested_by = None
    attendance.change_requested_at = None
    attendance.change_request_reason = None

    db.commit()
    db.refresh(attendance)

    # Audit log
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.UPDATE,
        user_id=current_user.id,
        resource_type="attendance",
        resource_id=attendance.id,
        details={
            "session_id": session_id,
            "action": f"change_request_{data.action.lower()}",
            "final_status": final_status,
            "reason": data.reason
        }
    )

    return HandleChangeRequestResponse(
        success=True,
        message=message,
        attendance_id=attendance.id,
        action=data.action,
        final_status=final_status
    )
