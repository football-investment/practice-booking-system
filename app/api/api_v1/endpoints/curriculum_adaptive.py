"""
Curriculum-Based Adaptive Learning API Endpoints
Personalized learning recommendations and profile management for curriculum system
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from ....dependencies import get_current_user
from app.models.user import User
from app.services.adaptive_learning_service import AdaptiveLearningService
from app.schemas.adaptive_learning import (
    LearningProfileResponse,
    RecommendationResponse,
    PerformanceSnapshotResponse
)

router = APIRouter()


@router.get("/profile", response_model=LearningProfileResponse)
def get_learning_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's learning profile

    Returns personalized learning metrics:
    - Learning pace (SLOW, MEDIUM, FAST, ACCELERATED)
    - Quiz average score
    - Lessons completed count
    - Preferred content type
    - Last activity timestamp
    """
    service = AdaptiveLearningService(db)
    profile = service.get_or_create_profile(current_user.id)
    return profile


@router.post("/profile/update", response_model=LearningProfileResponse)
def update_learning_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Force recalculation of learning profile metrics

    Useful after:
    - Completing several lessons
    - Finishing quizzes
    - Changing study patterns
    """
    service = AdaptiveLearningService(db)
    profile = service.update_profile_metrics(current_user.id)
    return profile


@router.get("/recommendations", response_model=List[RecommendationResponse])
def get_recommendations(
    refresh: bool = Query(False, description="Force regenerate recommendations"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI-powered learning recommendations

    Recommendation types:
    - REVIEW_LESSON: Review weak topics
    - CONTINUE_LEARNING: Next lesson suggestion
    - TAKE_BREAK: Burnout prevention
    - RESUME_LEARNING: Inactivity reminder
    - PRACTICE_MORE: Practice exercises suggestion
    - START_LEARNING: First lesson prompt

    By default, returns cached recommendations (last 24h).
    Set refresh=true to force regeneration.
    """
    service = AdaptiveLearningService(db)
    recommendations = service.generate_recommendations(current_user.id, refresh=refresh)
    return recommendations


@router.post("/recommendations/{recommendation_id}/dismiss")
def dismiss_recommendation(
    recommendation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Dismiss a recommendation

    Marks the recommendation as inactive so it won't appear again.
    """
    service = AdaptiveLearningService(db)
    service.dismiss_recommendation(current_user.id, recommendation_id)
    return {"success": True, "message": "Recommendation dismissed"}


@router.get("/performance-history", response_model=List[PerformanceSnapshotResponse])
def get_performance_history(
    days: int = Query(30, description="Number of days to retrieve", ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get performance history snapshots

    Returns daily performance data:
    - Pace score
    - Quiz average
    - Lessons completed
    - Time spent studying

    Useful for charts and progress tracking.
    """
    service = AdaptiveLearningService(db)
    history = service.get_performance_history(current_user.id, days=days)
    return history


@router.post("/snapshot")
def create_performance_snapshot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create daily performance snapshot

    Called automatically by background job, but can be triggered manually.
    Captures today's learning metrics for historical tracking.
    """
    service = AdaptiveLearningService(db)
    service.create_daily_snapshot(current_user.id)
    return {"success": True, "message": "Performance snapshot created"}
