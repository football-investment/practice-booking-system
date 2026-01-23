"""
User endpoint helper utilities
Shared functions for pagination, validation, and statistics
"""
from typing import Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import re

from .....models.user import User


def calculate_pagination(
    page: int,
    size: int,
    skip: int = None,
    limit: int = None
) -> Tuple[int, int, int]:
    """
    Calculate pagination offset and page size.
    Supports both page/size and skip/limit modes.
    
    Args:
        page: Current page number (1-indexed)
        size: Items per page
        skip: Optional skip count (backward compatibility)
        limit: Optional limit count (backward compatibility)
    
    Returns:
        Tuple of (offset, page_size, current_page)
    """
    if skip is not None and limit is not None:
        # Backward compatibility: use skip/limit
        offset = skip
        page_size = limit
        current_page = (skip // limit) + 1 if limit > 0 else 1
    else:
        # Standard: use page/size
        offset = (page - 1) * size
        page_size = size
        current_page = page
    
    return offset, page_size, current_page


def validate_email_unique(db: Session, email: str, exclude_user_id: int = None) -> bool:
    """
    Check if email is unique in database.
    
    Args:
        db: Database session
        email: Email to check
        exclude_user_id: Optional user ID to exclude from check (for updates)
    
    Returns:
        True if email is unique, False otherwise
    """
    query = db.query(User).filter(User.email == email)
    if exclude_user_id:
        query = query.filter(User.id != exclude_user_id)
    
    return query.first() is None


def validate_nickname(nickname: str, db: Session, current_user_id: int = None) -> Tuple[bool, str]:
    """
    Validate nickname availability and format.
    
    Args:
        nickname: Nickname to validate
        db: Database session
        current_user_id: Optional current user ID (to allow keeping own nickname)
    
    Returns:
        Tuple of (is_valid, message)
    """
    # Basic validation
    if not nickname or len(nickname.strip()) < 3:
        return False, "A becenév legalább 3 karakter hosszú legyen"
    
    if len(nickname) > 30:
        return False, "A becenév maximum 30 karakter lehet"
    
    # Check for inappropriate characters
    if not re.match("^[a-zA-Z0-9_áéíóöőúüűÁÉÍÓÖŐÚÜŰ]+$", nickname):
        return False, "A becenév csak betűket, számokat és aláhúzást tartalmazhat"
    
    # Check if already exists (case insensitive)
    query = db.query(User).filter(func.lower(User.nickname) == nickname.lower())
    if current_user_id:
        query = query.filter(User.id != current_user_id)
    
    existing_user = query.first()
    if existing_user:
        return False, "Ez a becenév már foglalt. Kérjük, válasszon másikat!"
    
    # Check against reserved nicknames
    reserved_nicknames = ['admin', 'moderator', 'system', 'support', 'help', 'info', 'test']
    if nickname.lower() in reserved_nicknames:
        return False, "Ez a becenév foglalt. Kérjük, válasszon másikat!"
    
    return True, "Remek! Ez a becenév elérhető."


def get_user_statistics(db: Session, user_id: int) -> dict:
    """
    Get statistics for a user.
    
    Args:
        db: Database session
        user_id: User ID
    
    Returns:
        Dictionary with user statistics
    """
    from .....models.booking import Booking
    from .....models.attendance import Attendance
    from .....models.feedback import Feedback
    
    total_bookings = db.query(func.count(Booking.id)).filter(
        Booking.user_id == user_id
    ).scalar()
    
    completed_sessions = db.query(func.count(Attendance.id)).filter(
        and_(Attendance.user_id == user_id, Attendance.status == "present")
    ).scalar()
    
    feedback_count = db.query(func.count(Feedback.id)).filter(
        Feedback.user_id == user_id
    ).scalar()
    
    return {
        'total_bookings': total_bookings or 0,
        'completed_sessions': completed_sessions or 0,
        'feedback_count': feedback_count or 0
    }


def serialize_enum_value(value):
    """
    Serialize enum value to string.
    
    Args:
        value: Enum value or string
    
    Returns:
        String representation of value
    """
    if value is None:
        return None
    return value.value if hasattr(value, 'value') else str(value)
