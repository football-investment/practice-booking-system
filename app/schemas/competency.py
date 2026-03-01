"""
Competency Schemas
Pydantic models for competency API
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict
from datetime import datetime


# ============================================================================
# COMPETENCY CATEGORY SCHEMAS
# ============================================================================

class CompetencyCategoryResponse(BaseModel):
    """Competency category response"""
    id: int
    name: str
    description: Optional[str]
    icon: Optional[str]
    specialization_id: str
    weight: float = Field(description="Category weight in overall assessment")
    display_order: int

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# SKILL SCHEMAS
# ============================================================================

class SkillResponse(BaseModel):
    """Competency skill response"""
    id: int
    name: str
    description: Optional[str]
    current_score: float = Field(description="0-100 skill score")
    current_level: str = Field(description="Beginner, Developing, Competent, Proficient, Expert")
    total_assessments: int
    last_assessed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# USER COMPETENCY SCHEMAS
# ============================================================================

class UserCompetencyResponse(BaseModel):
    """User's competency score for a category"""
    id: int
    user_id: int
    category_id: int
    category_name: str
    category_icon: Optional[str]
    specialization_id: str
    current_score: float = Field(description="0-100 category score")
    current_level: str = Field(description="Beginner, Developing, Competent, Proficient, Expert")
    total_assessments: int
    last_assessed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class CompetencyBreakdownResponse(BaseModel):
    """Detailed breakdown of category with skills"""
    category: Dict
    skills: List[Dict]

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# ASSESSMENT SCHEMAS
# ============================================================================

class AssessmentHistoryResponse(BaseModel):
    """Assessment history entry"""
    id: int
    category_name: Optional[str]
    skill_name: Optional[str]
    score: float
    source_type: str = Field(description="QUIZ or EXERCISE")
    source_id: int
    assessed_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# MILESTONE SCHEMAS
# ============================================================================

class MilestoneResponse(BaseModel):
    """Competency milestone response"""
    id: int
    milestone_id: int
    milestone_name: str
    description: Optional[str]
    icon: Optional[str]
    xp_reward: int
    specialization_id: str
    achieved_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# RADAR CHART DATA SCHEMA
# ============================================================================

class RadarChartDataResponse(BaseModel):
    """Data formatted for radar chart visualization"""
    categories: List[str] = Field(description="Category names")
    scores: List[float] = Field(description="Category scores (0-100)")
    levels: List[str] = Field(description="Category levels")
    colors: List[str] = Field(description="Category colors for visualization")

    model_config = ConfigDict(from_attributes=True)
