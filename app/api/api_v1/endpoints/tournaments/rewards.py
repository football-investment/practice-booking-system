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
from app.models.skill_reward import SkillReward

# ✅ Import centralized services for idempotent reward distribution
from app.services.credit_service import CreditService
from app.services.xp_transaction_service import XPTransactionService
from app.services.football_skill_service import FootballSkillService


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
    winner_count: Optional[int] = Field(default=None, description="Number of winners for INDIVIDUAL_RANKING tournaments (E2E testing)")


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

    # 🔒 IDEMPOTENCY CHECK: Prevent re-submission if rewards already distributed
    if tournament.tournament_status == "REWARDS_DISTRIBUTED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify rankings after rewards have been distributed. Tournament is locked."
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

    # ✅ NEW: Allow tied ranks (multiple players can have same rank)
    # Validation: Ranks must start from 1 and be properly ordered
    min_rank = min(submitted_ranks)
    max_rank = max(submitted_ranks)

    if min_rank != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ranks must start from 1"
        )

    # Check that ranks make sense (e.g., can't have rank 5 without ranks 1-4 existing)
    unique_ranks = sorted(set(submitted_ranks))
    for i, rank in enumerate(unique_ranks):
        # After ties, next rank must skip properly
        # Example: 1, 2, 2, 4 is valid (skip 3 after two 2nds)
        # But: 1, 2, 2, 5 is invalid (should be 4, not 5)
        count_up_to_current = sum(1 for r in submitted_ranks if r <= rank)
        expected_next_rank = count_up_to_current + 1

        # The next unique rank after current should be expected_next_rank
        if i + 1 < len(unique_ranks):
            next_rank = unique_ranks[i + 1]
            count_at_current = sum(1 for r in submitted_ranks if r == rank)
            expected = rank + count_at_current
            if next_rank != expected:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid rank sequence: after {count_at_current} player(s) at rank {rank}, next rank should be {expected}, not {next_rank}"
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


@router.post("/{tournament_id}/complete")
def complete_tournament(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Complete tournament and transition to COMPLETED status

    Business Rules:
    - Tournament must be in IN_PROGRESS status
    - All sessions must be finalized (for INDIVIDUAL_RANKING) or results submitted (for HEAD_TO_HEAD)
    - Transitions tournament to COMPLETED status
    - Creates final rankings in tournament_rankings table

    Authorization: Admin OR tournament master instructor
    """

    # Fetch tournament first to check authorization
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament {tournament_id} not found"
        )

    # Authorization: Admin OR master instructor of this tournament
    is_admin = current_user.role == UserRole.ADMIN
    is_master_instructor = tournament.master_instructor_id == current_user.id

    if not (is_admin or is_master_instructor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins or the tournament's master instructor can complete tournaments"
        )

    # Validate tournament status
    if tournament.tournament_status != "IN_PROGRESS":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tournament must be IN_PROGRESS. Current status: {tournament.tournament_status}"
        )

    # Check if all sessions are finalized (INDIVIDUAL_RANKING) or have results (HEAD_TO_HEAD)
    from app.models.session import Session as SessionModel

    sessions = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.auto_generated == True
    ).all()

    if not sessions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No sessions found for this tournament"
        )

    # For INDIVIDUAL_RANKING: Check all sessions have game_results (finalized)
    if tournament.format == "INDIVIDUAL_RANKING":
        unfinalized = [s.id for s in sessions if not s.game_results]
        if unfinalized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot complete tournament: {len(unfinalized)} session(s) not finalized. Session IDs: {unfinalized}"
            )

    # For HEAD_TO_HEAD: Check all sessions have game_results (results submitted)
    else:
        no_results = [s.id for s in sessions if not s.game_results]
        if no_results:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot complete tournament: {len(no_results)} session(s) missing results. Session IDs: {no_results}"
            )

    # Create final rankings in tournament_rankings table
    # For INDIVIDUAL_RANKING: Rankings already exist from finalization
    # For HEAD_TO_HEAD: Need to calculate rankings from match results
    from app.models.tournament_ranking import TournamentRanking

    existing_rankings = db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == tournament_id
    ).count()

    if existing_rankings == 0:
        # No rankings exist yet - create them from session results
        # This handles HEAD_TO_HEAD tournaments where finalization doesn't run

        # Get all participants from enrollments
        from app.models.semester_enrollment import SemesterEnrollment

        enrollments = db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tournament_id,
            SemesterEnrollment.is_active == True
        ).all()

        # For HEAD_TO_HEAD: Calculate rankings from wins/losses
        # For INDIVIDUAL_RANKING: Should not reach here (finalization creates rankings)
        if tournament.format == "HEAD_TO_HEAD":
            # Simple ranking: All participants get same rank for now
            # TODO: Implement proper HEAD_TO_HEAD ranking calculation
            for idx, enrollment in enumerate(enrollments):
                ranking = TournamentRanking(
                    tournament_id=tournament_id,
                    user_id=enrollment.user_id,
                    team_id=None,
                    participant_type="INDIVIDUAL",
                    rank=idx + 1,  # Temporary: sequential ranks
                    points=0,
                    wins=0,
                    losses=0,
                    draws=0
                )
                db.add(ranking)
        else:
            # INDIVIDUAL_RANKING without rankings - this is an error state
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot complete INDIVIDUAL_RANKING tournament: No rankings found. Ensure all sessions are finalized."
            )

    # Transition tournament to COMPLETED status
    from app.api.api_v1.endpoints.tournaments.lifecycle import record_status_change

    old_status = tournament.tournament_status
    tournament.tournament_status = "COMPLETED"

    record_status_change(
        db=db,
        tournament_id=tournament.id,
        old_status=old_status,
        new_status="COMPLETED",
        changed_by=current_user.id,
        reason="Tournament completed - all sessions finalized",
        metadata={"sessions_count": len(sessions), "rankings_count": existing_rankings or len(enrollments)}
    )

    db.commit()
    db.refresh(tournament)

    return {
        "tournament_id": tournament_id,
        "tournament_name": tournament.name,
        "old_status": old_status,
        "new_status": "COMPLETED",
        "sessions_completed": len(sessions),
        "rankings_created": existing_rankings or len(enrollments),
        "message": "Tournament completed successfully. Ready for reward distribution."
    }


@router.post("/{tournament_id}/distribute-rewards", response_model=RewardDistributionResponse)
def distribute_tournament_rewards(
    tournament_id: int,
    request: RewardDistributionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    DEPRECATED — use POST /{tournament_id}/distribute-rewards-v2

    Returns HTTP 410 Gone. The V2 endpoint runs the full EMA skill
    propagation pipeline (Phase 3) and issues idempotent credit/XP grants.
    """

    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=(
            "This endpoint is deprecated and no longer distributes rewards. "
            f"Use POST /api/v1/tournaments/{tournament_id}/distribute-rewards-v2 instead. "
            "The V2 endpoint includes EMA skill propagation (Phase 3)."
        ),
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

    # Get actual ranks from tournament_rankings table
    # Note: For INDIVIDUAL tournaments, there may be multiple rankings per user (one per round)
    # We take the BEST (minimum) rank for each user
    from app.models.tournament_ranking import TournamentRanking
    from sqlalchemy import func

    rankings = db.query(
        TournamentRanking.user_id,
        func.min(TournamentRanking.rank).label('best_rank')
    ).filter(
        TournamentRanking.tournament_id == tournament_id,
        TournamentRanking.user_id.in_(user_ids)
    ).group_by(TournamentRanking.user_id).all()

    rank_by_user = {r.user_id: r.best_rank for r in rankings}

    # Update reward_map with correct ranks from tournament_rankings
    for user_id in reward_map.keys():
        if user_id in rank_by_user:
            reward_map[user_id]["rank"] = rank_by_user[user_id]

    # 🎯 Get skill rewards for this tournament from skill_rewards table
    # Separation of concerns: SkillReward = auditable events (NOT FootballSkillAssessment = measurements)
    skill_by_user = {}
    try:
        # Query skill rewards for this specific tournament
        skill_rewards = db.query(SkillReward).filter(
            SkillReward.source_type == "TOURNAMENT",
            SkillReward.source_id == tournament_id,
            SkillReward.user_id.in_(user_ids)
        ).all()

        # Group skill rewards by user_id
        for skill_reward in skill_rewards:
            user_id = skill_reward.user_id
            if user_id not in skill_by_user:
                skill_by_user[user_id] = {}
            skill_by_user[user_id][skill_reward.skill_name] = skill_reward.points_awarded
    except Exception as e:
        # If skill rewards query fails, just use empty dict (skill points not available yet)
        print(f"Error loading skill rewards: {e}")
        pass

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
            "xp": data["xp"],
            "skill_points_awarded": skill_by_user.get(user_id, {})
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
