"""
Sandbox Data Endpoints - Phase 1: Read-Only APIs

Provides admin-only endpoints for listing and inspecting users/instructors
for sandbox test configuration.

Scope:
- GET /sandbox/users - List users with skill preview
- GET /sandbox/instructors - List instructors
- GET /sandbox/users/{user_id}/skills - Full skill profile

No database modifications, read-only queries only.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel, ConfigDict, Field

from app.database import get_db
from app.api.deps import get_current_admin_user
from app.models.user import User
from app.models.license import UserLicense
from app.services import skill_progression_service

logger = logging.getLogger(__name__)

router = APIRouter()


# Response Schemas

class UserSkillPreview(BaseModel):
    """Minimal skill preview for user listing"""
    passing: float
    dribbling: float
    shooting: float
    defending: float


class UserListItem(BaseModel):
    """User item for selection list"""
    id: int
    email: str
    name: str
    specialization: Optional[str]
    license_type: Optional[str]
    is_active: bool
    skill_preview: Optional[UserSkillPreview]


class InstructorListItem(BaseModel):
    """Instructor item for selection list"""
    id: int
    email: str
    name: str
    specialization: Optional[str]
    permissions: List[str]
    is_active: bool


class FullSkillProfile(BaseModel):
    """Complete skill profile response"""
    user_id: int
    email: str
    name: str
    skills: dict  # Full nested structure from skill_progression_service
    baseline_skills: dict
    last_updated: Optional[str]


# Endpoints

@router.get("/users", response_model=List[UserListItem])
def list_users_for_sandbox(
    search: Optional[str] = Query(None, description="Search by name or email"),
    license_type: Optional[str] = Query(None, description="Filter by license type (BASIC, PREMIUM, etc)"),
    specialization: Optional[str] = Query(None, description="Filter by specialization"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    List users available for sandbox testing

    Admin-only endpoint. Returns users with skill preview for selection.
    """
    logger.info(f"Admin {current_admin.email} listing users for sandbox (search={search}, license_type={license_type})")

    query = db.query(User).filter(User.role == "STUDENT")

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                User.name.ilike(search_pattern),
                User.email.ilike(search_pattern)
            )
        )

    # Apply specialization filter
    if specialization:
        query = query.filter(User.specialization == specialization)

    # Apply active status filter
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    # Apply license type filter (join with UserLicense)
    if license_type:
        query = query.join(UserLicense, User.id == UserLicense.user_id).filter(
            UserLicense.specialization_type == license_type,
            UserLicense.is_active == True
        )

    # Execute query with pagination
    users = query.order_by(User.name).limit(limit).offset(offset).all()

    # Build response with skill preview
    result = []
    for user in users:
        # Get active license
        active_license = db.query(UserLicense).filter(
            UserLicense.user_id == user.id,
            UserLicense.is_active == True
        ).first()

        # Get skill preview (top 4 skills only)
        skill_preview = None
        try:
            skill_profile = skill_progression_service.get_skill_profile(db, user.id)

            if isinstance(skill_profile, dict):
                skills_dict = skill_profile.get("skills", {})

                # Extract preview skills
                skill_preview = UserSkillPreview(
                    passing=skills_dict.get("passing", {}).get("current_level", 50.0),
                    dribbling=skills_dict.get("dribbling", {}).get("current_level", 50.0),
                    shooting=skills_dict.get("shooting", {}).get("current_level", 50.0),
                    defending=skills_dict.get("defending", {}).get("current_level", 50.0)
                )
        except Exception as e:
            logger.warning(f"Could not fetch skill preview for user {user.id}: {e}")

        result.append(UserListItem(
            id=user.id,
            email=user.email,
            name=user.name,
            specialization=user.specialization,
            license_type=active_license.specialization_type if active_license else None,
            is_active=user.is_active,
            skill_preview=skill_preview
        ))

    logger.info(f"Returning {len(result)} users for sandbox selection")
    return result


@router.get("/instructors", response_model=List[InstructorListItem])
def list_instructors_for_sandbox(
    search: Optional[str] = Query(None, description="Search by name or email"),
    specialization: Optional[str] = Query(None, description="Filter by specialization"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    List instructors available for sandbox testing

    Admin-only endpoint. Returns instructors with permissions for selection.
    """
    logger.info(f"Admin {current_admin.email} listing instructors for sandbox (search={search}, specialization={specialization})")

    query = db.query(User).filter(User.role == "INSTRUCTOR")

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                User.name.ilike(search_pattern),
                User.email.ilike(search_pattern)
            )
        )

    # Apply specialization filter
    if specialization:
        query = query.filter(User.specialization == specialization)

    # Execute query with pagination
    instructors = query.order_by(User.name).limit(limit).offset(offset).all()

    # Build response
    result = []
    for instructor in instructors:
        # Get instructor permissions (simplified for MVP - expand later if needed)
        permissions = []
        if instructor.specialization:
            permissions.append(f"teach_{instructor.specialization}")

        result.append(InstructorListItem(
            id=instructor.id,
            email=instructor.email,
            name=instructor.name,
            specialization=instructor.specialization,
            permissions=permissions,
            is_active=instructor.is_active
        ))

    logger.info(f"Returning {len(result)} instructors for sandbox selection")
    return result


@router.get("/users/{user_id}/skills", response_model=FullSkillProfile)
def get_user_skills_for_sandbox(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Get full skill profile for a user

    Admin-only endpoint. Reuses existing skill_progression_service.
    Used for detailed inspection before sandbox test configuration.
    """
    logger.info(f"Admin {current_admin.email} fetching skills for user {user_id}")

    # Check user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get full skill profile
    try:
        skill_profile = skill_progression_service.get_skill_profile(db, user_id)

        if not isinstance(skill_profile, dict):
            logger.warning(f"skill_profile returned non-dict type={type(skill_profile)}")
            raise HTTPException(
                status_code=500,
                detail="Invalid skill profile format"
            )

        # Get baseline skills
        baseline_skills = {}
        active_license = db.query(UserLicense).filter(
            UserLicense.user_id == user_id,
            UserLicense.is_active == True
        ).first()

        if active_license and isinstance(active_license.football_skills, dict):
            baseline_skills = active_license.football_skills

        return FullSkillProfile(
            user_id=user.id,
            email=user.email,
            name=user.name,
            skills=skill_profile.get("skills", {}),
            baseline_skills=baseline_skills,
            last_updated=skill_profile.get("last_updated")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch skills for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch skill profile: {str(e)}"
        )
