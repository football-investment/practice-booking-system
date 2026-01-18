"""
Team Service

Business logic for team management (CRUD operations, member management).
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException, status
from typing import List, Optional

from app.models import Team, TeamMember, User, TeamMemberRole


def create_team(
    db: Session,
    name: str,
    captain_user_id: int,
    specialization_type: str,
    code: Optional[str] = None
) -> Team:
    """Create a new team"""
    # Check if captain exists
    captain = db.query(User).filter(User.id == captain_user_id).first()
    if not captain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Captain user not found"
        )

    # Generate code if not provided
    if not code:
        code = f"TEAM-{name.upper().replace(' ', '-')[:10]}"

    # Check if code already exists
    existing = db.query(Team).filter(Team.code == code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Team code '{code}' already exists"
        )

    # Create team
    team = Team(
        name=name,
        code=code,
        captain_user_id=captain_user_id,
        specialization_type=specialization_type,
        is_active=True
    )
    db.add(team)
    db.flush()

    # Add captain as team member
    captain_member = TeamMember(
        team_id=team.id,
        user_id=captain_user_id,
        role=TeamMemberRole.CAPTAIN.value,
        is_active=True
    )
    db.add(captain_member)
    db.commit()
    db.refresh(team)

    return team


def get_team(db: Session, team_id: int) -> Optional[Team]:
    """Get team by ID"""
    return db.query(Team).filter(Team.id == team_id).first()


def get_teams(
    db: Session,
    specialization_type: Optional[str] = None,
    is_active: bool = True,
    limit: int = 100
) -> List[Team]:
    """Get teams with optional filtering"""
    query = db.query(Team).filter(Team.is_active == is_active)

    if specialization_type:
        query = query.filter(Team.specialization_type == specialization_type)

    return query.limit(limit).all()


def add_team_member(
    db: Session,
    team_id: int,
    user_id: int,
    role: str = TeamMemberRole.PLAYER.value
) -> TeamMember:
    """Add a member to a team"""
    # Check team exists
    team = get_team(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    # Check user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if already a member
    existing = db.query(TeamMember).filter(
        and_(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
            TeamMember.is_active == True
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a team member"
        )

    # Add member
    member = TeamMember(
        team_id=team_id,
        user_id=user_id,
        role=role,
        is_active=True
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    return member


def remove_team_member(
    db: Session,
    team_id: int,
    user_id: int
) -> bool:
    """Remove a member from a team"""
    member = db.query(TeamMember).filter(
        and_(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
            TeamMember.is_active == True
        )
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found"
        )

    # Don't allow removing captain (must transfer captain first)
    if member.role == TeamMemberRole.CAPTAIN.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove team captain. Transfer captaincy first."
        )

    member.is_active = False
    db.commit()

    return True


def get_team_members(db: Session, team_id: int, is_active: bool = True) -> List[TeamMember]:
    """Get all members of a team"""
    return db.query(TeamMember).filter(
        and_(
            TeamMember.team_id == team_id,
            TeamMember.is_active == is_active
        )
    ).all()


def transfer_captaincy(
    db: Session,
    team_id: int,
    current_captain_id: int,
    new_captain_id: int
) -> Team:
    """Transfer team captaincy to another member"""
    team = get_team(db, team_id)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    # Verify current captain
    if team.captain_user_id != current_captain_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only current captain can transfer captaincy"
        )

    # Check new captain is a member
    new_captain_member = db.query(TeamMember).filter(
        and_(
            TeamMember.team_id == team_id,
            TeamMember.user_id == new_captain_id,
            TeamMember.is_active == True
        )
    ).first()

    if not new_captain_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New captain must be an active team member"
        )

    # Update roles
    old_captain_member = db.query(TeamMember).filter(
        and_(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_captain_id
        )
    ).first()

    if old_captain_member:
        old_captain_member.role = TeamMemberRole.PLAYER.value

    new_captain_member.role = TeamMemberRole.CAPTAIN.value
    team.captain_user_id = new_captain_id

    db.commit()
    db.refresh(team)

    return team


def delete_team(db: Session, team_id: int) -> bool:
    """Delete a team (soft delete)"""
    team = get_team(db, team_id)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    team.is_active = False
    db.commit()

    return True
