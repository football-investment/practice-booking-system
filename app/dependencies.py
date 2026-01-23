import logging
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .database import get_db
from .core.auth import verify_token
from .models.user import User, UserRole

logger = logging.getLogger(__name__)

security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    username = verify_token(token, "access")
    
    if username is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == username).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current user if they are admin"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


def get_current_admin_or_instructor_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current user if they are admin or instructor"""
    if current_user.role not in [UserRole.ADMIN, UserRole.INSTRUCTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user from cookie (optional, for web pages)"""
    # Try to get token from cookie
    token_cookie = request.cookies.get("access_token")

    if not token_cookie:
        return None

    # Extract token from "Bearer <token>" format
    try:
        token = token_cookie.replace("Bearer ", "")
        username = verify_token(token, "access")

        if username is None:
            return None

        user = db.query(User).filter(User.email == username).first()
        if user and user.is_active:
            return user
    except Exception as e:
        logger.error(f"Error verifying optional user token: {e}")

    return None


async def get_current_user_web(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """Get current user from cookie (required, for web pages)"""
    user = await get_current_user_optional(request, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    return user


async def get_current_admin_user_web(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """Get current admin user from cookie (for web-based API calls)"""
    user = await get_current_user_web(request, db)

    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    return user