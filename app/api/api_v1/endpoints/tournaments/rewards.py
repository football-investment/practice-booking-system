"""
Tournament Rewards API Endpoints

Handles tournament ranking submission, reward calculation, and distribution.
"""
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.semester import Semester
from app.models.tournament_ranking import TournamentRanking
from app.models.credit_transaction import CreditTransaction, TransactionType
from app.services.tournament.status_validator import validate_status_transition


router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class RankingSubmissionItem(BaseModel):
    """Single player ranking entry"""
    user_id: int
    rank: int = Field(ge=1, description="Player rank (1 = 1st place, 2 = 2nd place, etc.)")
    points: Optional[float] = Field(default=0, description="Optional match points/score")


class RankingSubmissionRequest(BaseModel):
    """Bulk ranking submission for tournament"""
    rankings: List[RankingSubmissionItem]
    notes: Optional[str] = Field(default=None, max_length=500)


class RankingSubmissionResponse(BaseModel):
    """Response after submitting rankings"""
    tournament_id: int
    tournament_name: str
    rankings_submitted: int
    message: str


class RewardDistributionRequest(BaseModel):
    """Request to distribute rewards"""
    reason: Optional[str] = Field(default=None, max_length=200)


class RewardDistributionResponse(BaseModel):
    """Response after distributing rewards"""
    tournament_id: int
    tournament_name: str
    rewards_distributed: int
    total_credits_awarded: int
    status: str
    message: str


# ============================================================================
# DEFAULT REWARD POLICY
# ============================================================================

DEFAULT_REWARD_POLICY = {
    "policy_name": "default",
    "policy_version": "1.0",
    "rewards": {
        "1": {"credits": 500, "xp": 100, "description": "1st Place"},
        "2": {"credits": 300, "xp": 75, "description": "2nd Place"},
        "3": {"credits": 200, "xp": 50, "description": "3rd Place"},
        "participant": {"credits": 50, "xp": 25, "description": "Participation"}
    }
}


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/{tournament_id}/rankings", response_model=RankingSubmissionResponse)
def submit_tournament_rankings(
    tournament_id: int,
    request: RankingSubmissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit final rankings for a completed tournament (Instructor/Admin only)

    Business Rules:
    - Tournament must be in COMPLETED status
    - Only instructor assigned to tournament or admins can submit rankings
    - All enrolled active players must be ranked
    - Ranks must be unique and sequential starting from 1
    """

    # Authorization: Admin or assigned instructor
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Check user authorization
    is_admin = current_user.role == UserRole.ADMIN
    is_assigned_instructor = (
        current_user.role == UserRole.INSTRUCTOR and
        tournament.master_instructor_id == current_user.id
    )

    if not (is_admin or is_assigned_instructor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned instructor or admins can submit rankings"
        )

    # Validate tournament status
    if tournament.tournament_status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tournament must be COMPLETED to submit rankings. Current status: {tournament.tournament_status}"
        )

    # Get enrolled players
    from app.models.semester_enrollment import SemesterEnrollment
    enrollments = db.query(SemesterEnrollment).filter(
        SemesterEnrollment.semester_id == tournament_id,
        SemesterEnrollment.is_active == True
    ).all()

    enrolled_user_ids = {e.user_id for e in enrollments}

    # Validate rankings
    submitted_user_ids = {r.user_id for r in request.rankings}
    submitted_ranks = [r.rank for r in request.rankings]

    # Check all enrolled players are ranked
    if submitted_user_ids != enrolled_user_ids:
        missing = enrolled_user_ids - submitted_user_ids
        extra = submitted_user_ids - enrolled_user_ids
        error_parts = []
        if missing:
            error_parts.append(f"Missing rankings for user IDs: {missing}")
        if extra:
            error_parts.append(f"Extra rankings for non-enrolled user IDs: {extra}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(error_parts)
        )

    # Check ranks are unique and sequential
    if len(submitted_ranks) != len(set(submitted_ranks)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ranks must be unique (no ties allowed)"
        )

    expected_ranks = set(range(1, len(submitted_ranks) + 1))
    if set(submitted_ranks) != expected_ranks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ranks must be sequential from 1 to {len(submitted_ranks)}"
        )

    # Delete existing rankings (if re-submitting)
    db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == tournament_id
    ).delete()

    # Create new ranking records
    for ranking_item in request.rankings:
        ranking = TournamentRanking(
            tournament_id=tournament_id,
            user_id=ranking_item.user_id,
            team_id=None,  # Individual tournament
            participant_type="INDIVIDUAL",
            rank=ranking_item.rank,
            points=ranking_item.points or 0,
            wins=0,  # Can be extended later
            losses=0,
            draws=0
        )
        db.add(ranking)

    db.commit()

    return RankingSubmissionResponse(
        tournament_id=tournament_id,
        tournament_name=tournament.name,
        rankings_submitted=len(request.rankings),
        message=f"Successfully submitted rankings for {len(request.rankings)} players"
    )


@router.post("/{tournament_id}/distribute-rewards", response_model=RewardDistributionResponse)
def distribute_tournament_rewards(
    tournament_id: int,
    request: RewardDistributionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Distribute rewards to players based on rankings (Admin only)

    Business Rules:
    - Tournament must be in COMPLETED status
    - Rankings must be submitted first
    - Transitions tournament to REWARDS_DISTRIBUTED status
    - Credits are added to player accounts
    - Transactions are recorded
    """

    # Authorization: Admin only
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can distribute rewards"
        )

    # Fetch tournament
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Validate tournament status
    if tournament.tournament_status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tournament must be COMPLETED. Current status: {tournament.tournament_status}"
        )

    # Check if rankings exist
    rankings = db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == tournament_id
    ).order_by(TournamentRanking.rank).all()

    if not rankings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No rankings found. Submit rankings first before distributing rewards."
        )

    # Get or create reward policy snapshot
    reward_policy = tournament.reward_policy_snapshot or DEFAULT_REWARD_POLICY

    # Calculate and distribute rewards
    total_credits = 0
    rewards_count = 0

    for ranking in rankings:
        # Determine reward tier
        rank_key = str(ranking.rank) if str(ranking.rank) in reward_policy["rewards"] else "participant"
        reward_config = reward_policy["rewards"].get(rank_key, reward_policy["rewards"]["participant"])

        credits_amount = reward_config["credits"]
        xp_amount = reward_config["xp"]

        if credits_amount > 0:
            # Add credits to user account
            user = db.query(User).filter(User.id == ranking.user_id).first()
            if user:
                user.credit_balance += credits_amount
                total_credits += credits_amount

                # Record transaction
                transaction = CreditTransaction(
                    user_id=user.id,
                    transaction_type=TransactionType.TOURNAMENT_REWARD,
                    amount=credits_amount,
                    description=f"Tournament '{tournament.name}' - Rank #{ranking.rank} reward",
                    reference_id=str(tournament_id),
                    processed_by=current_user.id
                )
                db.add(transaction)
                rewards_count += 1

    # Transition tournament to REWARDS_DISTRIBUTED
    from app.api.api_v1.endpoints.tournaments.lifecycle import record_status_change

    old_status = tournament.tournament_status
    tournament.tournament_status = "REWARDS_DISTRIBUTED"
    tournament.reward_policy_snapshot = reward_policy  # Save policy snapshot

    record_status_change(
        db=db,
        tournament_id=tournament.id,
        old_status=old_status,
        new_status="REWARDS_DISTRIBUTED",
        changed_by=current_user.id,
        reason=request.reason or "Rewards distributed",
        metadata={"total_credits_awarded": total_credits, "rewards_count": rewards_count}
    )

    db.commit()

    return RewardDistributionResponse(
        tournament_id=tournament_id,
        tournament_name=tournament.name,
        rewards_distributed=rewards_count,
        total_credits_awarded=total_credits,
        status="REWARDS_DISTRIBUTED",
        message=f"Successfully distributed {total_credits} credits to {rewards_count} players"
    )


@router.get("/{tournament_id}/rankings")
def get_tournament_rankings(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get tournament rankings (leaderboard)
    """

    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    rankings = db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == tournament_id
    ).order_by(TournamentRanking.rank).all()

    # Include user details
    from sqlalchemy.orm import joinedload
    rankings = db.query(TournamentRanking).options(
        joinedload(TournamentRanking.user)
    ).filter(
        TournamentRanking.tournament_id == tournament_id
    ).order_by(TournamentRanking.rank).all()

    return {
        "tournament_id": tournament_id,
        "tournament_name": tournament.name,
        "tournament_status": tournament.tournament_status,
        "rankings": [
            {
                "rank": r.rank,
                "user_id": r.user_id,
                "user_name": r.user.name if r.user else None,
                "user_email": r.user.email if r.user else None,
                "points": float(r.points) if r.points else 0,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None
            }
            for r in rankings
        ],
        "total_participants": len(rankings)
    }
