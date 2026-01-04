"""
Tournament XP Service

Business logic for tournament-specific XP and rewards distribution.
"""
from sqlalchemy.orm import Session
from typing import Dict, Optional
from decimal import Decimal

from app.models import (
    TournamentReward,
    TournamentRanking,
    User,
    Team,
    CreditTransaction,
    TransactionType,
    Semester
)
from app.services.gamification.xp_service import award_xp


def create_tournament_rewards(
    db: Session,
    tournament_id: int,
    rewards_config: Dict[str, Dict[str, int]]
) -> None:
    """
    Create reward configuration for a tournament.
    
    Example:
    {
        "1ST": {"xp": 500, "credits": 100},
        "2ND": {"xp": 300, "credits": 50},
        "3RD": {"xp": 200, "credits": 25},
        "PARTICIPANT": {"xp": 50, "credits": 0}
    }
    """
    for position, rewards in rewards_config.items():
        reward = TournamentReward(
            tournament_id=tournament_id,
            position=position,
            xp_amount=rewards.get('xp', 0),
            credits_reward=rewards.get('credits', 0)
        )
        db.add(reward)
    
    db.commit()


def get_tournament_rewards(db: Session, tournament_id: int) -> Dict[str, TournamentReward]:
    """Get all rewards for a tournament"""
    rewards = db.query(TournamentReward).filter(
        TournamentReward.tournament_id == tournament_id
    ).all()
    
    return {reward.position: reward for reward in rewards}


def distribute_rewards(
    db: Session,
    tournament_id: int
) -> Dict[str, int]:
    """
    Distribute rewards to all participants based on final rankings.

    Uses the reward policy snapshot stored in the semester at tournament creation time.
    Falls back to TournamentReward table for backward compatibility.

    Returns: Dict with stats about distribution
    """
    # Get tournament semester to access reward policy snapshot
    semester = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not semester:
        raise ValueError(f"Tournament semester {tournament_id} not found")

    # Try to use reward policy snapshot (new system)
    if semester.reward_policy_snapshot and semester.reward_policy_snapshot.get("placement_rewards"):
        placement_rewards_config = semester.reward_policy_snapshot["placement_rewards"]
    else:
        # Fallback to TournamentReward table (old system) for backward compatibility
        rewards_config = get_tournament_rewards(db, tournament_id)

        if not rewards_config:
            # Create default rewards if none exist
            default_rewards = {
                "1ST": {"xp": 500, "credits": 100},
                "2ND": {"xp": 300, "credits": 50},
                "3RD": {"xp": 200, "credits": 25},
                "PARTICIPANT": {"xp": 50, "credits": 0}
            }
            create_tournament_rewards(db, tournament_id, default_rewards)
            rewards_config = get_tournament_rewards(db, tournament_id)

        # Convert old format to new format
        placement_rewards_config = {
            pos: {"xp": reward.xp_amount, "credits": reward.credits_reward}
            for pos, reward in rewards_config.items()
        }

    # Get all rankings
    rankings = db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == tournament_id
    ).all()

    stats = {
        'total_participants': len(rankings),
        'xp_distributed': 0,
        'credits_distributed': 0
    }

    for ranking in rankings:
        # Determine position
        if ranking.rank == 1:
            position = "1ST"
        elif ranking.rank == 2:
            position = "2ND"
        elif ranking.rank == 3:
            position = "3RD"
        else:
            position = "PARTICIPANT"

        # Get rewards for this position from policy snapshot
        reward_config = placement_rewards_config.get(position)
        if not reward_config:
            continue

        xp_amount = reward_config.get("xp", 0)
        credits_amount = reward_config.get("credits", 0)

        # Award XP
        if xp_amount > 0 and ranking.user_id:
            award_xp(
                db=db,
                user_id=ranking.user_id,
                xp_amount=xp_amount,
                reason=f"Tournament {position} Place"
            )
            stats['xp_distributed'] += xp_amount

        # Award credits (user-level, not license-specific)
        if credits_amount > 0 and ranking.user_id:
            user = db.query(User).filter(User.id == ranking.user_id).first()
            if user:
                # Update user credit balance
                old_balance = user.credit_balance
                user.credit_balance = old_balance + credits_amount

                # Create credit transaction for audit trail
                transaction = CreditTransaction(
                    user_id=user.id,
                    amount=credits_amount,
                    balance_after=user.credit_balance,
                    transaction_type=TransactionType.TOURNAMENT_REWARD.value,
                    description=f"Tournament {position} Place Reward"
                )
                db.add(transaction)

                stats['credits_distributed'] += credits_amount

    db.commit()

    return stats


def calculate_tournament_xp(
    rank: int,
    base_xp: int = 100,
    participation_xp: int = 50
) -> int:
    """
    Calculate XP for a tournament participant based on rank.
    
    Formula:
    - 1st place: base_xp * 5
    - 2nd place: base_xp * 3
    - 3rd place: base_xp * 2
    - 4th-10th: base_xp * 1
    - 11th+: participation_xp
    """
    if rank == 1:
        return base_xp * 5
    elif rank == 2:
        return base_xp * 3
    elif rank == 3:
        return base_xp * 2
    elif rank <= 10:
        return base_xp
    else:
        return participation_xp


def award_manual_reward(
    db: Session,
    tournament_id: int,
    user_id: int,
    xp_amount: int,
    credits_amount: int,
    reason: str
) -> bool:
    """Manually award XP/credits to a tournament participant (admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    # Award XP
    if xp_amount > 0:
        award_xp(db=db, user=user, amount=xp_amount, reason=reason)
    
    # Award credits (user-level) - also handles negative amounts (penalties)
    if credits_amount != 0:
        # Update user credit balance
        old_balance = user.credit_balance
        user.credit_balance = old_balance + credits_amount

        # Create credit transaction for audit trail
        transaction = CreditTransaction(
            user_id=user.id,
            amount=credits_amount,
            balance_after=user.credit_balance,
            transaction_type=TransactionType.MANUAL_ADJUSTMENT.value,
            description=reason
        )
        db.add(transaction)
    
    db.commit()
    return True
