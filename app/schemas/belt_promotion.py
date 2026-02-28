"""
🥋 Belt Promotion Schemas - Gancuju Belt System
Pydantic schemas for belt promotion requests and responses
"""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from datetime import datetime


class BeltPromotionCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Schema for creating a belt promotion"""
    notes: Optional[str] = Field(None, description="Promotion notes")
    exam_score: Optional[int] = Field(None, ge=0, le=100, description="Exam score (0-100)")
    exam_notes: Optional[str] = Field(None, description="Exam notes/feedback")

    @field_validator('exam_score')
    @classmethod
    def validate_exam_score(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Exam score must be between 0 and 100')
        return v


class InitialBeltAssignment(BaseModel):
    """Schema for assigning initial belt to new student"""
    notes: Optional[str] = Field(None, description="Assignment notes")


class BeltPromotionResponse(BaseModel):
    """Schema for belt promotion API response"""
    id: int
    user_license_id: int
    from_belt: Optional[str]
    to_belt: str
    promoted_by: int
    promoted_at: datetime
    notes: Optional[str]
    exam_score: Optional[int]
    exam_notes: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class BeltHistoryResponse(BaseModel):
    """Schema for belt promotion history"""
    id: int
    from_belt: Optional[str]
    from_belt_info: Optional[dict]
    to_belt: str
    to_belt_info: dict
    promoted_by: int
    promoter_name: str
    promoted_at: str
    notes: Optional[str]
    exam_score: Optional[int]
    exam_notes: Optional[str]


class BeltStatusResponse(BaseModel):
    """Schema for current belt status"""
    current_belt: str
    current_belt_info: dict
    next_belt: Optional[str]
    next_belt_info: Optional[dict]
    promotion_count: int
    latest_promotion: Optional[BeltHistoryResponse]
