from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from ....database import get_db
from ....dependencies import get_current_user
from ....models.user import User
from ....models.notification import Notification, NotificationType
from ....schemas.notification import (
    NotificationList,
    Notification as NotificationSchema,
    NotificationCreate,
    MarkAsRead
)

router = APIRouter()


@router.get("/me", response_model=NotificationList)
def get_my_notifications(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    unread_only: bool = Query(False)
) -> NotificationList:
    """
    Get current user's notifications
    """
    # Base query for user's notifications
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    # Filter by read status if requested
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    # Get total count
    total = query.count()
    
    # Get unread count
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    
    # Apply pagination and ordering
    notifications = query.order_by(Notification.created_at.desc()).offset(
        (page - 1) * size
    ).limit(size).all()
    
    return NotificationList(
        notifications=notifications,
        total=total,
        unread_count=unread_count
    )


@router.put("/mark-read", response_model=dict)
def mark_notifications_as_read(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    mark_data: MarkAsRead
) -> dict:
    """
    Mark notifications as read
    """
    # Update notifications
    updated_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.id.in_(mark_data.notification_ids)
    ).update(
        {
            "is_read": True,
            "read_at": func.now()
        },
        synchronize_session=False
    )
    
    db.commit()
    
    return {"message": f"Marked {updated_count} notifications as read"}


@router.put("/mark-all-read", response_model=dict)
def mark_all_notifications_as_read(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Mark all user's notifications as read
    """
    updated_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update(
        {
            "is_read": True,
            "read_at": func.now()
        },
        synchronize_session=False
    )
    
    db.commit()
    
    return {"message": f"Marked {updated_count} notifications as read"}


@router.post("/", response_model=NotificationSchema)
def create_notification(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    notification_data: NotificationCreate
) -> Notification:
    """
    Create a new notification (admin/instructor only)
    """
    # Check if user has permission to create notifications
    if current_user.role.value not in ["admin", "instructor"]:
        raise HTTPException(
            status_code=403,
            detail="Only admins and instructors can create notifications"
        )
    
    # Create notification
    notification = Notification(
        user_id=notification_data.user_id,
        title=notification_data.title,
        message=notification_data.message,
        type=notification_data.type,
        related_session_id=notification_data.related_session_id,
        related_booking_id=notification_data.related_booking_id
    )
    
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    return notification


@router.delete("/{notification_id}", response_model=dict)
def delete_notification(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    notification_id: int
) -> dict:
    """
    Delete a notification (user can only delete their own)
    """
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Notification not found"
        )
    
    db.delete(notification)
    db.commit()
    
    return {"message": "Notification deleted successfully"}