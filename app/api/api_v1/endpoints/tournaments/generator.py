"""
Tournament Generator API

Admin-only endpoint for creating one-day tournaments
"""
from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.api.api_v1.endpoints.auth import get_current_user
from app.models.user import User, UserRole
from app.models.specialization import SpecializationType
from app.services.tournament_service import TournamentService
from app.services.tournament.reward_policy_loader import (
    get_available_policies,
    get_policy_info,
    RewardPolicyError
)

router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class SessionConfig(BaseModel):
    """Configuration for a single tournament session"""
    time: str = Field(..., description="Start time in HH:MM format (e.g., '09:00')")
    title: str = Field(..., description="Session title")
    duration_minutes: int = Field(90, description="Session duration in minutes")
    capacity: int = Field(20, description="Maximum capacity")
    credit_cost: int = Field(1, description="Credit cost per booking")
    description: Optional[str] = Field("", description="Session description")


class TournamentGenerateRequest(BaseModel):
    """Request to generate a tournament"""
    date: str = Field(..., description="Tournament date (YYYY-MM-DD)")
    name: str = Field(..., description="Tournament name")
    specialization_type: SpecializationType = Field(..., description="Specialization type")
    age_group: Optional[str] = Field(None, description="Age group (e.g., PRE, YOUTH)")
    campus_id: Optional[int] = Field(None, description="Campus ID (preferred - most specific location)")
    location_id: Optional[int] = Field(None, description="Location ID (fallback if campus not specified)")
    sessions: List[SessionConfig] = Field(..., description="Session configurations")
    auto_book_students: bool = Field(False, description="Auto-book students (only for testing)")
    booking_capacity_pct: int = Field(70, ge=0, le=100, description="Booking fill percentage (0-100)")
    reward_policy_name: str = Field("default", description="Reward policy name (default: 'default')")


class SendInstructorRequestSchema(BaseModel):
    """Request to send instructor assignment request"""
    instructor_id: int = Field(..., description="Grandmaster instructor ID to invite")
    message: Optional[str] = Field(None, description="Optional message to instructor")


class InstructorRequestActionSchema(BaseModel):
    """Request to accept/decline instructor assignment"""
    reason: Optional[str] = Field(None, description="Optional reason for declining")


class TournamentGenerateResponse(BaseModel):
    """Response from tournament generation"""
    tournament_id: int = Field(..., description="Semester ID (tournament ID)")
    semester_id: int = Field(..., description="Semester ID")
    session_ids: List[int] = Field(..., description="Created session IDs")
    total_bookings: int = Field(..., description="Total bookings created")
    summary: dict = Field(..., description="Tournament summary")


class TournamentSummaryResponse(BaseModel):
    """Tournament summary response"""
    id: int  # ✅ Added for frontend compatibility
    tournament_id: int  # ✅ Added for frontend compatibility
    semester_id: int
    code: str  # ✅ Tournament code (TOURN-YYYYMMDD)
    name: str
    start_date: str  # ✅ ISO format date
    date: str
    status: Optional[str]  # ✅ Tournament status (SEEKING_INSTRUCTOR, READY_FOR_ENROLLMENT, etc.)
    specialization_type: Optional[str]  # ✅ LFA_FOOTBALL_PLAYER, etc.
    age_group: Optional[str]  # ✅ PRE, YOUTH, AMATEUR, PRO
    location_id: Optional[int]  # ✅ Location FK
    campus_id: Optional[int]  # ✅ Campus FK
    reward_policy_name: str  # ✅ Reward policy name
    reward_policy_snapshot: Optional[dict]  # ✅ Reward policy snapshot (JSONB)
    session_count: int
    sessions_count: int  # ✅ Added for frontend compatibility
    sessions: List[dict]
    total_capacity: int
    total_bookings: int
    fill_percentage: float


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/generate", response_model=TournamentGenerateResponse, status_code=status.HTTP_201_CREATED)
def generate_tournament(
    request: TournamentGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a one-day tournament (Admin only)

    **Authorization:** Admin only

    **IMPORTANT:** Tournament is created with status SEEKING_INSTRUCTOR.
    Admin must assign master instructor via /tournaments/{id}/assign-instructor
    before students can register.

    Creates:
    - 1-day semester (status: SEEKING_INSTRUCTOR)
    - Multiple sessions within the day (no instructor yet)
    - Optional auto-bookings for students (testing only)

    **Example:**
    ```json
    {
      "date": "2025-12-27",
      "name": "Holiday Football Cup",
      "specialization_type": "LFA_FOOTBALL_PLAYER",
      "age_group": "YOUTH",
      "location_id": 1,
      "sessions": [
        {"time": "09:00", "title": "Morning Session", "capacity": 20},
        {"time": "13:00", "title": "Afternoon Session", "capacity": 20}
      ]
    }
    ```
    """
    # Authorization: Admin only
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create tournaments"
        )

    # Validate date
    try:
        tournament_date = datetime.strptime(request.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )

    # Validate future date
    if tournament_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tournament date must be today or in the future"
        )

    # Create tournament semester (no instructor yet)
    semester = TournamentService.create_tournament_semester(
        db=db,
        tournament_date=tournament_date,
        name=request.name,
        specialization_type=request.specialization_type,
        campus_id=request.campus_id,  # ✅ NEW: Campus support
        location_id=request.location_id,
        age_group=request.age_group,
        reward_policy_name=request.reward_policy_name
    )

    # Create sessions (no instructor yet)
    session_configs = [
        {
            "time": s.time,
            "title": s.title,
            "duration_minutes": s.duration_minutes,
            "capacity": s.capacity,
            "credit_cost": s.credit_cost,
            "description": s.description
        }
        for s in request.sessions
    ]

    created_sessions = TournamentService.create_tournament_sessions(
        db=db,
        semester_id=semester.id,
        session_configs=session_configs,
        tournament_date=tournament_date
    )

    session_ids = [s.id for s in created_sessions]

    # Auto-book students if requested (FOR TESTING ONLY)
    total_bookings = 0
    if request.auto_book_students:
        bookings_map = TournamentService.auto_book_students(
            db=db,
            session_ids=session_ids,
            capacity_percentage=request.booking_capacity_pct
        )
        total_bookings = sum(len(user_ids) for user_ids in bookings_map.values())

    # Get summary
    summary = TournamentService.get_tournament_summary(db, semester.id)

    return TournamentGenerateResponse(
        tournament_id=semester.id,
        semester_id=semester.id,
        session_ids=session_ids,
        total_bookings=total_bookings,
        summary=summary
    )


@router.post("/{tournament_id}/send-instructor-request", status_code=status.HTTP_201_CREATED)
def send_instructor_request(
    tournament_id: int,
    request: SendInstructorRequestSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send instructor assignment request for tournament (Admin only)

    **Authorization:** Admin only

    **IMPORTANT:** This sends a PENDING request to the instructor (grandmaster).
    Tournament activates only when instructor ACCEPTS the request.

    Workflow:
    1. Admin sends request → Status: PENDING
    2. Instructor sees request in their dashboard
    3. Instructor accepts → Tournament status: READY_FOR_ENROLLMENT
    4. Instructor declines → Tournament status: SEEKING_INSTRUCTOR (can send new request)

    **Example:**
    ```json
    {
      "instructor_id": 2,
      "message": "Would you like to lead the Winter Cup tournament?"
    }
    ```
    """
    # Authorization: Admin only
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can send instructor requests"
        )

    try:
        assignment_request = TournamentService.send_instructor_request(
            db=db,
            semester_id=tournament_id,
            instructor_id=request.instructor_id,
            requested_by_admin_id=current_user.id,
            message=request.message
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return {
        "request_id": assignment_request.id,
        "tournament_id": tournament_id,
        "instructor_id": assignment_request.instructor_id,
        "status": assignment_request.status.value,
        "message": "Instructor request sent successfully. Waiting for instructor response."
    }


@router.post("/requests/{request_id}/accept", status_code=status.HTTP_200_OK)
def accept_instructor_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Accept tournament instructor assignment request (Instructor only)

    **Authorization:** Instructor only (must be the invited instructor)

    **IMPORTANT:** Accepting activates the tournament (status: READY_FOR_ENROLLMENT).

    **Example:**
    ```
    POST /api/v1/tournaments/requests/123/accept
    ```
    """
    # Authorization: Instructor only
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can accept requests"
        )

    try:
        semester = TournamentService.accept_instructor_request(
            db=db,
            request_id=request_id,
            instructor_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return {
        "request_id": request_id,
        "tournament_id": semester.id,
        "status": "ACCEPTED",
        "tournament_status": semester.status.value,
        "message": "Request accepted! You are now the master instructor for this tournament."
    }


@router.post("/requests/{request_id}/decline", status_code=status.HTTP_200_OK)
def decline_instructor_request(
    request_id: int,
    request: InstructorRequestActionSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Decline tournament instructor assignment request (Instructor only)

    **Authorization:** Instructor only (must be the invited instructor)

    **IMPORTANT:** Declining keeps tournament in SEEKING_INSTRUCTOR status.
    Admin can send new request to another instructor.

    **Example:**
    ```json
    {
      "reason": "Not available on that date"
    }
    ```
    """
    # Authorization: Instructor only
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can decline requests"
        )

    try:
        assignment_request = TournamentService.decline_instructor_request(
            db=db,
            request_id=request_id,
            instructor_id=current_user.id,
            reason=request.reason
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return {
        "request_id": request_id,
        "status": "DECLINED",
        "message": "Request declined. Admin can send a new request to another instructor."
    }


@router.get("/{tournament_id}/summary", response_model=TournamentSummaryResponse)
def get_tournament_summary(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get tournament summary

    **Authorization:** Any authenticated user
    """
    summary = TournamentService.get_tournament_summary(db, tournament_id)

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament with ID {tournament_id} not found"
        )

    return TournamentSummaryResponse(**summary)


@router.get("/requests/instructor/{instructor_id}")
def get_instructor_tournament_requests(
    instructor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get pending tournament assignment requests for an instructor

    **Authorization:** Instructor can only view their own requests, Admin can view any

    Returns list of pending tournament instructor assignment requests
    """
    # Authorization: Instructor can only see their own, admin can see any
    if current_user.role != UserRole.ADMIN and current_user.id != instructor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own requests"
        )

    from app.models.instructor_assignment import InstructorAssignmentRequest, AssignmentRequestStatus

    # Get pending requests for this instructor
    requests = db.query(InstructorAssignmentRequest).filter(
        InstructorAssignmentRequest.instructor_id == instructor_id,
        InstructorAssignmentRequest.status == AssignmentRequestStatus.PENDING
    ).all()

    # Format response
    return [
        {
            "id": req.id,
            "semester_id": req.semester_id,
            "message": req.request_message,
            "created_at": req.created_at.isoformat() if req.created_at else None,
            "expires_at": req.expires_at.isoformat() if req.expires_at else None,
            "priority": req.priority,
            "status": req.status.value
        }
        for req in requests
    ]


@router.delete("/{tournament_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tournament(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete tournament and all associated data

    **Authorization:** Admin only

    Deletes:
    - Tournament semester
    - All sessions (cascade)
    - All bookings (cascade)
    """
    # Authorization: Admin only
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete tournaments"
        )

    success = TournamentService.delete_tournament(db, tournament_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament with ID {tournament_id} not found"
        )

    return None


# NOTE: distribute_rewards endpoint moved to rewards.py for better organization
# The new endpoint includes:
# - Ranking validation
# - Status transition to REWARDS_DISTRIBUTED
# - Proper response schema with status field
# See: app/api/api_v1/endpoints/tournaments/rewards.py


@router.get("/reward-policies", status_code=status.HTTP_200_OK)
def get_reward_policies(
    current_user: User = Depends(get_current_user)
):
    """
    Get list of available reward policies (Admin only)

    **Authorization:** Admin only

    Returns list of available reward policy names and their metadata.

    **Example Response:**
    ```json
    {
      "policies": [
        {
          "policy_name": "default",
          "version": "1.0.0",
          "description": "Standard reward policy for all tournament types",
          "applies_to_all_tournament_types": true,
          "specializations": ["LFA_FOOTBALL_PLAYER", "LFA_COACH", "INTERNSHIP", "GANCUJU_PLAYER"]
        }
      ]
    }
    ```
    """
    # Authorization: Admin only
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view reward policies"
        )

    try:
        policy_names = get_available_policies()
        policies = []

        for name in policy_names:
            try:
                info = get_policy_info(name)
                policies.append(info)
            except RewardPolicyError:
                # Skip invalid policies
                continue

        return {
            "policies": policies,
            "count": len(policies)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading reward policies: {str(e)}"
        )


@router.get("/reward-policies/{policy_name}", status_code=status.HTTP_200_OK)
def get_reward_policy_details(
    policy_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get details of a specific reward policy (Admin only)

    **Authorization:** Admin only

    Returns detailed information about a specific reward policy.

    **Example Response:**
    ```json
    {
      "policy_name": "default",
      "version": "1.0.0",
      "description": "Standard reward policy for all tournament types",
      "placement_rewards": {
        "1ST": {"xp": 500, "credits": 100},
        "2ND": {"xp": 300, "credits": 50},
        "3RD": {"xp": 200, "credits": 25},
        "PARTICIPANT": {"xp": 50, "credits": 0}
      },
      "participation_rewards": {
        "session_attendance": {"xp": 10, "credits": 0}
      },
      "specializations": ["LFA_FOOTBALL_PLAYER", "LFA_COACH", "INTERNSHIP", "GANCUJU_PLAYER"],
      "applies_to_all_tournament_types": true
    }
    ```
    """
    # Authorization: Admin only
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view reward policies"
        )

    try:
        policy_info = get_policy_info(policy_name)
        return policy_info
    except RewardPolicyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
