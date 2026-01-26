from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from ..models.semester import SemesterStatus


class SemesterBase(BaseModel):
    code: str
    name: str
    start_date: date
    end_date: date
    status: SemesterStatus = SemesterStatus.DRAFT
    is_active: bool = True
    enrollment_cost: int = 500
    master_instructor_id: Optional[int] = None
    specialization_type: Optional[str] = None
    age_group: Optional[str] = None
    theme: Optional[str] = None
    focus_description: Optional[str] = None
    location_city: Optional[str] = None
    location_venue: Optional[str] = None
    location_address: Optional[str] = None
    assignment_type: Optional[str] = None  # 🔥 FIX: Add assignment_type for tournaments
    max_players: Optional[int] = None  # 🔥 FIX: Add max_players for tournaments
    tournament_type_id: Optional[int] = None  # FK to tournament_types table
    format: Optional[str] = None  # Tournament format: HEAD_TO_HEAD or INDIVIDUAL_RANKING
    scoring_type: Optional[str] = None  # Scoring type: TIME_BASED, DISTANCE_BASED, SCORE_BASED, PLACEMENT
    measurement_unit: Optional[str] = None  # Measurement unit for INDIVIDUAL_RANKING
    ranking_direction: Optional[str] = None  # Ranking direction: ASC (lowest wins) or DESC (highest wins)


class SemesterCreate(SemesterBase):
    pass


class SemesterUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[SemesterStatus] = None
    is_active: Optional[bool] = None
    enrollment_cost: Optional[int] = None
    master_instructor_id: Optional[int] = None

    # Tournament-specific fields (admin MUST be able to edit these)
    specialization_type: Optional[str] = None
    age_group: Optional[str] = None
    theme: Optional[str] = None
    focus_description: Optional[str] = None
    location_id: Optional[int] = None
    campus_id: Optional[int] = None
    tournament_type_id: Optional[int] = None
    assignment_type: Optional[str] = None
    max_players: Optional[int] = None
    participant_type: Optional[str] = None
    is_multi_day: Optional[bool] = None
    tournament_status: Optional[str] = None
    format: Optional[str] = None  # Tournament format
    scoring_type: Optional[str] = None  # Scoring type
    measurement_unit: Optional[str] = None  # Measurement unit
    ranking_direction: Optional[str] = None  # Ranking direction


class Semester(SemesterBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    tournament_status: Optional[str] = None  # Tournament-specific status

    model_config = ConfigDict(from_attributes=True)


class SemesterWithStats(Semester):
    total_groups: int
    total_sessions: int
    total_bookings: int
    active_users: int
    location_type: Optional[str] = None  # PARTNER or CENTER from location relationship
    master_instructor_name: Optional[str] = None  # Instructor name
    master_instructor_email: Optional[str] = None  # Instructor email
    sessions_generated: Optional[bool] = None  # Tournament sessions auto-generation flag
    sessions_generated_at: Optional[datetime] = None  # When sessions were generated
    reward_policy_name: Optional[str] = None  # Reward policy identifier
    reward_policy_snapshot: Optional[dict] = None  # Complete reward policy configuration (V1)
    reward_config: Optional[dict] = None  # V2 reward configuration with skills & badges
    match_duration_minutes: Optional[int] = None  # Match duration configuration for tournaments
    break_duration_minutes: Optional[int] = None  # Break duration configuration for tournaments
    parallel_fields: Optional[int] = None  # Number of parallel fields/pitches (1-4)
    format: Optional[str] = "INDIVIDUAL_RANKING"  # Tournament format: HEAD_TO_HEAD or INDIVIDUAL_RANKING
    scoring_type: Optional[str] = "PLACEMENT"  # Scoring type: TIME_BASED, DISTANCE_BASED, SCORE_BASED, PLACEMENT
    measurement_unit: Optional[str] = None  # Measurement unit for INDIVIDUAL_RANKING (seconds, meters, points, etc.)
    ranking_direction: Optional[str] = None  # Ranking direction: ASC (lowest wins) or DESC (highest wins)
    enrollment_snapshot: Optional[dict] = None  # 📸 Enrollment state snapshot before session generation


class SemesterList(BaseModel):
    semesters: List[SemesterWithStats]
    total: int