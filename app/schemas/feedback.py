from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
from .user import User
from .session import Session


class FeedbackBase(BaseModel):


    session_id: int
    rating: float
    instructor_rating: Optional[float] = None
    session_quality: Optional[float] = None
    would_recommend: Optional[bool] = None
    comment: Optional[str] = None
    is_anonymous: bool = False

    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        if not 1.0 <= v <= 5.0:
            raise ValueError('Rating must be between 1.0 and 5.0')
        return v

    @field_validator('instructor_rating')
    @classmethod
    def validate_instructor_rating(cls, v):
        if v is not None and not 1.0 <= v <= 5.0:
            raise ValueError('Instructor rating must be between 1.0 and 5.0')
        return v

    @field_validator('session_quality')
    @classmethod
    def validate_session_quality(cls, v):
        if v is not None and not 1.0 <= v <= 5.0:
            raise ValueError('Session quality must be between 1.0 and 5.0')
        return v


class FeedbackCreate(FeedbackBase):
    pass


class FeedbackUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    rating: Optional[float] = None
    instructor_rating: Optional[float] = None
    session_quality: Optional[float] = None
    would_recommend: Optional[bool] = None
    comment: Optional[str] = None
    is_anonymous: Optional[bool] = None

    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        if v is not None and not 1.0 <= v <= 5.0:
            raise ValueError('Rating must be between 1.0 and 5.0')
        return v

    @field_validator('instructor_rating')
    @classmethod
    def validate_instructor_rating(cls, v):
        if v is not None and not 1.0 <= v <= 5.0:
            raise ValueError('Instructor rating must be between 1.0 and 5.0')
        return v

    @field_validator('session_quality')
    @classmethod
    def validate_session_quality(cls, v):
        if v is not None and not 1.0 <= v <= 5.0:
            raise ValueError('Session quality must be between 1.0 and 5.0')
        return v


class Feedback(FeedbackBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FeedbackWithRelations(Feedback):
    user: Optional[User] = None  # None if anonymous
    session: Session


class FeedbackList(BaseModel):
    feedbacks: List[FeedbackWithRelations]
    total: int
    page: int
    size: int


class FeedbackSummary(BaseModel):
    session_id: int
    average_rating: float
    total_feedback: int
    rating_distribution: dict  # {1: count, 2: count, ...}
    recent_comments: List[str]