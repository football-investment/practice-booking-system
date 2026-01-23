"""
Tournament Instructor Assignment Endpoints

This module handles instructor assignment workflow for tournaments.

TWO SCENARIOS SUPPORTED:

SCENARIO 1 - Direct Assignment:
1. Admin creates tournament → status: SEEKING_INSTRUCTOR
2. Admin directly assigns instructor (via admin UI or direct call) → status: PENDING_INSTRUCTOR_ACCEPTANCE
3. Instructor accepts assignment → status: INSTRUCTOR_CONFIRMED
4. Admin opens enrollment (via UI) → status: READY_FOR_ENROLLMENT
5. Tournament becomes ready for player enrollment

SCENARIO 2 - Application Workflow:
1. Admin creates tournament → status: SEEKING_INSTRUCTOR
2. Instructor applies to tournament (POST /tournaments/{id}/instructor-applications)
3. Admin approves application → status: INSTRUCTOR_CONFIRMED
4. Admin opens enrollment (via UI) → status: READY_FOR_ENROLLMENT
5. Tournament becomes ready for player enrollment

Authorization:
- Only INSTRUCTOR role can apply and accept assignments
- Only ADMIN role can approve applications
- Instructor must have active LFA_COACH license

⚠️ REFACTORING NOTE (P0-1 Phase 1 - 2026-01-23):
The following endpoints have been EXTRACTED to match_results.py:
- POST /{tournament_id}/sessions/{session_id}/submit-results
- PATCH /{tournament_id}/sessions/{session_id}/results (legacy)
- POST /{tournament_id}/finalize-group-stage
- POST /{tournament_id}/finalize-tournament
See: app/api/api_v1/endpoints/tournaments/match_results.py
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime
import json

from app.database import get_db
from app.models.user import User, UserRole
from app.models.semester import Semester
from app.models.session import Session as SessionModel
from app.models.license import UserLicense
from app.models.instructor_assignment import InstructorAssignmentRequest, AssignmentRequestStatus
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.dependencies import get_current_user

router = APIRouter()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def record_status_change(
    db: Session,
    tournament_id: int,
    old_status: Optional[str],
    new_status: str,
    changed_by: int,
    reason: Optional[str] = None,
    metadata: Optional[dict] = None
) -> None:
    """
    Record a status change in tournament_status_history table

    Args:
        db: Database session
        tournament_id: Tournament ID
        old_status: Previous status (None for creation)
        new_status: New status
        changed_by: User ID who made the change
        reason: Optional reason for change
        metadata: Optional metadata dict
    """
    # Convert metadata dict to JSON string if provided
    metadata_json = json.dumps(metadata) if metadata is not None else None

    db.execute(
        text("""
        INSERT INTO tournament_status_history
        (tournament_id, old_status, new_status, changed_by, reason, extra_metadata)
        VALUES (:tournament_id, :old_status, :new_status, :changed_by, :reason, :extra_metadata)
        """),
        {
            "tournament_id": tournament_id,
            "old_status": old_status,
            "new_status": new_status,
            "changed_by": changed_by,
            "reason": reason,
            "extra_metadata": metadata_json
        }
    )


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

    This endpoint transitions a tournament to INSTRUCTOR_CONFIRMED status.
    Supports two scenarios:
    1. APPLICATION_BASED: Tournament status SEEKING_INSTRUCTOR → INSTRUCTOR_CONFIRMED
    2. OPEN_ASSIGNMENT: Tournament status PENDING_INSTRUCTOR_ACCEPTANCE → INSTRUCTOR_CONFIRMED

    **Authorization:** INSTRUCTOR role only

    **Validations:**
    - Current user is INSTRUCTOR
    - Current user has active LFA_COACH license
    - Tournament exists
    - Tournament status is SEEKING_INSTRUCTOR or PENDING_INSTRUCTOR_ACCEPTANCE

    **Actions Performed:**
    - Updates semester.master_instructor_id = current_user.id
    - Updates semester.tournament_status = INSTRUCTOR_CONFIRMED
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
        "tournament_status": "INSTRUCTOR_CONFIRMED",
        "instructor_id": 5,
        "instructor_name": "Coach Smith",
        "sessions_updated": 3
    }
    ```

    **Raises:**
    - 403 FORBIDDEN: User is not an instructor or lacks LFA_COACH license
    - 404 NOT FOUND: Tournament not found
    - 400 BAD REQUEST: Tournament is not in valid status for acceptance
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
    # VALIDATION 4: Tournament status allows instructor acceptance
    # ============================================================================
    # Two scenarios:
    # 1. SEEKING_INSTRUCTOR: Instructor volunteers for APPLICATION_BASED tournaments
    # 2. PENDING_INSTRUCTOR_ACCEPTANCE: Admin directly assigned instructor (OPEN_ASSIGNMENT)
    valid_statuses = ["SEEKING_INSTRUCTOR", "PENDING_INSTRUCTOR_ACCEPTANCE"]

    if tournament.tournament_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_tournament_status",
                "message": f"Tournament cannot accept instructor assignment in current status",
                "current_status": tournament.tournament_status,
                "required_status": "SEEKING_INSTRUCTOR or PENDING_INSTRUCTOR_ACCEPTANCE",
                "tournament_id": tournament_id,
                "tournament_name": tournament.name
            }
        )

    # ============================================================================
    # ACTION 1: Update tournament master_instructor_id
    # ============================================================================
    tournament.master_instructor_id = current_user.id

    # ============================================================================
    # ACTION 2: Update tournament status to INSTRUCTOR_CONFIRMED
    # ============================================================================
    # After instructor accepts, tournament is ready for admin to open enrollment
    tournament.tournament_status = "INSTRUCTOR_CONFIRMED"
    tournament.status = "INSTRUCTOR_ASSIGNED"  # Keep old status field in sync (maps to INSTRUCTOR_ASSIGNED enum)

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
    # Get the HIGHEST level coach license for this user
    # (Instructors may have multiple LFA_COACH licenses with different levels)
    coach_license = db.query(UserLicense).filter(
        UserLicense.user_id == current_user.id,
        UserLicense.specialization_type == "LFA_COACH"
    ).order_by(UserLicense.current_level.desc()).first()

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
    # VALIDATION 2B: Coach level must be sufficient for tournament category
    # ============================================================================
    # Note: We need to check the tournament first to get its category
    # Moving this validation after tournament existence check (see VALIDATION 3B below)

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
    # VALIDATION 3B: Coach level must be sufficient for tournament age group
    # ============================================================================
    # Define minimum required coach levels for each age group
    MINIMUM_COACH_LEVELS = {
        "PRE": 1,       # Level 1 (lowest)
        "YOUTH": 3,     # Level 3
        "AMATEUR": 5,   # Level 5
        "PRO": 7        # Level 7 (highest)
    }

    tournament_age_group = tournament.age_group
    required_level = MINIMUM_COACH_LEVELS.get(tournament_age_group)

    if required_level is None:
        # Tournament age group not recognized - log warning but allow (backward compatibility)
        pass
    elif coach_license.current_level < required_level:
        # Coach level is insufficient for this tournament age group
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "insufficient_coach_level",
                "message": f"Your coach level ({coach_license.current_level}) is insufficient for {tournament_age_group} age group tournaments. Minimum required: Level {required_level}",
                "user_id": current_user.id,
                "user_email": current_user.email,
                "current_coach_level": coach_license.current_level,
                "required_coach_level": required_level,
                "tournament_age_group": tournament_age_group,
                "tournament_id": tournament_id,
                "tournament_name": tournament.name
            }
        )

    # ============================================================================
    # VALIDATION 4: Tournament must be APPLICATION_BASED (not OPEN_ASSIGNMENT)
    # ============================================================================
    if tournament.assignment_type == "OPEN_ASSIGNMENT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "direct_assignment_only",
                "message": "This tournament uses direct assignment. Instructors cannot apply - admin must directly assign.",
                "assignment_type": "OPEN_ASSIGNMENT",
                "tournament_id": tournament_id,
                "tournament_name": tournament.name
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
                "message": f"Tournament is not accepting instructor applications",
                "current_status": tournament.tournament_status,
                "required_status": "SEEKING_INSTRUCTOR",
                "tournament_id": tournament_id,
                "tournament_name": tournament.name
            }
        )

    # ============================================================================
    # VALIDATION 6: Check for existing application
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
    SCENARIO 2: Admin approves instructor application (APPLICATION_BASED).

    This endpoint allows an admin to approve an instructor's application to lead
    a tournament. For APPLICATION_BASED tournaments, approval automatically assigns
    the instructor (no further acceptance needed from instructor).

    **Authorization:** ADMIN role only

    **Validations:**
    - Current user is ADMIN
    - Tournament exists
    - Tournament must be APPLICATION_BASED (not OPEN_ASSIGNMENT)
    - Application exists and belongs to the tournament
    - Application status is PENDING
    - Tournament status is SEEKING_INSTRUCTOR

    **Actions Performed:**
    - Updates application status to ACCEPTED
    - Records responded_at timestamp
    - Records optional response_message from admin
    - Assigns instructor to tournament (master_instructor_id)
    - Updates tournament status to ONGOING
    - Creates notification for instructor

    **Returns:**
    - Application details
    - Tournament updated status

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
    # VALIDATION 3: Tournament must be APPLICATION_BASED (not OPEN_ASSIGNMENT)
    # ============================================================================
    if tournament.assignment_type == "OPEN_ASSIGNMENT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "direct_assignment_only",
                "message": "This tournament uses direct assignment. Cannot approve applications for OPEN_ASSIGNMENT tournaments.",
                "assignment_type": "OPEN_ASSIGNMENT",
                "tournament_id": tournament_id,
                "tournament_name": tournament.name
            }
        )

    # ============================================================================
    # VALIDATION 4: Application exists and belongs to tournament
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

    # Get instructor details
    instructor = db.query(User).filter(User.id == application.instructor_id).first()

    # Update tournament status and assign instructor
    # For APPLICATION_BASED: Approval = automatic assignment (status → INSTRUCTOR_CONFIRMED)
    # Instructor already showed interest by applying, no further acceptance needed
    old_tournament_status = tournament.tournament_status
    tournament.master_instructor_id = application.instructor_id
    tournament.tournament_status = "INSTRUCTOR_CONFIRMED"

    # Record status history
    record_status_change(
        db=db,
        tournament_id=tournament.id,
        old_status=old_tournament_status,
        new_status="INSTRUCTOR_CONFIRMED",
        changed_by=current_user.id,
        reason=f"Admin approved instructor application from {instructor.name} - automatically assigned",
        metadata={
            "application_id": application.id,
            "instructor_id": instructor.id,
            "instructor_name": instructor.name,
            "assignment_type": "APPLICATION_BASED"
        }
    )

    db.commit()
    db.refresh(application)
    db.refresh(tournament)

    # ============================================================================
    # CREATE NOTIFICATION for instructor
    # ============================================================================
    from app.services.notification_service import create_tournament_application_approved_notification
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"🔍 DEBUG: Creating notification for application approval")
    logger.info(f"   - Application ID: {application.id}")
    logger.info(f"   - Instructor ID: {instructor.id}")
    logger.info(f"   - Tournament ID: {tournament.id}")
    logger.info(f"   - Tournament Name: {tournament.name}")

    try:
        notification = create_tournament_application_approved_notification(
            db=db,
            instructor_id=instructor.id,
            tournament=tournament,
            response_message=approval_data.response_message or "Your application has been approved!",
            request_id=application.id
        )

        logger.info(f"✅ DEBUG: Notification object created successfully")
        logger.info(f"   - Notification type: {notification.type}")
        logger.info(f"   - User ID: {notification.user_id}")
        logger.info(f"   - Related request ID: {notification.related_request_id}")
        logger.info(f"   - Related semester ID: {notification.related_semester_id}")

        # Commit the notification
        logger.info(f"🔍 DEBUG: About to commit notification to database...")
        db.commit()
        logger.info(f"✅ DEBUG: Notification committed successfully!")

    except Exception as e:
        logger.error(f"❌ DEBUG: Error during notification creation/commit!")
        logger.error(f"   - Error type: {type(e).__name__}")
        logger.error(f"   - Error message: {str(e)}")
        logger.error(f"   - Application ID being used: {application.id}")
        logger.error(f"   - Instructor ID being used: {instructor.id}")
        logger.error(f"   - Tournament ID being used: {tournament.id}")

        # Rollback the notification (but keep the application approval)
        db.rollback()

        # Re-raise as HTTPException with detailed info
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "notification_creation_failed",
                "message": f"Application approved successfully, but notification creation failed: {str(e)}",
                "error_type": type(e).__name__,
                "application_id": application.id,
                "tournament_id": tournament_id,
                "instructor_id": instructor.id
            }
        )

    # ============================================================================
    # RETURN SUCCESS RESPONSE
    # ============================================================================
    return {
        "message": "Application approved successfully - Instructor automatically assigned",
        "application_id": application.id,
        "tournament_id": tournament.id,
        "tournament_name": tournament.name,
        "tournament_status": tournament.tournament_status,
        "instructor_id": instructor.id,
        "instructor_name": instructor.name,
        "instructor_email": instructor.email,
        "status": application.status.value,
        "approved_at": application.responded_at.isoformat(),
        "approved_by": current_user.id,
        "approved_by_name": current_user.name,
        "response_message": application.response_message,
        "assignment_type": "APPLICATION_BASED",
        "next_step": "Tournament is now ONGOING with instructor assigned"
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
# INSTRUCTOR ENDPOINT: Get My Application for Specific Tournament
# ============================================================================

@router.get("/{tournament_id}/my-application")
def get_my_tournament_application(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the current instructor's application for a specific tournament.

    **Authorization:** INSTRUCTOR role only

    **Returns:**
    - Application details if exists
    - 404 if no application exists for this tournament

    **Example Response:**
    ```json
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
                "message": "Only instructors can view their applications",
                "current_role": current_user.role.value,
                "required_role": "INSTRUCTOR"
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
    # FETCH: Application for this tournament by current instructor
    # ============================================================================
    application = db.query(InstructorAssignmentRequest).filter(
        InstructorAssignmentRequest.semester_id == tournament_id,
        InstructorAssignmentRequest.instructor_id == current_user.id
    ).first()

    # Return 404 if no application exists
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "application_not_found",
                "message": f"No application found for tournament {tournament_id}",
                "tournament_id": tournament_id,
                "instructor_id": current_user.id
            }
        )

    # ============================================================================
    # RETURN SUCCESS RESPONSE
    # ============================================================================
    # For direct assignments (requested_by != None), return special status
    # to indicate instructor must still accept
    display_status = application.status.value
    if application.requested_by is not None and application.status.value == "ACCEPTED":
        # Admin directly assigned - instructor must accept
        display_status = "PENDING_ACCEPTANCE"

    return {
        "id": application.id,
        "tournament_id": tournament.id,
        "tournament_name": tournament.name,
        "status": display_status,
        "requested_by": application.requested_by,  # None = instructor applied, not None = admin assigned
        "created_at": application.created_at.isoformat() if application.created_at else None,
        "application_message": application.request_message,
        "responded_at": application.responded_at.isoformat() if application.responded_at else None,
        "response_message": application.response_message
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
    # Get the HIGHEST level coach license for this instructor
    # (Instructors may have multiple LFA_COACH licenses with different levels)
    coach_license = db.query(UserLicense).filter(
        UserLicense.user_id == instructor.id,
        UserLicense.specialization_type == "LFA_COACH"
    ).order_by(UserLicense.current_level.desc()).first()

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
    # VALIDATION 5B: Coach level must be sufficient for tournament category
    # ============================================================================
    MINIMUM_COACH_LEVELS = {
        "PRE": 1,       # Level 1 (lowest)
        "YOUTH": 3,     # Level 3
        "AMATEUR": 5,   # Level 5
        "PRO": 7        # Level 7 (highest)
    }

    tournament_age_group = tournament.age_group
    required_level = MINIMUM_COACH_LEVELS.get(tournament_age_group)

    if required_level is None:
        # Tournament age group not recognized - log warning but allow (backward compatibility)
        pass
    elif coach_license.current_level < required_level:
        # Coach level is insufficient for this tournament age group
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "insufficient_coach_level",
                "message": f"Instructor's coach level ({coach_license.current_level}) is insufficient for {tournament_age_group} age group tournaments. Minimum required: Level {required_level}",
                "instructor_id": instructor.id,
                "instructor_email": instructor.email,
                "current_coach_level": coach_license.current_level,
                "required_coach_level": required_level,
                "tournament_age_group": tournament_age_group,
                "tournament_id": tournament_id,
                "tournament_name": tournament.name
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

    # ============================================================================
    # ACTION: Update tournament with instructor and status
    # ============================================================================
    # Admin has assigned instructor, but instructor must still accept
    old_status = tournament.tournament_status
    tournament.master_instructor_id = instructor.id
    tournament.tournament_status = "PENDING_INSTRUCTOR_ACCEPTANCE"

    # Record status change in history
    record_status_change(
        db=db,
        tournament_id=tournament.id,
        old_status=old_status,
        new_status="PENDING_INSTRUCTOR_ACCEPTANCE",
        changed_by=current_user.id,
        reason=f"Admin directly assigned instructor {instructor.name}",
        metadata={
            "assignment_id": assignment.id,
            "instructor_id": instructor.id,
            "instructor_name": instructor.name,
            "assignment_type": "DIRECT_ASSIGNMENT"
        }
    )

    db.commit()
    db.refresh(assignment)
    db.refresh(tournament)

    # ============================================================================
    # CREATE NOTIFICATION for instructor
    # ============================================================================
    from app.services.notification_service import create_tournament_direct_invitation_notification

    create_tournament_direct_invitation_notification(
        db=db,
        instructor_id=instructor.id,
        tournament=tournament,
        invitation_message=request_data.assignment_message or "You have been selected to lead this tournament!",
        request_id=assignment.id
    )

    # Commit the notification
    db.commit()

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
    # CREATE NOTIFICATION for instructor
    # ============================================================================
    from app.services.notification_service import create_tournament_application_rejected_notification

    create_tournament_application_rejected_notification(
        db=db,
        instructor_id=instructor.id,
        tournament=tournament,
        response_message=decline_data.decline_message or "Thank you for your interest.",
        request_id=application.id
    )

    # Commit the notification
    db.commit()

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


# ============================================================================
# MATCH COMMAND CENTER ENDPOINTS
# ============================================================================

@router.get("/{tournament_id}/active-match")
async def get_active_match(
    tournament_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get the current active match (session) that needs attention.

    Returns the first tournament session where:
    - is_tournament_game = true
    - game_results IS NULL (not yet recorded)

    Includes:
    - Session details
    - List of enrolled participants with attendance status
    - Next upcoming matches (queue)

    Authorization: INSTRUCTOR (must be assigned to tournament) or ADMIN
    """
    # ============================================================================
    # AUTHORIZATION CHECK
    # ============================================================================
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Check authorization
    if current_user.role == UserRole.ADMIN:
        pass  # Admin can access any tournament
    elif current_user.role == UserRole.INSTRUCTOR:
        if tournament.master_instructor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this tournament"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and admins can access match management"
        )

    # ============================================================================
    # GET ACTIVE MATCH (first session without results)
    # ============================================================================
    from app.models.attendance import Attendance
    from sqlalchemy.orm import joinedload

    active_session = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.is_tournament_game == True,
        SessionModel.game_results == None
    ).order_by(SessionModel.id).first()  # ✅ FIX: Order by ID for consistent match sequence (all sessions have same date_start with parallel fields)

    if not active_session:
        # No more matches to process
        return {
            "active_match": None,
            "message": "All matches have been completed",
            "tournament_id": tournament_id,
            "tournament_name": tournament.name
        }

    # ============================================================================
    # GET PARTICIPANTS - EXPLICIT participant_user_ids ONLY
    # ✅ MATCH STRUCTURE: No runtime filtering! Use explicit participant list.
    # ✅ NO BOOKINGS: Tournament sessions use participant_user_ids + semester_enrollments
    # ============================================================================

    # ⚠️ PREREQUISITE CHECK: participant_user_ids must be defined
    if active_session.participant_user_ids is None:
        # This match cannot start yet (e.g., knockout waiting for group stage results)
        return {
            "active_match": None,
            "message": "Match participants not yet determined. Prerequisites not met.",
            "prerequisite_status": {
                "ready": False,
                "reason": "Knockout matches require group stage results to determine qualified participants.",
                "action_required": "Complete all group stage matches first."
            },
            "tournament_id": tournament_id,
            "tournament_name": tournament.name
        }

    # Get EXPLICIT match participants (NO FILTERING, NO FALLBACK, NO BOOKINGS)
    match_participant_user_ids = active_session.participant_user_ids

    # Query users directly (NO bookings dependency)
    from app.models.user import User
    users = db.query(User).filter(
        User.id.in_(match_participant_user_ids)
    ).all()

    # Build MATCH participants list (EXPLICIT ONLY)
    match_participants = []
    for user in users:
        # Check if attendance has been marked (attendance links directly to session + user)
        attendance = db.query(Attendance).filter(
            Attendance.session_id == active_session.id,
            Attendance.user_id == user.id
        ).first()

        match_participants.append({
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "attendance_status": attendance.status.value if attendance else "PENDING",
            "is_present": attendance.status.value == "present" if attendance else False
        })

    # Get ALL tournament participants (TOURNAMENT SCOPE) for debugging/context
    # Get from semester_enrollments, not bookings
    tournament_enrollments = db.query(SemesterEnrollment).options(
        joinedload(SemesterEnrollment.user)
    ).filter(
        SemesterEnrollment.semester_id == tournament_id,
        SemesterEnrollment.is_active == True,
        SemesterEnrollment.request_status == EnrollmentStatus.APPROVED
    ).all()

    tournament_participants = []
    for enrollment in tournament_enrollments:
        attendance = db.query(Attendance).filter(
            Attendance.session_id == active_session.id,
            Attendance.user_id == enrollment.user_id
        ).first()

        tournament_participants.append({
            "user_id": enrollment.user_id,
            "name": enrollment.user.name,
            "email": enrollment.user.email,
            "attendance_status": attendance.status.value if attendance else "PENDING",
            "is_present": attendance.status.value == "present" if attendance else False
        })

    # ============================================================================
    # GET UPCOMING MATCHES (next 5 sessions without results)
    # ============================================================================
    upcoming_sessions = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.is_tournament_game == True,
        SessionModel.game_results == None,
        SessionModel.id != active_session.id
    ).order_by(SessionModel.date_start).limit(5).all()

    upcoming_matches = [
        {
            "session_id": s.id,
            "match_name": s.title,
            "start_time": s.date_start.isoformat() if s.date_start else None,
            "location": s.location
        }
        for s in upcoming_sessions
    ]

    # ✅ NEW: Calculate tournament progress
    total_matches = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.is_tournament_game == True
    ).count()

    completed_matches = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.is_tournament_game == True,
        SessionModel.game_results != None
    ).count()

    # ============================================================================
    # RETURN ACTIVE MATCH DATA
    # ✅ MATCH STRUCTURE: Explicit scope separation
    # ============================================================================
    return {
        "active_match": {
            "session_id": active_session.id,
            "match_name": active_session.title,
            "match_description": active_session.description,
            "start_time": active_session.date_start.isoformat() if active_session.date_start else None,
            "end_time": active_session.date_end.isoformat() if active_session.date_end else None,
            "location": active_session.location,
            # ✅ EXPLICIT SCOPE SEPARATION: Two participant lists
            "match_participants": match_participants,  # ⚠️ USE THIS FOR RESULT INPUT!
            "tournament_participants": tournament_participants,  # For debugging/context only
            "match_participants_count": len(match_participants),
            "tournament_participants_count": len(tournament_participants),
            "present_count": sum(1 for p in match_participants if p["is_present"]),
            "pending_count": sum(1 for p in match_participants if p["attendance_status"] == "PENDING"),
            # ✅ UNIFIED RANKING: Ranking metadata for frontend
            "ranking_mode": active_session.ranking_mode,
            "group_identifier": active_session.group_identifier,
            "expected_participants": active_session.expected_participants,
            "participant_filter": active_session.participant_filter,
            "pod_tier": active_session.pod_tier,
            "tournament_phase": active_session.tournament_phase,
            "tournament_round": active_session.tournament_round,
            # ✅ MATCH STRUCTURE: Format and scoring metadata
            "match_format": active_session.match_format or 'INDIVIDUAL_RANKING',  # Backward compatibility
            "scoring_type": active_session.scoring_type or 'PLACEMENT',
            "structure_config": active_session.structure_config
        },
        "upcoming_matches": upcoming_matches,
        "tournament_id": tournament_id,
        "tournament_name": tournament.name,
        # ✅ NEW: Progress tracking
        "total_matches": total_matches,
        "completed_matches": completed_matches
    }


@router.patch("/{tournament_id}/sessions/{session_id}/results")
async def record_match_results(
    tournament_id: int,
    session_id: int,
    result_data: RecordMatchResultsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Record results for a tournament match (session).

    - Stores results in session.game_results JSONB field
    - Updates tournament_rankings table with points
    - Auto-calculates standings based on points system

    Points System (default):
    - 1st place: 3 points
    - 2nd place: 2 points
    - 3rd place: 1 point
    - Participation: 0 points

    Authorization: INSTRUCTOR (must be assigned to tournament) or ADMIN
    """
    # ============================================================================
    # AUTHORIZATION CHECK
    # ============================================================================
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Check authorization
    if current_user.role == UserRole.ADMIN:
        pass  # Admin can access any tournament
    elif current_user.role == UserRole.INSTRUCTOR:
        if tournament.master_instructor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this tournament"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and admins can record match results"
        )

    # ============================================================================
    # GET SESSION
    # ============================================================================
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.semester_id == tournament_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found in tournament {tournament_id}"
        )

    if not session.is_tournament_game:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This session is not a tournament match"
        )

    if session.game_results is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Results have already been recorded for this match"
        )

    # ============================================================================
    # VALIDATE RESULTS
    # ============================================================================
    # Check that all users are enrolled in tournament
    from app.models.semester_enrollment import SemesterEnrollment

    user_ids = [r.user_id for r in result_data.results]
    enrollments = db.query(SemesterEnrollment).filter(
        SemesterEnrollment.semester_id == tournament_id,
        SemesterEnrollment.user_id.in_(user_ids),
        SemesterEnrollment.is_active == True
    ).all()

    enrolled_user_ids = {e.user_id for e in enrollments}
    invalid_users = set(user_ids) - enrolled_user_ids

    if invalid_users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Users {invalid_users} are not enrolled in this tournament"
        )

    # Check that ranks are valid (no duplicates)
    ranks = [r.rank for r in result_data.results]
    if len(ranks) != len(set(ranks)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate ranks are not allowed"
        )

    # ============================================================================
    # STORE RESULTS IN SESSION
    # ============================================================================
    results_dict = {
        "recorded_at": datetime.utcnow().isoformat(),
        "recorded_by": current_user.id,
        "recorded_by_name": current_user.name,
        "match_notes": result_data.match_notes,
        "results": [
            {
                "user_id": r.user_id,
                "rank": r.rank,
                "score": r.score,
                "notes": r.notes
            }
            for r in result_data.results
        ]
    }

    # Convert dict to JSON string (game_results is Text type, not JSONB)
    session.game_results = json.dumps(results_dict)
    db.flush()

    # ============================================================================
    # ⚠️ IMPORTANT: DO NOT UPDATE tournament_rankings HERE!
    # ============================================================================
    # Rankings are calculated ONLY at tournament finalization:
    # - Group Stage finalization: Calculate group standings
    # - Tournament finalization: Calculate final rankings (1st, 2nd, 3rd)
    #
    # This ensures that:
    # - Group+Knockout tournaments: Final ranking based on knockout results
    # - League tournaments: Final ranking based on total points after all matches
    # ============================================================================

    # ============================================================================
    # UPDATE RANKS (for reward distribution)
    # ============================================================================
    # After all points are recorded, update rank field based on points DESC
    db.execute(
        text("""
        UPDATE tournament_rankings tr
        SET rank = ranked.row_num
        FROM (
            SELECT
                id,
                ROW_NUMBER() OVER (ORDER BY COALESCE(points, 0) DESC, updated_at ASC) as row_num
            FROM tournament_rankings
            WHERE tournament_id = :tournament_id
        ) ranked
        WHERE tr.id = ranked.id
        """),
        {"tournament_id": tournament_id}
    )

    db.commit()
    db.refresh(session)

    # ============================================================================
    # RETURN SUCCESS RESPONSE
    # ============================================================================
    return {
        "message": "Match results recorded successfully",
        "session_id": session.id,
        "match_name": session.title,
        "tournament_id": tournament_id,
        "results": results_dict["results"],
        "recorded_at": results_dict["recorded_at"],
        "recorded_by": current_user.name
    }


@router.get("/{tournament_id}/leaderboard")
async def get_tournament_leaderboard(
    tournament_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get live tournament leaderboard/standings.

    Returns:
    - Ranked list of participants
    - Total points, matches played
    - Win/loss statistics (future enhancement)

    Authorization: Anyone can view (public leaderboard)
    But tournament must exist and be accessible to current user
    """
    # ============================================================================
    # AUTHORIZATION CHECK
    # ============================================================================
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Check if user has access (students must be enrolled, instructors must be assigned, admins always have access)
    if current_user.role == UserRole.ADMIN:
        pass
    elif current_user.role == UserRole.INSTRUCTOR:
        if tournament.master_instructor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this tournament"
            )
    elif current_user.role == UserRole.STUDENT:
        # Check if student is enrolled
        from app.models.semester_enrollment import SemesterEnrollment
        enrollment = db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tournament_id,
            SemesterEnrollment.user_id == current_user.id,
            SemesterEnrollment.is_active == True
        ).first()
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not enrolled in this tournament"
            )

    # ============================================================================
    # GET LEADERBOARD DATA
    # ============================================================================
    rankings = db.execute(
        text("""
        SELECT
            tr.user_id,
            u.name as user_name,
            u.email as user_email,
            COALESCE(tr.points, 0) as points,
            COALESCE(tr.wins, 0) as wins,
            COALESCE(tr.losses, 0) as losses,
            COALESCE(tr.draws, 0) as draws,
            tr.updated_at
        FROM tournament_rankings tr
        JOIN users u ON tr.user_id = u.id
        WHERE tr.tournament_id = :tournament_id
        ORDER BY COALESCE(tr.points, 0) DESC, u.name ASC
        """),
        {"tournament_id": tournament_id}
    ).fetchall()

    leaderboard = []
    for rank, row in enumerate(rankings, start=1):
        leaderboard.append({
            "rank": rank,
            "user_id": row.user_id,
            "name": row.user_name,
            "email": row.user_email,
            "points": float(row.points) if row.points else 0.0,
            "wins": row.wins,
            "losses": row.losses,
            "draws": row.draws,
            "last_updated": row.updated_at.isoformat() if row.updated_at else None
        })

    # ============================================================================
    # ✅ NEW: GROUP STANDINGS (for Group + Knockout tournaments)
    # ============================================================================
    group_standings = {}

    # Check if this tournament has group stage sessions
    group_sessions = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.is_tournament_game == True,
        SessionModel.tournament_phase == 'Group Stage'
    ).all()

    # ============================================================================
    # GET TOURNAMENT STATS
    # ============================================================================
    # If tournament has group stages, only count group stage matches for progress
    # (because knockout matches can't start until group stage is finalized)
    if group_sessions:
        total_matches = len(group_sessions)
        completed_matches = sum(1 for s in group_sessions if s.game_results is not None)
    else:
        # For non-group tournaments, count all matches
        total_matches = db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.is_tournament_game == True
        ).count()

        completed_matches = db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.is_tournament_game == True,
            SessionModel.game_results != None
        ).count()

    if group_sessions:
        # Calculate group standings from game_results
        from collections import defaultdict

        # Structure: {group_id: {user_id: {wins, losses, draws, points, goals_for, goals_against}}}
        group_stats = defaultdict(lambda: defaultdict(lambda: {
            'wins': 0, 'losses': 0, 'draws': 0, 'points': 0,
            'goals_for': 0, 'goals_against': 0, 'matches_played': 0
        }))

        # ✅ NEW: Initialize all groups with all participants (even if no matches played yet)
        for session in group_sessions:
            if session.group_identifier and session.participant_user_ids:
                group_id = session.group_identifier
                # Initialize all participants in this group with 0 stats
                for user_id in session.participant_user_ids:
                    # This will create the entry with default values if not exists
                    _ = group_stats[group_id][user_id]

        # Process completed matches
        for session in group_sessions:
            if not session.game_results or not session.group_identifier:
                continue

            group_id = session.group_identifier
            results = session.game_results

            # ✅ FIX: Parse game_results if it's a JSON string
            import json
            if isinstance(results, str):
                try:
                    results = json.loads(results)
                except json.JSONDecodeError:
                    continue

            # ✅ FIX: game_results is now a dict with "raw_results" key
            if isinstance(results, dict):
                raw_results = results.get('raw_results', [])
            elif isinstance(results, list):
                raw_results = results  # Fallback for old format
            else:
                continue

            # Process HEAD_TO_HEAD SCORE_BASED results
            if isinstance(raw_results, list) and len(raw_results) == 2:
                # Expect format: [{"user_id": X, "score": A}, {"user_id": Y, "score": B}]
                if all('user_id' in r and 'score' in r for r in raw_results):
                    user1_id = raw_results[0]['user_id']
                    user2_id = raw_results[1]['user_id']
                    score1 = raw_results[0]['score']
                    score2 = raw_results[1]['score']

                    # Update stats
                    group_stats[group_id][user1_id]['goals_for'] += score1
                    group_stats[group_id][user1_id]['goals_against'] += score2
                    group_stats[group_id][user2_id]['goals_for'] += score2
                    group_stats[group_id][user2_id]['goals_against'] += score1

                    group_stats[group_id][user1_id]['matches_played'] += 1
                    group_stats[group_id][user2_id]['matches_played'] += 1

                    if score1 > score2:
                        # User 1 wins
                        group_stats[group_id][user1_id]['wins'] += 1
                        group_stats[group_id][user1_id]['points'] += 3
                        group_stats[group_id][user2_id]['losses'] += 1
                    elif score2 > score1:
                        # User 2 wins
                        group_stats[group_id][user2_id]['wins'] += 1
                        group_stats[group_id][user2_id]['points'] += 3
                        group_stats[group_id][user1_id]['losses'] += 1
                    else:
                        # Draw
                        group_stats[group_id][user1_id]['draws'] += 1
                        group_stats[group_id][user1_id]['points'] += 1
                        group_stats[group_id][user2_id]['draws'] += 1
                        group_stats[group_id][user2_id]['points'] += 1

        # Convert to sorted standings per group
        from app.models.user import User

        for group_id, stats in group_stats.items():
            standings = []

            for user_id, user_stats in stats.items():
                # Fetch user name
                user = db.query(User).filter(User.id == user_id).first()
                user_name = user.name if user else f"User {user_id}"

                goal_diff = user_stats['goals_for'] - user_stats['goals_against']

                standings.append({
                    'user_id': user_id,
                    'name': user_name,
                    'points': user_stats['points'],
                    'wins': user_stats['wins'],
                    'losses': user_stats['losses'],
                    'draws': user_stats['draws'],
                    'matches_played': user_stats['matches_played'],
                    'goals_for': user_stats['goals_for'],
                    'goals_against': user_stats['goals_against'],
                    'goal_difference': goal_diff
                })

            # Sort by: points DESC, goal_difference DESC, goals_for DESC
            standings.sort(key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_for']))

            # Add rank
            for rank, player in enumerate(standings, start=1):
                player['rank'] = rank

            group_standings[group_id] = standings

    # ============================================================================
    # CHECK IF GROUP STAGE IS FINALIZED
    # ============================================================================
    group_stage_finalized = False
    knockout_sessions = []

    if group_sessions:
        # Check if any knockout session has participants assigned
        knockout_sessions = db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.is_tournament_game == True,
            SessionModel.tournament_phase == "Knockout Stage"
        ).all()

        if any(s.participant_user_ids for s in knockout_sessions):
            group_stage_finalized = True

    # ============================================================================
    # CALCULATE FINAL STANDINGS (for knockout tournaments that are complete)
    # ============================================================================
    final_standings = None

    if group_stage_finalized and knockout_sessions:
        # Check if ALL knockout matches are completed
        all_knockout_complete = all(s.game_results is not None for s in knockout_sessions)

        if all_knockout_complete:
            # Find final and bronze matches
            final_match = None
            bronze_match = None

            for session in knockout_sessions:
                title_lower = session.title.lower()
                if 'bronze' in title_lower or '3rd place' in title_lower:
                    bronze_match = session
                elif session.tournament_round == max(s.tournament_round for s in knockout_sessions):
                    # Highest round = final
                    if final_match is None or 'final' in title_lower:
                        final_match = session

            if final_match and final_match.game_results:
                # Parse final match results
                final_results = final_match.game_results
                if isinstance(final_results, str):
                    final_results = json.loads(final_results)

                final_rankings = final_results.get('derived_rankings', [])

                # Get winner and runner-up from final
                champion_id = None
                runner_up_id = None

                for r in final_rankings:
                    if r['rank'] == 1:
                        champion_id = r['user_id']
                    elif r['rank'] == 2:
                        runner_up_id = r['user_id']

                # Get 3rd and 4th from bronze match
                third_place_id = None
                fourth_place_id = None

                if bronze_match and bronze_match.game_results:
                    bronze_results = bronze_match.game_results
                    if isinstance(bronze_results, str):
                        bronze_results = json.loads(bronze_results)

                    bronze_rankings = bronze_results.get('derived_rankings', [])

                    for r in bronze_rankings:
                        if r['rank'] == 1:
                            third_place_id = r['user_id']
                        elif r['rank'] == 2:
                            fourth_place_id = r['user_id']

                # Build final standings with user details
                from app.models.user import User as UserModel

                user_ids = [champion_id, runner_up_id, third_place_id, fourth_place_id]
                user_ids = [uid for uid in user_ids if uid is not None]

                users = db.query(UserModel).filter(UserModel.id.in_(user_ids)).all()
                user_dict = {user.id: user for user in users}

                final_standings = []

                if champion_id and champion_id in user_dict:
                    final_standings.append({
                        'rank': 1,
                        'medal': '🥇',
                        'user_id': champion_id,
                        'name': user_dict[champion_id].name or user_dict[champion_id].email,
                        'title': 'Champion'
                    })

                if runner_up_id and runner_up_id in user_dict:
                    final_standings.append({
                        'rank': 2,
                        'medal': '🥈',
                        'user_id': runner_up_id,
                        'name': user_dict[runner_up_id].name or user_dict[runner_up_id].email,
                        'title': 'Runner-up'
                    })

                if third_place_id and third_place_id in user_dict:
                    final_standings.append({
                        'rank': 3,
                        'medal': '🥉',
                        'user_id': third_place_id,
                        'name': user_dict[third_place_id].name or user_dict[third_place_id].email,
                        'title': 'Third Place'
                    })

                if fourth_place_id and fourth_place_id in user_dict:
                    final_standings.append({
                        'rank': 4,
                        'medal': '',
                        'user_id': fourth_place_id,
                        'name': user_dict[fourth_place_id].name or user_dict[fourth_place_id].email,
                        'title': 'Fourth Place'
                    })

    # ============================================================================
    # RETURN LEADERBOARD
    # ============================================================================
    return {
        "tournament_id": tournament_id,
        "tournament_name": tournament.name,
        "leaderboard": leaderboard,
        "group_standings": group_standings if group_standings else None,  # ✅ NEW
        "group_stage_finalized": group_stage_finalized,  # ✅ NEW
        "final_standings": final_standings,  # ✅ NEW
        "total_participants": len(leaderboard),
        "total_matches": total_matches,
        "completed_matches": completed_matches,
        "remaining_matches": total_matches - completed_matches,
        "tournament_status": tournament.tournament_status
    }


# ============================================================================
# ✅ NEW: STRUCTURED MATCH RESULTS SUBMISSION API
# ============================================================================

class SubmitMatchResultsRequest(BaseModel):
    """
    Structured match results submission

    Format depends on match_format:
    - INDIVIDUAL_RANKING: [{"user_id": 1, "placement": 1}, ...]
    - HEAD_TO_HEAD (WIN_LOSS): [{"user_id": 1, "result": "WIN"}, {"user_id": 2, "result": "LOSS"}]
    - HEAD_TO_HEAD (SCORE): [{"user_id": 1, "score": 3}, {"user_id": 2, "score": 1}]
    - TEAM_MATCH: [{"user_id": 1, "team": "A", "team_score": 5, "opponent_score": 3}, ...]
    - TIME_BASED: [{"user_id": 1, "time_seconds": 12.45}, ...]
    - SKILL_RATING: [{"user_id": 1, "rating": 8.5, "criteria_scores": {...}}, ...]  # Extension point
    """
    results: list[Dict[str, Any]]
    notes: Optional[str] = None


@router.post("/{tournament_id}/sessions/{session_id}/submit-results")
def submit_structured_match_results(
    tournament_id: int,
    session_id: int,
    result_data: SubmitMatchResultsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    ✅ NEW: Submit structured match results

    This endpoint replaces the legacy /record-match-results endpoint with
    a more flexible structure that supports multiple match formats.

    Flow:
    1. Validate authorization and session
    2. Validate results format matches session.match_format
    3. Process results using ResultProcessor → derive rankings
    4. Calculate points using PointsCalculatorService
    5. Store results in session.game_results (DO NOT update tournament_rankings)
    6. Rankings calculated ONLY at tournament finalization

    Authorization: INSTRUCTOR (assigned to tournament) or ADMIN
    """
    # ============================================================================
    # AUTHORIZATION CHECK
    # ============================================================================
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Check authorization
    if current_user.role == UserRole.ADMIN:
        pass  # Admin can access any tournament
    elif current_user.role == UserRole.INSTRUCTOR:
        if tournament.master_instructor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this tournament"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and admins can record match results"
        )

    # ============================================================================
    # GET SESSION
    # ============================================================================
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.semester_id == tournament_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found in tournament {tournament_id}"
        )

    if not session.is_tournament_game:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This session is not a tournament match"
        )

    if session.game_results is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Results have already been recorded for this match"
        )

    # ============================================================================
    # VALIDATE MATCH FORMAT
    # ============================================================================
    match_format = session.match_format or 'INDIVIDUAL_RANKING'  # Backward compatibility

    # ============================================================================
    # PROCESS RESULTS → DERIVE RANKINGS
    # ============================================================================
    from app.services.tournament.result_processor import ResultProcessor

    result_processor = ResultProcessor(db)

    # Validate results format
    is_valid, error_msg = result_processor.validate_results(
        match_format=match_format,
        results=result_data.results,
        expected_participants=session.expected_participants
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid results format: {error_msg}"
        )

    # Process results and derive rankings
    try:
        derived_rankings = result_processor.process_results(
            session_id=session_id,
            match_format=match_format,
            results=result_data.results,
            structure_config=session.structure_config
        )
    except NotImplementedError as e:
        # SKILL_RATING not yet implemented
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing results: {str(e)}"
        )

    # ============================================================================
    # CALCULATE POINTS (for display only, NOT saved to tournament_rankings yet)
    # ============================================================================
    from app.services.tournament.points_calculator_service import PointsCalculatorService

    points_calculator = PointsCalculatorService(db)
    tournament_config = points_calculator.get_tournament_type_config(tournament_id)

    points_map = points_calculator.calculate_points_batch(
        session_id=session_id,
        rankings=derived_rankings,
        tournament_type_config=tournament_config
    )

    # ============================================================================
    # ⚠️ IMPORTANT: DO NOT UPDATE tournament_rankings HERE!
    # ============================================================================
    # Rankings are calculated ONLY at tournament finalization:
    # - Group Stage finalization: Calculate group standings
    # - Tournament finalization: Calculate final rankings (1st, 2nd, 3rd)
    #
    # This ensures that:
    # - Group+Knockout tournaments: Final ranking based on knockout results
    # - League tournaments: Final ranking based on total points after all matches
    # ============================================================================

    # ============================================================================
    # STORE RESULTS IN SESSION
    # ============================================================================
    results_dict = {
        "match_format": match_format,
        "submitted_at": datetime.utcnow().isoformat(),
        "submitted_by": current_user.id,
        "raw_results": result_data.results,
        "derived_rankings": [{"user_id": uid, "rank": rank} for uid, rank in derived_rankings],
        "points_awarded": {str(uid): pts for uid, pts in points_map.items()},
        "notes": result_data.notes
    }

    session.game_results = json.dumps(results_dict)
    db.commit()

    # ============================================================================
    # ✅ AUTO-ADVANCE: Set next round participants for knockout tournaments
    # ============================================================================
    if session.tournament_phase == "Knockout Stage" and session.tournament_round:
        # Get winner (rank 1) from this match
        winner_id = None
        for uid, rank in derived_rankings:
            if rank == 1:
                winner_id = uid
                break

        if winner_id:
            # Check if all matches in current round are completed
            current_round_sessions = db.query(SessionModel).filter(
                SessionModel.semester_id == tournament_id,
                SessionModel.is_tournament_game == True,
                SessionModel.tournament_phase == "Knockout Stage",
                SessionModel.tournament_round == session.tournament_round
            ).all()

            all_completed = all(s.game_results is not None for s in current_round_sessions)

            if all_completed:
                # Get winners from all matches in current round
                round_winners = []
                for s in current_round_sessions:
                    if s.game_results:
                        results = json.loads(s.game_results) if isinstance(s.game_results, str) else s.game_results
                        rankings = results.get('derived_rankings', [])
                        for r in rankings:
                            if r['rank'] == 1:
                                round_winners.append(r['user_id'])
                                break

                # Get next round sessions
                next_round = session.tournament_round + 1
                next_round_sessions = db.query(SessionModel).filter(
                    SessionModel.semester_id == tournament_id,
                    SessionModel.is_tournament_game == True,
                    SessionModel.tournament_phase == "Knockout Stage",
                    SessionModel.tournament_round == next_round
                ).order_by(SessionModel.id).all()

                # Assign winners to next round matches
                if next_round_sessions and len(round_winners) >= 2:
                    # Simple pairing: winners[0] vs winners[1], winners[2] vs winners[3], etc.
                    for idx, next_session in enumerate(next_round_sessions):
                        start_idx = idx * 2
                        if start_idx + 1 < len(round_winners):
                            next_session.participant_user_ids = [
                                round_winners[start_idx],
                                round_winners[start_idx + 1]
                            ]

                    db.commit()

    # ============================================================================
    # RETURN SUCCESS RESPONSE
    # ============================================================================
    return {
        "success": True,
        "message": f"Results recorded successfully for {len(derived_rankings)} participants",
        "session_id": session_id,
        "match_format": match_format,
        "rankings": [
            {
                "user_id": uid,
                "rank": rank,
                "points_earned": points_map.get(uid, 0.0)
            }
            for uid, rank in derived_rankings
        ],
        "total_points_awarded": sum(points_map.values())
    }


@router.get("/{tournament_id}/sessions")
def get_tournament_sessions_debug(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get all sessions for a tournament with participant_user_ids for debug purposes

    Authorization: INSTRUCTOR or ADMIN
    """
    try:
        print(f"🔍 DEBUG: get_tournament_sessions called for tournament_id={tournament_id}, user={current_user.email}")

        # Check authorization
        tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

        if not tournament:
            print(f"🔍 DEBUG: Tournament {tournament_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tournament {tournament_id} not found"
            )

        print(f"🔍 DEBUG: Tournament found: {tournament.name}, master_instructor_id={tournament.master_instructor_id}")

        if current_user.role == UserRole.ADMIN:
            print(f"🔍 DEBUG: User is ADMIN, access granted")
            pass  # Admin can access any tournament
        elif current_user.role == UserRole.INSTRUCTOR:
            print(f"🔍 DEBUG: User is INSTRUCTOR, checking assignment")
            if tournament.master_instructor_id != current_user.id:
                print(f"🔍 DEBUG: Access denied - instructor not assigned")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not assigned to this tournament"
                )
            print(f"🔍 DEBUG: Access granted - instructor is assigned")
        else:
            print(f"🔍 DEBUG: Access denied - role is {current_user.role}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only instructors and admins can access tournament sessions"
            )

        # Get all sessions
        sessions = db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.is_tournament_game == True
        ).order_by(SessionModel.date_start).all()

        print(f"🔍 DEBUG: Found {len(sessions)} tournament sessions")

        result = []
        for idx, session in enumerate(sessions):
            print(f"🔍 DEBUG: Processing session {idx+1}/{len(sessions)}: id={session.id}, participant_user_ids={session.participant_user_ids}")

            # Get participant names from user IDs
            participant_names = []
            if session.participant_user_ids:
                for user_id in session.participant_user_ids:
                    user = db.query(User).filter(User.id == user_id).first()
                    if user:
                        participant_names.append(user.name)
                    else:
                        participant_names.append(f"User {user_id}")

            # Extract matchup info from structure_config for knockout matches
            matchup_display = None
            if session.structure_config and isinstance(session.structure_config, dict):
                matchup_display = session.structure_config.get('matchup')

            # Parse game_results if it's a JSON string
            game_results_parsed = None
            if session.game_results:
                if isinstance(session.game_results, str):
                    try:
                        game_results_parsed = json.loads(session.game_results)
                    except:
                        game_results_parsed = session.game_results
                else:
                    game_results_parsed = session.game_results

            result.append({
                "session_id": session.id,
                "title": session.title,
                "tournament_phase": session.tournament_phase,
                "tournament_round": session.tournament_round,
                "group_identifier": session.group_identifier,
                "round_number": session.round_number,
                "match_format": session.match_format,
                "scoring_type": session.scoring_type,
                "expected_participants": session.expected_participants,
                "participant_user_ids": session.participant_user_ids,
                "participant_names": participant_names,
                "matchup_display": matchup_display,  # ADDED: For knockout matches (A1 vs B2, etc.)
                "date": session.date_start.isoformat() if session.date_start else None,
                "has_results": session.game_results is not None,
                "game_results": game_results_parsed  # ✅ ADDED
            })

        print(f"🔍 DEBUG: Returning {len(result)} sessions")
        return result

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        print(f"🔍 DEBUG: EXCEPTION in get_tournament_sessions: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# ✅ NEW: TOURNAMENT FINALIZATION ENDPOINTS
# ============================================================================

@router.post("/{tournament_id}/finalize-group-stage")
def finalize_group_stage(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    🏆 Finalize Group Stage and calculate group standings.

    This endpoint:
    1. Validates all group stage matches are completed
    2. Calculates group standings (points from game_results)
    3. Determines qualified participants for knockout stage
    4. Updates knockout session participant_user_ids with seeding

    Authorization: ADMIN or INSTRUCTOR
    """
    # Authorization check
    if current_user.role not in [UserRole.ADMIN, UserRole.INSTRUCTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and instructors can finalize tournament stages"
        )

    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Get all group stage sessions
    group_sessions = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.is_tournament_game == True,
        SessionModel.tournament_phase == "Group Stage"
    ).all()

    if not group_sessions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No group stage matches found"
        )

    # Check if all group matches are completed
    incomplete_matches = [s for s in group_sessions if s.game_results is None]

    if incomplete_matches:
        return {
            "success": False,
            "message": f"{len(incomplete_matches)} group stage matches are not completed yet",
            "incomplete_matches": [
                {"session_id": s.id, "title": s.title} for s in incomplete_matches
            ]
        }

    # Calculate group standings (using same logic as /leaderboard endpoint)
    from collections import defaultdict
    import json

    # Structure: {group_id: {user_id: {wins, losses, draws, points, goals_for, goals_against}}}
    group_stats = defaultdict(lambda: defaultdict(lambda: {
        'wins': 0, 'losses': 0, 'draws': 0, 'points': 0,
        'goals_for': 0, 'goals_against': 0, 'matches_played': 0
    }))

    # Initialize all groups with all participants (even if no matches played yet)
    for session in group_sessions:
        if session.group_identifier and session.participant_user_ids:
            group_id = session.group_identifier
            for user_id in session.participant_user_ids:
                _ = group_stats[group_id][user_id]

    # Process completed matches
    for session in group_sessions:
        if not session.game_results or not session.group_identifier:
            continue

        results = session.game_results

        # Parse game_results if it's a JSON string
        if isinstance(results, str):
            try:
                results = json.loads(results)
            except json.JSONDecodeError:
                continue

        # game_results is a dict with "raw_results" key for HEAD_TO_HEAD
        if isinstance(results, dict):
            raw_results = results.get('raw_results', [])
        elif isinstance(results, list):
            raw_results = results  # Fallback for old format
        else:
            continue

        if len(raw_results) != 2:
            continue  # HEAD_TO_HEAD should have exactly 2 players

        group_id = session.group_identifier
        player1 = raw_results[0]
        player2 = raw_results[1]

        user1_id = player1['user_id']
        user2_id = player2['user_id']
        score1 = player1.get('score', 0)
        score2 = player2.get('score', 0)

        # Update goals
        group_stats[group_id][user1_id]['goals_for'] += score1
        group_stats[group_id][user1_id]['goals_against'] += score2
        group_stats[group_id][user1_id]['matches_played'] += 1

        group_stats[group_id][user2_id]['goals_for'] += score2
        group_stats[group_id][user2_id]['goals_against'] += score1
        group_stats[group_id][user2_id]['matches_played'] += 1

        # Determine win/loss/draw and update points (Football: 3 pts win, 1 pt draw, 0 loss)
        if score1 > score2:
            group_stats[group_id][user1_id]['wins'] += 1
            group_stats[group_id][user1_id]['points'] += 3
            group_stats[group_id][user2_id]['losses'] += 1
        elif score2 > score1:
            group_stats[group_id][user2_id]['wins'] += 1
            group_stats[group_id][user2_id]['points'] += 3
            group_stats[group_id][user1_id]['losses'] += 1
        else:  # Draw
            group_stats[group_id][user1_id]['draws'] += 1
            group_stats[group_id][user1_id]['points'] += 1
            group_stats[group_id][user2_id]['draws'] += 1
            group_stats[group_id][user2_id]['points'] += 1

    # Convert to sorted standings with user details
    from app.models.user import User as UserModel

    group_standings = {}
    qualified_participants = []  # List of qualified user_ids for knockout stage

    for group_id, stats in group_stats.items():
        # Get user details
        user_ids = list(stats.keys())
        users = db.query(UserModel).filter(UserModel.id.in_(user_ids)).all()
        user_dict = {user.id: user for user in users}

        # Create standings list
        standings_list = []
        for user_id, user_stats in stats.items():
            user = user_dict.get(user_id)
            if not user:
                continue

            goal_difference = user_stats['goals_for'] - user_stats['goals_against']

            standings_list.append({
                'user_id': user_id,
                'name': user.name or user.email,
                'points': user_stats['points'],
                'wins': user_stats['wins'],
                'draws': user_stats['draws'],
                'losses': user_stats['losses'],
                'goals_for': user_stats['goals_for'],
                'goals_against': user_stats['goals_against'],
                'goal_difference': goal_difference,
                'matches_played': user_stats['matches_played']
            })

        # Sort by: points (desc), goal_difference (desc), goals_for (desc)
        standings_list.sort(
            key=lambda x: (x['points'], x['goal_difference'], x['goals_for']),
            reverse=True
        )

        # Add rank
        for rank, player in enumerate(standings_list, start=1):
            player['rank'] = rank

        group_standings[group_id] = standings_list

        # Top 2 from each group qualify for knockout stage
        qualified_from_group = [p['user_id'] for p in standings_list[:2]]
        qualified_participants.extend(qualified_from_group)

    # 📸 Save snapshot of group stage standings before transitioning to knockout
    from datetime import datetime

    snapshot_data = {
        "timestamp": datetime.now().isoformat(),
        "phase": "group_stage_complete",
        "group_standings": group_standings,
        "qualified_participants": qualified_participants,
        "total_groups": len(group_standings),
        "total_qualified": len(qualified_participants),
        "qualification_rule": "top_2_per_group"
    }

    # Save snapshot to tournament.enrollment_snapshot
    tournament.enrollment_snapshot = snapshot_data

    # Update knockout sessions with qualified participants
    knockout_sessions = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.is_tournament_game == True,
        SessionModel.tournament_phase == "Knockout Stage"
    ).order_by(SessionModel.tournament_round, SessionModel.id).all()

    # ✅ Seeding logic: Standard crossover bracket (A1 vs B2, B1 vs A2)
    # Get top 2 from each group
    sorted_groups = sorted(group_standings.items())  # Sort by group_id to ensure consistency

    if len(sorted_groups) >= 2:
        group_a_id, group_a_standings = sorted_groups[0]
        group_b_id, group_b_standings = sorted_groups[1]

        # Extract top 2 from each group
        a1 = group_a_standings[0]['user_id'] if len(group_a_standings) >= 1 else None
        a2 = group_a_standings[1]['user_id'] if len(group_a_standings) >= 2 else None
        b1 = group_b_standings[0]['user_id'] if len(group_b_standings) >= 1 else None
        b2 = group_b_standings[1]['user_id'] if len(group_b_standings) >= 2 else None

        # Get Round of 4 (Semifinal) sessions - tournament_round is Integer!
        # Round 1 = Semifinals (4 players), Round 2 = Final (2 players)
        semifinal_sessions = [s for s in knockout_sessions if s.tournament_round == 1]

        if len(semifinal_sessions) >= 2 and all([a1, a2, b1, b2]):
            # Semifinal 1: A1 vs B2 (crossover bracket)
            semifinal_sessions[0].participant_user_ids = [a1, b2]

            # Semifinal 2: B1 vs A2 (crossover bracket)
            semifinal_sessions[1].participant_user_ids = [b1, a2]

            # Note: Final match (round 2) participant_user_ids will be set after semifinals are completed

    db.commit()

    return {
        "success": True,
        "message": "✅ Group stage finalized successfully! Snapshot saved.",
        "group_standings": group_standings,
        "qualified_participants": qualified_participants,
        "knockout_sessions_updated": len(knockout_sessions),
        "snapshot_saved": True
    }


@router.post("/{tournament_id}/finalize-tournament")
def finalize_tournament(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    🏆 Finalize Tournament and calculate FINAL RANKING.

    This endpoint:
    1. Validates ALL matches are completed
    2. Calculates final ranking based on tournament structure:
       - Group+Knockout: Based on final match (1st, 2nd, 3rd place match)
       - League: Based on total points
    3. Updates tournament_rankings table
    4. Sets tournament status to COMPLETED

    Authorization: ADMIN only
    """
    # Authorization check
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can finalize tournaments"
        )

    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Get ALL tournament sessions
    all_sessions = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.is_tournament_game == True
    ).all()

    if not all_sessions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tournament matches found"
        )

    # Check if all matches are completed
    incomplete_matches = [s for s in all_sessions if s.game_results is None]

    if incomplete_matches:
        return {
            "success": False,
            "message": f"{len(incomplete_matches)} matches are not completed yet",
            "incomplete_matches": [
                {"session_id": s.id, "title": s.title} for s in incomplete_matches
            ]
        }

    # Calculate final ranking
    # This is where we determine 1st, 2nd, 3rd place based on final match results

    # For Group+Knockout: Find final match and 3rd place match
    final_match = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.tournament_phase == "Knockout Stage",
        SessionModel.title.ilike("%final%")
    ).first()

    third_place_match = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.tournament_phase == "Knockout Stage",
        SessionModel.title.ilike("%3rd%")
    ).first()

    final_rankings = []

    if final_match and final_match.game_results:
        results = json.loads(final_match.game_results)
        for result in results.get("derived_rankings", []):
            if result["rank"] == 1:
                final_rankings.append({"user_id": result["user_id"], "final_rank": 1, "place": "1st"})
            elif result["rank"] == 2:
                final_rankings.append({"user_id": result["user_id"], "final_rank": 2, "place": "2nd"})

    if third_place_match and third_place_match.game_results:
        results = json.loads(third_place_match.game_results)
        for result in results.get("derived_rankings", []):
            if result["rank"] == 1:
                final_rankings.append({"user_id": result["user_id"], "final_rank": 3, "place": "3rd"})

    # Update tournament_rankings table
    # Clear existing rankings
    db.execute(
        text("DELETE FROM tournament_rankings WHERE tournament_id = :tournament_id"),
        {"tournament_id": tournament_id}
    )

    # Insert final rankings
    for ranking in final_rankings:
        db.execute(
            text("""
            INSERT INTO tournament_rankings (tournament_id, user_id, rank, points, participant_type)
            VALUES (:tournament_id, :user_id, :rank, :points, 'USER')
            """),
            {
                "tournament_id": tournament_id,
                "user_id": ranking["user_id"],
                "rank": ranking["final_rank"],
                "points": 0  # Points not used for final ranking
            }
        )

    # Update tournament status
    tournament.tournament_status = "COMPLETED"

    db.commit()

    return {
        "success": True,
        "message": "Tournament finalized successfully",
        "final_rankings": final_rankings,
        "tournament_status": "COMPLETED"
    }
