"""
Tournament Rewards API Endpoints

Handles tournament ranking submission, reward calculation, and distribution.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.semester import Semester
from app.models.tournament_ranking import TournamentRanking
from app.models.tournament_achievement import TournamentParticipation
from app.models.credit_transaction import CreditTransaction, TransactionType
from app.models.xp_transaction import XPTransaction


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


class PlayerRewardDetail(BaseModel):
    """Individual player reward details"""
    user_id: int
    player_name: str
    player_email: str
    rank: int
    credits: int
    xp: int


class RewardDistributionResponse(BaseModel):
    """Response after distributing rewards"""
    tournament_id: int
    tournament_name: str
    rewards_distributed: int
    total_credits_awarded: int
    total_xp_awarded: int
    status: str
    message: str
    rewards: List[PlayerRewardDetail]


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

    # Defensive: Ensure reward_policy has valid structure
    # Support both OLD format (rewards) and NEW format (placement_rewards)
    if not isinstance(reward_policy, dict):
        reward_policy = DEFAULT_REWARD_POLICY

    # Detect which format is being used
    if "rewards" in reward_policy:
        # OLD format: { "rewards": { "1": {...}, "2": {...}, "participant": {...} } }
        rewards_map = reward_policy["rewards"]
    elif "placement_rewards" in reward_policy:
        # NEW format: { "placement_rewards": { "1ST": {...}, "2ND": {...}, "PARTICIPANT": {...} } }
        placement_rewards = reward_policy["placement_rewards"]
        # Convert NEW format to OLD format for backward compatibility
        rewards_map = {
            "1": placement_rewards.get("1ST", placement_rewards.get("PARTICIPANT", {"credits": 0, "xp": 0})),
            "2": placement_rewards.get("2ND", placement_rewards.get("PARTICIPANT", {"credits": 0, "xp": 0})),
            "3": placement_rewards.get("3RD", placement_rewards.get("PARTICIPANT", {"credits": 0, "xp": 0})),
            "participant": placement_rewards.get("PARTICIPANT", {"credits": 0, "xp": 0})
        }
    else:
        # Fallback to DEFAULT if neither format is present
        reward_policy = DEFAULT_REWARD_POLICY
        rewards_map = reward_policy["rewards"]

    # Calculate and distribute rewards
    total_credits = 0
    total_xp = 0
    rewards_count = 0
    reward_details = []

    for ranking in rankings:
        # Determine reward tier
        rank_key = str(ranking.rank) if str(ranking.rank) in rewards_map else "participant"
        reward_config = rewards_map.get(rank_key, rewards_map["participant"])

        credits_amount = reward_config["credits"]
        xp_amount = reward_config["xp"]

        # Get user details
        user = db.query(User).filter(User.id == ranking.user_id).first()
        if not user:
            continue

        # Add credits to user account (only if > 0)
        if credits_amount > 0:
            user.credit_balance += credits_amount
            total_credits += credits_amount

            # Record credit transaction
            credit_transaction = CreditTransaction(
                user_id=user.id,
                transaction_type=TransactionType.TOURNAMENT_REWARD.value,  # Convert enum to string
                amount=credits_amount,
                balance_after=user.credit_balance,
                description=f"Tournament '{tournament.name}' - Rank #{ranking.rank} reward",
                semester_id=tournament_id
            )
            db.add(credit_transaction)

        # Add XP to user account (always, even if 0 to track participation)
        if xp_amount > 0:
            user.xp_balance += xp_amount
            total_xp += xp_amount

            # Record XP transaction
            xp_transaction = XPTransaction(
                user_id=user.id,
                transaction_type="TOURNAMENT_REWARD",
                amount=xp_amount,
                balance_after=user.xp_balance,
                description=f"Tournament '{tournament.name}' - Rank #{ranking.rank} reward",
                semester_id=tournament_id
            )
            db.add(xp_transaction)

        rewards_count += 1

        # Add to reward details list
        reward_details.append(PlayerRewardDetail(
            user_id=user.id,
            player_name=user.name,
            player_email=user.email,
            rank=ranking.rank,
            credits=credits_amount,
            xp=xp_amount
        ))

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
        total_xp_awarded=total_xp,
        status="REWARDS_DISTRIBUTED",
        message=f"Successfully distributed {total_credits} credits and {total_xp} XP to {rewards_count} players",
        rewards=reward_details
    )


@router.get("/{tournament_id}/distributed-rewards")
def get_distributed_rewards(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get list of distributed rewards for a tournament (for instructor view)

    Returns:
    - List of players with their rank, credits, and XP received
    - Total credits and XP awarded
    - Distribution timestamp

    Authorization: INSTRUCTOR (assigned) or ADMIN
    """
    # Check authorization
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()

    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    if current_user.role == UserRole.ADMIN:
        pass  # Admin can access any tournament
    elif current_user.role == UserRole.INSTRUCTOR:
        if tournament.master_instructor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this tournament"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and admins can view distributed rewards"
        )

    # Check if rewards have been distributed
    if tournament.tournament_status != "REWARDS_DISTRIBUTED":
        return {
            "tournament_id": tournament_id,
            "tournament_name": tournament.name,
            "rewards_distributed": False,
            "message": "Rewards have not been distributed yet",
            "rewards": []
        }

    # Get credit transactions for this tournament
    from app.models.credit_transaction import CreditTransaction

    credit_transactions = db.query(CreditTransaction).filter(
        CreditTransaction.semester_id == tournament_id,
        CreditTransaction.transaction_type == TransactionType.TOURNAMENT_REWARD.value
    ).all()

    # Get XP transactions for this tournament
    from app.models.xp_transaction import XPTransaction

    xp_transactions = db.query(XPTransaction).filter(
        XPTransaction.semester_id == tournament_id,
        XPTransaction.transaction_type == "TOURNAMENT_REWARD"
    ).all()

    # Build reward details from transactions
    reward_map = {}  # {user_id: {credits, xp, rank}}

    for txn in credit_transactions:
        if txn.user_id not in reward_map:
            reward_map[txn.user_id] = {"credits": 0, "xp": 0, "rank": None}
        reward_map[txn.user_id]["credits"] += txn.amount

        # Extract rank from description (e.g., "Rank #1 reward")
        if "Rank #" in txn.description:
            try:
                rank_str = txn.description.split("Rank #")[1].split()[0]
                reward_map[txn.user_id]["rank"] = int(rank_str)
            except:
                pass

    for txn in xp_transactions:
        if txn.user_id not in reward_map:
            reward_map[txn.user_id] = {"credits": 0, "xp": 0, "rank": None}
        reward_map[txn.user_id]["xp"] += txn.amount

        # Extract rank if not already set
        if reward_map[txn.user_id]["rank"] is None and "Rank #" in txn.description:
            try:
                rank_str = txn.description.split("Rank #")[1].split()[0]
                reward_map[txn.user_id]["rank"] = int(rank_str)
            except:
                pass

    # Get user details and build final list
    user_ids = list(reward_map.keys())
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_dict = {user.id: user for user in users}

    reward_details = []
    total_credits = 0
    total_xp = 0

    for user_id, data in reward_map.items():
        user = user_dict.get(user_id)
        if not user:
            continue

        reward_details.append({
            "user_id": user_id,
            "player_name": user.name or user.email,
            "player_email": user.email,
            "rank": data["rank"],
            "credits": data["credits"],
            "xp": data["xp"]
        })

        total_credits += data["credits"]
        total_xp += data["xp"]

    # Sort by rank
    reward_details.sort(key=lambda x: x["rank"] if x["rank"] else 999)

    return {
        "tournament_id": tournament_id,
        "tournament_name": tournament.name,
        "rewards_distributed": True,
        "total_credits_awarded": total_credits,
        "total_xp_awarded": total_xp,
        "rewards_count": len(reward_details),
        "rewards": reward_details
    }


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

    # Include user details and reward data from tournament_participations
    from sqlalchemy.orm import joinedload
    rankings = db.query(TournamentRanking).options(
        joinedload(TournamentRanking.user)
    ).filter(
        TournamentRanking.tournament_id == tournament_id
    ).order_by(TournamentRanking.rank).all()

    # Fetch reward data from tournament_participations
    participation_rewards = {}
    participations = db.query(TournamentParticipation).filter(
        TournamentParticipation.semester_id == tournament_id
    ).all()

    for p in participations:
        participation_rewards[p.user_id] = {
            "credits_awarded": p.credits_awarded,
            "xp_awarded": p.xp_awarded,
            "skill_points_awarded": p.skill_points_awarded or {}
        }

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
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                # Add reward data
                "credits_awarded": participation_rewards.get(r.user_id, {}).get("credits_awarded", 0),
                "xp_awarded": participation_rewards.get(r.user_id, {}).get("xp_awarded", 0),
                "skill_points_awarded": participation_rewards.get(r.user_id, {}).get("skill_points_awarded", {})
            }
            for r in rankings
        ],
        "total_participants": len(rankings)
    }
