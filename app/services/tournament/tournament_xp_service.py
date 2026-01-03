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
    TransactionType
)
from app.services.gamification_service import award_xp


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
    
    Returns: Dict with stats about distribution
    """
    # Get reward config
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
        
        # Get rewards for this position
        reward = rewards_config.get(position)
        if not reward:
            continue
        
        # Award XP
        if reward.xp_amount > 0 and ranking.user_id:
            user = db.query(User).filter(User.id == ranking.user_id).first()
            if user:
                award_xp(
                    db=db,
                    user=user,
                    amount=reward.xp_amount,
                    reason=f"Tournament {position} Place"
                )
                stats['xp_distributed'] += reward.xp_amount
        
        # Award credits
        if reward.credits_reward > 0 and ranking.user_id:
            user = db.query(User).filter(User.id == ranking.user_id).first()
            if user:
                # Create credit transaction
                transaction = CreditTransaction(
                    user_id=user.id,
                    amount=reward.credits_reward,
                    transaction_type=TransactionType.TOURNAMENT_REWARD,
                    description=f"Tournament {position} Place Reward"
                )
                db.add(transaction)
                
                # Update user credits
                user.credits = (user.credits or 0) + reward.credits_reward
                stats['credits_distributed'] += reward.credits_reward
    
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
    
    # Award credits
    if credits_amount > 0:
        transaction = CreditTransaction(
            user_id=user.id,
            amount=credits_amount,
            transaction_type=TransactionType.MANUAL_ADJUSTMENT,
            description=reason
        )
        db.add(transaction)
        user.credits = (user.credits or 0) + credits_amount
    
    db.commit()
    return True
