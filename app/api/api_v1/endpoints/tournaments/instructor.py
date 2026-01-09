"""
Tournament Instructor Assignment Endpoints

This module handles instructor assignment workflow for tournaments.

TWO SCENARIOS SUPPORTED:

SCENARIO 1 - Direct Assignment:
1. Admin creates tournament → status: SEEKING_INSTRUCTOR
2. Admin directly assigns instructor (via admin UI or direct call)
3. Instructor accepts assignment → status: READY_FOR_ENROLLMENT
4. Tournament becomes ready for player enrollment

SCENARIO 2 - Application Workflow:
1. Admin creates tournament → status: SEEKING_INSTRUCTOR
2. Instructor applies to tournament (POST /tournaments/{id}/instructor-applications)
3. Admin approves application (POST /tournaments/{id}/instructor-applications/{id}/approve)
4. Instructor accepts assignment → status: READY_FOR_ENROLLMENT
5. Tournament becomes ready for player enrollment

Authorization:
- Only INSTRUCTOR role can apply and accept assignments
- Only ADMIN role can approve applications
- Instructor must have active LFA_COACH license
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.user import User, UserRole
from app.models.semester import Semester, SemesterStatus
from app.models.session import Session as SessionModel
from app.models.license import UserLicense
from app.models.instructor_assignment import InstructorAssignmentRequest, AssignmentRequestStatus
from app.dependencies import get_current_user

router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class InstructorApplicationRequest(BaseModel):
    """Request schema for instructor application"""
    application_message: Optional[str] = None


class InstructorApplicationApprovalRequest(BaseModel):
    """Request schema for admin approval"""
    response_message: Optional[str] = None


class DirectAssignmentRequest(BaseModel):
    """Request schema for direct instructor assignment"""
    instructor_id: int
    assignment_message: Optional[str] = None


class DeclineApplicationRequest(BaseModel):
    """Request schema for declining an application"""
    decline_message: Optional[str] = None


@router.post("/{tournament_id}/instructor-assignment/accept")
def accept_instructor_assignment(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Instructor accepts tournament assignment.

    This endpoint transitions a tournament from SEEKING_INSTRUCTOR to READY_FOR_ENROLLMENT
    by assigning an instructor to lead the tournament.

    **Authorization:** INSTRUCTOR role only

    **Validations:**
    - Current user is INSTRUCTOR
    - Current user has active LFA_COACH license
    - Tournament exists
    - Tournament status is SEEKING_INSTRUCTOR

    **Actions Performed:**
    - Updates semester.master_instructor_id = current_user.id
    - Updates semester.status = READY_FOR_ENROLLMENT
    - Updates all associated sessions.instructor_id = current_user.id

    **Returns:**
    - Tournament details
    - Number of sessions updated
    - Confirmation message

    **Example Response:**
    ```json
    {
        "message": "Tournament assignment accepted successfully",
        "tournament_id": 123,
        "tournament_name": "Youth Football Tournament 2026",
        "status": "READY_FOR_ENROLLMENT",
        "instructor_id": 5,
        "instructor_name": "Coach Smith",
        "sessions_updated": 3
    }
    ```

    **Raises:**
    - 403 FORBIDDEN: User is not an instructor or lacks LFA_COACH license
    - 404 NOT FOUND: Tournament not found
    - 400 BAD REQUEST: Tournament is not in SEEKING_INSTRUCTOR status
    """
    # ============================================================================
    # VALIDATION 1: Current user is INSTRUCTOR
    # ============================================================================
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "authorization_error",
                "message": "Only instructors can accept tournament assignments",
                "current_role": current_user.role.value,
                "required_role": "INSTRUCTOR"
            }
        )

    # ============================================================================
    # VALIDATION 2: Current user has LFA_COACH license
    # ============================================================================
    coach_license = db.query(UserLicense).filter(
        UserLicense.user_id == current_user.id,
        UserLicense.specialization_type == "LFA_COACH"
    ).first()

    if not coach_license:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "license_required",
                "message": "Instructor must have LFA_COACH license to lead tournaments",
                "user_id": current_user.id,
                "user_email": current_user.email,
                "required_license": "LFA_COACH"
            }
        )

    # ============================================================================
    # VALIDATION 3: Tournament exists
    # ============================================================================
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "tournament_not_found",
                "message": f"Tournament {tournament_id} not found",
                "tournament_id": tournament_id
            }
        )

    # ============================================================================
    # VALIDATION 4: Tournament status is SEEKING_INSTRUCTOR
    # ============================================================================
    if tournament.tournament_status != "SEEKING_INSTRUCTOR":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_tournament_status",
                "message": f"Tournament cannot accept instructor assignment in current status",
                "current_status": tournament.tournament_status,
                "required_status": "SEEKING_INSTRUCTOR",
                "tournament_id": tournament_id,
                "tournament_name": tournament.name
            }
        )

    # ============================================================================
    # ACTION 1: Update tournament master_instructor_id
    # ============================================================================
    tournament.master_instructor_id = current_user.id

    # ============================================================================
    # ACTION 2: Update tournament status to READY_FOR_ENROLLMENT
    # ============================================================================
    tournament.tournament_status = "READY_FOR_ENROLLMENT"

    # ============================================================================
    # ACTION 3: Update all sessions with instructor_id
    # ============================================================================
    sessions = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id
    ).all()

    for session in sessions:
        session.instructor_id = current_user.id

    # ============================================================================
    # COMMIT TRANSACTION
    # ============================================================================
    db.commit()
    db.refresh(tournament)

    # ============================================================================
    # RETURN SUCCESS RESPONSE
    # ============================================================================
    return {
        "message": "Tournament assignment accepted successfully",
        "tournament_id": tournament.id,
        "tournament_name": tournament.name,
        "tournament_code": tournament.code,
        "status": tournament.tournament_status,
        "instructor_id": current_user.id,
        "instructor_name": current_user.name,
        "instructor_email": current_user.email,
        "sessions_updated": len(sessions),
        "tournament_date": tournament.start_date.isoformat() if tournament.start_date else None
    }


@router.post("/{tournament_id}/instructor-applications")
def apply_to_tournament(
    tournament_id: int,
    request_data: InstructorApplicationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    SCENARIO 2: Instructor applies to tournament.

    This endpoint allows an instructor to apply to lead a tournament that is
    seeking an instructor.

    **Authorization:** INSTRUCTOR role only

    **Validations:**
    - Current user is INSTRUCTOR
    - Current user has active LFA_COACH license
    - Tournament exists
    - Tournament status is SEEKING_INSTRUCTOR
    - No existing PENDING or ACCEPTED application from this instructor

    **Actions Performed:**
    - Creates InstructorAssignmentRequest with status PENDING
    - Records application_message from instructor

    **Returns:**
    - Application details
    - Application ID
    - Confirmation message

    **Raises:**
    - 403 FORBIDDEN: User is not an instructor or lacks LFA_COACH license
    - 404 NOT FOUND: Tournament not found
    - 400 BAD REQUEST: Invalid tournament status or duplicate application
    """
    # ============================================================================
    # VALIDATION 1: Current user is INSTRUCTOR
    # ============================================================================
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "authorization_error",
                "message": "Only instructors can apply to tournaments",
                "current_role": current_user.role.value,
                "required_role": "INSTRUCTOR"
            }
        )

    # ============================================================================
    # VALIDATION 2: Current user has LFA_COACH license
    # ============================================================================
    coach_license = db.query(UserLicense).filter(
        UserLicense.user_id == current_user.id,
        UserLicense.specialization_type == "LFA_COACH"
    ).first()

    if not coach_license:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "license_required",
                "message": "Instructor must have LFA_COACH license to apply to tournaments",
                "user_id": current_user.id,
                "user_email": current_user.email,
                "required_license": "LFA_COACH"
            }
        )

    # ============================================================================
    # VALIDATION 3: Tournament exists
    # ============================================================================
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "tournament_not_found",
                "message": f"Tournament {tournament_id} not found",
                "tournament_id": tournament_id
            }
        )

    # ============================================================================
    # VALIDATION 4: Tournament status is SEEKING_INSTRUCTOR
    # ============================================================================
    if tournament.tournament_status != "SEEKING_INSTRUCTOR":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_tournament_status",
                "message": f"Tournament is not accepting instructor applications",
                "current_status": tournament.tournament_status,
                "required_status": "SEEKING_INSTRUCTOR",
                "tournament_id": tournament_id,
                "tournament_name": tournament.name
            }
        )

    # ============================================================================
    # VALIDATION 5: Check for existing application
    # ============================================================================
    existing_application = db.query(InstructorAssignmentRequest).filter(
        InstructorAssignmentRequest.semester_id == tournament_id,
        InstructorAssignmentRequest.instructor_id == current_user.id,
        InstructorAssignmentRequest.status.in_([
            AssignmentRequestStatus.PENDING,
            AssignmentRequestStatus.ACCEPTED
        ])
    ).first()

    if existing_application:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "duplicate_application",
                "message": f"You already have a {existing_application.status.value} application for this tournament",
                "application_id": existing_application.id,
                "application_status": existing_application.status.value
            }
        )

    # ============================================================================
    # ACTION: Create application record
    # ============================================================================
    application = InstructorAssignmentRequest(
        semester_id=tournament_id,
        instructor_id=current_user.id,
        requested_by=None,  # Instructor-initiated application
        status=AssignmentRequestStatus.PENDING,
        request_message=request_data.application_message,
        priority=0
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    # ============================================================================
    # RETURN SUCCESS RESPONSE
    # ============================================================================
    return {
        "message": "Application submitted successfully",
        "application_id": application.id,
        "tournament_id": tournament.id,
        "tournament_name": tournament.name,
        "instructor_id": current_user.id,
        "instructor_name": current_user.name,
        "instructor_email": current_user.email,
        "status": application.status.value,
        "applied_at": application.created_at.isoformat(),
        "application_message": application.request_message
    }


@router.post("/{tournament_id}/instructor-applications/{application_id}/approve")
def approve_instructor_application(
    tournament_id: int,
    application_id: int,
    approval_data: InstructorApplicationApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    SCENARIO 2: Admin approves instructor application.

    This endpoint allows an admin to approve an instructor's application to lead
    a tournament. After approval, the instructor must still accept the assignment
    via the /instructor-assignment/accept endpoint.

    **Authorization:** ADMIN role only

    **Validations:**
    - Current user is ADMIN
    - Tournament exists
    - Application exists and belongs to the tournament
    - Application status is PENDING
    - Tournament status is SEEKING_INSTRUCTOR

    **Actions Performed:**
    - Updates application status to ACCEPTED
    - Records responded_at timestamp
    - Records optional response_message from admin

    **Returns:**
    - Application details
    - Next steps for instructor

    **Raises:**
    - 403 FORBIDDEN: User is not an admin
    - 404 NOT FOUND: Tournament or application not found
    - 400 BAD REQUEST: Invalid status or already processed
    """
    # ============================================================================
    # VALIDATION 1: Current user is ADMIN
    # ============================================================================
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "authorization_error",
                "message": "Only admins can approve instructor applications",
                "current_role": current_user.role.value,
                "required_role": "ADMIN"
            }
        )

    # ============================================================================
    # VALIDATION 2: Tournament exists
    # ============================================================================
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "tournament_not_found",
                "message": f"Tournament {tournament_id} not found",
                "tournament_id": tournament_id
            }
        )

    # ============================================================================
    # VALIDATION 3: Application exists and belongs to tournament
    # ============================================================================
    application = db.query(InstructorAssignmentRequest).filter(
        InstructorAssignmentRequest.id == application_id,
        InstructorAssignmentRequest.semester_id == tournament_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "application_not_found",
                "message": f"Application {application_id} not found for tournament {tournament_id}",
                "application_id": application_id,
                "tournament_id": tournament_id
            }
        )

    # ============================================================================
    # VALIDATION 4: Application status is PENDING
    # ============================================================================
    if application.status != AssignmentRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_application_status",
                "message": f"Application cannot be approved in current status",
                "current_status": application.status.value,
                "required_status": "PENDING",
                "application_id": application_id
            }
        )

    # ============================================================================
    # VALIDATION 5: Tournament status is SEEKING_INSTRUCTOR
    # ============================================================================
    if tournament.tournament_status != "SEEKING_INSTRUCTOR":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_tournament_status",
                "message": f"Tournament is not seeking instructor",
                "current_status": tournament.tournament_status,
                "required_status": "SEEKING_INSTRUCTOR",
                "tournament_id": tournament_id
            }
        )

    # ============================================================================
    # ACTION: Approve application
    # ============================================================================
    application.status = AssignmentRequestStatus.ACCEPTED
    application.responded_at = datetime.utcnow()
    application.response_message = approval_data.response_message

    db.commit()
    db.refresh(application)

    # Get instructor details
    instructor = db.query(User).filter(User.id == application.instructor_id).first()

    # ============================================================================
    # RETURN SUCCESS RESPONSE
    # ============================================================================
    return {
        "message": "Application approved successfully",
        "application_id": application.id,
        "tournament_id": tournament.id,
        "tournament_name": tournament.name,
        "instructor_id": instructor.id,
        "instructor_name": instructor.name,
        "instructor_email": instructor.email,
        "status": application.status.value,
        "approved_at": application.responded_at.isoformat(),
        "approved_by": current_user.id,
        "approved_by_name": current_user.name,
        "response_message": application.response_message,
        "next_step": "Instructor must now accept the assignment via POST /tournaments/{tournament_id}/instructor-assignment/accept"
    }


@router.get("/{tournament_id}/instructor-applications")
def get_instructor_applications(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get all instructor applications for a tournament.

    **Authorization:** ADMIN role only

    **Returns:**
    - List of all applications for the tournament with instructor details

    **Example Response:**
    ```json
    {
        "tournament_id": 123,
        "tournament_name": "Youth Football Tournament 2026",
        "applications": [
            {
                "id": 1,
                "instructor_id": 5,
                "instructor_name": "Coach Smith",
                "instructor_email": "coach.smith@example.com",
                "status": "PENDING",
                "created_at": "2026-01-04T10:30:00",
                "request_message": "I would love to lead this tournament",
                "responded_at": null,
                "response_message": null
            }
        ]
    }
    ```
    """
    # ============================================================================
    # VALIDATION 1: Current user is ADMIN
    # ============================================================================
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "authorization_error",
                "message": "Only admins can view instructor applications",
                "current_role": current_user.role.value,
                "required_role": "ADMIN"
            }
        )

    # ============================================================================
    # VALIDATION 2: Tournament exists
    # ============================================================================
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "tournament_not_found",
                "message": f"Tournament {tournament_id} not found",
                "tournament_id": tournament_id
            }
        )

    # ============================================================================
    # FETCH: All applications for this tournament
    # ============================================================================
    applications = db.query(InstructorAssignmentRequest).filter(
        InstructorAssignmentRequest.semester_id == tournament_id
    ).all()

    # Build response with instructor details
    applications_data = []
    for app in applications:
        instructor = db.query(User).filter(User.id == app.instructor_id).first()

        applications_data.append({
            "id": app.id,
            "instructor_id": app.instructor_id,
            "instructor_name": instructor.name if instructor else "Unknown",
            "instructor_email": instructor.email if instructor else "N/A",
            "status": app.status.value,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "request_message": app.request_message,
            "responded_at": app.responded_at.isoformat() if app.responded_at else None,
            "response_message": app.response_message,
            "requested_by": app.requested_by
        })

    # ============================================================================
    # RETURN SUCCESS RESPONSE
    # ============================================================================
    return {
        "tournament_id": tournament.id,
        "tournament_name": tournament.name,
        "tournament_status": tournament.tournament_status,
        "master_instructor_id": tournament.master_instructor_id,
        "applications": applications_data,
        "total_applications": len(applications_data)
    }


# ============================================================================
# INSTRUCTOR ENDPOINT: Get My Applications
# ============================================================================

@router.get("/instructor/my-applications")
def get_my_instructor_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get all tournament applications submitted by the current instructor.

    **Authorization:** INSTRUCTOR role only

    **Returns:**
    - List of instructor's own applications with tournament details
    - Application status and messages
    - Tournament information

    **Example Response:**
    ```json
    {
        "applications": [
            {
                "id": 1,
                "tournament_id": 123,
                "tournament_name": "Youth Football Tournament 2026",
                "status": "PENDING",
                "created_at": "2026-01-04T10:00:00",
                "application_message": "I am interested in leading this tournament",
                "responded_at": null,
                "response_message": null
            }
        ],
        "total_applications": 1
    }
    ```
    """
    # ============================================================================
    # VALIDATION 1: Current user is INSTRUCTOR
    # ============================================================================
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "authorization_error",
                "message": "Only instructors can view their own applications",
                "current_role": current_user.role.value,
                "required_role": "INSTRUCTOR"
            }
        )

    # ============================================================================
    # FETCH: All applications by this instructor
    # ============================================================================
    applications = db.query(InstructorAssignmentRequest).filter(
        InstructorAssignmentRequest.instructor_id == current_user.id
    ).order_by(InstructorAssignmentRequest.created_at.desc()).all()

    # ============================================================================
    # BUILD RESPONSE: Include tournament details for each application
    # ============================================================================
    applications_data = []

    for app in applications:
        # Get tournament details
        tournament = db.query(Semester).filter(Semester.id == app.semester_id).first()

        applications_data.append({
            "id": app.id,
            "tournament_id": app.semester_id,
            "tournament_name": tournament.name if tournament else "Unknown Tournament",
            "tournament_start_date": tournament.start_date.isoformat() if tournament and tournament.start_date else None,
            "tournament_status": tournament.tournament_status if tournament else "UNKNOWN",
            "status": app.status.value,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "application_message": app.request_message,
            "responded_at": app.responded_at.isoformat() if app.responded_at else None,
            "response_message": app.response_message
        })

    # ============================================================================
    # RETURN SUCCESS RESPONSE
    # ============================================================================
    return {
        "applications": applications_data,
        "total_applications": len(applications_data),
        "instructor_id": current_user.id,
        "instructor_name": current_user.name
    }


@router.post("/{tournament_id}/direct-assign-instructor")
def direct_assign_instructor(
    tournament_id: int,
    request_data: DirectAssignmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    SCENARIO 1: Admin directly assigns instructor to tournament.

    This endpoint allows an admin to directly assign an instructor without the
    application workflow. Creates an ACCEPTED assignment request immediately.

    **Authorization:** ADMIN role only

    **Validations:**
    - Current user is ADMIN
    - Tournament exists
    - Tournament status is SEEKING_INSTRUCTOR
    - Instructor exists and has INSTRUCTOR role
    - Instructor has active LFA_COACH license

    **Actions Performed:**
    - Creates InstructorAssignmentRequest with status ACCEPTED
    - Records assignment_message from admin
    - Sets requested_by to admin's user ID

    **Returns:**
    - Assignment details
    - Instructor information
    - Next step for instructor acceptance

    **Raises:**
    - 403 FORBIDDEN: User is not an admin
    - 404 NOT FOUND: Tournament or instructor not found
    - 400 BAD REQUEST: Invalid status or license missing
    """
    # ============================================================================
    # VALIDATION 1: Current user is ADMIN
    # ============================================================================
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "authorization_error",
                "message": "Only admins can directly assign instructors",
                "current_role": current_user.role.value,
                "required_role": "ADMIN"
            }
        )

    # ============================================================================
    # VALIDATION 2: Tournament exists
    # ============================================================================
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "tournament_not_found",
                "message": f"Tournament {tournament_id} not found",
                "tournament_id": tournament_id
            }
        )

    # ============================================================================
    # VALIDATION 3: Tournament status is SEEKING_INSTRUCTOR
    # ============================================================================
    if tournament.tournament_status != "SEEKING_INSTRUCTOR":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_tournament_status",
                "message": f"Tournament is not seeking instructor",
                "current_status": tournament.tournament_status,
                "required_status": "SEEKING_INSTRUCTOR",
                "tournament_id": tournament_id
            }
        )

    # ============================================================================
    # VALIDATION 4: Instructor exists and has INSTRUCTOR role
    # ============================================================================
    instructor = db.query(User).filter(User.id == request_data.instructor_id).first()

    if not instructor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "instructor_not_found",
                "message": f"Instructor {request_data.instructor_id} not found",
                "instructor_id": request_data.instructor_id
            }
        )

    if instructor.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_instructor_role",
                "message": "Selected user is not an instructor",
                "user_id": instructor.id,
                "user_role": instructor.role.value,
                "required_role": "INSTRUCTOR"
            }
        )

    # ============================================================================
    # VALIDATION 5: Instructor has LFA_COACH license
    # ============================================================================
    coach_license = db.query(UserLicense).filter(
        UserLicense.user_id == instructor.id,
        UserLicense.specialization_type == "LFA_COACH"
    ).first()

    if not coach_license:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "license_required",
                "message": "Instructor must have LFA_COACH license",
                "instructor_id": instructor.id,
                "instructor_email": instructor.email,
                "required_license": "LFA_COACH"
            }
        )

    # ============================================================================
    # VALIDATION 6: Check for existing ACCEPTED assignment
    # ============================================================================
    existing_assignment = db.query(InstructorAssignmentRequest).filter(
        InstructorAssignmentRequest.semester_id == tournament_id,
        InstructorAssignmentRequest.instructor_id == instructor.id,
        InstructorAssignmentRequest.status == AssignmentRequestStatus.ACCEPTED
    ).first()

    if existing_assignment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "duplicate_assignment",
                "message": f"Instructor already has an ACCEPTED assignment for this tournament",
                "assignment_id": existing_assignment.id
            }
        )

    # ============================================================================
    # ACTION: Create direct assignment with ACCEPTED status
    # ============================================================================
    assignment = InstructorAssignmentRequest(
        semester_id=tournament_id,
        instructor_id=instructor.id,
        requested_by=current_user.id,  # Admin who made the direct assignment
        status=AssignmentRequestStatus.ACCEPTED,  # Directly accepted
        request_message=request_data.assignment_message,
        responded_at=datetime.utcnow(),  # Immediately responded
        priority=10  # High priority for direct assignments
    )

    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    # ============================================================================
    # RETURN SUCCESS RESPONSE
    # ============================================================================
    return {
        "message": "Instructor directly assigned successfully",
        "assignment_id": assignment.id,
        "tournament_id": tournament.id,
        "tournament_name": tournament.name,
        "instructor_id": instructor.id,
        "instructor_name": instructor.name,
        "instructor_email": instructor.email,
        "status": assignment.status.value,
        "assigned_by": current_user.id,
        "assigned_by_name": current_user.name,
        "assigned_at": assignment.responded_at.isoformat(),
        "assignment_message": assignment.request_message,
        "next_step": f"Instructor must accept assignment via POST /tournaments/{tournament_id}/instructor-assignment/accept"
    }


@router.post("/{tournament_id}/instructor-applications/{application_id}/decline")
def decline_instructor_application(
    tournament_id: int,
    application_id: int,
    decline_data: DeclineApplicationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    SCENARIO 2: Admin declines instructor application.

    This endpoint allows an admin to decline an instructor's application to lead
    a tournament.

    **Authorization:** ADMIN role only

    **Validations:**
    - Current user is ADMIN
    - Tournament exists
    - Application exists and belongs to the tournament
    - Application status is PENDING

    **Actions Performed:**
    - Updates application status to DECLINED
    - Records responded_at timestamp
    - Records optional decline_message from admin

    **Returns:**
    - Application details
    - Decline confirmation

    **Raises:**
    - 403 FORBIDDEN: User is not an admin
    - 404 NOT FOUND: Tournament or application not found
    - 400 BAD REQUEST: Invalid status or already processed
    """
    # ============================================================================
    # VALIDATION 1: Current user is ADMIN
    # ============================================================================
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "authorization_error",
                "message": "Only admins can decline instructor applications",
                "current_role": current_user.role.value,
                "required_role": "ADMIN"
            }
        )

    # ============================================================================
    # VALIDATION 2: Tournament exists
    # ============================================================================
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "tournament_not_found",
                "message": f"Tournament {tournament_id} not found",
                "tournament_id": tournament_id
            }
        )

    # ============================================================================
    # VALIDATION 3: Application exists and belongs to tournament
    # ============================================================================
    application = db.query(InstructorAssignmentRequest).filter(
        InstructorAssignmentRequest.id == application_id,
        InstructorAssignmentRequest.semester_id == tournament_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "application_not_found",
                "message": f"Application {application_id} not found for tournament {tournament_id}",
                "application_id": application_id,
                "tournament_id": tournament_id
            }
        )

    # ============================================================================
    # VALIDATION 4: Application status is PENDING
    # ============================================================================
    if application.status != AssignmentRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_application_status",
                "message": f"Application cannot be declined in current status",
                "current_status": application.status.value,
                "required_status": "PENDING",
                "application_id": application_id
            }
        )

    # ============================================================================
    # ACTION: Decline application
    # ============================================================================
    application.status = AssignmentRequestStatus.DECLINED
    application.responded_at = datetime.utcnow()
    application.response_message = decline_data.decline_message

    db.commit()
    db.refresh(application)

    # Get instructor details
    instructor = db.query(User).filter(User.id == application.instructor_id).first()

    # ============================================================================
    # RETURN SUCCESS RESPONSE
    # ============================================================================
    return {
        "message": "Application declined successfully",
        "application_id": application.id,
        "tournament_id": tournament.id,
        "tournament_name": tournament.name,
        "instructor_id": instructor.id if instructor else None,
        "instructor_name": instructor.name if instructor else "Unknown",
        "instructor_email": instructor.email if instructor else "N/A",
        "status": application.status.value,
        "declined_at": application.responded_at.isoformat(),
        "declined_by": current_user.id,
        "declined_by_name": current_user.name,
        "decline_message": application.response_message
    }
