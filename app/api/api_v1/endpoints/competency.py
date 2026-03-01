"""
Competency API Endpoints
Automatic competency assessment and skill tracking
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from ....dependencies import get_current_user
from app.models.user import User
from app.services.competency_service import CompetencyService
from app.schemas.competency import (
    UserCompetencyResponse,
    CompetencyBreakdownResponse,
    AssessmentHistoryResponse,
    MilestoneResponse,
    RadarChartDataResponse,
    CompetencyCategoryResponse
)

router = APIRouter()


@router.get("/my-competencies", response_model=List[UserCompetencyResponse])
def get_my_competencies(
    specialization_id: Optional[str] = Query(None, description="Filter by specialization (PLAYER, COACH, INTERNSHIP)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's competency scores

    Returns all competency categories with current scores and levels.
    Automatically assessed from quizzes and exercises.

    Competency levels:
    - Beginner (0-39%)
    - Developing (40-59%)
    - Competent (60-74%)
    - Proficient (75-89%)
    - Expert (90-100%)
    """
    try:
        service = CompetencyService(db)
        competencies = service.get_user_competencies(current_user.id, specialization_id)
        return competencies
    except Exception as e:
        # Log the error but return empty list instead of 500
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching competencies for user {current_user.id}: {str(e)}")
        # Return empty list if tables don't exist or other database error
        return []


@router.get("/categories", response_model=List[CompetencyCategoryResponse])
def get_competency_categories(
    specialization_id: str = Query(..., description="Specialization ID (PLAYER, COACH, INTERNSHIP)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all competency categories for a specialization

    Returns the competency framework structure.
    """
    from sqlalchemy import text

    results = db.execute(text("""
        SELECT * FROM competency_categories
        WHERE specialization_id = :spec_id
        ORDER BY display_order
    """), {"spec_id": specialization_id}).fetchall()

    return [{
        "id": r.id,
        "name": r.name,
        "description": r.description,
        "icon": r.icon,
        "specialization_id": r.specialization_id,
        "weight": float(r.weight),
        "display_order": r.display_order
    } for r in results]


@router.get("/breakdown/{category_id}", response_model=CompetencyBreakdownResponse)
def get_competency_breakdown(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed breakdown of a competency category

    Returns:
    - Overall category score and level
    - Individual skill scores within the category
    - Assessment count for each skill
    """
    service = CompetencyService(db)
    breakdown = service.get_competency_breakdown(current_user.id, category_id)

    if not breakdown:
        raise HTTPException(status_code=404, detail="Category not found")

    return breakdown


@router.get("/assessment-history", response_model=List[AssessmentHistoryResponse])
def get_assessment_history(
    limit: int = Query(20, description="Number of recent assessments", ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get recent competency assessment history

    Shows how competencies were assessed over time:
    - From quiz attempts
    - From exercise submissions
    """
    try:
        service = CompetencyService(db)
        history = service.get_assessment_history(current_user.id, limit)
        return history
    except Exception as e:
        # Defensive: If competency tables don't exist, return empty list
        # (tables are optional feature, not required for base functionality)
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Assessment history unavailable for user {current_user.id}: {str(e)}")
        return []


@router.get("/milestones", response_model=List[MilestoneResponse])
def get_user_milestones(
    specialization_id: Optional[str] = Query(None, description="Filter by specialization"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's achieved competency milestones

    Milestones are awarded when:
    - Overall competency score reaches threshold
    - All skills in category reach minimum level
    - Specific skill mastery is demonstrated

    Each milestone awards XP.
    """
    try:
        service = CompetencyService(db)
        milestones = service.get_user_milestones(current_user.id, specialization_id)
        return milestones
    except Exception as e:
        # Defensive: If competency tables don't exist, return empty list
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Milestones unavailable for user {current_user.id}: {str(e)}")
        return []


@router.get("/radar-chart-data", response_model=RadarChartDataResponse)
def get_radar_chart_data(
    specialization_id: str = Query(..., description="Specialization ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get competency data formatted for radar chart visualization

    Returns parallel arrays:
    - categories: Category names
    - scores: Category scores (0-100)
    - levels: Category levels
    - colors: Suggested colors for each category
    """
    service = CompetencyService(db)
    competencies = service.get_user_competencies(current_user.id, specialization_id)

    if not competencies:
        return {
            "categories": [],
            "scores": [],
            "levels": [],
            "colors": []
        }

    # Color mapping for levels
    level_colors = {
        "Beginner": "#ff4d4f",
        "Developing": "#faad14",
        "Competent": "#1890ff",
        "Proficient": "#52c41a",
        "Expert": "#722ed1"
    }

    return {
        "categories": [c["category_name"] for c in competencies],
        "scores": [c["current_score"] for c in competencies],
        "levels": [c["current_level"] for c in competencies],
        "colors": [level_colors.get(c["current_level"], "#d9d9d9") for c in competencies]
    }
