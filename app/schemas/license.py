"""
License schemas for API validation
"""
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime


class FootballSkillsBase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """6 football skills with percentage values (0-100)"""
    heading: float = Field(..., ge=0.0, le=100.0, description="Heading skill percentage (0-100)")
    shooting: float = Field(..., ge=0.0, le=100.0, description="Shooting skill percentage (0-100)")
    crossing: float = Field(..., ge=0.0, le=100.0, description="Crossing skill percentage (0-100)")
    passing: float = Field(..., ge=0.0, le=100.0, description="Passing skill percentage (0-100)")
    dribbling: float = Field(..., ge=0.0, le=100.0, description="Dribbling skill percentage (0-100)")
    ball_control: float = Field(..., ge=0.0, le=100.0, description="Ball control skill percentage (0-100)")

    @field_validator('heading', 'shooting', 'crossing', 'passing', 'dribbling', 'ball_control')
    @classmethod
    def round_to_one_decimal(cls, v: float) -> float:
        """Round to 1 decimal place for cleaner display"""
        return round(v, 1)


class FootballSkillsUpdate(FootballSkillsBase):
    """Request body for updating football skills (instructor only)"""
    instructor_notes: Optional[str] = Field(None, max_length=500, description="Optional notes about the skill assessment")


class FootballSkillsResponse(FootballSkillsBase):
    """Response with football skills and metadata"""
    skills_last_updated_at: Optional[datetime] = None
    skills_updated_by_id: Optional[int] = None
    skills_updated_by_name: Optional[str] = None
    instructor_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LicenseWithSkillsResponse(BaseModel):
    """User license with optional football skills (for LFA Player specs)"""
    id: int
    user_id: int
    specialization_type: str
    current_level: int
    max_achieved_level: int
    started_at: datetime
    last_advanced_at: Optional[datetime] = None

    # Football skills (only populated for LFA_PLAYER_* specializations)
    football_skills: Optional[FootballSkillsResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ⚽ NEW: Skill Assessment Schemas (Points-based system)

class SkillAssessmentCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Create a new skill assessment (instructor submits points)"""
    skill_name: str = Field(..., description="Skill name: heading, shooting, crossing, passing, dribbling, ball_control")
    points_earned: int = Field(..., ge=0, description="Points earned (e.g., 7)")
    points_total: int = Field(..., gt=0, description="Total points possible (e.g., 10)")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes about this assessment")

    @model_validator(mode='after')
    def validate_points(self):
        """Ensure points_earned <= points_total"""
        if self.points_earned > self.points_total:
            raise ValueError(f"Points earned ({self.points_earned}) cannot exceed total points ({self.points_total})")
        return self

    @field_validator('skill_name')
    @classmethod
    def validate_skill_name(cls, v: str) -> str:
        """Validate skill name is one of the 6 allowed skills"""
        allowed_skills = ['heading', 'shooting', 'crossing', 'passing', 'dribbling', 'ball_control']
        if v.lower() not in allowed_skills:
            raise ValueError(f"Skill must be one of: {', '.join(allowed_skills)}")
        return v.lower()


class SkillAssessmentResponse(BaseModel):
    """Single skill assessment response"""
    id: int
    user_license_id: int
    skill_name: str
    points_earned: int
    points_total: int
    percentage: float
    assessed_by: int
    assessed_at: datetime
    notes: Optional[str] = None
    assessor_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SkillAssessmentHistoryResponse(BaseModel):
    """Assessment history for a specific skill"""
    skill_name: str
    current_average: float
    assessment_count: int
    assessments: List[SkillAssessmentResponse]

    model_config = ConfigDict(from_attributes=True)


class BulkSkillAssessmentCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Create assessments for all 6 skills at once"""
    heading: SkillAssessmentCreate
    shooting: SkillAssessmentCreate
    crossing: SkillAssessmentCreate
    passing: SkillAssessmentCreate
    dribbling: SkillAssessmentCreate
    ball_control: SkillAssessmentCreate
