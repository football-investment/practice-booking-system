"""
Tournament Enrollment API Endpoint
Students can enroll in available tournaments
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.semester import Semester, SemesterStatus
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.models.license import UserLicense
from app.models.session import Session as SessionModel
from app.models.booking import Booking, BookingStatus
from app.schemas.tournament import EnrollmentResponse, EnrollmentConflict
from app.services.age_category_service import (
    get_automatic_age_category,
    get_current_season_year,
    calculate_age_at_season_start
)
from app.services.enrollment_conflict_service import EnrollmentConflictService


router = APIRouter()

# Module-level logging to confirm this file loads
import logging
_module_logger = logging.getLogger(__name__)
_module_logger.error(f"🔥 TOURNAMENTS/ENROLL.PY MODULE LOADED SUCCESSFULLY")


@router.post("/{tournament_id}/enroll", response_model=EnrollmentResponse)
def enroll_in_tournament(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Enroll current student in a tournament

    **Authorization:** Student role only

    **Validations:**
    1. Tournament exists and status is READY_FOR_ENROLLMENT
    2. Student has LFA_FOOTBALL_PLAYER license
    3. Age category enrollment rules:
       - PRE (5-13): Can ONLY enroll in PRE tournaments
       - YOUTH (14-18): Can enroll in YOUTH OR AMATEUR (NOT PRO)
       - AMATEUR (18+): Can ONLY enroll in AMATEUR tournaments
       - PRO (18+): Can ONLY enroll in PRO tournaments
    4. Student not already enrolled
    5. Sufficient credit balance
    6. Conflict check (WARNING only, non-blocking)

    **Creates:**
    - SemesterEnrollment record (AUTO-APPROVED, is_active=True)
    - Deducts enrollment_cost from credit balance (INSTANT payment)
    - Assigns age_category based on age at season start (July 1)

    **Returns:**
    - Enrollment details
    - Conflict warnings (if any)
    - Credits remaining after enrollment
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"🚀 ENROLLMENT START - Tournament: {tournament_id}, User: {current_user.id}, Email: {current_user.email}")

    # 1. Fetch tournament
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found"
        )

    # 2. Verify tournament status
    if tournament.status != "READY_FOR_ENROLLMENT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tournament not ready for enrollment (status: {tournament.status})"
        )

    # 2.5. Verify enrollment deadline (1 hour before first tournament session)
    from datetime import timedelta
    # Get first session to determine actual tournament start time
    first_session = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id
    ).order_by(SessionModel.date_start).first()

    if first_session and first_session.date_start:
        enrollment_deadline = first_session.date_start - timedelta(hours=1)
        if datetime.utcnow() >= enrollment_deadline:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Enrollment closed - tournament starting soon (deadline: {enrollment_deadline.strftime('%Y-%m-%d %H:%M')} UTC)"
            )

    # 3. Verify student role
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can enroll in tournaments"
        )

    # 4. Get student's LFA_FOOTBALL_PLAYER license
    license = db.query(UserLicense).filter(
        UserLicense.user_id == current_user.id,
        UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER"
    ).first()

    if not license:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LFA Football Player license not found. Please unlock this specialization first."
        )

    # 5. Calculate age category at season start (July 1)
    if not current_user.date_of_birth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date of birth not set. Please set your date of birth in your profile."
        )

    season_year = get_current_season_year()
    age_at_season_start = calculate_age_at_season_start(current_user.date_of_birth, season_year)
    player_age_category = get_automatic_age_category(age_at_season_start)

    # For 18+ users, automatically infer category from tournament age group
    if not player_age_category:
        tournament_age_group = tournament.age_group
        if tournament_age_group in ["AMATEUR", "PRO"]:
            player_age_category = tournament_age_group
            logger.info(f"✅ Auto-assigned age category {player_age_category} to user {current_user.id} based on tournament {tournament.code}")
        else:
            # Tournament is PRE or YOUTH, but player is 18+
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You are over 18 and cannot enroll in {tournament_age_group} tournaments. Please enroll in AMATEUR or PRO tournaments."
            )

    # 6. Verify age category enrollment rules using shared validation
    from app.services.tournament.validation import validate_tournament_enrollment_age

    tournament_age_group = tournament.age_group
    is_valid, error_message = validate_tournament_enrollment_age(
        player_age_category,
        tournament_age_group
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    # 7. Check not already enrolled using shared validation
    from app.services.tournament.validation import check_duplicate_enrollment

    is_unique, duplicate_message = check_duplicate_enrollment(
        db,
        current_user.id,
        tournament_id
    )

    if not is_unique:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=duplicate_message
        )

    # 8. Check credit balance (use user-level credit_balance, not license-level)
    enrollment_cost = tournament.enrollment_cost or 500
    if current_user.credit_balance < enrollment_cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient credits: Need {enrollment_cost}, you have {current_user.credit_balance}"
        )

    # 9. Check conflicts (WARNING only - non-blocking)
    conflict_result = EnrollmentConflictService.check_session_time_conflict(
        user_id=current_user.id,
        semester_id=tournament_id,
        db=db
    )

    conflicts_list = []
    warnings_list = []

    if conflict_result and conflict_result.get("has_conflict"):
        for conflict in conflict_result.get("conflicts", []):
            conflicts_list.append(EnrollmentConflict(
                type=conflict.get("type", "time_overlap"),
                severity=conflict.get("severity", "warning"),
                message=conflict.get("message", ""),
                conflicting_session_id=conflict.get("session_id"),
                conflicting_semester_name=conflict.get("semester_name")
            ))

    if conflict_result and conflict_result.get("warnings"):
        warnings_list = conflict_result.get("warnings", [])

    # 10. Create enrollment record (AUTO-APPROVED ✅)
    enrollment = SemesterEnrollment(
        user_id=current_user.id,
        semester_id=tournament_id,
        user_license_id=license.id,
        age_category=player_age_category,
        request_status=EnrollmentStatus.APPROVED,  # ✅ AUTO-APPROVE (no manual approval)
        approved_at=datetime.utcnow(),
        approved_by=current_user.id,  # Self-enrollment
        payment_verified=True,  # ✅ INSTANT CREDIT PAYMENT (no manual verification)
        is_active=True,
        enrolled_at=datetime.utcnow(),
        requested_at=datetime.utcnow()
    )

    db.add(enrollment)

    # 11. Deduct credits from user (INSTANT payment - uses deprecated user-level credit_balance)
    # CRITICAL: Must explicitly add user to session for SQLAlchemy to track changes
    current_user.credit_balance = current_user.credit_balance - enrollment_cost
    db.add(current_user)  # ✅ THIS IS REQUIRED! Without this, SQLAlchemy won't track the change

    # 11.5. Create credit transaction record for audit trail
    from app.models.credit_transaction import CreditTransaction

    credit_transaction = CreditTransaction(
        user_license_id=license.id,
        transaction_type="TOURNAMENT_ENROLLMENT",
        amount=-enrollment_cost,  # Negative amount for deduction
        balance_after=current_user.credit_balance,
        description=f"Tournament enrollment: {tournament.name} ({tournament.code})",
        semester_id=tournament_id,
        enrollment_id=None  # Will be updated after enrollment is committed
    )
    db.add(credit_transaction)
    db.flush()  # Get enrollment.id before commit

    # Update transaction with enrollment_id
    credit_transaction.enrollment_id = enrollment.id
    db.add(credit_transaction)

    # 11.7. Auto-create booking for tournament session (tournament enrollment = auto-booking)
    # Get the tournament's session
    tournament_session = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id
    ).first()

    if tournament_session:
        # Create booking automatically
        booking = Booking(
            user_id=current_user.id,
            session_id=tournament_session.id,
            status=BookingStatus.CONFIRMED,
            created_at=datetime.utcnow()
        )
        db.add(booking)
        logger.info(f"✅ Auto-created booking for session {tournament_session.id}")
    else:
        logger.warning(f"⚠️ No session found for tournament {tournament_id} - booking not created")

    # 12. Commit transaction
    import logging
    import traceback
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"🔍 PRE-COMMIT DEBUG:")
        logger.info(f"   - Tournament ID: {tournament_id}, Name: {tournament.name}")
        logger.info(f"   - User ID: {current_user.id}, Email: {current_user.email}")
        logger.info(f"   - Credit balance BEFORE: {current_user.credit_balance + enrollment_cost}")
        logger.info(f"   - Credit balance AFTER: {current_user.credit_balance}")
        logger.info(f"   - Enrollment ID (pre-flush): {enrollment.id}")
        logger.info(f"   - Transaction amount: {credit_transaction.amount}")
        logger.info(f"   - Transaction balance_after: {credit_transaction.balance_after}")

        db.commit()
        db.refresh(enrollment)
        db.refresh(current_user)

        logger.info(f"✅ ENROLLMENT SUCCESS: Enrollment ID = {enrollment.id}")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ TOURNAMENT ENROLLMENT FAILED: {str(e)}")
        logger.error(f"❌ ERROR TYPE: {type(e).__name__}")
        logger.error(f"❌ FULL TRACEBACK:")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create enrollment: {str(e)}"
        )

    # 13. Serialize response data
    enrollment_dict = {
        "id": enrollment.id,
        "user_id": enrollment.user_id,
        "semester_id": enrollment.semester_id,
        "user_license_id": enrollment.user_license_id,
        "age_category": enrollment.age_category,
        "request_status": enrollment.request_status.value,
        "payment_verified": enrollment.payment_verified,
        "is_active": enrollment.is_active,
        "enrolled_at": enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None,
        "approved_at": enrollment.approved_at.isoformat() if enrollment.approved_at else None
    }

    tournament_dict = {
        "id": tournament.id,
        "code": tournament.code,
        "name": tournament.name,
        "start_date": tournament.start_date.isoformat(),
        "end_date": tournament.end_date.isoformat(),
        "age_group": tournament.age_group,
        "enrollment_cost": enrollment_cost
    }

    # 14. Return response with warnings
    return {
        "success": True,
        "enrollment": enrollment_dict,
        "tournament": tournament_dict,
        "conflicts": conflicts_list,
        "warnings": warnings_list,
        "credits_remaining": current_user.credit_balance
    }
