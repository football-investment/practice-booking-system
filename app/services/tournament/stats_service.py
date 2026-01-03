"""
Tournament Stats Service

Business logic for tournament statistics and analytics.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Dict, Optional
from decimal import Decimal

from app.models import (
    TournamentStats,
    TournamentRanking,
    Semester,
    Session as SessionModel,
    Attendance,
    AttendanceStatus,
    SemesterEnrollment,
    TournamentTeamEnrollment
)


def get_or_create_stats(db: Session, tournament_id: int) -> TournamentStats:
    """Get existing stats or create new ones"""
    stats = db.query(TournamentStats).filter(
        TournamentStats.tournament_id == tournament_id
    ).first()
    
    if not stats:
        stats = TournamentStats(
            tournament_id=tournament_id,
            total_participants=0,
            total_teams=0,
            total_matches=0,
            completed_matches=0,
            total_revenue=0,
            avg_attendance_rate=Decimal('0')
        )
        db.add(stats)
        db.commit()
        db.refresh(stats)
    
    return stats


def update_tournament_stats(db: Session, tournament_id: int) -> TournamentStats:
    """Recalculate all statistics for a tournament"""
    
    stats = get_or_create_stats(db, tournament_id)
    
    # Get tournament
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        return stats
    
    # Count individual participants
    individual_count = db.query(SemesterEnrollment).filter(
        and_(
            SemesterEnrollment.semester_id == tournament_id,
            SemesterEnrollment.is_active == True
        )
    ).count()
    
    # Count team participants
    team_count = db.query(TournamentTeamEnrollment).filter(
        and_(
            TournamentTeamEnrollment.semester_id == tournament_id,
            TournamentTeamEnrollment.is_active == True
        )
    ).count()
    
    # Count total matches (sessions)
    total_matches = db.query(SessionModel).filter(
        and_(
            SessionModel.semester_id == tournament_id,
            SessionModel.is_tournament_game == True
        )
    ).count()
    
    # Count completed matches (sessions with results)
    completed_matches = db.query(SessionModel).filter(
        and_(
            SessionModel.semester_id == tournament_id,
            SessionModel.is_tournament_game == True,
            SessionModel.game_results.isnot(None)
        )
    ).count()
    
    # Calculate attendance rate
    total_attendance_records = db.query(Attendance).join(SessionModel).filter(
        SessionModel.semester_id == tournament_id
    ).count()
    
    present_count = db.query(Attendance).join(SessionModel).filter(
        and_(
            SessionModel.semester_id == tournament_id,
            Attendance.status == AttendanceStatus.PRESENT
        )
    ).count()
    
    avg_attendance = Decimal('0')
    if total_attendance_records > 0:
        avg_attendance = Decimal(present_count) / Decimal(total_attendance_records) * 100
    
    # Calculate total revenue (credits collected)
    total_revenue = (individual_count * (tournament.enrollment_cost or 0)) + \
                   (team_count * (tournament.enrollment_cost or 0))
    
    # Update stats
    stats.total_participants = individual_count
    stats.total_teams = team_count
    stats.total_matches = total_matches
    stats.completed_matches = completed_matches
    stats.total_revenue = total_revenue
    stats.avg_attendance_rate = avg_attendance.quantize(Decimal('0.01'))
    
    db.commit()
    db.refresh(stats)
    
    return stats


def get_tournament_analytics(db: Session, tournament_id: int) -> Dict:
    """Get comprehensive analytics for a tournament"""
    
    # Update stats first
    stats = update_tournament_stats(db, tournament_id)
    
    # Get top performers
    top_rankings = db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == tournament_id
    ).order_by(
        TournamentRanking.rank.nullslast()
    ).limit(10).all()
    
    # Calculate completion rate
    completion_rate = Decimal('0')
    if stats.total_matches > 0:
        completion_rate = (Decimal(stats.completed_matches) / Decimal(stats.total_matches)) * 100
    
    return {
        'tournament_id': tournament_id,
        'stats': {
            'total_participants': stats.total_participants,
            'total_teams': stats.total_teams,
            'total_matches': stats.total_matches,
            'completed_matches': stats.completed_matches,
            'completion_rate': float(completion_rate.quantize(Decimal('0.01'))),
            'total_revenue': stats.total_revenue,
            'avg_attendance_rate': float(stats.avg_attendance_rate)
        },
        'top_10_rankings': [
            {
                'rank': r.rank,
                'user_id': r.user_id,
                'team_id': r.team_id,
                'points': float(r.points),
                'wins': r.wins,
                'losses': r.losses,
                'draws': r.draws
            }
            for r in top_rankings
        ]
    }


def get_participant_stats(
    db: Session,
    tournament_id: int,
    user_id: Optional[int] = None,
    team_id: Optional[int] = None
) -> Optional[Dict]:
    """Get detailed stats for a specific participant"""
    
    # Get ranking
    query = db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == tournament_id
    )
    
    if user_id:
        query = query.filter(TournamentRanking.user_id == user_id)
    elif team_id:
        query = query.filter(TournamentRanking.team_id == team_id)
    else:
        return None
    
    ranking = query.first()
    if not ranking:
        return None
    
    # Calculate stats
    matches_played = ranking.wins + ranking.losses + ranking.draws
    win_rate = Decimal('0')
    if matches_played > 0:
        win_rate = (Decimal(ranking.wins) / Decimal(matches_played)) * 100
    
    return {
        'rank': ranking.rank,
        'points': float(ranking.points),
        'matches_played': matches_played,
        'wins': ranking.wins,
        'losses': ranking.losses,
        'draws': ranking.draws,
        'win_rate': float(win_rate.quantize(Decimal('0.01')))
    }
