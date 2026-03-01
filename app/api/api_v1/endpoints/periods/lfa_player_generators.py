"""
LFA_PLAYER Season Generators
============================
Individual season generation endpoints for all LFA_PLAYER age groups.

All endpoints use "season" terminology (not "semester").

Endpoints:
- POST /lfa-player/pre - Monthly seasons (12/year): M01, M02, ..., M12
- POST /lfa-player/youth - Quarterly seasons (4/year): Q1, Q2, Q3, Q4
- POST /lfa-player/amateur - Semi-annual seasons (2/year): Fall, Spring
- POST /lfa-player/pro - Annual season (1/year): Season
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Dict

from .....database import get_db
from .....models.semester import Semester, SemesterStatus
from .....models.location import Location
from .....dependencies import get_current_admin_user
from .....services.semester_templates import (
    LFA_PLAYER_PRE_TEMPLATE,
    LFA_PLAYER_YOUTH_TEMPLATE,
    LFA_PLAYER_AMATEUR_TEMPLATE,
    LFA_PLAYER_PRO_TEMPLATE
)
from .base import (
    get_first_monday,
    get_last_sunday,
    check_existing_period,
    get_period_label
)

router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class LFAPlayerPreRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Request to generate a single monthly season for LFA_PLAYER PRE"""
    year: int
    month: int  # 1-12
    location_id: int
    force_overwrite: bool = False


class LFAPlayerYouthRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Request to generate a single quarterly season for LFA_PLAYER YOUTH"""
    year: int
    quarter: int  # 1-4
    location_id: int
    force_overwrite: bool = False


class LFAPlayerAmateurRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Request to generate annual season for LFA_PLAYER AMATEUR (Jul-Jun)"""
    year: int
    location_id: int
    force_overwrite: bool = False


class LFAPlayerProRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    """Request to generate annual season for LFA_PLAYER PRO"""
    year: int
    location_id: int
    force_overwrite: bool = False


class PeriodGenerationResponse(BaseModel):
    """Response after generating a single period"""
    success: bool
    message: str
    period: Dict


# ============================================================================
# LFA_PLAYER PRE: MONTHLY SEASONS (12/year)
# ============================================================================

@router.post("/lfa-player/pre", response_model=PeriodGenerationResponse)
def generate_lfa_player_pre_season(
    request: LFAPlayerPreRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Generate a single monthly season for LFA_PLAYER PRE

    Generates one of 12 monthly seasons (M01-M12) for the specified year.

    Args:
        request: LFAPlayerPreRequest with year, month (1-12), location_id
        db: Database session
        current_user: Authenticated admin user

    Returns:
        PeriodGenerationResponse with success message and generated season details

    Raises:
        HTTPException 400: Invalid month or season already exists
        HTTPException 404: Location not found
    """
    # Validate month
    if not 1 <= request.month <= 12:
        raise HTTPException(status_code=400, detail="Month must be between 1-12")

    # Get template
    template = LFA_PLAYER_PRE_TEMPLATE
    month_theme = next((t for t in template["themes"] if t["month"] == request.month), None)
    if not month_theme:
        raise HTTPException(status_code=400, detail=f"No template for month {request.month}")

    # Validate location
    location = db.query(Location).filter(Location.id == request.location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    # Generate code: "2025/LFA_PLAYER_PRE_M03"
    code = f"{request.year}/LFA_PLAYER_PRE_{month_theme['code']}"

    # Check if already exists
    exists, existing = check_existing_period(db, "LFA_PLAYER_PRE", code)
    if exists and not request.force_overwrite:
        raise HTTPException(
            status_code=400,
            detail=f"Season {code} already exists. Use force_overwrite=true to replace."
        )

    # Calculate dates (first Monday to last Sunday of month)
    start_date = get_first_monday(request.year, request.month)
    end_date = get_last_sunday(request.year, request.month)

    # Create or update semester
    if exists and request.force_overwrite:
        semester = existing
        semester.start_date = start_date
        semester.end_date = end_date
        semester.theme = month_theme["theme"]
        semester.focus_description = month_theme["focus"]
        semester.location_id = location.id
    else:
        semester = Semester(
            code=code,
            name=f"{request.year} LFA_PLAYER PRE - {month_theme['theme']}",
            start_date=start_date,
            end_date=end_date,
            specialization_type="LFA_PLAYER_PRE",
            age_group="PRE",
            theme=month_theme["theme"],
            focus_description=month_theme["focus"],
            is_active=True,
            status=SemesterStatus.DRAFT,
            location_id=location.id
        )
        db.add(semester)

    db.commit()
    db.refresh(semester)

    # Return with intelligent labeling
    period_label = get_period_label("LFA_PLAYER")
    return PeriodGenerationResponse(
        success=True,
        message=f"Successfully generated {period_label} {month_theme['code']} for {request.year}/LFA_PLAYER/PRE",
        period={
            "code": semester.code,
            "name": semester.name,
            "start_date": str(semester.start_date),
            "end_date": str(semester.end_date),
            "theme": semester.theme,
            "focus_description": semester.focus_description,
            "period_type": period_label
        }
    )


# ============================================================================
# LFA_PLAYER YOUTH: QUARTERLY SEASONS (4/year)
# ============================================================================

@router.post("/lfa-player/youth", response_model=PeriodGenerationResponse)
def generate_lfa_player_youth_season(
    request: LFAPlayerYouthRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Generate a single quarterly season for LFA_PLAYER YOUTH

    Generates one of 4 quarterly seasons (Q1-Q4) for the specified year.

    Args:
        request: LFAPlayerYouthRequest with year, quarter (1-4), location_id
        db: Database session
        current_user: Authenticated admin user

    Returns:
        PeriodGenerationResponse with success message and generated season details

    Raises:
        HTTPException 400: Invalid quarter or season already exists
        HTTPException 404: Location not found
    """
    # Validate quarter
    if not 1 <= request.quarter <= 4:
        raise HTTPException(status_code=400, detail="Quarter must be between 1-4")

    # Get template
    template = LFA_PLAYER_YOUTH_TEMPLATE
    quarter_theme = next((t for t in template["themes"] if t["quarter"] == request.quarter), None)
    if not quarter_theme:
        raise HTTPException(status_code=400, detail=f"No template for quarter {request.quarter}")

    # Validate location
    location = db.query(Location).filter(Location.id == request.location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    # Generate code: "2025/LFA_PLAYER_YOUTH_Q2"
    code = f"{request.year}/LFA_PLAYER_YOUTH_{quarter_theme['code']}"

    # Check if already exists
    exists, existing = check_existing_period(db, "LFA_PLAYER_YOUTH", code)
    if exists and not request.force_overwrite:
        raise HTTPException(
            status_code=400,
            detail=f"Season {code} already exists. Use force_overwrite=true to replace."
        )

    # Calculate dates (first Monday of first month to last Sunday of last month)
    months = quarter_theme["months"]
    start_date = get_first_monday(request.year, months[0])
    end_date = get_last_sunday(request.year, months[-1])

    # Create or update semester
    if exists and request.force_overwrite:
        semester = existing
        semester.start_date = start_date
        semester.end_date = end_date
        semester.theme = quarter_theme["theme"]
        semester.focus_description = quarter_theme["focus"]
        semester.location_id = location.id
    else:
        semester = Semester(
            code=code,
            name=f"{request.year} LFA_PLAYER YOUTH - {quarter_theme['theme']}",
            start_date=start_date,
            end_date=end_date,
            specialization_type="LFA_PLAYER_YOUTH",
            age_group="YOUTH",
            theme=quarter_theme["theme"],
            focus_description=quarter_theme["focus"],
            is_active=True,
            status=SemesterStatus.DRAFT,
            location_id=location.id
        )
        db.add(semester)

    db.commit()
    db.refresh(semester)

    # Return with intelligent labeling
    period_label = get_period_label("LFA_PLAYER")
    return PeriodGenerationResponse(
        success=True,
        message=f"Successfully generated {period_label} {quarter_theme['code']} for {request.year}/LFA_PLAYER/YOUTH",
        period={
            "code": semester.code,
            "name": semester.name,
            "start_date": str(semester.start_date),
            "end_date": str(semester.end_date),
            "theme": semester.theme,
            "focus_description": semester.focus_description,
            "period_type": period_label
        }
    )


# ============================================================================
# LFA_PLAYER AMATEUR: ANNUAL SEASON (1/year: Jul-Jun, same as PRO)
# ============================================================================

@router.post("/lfa-player/amateur", response_model=PeriodGenerationResponse)
def generate_lfa_player_amateur_season(
    request: LFAPlayerAmateurRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Generate annual season for LFA_PLAYER AMATEUR (Jul-Jun)

    Generates one annual season running from July (year N) to June (year N+1).
    Same structure as PRO level.

    Args:
        request: LFAPlayerAmateurRequest with year, location_id
        db: Database session
        current_user: Authenticated admin user

    Returns:
        PeriodGenerationResponse with success message and generated season details

    Raises:
        HTTPException 400: Season already exists
        HTTPException 404: Location not found
    """
    # Get template
    template = LFA_PLAYER_AMATEUR_TEMPLATE
    season_theme = template["themes"][0]  # Only one annual season

    # Validate location
    location = db.query(Location).filter(Location.id == request.location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    # Generate code: "2025/LFA_PLAYER_AMATEUR_Season"
    code = f"{request.year}/LFA_PLAYER_AMATEUR_{season_theme['code']}"

    # Check if already exists
    exists, existing = check_existing_period(db, "LFA_PLAYER_AMATEUR", code)
    if exists and not request.force_overwrite:
        raise HTTPException(
            status_code=400,
            detail=f"Season {code} already exists. Use force_overwrite=true to replace."
        )

    # Calculate dates (July year N to June year N+1)
    start_date = get_first_monday(request.year, season_theme["start_month"])
    end_date = get_last_sunday(request.year + 1, season_theme["end_month"])

    # Create or update semester
    if exists and request.force_overwrite:
        semester = existing
        semester.start_date = start_date
        semester.end_date = end_date
        semester.theme = season_theme["theme"]
        semester.focus_description = season_theme["focus"]
        semester.location_id = location.id
    else:
        semester = Semester(
            code=code,
            name=f"{request.year}/{request.year+1} LFA_PLAYER AMATEUR - {season_theme['theme']}",
            start_date=start_date,
            end_date=end_date,
            specialization_type="LFA_PLAYER_AMATEUR",
            age_group="AMATEUR",
            theme=season_theme["theme"],
            focus_description=season_theme["focus"],
            is_active=True,
            status=SemesterStatus.DRAFT,
            location_id=location.id
        )
        db.add(semester)

    db.commit()
    db.refresh(semester)

    # Return with intelligent labeling
    period_label = get_period_label("LFA_PLAYER")
    return PeriodGenerationResponse(
        success=True,
        message=f"Successfully generated {period_label} for {request.year}/{request.year+1} LFA_PLAYER/AMATEUR",
        period={
            "code": semester.code,
            "name": semester.name,
            "start_date": str(semester.start_date),
            "end_date": str(semester.end_date),
            "theme": semester.theme,
            "focus_description": semester.focus_description,
            "period_type": period_label
        }
    )


# ============================================================================
# LFA_PLAYER PRO: ANNUAL SEASON (1/year)
# ============================================================================

@router.post("/lfa-player/pro", response_model=PeriodGenerationResponse)
def generate_lfa_player_pro_season(
    request: LFAPlayerProRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Generate annual season for LFA_PLAYER PRO

    Generates one annual season running from July (year N) to June (year N+1).

    Args:
        request: LFAPlayerProRequest with year, location_id
        db: Database session
        current_user: Authenticated admin user

    Returns:
        PeriodGenerationResponse with success message and generated season details

    Raises:
        HTTPException 400: Season already exists
        HTTPException 404: Location not found
    """
    # Get template
    template = LFA_PLAYER_PRO_TEMPLATE
    season_theme = template["themes"][0]  # Only one annual season

    # Validate location
    location = db.query(Location).filter(Location.id == request.location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    # Generate code: "2025/LFA_PLAYER_PRO_Season"
    code = f"{request.year}/LFA_PLAYER_PRO_{season_theme['code']}"

    # Check if already exists
    exists, existing = check_existing_period(db, "LFA_PLAYER_PRO", code)
    if exists and not request.force_overwrite:
        raise HTTPException(
            status_code=400,
            detail=f"Season {code} already exists. Use force_overwrite=true to replace."
        )

    # Calculate dates (July year N to June year N+1)
    start_date = get_first_monday(request.year, season_theme["start_month"])
    end_date = get_last_sunday(request.year + 1, season_theme["end_month"])

    # Create or update semester
    if exists and request.force_overwrite:
        semester = existing
        semester.start_date = start_date
        semester.end_date = end_date
        semester.theme = season_theme["theme"]
        semester.focus_description = season_theme["focus"]
        semester.location_id = location.id
    else:
        semester = Semester(
            code=code,
            name=f"{request.year} LFA_PLAYER PRO - {season_theme['theme']}",
            start_date=start_date,
            end_date=end_date,
            specialization_type="LFA_PLAYER_PRO",
            age_group="PRO",
            theme=season_theme["theme"],
            focus_description=season_theme["focus"],
            is_active=True,
            status=SemesterStatus.DRAFT,
            location_id=location.id
        )
        db.add(semester)

    db.commit()
    db.refresh(semester)

    # Return with intelligent labeling
    period_label = get_period_label("LFA_PLAYER")
    return PeriodGenerationResponse(
        success=True,
        message=f"Successfully generated {period_label} for {request.year}/LFA_PLAYER/PRO",
        period={
            "code": semester.code,
            "name": semester.name,
            "start_date": str(semester.start_date),
            "end_date": str(semester.end_date),
            "theme": semester.theme,
            "focus_description": semester.focus_description,
            "period_type": period_label
        }
    )
