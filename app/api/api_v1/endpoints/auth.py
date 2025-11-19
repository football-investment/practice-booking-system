from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ....database import get_db
from ....dependencies import get_current_user
from ....core.auth import create_access_token, create_refresh_token, verify_token
from ....core.security import verify_password, get_password_hash
from ....models.user import User
from ....schemas.auth import Login, Token, RefreshToken, ChangePassword
from ....schemas.user import User as UserSchema
from ....config import settings
from ....services.audit_service import AuditService
from ....models.audit_log import AuditAction

router = APIRouter()


@router.post("/login", response_model=Token)
def login(
    user_credentials: Login,
    db: Session = Depends(get_db)
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    print(f"🔍 LOGIN ATTEMPT - Email: {user_credentials.email}")
    print(f"🔍 Password received: '{user_credentials.password}' (length: {len(user_credentials.password)})")
    
    user = db.query(User).filter(User.email == user_credentials.email).first()
    print(f"🔍 User found: {user is not None}")
    
    if user:
        print(f"🔍 User active: {user.is_active}")
        password_check = verify_password(user_credentials.password, user.password_hash)
        print(f"🔍 Password valid: {password_check}")
        print(f"🔍 Password hash: {user.password_hash[:30]}...")
        
        # Test with expected password
        expected_check = verify_password("password123", user.password_hash)
        print(f"🔍 Expected password123 works: {expected_check}")
    
    if not user or not verify_password(user_credentials.password, user.password_hash):
        print(f"❌ LOGIN FAILED - User: {user is not None}, Password: {verify_password(user_credentials.password, user.password_hash) if user else False}")

        # 🔍 AUDIT: Log failed login
        audit_service = AuditService(db)
        audit_service.log(
            action=AuditAction.LOGIN_FAILED,
            user_id=user.id if user else None,
            details={
                "email": user_credentials.email,
                "reason": "invalid_password" if user else "user_not_found"
            }
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.email}, expires_delta=refresh_token_expires
    )

    # 🔍 AUDIT: Log successful login
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.LOGIN,
        user_id=user.id,
        details={
            "email": user.email,
            "role": user.role.value if user.role else None,
            "success": True
        }
    )

    # 🏆 GAMIFICATION: Check for achievement unlocks
    from app.services.gamification import GamificationService
    gamification_service = GamificationService(db)
    try:
        unlocked = gamification_service.check_and_unlock_achievements(
            user_id=user.id,
            trigger_action="login"
        )
        if unlocked:
            print(f"🎉 Unlocked {len(unlocked)} achievement(s) for user {user.id}")
    except Exception as e:
        # Don't fail login if achievement check fails
        print(f"⚠️  Achievement check failed: {e}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/login/form", response_model=Token)
def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """
    OAuth2 compatible token login with form data
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.email}, expires_delta=refresh_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
def refresh_token(
    token_data: RefreshToken,
    db: Session = Depends(get_db)
) -> Any:
    """
    Refresh access token using refresh token
    """
    username = verify_token(token_data.refresh_token, "refresh")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.email == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    new_refresh_token = create_refresh_token(
        data={"sub": user.email}, expires_delta=refresh_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout")
def logout() -> Any:
    """
    Logout (in a stateless JWT system, this is mostly symbolic)
    """
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserSchema)
def read_users_me(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get current user
    """
    return current_user


@router.post("/change-password")
def change_password(
    password_data: ChangePassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Change current user's password
    """
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password"
        )
    
    current_user.password_hash = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "Password updated successfully"}