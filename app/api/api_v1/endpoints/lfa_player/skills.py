"""
LFA Player skill management — legacy endpoint (deprecated)

The skill update endpoint has been superseded by the 29-skill system
stored in UserLicense.football_skills JSONB and updated via
app/api/api_v1/endpoints/licenses/skills.py.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User

router = APIRouter()


@router.put("/licenses/{license_id}/skills", status_code=status.HTTP_410_GONE)
def update_skill(
    license_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a skill average — **DEPRECATED (410 Gone)**

    Skill updates are now handled via the 29-skill system.
    Use PUT /licenses/{license_id}/football-skills instead.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Skill updates via this endpoint are deprecated. Use PUT /licenses/{license_id}/football-skills instead."
    )
