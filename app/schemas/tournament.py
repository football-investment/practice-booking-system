"""
Tournament-specific Pydantic schemas for API responses
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import date
from ..models.semester_enrollment import EnrollmentStatus


# ============================================================================
# Tournament Browse/List Schemas
# ============================================================================

class TournamentSessionDetail(BaseModel):
    """Session details for tournament (game)"""
    id: int
    date: date
    start_time: str
    end_time: str
    game_type: Optional[str] = None
    capacity: int
    current_bookings: int

    model_config = ConfigDict(from_attributes=True)


class TournamentLocationDetail(BaseModel):
    """Location details for tournament"""
    id: int
    city: str
    address: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TournamentCampusDetail(BaseModel):
    """Campus details for tournament"""
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class TournamentInstructorDetail(BaseModel):
    """Master instructor details for tournament"""
    id: int
    name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class TournamentWithDetails(BaseModel):
    """
    Complete tournament details for browsing
    Includes all info needed to display tournament card and enroll
    """
    # Tournament (Semester) data
    tournament: Dict[str, Any]  # Full semester object

    # Enrollment statistics
    enrollment_count: int
    is_enrolled: bool
    user_enrollment_status: Optional[EnrollmentStatus] = None

    # Related data
    sessions: List[Dict[str, Any]]
    location: Optional[Dict[str, Any]] = None
    campus: Optional[Dict[str, Any]] = None
    instructor: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Tournament Enrollment Schemas
# ============================================================================

class EnrollmentConflict(BaseModel):
    """Conflict warning detail"""
    type: str  # "time_overlap" or "travel_time"
    severity: str  # "blocking" or "warning"
    message: str
    conflicting_session_id: Optional[int] = None
    conflicting_semester_name: Optional[str] = None


class EnrollmentResponse(BaseModel):
    """
    Response after successful tournament enrollment
    Includes enrollment details and any conflict warnings
    """
    success: bool
    enrollment: Dict[str, Any]  # SemesterEnrollment object
    tournament: Dict[str, Any]  # Tournament (Semester) object
    conflicts: List[EnrollmentConflict] = []
    warnings: List[str] = []
    credits_remaining: int

    model_config = ConfigDict(from_attributes=True)
