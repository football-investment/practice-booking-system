from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.dependencies import get_current_user
from pydantic import BaseModel

router = APIRouter()

class UserProgressResponse(BaseModel):
    internship_level: Optional[str] = None
    coach_foundation_level: Optional[str] = None
    coach_specializations: List[str] = []
    gancuju_level: Optional[str] = None
    completed_semesters: dict = {}

class UpdateProgressRequest(BaseModel):
    track: str  # 'internship', 'coach', 'gancuju'
    level: str
    specializations: Optional[List[str]] = None

# Progression system definitions
PROGRESSION_SYSTEMS = {
    "internship": {
        "levels": ["junior", "medior", "senior"],
        "prerequisites": {
            "medior": "junior",
            "senior": "medior"
        }
    },
    "coach": {
        "foundation_levels": [
            "pre_assistant", "pre_lead", "youth_assistant", "youth_lead",
            "amateur_assistant", "amateur_lead", "pro_assistant", "pro_lead"
        ],
        "specializations": ["goalkeeper", "fitness", "rehabilitation"],
        "prerequisites": {
            "pre_lead": "pre_assistant",
            "youth_assistant": "pre_lead",
            "youth_lead": "youth_assistant",
            "amateur_assistant": "youth_lead",
            "amateur_lead": "amateur_assistant",
            "pro_assistant": "amateur_lead",
            "pro_lead": "pro_assistant"
        },
        "specialization_prerequisite": "pre_lead"  # Need Pre Lead to access specializations
    },
    "gancuju": {
        "levels": [
            "bamboo", "dawn", "reed", "river",
            "root", "moon", "guardian", "dragon"
        ],
        "prerequisites": {
            "dawn": "bamboo",
            "reed": "dawn",
            "river": "reed",
            "root": "river",
            "moon": "root",
            "guardian": "moon",
            "dragon": "guardian"
        }
    }
}

SEMESTER_COUNTS = {
    # Internship track
    "junior": 1, "medior": 1, "senior": 1,
    
    # Coach foundation track
    "pre_assistant": 1, "pre_lead": 2, "youth_assistant": 2, "youth_lead": 3,
    "amateur_assistant": 4, "amateur_lead": 4, "pro_assistant": 5, "pro_lead": 5,
    
    # Coach specializations
    "goalkeeper": 2, "fitness": 2, "rehabilitation": 2,
    
    # GānCuju track
    "bamboo": 1, "dawn": 1, "reed": 1, "river": 1,
    "root": 1, "moon": 1, "guardian": 1, "dragon": 1
}

def validate_prerequisite(track: str, level: str, current_progress: dict) -> bool:
    """Check if user meets prerequisites for a level"""
    system = PROGRESSION_SYSTEMS.get(track)
    if not system:
        return False
    
    prerequisites = system.get("prerequisites", {})
    required_level = prerequisites.get(level)
    
    if not required_level:
        return True  # No prerequisite needed
    
    if track == "internship":
        current_level = current_progress.get("internship_level")
        levels = system["levels"]
        current_index = levels.index(current_level) if current_level in levels else -1
        required_index = levels.index(required_level)
        return current_index >= required_index
    
    elif track == "coach":
        if level in system["specializations"]:
            # Specialization requires pre_lead
            current_level = current_progress.get("coach_foundation_level")
            if not current_level:
                return False
            foundation_levels = system["foundation_levels"]
            current_index = foundation_levels.index(current_level) if current_level in foundation_levels else -1
            required_index = foundation_levels.index(system["specialization_prerequisite"])
            return current_index >= required_index
        else:
            # Foundation level
            current_level = current_progress.get("coach_foundation_level")
            levels = system["foundation_levels"]
            current_index = levels.index(current_level) if current_level in levels else -1
            required_index = levels.index(required_level)
            return current_index >= required_index
    
    elif track == "gancuju":
        current_level = current_progress.get("gancuju_level")
        levels = system["levels"]
        current_index = levels.index(current_level) if current_level in levels else -1
        required_index = levels.index(required_level)
        return current_index >= required_index
    
    return False

def calculate_completed_semesters(progress: dict) -> dict:
    """Calculate total completed semesters for each track"""
    result = {"internship": 0, "coach": 0, "gancuju": 0}
    
    # Internship track
    if progress.get("internship_level"):
        level = progress["internship_level"]
        levels = PROGRESSION_SYSTEMS["internship"]["levels"]
        current_index = levels.index(level) if level in levels else -1
        for i in range(current_index + 1):
            result["internship"] += SEMESTER_COUNTS[levels[i]]
    
    # Coach track (foundation + specializations)
    if progress.get("coach_foundation_level"):
        level = progress["coach_foundation_level"]
        levels = PROGRESSION_SYSTEMS["coach"]["foundation_levels"]
        current_index = levels.index(level) if level in levels else -1
        for i in range(current_index + 1):
            result["coach"] += SEMESTER_COUNTS[levels[i]]
    
    # Add specialization semesters
    for spec in progress.get("coach_specializations", []):
        if spec in SEMESTER_COUNTS:
            result["coach"] += SEMESTER_COUNTS[spec]
    
    # GānCuju track
    if progress.get("gancuju_level"):
        level = progress["gancuju_level"]
        levels = PROGRESSION_SYSTEMS["gancuju"]["levels"]
        current_index = levels.index(level) if level in levels else -1
        for i in range(current_index + 1):
            result["gancuju"] += SEMESTER_COUNTS[levels[i]]
    
    return result

@router.get("/progress", response_model=UserProgressResponse)
def get_user_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's progression status"""
    
    # Mock data for now - in real implementation this would come from database
    # You would store this in user profile or separate progression table
    mock_progress = {
        "internship_level": "junior",
        "coach_foundation_level": "pre_assistant", 
        "coach_specializations": [],
        "gancuju_level": "bamboo"
    }
    
    completed_semesters = calculate_completed_semesters(mock_progress)
    
    return UserProgressResponse(
        internship_level=mock_progress.get("internship_level"),
        coach_foundation_level=mock_progress.get("coach_foundation_level"),
        coach_specializations=mock_progress.get("coach_specializations", []),
        gancuju_level=mock_progress.get("gancuju_level"),
        completed_semesters=completed_semesters
    )

@router.post("/progress/update")
def update_user_progress(
    request: UpdateProgressRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user's progression status"""
    
    # Get current progress
    current_progress = {
        "internship_level": "junior",  # Mock - get from database
        "coach_foundation_level": "pre_assistant",
        "coach_specializations": [],
        "gancuju_level": "bamboo"
    }
    
    # Validate prerequisites
    if not validate_prerequisite(request.track, request.level, current_progress):
        raise HTTPException(
            status_code=400, 
            detail=f"Prerequisites not met for {request.track} level {request.level}"
        )
    
    # Update progress (in real implementation, save to database)
    if request.track == "internship":
        current_progress["internship_level"] = request.level
    elif request.track == "coach":
        if request.level in PROGRESSION_SYSTEMS["coach"]["specializations"]:
            # Adding specialization
            if request.level not in current_progress["coach_specializations"]:
                current_progress["coach_specializations"].append(request.level)
        else:
            # Foundation level
            current_progress["coach_foundation_level"] = request.level
    elif request.track == "gancuju":
        current_progress["gancuju_level"] = request.level
    
    completed_semesters = calculate_completed_semesters(current_progress)
    
    return {
        "message": "Progress updated successfully",
        "new_progress": current_progress,
        "completed_semesters": completed_semesters
    }

@router.get("/systems")
def get_progression_systems():
    """Get all progression system definitions"""
    
    # Add UI metadata to the systems
    enhanced_systems = {
        "internship": {
            **PROGRESSION_SYSTEMS["internship"],
            "id": "internship",
            "title": "Internship Track",
            "subtitle": "LFA Gyakornoki Program",
            "emoji": "💼",
            "color": "#059669",
            "gradient": "linear-gradient(135deg, #10b981 0%, #059669 100%)"
        },
        "coach": {
            **PROGRESSION_SYSTEMS["coach"],
            "id": "coach", 
            "title": "Coach Track",
            "subtitle": "LFA Edzői Specializáció",
            "emoji": "👨‍🏫",
            "color": "#DC2626",
            "gradient": "linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)"
        },
        "gancuju": {
            **PROGRESSION_SYSTEMS["gancuju"],
            "id": "gancuju",
            "title": "GānCuju™️©️ Track", 
            "subtitle": "8 Szintű Játékos Fejlesztési Rendszer",
            "emoji": "⚽",
            "color": "#4F46E5",
            "gradient": "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)"
        }
    }
    
    return {
        "systems": enhanced_systems,
        "semester_counts": SEMESTER_COUNTS
    }