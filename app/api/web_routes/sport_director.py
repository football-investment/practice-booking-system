"""
Sport Director web routes — location-scoped team enrollment management.

A Sport Director (linked to a location via SportDirectorAssignment) can:
  - Browse TEAM tournaments at their location
  - Enroll club teams into ENROLLMENT_OPEN tournaments
  - Remove team enrollments (ENROLLMENT_OPEN only)

Routes:
  GET  /sport-director/tournaments                                 → tournament list
  GET  /sport-director/tournaments/{tid}/teams                     → team enrollment management
  POST /sport-director/tournaments/{tid}/teams/{team_id}/enroll    → enroll team
  POST /sport-director/tournaments/{tid}/teams/{team_id}/remove    → remove team enrollment
"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ...database import get_db
from ...dependencies import get_current_sport_director_user_web
from ...models.campus import Campus
from ...models.instructor_assignment import SportDirectorAssignment
from ...models.semester import Semester
from ...models.team import Team, TeamMember, TournamentTeamEnrollment
from ...models.tournament_configuration import TournamentConfiguration
from ...models.user import User

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(prefix="/sport-director")


# ── Auth helpers ────────────────────────────────────────────────────────────────

def _get_sd_location_ids(db: Session, user: User) -> set[int]:
    """Return set of location IDs where the user has an active SportDirectorAssignment."""
    assignments = db.query(SportDirectorAssignment).filter(
        SportDirectorAssignment.user_id == user.id,
        SportDirectorAssignment.is_active == True,
    ).all()
    return {a.location_id for a in assignments}


def _get_tournament_location_id(db: Session, tournament: Semester) -> int | None:
    """Derive location_id for a tournament: campus.location_id if campus set, else tournament.location_id."""
    if tournament.campus_id:
        campus = db.query(Campus).filter(Campus.id == tournament.campus_id).first()
        if campus:
            return campus.location_id
    return getattr(tournament, "location_id", None)


def _check_sd_owns_tournament(db: Session, user: User, tournament: Semester) -> None:
    """Raise 403 if this SD does not manage the tournament's location."""
    sd_locations = _get_sd_location_ids(db, user)
    # Admin bypass
    if user.role.value == "admin":
        return
    tournament_location = _get_tournament_location_id(db, tournament)
    if tournament_location not in sd_locations:
        raise HTTPException(
            status_code=403,
            detail="Not authorized: tournament is not at your assigned location",
        )


# ── Routes ───────────────────────────────────────────────────────────────────────

@router.get("/tournaments", response_class=HTMLResponse)
async def sd_tournament_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_sport_director_user_web),
):
    """List TEAM tournaments scoped to the SD's location(s)."""
    sd_location_ids = _get_sd_location_ids(db, user)

    # Build candidate tournament list
    rows = (
        db.query(Semester, TournamentConfiguration)
        .join(TournamentConfiguration, TournamentConfiguration.semester_id == Semester.id)
        .filter(
            Semester.tournament_status.in_(["ENROLLMENT_OPEN", "ENROLLMENT_CLOSED", "IN_PROGRESS"]),
            TournamentConfiguration.participant_type == "TEAM",
        )
        .order_by(Semester.start_date.desc())
        .all()
    )

    # Filter by SD's locations
    filtered = []
    for t, cfg in rows:
        t_loc = _get_tournament_location_id(db, t)
        if t_loc in sd_location_ids:
            enrolled_count = db.query(TournamentTeamEnrollment).filter(
                TournamentTeamEnrollment.semester_id == t.id,
                TournamentTeamEnrollment.is_active == True,
            ).count()
            filtered.append({
                "tournament": t,
                "cfg": cfg,
                "enrolled_count": enrolled_count,
            })

    return templates.TemplateResponse(
        "sport_director/tournaments.html",
        {
            "request": request,
            "user": user,
            "rows": filtered,
        },
    )


@router.get("/tournaments/{tournament_id}/teams", response_class=HTMLResponse)
async def sd_tournament_teams(
    tournament_id: int,
    request: Request,
    msg: str = None,
    error: str = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_sport_director_user_web),
):
    """Show enrolled teams + eligible club teams for enrollment."""
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    _check_sd_owns_tournament(db, user, tournament)

    # Currently enrolled teams
    enrolled_rows = (
        db.query(TournamentTeamEnrollment, Team)
        .join(Team, Team.id == TournamentTeamEnrollment.team_id)
        .filter(
            TournamentTeamEnrollment.semester_id == tournament_id,
            TournamentTeamEnrollment.is_active == True,
        )
        .all()
    )

    enrolled_team_ids = {e.team_id for e, _ in enrolled_rows}

    # Eligible club teams — teams linked to SD's clubs via club.location
    # Broad query: all active teams not yet enrolled (SD can manage any team at their location)
    eligible_teams = (
        db.query(Team)
        .filter(
            Team.is_active == True,
            Team.id.notin_(enrolled_team_ids),
        )
        .order_by(Team.name)
        .all()
    )

    return templates.TemplateResponse(
        "sport_director/tournament_teams.html",
        {
            "request": request,
            "user": user,
            "tournament": tournament,
            "enrolled_rows": enrolled_rows,
            "eligible_teams": eligible_teams,
            "msg": msg,
            "error": error,
        },
    )


@router.post("/tournaments/{tournament_id}/teams/{team_id}/enroll")
async def sd_enroll_team(
    tournament_id: int,
    team_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_sport_director_user_web),
):
    """Enroll a club team in the tournament (SD/admin bypass — no credit cost)."""
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        return RedirectResponse(f"/sport-director/tournaments", status_code=303)

    try:
        _check_sd_owns_tournament(db, user, tournament)
    except HTTPException as exc:
        return RedirectResponse(
            f"/sport-director/tournaments/{tournament_id}/teams?error={exc.detail}",
            status_code=303,
        )

    # Must be ENROLLMENT_OPEN
    if tournament.tournament_status != "ENROLLMENT_OPEN":
        return RedirectResponse(
            f"/sport-director/tournaments/{tournament_id}/teams"
            f"?error=Tournament+enrollment+is+not+open+%28status%3A+{tournament.tournament_status}%29",
            status_code=303,
        )

    # Must be TEAM tournament
    cfg = db.query(TournamentConfiguration).filter(
        TournamentConfiguration.semester_id == tournament_id
    ).first()
    if not cfg or cfg.participant_type != "TEAM":
        return RedirectResponse(
            f"/sport-director/tournaments/{tournament_id}/teams"
            f"?error=This+tournament+does+not+support+team+enrollment",
            status_code=303,
        )

    # Check team exists
    team = db.query(Team).filter(Team.id == team_id, Team.is_active == True).first()
    if not team:
        return RedirectResponse(
            f"/sport-director/tournaments/{tournament_id}/teams?error=Team+not+found",
            status_code=303,
        )

    # Check duplicate
    existing = db.query(TournamentTeamEnrollment).filter(
        TournamentTeamEnrollment.semester_id == tournament_id,
        TournamentTeamEnrollment.team_id == team_id,
        TournamentTeamEnrollment.is_active == True,
    ).first()
    if existing:
        return RedirectResponse(
            f"/sport-director/tournaments/{tournament_id}/teams"
            f"?error=Team+already+enrolled",
            status_code=303,
        )

    enrollment = TournamentTeamEnrollment(
        semester_id=tournament_id,
        team_id=team_id,
        is_active=True,
        payment_verified=True,  # SD/admin bypass — no credit deduction
    )
    db.add(enrollment)
    db.commit()

    return RedirectResponse(
        f"/sport-director/tournaments/{tournament_id}/teams?msg=Team+enrolled+successfully",
        status_code=303,
    )


@router.post("/tournaments/{tournament_id}/teams/{team_id}/remove")
async def sd_remove_team(
    tournament_id: int,
    team_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_sport_director_user_web),
):
    """Remove a team's enrollment (only allowed when tournament is ENROLLMENT_OPEN)."""
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        return RedirectResponse(f"/sport-director/tournaments", status_code=303)

    try:
        _check_sd_owns_tournament(db, user, tournament)
    except HTTPException as exc:
        return RedirectResponse(
            f"/sport-director/tournaments/{tournament_id}/teams?error={exc.detail}",
            status_code=303,
        )

    if tournament.tournament_status != "ENROLLMENT_OPEN":
        return RedirectResponse(
            f"/sport-director/tournaments/{tournament_id}/teams"
            f"?error=Can+only+remove+teams+when+enrollment+is+open",
            status_code=303,
        )

    enrollment = db.query(TournamentTeamEnrollment).filter(
        TournamentTeamEnrollment.semester_id == tournament_id,
        TournamentTeamEnrollment.team_id == team_id,
        TournamentTeamEnrollment.is_active == True,
    ).first()
    if not enrollment:
        return RedirectResponse(
            f"/sport-director/tournaments/{tournament_id}/teams?error=Team+not+enrolled",
            status_code=303,
        )

    enrollment.is_active = False
    db.commit()

    return RedirectResponse(
        f"/sport-director/tournaments/{tournament_id}/teams?msg=Team+removed+from+tournament",
        status_code=303,
    )
