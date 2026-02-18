"""
Tournament Generator API

Admin-only endpoint for creating one-day tournaments
"""
from datetime import date, datetime
from typing import Dict, List, Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, validator

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

    # ⚠️ BUSINESS LOGIC FIX: Sessions are OPTIONAL at tournament creation
    # Sessions are added LATER by admin/instructor via Tournament Management
    sessions: List[SessionConfig] = Field(default=[], description="Session configurations (optional - can be added later)")

    auto_book_students: bool = Field(False, description="Auto-book students (only for testing)")
    booking_capacity_pct: int = Field(70, ge=0, le=100, description="Booking fill percentage (0-100)")
    reward_policy_name: str = Field("default", description="Reward policy name (default: 'default')")
    custom_reward_policy: Optional[dict] = Field(None, description="Custom reward policy (if reward_policy_name is 'custom')")

    # 🎯 NEW: Explicit business attributes (DOMAIN GAP RESOLUTION)
    assignment_type: Literal["OPEN_ASSIGNMENT", "APPLICATION_BASED"] = Field(
        ...,
        description="Tournament instructor assignment strategy: OPEN_ASSIGNMENT (admin assigns directly) or APPLICATION_BASED (instructors apply)"
    )
    max_players: int = Field(
        ...,
        gt=0,
        description="Maximum tournament participants (explicit capacity, independent of session capacity sum)"
    )
    enrollment_cost: int = Field(
        ...,
        ge=0,
        description="Enrollment fee in credits (0 = FREE, >0 = paid tournament)"
    )
    instructor_id: Optional[int] = Field(
        None,
        description="Instructor ID (ALWAYS None at creation - instructor assigned AFTER via Tournament Management)"
    )
    # ✅ CRITICAL: format MUST be defined BEFORE tournament_type_id for validator to work
    format: Literal["INDIVIDUAL_RANKING", "HEAD_TO_HEAD"] = Field(
        "HEAD_TO_HEAD",
        description="Tournament format: INDIVIDUAL_RANKING (all compete, ranked by result) or HEAD_TO_HEAD (1v1 matches)"
    )
    scoring_type: str = Field(
        "PLACEMENT",
        description="Scoring type for INDIVIDUAL_RANKING: TIME_BASED, SCORE_BASED, DISTANCE_BASED, PLACEMENT. Ignored for HEAD_TO_HEAD."
    )
    measurement_unit: Optional[str] = Field(
        None,
        description="Unit of measurement for INDIVIDUAL_RANKING: seconds/minutes (TIME_BASED), meters/centimeters (DISTANCE_BASED), points/repetitions (SCORE_BASED). NULL for PLACEMENT or HEAD_TO_HEAD."
    )
    ranking_direction: Optional[str] = Field(
        None,
        description="Ranking direction for INDIVIDUAL_RANKING: ASC (lowest wins), DESC (highest wins). HEAD_TO_HEAD always DESC. NULL for PLACEMENT."
    )
    tournament_type_id: Optional[int] = Field(
        None,
        description="Tournament type ID (e.g., knockout, league, swiss) - ONLY for HEAD_TO_HEAD format"
    )
    game_preset_id: Optional[int] = Field(
        None,
        description="Game preset ID - references pre-configured game type (e.g., Sprint Challenge, Technical Mastery)"
    )

    @validator('measurement_unit')
    def validate_measurement_unit(cls, v, values):
        """
        Validate measurement_unit consistency with scoring_type:
        - TIME_BASED: 'seconds', 'minutes', 'hours'
        - DISTANCE_BASED: 'meters', 'centimeters', 'kilometers'
        - SCORE_BASED: 'points', 'repetitions', 'goals'
        - PLACEMENT: NULL (not applicable)
        """
        scoring_type = values.get('scoring_type', 'PLACEMENT')
        format_val = values.get('format', 'HEAD_TO_HEAD')

        # HEAD_TO_HEAD: measurement_unit not used
        if format_val == "HEAD_TO_HEAD":
            return None

        # PLACEMENT: measurement_unit not applicable
        if scoring_type == "PLACEMENT":
            return None

        # For TIME_BASED, DISTANCE_BASED, SCORE_BASED: validate unit
        valid_units = {
            'TIME_BASED': ['seconds', 'minutes', 'hours'],
            'DISTANCE_BASED': ['meters', 'centimeters', 'kilometers'],
            'SCORE_BASED': ['points', 'repetitions', 'goals']
        }

        if scoring_type in valid_units:
            if v is None:
                raise ValueError(
                    f"{scoring_type} requires a measurement_unit. "
                    f"Valid options: {', '.join(valid_units[scoring_type])}"
                )
            if v not in valid_units[scoring_type]:
                raise ValueError(
                    f"Invalid measurement_unit '{v}' for {scoring_type}. "
                    f"Valid options: {', '.join(valid_units[scoring_type])}"
                )

        return v

    @validator('ranking_direction')
    def validate_ranking_direction(cls, v, values):
        """
        Validate ranking_direction:
        - INDIVIDUAL_RANKING (non-PLACEMENT): ASC or DESC required
        - PLACEMENT: NULL (not applicable)
        - HEAD_TO_HEAD: DESC (fixed)
        """
        format_val = values.get('format', 'HEAD_TO_HEAD')
        scoring_type = values.get('scoring_type', 'PLACEMENT')

        # HEAD_TO_HEAD: Always DESC
        if format_val == "HEAD_TO_HEAD":
            return "DESC"

        # PLACEMENT: NULL
        if scoring_type == "PLACEMENT":
            return None

        # INDIVIDUAL_RANKING (non-PLACEMENT): ASC or DESC required
        if format_val == "INDIVIDUAL_RANKING" and scoring_type != "PLACEMENT":
            if v is None:
                raise ValueError(
                    f"{scoring_type} requires a ranking_direction. "
                    "Valid options: ASC (lowest wins), DESC (highest wins)"
                )
            if v not in ['ASC', 'DESC']:
                raise ValueError(
                    f"Invalid ranking_direction '{v}'. "
                    "Valid options: ASC (lowest wins), DESC (highest wins)"
                )

        return v

    @validator('tournament_type_id')
    def validate_format_and_type_consistency(cls, v, values):
        """
        Validate format and tournament_type_id consistency:
        - INDIVIDUAL_RANKING: tournament_type_id MUST be None
        - HEAD_TO_HEAD: tournament_type_id MUST be set
        """
        format_val = values.get('format', 'HEAD_TO_HEAD')

        if format_val == "INDIVIDUAL_RANKING":
            if v is not None:
                raise ValueError(
                    "INDIVIDUAL_RANKING tournaments cannot have a tournament_type. "
                    "Set tournament_type_id to null."
                )
        elif format_val == "HEAD_TO_HEAD":
            if v is None:
                raise ValueError(
                    "HEAD_TO_HEAD tournaments MUST have a tournament_type (Swiss, League, Knockout, etc.). "
                    "Please select a tournament type."
                )
        return v

    @validator('instructor_id')
    def validate_instructor_at_creation(cls, v, values):
        """
        BUSINESS LOGIC: instructor_id is ALWAYS None at tournament creation

        Instructor assignment happens AFTER creation via Tournament Management:
        - OPEN_ASSIGNMENT: Admin invites specific instructor (invitation flow)
        - APPLICATION_BASED: Instructors apply, admin selects one
        """
        if v is not None:
            raise ValueError(
                'instructor_id must be None at tournament creation. '
                'Instructor assignment happens AFTER creation via Tournament Management.'
            )
        return v

    @validator('max_players')
    def validate_capacity_vs_sessions(cls, v, values):
        """Validate that session capacities do not exceed max_players"""
        sessions = values.get('sessions', [])
        if sessions:
            total_session_capacity = sum(s.capacity for s in sessions)
            if total_session_capacity > v:
                raise ValueError(
                    f'Total session capacity ({total_session_capacity}) exceeds max_players ({v}). '
                    f'Either increase max_players or reduce session capacities.'
                )
        return v


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
    tournament_status: Optional[str] = None  # ✅ Tournament completion status (DRAFT, IN_PROGRESS, COMPLETED)
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
    rankings_count: int = 0  # ✅ Count of tournament_rankings entries
    game_preset_id: Optional[int] = None
    game_preset_name: Optional[str] = None
    skills_config: Optional[dict] = None  # {skill_name: weight, ...} from tournament_skill_mappings


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/admin/list", response_model=List[dict])
def list_tournaments_admin(
    status_filter: Optional[str] = None,
    tournament_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all tournaments for admin monitoring.

    **Authorization:** Admin only.

    Query params:
    - `status_filter`: optional tournament_status filter (e.g. "IN_PROGRESS", "DRAFT")
    - `tournament_id`:  optional single-tournament filter (returns list of 1)
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

    from app.models.semester import Semester

    query = db.query(Semester).filter(Semester.tournament_status.isnot(None))

    if tournament_id is not None:
        query = query.filter(Semester.id == tournament_id)
    elif status_filter:
        query = query.filter(Semester.tournament_status == status_filter)

    tournaments = query.order_by(Semester.id.desc()).all()

    from app.models.semester_enrollment import SemesterEnrollment
    from app.models.session import Session as _SessionModel
    from sqlalchemy import func

    t_ids = [t.id for t in tournaments]

    # Batch-count enrollments (avoids N+1)
    counts = {}
    if t_ids:
        rows = (
            db.query(SemesterEnrollment.semester_id, func.count(SemesterEnrollment.id))
            .filter(SemesterEnrollment.semester_id.in_(t_ids))
            .group_by(SemesterEnrollment.semester_id)
            .all()
        )
        counts = {row[0]: row[1] for row in rows}

    # Batch-count tournament sessions (for STUCK detection: IN_PROGRESS + 0 sessions)
    session_counts = {}
    if t_ids:
        s_rows = (
            db.query(_SessionModel.semester_id, func.count(_SessionModel.id))
            .filter(
                _SessionModel.semester_id.in_(t_ids),
                _SessionModel.is_tournament_game == True,
            )
            .group_by(_SessionModel.semester_id)
            .all()
        )
        session_counts = {row[0]: row[1] for row in s_rows}

    result = []
    for t in tournaments:
        enrolled_count = counts.get(t.id, 0)
        t_status = t.tournament_status or (t.status.value if t.status else "UNKNOWN")
        sc = session_counts.get(t.id, 0)
        # Derive source from code prefix: OPS-* = ops wizard, TOURN-* = manual form
        code = t.code or ""
        source = "ops" if code.startswith("OPS-") else "manual"
        result.append({
            "id":                  t.id,
            "tournament_id":       t.id,
            "code":                code,
            "name":                t.name,
            "status":              t_status,
            "tournament_status":   t_status,
            "enrolled_count":      enrolled_count,
            "participant_count":   enrolled_count,
            "session_count":       sc,
            "source":              source,
            "start_date":          str(t.start_date) if t.start_date else None,
            "end_date":            str(t.end_date) if t.end_date else None,
            "specialization_type": t.specialization_type,
        })

    return result


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

    # Create tournament semester with explicit business attributes
    try:
        print(f"🔍 DEBUG: Creating tournament semester...")
        print(f"🔍 DEBUG: reward_policy_name = {request.reward_policy_name}")
        print(f"🔍 DEBUG: custom_reward_policy = {request.custom_reward_policy}")

        semester = TournamentService.create_tournament_semester(
            db=db,
            tournament_date=tournament_date,
            name=request.name,
            specialization_type=request.specialization_type,
            campus_id=request.campus_id,  # ✅ NEW: Campus support
            location_id=request.location_id,
            age_group=request.age_group,
            reward_policy_name=request.reward_policy_name,
            custom_reward_policy=request.custom_reward_policy,  # ✅ NEW: Custom reward policy support
            # 🎯 NEW: Explicit business attributes (DOMAIN GAP RESOLUTION)
            assignment_type=request.assignment_type,
            max_players=request.max_players,
            enrollment_cost=request.enrollment_cost,
            instructor_id=request.instructor_id,
            tournament_type_id=request.tournament_type_id,  # ✅ ONLY for HEAD_TO_HEAD
            format=request.format,  # ✅ NEW: Tournament format
            scoring_type=request.scoring_type,  # ✅ NEW: Scoring type for INDIVIDUAL_RANKING
            measurement_unit=request.measurement_unit,  # ✅ NEW: Measurement unit for INDIVIDUAL_RANKING
            ranking_direction=request.ranking_direction,  # ✅ NEW: Ranking direction (ASC/DESC)
            game_preset_id=request.game_preset_id  # ✅ NEW: Game preset reference
        )

        print(f"🔍 DEBUG: Tournament semester created successfully: {semester.id}")
    except Exception as e:
        print(f"❌ ERROR in create_tournament_semester: {type(e).__name__}")
        print(f"❌ ERROR message: {str(e)}")
        import traceback
        print(f"❌ ERROR traceback:\n{traceback.format_exc()}")
        raise

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

    # TICKET-UI-01: Extend response with seeding metrics post-generation
    # Add to TournamentSummaryResponse (and get_tournament_summary service):
    #   seeded_count    : int | None  — number of players in the bracket pool
    #   checked_in_count: int | None  — confirmed check-ins at generation time
    #   pool_label      : str | None  — "check-in confirmed" | "fallback: all approved"
    # These fields are available in session_generator.py after generate_sessions() runs.
    # Consumer: Tournament Monitor header (Enrolled / Confirmed / Seeded display).
    # Priority: UX improvement, not a correctness fix. Does NOT block current release.
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


# ============================================================================
# OPS SCENARIO ENDPOINT
# ============================================================================

_OPS_CONFIRM_THRESHOLD = 128  # player_count >= this requires confirmed=True


class OpsScenarioRequest(BaseModel):
    """Request to trigger an ops scenario (admin-only)."""
    scenario: Literal["large_field_monitor", "smoke_test", "scale_test"] = Field(
        ...,
        description="Scenario to run: 'large_field_monitor', 'smoke_test', or 'scale_test'."
    )
    player_count: int = Field(
        default=1024,
        ge=2,
        le=1024,
        description="Number of players to seed + enroll (2–1024).",
    )
    tournament_type_code: Optional[str] = Field(
        "knockout",
        description="Tournament type code: 'knockout', 'league', or 'group_knockout'. Only used for HEAD_TO_HEAD format.",
    )
    tournament_format: Literal["HEAD_TO_HEAD", "INDIVIDUAL_RANKING"] = Field(
        "HEAD_TO_HEAD",
        description="Tournament format: HEAD_TO_HEAD (1v1 matches) or INDIVIDUAL_RANKING (all compete, ranked by result).",
    )
    scoring_type: Optional[str] = Field(
        None,
        description="Scoring type for INDIVIDUAL_RANKING: TIME_BASED, SCORE_BASED, DISTANCE_BASED, PLACEMENT. Ignored for HEAD_TO_HEAD.",
    )
    ranking_direction: Optional[str] = Field(
        None,
        description="Ranking direction for INDIVIDUAL_RANKING: ASC (lowest wins), DESC (highest wins). Ignored for HEAD_TO_HEAD.",
    )
    tournament_name: Optional[str] = Field(
        None,
        description="Tournament name. Auto-generated as 'Ops-<scenario>-<timestamp>' if omitted.",
    )
    dry_run: bool = Field(
        False,
        description="If True, validate inputs and return without creating any DB records.",
    )
    confirmed: bool = Field(
        False,
        description=(
            "Safety gate for large-scale operations. "
            f"Must be True when player_count >= {_OPS_CONFIRM_THRESHOLD}."
        ),
    )
    simulation_mode: Literal["manual", "auto_immediate", "accelerated"] = Field(
        "accelerated",
        description=(
            "Controls result auto-simulation: "
            "'manual' — sessions created, no auto-simulation (observe live); "
            "'auto_immediate' — results simulated but lifecycle not completed; "
            "'accelerated' — full lifecycle completed synchronously (default)."
        ),
    )
    game_preset_id: Optional[int] = Field(
        None,
        description=(
            "Game preset ID (e.g., GānFootvolley=1). When provided, skills and game config "
            "are auto-synced from the preset. Overrides the default hardcoded skill list."
        ),
    )
    reward_config: Optional[Dict] = Field(
        None,
        description=(
            "Reward config override in the format: "
            "{'first_place': {'xp': N, 'credits': N}, 'second_place': {...}, "
            "'third_place': {...}, 'participation': {'xp': N, 'credits': 0}}. "
            "If omitted, the OPS default policy is used."
        ),
    )
    number_of_rounds: Optional[int] = Field(
        None,
        ge=1,
        le=20,
        description=(
            "Number of rounds for INDIVIDUAL_RANKING tournaments (1–20). "
            "Defaults to 1 if omitted."
        ),
    )
    player_ids: Optional[List[int]] = Field(
        None,
        description=(
            "Explicit list of user IDs to enroll. When provided, overrides player_count "
            "and skips the @lfa-seed.hu pool lookup — any active users can be selected. "
            "player_count is ignored when player_ids is set."
        ),
    )


class OpsScenarioResponse(BaseModel):
    """Response from an ops scenario trigger."""
    triggered: bool
    scenario: str
    tournament_id: Optional[int] = None
    tournament_name: Optional[str] = None
    task_id: Optional[str] = None
    enrolled_count: Optional[int] = None
    session_count: Optional[int] = None
    dry_run: bool
    audit_log_id: Optional[int] = None
    message: str


import logging as _logging
import json as _json
_ops_logger = _logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private simulation helpers
# ---------------------------------------------------------------------------

def _get_tournament_sessions(
    db,
    tournament_id: int,
    ordered: bool = False,
    with_phase: bool = False,
):
    """Fetch all is_tournament_game sessions for a tournament.

    Consolidates the repeated:
        db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.is_tournament_game == True,
        ).order_by(...).all()
    pattern used across every simulation function.

    Args:
        db:            SQLAlchemy session.
        tournament_id: Semester / tournament primary key.
        ordered:       Sort by (tournament_round ASC, tournament_match_number ASC).
        with_phase:    Sort by (tournament_phase, round ASC, match_number ASC).
                       Takes precedence over ``ordered``.

    Returns:
        List of SessionModel instances.
    """
    from app.models.session import Session as _SM
    from sqlalchemy import asc as _asc
    q = db.query(_SM).filter(
        _SM.semester_id == tournament_id,
        _SM.is_tournament_game == True,
    )
    if with_phase:
        q = q.order_by(_SM.tournament_phase, _asc(_SM.tournament_round), _asc(_SM.tournament_match_number))
    elif ordered:
        q = q.order_by(_asc(_SM.tournament_round), _asc(_SM.tournament_match_number))
    return q.all()


def _build_h2h_game_results(
    participants: list,
    round_number: int,
) -> str:
    """Serialise a HEAD_TO_HEAD game_results dict to JSON.

    Consolidates the repeated:
        {"match_format": "HEAD_TO_HEAD", "round_number": ..., "participants": [...]}
    pattern used in every simulation function.

    Args:
        participants:  List of participant dicts, each with keys
                       ``user_id``, ``result`` ("win"/"loss"), ``score`` (int).
        round_number:  Tournament round (used by ranking strategies for bracket ordering).

    Returns:
        JSON string ready to assign to ``session.game_results``.
    """
    return _json.dumps({
        "match_format": "HEAD_TO_HEAD",
        "round_number": round_number,
        "participants": participants,
    })


def _calculate_ir_rankings(tournament, sessions: list, logger: _logging.Logger) -> list:
    """Calculate INDIVIDUAL_RANKING rankings using RankingAggregator.

    Aggregates per-round results across all sessions for the tournament,
    then ranks players by their final value (direction-aware: ASC for time, DESC for score).

    Returns:
        List of ranking dicts: [{"user_id": int, "rank": int, "final_value": float}]
        Empty list if no round results are found.
    """
    from app.services.tournament.results.calculators.ranking_aggregator import RankingAggregator

    _combined_rr: dict = {}
    for _s in sessions:
        _rd = _s.rounds_data or {}
        _rr = _rd.get("round_results", {})
        if isinstance(_rr, dict):
            for _rk, _pv in _rr.items():
                if isinstance(_pv, dict):
                    _combined_rr[_rk] = _pv

    _ranking_direction = "ASC"
    if tournament.tournament_config_obj:
        _ranking_direction = tournament.tournament_config_obj.ranking_direction or "ASC"

    logger.info(
        "[ops] INDIVIDUAL_RANKING aggregator: direction=%s, rounds=%d",
        _ranking_direction,
        len(_combined_rr),
    )
    if _combined_rr:
        _user_finals = RankingAggregator.aggregate_user_values(_combined_rr, _ranking_direction)
        return RankingAggregator.calculate_performance_rankings(_user_finals, _ranking_direction)
    return []


def _finalize_tournament_with_rewards(tid: int, db, logger: _logging.Logger) -> None:
    """Run TournamentFinalizer to advance tournament COMPLETED → REWARDS_DISTRIBUTED.

    Non-fatal: any exception is logged and the DB transaction is rolled back.
    """
    try:
        from app.models.semester import Semester as _Semester
        from app.services.tournament.results.finalization.tournament_finalizer import TournamentFinalizer
        _t = db.query(_Semester).filter(_Semester.id == tid).first()
        if _t:
            finalizer = TournamentFinalizer(db)
            fin_result = finalizer.finalize(_t)
            if fin_result.get("success"):
                logger.info(
                    "[ops] Tournament lifecycle complete: status=%s — %s",
                    fin_result.get("tournament_status"),
                    fin_result.get("rewards_message", "no rewards message"),
                )
            else:
                logger.warning(
                    "[ops] Tournament finalization returned non-success: %s",
                    fin_result.get("message"),
                )
    except Exception as fin_exc:
        import traceback
        logger.warning("[ops] Tournament finalization failed (non-fatal): %s", fin_exc)
        logger.warning("[ops] Finalization traceback:\n%s", traceback.format_exc())
        try:
            db.rollback()
        except Exception:
            pass


def _simulate_tournament_results(
    db: Session,
    tournament_id: int,
    logger: _logging.Logger,
) -> tuple[bool, str]:
    """
    Simulate tournament results for OPS-generated tournaments.

    Supports:
    - HEAD_TO_HEAD knockout: Full bracket advancement logic
    - HEAD_TO_HEAD group+knockout: Group stage → Knockout stage progression
    - HEAD_TO_HEAD league: Round robin (all play all)
    - INDIVIDUAL_RANKING: Random performance data (time/score/rounds based on scoring_type)

    Returns:
        (success: bool, message: str)
    """
    import random
    import json
    from app.models.session import Session as SessionModel
    from app.models.semester import Semester as TournamentModel
    from app.models.tournament_enums import TournamentPhase
    from sqlalchemy import asc

    # Detect tournament format and phases
    tournament = db.query(TournamentModel).filter(TournamentModel.id == tournament_id).first()
    if not tournament:
        return False, "Tournament not found"

    # Get tournament format (derived from tournament_type)
    tournament_format = tournament.format if tournament.format else "INDIVIDUAL_RANKING"

    # Check if tournament has multiple phases (GROUP_STAGE + KNOCKOUT)
    sessions = _get_tournament_sessions(db, tournament_id)

    phases_present = set([s.tournament_phase for s in sessions if s.tournament_phase])
    has_group_stage = TournamentPhase.GROUP_STAGE in phases_present or TournamentPhase.GROUP_STAGE.value in phases_present
    has_knockout = TournamentPhase.KNOCKOUT in phases_present or TournamentPhase.KNOCKOUT.value in phases_present

    logger.info("[ops] Starting auto-result simulation for tournament_id=%d, format=%s, phases=%s",
                tournament_id, tournament_format, phases_present)

    # Route to appropriate simulation based on format and phases
    if tournament_format == "HEAD_TO_HEAD":
        if has_group_stage and has_knockout:
            # Group + Knockout hybrid
            return _simulate_group_knockout_tournament(db, tournament_id, logger)
        elif has_group_stage:
            # League (round robin)
            return _simulate_league_tournament(db, tournament_id, logger)
        else:
            # Pure knockout
            return _simulate_head_to_head_knockout(db, tournament_id, logger)
    elif tournament_format == "INDIVIDUAL_RANKING":
        return _simulate_individual_ranking(db, tournament, logger)
    else:
        return False, f"Unsupported tournament format: {tournament_format}"


def _simulate_head_to_head_knockout(
    db: Session,
    tournament_id: int,
    logger: _logging.Logger,
) -> tuple[bool, str]:
    """
    Simulate HEAD_TO_HEAD knockout tournament with full bracket advancement.

    1. Process sessions round-by-round (Semi-finals → Final/3rd Place)
    2. For each session: randomly select a winner, populate game_results
    3. Advance winners/losers to next round sessions (update participant_user_ids)
    4. Continue until all rounds are simulated

    Returns:
        (success: bool, message: str)
    """
    import random
    import json
    from app.models.session import Session as SessionModel
    from sqlalchemy import asc

    logger.info("[ops] Starting HEAD_TO_HEAD knockout bracket simulation for tournament_id=%d", tournament_id)

    # Get all tournament sessions, ordered by tournament_round
    sessions = _get_tournament_sessions(db, tournament_id, ordered=True)

    if not sessions:
        return False, "No tournament sessions found for simulation"

    # Group sessions by round
    from collections import defaultdict
    rounds = defaultdict(list)
    for session in sessions:
        round_num = session.tournament_round or 1
        rounds[round_num].append(session)

    total_simulated = 0
    total_skipped = 0

    # Process rounds in order
    for round_num in sorted(rounds.keys()):
        round_sessions = rounds[round_num]
        logger.info("[ops] Processing Round %d (%d sessions)", round_num, len(round_sessions))

        round_simulated = 0
        round_winners = []
        round_losers = []

        for session in round_sessions:
            # Skip if already has results
            if session.game_results:
                total_skipped += 1
                continue

            # Skip if no participants assigned
            if not session.participant_user_ids or len(session.participant_user_ids) == 0:
                total_skipped += 1
                logger.warning("[ops] Session %d (Round %d, Match %d) has no participants — skipping",
                              session.id, session.tournament_round, session.tournament_match_number)
                continue

            # Knockout sessions have exactly 2 participants
            if len(session.participant_user_ids) != 2:
                total_skipped += 1
                logger.warning("[ops] Session %d has %d participants (expected 2) — skipping",
                              session.id, len(session.participant_user_ids))
                continue

            # Simulate: randomly pick a winner
            winner_id = random.choice(session.participant_user_ids)
            loser_id = [uid for uid in session.participant_user_ids if uid != winner_id][0]

            # Update session
            session.game_results = _build_h2h_game_results(
                [{"user_id": winner_id, "result": "win", "score": 3},
                 {"user_id": loser_id, "result": "loss", "score": 0}],
                session.tournament_round,
            )
            session.session_status = "completed"
            round_simulated += 1

            # Track winners and losers for bracket advancement
            round_winners.append(winner_id)
            round_losers.append(loser_id)

            logger.info("[ops] Round %d, Match %d: User %d defeats User %d",
                       round_num, session.tournament_match_number, winner_id, loser_id)

        # Commit after each round
        db.commit()
        total_simulated += round_simulated
        logger.info("[ops] Round %d complete: %d sessions simulated", round_num, round_simulated)

        # Bracket advancement: assign winners/losers to next round sessions
        next_round = round_num + 1
        if next_round in rounds:
            next_round_sessions = sorted(rounds[next_round], key=lambda s: s.tournament_match_number or 0)

            # Separate playoff (3rd place) sessions from main bracket sessions
            main_sessions = [s for s in next_round_sessions
                             if "3rd Place" not in (s.title or "") and "Playoff" not in (s.title or "")]
            playoff_sessions = [s for s in next_round_sessions
                                if "3rd Place" in (s.title or "") or "Playoff" in (s.title or "")]

            # General bracket pairing: pair winners into main bracket sessions (2 per session)
            for idx, ns in enumerate(main_sessions):
                p1_idx = idx * 2
                p2_idx = idx * 2 + 1
                if p1_idx < len(round_winners) and p2_idx < len(round_winners):
                    ns.participant_user_ids = [round_winners[p1_idx], round_winners[p2_idx]]
                    logger.info("[ops] Round %d→%d, Match %d: Assigned winners %s to session %d (%s)",
                               round_num, next_round, idx + 1,
                               ns.participant_user_ids, ns.id, ns.title)
                else:
                    logger.warning("[ops] Not enough winners (%d) to fill main session %d (slot %d-%d)",
                                   len(round_winners), ns.id, p1_idx, p2_idx)

            # Assign losers to 3rd Place Playoff (only if losers exist and there's a playoff session)
            if playoff_sessions and len(round_losers) >= 2:
                playoff_sessions[0].participant_user_ids = round_losers[:2]
                logger.info("[ops] Assigned losers %s to 3rd Place Playoff (session %d)",
                           round_losers[:2], playoff_sessions[0].id)

            db.commit()

    logger.info(
        "[ops] Bracket simulation complete: %d sessions simulated, %d skipped",
        total_simulated, total_skipped
    )

    return True, f"{total_simulated} sessions simulated, {total_skipped} skipped"


def _simulate_individual_ranking(
    db: Session,
    tournament,
    logger: _logging.Logger,
) -> tuple[bool, str]:
    """
    Simulate INDIVIDUAL_RANKING tournament results.

    Generates random performance data based on scoring_type:
    - TIME_BASED: Random times (lower is better)
    - SCORE_BASED: Random scores (higher is better)
    - ROUNDS_BASED: Random rounds completed (higher is better)

    Returns:
        (success: bool, message: str)
    """
    import random
    import json
    from app.models.session import Session as SessionModel

    tournament_id = tournament.id

    # Get scoring_type from tournament configuration
    scoring_type = None
    if tournament.tournament_config_obj:
        scoring_type = tournament.tournament_config_obj.scoring_type

    if not scoring_type:
        return False, "INDIVIDUAL_RANKING tournament missing scoring_type"

    logger.info("[ops] Starting INDIVIDUAL_RANKING simulation: scoring_type=%s", scoring_type)

    # Get all tournament sessions
    sessions = _get_tournament_sessions(db, tournament_id)

    if not sessions:
        return False, "No tournament sessions found"

    simulated_count = 0
    skipped_count = 0

    for session in sessions:
        # Skip if no participants
        if not session.participant_user_ids or len(session.participant_user_ids) == 0:
            skipped_count += 1
            continue

        participants = session.participant_user_ids
        is_rounds_based = session.scoring_type == "ROUNDS_BASED"

        if is_rounds_based:
            # Multi-round session: skip only if ALL rounds already done
            rd = session.rounds_data or {}
            total_r = int(rd.get("total_rounds", 1))
            completed_r = int(rd.get("completed_rounds", 0))
            if completed_r >= total_r > 0:
                skipped_count += 1
                continue

            # Simulate each missing round using the underlying scoring type
            underlying = (session.structure_config or {}).get("scoring_method") or scoring_type
            new_rd = dict(rd)
            if "round_results" not in new_rd:
                new_rd["round_results"] = {}

            for rn in range(completed_r + 1, total_r + 1):
                rn_key = str(rn)
                if rn_key in new_rd["round_results"]:
                    continue  # already submitted
                round_entry = {}
                for user_id in participants:
                    if "TIME" in underlying:
                        val = f"{round(random.uniform(30.0, 120.0), 2)}"
                    elif "DISTANCE" in underlying:
                        val = f"{round(random.uniform(1.0, 50.0), 2)}"
                    else:
                        val = f"{random.randint(50, 100)}"
                    round_entry[str(user_id)] = val
                new_rd["round_results"][rn_key] = round_entry

            new_rd["completed_rounds"] = total_r
            session.rounds_data = new_rd
            from sqlalchemy.orm.attributes import flag_modified as _fm
            _fm(session, "rounds_data")

        else:
            # Single-round session: skip if already has results
            if session.game_results:
                skipped_count += 1
                continue

            round_results = []
            if scoring_type == "TIME_BASED":
                for user_id in participants:
                    round_results.append({
                        "user_id": user_id,
                        "measured_value": round(random.uniform(30.0, 120.0), 2),
                    })
            elif scoring_type == "SCORE_BASED":
                for user_id in participants:
                    round_results.append({
                        "user_id": user_id,
                        "measured_value": float(random.randint(50, 100)),
                    })
            elif scoring_type == "DISTANCE_BASED":
                for user_id in participants:
                    round_results.append({
                        "user_id": user_id,
                        "measured_value": round(random.uniform(1.0, 50.0), 2),
                    })
            else:
                logger.warning("[ops] Unsupported scoring_type: %s, skipping session %d",
                               scoring_type, session.id)
                skipped_count += 1
                continue

            # Use the same ResultProcessor that the manual submit endpoint uses
            try:
                from app.services.tournament.result_processor import ResultProcessor
                processor = ResultProcessor(db)
                processor.process_match_results(
                    db=db,
                    session=session,
                    tournament=tournament,
                    raw_results=round_results,
                    match_notes="OPS auto-simulated",
                    recorded_by_user_id=0,
                    recorded_by_name="OPS",
                )
            except Exception as _e:
                logger.warning("[ops] process_match_results failed for session %d: %s", session.id, _e)
                skipped_count += 1
                continue

        simulated_count += 1

    db.commit()

    logger.info(
        "[ops] INDIVIDUAL_RANKING simulation complete: %d sessions simulated, %d skipped",
        simulated_count, skipped_count
    )

    return True, f"{simulated_count} sessions simulated ({scoring_type}), {skipped_count} skipped"


def _simulate_group_knockout_tournament(
    db: Session,
    tournament_id: int,
    logger: _logging.Logger,
) -> tuple[bool, str]:
    """
    Simulate GROUP_STAGE + KNOCKOUT tournament:
    1. Simulate all group stage sessions (HEAD_TO_HEAD matches within groups)
    2. Calculate group standings (wins, goal difference, etc.)
    3. Determine qualifiers (top N from each group)
    4. Assign qualifiers to knockout bracket sessions
    5. Simulate knockout stage (winners advance to next round)

    Returns:
        (success: bool, message: str)
    """
    import random
    import json
    from app.models.session import Session as SessionModel
    from app.models.tournament_enums import TournamentPhase
    from sqlalchemy import asc
    from collections import defaultdict

    logger.info("[ops] Starting GROUP + KNOCKOUT simulation for tournament_id=%d", tournament_id)

    # Get all tournament sessions, ordered by phase, round, match
    sessions = _get_tournament_sessions(db, tournament_id, with_phase=True)

    if not sessions:
        return False, "No tournament sessions found for simulation"

    # Separate sessions by phase
    group_sessions = [s for s in sessions if s.tournament_phase == TournamentPhase.GROUP_STAGE.value]
    knockout_sessions = [s for s in sessions if s.tournament_phase == TournamentPhase.KNOCKOUT.value]

    logger.info("[ops] Found %d group sessions, %d knockout sessions", len(group_sessions), len(knockout_sessions))

    # ============================================================================
    # PHASE 1: Simulate Group Stage
    # ============================================================================
    group_simulated = 0
    group_skipped = 0

    # Track group standings: {group_identifier: {user_id: {wins, losses, draws, gf, ga, points}}}
    group_standings = defaultdict(lambda: defaultdict(lambda: {
        "wins": 0, "losses": 0, "draws": 0, "goals_for": 0, "goals_against": 0, "points": 0
    }))

    for session in group_sessions:
        # Skip if already has results
        if session.game_results:
            group_skipped += 1
            continue

        # Verify session has participants
        if not session.participant_user_ids or len(session.participant_user_ids) < 2:
            logger.warning("[ops] Group session %d has no participants, skipping", session.id)
            group_skipped += 1
            continue

        # Simulate HEAD_TO_HEAD match (1v1)
        user_id_1, user_id_2 = session.participant_user_ids[0], session.participant_user_ids[1]

        # Random match result: win, loss, or draw
        outcome = random.choice(["win", "draw", "win"])  # Bias towards decisive results

        if outcome == "draw":
            score_1 = random.randint(0, 3)
            score_2 = score_1  # Equal scores for draw
            result_1 = "draw"
            result_2 = "draw"
        else:
            # Winner gets higher score
            winner_score = random.randint(1, 5)
            loser_score = random.randint(0, winner_score - 1)

            if random.choice([True, False]):  # Randomly assign winner
                score_1 = winner_score
                score_2 = loser_score
                result_1 = "win"
                result_2 = "loss"
            else:
                score_1 = loser_score
                score_2 = winner_score
                result_1 = "loss"
                result_2 = "win"

        session.game_results = _build_h2h_game_results(
            [{"user_id": user_id_1, "result": result_1, "score": score_1},
             {"user_id": user_id_2, "result": result_2, "score": score_2}],
            session.tournament_round or 1,
        )
        session.session_status = "completed"

        # Update group standings
        group_id = session.group_identifier or "A"

        # Update user_1 stats
        group_standings[group_id][user_id_1]["goals_for"] += score_1
        group_standings[group_id][user_id_1]["goals_against"] += score_2
        if result_1 == "win":
            group_standings[group_id][user_id_1]["wins"] += 1
            group_standings[group_id][user_id_1]["points"] += 3
        elif result_1 == "draw":
            group_standings[group_id][user_id_1]["draws"] += 1
            group_standings[group_id][user_id_1]["points"] += 1
        else:
            group_standings[group_id][user_id_1]["losses"] += 1

        # Update user_2 stats
        group_standings[group_id][user_id_2]["goals_for"] += score_2
        group_standings[group_id][user_id_2]["goals_against"] += score_1
        if result_2 == "win":
            group_standings[group_id][user_id_2]["wins"] += 1
            group_standings[group_id][user_id_2]["points"] += 3
        elif result_2 == "draw":
            group_standings[group_id][user_id_2]["draws"] += 1
            group_standings[group_id][user_id_2]["points"] += 1
        else:
            group_standings[group_id][user_id_2]["losses"] += 1

        group_simulated += 1

    db.commit()

    logger.info("[ops] Group stage simulation: %d sessions simulated, %d skipped", group_simulated, group_skipped)

    # ============================================================================
    # PHASE 2: Calculate Group Qualifiers
    # ============================================================================
    # Sort each group by: points DESC, goal_diff DESC, goals_for DESC
    group_qualifiers = {}  # {group_id: [user_id_rank1, user_id_rank2, ...]}

    for group_id, standings in group_standings.items():
        # Convert to list of (user_id, stats)
        standings_list = [(user_id, stats) for user_id, stats in standings.items()]

        # Sort by: points DESC, goal_diff DESC, goals_for DESC
        standings_list.sort(
            key=lambda x: (
                -x[1]["points"],
                -(x[1]["goals_for"] - x[1]["goals_against"]),  # goal difference
                -x[1]["goals_for"],
                x[0]  # user_id as tiebreaker (stable sort)
            )
        )

        # Extract top qualifiers (typically top 2 from each group)
        group_qualifiers[group_id] = [user_id for user_id, _ in standings_list]

        logger.info("[ops] Group %s standings: %s", group_id,
                   [(uid, stats["points"], stats["goals_for"] - stats["goals_against"])
                    for uid, stats in standings_list])

    # ============================================================================
    # PHASE 3: Assign Qualifiers to Knockout Bracket
    # ============================================================================
    # Determine seeding order: A1, B1, C1, D1, A2, B2, C2, D2, ...
    # For standard group_knockout: top 2 from each group qualify
    # Seeding: Winners from each group first, then runners-up

    group_ids_sorted = sorted(group_qualifiers.keys())  # ['A', 'B', 'C', 'D', ...]
    qualifiers_per_group = 2  # Standard config

    # Build seeded list: [A1, B1, C1, D1, A2, B2, C2, D2]
    seeded_qualifiers = []
    for rank_index in range(qualifiers_per_group):
        for group_id in group_ids_sorted:
            if rank_index < len(group_qualifiers[group_id]):
                seeded_qualifiers.append(group_qualifiers[group_id][rank_index])

    logger.info("[ops] Seeded qualifiers for knockout: %s", seeded_qualifiers)

    # Assign qualifiers to first knockout round sessions
    # First round knockout sessions should have participant_user_ids = None (need assignment)
    first_round_sessions = [s for s in knockout_sessions if s.tournament_round == 1]

    # Standard bracket seeding: 1 vs N, 2 vs N-1, 3 vs N-2, etc.
    if len(seeded_qualifiers) != len(first_round_sessions) * 2:
        logger.warning("[ops] Seeded qualifiers count (%d) doesn't match first round sessions (%d * 2)",
                      len(seeded_qualifiers), len(first_round_sessions))

    # Assign participants to first round sessions using standard bracket seeding
    for i, session in enumerate(first_round_sessions):
        if i * 2 + 1 < len(seeded_qualifiers):
            # Standard seeding: 1v8, 2v7, 3v6, 4v5 for 8 players
            seed_high = i  # 0, 1, 2, 3
            seed_low = len(seeded_qualifiers) - 1 - i  # 7, 6, 5, 4

            session.participant_user_ids = [seeded_qualifiers[seed_high], seeded_qualifiers[seed_low]]

            logger.info("[ops] Assigned knockout R1 Match %d: Seed %d (user %d) vs Seed %d (user %d)",
                       i + 1, seed_high + 1, seeded_qualifiers[seed_high],
                       seed_low + 1, seeded_qualifiers[seed_low])

    db.commit()

    # ============================================================================
    # PHASE 4: Simulate Knockout Stage (same as pure knockout)
    # ============================================================================
    knockout_simulated, knockout_skipped = _simulate_knockout_bracket(
        db, knockout_sessions, logger
    )

    db.commit()

    total_simulated = group_simulated + knockout_simulated
    total_skipped = group_skipped + knockout_skipped

    logger.info(
        "[ops] GROUP+KNOCKOUT simulation complete: %d total sessions simulated, %d skipped",
        total_simulated, total_skipped
    )

    return True, f"{total_simulated} sessions simulated (group={group_simulated}, knockout={knockout_simulated}), {total_skipped} skipped"


def _simulate_league_tournament(
    db: Session,
    tournament_id: int,
    logger: _logging.Logger,
) -> tuple[bool, str]:
    """
    Simulate LEAGUE (Round Robin) tournament:
    - All players play against each other once
    - Each match is HEAD_TO_HEAD
    - Final rankings based on points, goal difference, goals scored

    Returns:
        (success: bool, message: str)
    """
    import random
    import json
    from app.models.session import Session as SessionModel
    from sqlalchemy import asc

    logger.info("[ops] Starting LEAGUE (Round Robin) simulation for tournament_id=%d", tournament_id)

    # Get all tournament sessions
    sessions = _get_tournament_sessions(db, tournament_id, ordered=True)

    if not sessions:
        return False, "No tournament sessions found for simulation"

    simulated_count = 0
    skipped_count = 0

    for session in sessions:
        # Skip if already has results
        if session.game_results:
            skipped_count += 1
            continue

        # Verify session has participants
        if not session.participant_user_ids or len(session.participant_user_ids) < 2:
            logger.warning("[ops] League session %d has no participants, skipping", session.id)
            skipped_count += 1
            continue

        # Simulate HEAD_TO_HEAD match (1v1)
        user_id_1, user_id_2 = session.participant_user_ids[0], session.participant_user_ids[1]

        # Random match result: win, loss, or draw
        outcome = random.choice(["win", "draw", "win"])  # Bias towards decisive results

        if outcome == "draw":
            score_1 = random.randint(0, 3)
            score_2 = score_1  # Equal scores for draw
            result_1 = "draw"
            result_2 = "draw"
        else:
            # Winner gets higher score
            winner_score = random.randint(1, 5)
            loser_score = random.randint(0, winner_score - 1)

            if random.choice([True, False]):  # Randomly assign winner
                score_1 = winner_score
                score_2 = loser_score
                result_1 = "win"
                result_2 = "loss"
            else:
                score_1 = loser_score
                score_2 = winner_score
                result_1 = "loss"
                result_2 = "win"

        session.game_results = _build_h2h_game_results(
            [{"user_id": user_id_1, "result": result_1, "score": score_1},
             {"user_id": user_id_2, "result": result_2, "score": score_2}],
            session.tournament_round or 1,
        )
        session.session_status = "completed"
        simulated_count += 1

    db.commit()

    logger.info(
        "[ops] LEAGUE simulation complete: %d sessions simulated, %d skipped",
        simulated_count, skipped_count
    )

    return True, f"{simulated_count} league sessions simulated, {skipped_count} skipped"


def _simulate_knockout_bracket(
    db: Session,
    knockout_sessions: list,
    logger: _logging.Logger,
) -> tuple[int, int]:
    """
    Helper: Simulate knockout bracket sessions round-by-round.
    Used by both pure knockout and group+knockout tournaments.

    Returns:
        (simulated_count, skipped_count)
    """
    import random
    import json
    from collections import defaultdict
    from sqlalchemy import asc

    # Group sessions by round
    rounds = defaultdict(list)
    for session in knockout_sessions:
        round_num = session.tournament_round or 1
        rounds[round_num].append(session)

    total_simulated = 0
    total_skipped = 0

    # Process rounds in order
    for round_num in sorted(rounds.keys()):
        round_sessions = rounds[round_num]
        logger.info("[ops] Processing Knockout Round %d (%d sessions)", round_num, len(round_sessions))

        round_winners = []
        round_losers = []

        for session in round_sessions:
            # Skip if already has results
            if session.game_results:
                total_skipped += 1
                continue

            # Skip if no participants yet (waiting for previous round)
            if not session.participant_user_ids or len(session.participant_user_ids) < 2:
                logger.info("[ops] Session %d has no participants yet (waiting for previous round), skipping", session.id)
                total_skipped += 1
                continue

            # Randomly select winner
            winner_id = random.choice(session.participant_user_ids)
            loser_id = [uid for uid in session.participant_user_ids if uid != winner_id][0]

            session.game_results = _build_h2h_game_results(
                [{"user_id": winner_id, "result": "win", "score": random.randint(1, 5)},
                 {"user_id": loser_id, "result": "loss", "score": random.randint(0, 3)}],
                session.tournament_round,
            )
            session.session_status = "completed"

            round_winners.append(winner_id)
            round_losers.append(loser_id)

            logger.info("[ops] Simulated knockout session %d: Winner=%d, Loser=%d",
                       session.id, winner_id, loser_id)

            total_simulated += 1

        # Bracket advancement: assign winners/losers to next round
        next_round = round_num + 1
        if next_round in rounds:
            next_round_sessions = rounds[next_round]

            # General bracket pairing: separate playoff from main bracket
            next_round_sessions_sorted = sorted(next_round_sessions, key=lambda s: s.tournament_match_number or 0)
            main_sessions = [s for s in next_round_sessions_sorted
                             if "3rd Place" not in (s.title or "") and "Playoff" not in (s.title or "")]
            playoff_sessions = [s for s in next_round_sessions_sorted
                                if "3rd Place" in (s.title or "") or "Playoff" in (s.title or "")]

            # Assign winners into main bracket sessions (2 per session, in order)
            for idx, ns in enumerate(main_sessions):
                p1_idx = idx * 2
                p2_idx = idx * 2 + 1
                if p1_idx < len(round_winners) and p2_idx < len(round_winners):
                    ns.participant_user_ids = [round_winners[p1_idx], round_winners[p2_idx]]
                    logger.info("[ops] Round %d→%d, Match %d: Assigned winners %s to session %d (%s)",
                               round_num, next_round, idx + 1,
                               ns.participant_user_ids, ns.id, ns.title)

            # Assign losers to 3rd Place Playoff
            if playoff_sessions and len(round_losers) >= 2:
                playoff_sessions[0].participant_user_ids = round_losers[:2]
                logger.info("[ops] Assigned 3rd Place Playoff participants: %s", round_losers[:2])

    return total_simulated, total_skipped


@router.post("/ops/run-scenario", response_model=OpsScenarioResponse)
def run_ops_scenario(
    request: OpsScenarioRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OpsScenarioResponse:
    """
    Trigger an admin ops scenario from the Tournament Monitor UI.

    **Authorization:** Admin only

    **Safety gate:** player_count >= 128 requires confirmed=True to prevent
    accidental large-scale data generation.

    **Scenario: large_field_monitor**
    1. Seeds N LFA_FOOTBALL_PLAYER users (skips existing ones)
    2. Creates a knockout tournament
    3. Batch-enrolls all N players
    4. Triggers session generation (async for N >= 128)

    The caller can poll `GET /tournaments/{id}/generation-status/{task_id}`
    to track progress.
    """
    import time as _time
    import uuid as _uuid
    from datetime import datetime as _dt, timedelta as _td

    # ── Auth ─────────────────────────────────────────────────────────────────
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can trigger ops scenarios",
        )

    # ── Dry-run: validate only, no DB writes (checked before safety gate) ───────
    if request.dry_run:
        return OpsScenarioResponse(
            triggered=False,
            scenario=request.scenario,
            dry_run=True,
            message=(
                f"dry_run: validation passed — "
                f"scenario={request.scenario}, player_count={request.player_count}, "
                f"confirmed={request.confirmed}"
            ),
        )

    # ── Effective player count ────────────────────────────────────────────────
    # player_count is always the TARGET (total including pinned + auto-fill).
    # player_ids are the PINNED subset; remaining slots are filled from seed pool.
    # Fallback to len(player_ids) only if player_count was not provided.
    _effective_count = request.player_count or (len(request.player_ids) if request.player_ids else 0)

    # ── Safety gate (only applies to real runs) ───────────────────────────────
    if _effective_count >= _OPS_CONFIRM_THRESHOLD and not request.confirmed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Large-scale operation ({_effective_count} players) requires confirmed=True. "
                "Set confirmed=True to proceed."
            ),
        )

    # ── Resolve tournament name ───────────────────────────────────────────────
    ts_label = _dt.utcnow().strftime("%Y%m%d-%H%M%S")
    if request.tournament_name:
        tournament_name = request.tournament_name
    elif _effective_count >= _OPS_CONFIRM_THRESHOLD:
        tournament_name = f"OPS-LF-{_effective_count}-{ts_label}"
    else:
        tournament_name = f"OPS-SMOKE-{_effective_count}-{ts_label}"

    # ── Step 1: Resolve player pool ───────────────────────────────────────────
    import uuid as _uuid
    from datetime import timezone as _tz
    from app.models.user import User as _User, UserRole as _UserRole
    from app.models.license import UserLicense
    from app.models.specialization import SpecializationType as _SpecType

    # Generate a run-specific short ID for logging purposes
    _run_id = _uuid.uuid4().hex[:8]  # e.g. "a3f2b1c0"

    if request.player_ids:
        # ── Manual / hybrid player selection ──────────────────────────────
        _ops_logger.info(
            "[ops] player_ids provided (%d) effective_count=%d scenario=%s admin=%s run_id=%s",
            len(request.player_ids), _effective_count, request.scenario, current_user.email, _run_id,
        )
        # 1. Validate the manually picked players
        valid_rows = (
            db.query(_User.id, _User.name, _User.email)
            .filter(
                _User.id.in_(request.player_ids),
                _User.is_active == True,
            )
            .order_by(_User.id)
            .all()
        )
        found_ids = {row.id for row in valid_rows}
        missing = [uid for uid in request.player_ids if uid not in found_ids]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"player_ids not found or inactive: {missing}",
            )
        manual_ids = [row.id for row in valid_rows]

        # 2. Hybrid fill: if target count > manual count, top-up from seed pool
        remaining = _effective_count - len(manual_ids)
        if remaining > 0:
            fill_rows = (
                db.query(_User.id)
                .join(UserLicense, UserLicense.user_id == _User.id)
                .filter(
                    _User.email.like("%@lfa-seed.hu"),
                    _User.is_active == True,
                    UserLicense.is_active == True,
                    ~_User.id.in_(set(manual_ids)),
                )
                .order_by(_User.id)
                .limit(remaining)
                .all()
            )
            if len(fill_rows) < remaining:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Hybrid fill: need {remaining} more seed players but only "
                        f"{len(fill_rows)} available. Reduce target count or add more seed users."
                    ),
                )
            seeded_ids = manual_ids + [r.id for r in fill_rows]
            _ops_logger.info(
                "[ops] Hybrid: %d manual + %d seed fill = %d total (run_id=%s)",
                len(manual_ids), remaining, len(seeded_ids), _run_id,
            )
        else:
            # Manual-only: exactly the picked players
            seeded_ids = manual_ids
            _ops_logger.info(
                "[ops] Manual-only: %d players (run_id=%s)", len(seeded_ids), _run_id,
            )
    else:
        # ── Auto mode: query @lfa-seed.hu pool ────────────────────────────
        _ops_logger.info(
            "[ops] Querying %d @lfa-seed.hu players for scenario=%s admin=%s run_id=%s",
            request.player_count, request.scenario, current_user.email, _run_id,
        )
        seed_rows = (
            db.query(_User.id, _User.name, _User.email)
            .join(UserLicense, UserLicense.user_id == _User.id)
            .filter(
                _User.email.like("%@lfa-seed.hu"),
                _User.is_active == True,
                UserLicense.is_active == True,
            )
            .order_by(_User.id)
            .all()
        )
        seed_user_ids = [row.id for row in seed_rows]

        if not seed_user_ids:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"No active @lfa-seed.hu users found with licenses. "
                    f"Run 'python scripts/seed_star_players.py' to create seed users first."
                ),
            )

        if request.player_count > len(seed_user_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot enroll {request.player_count} players: only {len(seed_user_ids)} "
                    f"@lfa-seed.hu seed users available. Increase seed user count or reduce player_count."
                ),
            )

        # ✅ DETERMINISTIC: Take first N players from ordered pool
        seeded_ids = seed_user_ids[:request.player_count]
        _ops_logger.info(
            "[ops] Using %d existing seed players (pool size: %d, run_id=%s)",
            len(seeded_ids), len(seed_user_ids), _run_id
        )
        _ops_logger.debug(
            "[ops] Sample seed users: %s",
            [(r.id, r.name, r.email) for r in seed_rows[:5]]
        )

    # ── Step 2: Create tournament ─────────────────────────────────────────────
    from app.models.semester import Semester as _Semester, SemesterStatus as _SemStatus
    from app.models.tournament_type import TournamentType as _TType
    from app.models.tournament_configuration import TournamentConfiguration as _TCfg
    from app.models.tournament_reward_config import TournamentRewardConfig as _TRwd
    from app.models.tournament_achievement import TournamentSkillMapping as _TSkill

    # ── Resolve tournament type (HEAD_TO_HEAD only) ───────────────────────────
    tt = None
    if request.tournament_format == "HEAD_TO_HEAD":
        tournament_type_code = request.tournament_type_code or "knockout"
        tt = db.query(_TType).filter(_TType.code == tournament_type_code).first()
        if not tt:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Tournament type '{tournament_type_code}' not found in DB. Run seed_tournament_types first.",
            )

    grandmaster = db.query(_User).filter(
        _User.role == _UserRole.INSTRUCTOR,
        _User.email == "grandmaster@lfa.com",
    ).first()

    tc_ts = _dt.now().strftime("%Y%m%d-%H%M%S")
    tournament = _Semester(
        code=f"OPS-{_run_id}-{tc_ts}",
        name=tournament_name,
        start_date=_dt.now().date(),
        end_date=(_dt.now() + _td(days=30)).date(),
        is_active=True,
        status=_SemStatus.ONGOING,        # lifecycle enum
        tournament_status="IN_PROGRESS",  # tournament-specific string field
        master_instructor_id=grandmaster.id if grandmaster else None,
        enrollment_cost=0,
    )
    db.add(tournament)
    db.flush()

    # Tournament configuration — format-aware
    if request.tournament_format == "HEAD_TO_HEAD":
        t_cfg = _TCfg(
            semester_id=tournament.id,
            tournament_type_id=tt.id,
            participant_type="INDIVIDUAL",
            is_multi_day=False,
            max_players=_effective_count,
            parallel_fields=1,
            scoring_type="HEAD_TO_HEAD",
            number_of_rounds=request.number_of_rounds or 1,
        )
    else:
        # INDIVIDUAL_RANKING: no tournament_type, use scoring_type from request
        _scoring = request.scoring_type or "PLACEMENT"
        t_cfg = _TCfg(
            semester_id=tournament.id,
            tournament_type_id=None,
            participant_type="INDIVIDUAL",
            is_multi_day=False,
            max_players=_effective_count,
            parallel_fields=1,
            scoring_type=_scoring,
            ranking_direction=request.ranking_direction,
            number_of_rounds=request.number_of_rounds or 1,
        )
    db.add(t_cfg)
    db.flush()

    # Reward config — use user-provided config or OPS default
    _reward_cfg = request.reward_config or {
        "first_place":   {"xp": 2000, "credits": 1000},
        "second_place":  {"xp": 1200, "credits": 500},
        "third_place":   {"xp": 800,  "credits": 250},
        "participation": {"xp": 100,  "credits": 0},
    }
    db.add(_TRwd(
        semester_id=tournament.id,
        reward_policy_name="custom",
        reward_config=_reward_cfg,
    ))

    # Skill mappings + game config — use preset if provided, else default list
    if request.game_preset_id:
        from app.models.game_preset import GamePreset as _GamePreset
        from app.models.game_configuration import GameConfiguration as _GameCfg
        _preset = db.query(_GamePreset).filter(
            _GamePreset.id == request.game_preset_id,
            _GamePreset.is_active == True,
        ).first()
        if _preset:
            db.add(_GameCfg(
                semester_id=tournament.id,
                game_preset_id=_preset.id,
                game_config=_preset.game_config,
            ))
            _avg_w = 1.0
            if _preset.skill_weights:
                _vals = list(_preset.skill_weights.values())
                _avg_w = sum(_vals) / len(_vals) if _vals else 1.0
            for _skill in (_preset.skills_tested or []):
                _frac = (_preset.skill_weights or {}).get(_skill, _avg_w)
                _react = round(_frac / _avg_w, 2) if _avg_w else 1.0
                _react = max(0.1, min(5.0, _react))
                db.add(_TSkill(semester_id=tournament.id, skill_name=_skill, weight=_react))
            _ops_logger.info(
                "[ops] Game preset '%s' applied: %d skills", _preset.code, len(_preset.skills_tested or [])
            )
        else:
            _ops_logger.warning("[ops] game_preset_id=%d not found, using default skills", request.game_preset_id)
            for skill in ["PASSING", "DRIBBLING", "FINISHING"]:
                db.add(_TSkill(semester_id=tournament.id, skill_name=skill, weight=1.0))
    else:
        for skill in ["PASSING", "DRIBBLING", "FINISHING"]:
            db.add(_TSkill(semester_id=tournament.id, skill_name=skill, weight=1.0))

    db.commit()
    tid = tournament.id
    _ops_logger.info("[ops] Tournament created: id=%d name=%r", tid, tournament_name)

    # ── Step 3: Batch-enroll players ─────────────────────────────────────────
    from app.models.semester_enrollment import SemesterEnrollment as _Enroll, EnrollmentStatus as _ES
    from app.models.license import UserLicense as _Lic

    enrolled_count = 0
    for player_id in seeded_ids:
        existing = db.query(_Enroll).filter(
            _Enroll.user_id == player_id,
            _Enroll.semester_id == tid,
            _Enroll.is_active == True,
        ).first()
        if existing:
            enrolled_count += 1
            continue
        lic = db.query(_Lic).filter(
            _Lic.user_id == player_id,
            _Lic.specialization_type == "LFA_FOOTBALL_PLAYER",
        ).first()
        if not lic:
            continue
        enroll = _Enroll(
            user_id=player_id,
            semester_id=tid,
            user_license_id=lic.id,
            age_category="PRO",
            request_status=_ES.APPROVED,
            approved_at=_dt.utcnow(),
            approved_by=current_user.id,
            payment_verified=True,
            is_active=True,
            enrolled_at=_dt.utcnow(),
            requested_at=_dt.utcnow(),
            # OPS scenarios bypass the real 15-min check-in window:
            # auto-confirm all players as checked-in at enrollment time
            tournament_checked_in_at=_dt.utcnow(),
        )
        db.add(enroll)
        enrolled_count += 1

    db.commit()
    _ops_logger.info("[ops] %d/%d players enrolled", enrolled_count, len(seeded_ids))

    # ── Step 4: Trigger session generation ───────────────────────────────────
    from app.api.api_v1.endpoints.tournaments.generate_sessions import (
        _is_celery_available,
        _run_generation_in_background,
        _task_registry,
        _registry_lock,
        BACKGROUND_GENERATION_THRESHOLD,
    )
    import threading as _threading

    # ✅ MULTI-CAMPUS SUPPORT: Query active physical campuses for distributed sessions
    # Use campuses with addresses (physical locations, not virtual)
    from app.models.campus import Campus as _Campus
    physical_campuses = db.query(_Campus.id).filter(
        _Campus.is_active == True,
        _Campus.address.isnot(None),  # Physical campuses have addresses
    ).order_by(_Campus.id).limit(8).all()
    campus_ids = [c.id for c in physical_campuses] if physical_campuses else []
    _ops_logger.info("[ops] Using %d physical campuses for distributed sessions: %s",
                     len(campus_ids), campus_ids)

    # Persist one CampusScheduleConfig row per physical campus so the monitor
    # UI can show named campus cards (1 field per campus in the display).
    # parallel_fields=None → falls back to the global value in session_generator,
    # so sessions are distributed across all campus-fields (field_numbers 1..N).
    if campus_ids:
        from app.models.campus_schedule_config import CampusScheduleConfig as _CSC
        for _cid in campus_ids:
            _existing = db.query(_CSC).filter_by(tournament_id=tid, campus_id=_cid).first()
            if not _existing:
                db.add(_CSC(
                    tournament_id=tid,
                    campus_id=_cid,
                    parallel_fields=None,   # NULL → resolved from global parallel_fields
                    is_active=True,
                ))
        db.flush()

    campus_overrides_raw = None
    # 1 field per physical campus — distributes sessions across campus-field slots.
    # Without this, every session lands on field_number=1 regardless of campus count.
    parallel_fields = len(campus_ids) if campus_ids else 1
    session_duration = 90
    break_duration = 15
    # INDIVIDUAL_RANKING: use requested rounds (default 1)
    # HEAD_TO_HEAD knockout: 10 rounds supports up to 1024 players (log2(1024)=10)
    if request.tournament_format == "INDIVIDUAL_RANKING":
        number_of_rounds = request.number_of_rounds or 1
    else:
        number_of_rounds = 10

    task_id: Optional[str] = None

    if request.player_count >= BACKGROUND_GENERATION_THRESHOLD:
        if _is_celery_available():
            from app.tasks.tournament_tasks import generate_sessions_task
            celery_result = generate_sessions_task.apply_async(
                args=[tid, parallel_fields, session_duration, break_duration,
                      number_of_rounds, campus_overrides_raw, campus_ids],
                queue="tournaments",
                headers={"dispatched_at": _time.perf_counter()},
            )
            task_id = celery_result.id
            _ops_logger.info("[ops] Celery task dispatched task_id=%s", task_id)
        else:
            task_id = str(_uuid.uuid4())
            with _registry_lock:
                _task_registry[task_id] = {
                    "status": "pending",
                    "tournament_id": tid,
                    "player_count": request.player_count,
                    "message": None,
                    "sessions_count": 0,
                }
            _threading.Thread(
                target=_run_generation_in_background,
                args=(task_id, tid, parallel_fields, session_duration,
                      break_duration, number_of_rounds, campus_overrides_raw, campus_ids),
                daemon=True,
            ).start()
            _ops_logger.info("[ops] Thread task dispatched task_id=%s", task_id)
    else:
        # Sync generation for small counts
        from app.services.tournament.session_generation.session_generator import (
            TournamentSessionGenerator,
        )
        from app.models.semester_enrollment import SemesterEnrollment as _SE2, EnrollmentStatus as _ES2

        enrolled_user_ids = [
            r[0] for r in db.query(_SE2.user_id).filter(
                _SE2.semester_id == tid,
                _SE2.is_active == True,
                _SE2.request_status == _ES2.APPROVED,
            ).all()
        ]
        generator = TournamentSessionGenerator(db)
        _gen_ok, _gen_msg, _ = generator.generate_sessions(
            tournament_id=tid,
            parallel_fields=parallel_fields,
            session_duration_minutes=session_duration,
            break_minutes=break_duration,
            number_of_rounds=number_of_rounds,
            campus_ids=campus_ids,
        )
        task_id = "sync-done"
        if not _gen_ok:
            _ops_logger.error(
                "[ops] Sync generation FAILED for %d players: %s",
                request.player_count, _gen_msg,
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Session generation failed: {_gen_msg}. "
                    f"Tournament id={tid} was created but has 0 sessions. "
                    f"Adjust player_count or tournament_type_code and retry."
                ),
            )
        _ops_logger.info(
            "[ops] Sync generation done for %d players: %s",
            request.player_count, _gen_msg,
        )

        # ── Step 4.1: Auto-simulate results (skipped for manual/observe modes) ──
        sim_ok = request.simulation_mode in ("auto_immediate", "accelerated")
        sim_msg = "skipped (manual mode)"
        if sim_ok:
            sim_ok, sim_msg = _simulate_tournament_results(
                db=db,
                tournament_id=tid,
                logger=_ops_logger,
            )
        if sim_ok:
            _ops_logger.info("[ops] Auto-result simulation: %s", sim_msg)

            # ── Step 4.2: Calculate rankings to populate leaderboard ─────────────
            try:
                from app.services.tournament.ranking.strategies.factory import RankingStrategyFactory
                from app.models.tournament_ranking import TournamentRanking

                # Get tournament format and type
                tournament = db.query(_Semester).filter(_Semester.id == tid).first()
                tournament_format = tournament.format if tournament.format else "HEAD_TO_HEAD"
                tournament_type_code = None
                if tournament.tournament_config_obj and tournament.tournament_config_obj.tournament_type:
                    tournament_type_code = tournament.tournament_config_obj.tournament_type.code

                # Get all sessions for ranking calculation
                sessions = _get_tournament_sessions(db, tid)

                if tournament_format == "INDIVIDUAL_RANKING":
                    rankings = _calculate_ir_rankings(tournament, sessions, _ops_logger)
                    strategy = True  # Sentinel so the insert block runs
                elif tournament_type_code:
                    # HEAD_TO_HEAD: use tournament type-based strategy
                    strategy = RankingStrategyFactory.create(
                        tournament_format=tournament_format,
                        tournament_type_code=tournament_type_code,
                    )
                else:
                    _ops_logger.warning("[ops] Cannot calculate rankings: unknown format/type")
                    strategy = None

                if strategy is not None:
                    if tournament_format != "INDIVIDUAL_RANKING":
                        # H2H strategies expect (sessions, db) and return List[Dict]
                        rankings = strategy.calculate_rankings(sessions, db)

                    # Delete existing rankings (idempotency)
                    db.query(TournamentRanking).filter(
                        TournamentRanking.tournament_id == tid
                    ).delete()

                    # Insert new rankings
                    for ranking_data in rankings:
                        ranking_record = TournamentRanking(
                            tournament_id=tid,
                            user_id=ranking_data["user_id"],
                            participant_type="INDIVIDUAL",
                            rank=ranking_data["rank"],
                            # IR strategies return "final_value"; H2H returns "points"
                            points=ranking_data.get("points") or ranking_data.get("final_value", 0),
                            wins=ranking_data.get("wins", 0),
                            losses=ranking_data.get("losses", 0),
                            draws=ranking_data.get("ties", 0),
                            goals_for=ranking_data.get("goals_scored", 0),
                            goals_against=ranking_data.get("goals_conceded", 0),
                        )
                        db.add(ranking_record)

                    db.commit()
                    _ops_logger.info("[ops] Rankings calculated: %d players ranked", len(rankings))

            except Exception as rank_exc:
                import traceback
                _ops_logger.warning("[ops] Ranking calculation failed (non-fatal): %s", rank_exc)
                _ops_logger.warning("[ops] Ranking calculation traceback:\n%s", traceback.format_exc())
                db.rollback()

            # ── Step 4.3: Finalize tournament + auto-distribute rewards ───────────
            # Runs TournamentFinalizer to set COMPLETED → REWARDS_DISTRIBUTED lifecycle
            _finalize_tournament_with_rewards(tid, db, _ops_logger)

        else:
            _ops_logger.warning("[ops] Auto-result simulation skipped or failed (non-fatal): %s", sim_msg)

    # ── Step 5: Audit log ─────────────────────────────────────────────────────
    audit_log_id: Optional[int] = None
    try:
        from app.services.audit_service import AuditService
        from app.models.audit_log import AuditAction
        audit_svc = AuditService(db)
        log_entry = audit_svc.log(
            action=AuditAction.OPS_SCENARIO_TRIGGERED,
            user_id=current_user.id,
            resource_type="tournament",
            resource_id=tid,
            details={
                "scenario": request.scenario,
                "player_count": request.player_count,
                "enrolled_count": enrolled_count,
                "triggered_by_email": current_user.email,
                "dry_run": False,
                "confirmed": request.confirmed,
                "task_id": task_id,
            },
        )
        audit_log_id = log_entry.id if log_entry else None
    except Exception as audit_exc:
        _ops_logger.warning("[ops] Audit log failed (non-fatal): %s", audit_exc)

    # Count sessions created (query after generation)
    from app.models.session import Session as _SessionModel
    _session_count = db.query(_SessionModel).filter(
        _SessionModel.semester_id == tid,
        _SessionModel.is_tournament_game == True,
    ).count()

    return OpsScenarioResponse(
        triggered=True,
        scenario=request.scenario,
        tournament_id=tid,
        tournament_name=tournament_name,
        task_id=task_id,
        enrolled_count=enrolled_count,
        session_count=_session_count,
        dry_run=False,
        audit_log_id=audit_log_id,
        message=(
            f"Ops scenario '{request.scenario}' launched: "
            f"tournament_id={tid}, {enrolled_count} players enrolled, "
            f"{_session_count} sessions created, task_id={task_id}"
        ),
    )
