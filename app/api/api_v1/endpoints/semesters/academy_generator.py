"""
🏫 Academy Season Generator API Endpoint
=========================================
Generates full-year Academy Season semesters (July 1 - June 30)

Business Rules:
- Supports all 4 age groups: PRE_ACADEMY, YOUTH_ACADEMY, AMATEUR_ACADEMY, PRO_ACADEMY
- Can only be created at CENTER locations
- Full year commitment with age lock at July 1
- Cost range: 5000-10000 credits (PRE→YOUTH→AMATEUR→PRO)
"""
from typing import Any
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from .....database import get_db
from .....dependencies import get_current_admin_user
from .....models.user import User
from .....models.semester import Semester, SemesterStatus
from .....models.location import Location, LocationType
from .....models.specialization import SpecializationType
from .....schemas.semester import Semester as SemesterSchema
from .....services.location_validation_service import LocationValidationService
from .....services.semester_templates import SEMESTER_TEMPLATES

router = APIRouter()


class AcademySeasonGenerateRequest(BaseModel):
    """Request model for generating Academy Season"""
    specialization_type: SpecializationType = Field(
        ...,
        description="Academy Season type (PRE_ACADEMY, YOUTH_ACADEMY, AMATEUR_ACADEMY, or PRO_ACADEMY)"
    )
    location_id: int = Field(..., description="Location ID (must be CENTER type)")
    campus_id: int = Field(..., description="Campus ID within the location")
    year: int = Field(..., description="Starting year (e.g., 2025 for 2025-2026 season)")
    master_instructor_id: int | None = Field(None, description="Optional Master Instructor assignment")


class AcademySeasonGenerateResponse(BaseModel):
    """Response model for Academy Season generation"""
    semester: SemesterSchema
    message: str
    template_used: str
    cost_credits: int
    season_dates: dict


@router.post("/generate-academy-season", response_model=AcademySeasonGenerateResponse)
def generate_academy_season(
    request: AcademySeasonGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Generate a full-year Academy Season semester (July 1 - June 30)

    Validations:
    1. Specialization type must be Academy type (PRE/YOUTH/AMATEUR/PRO_ACADEMY)
    2. Location must be CENTER type
    3. Year must be valid (not in past)
    4. No duplicate Academy Season for same year/location/type

    Creates:
    - Single semester spanning July 1 (year) to June 30 (year+1)
    - Status: DRAFT (awaiting instructor assignment)
    - Code format: {AGE_GROUP}-ACAD-{year}-{location_code}
    """
    # Validation 1: Check Academy Season type
    if request.specialization_type not in [
        SpecializationType.LFA_PLAYER_PRE_ACADEMY,
        SpecializationType.LFA_PLAYER_YOUTH_ACADEMY,
        SpecializationType.LFA_PLAYER_AMATEUR_ACADEMY,
        SpecializationType.LFA_PLAYER_PRO_ACADEMY
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Érvénytelen specializáció típus",
                "message": "Csak Academy Season típusok engedélyezettek (PRE/YOUTH/AMATEUR/PRO_ACADEMY)",
                "provided": str(request.specialization_type)
            }
        )

    # Validation 2: Check location exists and is CENTER type
    location = db.query(Location).filter(Location.id == request.location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )

    if location.location_type != LocationType.CENTER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Helyszín típus korlátozás",
                "message": f"Academy Season csak CENTER helyszíneken hozható létre. {location.city} PARTNER szintű helyszín.",
                "location_type": location.location_type.value,
                "location_city": location.city
            }
        )

    # Validation 3: Use LocationValidationService for additional checks
    validation = LocationValidationService.can_create_semester_at_location(
        location_id=request.location_id,
        specialization_type=request.specialization_type,
        db=db
    )

    if not validation["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Validációs hiba",
                "message": validation["reason"]
            }
        )

    # Validation 4: Check year is valid
    current_year = datetime.now().year
    if request.year < current_year:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Érvénytelen év",
                "message": f"Az Academy Season nem hozható létre múltbeli évre. Minimum év: {current_year}",
                "provided_year": request.year
            }
        )

    # Get template for this Academy Season type
    # Map specialization type to age group
    age_group_map = {
        SpecializationType.LFA_PLAYER_PRE_ACADEMY: "PRE",
        SpecializationType.LFA_PLAYER_YOUTH_ACADEMY: "YOUTH",
        SpecializationType.LFA_PLAYER_AMATEUR_ACADEMY: "AMATEUR",
        SpecializationType.LFA_PLAYER_PRO_ACADEMY: "PRO"
    }
    age_group = age_group_map.get(request.specialization_type)
    template_key = (request.specialization_type.value, age_group)

    if template_key not in SEMESTER_TEMPLATES:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Template not found for {request.specialization_type.value} / {age_group}"
        )

    template = SEMESTER_TEMPLATES[template_key]

    # Generate semester code and name based on age group
    location_code = location.city[:3].upper()  # First 3 letters of city
    semester_code = f"{age_group}-ACAD-{request.year}-{location_code}"
    semester_name = f"{age_group} Academy Season {request.year}/{request.year + 1}"

    # Validation 5: Check for duplicate
    existing = db.query(Semester).filter(Semester.code == semester_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Duplikált Academy Season",
                "message": f"Academy Season már létezik ezzel a kóddal: {semester_code}",
                "existing_semester_id": existing.id
            }
        )

    # Create semester dates (July 1 to June 30)
    start_date = date(request.year, 7, 1)
    end_date = date(request.year + 1, 6, 30)

    # Create semester
    new_semester = Semester(
        code=semester_code,
        name=semester_name,
        specialization_type=request.specialization_type,
        start_date=start_date,
        end_date=end_date,
        location_id=request.location_id,
        campus_id=request.campus_id,
        master_instructor_id=request.master_instructor_id,
        status=SemesterStatus.DRAFT if not request.master_instructor_id else SemesterStatus.SEEKING_INSTRUCTOR,
        is_active=True
    )

    db.add(new_semester)
    db.commit()
    db.refresh(new_semester)

    # Prepare response
    response = AcademySeasonGenerateResponse(
        semester=SemesterSchema.model_validate(new_semester),
        message=f"Academy Season sikeresen létrehozva: {semester_name}",
        template_used=template["cycle_type"],
        cost_credits=template.get("cost_credits", 0),
        season_dates={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "duration_days": (end_date - start_date).days,
            "season_year": f"{request.year}/{request.year + 1}"
        }
    )

    return response


@router.get("/academy-seasons/available-years")
def get_available_academy_years(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Get list of available years for Academy Season creation

    Returns current year + next 2 years
    """
    current_year = datetime.now().year
    return {
        "available_years": [
            current_year,
            current_year + 1,
            current_year + 2
        ],
        "current_year": current_year,
        "recommendation": f"Új Academy Season általában {current_year} júliusában indul"
    }
