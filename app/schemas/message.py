from pydantic import BaseModel, ConfigDict, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MessagePriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class MessageUserInfo(BaseModel):
    id: int
    name: str
    nickname: Optional[str] = None
    email: str
    
    model_config = ConfigDict(from_attributes=True)


class MessageBase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    subject: str
    message: str
    priority: MessagePriority = MessagePriority.NORMAL


class MessageCreate(MessageBase):
    recipient_id: int
    
    @validator('subject')
    def subject_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Subject cannot be empty')
        return v
    
    @validator('message')
    def message_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v


class MessageCreateByNickname(MessageBase):
    recipient_nickname: str
    
    @validator('subject')
    def subject_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Subject cannot be empty')
        return v
    
    @validator('message')
    def message_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v


class MessageUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    is_read: Optional[bool] = None
    message: Optional[str] = None
    
    @validator('message')
    def message_must_not_be_empty_if_provided(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Message cannot be empty')
        return v


class Message(MessageBase):
    id: int
    sender_id: int
    recipient_id: int
    is_read: bool
    is_edited: Optional[bool] = False
    created_at: datetime
    read_at: Optional[datetime] = None
    edited_at: Optional[datetime] = None
    sender: MessageUserInfo
    recipient: MessageUserInfo
    
    model_config = ConfigDict(from_attributes=True)


class MessageList(BaseModel):
    messages: List[Message]
    total_count: int
    unread_count: int
    
    model_config = ConfigDict(from_attributes=True)


class MessageSummary(BaseModel):
    id: int
    subject: str
    message_preview: str
    priority: MessagePriority
    is_read: bool
    created_at: datetime
    sender: MessageUserInfo
    recipient: MessageUserInfo
    
    @validator('message_preview', pre=True)
    def create_preview(cls, v, values):
        if 'message' in values:
            return values['message'][:100] + '...' if len(values['message']) > 100 else values['message']
        return v
    
    class Config:
        from_attributes = True