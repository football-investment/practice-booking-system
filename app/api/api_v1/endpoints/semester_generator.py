"""
Admin Semester Generator Endpoint
==================================
Automatically generates semesters based on templates for each specialization and age group.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date, timedelta
from pydantic import BaseModel

from ....database import get_db
from ....models.semester import Semester, SemesterStatus
from ....models.location import Location
from ....dependencies import get_current_admin_user
from ....services.semester_templates import get_template, SEMESTER_TEMPLATES

router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class SemesterGenerationRequest(BaseModel):
    """Request to generate semesters for a specific year, specialization, and age group"""
    year: int
    specialization: str  # "LFA_PLAYER", "GANCUJU", "COACH", "INTERNSHIP"
    age_group: str  # "PRE", "YOUTH", "AMATEUR", "PRO"
    location_id: int  # Required: Location where semesters will be held


class GeneratedSemesterInfo(BaseModel):
    """Information about a generated semester"""
    code: str
    name: str
    start_date: date
    end_date: date
    specialization_type: str
    age_group: str
    theme: str
    focus_description: str


class SemesterGenerationResponse(BaseModel):
    """Response after generating semesters"""
    message: str
    generated_count: int
    semesters: List[GeneratedSemesterInfo]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_first_monday(year: int, month: int) -> date:
    """Get the first Monday of a given month"""
    d = date(year, month, 1)
    # Find first Monday
    while d.weekday() != 0:  # 0 = Monday
        d += timedelta(days=1)
    return d


def get_last_sunday(year: int, month: int) -> date:
    """Get the last Sunday of a given month"""
    # Start from last day of month
    if month == 12:
        d = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        d = date(year, month + 1, 1) - timedelta(days=1)

    # Find last Sunday
    while d.weekday() != 6:  # 6 = Sunday
        d -= timedelta(days=1)
    return d


def generate_monthly_semesters(year: int, template: dict, db: Session) -> List[Semester]:
    """
    Generate 12 monthly semesters for PRE age group with gap-filling logic.

    HYBRID APPROACH:
    - First semester: starts on month's first Monday
    - Subsequent semesters: start immediately after previous semester ends (gap-free)
    - All semesters: guaranteed Monday start, Sunday end
    """
    semesters = []
    spec = template["specialization"]
    age_group = template["age_group"]
    last_end_date = None

    for theme_data in template["themes"]:
        month = theme_data["month"]
        code = theme_data["code"]
        theme = theme_data["theme"]
        focus = theme_data["focus"]

        # HYBRID LOGIC: Gap-filling while preserving marketing themes
        if last_end_date is None:
            # First semester: month's first Monday
            start = get_first_monday(year, month)
        else:
            # Next semester: immediately after previous (gap-free)
            start = last_end_date + timedelta(days=1)
            # Align to Monday
            while start.weekday() != 0:  # 0 = Monday
                start += timedelta(days=1)

        # End: month's last Sunday
        end = get_last_sunday(year, month)

        semester = Semester(
            code=f"{year}/{spec}_{age_group}_{code}",
            name=f"{year} {spec} {age_group} - {theme}",
            start_date=start,
            end_date=end,
            specialization_type=f"{spec}_{age_group}",
            age_group=age_group,
            theme=theme,
            focus_description=focus,
            status=SemesterStatus.DRAFT,  # DRAFT by default - admin must assign instructor first
            is_active=False,
            enrollment_cost=500  # Default cost
        )
        semesters.append(semester)
        last_end_date = end

    return semesters


def generate_quarterly_semesters(year: int, template: dict, db: Session) -> List[Semester]:
    """
    Generate 4 quarterly semesters for YOUTH age group with gap-filling logic.

    HYBRID APPROACH:
    - First quarter: starts on first month's first Monday
    - Subsequent quarters: start immediately after previous quarter ends (gap-free)
    - All quarters: guaranteed Monday start, Sunday end
    """
    semesters = []
    spec = template["specialization"]
    age_group = template["age_group"]
    last_end_date = None

    for theme_data in template["themes"]:
        quarter = theme_data["quarter"]
        code = theme_data["code"]
        months = theme_data["months"]
        theme = theme_data["theme"]
        focus = theme_data["focus"]

        # HYBRID LOGIC: Gap-filling while preserving marketing themes
        if last_end_date is None:
            # First quarter: first month's first Monday
            start = get_first_monday(year, months[0])
        else:
            # Next quarter: immediately after previous (gap-free)
            start = last_end_date + timedelta(days=1)
            # Align to Monday
            while start.weekday() != 0:  # 0 = Monday
                start += timedelta(days=1)

        # End: last Sunday of last month
        end = get_last_sunday(year, months[-1])

        semester = Semester(
            code=f"{year}/{spec}_{age_group}_{code}",
            name=f"{year} {spec} {age_group} - {theme}",
            start_date=start,
            end_date=end,
            specialization_type=f"{spec}_{age_group}",
            age_group=age_group,
            theme=theme,
            focus_description=focus,
            status=SemesterStatus.DRAFT,  # DRAFT by default - admin must assign instructor first
            is_active=False,
            enrollment_cost=500
        )
        semesters.append(semester)
        last_end_date = end

    return semesters


def generate_semiannual_semesters(year: int, template: dict, db: Session) -> List[Semester]:
    """
    Generate 2 semi-annual semesters for AMATEUR age group with gap-filling logic.

    HYBRID APPROACH:
    - First semester (Fall): starts on start month's first Monday
    - Second semester (Spring): starts immediately after Fall ends (gap-free)
    - All semesters: guaranteed Monday start, Sunday end
    - Handles year wrap-around (Fall: Sep-Feb crosses year boundary)
    """
    semesters = []
    spec = template["specialization"]
    age_group = template["age_group"]
    last_end_date = None

    for theme_data in template["themes"]:
        code = theme_data["code"]
        start_month = theme_data["start_month"]
        end_month = theme_data["end_month"]
        theme = theme_data["theme"]
        focus = theme_data["focus"]

        # HYBRID LOGIC: Gap-filling while preserving marketing themes
        if last_end_date is None:
            # First semester (Fall): start month's first Monday
            start = get_first_monday(year, start_month)
        else:
            # Second semester (Spring): immediately after Fall (gap-free)
            start = last_end_date + timedelta(days=1)
            # Align to Monday
            while start.weekday() != 0:  # 0 = Monday
                start += timedelta(days=1)

        # Handle year wrap-around for Fall semester (Sep-Feb)
        if start_month > end_month:  # Fall semester (Sep-Feb)
            end = get_last_sunday(year + 1, end_month)
        else:  # Spring semester (Mar-Aug)
            end = get_last_sunday(year, end_month)

        semester = Semester(
            code=f"{year}/{spec}_{age_group}_{code}",
            name=f"{year} {spec} {age_group} - {theme}",
            start_date=start,
            end_date=end,
            specialization_type=f"{spec}_{age_group}",
            age_group=age_group,
            theme=theme,
            focus_description=focus,
            status=SemesterStatus.DRAFT,  # DRAFT by default - admin must assign instructor first
            is_active=False,
            enrollment_cost=500
        )
        semesters.append(semester)
        last_end_date = end

    return semesters


def generate_annual_semesters(year: int, template: dict, db: Session) -> List[Semester]:
    """
    Generate 1 annual semester for PRO age group (Jul-Jun, football season).

    HYBRID APPROACH:
    - Single annual semester: starts on July's first Monday
    - Ends on June's last Sunday of following year
    - Guaranteed Monday start, Sunday end
    - No gap-filling needed (only one semester per year)
    """
    semesters = []
    spec = template["specialization"]
    age_group = template["age_group"]

    theme_data = template["themes"][0]
    code = theme_data["code"]
    start_month = theme_data["start_month"]  # 7 (July)
    end_month = theme_data["end_month"]  # 6 (June)
    theme = theme_data["theme"]
    focus = theme_data["focus"]

    # Annual season: Jul (year) - Jun (year+1)
    start = get_first_monday(year, start_month)
    end = get_last_sunday(year + 1, end_month)

    semester = Semester(
        code=f"{year}/{spec}_{age_group}_{code}",
        name=f"{year}/{year+1} {spec} {age_group} - {theme}",
        start_date=start,
        end_date=end,
        specialization_type=f"{spec}_{age_group}",
        age_group=age_group,
        theme=theme,
        focus_description=focus,
        is_active=False,  # Inactive by default - admin must assign instructor first
        enrollment_cost=500
    )
    semesters.append(semester)

    return semesters


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/generate", response_model=SemesterGenerationResponse)
async def generate_semesters(
    request: SemesterGenerationRequest,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin_user)
):
    """
    Generate semesters for a specific year, specialization, and age group.

    **Admin only** - Automatically creates all semesters based on templates.

    Examples:
    - LFA_PLAYER + PRE → 12 monthly semesters (M01-M12)
    - LFA_PLAYER + YOUTH → 4 quarterly semesters (Q1-Q4)
    - LFA_PLAYER + AMATEUR → 2 semi-annual semesters (Fall, Spring)
    - LFA_PLAYER + PRO → 1 annual semester (Season)
    """

    # Validate location exists and is active
    location = db.query(Location).filter(Location.id == request.location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail=f"Location with ID {request.location_id} not found")

    if not location.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Location '{location.name}' is not active. Please activate it first."
        )

    # Validate template exists
    try:
        template = get_template(request.specialization, request.age_group)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check for existing semesters with same spec/age/year
    existing = db.query(Semester).filter(
        Semester.specialization_type == f"{request.specialization}_{request.age_group}",
        Semester.code.like(f"{request.year}/%")
    ).all()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Semesters already exist for {request.year}/{request.specialization}/{request.age_group}. "
                   f"Delete them first if you want to regenerate."
        )

    # Generate semesters based on cycle type
    cycle_type = template["cycle_type"]

    if cycle_type == "monthly":
        semesters = generate_monthly_semesters(request.year, template, db)
    elif cycle_type == "quarterly":
        semesters = generate_quarterly_semesters(request.year, template, db)
    elif cycle_type == "semi-annual":
        semesters = generate_semiannual_semesters(request.year, template, db)
    elif cycle_type == "annual":
        semesters = generate_annual_semesters(request.year, template, db)
    else:
        raise HTTPException(status_code=500, detail=f"Unknown cycle type: {cycle_type}")

    # Assign location to all generated semesters
    for semester in semesters:
        semester.location_id = location.id
        db.add(semester)

    db.commit()

    # Prepare response
    generated_info = [
        GeneratedSemesterInfo(
            code=s.code,
            name=s.name,
            start_date=s.start_date,
            end_date=s.end_date,
            specialization_type=s.specialization_type,
            age_group=s.age_group,
            theme=s.theme,
            focus_description=s.focus_description
        )
        for s in semesters
    ]

    return SemesterGenerationResponse(
        message=f"Successfully generated {len(semesters)} semesters for {request.year}/{request.specialization}/{request.age_group}",
        generated_count=len(semesters),
        semesters=generated_info
    )


@router.get("/available-templates")
async def get_available_templates(
    current_admin = Depends(get_current_admin_user)
):
    """
    List all available semester templates.

    **Admin only**
    """
    templates_list = []
    for (spec, age_group), template in SEMESTER_TEMPLATES.items():
        templates_list.append({
            "specialization": spec,
            "age_group": age_group,
            "cycle_type": template["cycle_type"],
            "semester_count": len(template["themes"])
        })

    return {
        "available_templates": templates_list
    }
