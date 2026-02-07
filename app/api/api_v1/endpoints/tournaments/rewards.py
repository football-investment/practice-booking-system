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

    # 🔒 IDEMPOTENCY CHECK: Prevent duplicate reward distribution
    existing_rewards = db.query(CreditTransaction).filter(
        CreditTransaction.semester_id == tournament_id,
        CreditTransaction.transaction_type == TransactionType.TOURNAMENT_REWARD.value
    ).count()

    if existing_rewards > 0:
        # ✅ FIX: If rewards exist but status is not REWARDS_DISTRIBUTED, fix the status
        if tournament.tournament_status != "REWARDS_DISTRIBUTED":
            from app.api.api_v1.endpoints.tournaments.lifecycle import record_status_change

            old_status = tournament.tournament_status
            tournament.tournament_status = "REWARDS_DISTRIBUTED"
            db.add(tournament)  # ✅ CRITICAL FIX: Explicitly add to session
            db.flush()  # ✅ Force immediate write to DB

            record_status_change(
                db=db,
                tournament_id=tournament.id,
                old_status=old_status,
                new_status="REWARDS_DISTRIBUTED",
                changed_by=current_user.id,
                reason="Auto-corrected status (rewards already distributed)",
                metadata={"existing_rewards_count": existing_rewards}
            )

            db.commit()

            # Return success response with corrected status
            return RewardDistributionResponse(
                tournament_id=tournament_id,
                tournament_name=tournament.name,
                rewards_distributed=existing_rewards,
                total_credits_awarded=0,  # Not recalculated for idempotent responses
                total_xp_awarded=0,
                status="REWARDS_DISTRIBUTED",
                message=f"✅ Status corrected to REWARDS_DISTRIBUTED. Rewards were already distributed ({existing_rewards} transactions exist).",
                rewards=[]
            )

        # Status is already correct - return error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rewards already distributed for this tournament ({existing_rewards} transactions exist). Tournament is locked. Use rollback endpoint to reset if needed."
        )

    # ========================================
    # ✅ CRITICAL FIX: DEDUPLICATE rankings by user_id
    # ========================================
    # INDIVIDUAL/ROUNDS_BASED tournaments have MULTIPLE ranking rows per player (one per round)
    # We MUST reward each player ONLY ONCE based on their BEST (lowest) rank
    # Core principle: 1 user → 1 reward event
    from sqlalchemy import func

    # Get BEST (lowest) rank for each unique player
    subquery = db.query(
        TournamentRanking.user_id,
        func.min(TournamentRanking.rank).label('best_rank')
    ).filter(
        TournamentRanking.tournament_id == tournament_id
    ).group_by(TournamentRanking.user_id).subquery()

    # Get ONE ranking row per player (their best performance)
    rankings = db.query(TournamentRanking).join(
        subquery,
        (TournamentRanking.user_id == subquery.c.user_id) &
        (TournamentRanking.rank == subquery.c.best_rank)
    ).filter(
        TournamentRanking.tournament_id == tournament_id
    ).order_by(TournamentRanking.rank).all()

    if not rankings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No rankings found. Submit rankings first before distributing rewards."
        )

    # ✅ DEFENSIVE ASSERTION: Ensure 1 reward per player (no duplicates)
    unique_users = set(r.user_id for r in rankings)
    if len(rankings) != len(unique_users):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SYSTEM ERROR: Duplicate rankings detected! {len(rankings)} rankings for {len(unique_users)} players. Expected 1:1 mapping."
        )

    # ✅ E2E TESTING: Save winner_count to tournament if provided
    if request.winner_count is not None:
        tournament.winner_count = request.winner_count
        db.add(tournament)
        # Will commit later with other changes

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
    # 🎯 TIED RANKS BUSINESS RULE:
    # - Each tied player receives FULL reward for their shared rank
    # - Next rank tier is skipped (e.g., two 2nd place → next is 4th, not 3rd)
    # - Example: 1st (500c), 2nd (300c), 2nd (300c), 4th (participant 50c)
    total_credits = 0
    total_xp = 0
    rewards_count = 0
    reward_details = []

    # ✅ CRITICAL FIX: Put ALL DB operations (rewards + status change) in SINGLE transaction
    try:
        # ========================================
        # STEP 1: Distribute rewards to all players
        # ========================================
        for ranking in rankings:
            # Determine reward tier (handles tied ranks)
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

                # ✅ Use CreditService for idempotent transaction creation
                credit_service = CreditService(db)
                idempotency_key = credit_service.generate_idempotency_key(
                    source_type="tournament",
                    source_id=tournament_id,
                    user_id=user.id,
                    operation="reward"
                )

                (credit_transaction, created) = credit_service.create_transaction(
                    user_id=user.id,
                    user_license_id=None,
                    transaction_type=TransactionType.TOURNAMENT_REWARD.value,
                    amount=credits_amount,
                    balance_after=user.credit_balance,
                    description=f"Tournament '{tournament.name}' - Rank #{ranking.rank} reward",
                    idempotency_key=idempotency_key,
                    semester_id=tournament_id
                )

            # Add XP to user account (always, even if 0 to track participation)
            if xp_amount > 0:
                user.xp_balance += xp_amount
                total_xp += xp_amount

                # ✅ Use XPTransactionService for idempotent transaction creation
                xp_service = XPTransactionService(db)
                (xp_transaction, created) = xp_service.award_xp(
                    user_id=user.id,
                    transaction_type="TOURNAMENT_REWARD",
                    amount=xp_amount,
                    balance_after=user.xp_balance,
                    description=f"Tournament '{tournament.name}' - Rank #{ranking.rank} reward",
                    semester_id=tournament_id
                )

            rewards_count += 1

            #  ========== SKILL POINT ASSESSMENT ==========
            # Award/deduct skill points based on rank performance
            # Positive rewards: Top 3 players (1st, 2nd, 3rd)
            # Neutral: Middle players (4th-6th) - no change
            # Negative penalty: Bottom players (7th+) - skill decrease
            skill_points_awarded = {}

            # Determine total players to calculate bottom ranks
            total_players = db.query(TournamentRanking).filter(
                TournamentRanking.tournament_id == tournament.id
            ).count()

            # Calculate which ranks get negative penalties (last 2 players)
            second_last_rank = total_players - 1 if total_players > 1 else None
            last_rank = total_players

            # Only process skill changes for top 3 (positive) or bottom 2 (negative)
            if ranking.rank <= 3 or ranking.rank >= second_last_rank:
                from app.models.license import UserLicense
                from app.models.football_skill_assessment import FootballSkillAssessment
                from app.models.game_configuration import GameConfiguration
                import random
                from datetime import datetime

                # Get user's LFA_FOOTBALL_PLAYER license
                user_license = db.query(UserLicense).filter(
                    UserLicense.user_id == user.id,
                    UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER"
                ).first()

                if user_license:
                    # Get tournament's game preset skills (NOT all skills!)
                    game_config = db.query(GameConfiguration).filter(
                        GameConfiguration.semester_id == tournament.id
                    ).first()

                    # Extract skills_tested and skill_weights from game_config JSONB field
                    preset_skills = []
                    skill_weights = {}
                    if game_config and game_config.game_config:
                        skill_config = game_config.game_config.get("skill_config", {})
                        preset_skills = skill_config.get("skills_tested", [])
                        skill_weights = skill_config.get("skill_weights", {})

                    # If no preset skills found, skip skill assessment
                    if not preset_skills:
                        skill_points_awarded = {}
                    else:
                        # Determine base points based on rank (positive or negative)
                        if ranking.rank == 1:
                            num_skills = min(5, len(preset_skills))
                            base_points_per_skill = [5, 4, 3, 3, 2][:num_skills]  # Top: +5, +4, +3, +3, +2
                        elif ranking.rank == 2:
                            num_skills = min(4, len(preset_skills))
                            base_points_per_skill = [4, 3, 2, 2][:num_skills]  # 2nd: +4, +3, +2, +2
                        elif ranking.rank == 3:
                            num_skills = min(3, len(preset_skills))
                            base_points_per_skill = [3, 2, 2][:num_skills]  # 3rd: +3, +2, +2
                        elif ranking.rank == second_last_rank:
                            # Second to last: NEGATIVE penalty
                            num_skills = min(2, len(preset_skills))
                            base_points_per_skill = [-2, -1][:num_skills]  # Penalty: -2, -1
                        elif ranking.rank == last_rank:
                            # Last place: MAXIMUM NEGATIVE penalty
                            num_skills = min(3, len(preset_skills))
                            base_points_per_skill = [-3, -2, -1][:num_skills]  # Max penalty: -3, -2, -1
                        else:
                            # Should not reach here due to outer if condition
                            num_skills = 0
                            base_points_per_skill = []

                        # Sort preset_skills by weight (highest first) to award more points to important skills
                        skills_by_weight = sorted(
                            preset_skills,
                            key=lambda s: skill_weights.get(s, 0),
                            reverse=True
                        )

                        # Select top N skills by weight (not random!)
                        selected_skills = skills_by_weight[:num_skills]

                        # Create skill assessments with weight multipliers
                        for i, skill_key in enumerate(selected_skills):
                            base_points = base_points_per_skill[i]

                            # Apply weight multiplier: (weight + 1.0)
                            weight = skill_weights.get(skill_key, 0.0)
                            multiplier = weight + 1.0
                            final_points = round(base_points * multiplier)

                            # ✅ Use FootballSkillService for idempotent skill reward creation
                            # FootballSkillAssessment = measurement/state
                            # SkillReward = auditable historical event
                            skill_service = FootballSkillService(db)
                            (skill_reward, created) = skill_service.award_skill_points(
                                user_id=user.id,
                                source_type="TOURNAMENT",
                                source_id=tournament.id,
                                skill_name=skill_key,
                                points_awarded=final_points
                            )
                            skill_points_awarded[skill_key] = final_points

            # Add to reward details list
            reward_details.append(PlayerRewardDetail(
                user_id=user.id,
                player_name=user.name or user.email,  # ✅ FIX: Fallback to email if name is None
                player_email=user.email,
                rank=ranking.rank,
                credits=credits_amount,
                xp=xp_amount
            ))

        # ========================================
        # STEP 2: Update tournament status to REWARDS_DISTRIBUTED
        # ========================================
        from app.api.api_v1.endpoints.tournaments.lifecycle import record_status_change

        old_status = tournament.tournament_status
        tournament.tournament_status = "REWARDS_DISTRIBUTED"
        db.add(tournament)  # ✅ CRITICAL FIX: Explicitly add to session
        db.flush()  # ✅ Force immediate write to DB before commit
        # ✅ FIX: reward_policy_snapshot column doesn't exist in semesters table
        # tournament.reward_policy_snapshot = reward_policy  # Save policy snapshot

        record_status_change(
            db=db,
            tournament_id=tournament.id,
            old_status=old_status,
            new_status="REWARDS_DISTRIBUTED",
            changed_by=current_user.id,
            reason=request.reason or "Rewards distributed",
            metadata={"total_credits_awarded": total_credits, "rewards_count": rewards_count}
        )

        # ========================================
        # STEP 3: Commit ENTIRE transaction (rewards + status change)
        # ========================================
        db.commit()

    except Exception as e:
        # ✅ CRITICAL: Rollback EVERYTHING on any error (rewards + status change)
        db.rollback()
        # Log detailed error with context
        import traceback
        error_details = traceback.format_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to distribute rewards: {str(e)}\n\nDetails:\n{error_details}"
        )

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
