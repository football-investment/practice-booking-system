"""
Specialization Onboarding API Endpoints
========================================
API v1 wrappers for specialization onboarding flow:
- select: Choose initial specialization
- unlock: Unlock specialization (100 credits)
- switch: Switch to different specialization
- lfa-player/onboarding-submit: Complete LFA Player onboarding
- motivation-submit: Submit motivation questionnaire

These are API wrappers around existing web route logic in:
- app/api/web_routes/specialization.py
- app/api/web_routes/onboarding.py
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import date

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.license import UserLicense
from app.models.specialization import SpecializationType
from app.services.audit_service import AuditService
from app.models.audit_log import AuditAction

router = APIRouter()


# ============================================================================
# Request/Response Schemas
# ============================================================================

class SpecializationUnlockRequest(BaseModel):
    """Request to unlock a specialization (100 credits)"""
    specialization: str = Field(
        ...,
        description="Specialization code: LFA_PLAYER, LFA_COACH, INTERNSHIP, GANCUJU_PLAYER"
    )


class SpecializationSelectRequest(BaseModel):
    """Request to select initial specialization"""
    specialization: str = Field(..., description="Specialization code")


class SpecializationSwitchRequest(BaseModel):
    """Request to switch to different specialization"""
    new_specialization: str = Field(..., description="New specialization code")
    reason: str | None = Field(None, description="Optional reason for switching")


class LfaPlayerOnboardingRequest(BaseModel):
    """Request to complete LFA Player onboarding"""
    # Extract from web route - add fields as needed
    specialization_code: str = Field(default="LFA_PLAYER")
    # Add other fields from form


class MotivationSubmitRequest(BaseModel):
    """Request to submit motivation questionnaire"""
    motivation_data: Dict[str, Any] = Field(
        ...,
        description="Specialization-specific motivation/preference data"
    )


class SpecializationResponse(BaseModel):
    """Generic specialization operation response"""
    success: bool
    message: str
    data: Dict[str, Any] | None = None


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/unlock", response_model=SpecializationResponse)
async def unlock_specialization(
    request: SpecializationUnlockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Unlock a specialization (costs 100 credits)

    **Business Logic (from web route):**
    - Requires 100 credits
    - Validates age requirement
    - Creates UserLicense
    - Deducts credits

    **Age Requirements:**
    - INTERNSHIP: 18+
    - LFA_COACH: 14+
    - GANCUJU_PLAYER: 5+
    - LFA_PLAYER: 5+
    """
    # Credit balance check
    if current_user.credit_balance < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient credits. You have {current_user.credit_balance} credits, but need 100."
        )

    # Map specialization enum
    spec_mapping = {
        "LFA_PLAYER": SpecializationType.LFA_FOOTBALL_PLAYER,
        "LFA_COACH": SpecializationType.LFA_COACH,
        "INTERNSHIP": SpecializationType.INTERNSHIP,
        "GANCUJU_PLAYER": SpecializationType.GANCUJU_PLAYER
    }

    spec_type = spec_mapping.get(request.specialization)
    if not spec_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid specialization: {request.specialization}"
        )

    # Age requirement validation
    age_requirements = {
        "INTERNSHIP": 18,
        "LFA_COACH": 14,
        "GANCUJU_PLAYER": 5,
        "LFA_PLAYER": 5
    }

    required_age = age_requirements.get(request.specialization, 0)
    user_age = current_user.calculate_age() if current_user.date_of_birth else None

    if user_age is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please set your date of birth first (age verification required)"
        )

    if user_age < required_age:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Age requirement not met. This specialization requires age {required_age}+. Your current age: {user_age}."
        )

    # Deduct credits
    current_user.credit_balance -= 100

    # Create user license
    new_license = UserLicense(
        user_id=current_user.id,
        specialization_type=spec_type.value,
        current_level=1,
        total_experience=0
    )

    db.add(new_license)
    db.commit()
    db.refresh(new_license)
    db.refresh(current_user)

    # Audit log
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.SPECIALIZATION_UNLOCKED,
        user_id=current_user.id,
        resource_type="specialization",
        resource_id=new_license.id,
        details={
            "specialization": spec_type.value,
            "credits_spent": 100,
            "remaining_credits": current_user.credit_balance
        }
    )

    return SpecializationResponse(
        success=True,
        message=f"Specialization {spec_type.value} unlocked successfully!",
        data={
            "specialization": spec_type.value,
            "license_id": new_license.id,
            "credits_remaining": current_user.credit_balance
        }
    )


@router.post("/select", response_model=SpecializationResponse)
async def select_specialization(
    request: SpecializationSelectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Select initial specialization during onboarding

    **Note:** This is an alias/wrapper for the existing POST /me endpoint
    with onboarding-specific naming for clarity.
    """
    # Validate specialization
    try:
        spec_type = SpecializationType(request.specialization)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid specialization: {request.specialization}"
        )

    # Set user specialization
    current_user.specialization = spec_type
    db.commit()
    db.refresh(current_user)

    # Audit log
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.SPECIALIZATION_SELECTED,
        user_id=current_user.id,
        details={
            "specialization": spec_type.value,
            "context": "onboarding"
        }
    )

    return SpecializationResponse(
        success=True,
        message=f"Specialization {spec_type.value} selected successfully!",
        data={
            "specialization": spec_type.value,
            "user_id": current_user.id
        }
    )


@router.post("/switch", response_model=SpecializationResponse)
async def switch_specialization(
    request: SpecializationSwitchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Switch to a different specialization

    **Business Logic:**
    - Requires existing specialization
    - May have restrictions/cooldowns (implement as needed)
    - Updates user.specialization
    """
    if not current_user.specialization:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No current specialization to switch from. Please select one first."
        )

    # Validate new specialization
    try:
        new_spec = SpecializationType(request.new_specialization)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid specialization: {request.new_specialization}"
        )

    old_spec = current_user.specialization.value

    # Update specialization
    current_user.specialization = new_spec
    db.commit()
    db.refresh(current_user)

    # Audit log
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.SPECIALIZATION_CHANGED,
        user_id=current_user.id,
        details={
            "old_specialization": old_spec,
            "new_specialization": new_spec.value,
            "reason": request.reason
        }
    )

    return SpecializationResponse(
        success=True,
        message=f"Switched from {old_spec} to {new_spec.value}",
        data={
            "old_specialization": old_spec,
            "new_specialization": new_spec.value
        }
    )


@router.post("/lfa-player/onboarding-submit", response_model=SpecializationResponse)
async def submit_lfa_player_onboarding(
    request: LfaPlayerOnboardingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Complete LFA Player onboarding flow

    **Note:** This is a wrapper around web route logic.
    Implement full business logic as needed.
    """
    # Set specialization to LFA_PLAYER
    current_user.specialization = SpecializationType.LFA_FOOTBALL_PLAYER
    db.commit()
    db.refresh(current_user)

    # Audit log
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.ONBOARDING_COMPLETED,
        user_id=current_user.id,
        details={
            "specialization": "LFA_PLAYER",
            "onboarding_type": "lfa_player"
        }
    )

    return SpecializationResponse(
        success=True,
        message="LFA Player onboarding completed successfully!",
        data={
            "specialization": "LFA_PLAYER",
            "user_id": current_user.id
        }
    )


@router.post("/motivation-submit", response_model=SpecializationResponse)
async def submit_motivation_questionnaire(
    request: MotivationSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit motivation/preference questionnaire

    **Specialization-specific data:**
    - LFA Player: Skill self-ratings (1-10)
    - GānCuju: Character type (Warrior/Teacher)
    - Coach: Age group + role preferences
    - Internship: Position selection

    **Storage:** Saved to user_licenses.motivation_scores (JSON)
    """
    # Get user's active license
    license = db.query(UserLicense).filter(
        UserLicense.user_id == current_user.id,
        UserLicense.specialization_type == current_user.specialization.value
    ).first()

    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active license found for current specialization"
        )

    # Save motivation data
    license.motivation_scores = request.motivation_data
    db.commit()
    db.refresh(license)

    # Audit log
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.MOTIVATION_ASSESSED,
        user_id=current_user.id,
        resource_type="license",
        resource_id=license.id,
        details={
            "specialization": license.specialization_type,
            "data_keys": list(request.motivation_data.keys())
        }
    )

    return SpecializationResponse(
        success=True,
        message="Motivation questionnaire submitted successfully!",
        data={
            "license_id": license.id,
            "specialization": license.specialization_type
        }
    )
