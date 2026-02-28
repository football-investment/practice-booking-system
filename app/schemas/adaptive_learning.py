"""
Adaptive Learning Schemas
Pydantic models for adaptive learning API
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# LEARNING PROFILE SCHEMAS
# ============================================================================

class LearningProfileResponse(BaseModel):
    """User learning profile response"""
    id: int
    user_id: int
    learning_pace: str = Field(description="SLOW, MEDIUM, FAST, ACCELERATED")
    pace_score: float = Field(description="0-100 pace score")
    quiz_average_score: float = Field(description="Weighted average of last 10 quizzes")
    lessons_completed_count: int
    avg_time_per_lesson_minutes: float
    preferred_content_type: str = Field(description="VIDEO, TEXT, PRACTICE")
    last_activity_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# RECOMMENDATION SCHEMAS
# ============================================================================

class RecommendationResponse(BaseModel):
    """AI recommendation response"""
    id: int
    type: str = Field(description="REVIEW_LESSON, CONTINUE_LEARNING, TAKE_BREAK, etc.")
    title: str
    message: str
    priority: int = Field(description="0-100, higher = more important")
    metadata: Dict[str, Any]
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GenerateRecommendationsRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Request to generate new recommendations"""
    refresh: bool = Field(default=False, description="Force regenerate recommendations")


# ============================================================================
# PERFORMANCE TRACKING SCHEMAS
# ============================================================================

class PerformanceSnapshotResponse(BaseModel):
    """Daily performance snapshot"""
    date: datetime
    pace_score: float
    quiz_average: float
    lessons_completed: int
    time_spent: float = Field(description="Minutes spent studying today")

    model_config = ConfigDict(from_attributes=True)


class PerformanceHistoryRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Request performance history"""
    days: int = Field(default=30, description="Number of days to retrieve", ge=1, le=365)


# ============================================================================
# ANALYTICS SCHEMAS
# ============================================================================

class LearningAnalytics(BaseModel):
    """Comprehensive learning analytics"""
    profile: LearningProfileResponse
    recommendations: List[RecommendationResponse]
    recent_performance: List[PerformanceSnapshotResponse]

    # Additional metrics
    total_study_time_minutes: float
    average_session_duration: float
    consistency_score: float = Field(description="0-100, based on regular study habits")

    model_config = ConfigDict(from_attributes=True)
