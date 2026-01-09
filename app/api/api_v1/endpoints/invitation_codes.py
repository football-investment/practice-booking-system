from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from pydantic import BaseModel, EmailStr

from ....database import get_db
from ....dependencies import get_current_admin_user_web, get_current_user_web, get_current_admin_user, security_optional
from fastapi.security import HTTPAuthorizationCredentials
from ....models.user import User
from ....models.invitation_code import InvitationCode
from ....models.credit_transaction import CreditTransaction, TransactionType

router = APIRouter()


# ==================== HYBRID AUTH HELPER ====================

async def get_admin_user_hybrid(
    request: Request,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security_optional)
) -> User:
    """
    Hybrid authentication: supports both Bearer token AND cookie-based auth
    - Bearer token: for API tests (Authorization: Bearer <token>)
    - Cookie: for Streamlit frontend (Cookie: access_token=<token>)
    """
    from ....core.auth import verify_token
    from ....models.user import UserRole

    # Try Bearer token first (API tests)
    if credentials:
        token = credentials.credentials
        username = verify_token(token, "access")

        if username:
            user = db.query(User).filter(User.email == username).first()
            if user and user.is_active and user.role == UserRole.ADMIN:
                return user

    # Try cookie (Streamlit frontend)
    token_cookie = request.cookies.get("access_token")
    if token_cookie:
        try:
            token = token_cookie.replace("Bearer ", "")
            username = verify_token(token, "access")

            if username:
                user = db.query(User).filter(User.email == username).first()
                if user and user.is_active and user.role == UserRole.ADMIN:
                    return user
        except:
            pass

    # Neither method worked
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authenticated or not admin"
    )


# ==================== SCHEMAS ====================

class InvitationCodeCreate(BaseModel):
    """Request body for creating an invitation code"""
    invited_name: str
    invited_email: EmailStr | None = None
    bonus_credits: int
    expires_at: datetime | None = None
    notes: str | None = None


class InvitationCodeResponse(BaseModel):
    """Response model for invitation code"""
    id: int
    code: str
    invited_name: str
    invited_email: str | None
    bonus_credits: int
    is_used: bool
    used_by_user_id: int | None
    used_at: datetime | None
    created_by_admin_id: int | None
    created_at: datetime
    expires_at: datetime | None
    notes: str | None

    # Additional fields
    used_by_name: str | None = None
    created_by_name: str | None = None
    is_valid: bool = True

    class Config:
        from_attributes = True


class InvitationCodeRedeem(BaseModel):
    """Request body for redeeming an invitation code"""
    code: str


# ==================== ADMIN ENDPOINTS ====================

@router.get("/admin/invitation-codes", response_model=List[InvitationCodeResponse])
async def get_all_invitation_codes(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user_hybrid)
) -> Any:
    """
    Get all invitation codes (Admin only)
    Supports both Bearer token (API tests) and cookie (Streamlit) authentication
    """
    codes = db.query(InvitationCode).order_by(InvitationCode.created_at.desc()).all()

    # Enrich with user names
    result = []
    for code in codes:
        code_dict = {
            "id": code.id,
            "code": code.code,
            "invited_name": code.invited_name,
            "invited_email": code.invited_email,
            "bonus_credits": code.bonus_credits,
            "is_used": code.is_used,
            "used_by_user_id": code.used_by_user_id,
            "used_at": code.used_at,
            "created_by_admin_id": code.created_by_admin_id,
            "created_at": code.created_at,
            "expires_at": code.expires_at,
            "notes": code.notes,
            "is_valid": code.is_valid(),
            "used_by_name": None,
            "created_by_name": None
        }

        # Get user names
        if code.used_by_user_id:
            user = db.query(User).filter(User.id == code.used_by_user_id).first()
            if user:
                code_dict["used_by_name"] = user.name

        if code.created_by_admin_id:
            admin = db.query(User).filter(User.id == code.created_by_admin_id).first()
            if admin:
                code_dict["created_by_name"] = admin.name

        result.append(code_dict)

    return result


@router.post("/admin/invitation-codes", response_model=InvitationCodeResponse)
async def create_invitation_code(
    request: Request,
    code_data: InvitationCodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user_hybrid)
) -> Any:
    """
    Create a new invitation code (Admin only)
    Supports both Bearer token (API tests) and cookie (Streamlit) authentication
    """
    # Validate bonus_credits
    if code_data.bonus_credits <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bonus credits must be positive"
        )

    # Generate unique code
    code = InvitationCode.generate_code()

    # Check for duplicates (extremely unlikely but possible)
    attempts = 0
    while db.query(InvitationCode).filter(InvitationCode.code == code).first():
        code = InvitationCode.generate_code()
        attempts += 1
        if attempts > 10:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate unique code"
            )

    # Create invitation code
    invitation_code = InvitationCode(
        code=code,
        invited_name=code_data.invited_name,
        invited_email=code_data.invited_email,
        bonus_credits=code_data.bonus_credits,
        expires_at=code_data.expires_at,
        notes=code_data.notes,
        created_by_admin_id=current_user.id,
        created_at=datetime.now(timezone.utc)
    )

    db.add(invitation_code)
    db.commit()
    db.refresh(invitation_code)

    print(f"✅ Invitation code created: {code} for {code_data.invited_name} ({code_data.bonus_credits} credits) by {current_user.name}")

    return InvitationCodeResponse(
        id=invitation_code.id,
        code=invitation_code.code,
        invited_name=invitation_code.invited_name,
        invited_email=invitation_code.invited_email,
        bonus_credits=invitation_code.bonus_credits,
        is_used=invitation_code.is_used,
        used_by_user_id=invitation_code.used_by_user_id,
        used_at=invitation_code.used_at,
        created_by_admin_id=invitation_code.created_by_admin_id,
        created_at=invitation_code.created_at,
        expires_at=invitation_code.expires_at,
        notes=invitation_code.notes,
        is_valid=invitation_code.is_valid(),
        created_by_name=current_user.name
    )


@router.delete("/admin/invitation-codes/{code_id}")
async def delete_invitation_code(
    request: Request,
    code_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user_hybrid)
) -> Any:
    """
    Delete an invitation code (Admin only)
    Only unused codes can be deleted
    Supports both Bearer token (API tests) and cookie (Streamlit) authentication
    """
    code = db.query(InvitationCode).filter(InvitationCode.id == code_id).first()

    if not code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation code not found"
        )

    if code.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete used invitation code"
        )

    code_str = code.code
    invited_name = code.invited_name

    db.delete(code)
    db.commit()

    print(f"🗑️ Invitation code {code_str} for {invited_name} deleted by {current_user.name}")

    return {
        "success": True,
        "message": f"Invitation code {code_str} deleted successfully"
    }


# ==================== STUDENT ENDPOINTS ====================

@router.post("/invitation-codes/validate")
async def validate_invitation_code(
    request: Request,
    redeem_data: InvitationCodeRedeem,
    db: Session = Depends(get_db)
) -> Any:
    """
    Validate an invitation code (Public - no auth required)
    Returns code details if valid
    """
    code = db.query(InvitationCode).filter(
        InvitationCode.code == redeem_data.code.upper().strip()
    ).first()

    if not code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation code not found"
        )

    # Check if valid
    if not code.is_valid():
        if code.is_used:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation code has already been used"
            )
        if code.expires_at and code.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation code has expired"
            )

    return {
        "success": True,
        "valid": True,
        "bonus_credits": code.bonus_credits,
        "invited_name": code.invited_name,
        "expires_at": code.expires_at
    }


@router.post("/invitation-codes/redeem")
async def redeem_invitation_code(
    request: Request,
    redeem_data: InvitationCodeRedeem,
    db: Session = Depends(get_db)
) -> Any:
    """
    Redeem an invitation code and add bonus credits to user account
    Requires authentication
    """
    # Get current user from cookie
    try:
        current_user = await get_current_user_web(request, db)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You must be logged in to redeem an invitation code"
        )

    # Find code
    code = db.query(InvitationCode).filter(
        InvitationCode.code == redeem_data.code.upper().strip()
    ).first()

    if not code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation code not found"
        )

    # Check if valid
    if not code.is_valid():
        if code.is_used:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation code has already been used"
            )
        if code.expires_at and code.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation code has expired"
            )

    # Check email restriction
    if not code.can_be_used_by_email(current_user.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This invitation code is restricted to {code.invited_email}"
        )

    # Check if user has already redeemed ANY invitation code
    existing_redemption = db.query(InvitationCode).filter(
        InvitationCode.used_by_user_id == current_user.id
    ).first()

    if existing_redemption:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already redeemed an invitation code"
        )

    # Add credits to user account
    old_balance = current_user.credit_balance
    current_user.credit_balance += code.bonus_credits
    new_balance = current_user.credit_balance

    # Mark code as used
    now = datetime.now(timezone.utc)
    code.is_used = True
    code.used_by_user_id = current_user.id
    code.used_at = now

    db.commit()
    db.refresh(current_user)
    db.refresh(code)

    print(f"🎁 Invitation code {code.code} redeemed by {current_user.name} ({current_user.email}). Added {code.bonus_credits} credits. Balance: {old_balance} → {new_balance}")

    return {
        "success": True,
        "message": f"🎁 Welcome! {code.bonus_credits} bonus credits added to your account!",
        "bonus_credits": code.bonus_credits,
        "old_balance": old_balance,
        "new_balance": new_balance
    }
