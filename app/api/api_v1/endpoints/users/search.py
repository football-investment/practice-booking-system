"""
User search endpoints
Search and filter users by various criteria
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from .....database import get_db
from .....dependencies import get_current_admin_user
from .....models.user import User, UserRole
from .....schemas.user import User as UserSchema

router = APIRouter()


@router.get("/search", response_model=List[UserSchema])
def search_users(
    q: str = Query(..., min_length=1, description="Search query for user name or email"),
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> List[User]:
    """
    Search users by name or email (Admin only)
    Returns a list of users matching the search criteria.
    """
    # Build base query
    query = db.query(User).filter(
        or_(
            User.name.ilike(f"%{q}%"),
            User.email.ilike(f"%{q}%")
        )
    )
    
    # Apply filters
    if role is not None:
        query = query.filter(User.role == role)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    # Execute query with limit
    users = query.limit(limit).all()
    
    # Return just the users list - Pydantic will handle serialization
    return users
