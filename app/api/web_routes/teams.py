"""
Team web routes — student-facing HTML flow

Route order matters: static paths (/teams/invites) must come before
path-parameterized routes (/teams/{team_id}).

Student:
    GET  /tournaments/{id}/team/create   — show create-team form
    POST /tournaments/{id}/team/create   — create team (credit deduction)
    GET  /teams/invites                  — incoming invites for current user
    POST /teams/invites/{inv_id}/accept  — accept invite
    POST /teams/invites/{inv_id}/reject  — reject invite
    GET  /teams/{id}                     — captain dashboard (members + invites)
    POST /teams/{id}/invite              — invite a player
    POST /teams/{id}/invites/{inv_id}/cancel  — captain cancels invite
"""
from pathlib import Path

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ...database import get_db
from ...dependencies import get_current_user_web
from ...models.semester import Semester
from ...models.tournament_configuration import TournamentConfiguration
from ...models.user import User, UserRole
from ...services.tournament import team_service

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()


def _require_student(user: User) -> None:
    if user.role not in (UserRole.STUDENT, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Students only")


# ---------------------------------------------------------------------------
# Create team
# ---------------------------------------------------------------------------

@router.get("/tournaments/{tournament_id}/team/create", response_class=HTMLResponse)
async def team_create_form(
    tournament_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    _require_student(user)
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    cfg = db.query(TournamentConfiguration).filter(
        TournamentConfiguration.semester_id == tournament_id
    ).first()
    cost = cfg.team_enrollment_cost if cfg else 0

    return templates.TemplateResponse(
        "student/team_create.html",
        {
            "request": request,
            "user": user,
            "tournament": tournament,
            "cost": cost,
        },
    )


@router.post("/tournaments/{tournament_id}/team/create")
async def team_create_submit(
    tournament_id: int,
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    _require_student(user)

    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    cfg = db.query(TournamentConfiguration).filter(
        TournamentConfiguration.semester_id == tournament_id
    ).first()
    if not cfg or cfg.participant_type != "TEAM":
        raise HTTPException(status_code=400, detail="This tournament does not support team enrollment")

    try:
        team = team_service.create_team_with_cost(
            db=db,
            name=name,
            captain_user_id=user.id,
            specialization_type=cfg.tournament_type.format if cfg.tournament_type else "TEAM",
            tournament_id=tournament_id,
        )
    except HTTPException as exc:
        cost = cfg.team_enrollment_cost if cfg else 0
        return templates.TemplateResponse(
            "student/team_create.html",
            {
                "request": request,
                "user": user,
                "tournament": tournament,
                "cost": cost,
                "error": exc.detail,
            },
            status_code=exc.status_code,
        )

    return RedirectResponse(f"/teams/{team.id}?msg=Team+created", status_code=303)


# ---------------------------------------------------------------------------
# Incoming invites (student view) — MUST be before /teams/{team_id}
# ---------------------------------------------------------------------------

@router.get("/teams/invites", response_class=HTMLResponse)
async def my_invites(
    request: Request,
    msg: str = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    invites = team_service.get_pending_invites_for_user(db, user.id)
    return templates.TemplateResponse(
        "student/team_invites.html",
        {
            "request": request,
            "user": user,
            "invites": invites,
            "msg": msg,
        },
    )


@router.post("/teams/invites/{invite_id}/accept")
async def accept_invite(
    invite_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    try:
        team_service.respond_to_invite(db, invite_id, user.id, accept=True)
    except HTTPException as exc:
        return RedirectResponse(f"/teams/invites?error={exc.detail}", status_code=303)

    return RedirectResponse("/teams/invites?msg=You+joined+the+team", status_code=303)


@router.post("/teams/invites/{invite_id}/reject")
async def reject_invite(
    invite_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    try:
        team_service.respond_to_invite(db, invite_id, user.id, accept=False)
    except HTTPException as exc:
        return RedirectResponse(f"/teams/invites?error={exc.detail}", status_code=303)

    return RedirectResponse("/teams/invites?msg=Invite+declined", status_code=303)


# ---------------------------------------------------------------------------
# Team dashboard (captain view) — AFTER static /teams/invites route
# ---------------------------------------------------------------------------

@router.get("/teams/{team_id}", response_class=HTMLResponse)
async def team_dashboard(
    team_id: int,
    request: Request,
    msg: str = None,
    error: str = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    team = team_service.get_team(db, team_id)
    if not team or not team.is_active:
        raise HTTPException(status_code=404, detail="Team not found")

    is_captain = team.captain_user_id == user.id
    is_admin = user.role == UserRole.ADMIN

    if not is_captain and not is_admin:
        raise HTTPException(status_code=403, detail="Captain or admin access required")

    members = team_service.get_team_members(db, team_id)
    pending_invites = team_service.get_team_pending_invites(db, team_id)

    return templates.TemplateResponse(
        "student/team_dashboard.html",
        {
            "request": request,
            "user": user,
            "team": team,
            "members": members,
            "pending_invites": pending_invites,
            "msg": msg,
            "error": error,
        },
    )


# ---------------------------------------------------------------------------
# Invite
# ---------------------------------------------------------------------------

@router.post("/teams/{team_id}/invite")
async def team_invite(
    team_id: int,
    request: Request,
    invited_user_id: int = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    try:
        team_service.invite_member(
            db=db,
            team_id=team_id,
            invited_user_id=invited_user_id,
            invited_by_id=user.id,
        )
    except HTTPException as exc:
        return RedirectResponse(f"/teams/{team_id}?error={exc.detail}", status_code=303)

    return RedirectResponse(f"/teams/{team_id}?msg=Invited", status_code=303)


@router.post("/teams/{team_id}/invites/{invite_id}/cancel")
async def team_cancel_invite(
    team_id: int,
    invite_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    try:
        team_service.cancel_invite(db, invite_id, user.id)
    except HTTPException as exc:
        return RedirectResponse(f"/teams/{team_id}?error={exc.detail}", status_code=303)

    return RedirectResponse(f"/teams/{team_id}?msg=Invite+cancelled", status_code=303)
