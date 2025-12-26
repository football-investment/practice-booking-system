"""
Gamification Utility Functions
Common helper functions used across gamification modules
"""
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ...models.gamification import UserStats


def get_or_create_user_stats(db: Session, user_id: int) -> UserStats:
    """
    Get or create user statistics

    Args:
        db: Database session
        user_id: User ID

    Returns:
        UserStats object (existing or newly created)
    """
    stats = db.query(UserStats).filter(UserStats.user_id == user_id).first()
    if not stats:
        stats = UserStats(user_id=user_id)
        db.add(stats)
        db.commit()
        db.refresh(stats)
    return stats
