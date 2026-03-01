from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from ..models.notification import NotificationType


class NotificationBase(BaseModel):


    title: str
    message: str
    type: NotificationType = NotificationType.GENERAL
    related_session_id: Optional[int] = None
    related_booking_id: Optional[int] = None
    # New fields for instructor job offers
    link: Optional[str] = None
    related_semester_id: Optional[int] = None
    related_request_id: Optional[int] = None


class NotificationCreate(NotificationBase):
    user_id: int


class NotificationUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    title: Optional[str] = None
    message: Optional[str] = None
    type: Optional[NotificationType] = None
    is_read: Optional[bool] = None


class Notification(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationList(BaseModel):
    notifications: List[Notification]
    total: int
    unread_count: int


class MarkAsRead(BaseModel):
    notification_ids: List[int]