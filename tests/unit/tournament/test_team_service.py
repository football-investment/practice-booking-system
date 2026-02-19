"""
Comprehensive unit tests for team_service.py

Tests all 8 functions with happy path, edge cases, error handling, and validation.
"""
import pytest
import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime

from app.services.tournament import team_service
from app.models import Team, TeamMember, User, TeamMemberRole
from app.models.user import UserRole


def create_test_user(db: Session, email: str, name: str, role: UserRole = UserRole.STUDENT) -> User:
    """Helper function to create a test user with unique email"""
    # Add UUID suffix to prevent duplicate key violations
    unique_email = f"{email.split('@')[0]}+{uuid.uuid4().hex[:8]}@{email.split('@')[1]}"
    user = User(
        email=unique_email,
        name=name,
        password_hash="test_hash_123",
        role=role  # Pass enum directly, SQLAlchemy handles conversion
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestCreateTeam:
    """Test create_team() function"""

    def test_create_team_success(self, test_db: Session):
        """Happy path: Create team with valid captain"""
        # Create a user to be captain
        captain = create_test_user(test_db, email="captain@test.com", name="Captain Test")

        # Create team
        team = team_service.create_team(
            db=test_db,
            name="Test Team",
            captain_user_id=captain.id,
            specialization_type="LFA_PLAYER"
        )

        assert team.name == "Test Team"
        assert team.captain_user_id == captain.id
        assert team.specialization_type == "LFA_PLAYER"
        assert team.is_active is True
        assert team.code.startswith("TEAM-")

        # Verify captain is added as team member
        members = test_db.query(TeamMember).filter(TeamMember.team_id == team.id).all()
        assert len(members) == 1
        assert members[0].user_id == captain.id
        assert members[0].role == TeamMemberRole.CAPTAIN.value

    def test_create_team_with_custom_code(self, test_db: Session):
        """Create team with custom code"""
        captain = create_test_user(test_db, email="captain2@test.com", name="Captain 2")

        team = team_service.create_team(
            db=test_db,
            name="Custom Team",
            captain_user_id=captain.id,
            specialization_type="LFA_PLAYER",
            code="CUSTOM-123"
        )

        assert team.code == "CUSTOM-123"

    def test_create_team_auto_generates_code(self, test_db: Session):
        """Auto-generated code is formatted correctly"""
        captain = create_test_user(test_db, email="captain3@test.com", name="Captain 3")

        team = team_service.create_team(
            db=test_db,
            name="Super Long Team Name That Exceeds Limit",
            captain_user_id=captain.id,
            specialization_type="LFA_PLAYER"
        )

        # Code should be truncated to 10 chars after "TEAM-"
        assert team.code == "TEAM-SUPER-LONG"
        # Verify truncation happened (original would be much longer)
        assert len(team.code.split("TEAM-")[1]) == 10

    def test_create_team_captain_not_found(self, test_db: Session):
        """Error: Captain user does not exist"""
        with pytest.raises(HTTPException) as exc_info:
            team_service.create_team(
                db=test_db,
                name="Team Without Captain",
                captain_user_id=99999,  # Non-existent user
                specialization_type="LFA_PLAYER"
            )

        assert exc_info.value.status_code == 404
        assert "Captain user not found" in exc_info.value.detail

    def test_create_team_duplicate_code(self, test_db: Session):
        """Error: Team code already exists"""
        captain = create_test_user(test_db, email="captain4@test.com", name="Captain 4")

        # Create first team with code
        team_service.create_team(
            db=test_db,
            name="Team 1",
            captain_user_id=captain.id,
            specialization_type="LFA_PLAYER",
            code="DUPLICATE"
        )

        # Try to create second team with same code
        with pytest.raises(HTTPException) as exc_info:
            team_service.create_team(
                db=test_db,
                name="Team 2",
                captain_user_id=captain.id,
                specialization_type="LFA_PLAYER",
                code="DUPLICATE"
            )

        assert exc_info.value.status_code == 409
        assert "already exists" in exc_info.value.detail


class TestGetTeam:
    """Test get_team() function"""

    def test_get_team_success(self, test_db: Session):
        """Happy path: Get existing team"""
        captain = create_test_user(test_db, email="captain5@test.com", name="Captain 5")

        team = team_service.create_team(
            db=test_db,
            name="Get Test Team",
            captain_user_id=captain.id,
            specialization_type="LFA_PLAYER"
        )

        retrieved = team_service.get_team(test_db, team.id)

        assert retrieved is not None
        assert retrieved.id == team.id
        assert retrieved.name == "Get Test Team"

    def test_get_team_not_found(self, test_db: Session):
        """Edge case: Team does not exist"""
        retrieved = team_service.get_team(test_db, 99999)
        assert retrieved is None


class TestGetTeams:
    """Test get_teams() function"""

    def test_get_teams_all_active(self, test_db: Session):
        """Get all active teams"""
        captain = create_test_user(test_db, email="captain6@test.com", name="Captain 6")

        # Create 3 teams
        team1 = team_service.create_team(test_db, "Team A", captain.id, "LFA_PLAYER")
        team2 = team_service.create_team(test_db, "Team B", captain.id, "LFA_PLAYER")
        team3 = team_service.create_team(test_db, "Team C", captain.id, "LFA_COACH")

        teams = team_service.get_teams(test_db)

        assert len(teams) >= 3
        team_ids = [t.id for t in teams]
        assert team1.id in team_ids
        assert team2.id in team_ids
        assert team3.id in team_ids

    def test_get_teams_filter_by_specialization(self, test_db: Session):
        """Filter teams by specialization type"""
        captain = create_test_user(test_db, email="captain7@test.com", name="Captain 7")

        team1 = team_service.create_team(test_db, "Player Team", captain.id, "LFA_PLAYER")
        team2 = team_service.create_team(test_db, "Coach Team", captain.id, "LFA_COACH")

        player_teams = team_service.get_teams(test_db, specialization_type="LFA_PLAYER")

        # Verify only LFA_PLAYER teams are returned
        for team in player_teams:
            assert team.specialization_type == "LFA_PLAYER"

    def test_get_teams_include_inactive(self, test_db: Session):
        """Get inactive teams when specified"""
        captain = create_test_user(test_db, email="captain8@test.com", name="Captain 8")

        team = team_service.create_team(test_db, "Inactive Team", captain.id, "LFA_PLAYER")

        # Deactivate team
        team_service.delete_team(test_db, team.id)

        # Get inactive teams
        inactive_teams = team_service.get_teams(test_db, is_active=False)

        team_ids = [t.id for t in inactive_teams]
        assert team.id in team_ids

    def test_get_teams_limit(self, test_db: Session):
        """Respect limit parameter"""
        captain = create_test_user(test_db, email="captain9@test.com", name="Captain 9")

        # Create 5 teams
        for i in range(5):
            team_service.create_team(test_db, f"Team {i}", captain.id, "LFA_PLAYER")

        teams = team_service.get_teams(test_db, limit=2)

        assert len(teams) <= 2


class TestAddTeamMember:
    """Test add_team_member() function"""

    def test_add_team_member_success(self, test_db: Session):
        """Happy path: Add member to team"""
        captain = create_test_user(test_db, email="cap10@test.com", name="Captain 10")
        player = create_test_user(test_db, email="player1@test.com", name="Player 1")

        team = team_service.create_team(test_db, "Team With Members", captain.id, "LFA_PLAYER")

        member = team_service.add_team_member(test_db, team.id, player.id)

        assert member.team_id == team.id
        assert member.user_id == player.id
        assert member.role == TeamMemberRole.PLAYER.value
        assert member.is_active is True

    def test_add_team_member_team_not_found(self, test_db: Session):
        """Error: Team does not exist"""
        player = create_test_user(test_db, email="player2@test.com", name="Player 2")

        with pytest.raises(HTTPException) as exc_info:
            team_service.add_team_member(test_db, 99999, player.id)

        assert exc_info.value.status_code == 404
        assert "Team not found" in exc_info.value.detail

    def test_add_team_member_user_not_found(self, test_db: Session):
        """Error: User does not exist"""
        captain = create_test_user(test_db, email="cap11@test.com", name="Captain 11")

        team = team_service.create_team(test_db, "Team", captain.id, "LFA_PLAYER")

        with pytest.raises(HTTPException) as exc_info:
            team_service.add_team_member(test_db, team.id, 99999)

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail

    def test_add_team_member_already_member(self, test_db: Session):
        """Error: User is already a team member"""
        captain = create_test_user(test_db, email="cap12@test.com", name="Captain 12")
        player = create_test_user(test_db, email="player3@test.com", name="Player 3")

        team = team_service.create_team(test_db, "Team", captain.id, "LFA_PLAYER")
        team_service.add_team_member(test_db, team.id, player.id)

        # Try to add again
        with pytest.raises(HTTPException) as exc_info:
            team_service.add_team_member(test_db, team.id, player.id)

        assert exc_info.value.status_code == 409
        assert "already a team member" in exc_info.value.detail


class TestRemoveTeamMember:
    """Test remove_team_member() function"""

    def test_remove_team_member_success(self, test_db: Session):
        """Happy path: Remove member from team"""
        captain = create_test_user(test_db, email="cap13@test.com", name="Captain 13")
        player = create_test_user(test_db, email="player4@test.com", name="Player 4")

        team = team_service.create_team(test_db, "Team", captain.id, "LFA_PLAYER")
        team_service.add_team_member(test_db, team.id, player.id)

        result = team_service.remove_team_member(test_db, team.id, player.id)

        assert result is True

        # Verify member is marked inactive
        members = team_service.get_team_members(test_db, team.id)
        member_ids = [m.user_id for m in members]
        assert player.id not in member_ids

    def test_remove_team_member_not_found(self, test_db: Session):
        """Error: Member not found in team"""
        captain = create_test_user(test_db, email="cap14@test.com", name="Captain 14")

        team = team_service.create_team(test_db, "Team", captain.id, "LFA_PLAYER")

        with pytest.raises(HTTPException) as exc_info:
            team_service.remove_team_member(test_db, team.id, 99999)

        assert exc_info.value.status_code == 404
        assert "Team member not found" in exc_info.value.detail

    def test_remove_team_member_cannot_remove_captain(self, test_db: Session):
        """Error: Cannot remove captain without transfer"""
        captain = create_test_user(test_db, email="cap15@test.com", name="Captain 15")

        team = team_service.create_team(test_db, "Team", captain.id, "LFA_PLAYER")

        with pytest.raises(HTTPException) as exc_info:
            team_service.remove_team_member(test_db, team.id, captain.id)

        assert exc_info.value.status_code == 400
        assert "Transfer captaincy first" in exc_info.value.detail


class TestGetTeamMembers:
    """Test get_team_members() function"""

    def test_get_team_members_success(self, test_db: Session):
        """Get all active team members"""
        captain = create_test_user(test_db, email="cap16@test.com", name="Captain 16")
        player1 = create_test_user(test_db, email="player5@test.com", name="Player 5")
        player2 = create_test_user(test_db, email="player6@test.com", name="Player 6")

        team = team_service.create_team(test_db, "Team", captain.id, "LFA_PLAYER")
        team_service.add_team_member(test_db, team.id, player1.id)
        team_service.add_team_member(test_db, team.id, player2.id)

        members = team_service.get_team_members(test_db, team.id)

        assert len(members) == 3  # Captain + 2 players
        user_ids = [m.user_id for m in members]
        assert captain.id in user_ids
        assert player1.id in user_ids
        assert player2.id in user_ids

    def test_get_team_members_only_active(self, test_db: Session):
        """Get only active members (exclude removed)"""
        captain = create_test_user(test_db, email="cap17@test.com", name="Captain 17")
        player1 = create_test_user(test_db, email="player7@test.com", name="Player 7")
        player2 = create_test_user(test_db, email="player8@test.com", name="Player 8")

        team = team_service.create_team(test_db, "Team", captain.id, "LFA_PLAYER")
        team_service.add_team_member(test_db, team.id, player1.id)
        team_service.add_team_member(test_db, team.id, player2.id)

        # Remove player1
        team_service.remove_team_member(test_db, team.id, player1.id)

        members = team_service.get_team_members(test_db, team.id)

        user_ids = [m.user_id for m in members]
        assert player1.id not in user_ids
        assert player2.id in user_ids


class TestTransferCaptaincy:
    """Test transfer_captaincy() function"""

    def test_transfer_captaincy_success(self, test_db: Session):
        """Happy path: Transfer captain role to another member"""
        captain = create_test_user(test_db, email="cap18@test.com", name="Captain 18")
        player = create_test_user(test_db, email="player9@test.com", name="Player 9")

        team = team_service.create_team(test_db, "Team", captain.id, "LFA_PLAYER")
        team_service.add_team_member(test_db, team.id, player.id)

        updated_team = team_service.transfer_captaincy(test_db, team.id, captain.id, player.id)

        assert updated_team.captain_user_id == player.id

        # Verify roles updated
        members = test_db.query(TeamMember).filter(TeamMember.team_id == team.id).all()
        for member in members:
            if member.user_id == player.id:
                assert member.role == TeamMemberRole.CAPTAIN.value
            elif member.user_id == captain.id:
                assert member.role == TeamMemberRole.PLAYER.value

    def test_transfer_captaincy_team_not_found(self, test_db: Session):
        """Error: Team does not exist"""
        with pytest.raises(HTTPException) as exc_info:
            team_service.transfer_captaincy(test_db, 99999, 1, 2)

        assert exc_info.value.status_code == 404
        assert "Team not found" in exc_info.value.detail

    def test_transfer_captaincy_not_current_captain(self, test_db: Session):
        """Error: Only current captain can transfer"""
        captain = create_test_user(test_db, email="cap19@test.com", name="Captain 19")
        player1 = create_test_user(test_db, email="player10@test.com", name="Player 10")
        player2 = create_test_user(test_db, email="player11@test.com", name="Player 11")

        team = team_service.create_team(test_db, "Team", captain.id, "LFA_PLAYER")
        team_service.add_team_member(test_db, team.id, player1.id)
        team_service.add_team_member(test_db, team.id, player2.id)

        # Player1 tries to transfer captaincy (not captain)
        with pytest.raises(HTTPException) as exc_info:
            team_service.transfer_captaincy(test_db, team.id, player1.id, player2.id)

        assert exc_info.value.status_code == 403
        assert "Only current captain" in exc_info.value.detail

    def test_transfer_captaincy_new_captain_not_member(self, test_db: Session):
        """Error: New captain must be a team member"""
        captain = create_test_user(test_db, email="cap20@test.com", name="Captain 20")
        outsider = create_test_user(test_db, email="outsider@test.com", name="Outsider")

        team = team_service.create_team(test_db, "Team", captain.id, "LFA_PLAYER")

        with pytest.raises(HTTPException) as exc_info:
            team_service.transfer_captaincy(test_db, team.id, captain.id, outsider.id)

        assert exc_info.value.status_code == 400
        assert "must be an active team member" in exc_info.value.detail


class TestDeleteTeam:
    """Test delete_team() function"""

    def test_delete_team_success(self, test_db: Session):
        """Happy path: Soft-delete team"""
        captain = create_test_user(test_db, email="cap21@test.com", name="Captain 21")

        team = team_service.create_team(test_db, "Team To Delete", captain.id, "LFA_PLAYER")

        result = team_service.delete_team(test_db, team.id)

        assert result is True

        # Verify team is inactive
        deleted_team = test_db.query(Team).filter(Team.id == team.id).first()
        assert deleted_team.is_active is False

    def test_delete_team_not_found(self, test_db: Session):
        """Error: Team does not exist"""
        with pytest.raises(HTTPException) as exc_info:
            team_service.delete_team(test_db, 99999)

        assert exc_info.value.status_code == 404
        assert "Team not found" in exc_info.value.detail

    def test_delete_team_idempotent(self, test_db: Session):
        """Edge case: Deleting already deleted team"""
        captain = create_test_user(test_db, email="cap22@test.com", name="Captain 22")

        team = team_service.create_team(test_db, "Team", captain.id, "LFA_PLAYER")

        # Delete once
        team_service.delete_team(test_db, team.id)

        # Delete again - should succeed (soft delete is idempotent)
        result = team_service.delete_team(test_db, team.id)
        assert result is True
