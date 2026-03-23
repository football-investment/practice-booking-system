"""
Teams REST API

Endpoints for team management in team-based tournaments.
Student-facing: create teams, invite members, respond to invites.
Admin: user search for invite flow.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from ....database import get_db
from ....dependencies import get_current_user, get_current_active_user
from ....models.user import User, UserRole
from ....models.team import Team, TeamMember, TeamInvite, TeamInviteStatus
from ....services.tournament import team_service

router = APIRouter()


# ---------------------------------------------------------------------------
# User search — for the invite flow (any authenticated user can search)
# ---------------------------------------------------------------------------

@router.get("/users/invite-search")
def invite_search_users(
    q: str = Query(..., min_length=2, description="Name or email prefix"),
    team_id: Optional[int] = Query(None, description="Exclude existing members of this team"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Search active users by name/email for the invite form.
    Excludes the caller, existing active members of the given team, and users
    with a PENDING invite to that team.
    """
    query = db.query(User).filter(
        User.is_active == True,
        User.id != current_user.id,
        or_(
            User.name.ilike(f"%{q}%"),
            User.email.ilike(f"%{q}%"),
        ),
    )

    if team_id:
        # Exclude active members
        member_user_ids = db.query(TeamMember.user_id).filter(
            TeamMember.team_id == team_id,
            TeamMember.is_active == True,
        ).subquery()
        query = query.filter(User.id.notin_(member_user_ids))

        # Exclude users with pending invite
        pending_user_ids = db.query(TeamInvite.invited_user_id).filter(
            TeamInvite.team_id == team_id,
            TeamInvite.status == TeamInviteStatus.PENDING.value,
        ).subquery()
        query = query.filter(User.id.notin_(pending_user_ids))

    users = query.limit(limit).all()
    return [{"id": u.id, "name": u.name, "email": u.email} for u in users]


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------

@router.get("/teams/{team_id}")
def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get team details (members + pending invites). Captain or admin only."""
    team = team_service.get_team(db, team_id)
    if not team or not team.is_active:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    if current_user.role != UserRole.ADMIN and team.captain_user_id != current_user.id:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    members = team_service.get_team_members(db, team_id)
    pending_invites = team_service.get_team_pending_invites(db, team_id)

    return {
        "id": team.id,
        "name": team.name,
        "code": team.code,
        "captain_user_id": team.captain_user_id,
        "specialization_type": team.specialization_type,
        "members": [
            {"user_id": m.user_id, "role": m.role, "joined_at": m.joined_at}
            for m in members
        ],
        "pending_invites": [
            {
                "id": i.id,
                "invited_user_id": i.invited_user_id,
                "invited_by_id": i.invited_by_id,
                "created_at": i.created_at,
            }
            for i in pending_invites
        ],
    }


# ---------------------------------------------------------------------------
# Invites
# ---------------------------------------------------------------------------

@router.post("/teams/{team_id}/invites")
def create_invite(
    team_id: int,
    invited_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Captain invites a player. Caller must be the team captain."""
    invite = team_service.invite_member(
        db=db,
        team_id=team_id,
        invited_user_id=invited_user_id,
        invited_by_id=current_user.id,
    )
    return {
        "id": invite.id,
        "team_id": invite.team_id,
        "invited_user_id": invite.invited_user_id,
        "status": invite.status,
        "created_at": invite.created_at,
    }


@router.post("/teams/invites/{invite_id}/accept")
def accept_invite(
    invite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Accept a pending team invite."""
    invite = team_service.respond_to_invite(db, invite_id, current_user.id, accept=True)
    return {"id": invite.id, "status": invite.status}


@router.post("/teams/invites/{invite_id}/reject")
def reject_invite(
    invite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Reject a pending team invite."""
    invite = team_service.respond_to_invite(db, invite_id, current_user.id, accept=False)
    return {"id": invite.id, "status": invite.status}


@router.delete("/teams/{team_id}/invites/{invite_id}")
def cancel_invite(
    team_id: int,
    invite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Captain cancels a pending invite."""
    team_service.cancel_invite(db, invite_id, current_user.id)
    return {"cancelled": True}


@router.get("/teams/invites/my")
def my_invites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get all pending invites for the current user."""
    invites = team_service.get_pending_invites_for_user(db, current_user.id)
    return [
        {
            "id": i.id,
            "team_id": i.team_id,
            "team_name": i.team.name if i.team else None,
            "invited_by_id": i.invited_by_id,
            "created_at": i.created_at,
        }
        for i in invites
    ]
