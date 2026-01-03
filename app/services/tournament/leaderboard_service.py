"""
Leaderboard Service

Business logic for tournament rankings and leaderboard calculations.
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional, Dict
from decimal import Decimal

from app.models import (
    TournamentRanking, 
    Semester, 
    User, 
    Team,
    Attendance,
    AttendanceStatus,
    Session as SessionModel,
    ParticipantType
)


def get_or_create_ranking(
    db: Session,
    tournament_id: int,
    user_id: Optional[int] = None,
    team_id: Optional[int] = None,
    participant_type: str = ParticipantType.INDIVIDUAL.value
) -> TournamentRanking:
    """Get existing ranking or create new one"""
    
    # Find existing ranking
    query = db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == tournament_id,
        TournamentRanking.participant_type == participant_type
    )
    
    if user_id:
        query = query.filter(TournamentRanking.user_id == user_id)
    if team_id:
        query = query.filter(TournamentRanking.team_id == team_id)
    
    ranking = query.first()
    
    if not ranking:
        ranking = TournamentRanking(
            tournament_id=tournament_id,
            user_id=user_id,
            team_id=team_id,
            participant_type=participant_type,
            points=Decimal('0'),
            wins=0,
            losses=0,
            draws=0,
            rank=None
        )
        db.add(ranking)
        db.flush()
    
    return ranking


def update_ranking_from_result(
    db: Session,
    tournament_id: int,
    user_id: Optional[int] = None,
    team_id: Optional[int] = None,
    points: Decimal = Decimal('0'),
    win: bool = False,
    loss: bool = False,
    draw: bool = False
) -> TournamentRanking:
    """Update ranking based on match result"""
    
    participant_type = ParticipantType.TEAM.value if team_id else ParticipantType.INDIVIDUAL.value
    
    ranking = get_or_create_ranking(
        db=db,
        tournament_id=tournament_id,
        user_id=user_id,
        team_id=team_id,
        participant_type=participant_type
    )
    
    # Update stats
    ranking.points += points
    if win:
        ranking.wins += 1
    if loss:
        ranking.losses += 1
    if draw:
        ranking.draws += 1
    
    db.commit()
    db.refresh(ranking)
    
    return ranking


def calculate_ranks(db: Session, tournament_id: int) -> List[TournamentRanking]:
    """Recalculate all ranks for a tournament"""
    
    # Get all rankings for this tournament, ordered by points (desc), then wins
    rankings = db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == tournament_id
    ).order_by(
        desc(TournamentRanking.points),
        desc(TournamentRanking.wins),
        TournamentRanking.losses  # fewer losses = better
    ).all()
    
    # Assign ranks
    for idx, ranking in enumerate(rankings, start=1):
        ranking.rank = idx
    
    db.commit()
    
    return rankings


def get_leaderboard(
    db: Session,
    tournament_id: int,
    participant_type: Optional[str] = None,
    limit: int = 100
) -> List[Dict]:
    """Get tournament leaderboard with full details"""
    
    query = db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == tournament_id
    )
    
    if participant_type:
        query = query.filter(TournamentRanking.participant_type == participant_type)
    
    rankings = query.order_by(
        TournamentRanking.rank.nullslast(),
        desc(TournamentRanking.points),
        desc(TournamentRanking.wins)
    ).limit(limit).all()
    
    # Enrich with user/team details
    result = []
    for ranking in rankings:
        entry = {
            'rank': ranking.rank,
            'points': float(ranking.points),
            'wins': ranking.wins,
            'losses': ranking.losses,
            'draws': ranking.draws,
            'participant_type': ranking.participant_type,
            'matches_played': ranking.wins + ranking.losses + ranking.draws
        }
        
        if ranking.user_id:
            user = db.query(User).filter(User.id == ranking.user_id).first()
            if user:
                entry['user_id'] = user.id
                entry['user_name'] = user.name
                entry['user_email'] = user.email
        
        if ranking.team_id:
            team = db.query(Team).filter(Team.id == ranking.team_id).first()
            if team:
                entry['team_id'] = team.id
                entry['team_name'] = team.name
                entry['team_code'] = team.code
        
        result.append(entry)
    
    return result


def calculate_league_points(
    db: Session,
    tournament_id: int,
    session_id: int
) -> None:
    """
    Calculate league points for a session.
    
    League scoring:
    - Win: 3 points
    - Draw: 1 point
    - Loss: 0 points
    - Present (participation): 1 point
    """
    
    # Get all attendance records for this session
    attendances = db.query(Attendance).join(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.semester_id == tournament_id,
        Attendance.status == AttendanceStatus.PRESENT
    ).all()
    
    # Award participation points
    for attendance in attendances:
        update_ranking_from_result(
            db=db,
            tournament_id=tournament_id,
            user_id=attendance.user_id,
            points=Decimal('1.0')  # Participation point
        )
    
    # Recalculate ranks after update
    calculate_ranks(db, tournament_id)


def get_user_rank(db: Session, tournament_id: int, user_id: int) -> Optional[int]:
    """Get a specific user's rank in a tournament"""
    ranking = db.query(TournamentRanking).filter(
        and_(
            TournamentRanking.tournament_id == tournament_id,
            TournamentRanking.user_id == user_id
        )
    ).first()
    
    return ranking.rank if ranking else None


def get_team_rank(db: Session, tournament_id: int, team_id: int) -> Optional[int]:
    """Get a specific team's rank in a tournament"""
    ranking = db.query(TournamentRanking).filter(
        and_(
            TournamentRanking.tournament_id == tournament_id,
            TournamentRanking.team_id == team_id
        )
    ).first()
    
    return ranking.rank if ranking else None


def reset_tournament_rankings(db: Session, tournament_id: int) -> bool:
    """Reset all rankings for a tournament (admin only)"""
    db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == tournament_id
    ).delete()
    db.commit()
    return True
