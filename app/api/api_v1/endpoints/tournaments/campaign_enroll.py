"""POST /api/v1/tournaments/{tournament_id}/bulk-enroll-campaign

Admin-only endpoint. Bulk-enrolls all eligible sponsor campaign audience
entries as SemesterEnrollment rows for a PROMOTION_EVENT tournament.

Allowed only in DRAFT or ENROLLMENT_CLOSED status.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_web
from app.models.semester import SemesterCategory
from app.models.semester import Semester
from app.models.user import User, UserRole
import app.services.tournament.campaign_enrollment_service as _svc

router = APIRouter()


@router.post("/{tournament_id}/bulk-enroll-campaign")
def bulk_enroll_campaign_audience(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_web),
):
    """Bulk-enroll all eligible campaign audience entries for a PROMOTION_EVENT.

    Returns:
        {
            "enrolled_count": int,
            "skipped_count": int,
            "enrolled": [user_id, ...],
            "skipped": [{"user_id": int, "reason": str}, ...]
        }
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    if tournament.semester_category != SemesterCategory.PROMOTION_EVENT:
        raise HTTPException(
            status_code=400,
            detail="bulk-enroll-campaign is only available for PROMOTION_EVENT tournaments",
        )

    try:
        result = _svc.bulk_enroll_from_campaign(db, tournament_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    db.commit()
    return JSONResponse(content=result)
