"""
Public tournament/event detail page — no authentication required.
URL: GET /events/{tournament_id}
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.semester import Semester
from app.models.tournament_ranking import TournamentRanking
from app.models.user import User
from app.models.team import Team, TournamentTeamEnrollment
from app.models.club import Club
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

_STATUS_LABEL = {
    "DRAFT": "Draft",
    "ENROLLMENT_OPEN": "Enrollment Open",
    "ENROLLMENT_CLOSED": "Enrollment Closed",
    "CHECK_IN_OPEN": "Check-In Open",
    "IN_PROGRESS": "In Progress",
    "COMPLETED": "Completed",
    "REWARDS_DISTRIBUTED": "Rewards Distributed",
    "CANCELLED": "Cancelled",
}

_STATUS_COLOR = {
    "DRAFT": "#a0aec0",
    "ENROLLMENT_OPEN": "#48bb78",
    "ENROLLMENT_CLOSED": "#ed8936",
    "CHECK_IN_OPEN": "#667eea",
    "IN_PROGRESS": "#e53e3e",
    "COMPLETED": "#38a169",
    "REWARDS_DISTRIBUTED": "#d69e2e",
    "CANCELLED": "#718096",
}


@router.get("/events/{tournament_id}", response_class=HTMLResponse)
def public_event_detail(
    request: Request,
    tournament_id: int,
    db: Session = Depends(get_db),
):
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        return HTMLResponse("<h2>Event not found</h2>", status_code=404)

    # Every existing event has a public page — visibility is state-driven, not binary.
    # 404 is reserved for non-existent IDs only.
    status = tournament.tournament_status or "DRAFT"

    cfg = tournament.tournament_config_obj
    participant_type = cfg.participant_type if cfg else "INDIVIDUAL"
    tournament_format = tournament.format  # HEAD_TO_HEAD / INDIVIDUAL_RANKING
    max_players = cfg.max_players if cfg else None
    match_duration = cfg.match_duration_minutes if cfg else None
    number_of_legs = cfg.number_of_legs if cfg and hasattr(cfg, "number_of_legs") else 1

    # Location / Campus
    location_name = None
    campus_name = None
    try:
        if tournament.location_id:
            from app.models.location import Location
            loc = db.query(Location).filter(Location.id == tournament.location_id).first()
            location_name = loc.city if loc else None
        if tournament.campus_id:
            from app.models.campus import Campus
            camp = db.query(Campus).filter(Campus.id == tournament.campus_id).first()
            campus_name = camp.name if camp else None
    except Exception:
        pass

    # Tournament type display name
    type_name = ""
    try:
        if cfg and cfg.tournament_type:
            type_name = cfg.tournament_type.name
    except Exception:
        pass

    # ── Rankings ──────────────────────────────────────────────────────────────
    ranking_rows = db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == tournament_id
    ).order_by(TournamentRanking.rank.asc().nulls_last()).all()

    rankings = []
    if participant_type == "TEAM":
        for row in ranking_rows:
            team = db.query(Team).filter(Team.id == row.team_id).first() if row.team_id else None
            club = db.query(Club).filter(Club.id == team.club_id).first() if team and team.club_id else None
            rankings.append({
                "rank": row.rank,
                "name": team.name if team else f"Team #{row.team_id}",
                "club_name": club.name if club else None,
                "points": row.points,
                "wins": row.wins,
                "draws": row.draws,
                "losses": row.losses,
                "goals_for": row.goals_for,
                "goals_against": row.goals_against,
                "team_id": row.team_id,
                "user_id": None,
            })
    else:
        for row in ranking_rows:
            user = db.query(User).filter(User.id == row.user_id).first() if row.user_id else None
            rankings.append({
                "rank": row.rank,
                "name": user.name if user and user.name else (user.email if user else f"Player #{row.user_id}"),
                "club_name": None,
                "points": row.points,
                "wins": row.wins,
                "draws": row.draws,
                "losses": row.losses,
                "goals_for": row.goals_for,
                "goals_against": row.goals_against,
                "team_id": None,
                "user_id": row.user_id,
            })

    has_rankings = len(rankings) > 0

    # ── Enrolled participants (shown when no final rankings yet) ──────────────
    enrolled_count = 0
    participants = []  # [{name, club_name}] for pre-result display

    if participant_type == "TEAM":
        team_enrollments = db.query(TournamentTeamEnrollment).filter(
            TournamentTeamEnrollment.semester_id == tournament_id,
            TournamentTeamEnrollment.is_active == True,
        ).all()
        enrolled_count = len(team_enrollments)
        if not has_rankings:
            for te in team_enrollments:
                team = db.query(Team).filter(Team.id == te.team_id).first()
                club = db.query(Club).filter(Club.id == team.club_id).first() if team and team.club_id else None
                participants.append({
                    "name": team.name if team else f"Team #{te.team_id}",
                    "club_name": club.name if club else None,
                })
    else:
        enrolled_count = db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tournament_id,
            SemesterEnrollment.is_active == True,
            SemesterEnrollment.request_status == EnrollmentStatus.APPROVED,
        ).count()
        if not has_rankings:
            rows = db.query(SemesterEnrollment, User).join(
                User, SemesterEnrollment.user_id == User.id
            ).filter(
                SemesterEnrollment.semester_id == tournament_id,
                SemesterEnrollment.is_active == True,
                SemesterEnrollment.request_status == EnrollmentStatus.APPROVED,
            ).all()
            for enr, user in rows:
                participants.append({
                    "name": user.name if user.name else user.email,
                    "club_name": None,
                })

    return templates.TemplateResponse(request, "public/tournament_detail.html", {
        "t": tournament,
        "status": status,
        "status_label": _STATUS_LABEL.get(status, status),
        "status_color": _STATUS_COLOR.get(status, "#a0aec0"),
        "participant_type": participant_type,
        "tournament_format": tournament_format,
        "type_name": type_name,
        "max_players": max_players,
        "match_duration": match_duration,
        "number_of_legs": number_of_legs,
        "location_name": location_name,
        "campus_name": campus_name,
        "rankings": rankings,
        "has_rankings": has_rankings,
        "enrolled_count": enrolled_count,
        "participants": participants,
        "is_draft": status == "DRAFT",
        "is_cancelled": status == "CANCELLED",
    })
