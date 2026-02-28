"""
⚽ Football Skill Assessment Lifecycle API (Phase 3)

Individual skill assessment endpoints with state machine lifecycle:
- NOT_ASSESSED → ASSESSED → VALIDATED → ARCHIVED

Routes:
- POST /{license_id}/skills/{skill_name}/assess - Create skill assessment
- GET /{license_id}/skills/{skill_name}/assessments - Get assessment history
- GET /assessments/{assessment_id} - Get single assessment
- POST /assessments/{assessment_id}/validate - Validate assessment (admin/instructor)
- POST /assessments/{assessment_id}/archive - Archive assessment (admin/instructor)
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, timezone

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User, UserRole
from .....models.license import UserLicense
from .....models.football_skill_assessment import FootballSkillAssessment
from .....services.football_skill_service import FootballSkillService
from .....services.skill_state_machine import SkillAssessmentState

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateAssessmentRequest(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
        json_schema_extra={
            "example": {
                "points_earned": 8,
                "points_total": 10,
                "notes": "Good ball control, needs improvement on weak foot"
            }
        }
    )

    """Request body for creating skill assessment"""
    points_earned: int = Field(..., ge=0, description="Points earned (numerator)")
    points_total: int = Field(..., gt=0, description="Total points possible (denominator)")
    notes: Optional[str] = Field(None, max_length=1000, description="Optional instructor notes")


class AssessmentResponse(BaseModel):
    """Response model for assessment"""
    id: int
    user_license_id: int
    skill_name: str
    points_earned: int
    points_total: int
    percentage: float
    status: str
    requires_validation: bool

    # Assessment metadata
    assessed_by: int
    assessed_at: datetime
    notes: Optional[str]

    # Validation metadata (if validated)
    validated_by: Optional[int]
    validated_at: Optional[datetime]

    # Archive metadata (if archived)
    archived_by: Optional[int]
    archived_at: Optional[datetime]
    archived_reason: Optional[str]

    # State transition audit
    previous_status: Optional[str]
    status_changed_at: Optional[datetime]
    status_changed_by: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class CreateAssessmentResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Response for assessment creation"""
    success: bool
    created: bool
    message: str
    assessment: AssessmentResponse


class ValidateArchiveResponse(BaseModel):
    """Response for validate/archive operations"""
    success: bool
    message: str
    assessment: AssessmentResponse


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/{license_id}/skills/{skill_name}/assess", response_model=CreateAssessmentResponse)
async def create_skill_assessment(
    license_id: int,
    skill_name: str,
    request: CreateAssessmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create individual skill assessment (INSTRUCTOR ONLY)

    Creates new assessment with state=ASSESSED. If identical assessment exists,
    returns existing (idempotent). If different assessment exists, archives old
    and creates new.

    **State transition:** NOT_ASSESSED → ASSESSED

    **Permissions:** INSTRUCTOR or ADMIN only

    **Idempotency:**
    - Identical data (same points) → returns existing (created=False)
    - Different data → archives old + creates new (created=True)

    **Business Rules:**
    - `requires_validation` auto-determined by:
      - License level 5+ → requires validation
      - Instructor tenure < 6 months → requires validation
      - Critical skills (mental, set_pieces) → requires validation

    **Args:**
    - license_id: UserLicense ID
    - skill_name: Skill identifier (e.g., 'ball_control', 'passing')
    - points_earned: Points scored (0-N)
    - points_total: Total possible points (must be > 0)
    - notes: Optional instructor notes

    **Returns:**
    - success: True if operation succeeded
    - created: True if new assessment created, False if existing returned
    - message: Human-readable status message
    - assessment: Full assessment object
    """
    # Permission check: Only instructors can create assessments
    if current_user.role not in [UserRole.INSTRUCTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and admins can create skill assessments"
        )

    # Verify license exists
    license = db.query(UserLicense).filter(UserLicense.id == license_id).first()
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"License {license_id} not found"
        )

    # Verify this is an LFA Player specialization
    if not license.specialization_type.startswith("LFA_PLAYER_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Skill assessments are only available for LFA Player specializations, not {license.specialization_type}"
        )

    # Validate skill name (basic validation - service layer has full list)
    if not skill_name or len(skill_name) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skill name must be 1-50 characters"
        )

    # Create assessment via service layer
    try:
        service = FootballSkillService(db)
        assessment, created = service.create_assessment(
            user_license_id=license_id,
            skill_name=skill_name,
            points_earned=request.points_earned,
            points_total=request.points_total,
            assessed_by=current_user.id,
            notes=request.notes
        )
        db.commit()
        db.refresh(assessment)

        # Build response message
        if created:
            message = f"Skill assessment created successfully (status={assessment.status})"
            if assessment.requires_validation:
                message += " - requires admin validation"
        else:
            message = "Identical assessment already exists (idempotent)"

        return CreateAssessmentResponse(
            success=True,
            created=created,
            message=message,
            assessment=AssessmentResponse.from_orm(assessment)
        )

    except ValueError as e:
        # Business logic error (e.g., invalid state transition)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create assessment: {str(e)}"
        )


@router.get("/{license_id}/skills/{skill_name}/assessments", response_model=List[AssessmentResponse])
async def get_skill_assessment_history(
    license_id: int,
    skill_name: str,
    include_archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get assessment history for a specific skill

    Returns all assessments for given license + skill, ordered by assessed_at DESC.

    **Permissions:**
    - Students can view their own assessments
    - Instructors/admins can view all assessments

    **Query Parameters:**
    - include_archived: If True, includes ARCHIVED assessments (default: False)

    **Args:**
    - license_id: UserLicense ID
    - skill_name: Skill identifier

    **Returns:**
    - List of assessments (most recent first)
    """
    # Verify license exists
    license = db.query(UserLicense).filter(UserLicense.id == license_id).first()
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"License {license_id} not found"
        )

    # Permission check: Students can only view their own, instructors can view all
    if license.user_id != current_user.id and current_user.role not in [UserRole.INSTRUCTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own skill assessments"
        )

    # Build query
    query = db.query(FootballSkillAssessment).filter(
        FootballSkillAssessment.user_license_id == license_id,
        FootballSkillAssessment.skill_name == skill_name
    )

    # Filter by status if not including archived
    if not include_archived:
        query = query.filter(
            FootballSkillAssessment.status.in_([
                SkillAssessmentState.ASSESSED,
                SkillAssessmentState.VALIDATED
            ])
        )

    # Order by assessed_at DESC (most recent first)
    assessments = query.order_by(FootballSkillAssessment.assessed_at.desc()).all()

    return [AssessmentResponse.from_orm(a) for a in assessments]


@router.get("/assessments/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment(
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get single assessment by ID

    **Permissions:**
    - Students can view their own assessments
    - Instructors/admins can view all assessments

    **Args:**
    - assessment_id: Assessment ID

    **Returns:**
    - Full assessment object
    """
    assessment = db.query(FootballSkillAssessment).filter(
        FootballSkillAssessment.id == assessment_id
    ).first()

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment {assessment_id} not found"
        )

    # Permission check: Students can only view their own
    license = db.query(UserLicense).filter(
        UserLicense.id == assessment.user_license_id
    ).first()

    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated license not found"
        )

    if license.user_id != current_user.id and current_user.role not in [UserRole.INSTRUCTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own skill assessments"
        )

    return AssessmentResponse.from_orm(assessment)


@router.post("/assessments/{assessment_id}/validate", response_model=ValidateArchiveResponse)
async def validate_assessment(
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate skill assessment (ADMIN/INSTRUCTOR ONLY)

    Transitions assessment from ASSESSED → VALIDATED.

    **State transition:** ASSESSED → VALIDATED

    **Permissions:** ADMIN or INSTRUCTOR only

    **Idempotency:**
    - If already VALIDATED → returns existing (no error)

    **Invalid transitions:**
    - NOT_ASSESSED → VALIDATED (must assess first)
    - ARCHIVED → VALIDATED (cannot restore archived)

    **Args:**
    - assessment_id: Assessment ID

    **Returns:**
    - success: True
    - message: Status message
    - assessment: Updated assessment object
    """
    # Permission check: Only admins/instructors can validate
    if current_user.role not in [UserRole.INSTRUCTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and admins can validate assessments"
        )

    # Validate assessment via service layer
    try:
        service = FootballSkillService(db)
        assessment = service.validate_assessment(
            assessment_id=assessment_id,
            validated_by=current_user.id
        )
        db.commit()
        db.refresh(assessment)

        return ValidateArchiveResponse(
            success=True,
            message=f"Assessment validated successfully (status={assessment.status})",
            assessment=AssessmentResponse.from_orm(assessment)
        )

    except ValueError as e:
        # Business logic error (e.g., invalid state transition, assessment not found)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate assessment: {str(e)}"
        )


@router.post("/assessments/{assessment_id}/archive", response_model=ValidateArchiveResponse)
async def archive_assessment(
    assessment_id: int,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Archive skill assessment (ADMIN/INSTRUCTOR ONLY)

    Transitions assessment from ASSESSED/VALIDATED → ARCHIVED.

    **State transition:** ASSESSED/VALIDATED → ARCHIVED

    **Permissions:** ADMIN or INSTRUCTOR only

    **Idempotency:**
    - If already ARCHIVED → returns existing (no error)

    **Invalid transitions:**
    - NOT_ASSESSED → ARCHIVED (must assess first)
    - ARCHIVED → ARCHIVED (already archived - idempotent)

    **Query Parameters:**
    - reason: Optional reason for archiving (default: "Manually archived by instructor")

    **Args:**
    - assessment_id: Assessment ID

    **Returns:**
    - success: True
    - message: Status message
    - assessment: Updated assessment object
    """
    # Permission check: Only admins/instructors can archive
    if current_user.role not in [UserRole.INSTRUCTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and admins can archive assessments"
        )

    # Default reason if not provided
    if not reason:
        reason = "Manually archived by instructor"

    # Archive assessment via service layer
    try:
        service = FootballSkillService(db)
        assessment = service.archive_assessment(
            assessment_id=assessment_id,
            archived_by=current_user.id,
            reason=reason
        )
        db.commit()
        db.refresh(assessment)

        return ValidateArchiveResponse(
            success=True,
            message=f"Assessment archived successfully (reason: {reason})",
            assessment=AssessmentResponse.from_orm(assessment)
        )

    except ValueError as e:
        # Business logic error (e.g., invalid state transition, assessment not found)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive assessment: {str(e)}"
        )
