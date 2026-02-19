"""
Motivation Assessment Schemas
==============================
Pydantic models for specialization-specific motivation/preference assessments.
These assessments are completed ONCE after specialization unlock.
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


# ==================== LFA PLAYER MOTIVATION ====================

class PlayerPosition(str, Enum):
    """Football player positions"""
    STRIKER = "Striker"
    MIDFIELDER = "Midfielder"
    DEFENDER = "Defender"
    GOALKEEPER = "Goalkeeper"


class LFAPlayerMotivation(BaseModel):
    """
    LFA Player self-assessment of 7 football skills (1-10 scale) + position preference

    Student rates their current skill level and selects their preferred playing position.
    Later, instructor assessments will provide actual skill averages (0-100 scale).
    """
    # Position preference
    preferred_position: PlayerPosition = Field(..., description="Preferred playing position")

    # 7 skill self-ratings (1-10 scale)
    heading_self_rating: int = Field(..., ge=1, le=10, description="Self-rating for heading skill")
    shooting_self_rating: int = Field(..., ge=1, le=10, description="Self-rating for shooting skill")
    crossing_self_rating: int = Field(..., ge=1, le=10, description="Self-rating for crossing skill")
    passing_self_rating: int = Field(..., ge=1, le=10, description="Self-rating for passing skill")
    dribbling_self_rating: int = Field(..., ge=1, le=10, description="Self-rating for dribbling skill")
    ball_control_self_rating: int = Field(..., ge=1, le=10, description="Self-rating for ball control skill")
    defending_self_rating: int = Field(..., ge=1, le=10, description="Self-rating for defending skill")

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON for user_licenses.motivation_scores"""
        return {
            "preferred_position": self.preferred_position.value,
            "heading": self.heading_self_rating,
            "shooting": self.shooting_self_rating,
            "crossing": self.crossing_self_rating,
            "passing": self.passing_self_rating,
            "dribbling": self.dribbling_self_rating,
            "ball_control": self.ball_control_self_rating,
            "defending": self.defending_self_rating
        }


# ==================== GANCUJU MOTIVATION ====================

class GanCujuCharacterType(str, Enum):
    """Character path selection for GānCuju specialization"""
    WARRIOR = "warrior"
    TEACHER = "teacher"


class GanCujuMotivation(BaseModel):
    """
    GānCuju character type selection

    Determines student's focus:
    - Warrior: Competition-focused, winning mindset
    - Teacher: Knowledge transfer, teaching others
    """
    character_type: GanCujuCharacterType = Field(..., description="Warrior or Teacher path")

    def to_json(self) -> Dict[str, str]:
        """Convert to JSON for user_licenses.motivation_scores"""
        return {
            "character_type": self.character_type.value
        }


# ==================== COACH MOTIVATION ====================

class CoachAgeGroupPreference(str, Enum):
    """Preferred age group to coach"""
    PRE = "PRE"
    YOUTH = "YOUTH"
    AMATEUR = "AMATEUR"
    PRO = "PRO"
    ALL = "ALL"


class CoachRolePreference(str, Enum):
    """Preferred coaching role"""
    TECHNICAL_COACH = "Technical Coach"
    FITNESS_COACH = "Fitness Coach"
    TACTICAL_ANALYST = "Tactical Analyst"
    GOALKEEPING_COACH = "Goalkeeping Coach"
    HEAD_COACH = "Head Coach"
    COACHING_COORDINATOR = "Coaching Coordinator"


class CoachSpecializationArea(str, Enum):
    """Preferred specialization area"""
    ATTACKING_PLAY = "Attacking play"
    DEFENSIVE_PLAY = "Defensive play"
    GOALKEEPING = "Goalkeeping"
    SET_PIECES = "Set pieces"
    MENTAL_COACHING = "Mental coaching"


class CoachMotivation(BaseModel):
    """
    Coach specialization preferences

    Helps determine which coaching path the student prefers.
    """
    age_group_preference: CoachAgeGroupPreference = Field(..., description="Preferred age group to coach")
    role_preference: CoachRolePreference = Field(..., description="Preferred coaching role")
    specialization_area: CoachSpecializationArea = Field(..., description="Preferred specialization area")

    def to_json(self) -> Dict[str, str]:
        """Convert to JSON for user_licenses.motivation_scores"""
        return {
            "age_group_preference": self.age_group_preference.value,
            "role_preference": self.role_preference.value,
            "specialization_area": self.specialization_area.value
        }


# ==================== INTERNSHIP MOTIVATION ====================

class InternshipDepartment(str, Enum):
    """Department categories for internship positions"""
    ADMINISTRATIVE = "Administrative"
    FACILITY_MANAGEMENT = "Facility Management"
    COMMERCIAL = "Commercial"
    COMMUNICATIONS = "Communications"
    ACADEMY = "Academy"
    INTERNATIONAL = "International"


class InternshipPosition(str, Enum):
    """Available internship positions (45 total)"""
    # Administrative (6)
    SPORTS_DIRECTOR = "LFA Sports Director"
    DIGITAL_MARKETING_MANAGER = "LFA Digital Marketing Manager"
    SOCIAL_MEDIA_MANAGER = "LFA Social Media Manager"
    ADVERTISING_SPECIALIST = "LFA Advertising Specialist"
    BRAND_MANAGER = "LFA Brand Manager"
    EVENT_ORGANIZER = "LFA Event Organizer"

    # Facility Management (6)
    FACILITY_MANAGER = "LFA Facility Manager"
    TECHNICAL_MANAGER = "LFA Technical Manager"
    MAINTENANCE_TECHNICIAN = "LFA Maintenance Technician"
    ENERGY_SPECIALIST = "LFA Energy Specialist"
    GROUNDSKEEPING_SPECIALIST = "LFA Groundskeeping Specialist"
    SECURITY_DIRECTOR = "LFA Security Director"

    # Commercial (7)
    RETAIL_MANAGER = "LFA Retail Manager"
    INVENTORY_MANAGER = "LFA Inventory Manager"
    SALES_REPRESENTATIVE = "LFA Sales Representative"
    WEBSHOP_MANAGER = "LFA Webshop Manager"
    TICKET_OFFICE_MANAGER = "LFA Ticket Office Manager"
    CUSTOMER_SERVICE_AGENT = "LFA Customer Service Agent"
    VIP_RELATIONS_MANAGER = "LFA VIP Relations Manager"

    # Communications (5)
    PRESS_OFFICER = "LFA Press Officer"
    SPOKESPERSON = "LFA Spokesperson"
    CONTENT_CREATOR = "LFA Content Creator"
    PHOTOGRAPHER = "LFA Photographer"
    VIDEOGRAPHER = "LFA Videographer"

    # Academy (3)
    TALENT_SCOUT = "LFA Talent Scout"
    MENTAL_COACH = "LFA Mental Coach"
    SOCIAL_WORKER = "LFA Social Worker"

    # International (3)
    REGIONAL_DIRECTOR = "LFA Regional Director"
    LIAISON_OFFICER = "LFA Liaison Officer"
    BUSINESS_DEVELOPMENT_MANAGER = "LFA Business Development Manager"


class InternshipMotivation(BaseModel):
    """
    Internship position preferences (1-7 selections)

    Student selects between 1 and 7 positions from 45 available.
    No duplicates allowed, minimum 1 required, maximum 7 allowed.
    """
    selected_positions: list[str] = Field(
        ...,
        min_items=1,
        max_items=7,
        description="Selected internship positions (1-7 selections, no duplicates)"
    )

    @validator('selected_positions')
    def validate_positions(cls, v):
        """Validate positions: check uniqueness and valid values"""
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Duplicate positions are not allowed")

        # Check for valid positions
        valid_positions = [pos.value for pos in InternshipPosition]
        for position in v:
            if position not in valid_positions:
                raise ValueError(f"Invalid position: {position}. Must be one of: {', '.join(valid_positions)}")

        return v

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON for user_licenses.motivation_scores"""
        return {
            "selected_positions": self.selected_positions,
            "position_count": len(self.selected_positions)
        }


# ==================== UNIFIED MOTIVATION REQUEST ====================

class MotivationAssessmentRequest(BaseModel):
    """
    Unified motivation assessment request

    Accepts motivation data for any specialization type.
    Only ONE field should be populated based on specialization.
    """
    lfa_player: Optional[LFAPlayerMotivation] = None
    gancuju: Optional[GanCujuMotivation] = None
    coach: Optional[CoachMotivation] = None
    internship: Optional[InternshipMotivation] = None

    @validator('internship')
    def validate_single_spec(cls, v, values):
        """
        Ensure only ONE specialization data is provided

        Runs on the LAST field (internship) after all fields parsed.
        This way we can check all 4 fields are populated correctly.
        """
        populated = sum([
            values.get('lfa_player') is not None,
            values.get('gancuju') is not None,
            values.get('coach') is not None,
            v is not None
        ])
        if populated > 1:
            raise ValueError("Only one specialization motivation should be provided")
        if populated == 0:
            raise ValueError("At least one specialization motivation must be provided")
        return v

    def get_motivation_data(self) -> Dict[str, Any]:
        """Extract the populated motivation data"""
        if self.lfa_player:
            return self.lfa_player.to_json()
        elif self.gancuju:
            return self.gancuju.to_json()
        elif self.coach:
            return self.coach.to_json()
        elif self.internship:
            return self.internship.to_json()
        else:
            raise ValueError("No motivation data provided")


class MotivationAssessmentResponse(BaseModel):
    """Response after motivation assessment submission"""
    success: bool
    message: str
    motivation_data: Dict[str, Any]
