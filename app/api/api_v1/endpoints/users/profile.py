"""
User profile management endpoints
Self-service profile updates and password reset
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json

from .....database import get_db
from .....dependencies import get_current_user, get_current_admin_user
from .....core.security import get_password_hash
from .....models.user import User
from .....schemas.user import User as UserSchema, UserUpdateSelf
from .....schemas.auth import ResetPassword
from .helpers import validate_email_unique, validate_nickname

router = APIRouter()


@router.get("/me", response_model=UserSchema)
def get_current_user_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get current user profile with licenses
    """
    from sqlalchemy.orm import joinedload

    # Reload user with licenses relationship eagerly loaded
    user_with_licenses = db.query(User).options(
        joinedload(User.licenses)
    ).filter(User.id == current_user.id).first()

    # Keep interests as JSON string for schema compatibility
    user_data = user_with_licenses.__dict__.copy()
    # Ensure interests is a string (not parsed to list)
    if user_data.get('interests') is None:
        user_data['interests'] = None

    return user_data


@router.patch("/me", response_model=UserSchema)
def update_own_profile(
    user_update: UserUpdateSelf,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Update own profile
    """
    # Check email uniqueness if email is being updated
    if user_update.email and user_update.email != current_user.email:
        if not validate_email_unique(db, user_update.email, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

    # Validate that emergency phone is different from user phone
    update_data = user_update.model_dump(exclude_unset=True)
    user_phone = update_data.get('phone', current_user.phone)
    emergency_phone = update_data.get('emergency_phone', current_user.emergency_phone)

    if user_phone and emergency_phone and user_phone == emergency_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A vészhelyzeti telefonszám nem lehet ugyanaz, mint a saját telefonszámod"
        )

    # Handle NDA acceptance with timestamp
    if 'nda_accepted' in update_data and update_data['nda_accepted']:
        setattr(current_user, 'nda_accepted_at', datetime.now(timezone.utc))

    # Update fields
    for field, value in update_data.items():
        if field == 'interests' and isinstance(value, list):
            # Convert interests list to JSON string for database storage
            setattr(current_user, field, json.dumps(value))
        else:
            setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    # Keep interests as JSON string for schema compatibility
    user_data = current_user.__dict__.copy()
    # Ensure interests is a string (not parsed to list)
    if user_data.get('interests') is None:
        user_data['interests'] = None

    return user_data


@router.post("/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    password_data: ResetPassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Reset user password (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.password_hash = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "Password reset successfully"}


@router.get("/check-nickname/{nickname}")
def check_nickname_availability(
    nickname: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Check if a nickname is available for use
    """
    is_valid, message = validate_nickname(nickname, db, current_user.id)
    
    return {
        "available": is_valid,
        "message": message
    }
