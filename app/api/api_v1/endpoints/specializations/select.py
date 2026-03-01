"""
Specialization Selection API (TICKET-SMOKE-003)

JSON API endpoint for specialization selection during onboarding.
Replaces Form-based web route with proper Pydantic validation.

Business Logic:
- User selects a specialization type
- If no existing license → costs 100 credits to unlock
- Creates UserLicense + logs credit transaction
- Returns next step URL for onboarding flow
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from enum import Enum

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User, SpecializationType
from .....models.license import UserLicense
from .....models.credit_transaction import CreditTransaction, TransactionType


router = APIRouter()


# ============================================================================
# Request/Response Schemas
# ============================================================================

class SpecializationTypeEnum(str, Enum):
    """Available specialization types for selection"""
    INTERNSHIP = "INTERNSHIP"
    LFA_FOOTBALL_PLAYER = "LFA_FOOTBALL_PLAYER"
    LFA_COACH = "LFA_COACH"
    GANCUJU_PLAYER = "GANCUJU_PLAYER"


class SpecializationSelectRequest(BaseModel):
    """Request schema for specialization selection"""
    model_config = ConfigDict(extra='forbid')

    specialization: SpecializationTypeEnum = Field(
        ...,
        description="Specialization type to select"
    )


class SpecializationSelectResponse(BaseModel):
    """Response schema for specialization selection"""
    success: bool
    message: str
    specialization: str
    license_created: bool
    credits_deducted: int
    credit_balance_after: int
    next_step_url: str


# ============================================================================
# Endpoint
# ============================================================================

SPEC_UNLOCK_COST = 100  # Cost to unlock a new specialization


@router.post("/select", response_model=SpecializationSelectResponse)
def select_specialization(
    request_data: SpecializationSelectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Select specialization and unlock if needed (TICKET-SMOKE-003)

    **Business Rules:**
    1. If user already has license → FREE (just updates user.specialization)
    2. If user does NOT have license → 100 credits to unlock
       - Deducts credits
       - Creates UserLicense
       - Logs CreditTransaction

    **Acceptance Criteria:**
    - AC1: Valid specialization selection succeeds
    - AC2: Insufficient credits rejected with 400
    - AC3: Invalid specialization rejected with 422
    - AC4: Duplicate selection allowed (no cost if license exists)
    - AC5: Credit transaction logged correctly

    **Returns:**
    - next_step_url: URL for onboarding questionnaire based on specialization
    - credits_deducted: 100 if new unlock, 0 if existing license
    - license_created: True if new license created

    **Permissions:** Authenticated users only
    **Validation:** Pydantic schema enforces valid specialization enum
    """
    # Convert enum to SpecializationType
    spec_type = SpecializationType[request_data.specialization.value]

    # Check if user already has a license (already unlocked)
    user_license = db.query(UserLicense).filter(
        UserLicense.user_id == current_user.id,
        UserLicense.specialization_type == spec_type.value
    ).first()

    license_created = False
    credits_deducted = 0

    # If NO license exists, this is a NEW unlock → costs 100 credits
    if not user_license:
        # AC2: Check if user has enough credits
        if current_user.credit_balance < SPEC_UNLOCK_COST:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Insufficient credits. Unlocking {spec_type.value.replace('_', ' ')} "
                    f"requires {SPEC_UNLOCK_COST} credits. You have {current_user.credit_balance} credits."
                )
            )

        # DEDUCT credits and create the license
        current_user.credit_balance -= SPEC_UNLOCK_COST
        credits_deducted = SPEC_UNLOCK_COST

        # Create the UserLicense (unlock specialization)
        user_license = UserLicense(
            user_id=current_user.id,
            specialization_type=spec_type.value,
            current_level=1,
            max_achieved_level=1,
            started_at=datetime.utcnow(),
            payment_verified=True,  # Paid via credits
            payment_verified_at=datetime.utcnow(),
            is_active=True,
            onboarding_completed=False  # Will be completed after questionnaire
        )
        db.add(user_license)
        db.flush()  # Flush to get user_license.id
        license_created = True

        # AC5: Log credit transaction
        idempotency_key = f"spec-unlock-{current_user.id}-{spec_type.value}-{user_license.id}"
        credit_transaction = CreditTransaction(
            user_license_id=user_license.id,
            amount=-SPEC_UNLOCK_COST,
            transaction_type=TransactionType.PURCHASE.value,
            description=f"Unlocked specialization: {spec_type.value.replace('_', ' ')}",
            balance_after=current_user.credit_balance,
            idempotency_key=idempotency_key
        )
        db.add(credit_transaction)

    # Update user's specialization (onboarding_completed will be set after questionnaire)
    current_user.specialization = spec_type

    db.commit()
    db.refresh(current_user)

    # Determine next step URL based on specialization type
    if spec_type == SpecializationType.LFA_FOOTBALL_PLAYER:
        next_step_url = "/specialization/lfa-player/onboarding"
    else:
        next_step_url = f"/specialization/motivation?spec={spec_type.value}"

    # Build response message
    if license_created:
        message = f"Specialization unlocked successfully. {SPEC_UNLOCK_COST} credits deducted."
    else:
        message = f"Specialization updated successfully (already unlocked)."

    return SpecializationSelectResponse(
        success=True,
        message=message,
        specialization=spec_type.value,
        license_created=license_created,
        credits_deducted=credits_deducted,
        credit_balance_after=current_user.credit_balance,
        next_step_url=next_step_url
    )
