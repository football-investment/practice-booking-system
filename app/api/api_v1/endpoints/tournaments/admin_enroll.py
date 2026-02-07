"""
Admin Batch Enrollment Endpoint for Tournaments
Allows admins to enroll multiple players in a tournament for testing/setup purposes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from pydantic import BaseModel

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.semester import Semester
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.models.license import UserLicense
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class BatchEnrollRequest(BaseModel):
    player_ids: List[int]


class BatchEnrollResponse(BaseModel):
    success: bool
    enrolled_count: int
    total_players: int
    failed_players: List[int]
    message: str


@router.post("/{tournament_id}/admin/batch-enroll", response_model=BatchEnrollResponse)
def admin_batch_enroll_players(
    tournament_id: int,
    request: BatchEnrollRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Admin-only endpoint to batch enroll multiple players in a tournament

    **Authorization:** Admin role only

    **Use Case:** Testing, tournament setup, admin-managed tournaments

    **Business Rules:**
    1. Admin can enroll players regardless of tournament status
    2. Auto-creates enrollments with APPROVED status
    3. Skips credit deduction (admin privilege)
    4. Auto-assigns age_category = 'PRO' for testing
    5. Requires players to have LFA_FOOTBALL_PLAYER license

    **Returns:**
    - Total enrolled count
    - List of failed player IDs
    """
    # 1. Verify admin role
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can batch enroll players"
        )

    # 2. Verify tournament exists
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    logger.info(f"🔧 ADMIN BATCH ENROLL - Tournament: {tournament_id}, Players: {len(request.player_ids)}")

    enrolled_count = 0
    failed_players = []

    for player_id in request.player_ids:
        try:
            # 3. Verify player exists and is a student
            player = db.query(User).filter(
                User.id == player_id,
                User.role == UserRole.STUDENT
            ).first()

            if not player:
                logger.warning(f"⚠️ Player {player_id} not found or not a student")
                failed_players.append(player_id)
                continue

            # 4. Get player's LFA_FOOTBALL_PLAYER license
            license = db.query(UserLicense).filter(
                UserLicense.user_id == player_id,
                UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER"
            ).first()

            if not license:
                logger.warning(f"⚠️ Player {player_id} has no LFA_FOOTBALL_PLAYER license")
                failed_players.append(player_id)
                continue

            # 5. Check if already enrolled
            existing = db.query(SemesterEnrollment).filter(
                SemesterEnrollment.user_id == player_id,
                SemesterEnrollment.semester_id == tournament_id,
                SemesterEnrollment.is_active == True
            ).first()

            if existing:
                logger.info(f"✓ Player {player_id} already enrolled")
                enrolled_count += 1
                continue

            # 6. Create enrollment (admin privilege - auto-approved, no credit deduction)
            enrollment = SemesterEnrollment(
                user_id=player_id,
                semester_id=tournament_id,
                user_license_id=license.id,
                age_category="PRO",  # Default for testing
                request_status=EnrollmentStatus.APPROVED,
                approved_at=datetime.utcnow(),
                approved_by=current_user.id,  # Admin user
                payment_verified=True,  # Admin bypass
                is_active=True,
                enrolled_at=datetime.utcnow(),
                requested_at=datetime.utcnow()
            )

            db.add(enrollment)
            enrolled_count += 1
            logger.info(f"✅ Player {player_id} enrolled successfully")

        except Exception as e:
            logger.error(f"❌ Failed to enroll player {player_id}: {str(e)}")
            failed_players.append(player_id)
            db.rollback()
            continue

    # 7. Commit all enrollments
    try:
        db.commit()
        logger.info(f"✅ BATCH ENROLL COMPLETE: {enrolled_count}/{len(request.player_ids)} players enrolled")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ BATCH ENROLL FAILED: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to commit enrollments: {str(e)}"
        )

    return BatchEnrollResponse(
        success=enrolled_count == len(request.player_ids),
        enrolled_count=enrolled_count,
        total_players=len(request.player_ids),
        failed_players=failed_players,
        message=f"Successfully enrolled {enrolled_count}/{len(request.player_ids)} players"
    )
