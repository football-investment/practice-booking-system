"""
Tournament Test Data Seeding Fixtures

Provides reusable pytest fixtures for seeding tournament test data.

Usage:
    @pytest.mark.usefixtures("seed_tournament_types")
    def test_something(db_session):
        # Tournament types are already seeded
        pass
"""

import pytest
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.models.tournament_type import TournamentType
from app.models.location import Location
from app.models.campus import Campus
from app.models.user import User, UserRole
from app.models.semester import Semester, TournamentStatus, SemesterType
from app.core.security import get_password_hash


@pytest.fixture(scope="function")
def seed_tournament_types(db_session: Session):
    """
    Seed tournament types into test database

    Creates 4 standard tournament types:
    - League (Round Robin)
    - Knockout (Single Elimination)
    - Group Stage + Knockout
    - Swiss System
    """
    tournament_types = [
        {
            "code": "league",
            "display_name": "League (Round Robin)",
            "description": "Round-robin tournament where every player plays every other player",
            "min_players": 4,
            "max_players": 16,
            "requires_power_of_two": False,
            "session_duration_minutes": 90,
            "break_between_sessions_minutes": 15,
            "config": {
                "format": "round_robin",
                "matches_per_round": "all_combinations"
            }
        },
        {
            "code": "knockout",
            "display_name": "Single Elimination (Knockout)",
            "description": "Single-elimination bracket tournament",
            "min_players": 4,
            "max_players": 64,
            "requires_power_of_two": True,
            "session_duration_minutes": 90,
            "break_between_sessions_minutes": 15,
            "config": {
                "format": "knockout",
                "seeding": "random"
            }
        },
        {
            "code": "group_knockout",
            "display_name": "Group Stage + Knockout",
            "description": "Group stage followed by knockout bracket",
            "min_players": 8,
            "max_players": 32,
            "requires_power_of_two": False,
            "session_duration_minutes": 90,
            "break_between_sessions_minutes": 15,
            "config": {
                "format": "group_knockout",
                "group_size": 4,
                "advance_from_group": 2
            }
        },
        {
            "code": "swiss",
            "display_name": "Swiss System",
            "description": "Swiss-system tournament with pairing based on current standings",
            "min_players": 4,
            "max_players": 64,
            "requires_power_of_two": False,
            "session_duration_minutes": 90,
            "break_between_sessions_minutes": 15,
            "config": {
                "format": "swiss",
                "rounds": "auto"
            }
        }
    ]

    created_types = []
    for tt_data in tournament_types:
        # Check if already exists
        existing = db_session.query(TournamentType).filter_by(code=tt_data["code"]).first()
        if existing:
            created_types.append(existing)
            continue

        tournament_type = TournamentType(**tt_data)
        db_session.add(tournament_type)
        created_types.append(tournament_type)

    db_session.commit()

    return created_types


@pytest.fixture(scope="function")
def seed_test_location(db_session: Session):
    """
    Seed a test location into database

    Returns:
        Location object
    """
    location = Location(
        name="Test Location",
        address="123 Test Street",
        city="Test City",
        country="Test Country",
        is_active=True
    )
    db_session.add(location)
    db_session.commit()
    db_session.refresh(location)

    return location


@pytest.fixture(scope="function")
def seed_test_campus(db_session: Session, seed_test_location: Location):
    """
    Seed a test campus into database

    Args:
        seed_test_location: Location fixture

    Returns:
        Campus object
    """
    campus = Campus(
        location_id=seed_test_location.id,
        name="Test Campus",
        address="456 Campus Avenue",
        capacity=100,
        is_active=True
    )
    db_session.add(campus)
    db_session.commit()
    db_session.refresh(campus)

    return campus


@pytest.fixture(scope="function")
def seed_test_players(db_session: Session, count: int = 8):
    """
    Seed test player users into database

    Args:
        count: Number of players to create (default: 8)

    Returns:
        List of User objects
    """
    players = []

    for i in range(1, count + 1):
        player = User(
            name=f"Test Player {i}",
            email=f"player{i}@test.com",
            password_hash=get_password_hash("test123"),
            role=UserRole.STUDENT,
            is_active=True,
            date_of_birth=date.today() - timedelta(days=365 * 20),  # 20 years old
            credits=1000  # Initial credits for enrollment
        )
        db_session.add(player)
        players.append(player)

    db_session.commit()

    for player in players:
        db_session.refresh(player)

    return players


@pytest.fixture(scope="function")
def create_test_tournament(
    db_session: Session,
    client,
    admin_token: str,
    seed_tournament_types,
    seed_test_campus: Campus
):
    """
    Factory fixture to create test tournaments

    Usage:
        def test_something(create_test_tournament):
            tournament = create_test_tournament(
                name="My Test Tournament",
                tournament_type_code="knockout",
                max_players=8
            )

    Returns:
        Function that creates and returns tournament dict
    """

    def _create_tournament(
        name: str = "Test Tournament",
        tournament_type_code: str = "knockout",
        max_players: int = 8,
        enrollment_cost: int = 500
    ):
        """
        Create a test tournament via API

        Args:
            name: Tournament name
            tournament_type_code: Tournament type code (league, knockout, etc.)
            max_players: Maximum number of players
            enrollment_cost: Enrollment cost in credits

        Returns:
            Dict with tournament data from API response
        """
        # Get tournament type
        tournament_type = db_session.query(TournamentType).filter_by(
            code=tournament_type_code
        ).first()

        assert tournament_type is not None, f"Tournament type '{tournament_type_code}' not found"

        headers = {"Authorization": f"Bearer {admin_token}"}

        tournament_data = {
            "date": (date.today() + timedelta(days=7)).isoformat(),
            "name": name,
            "sessions": [],
            "auto_book_students": False,
            "reward_policy_name": "default",
            "assignment_type": "APPLICATION_BASED",
            "max_players": max_players,
            "enrollment_cost": enrollment_cost,
            "tournament_type_id": tournament_type.id
        }

        response = client.post(
            "/api/v1/tournaments/generate",
            headers=headers,
            json=tournament_data
        )

        assert response.status_code == 200, f"Failed to create tournament: {response.text}"

        return response.json()

    return _create_tournament


@pytest.fixture(scope="function")
def enroll_players_in_tournament(
    db_session: Session,
    client,
    admin_token: str
):
    """
    Factory fixture to enroll players in a tournament

    Usage:
        def test_something(enroll_players_in_tournament, seed_test_players):
            players = seed_test_players
            enrollments = enroll_players_in_tournament(
                tournament_id=123,
                players=players
            )

    Returns:
        Function that enrolls players and returns enrollment list
    """

    def _enroll_players(tournament_id: int, players: list):
        """
        Enroll multiple players in a tournament

        Args:
            tournament_id: Tournament ID
            players: List of User objects

        Returns:
            List of enrollment dicts from API responses
        """
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        enrollments = []

        for player in players:
            # Give player credits if needed
            if player.credits < 500:
                credit_response = client.post(
                    f"/api/v1/users/{player.id}/credits",
                    headers=admin_headers,
                    json={"amount": 1000, "reason": "Test enrollment credits"}
                )
                assert credit_response.status_code == 200

            # Login as player
            login_response = client.post(
                "/api/v1/auth/login",
                json={"email": player.email, "password": "test123"}
            )
            assert login_response.status_code == 200
            player_token = login_response.json()["access_token"]
            player_headers = {"Authorization": f"Bearer {player_token}"}

            # Enroll
            enroll_response = client.post(
                f"/api/v1/tournaments/{tournament_id}/enroll",
                headers=player_headers
            )
            assert enroll_response.status_code == 200
            enrollments.append(enroll_response.json())

        return enrollments

    return _enroll_players


@pytest.fixture(scope="function")
def transition_tournament_status(client, admin_token: str):
    """
    Factory fixture to transition tournament status

    Usage:
        def test_something(transition_tournament_status):
            transition_tournament_status(
                tournament_id=123,
                new_status="IN_PROGRESS",
                reason="Starting tournament"
            )

    Returns:
        Function that transitions tournament status
    """

    def _transition_status(
        tournament_id: int,
        new_status: str,
        reason: str = "Test status transition"
    ):
        """
        Transition tournament to new status

        Args:
            tournament_id: Tournament ID
            new_status: New TournamentStatus value
            reason: Transition reason

        Returns:
            Response JSON
        """
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.patch(
            f"/api/v1/tournaments/{tournament_id}/status",
            headers=headers,
            json={
                "new_status": new_status,
                "reason": reason
            }
        )

        assert response.status_code == 200, f"Failed to transition status: {response.text}"

        return response.json()

    return _transition_status


@pytest.fixture(scope="function")
def generate_tournament_sessions(client, admin_token: str):
    """
    Factory fixture to generate tournament sessions

    Usage:
        def test_something(generate_tournament_sessions):
            result = generate_tournament_sessions(
                tournament_id=123,
                parallel_fields=1,
                session_duration_minutes=90
            )

    Returns:
        Function that generates tournament sessions
    """

    def _generate_sessions(
        tournament_id: int,
        parallel_fields: int = 1,
        session_duration_minutes: int = 90,
        break_minutes: int = 15
    ):
        """
        Generate tournament sessions via API

        Args:
            tournament_id: Tournament ID
            parallel_fields: Number of parallel fields
            session_duration_minutes: Session duration
            break_minutes: Break between sessions

        Returns:
            Response JSON with generation results
        """
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.post(
            f"/api/v1/tournaments/{tournament_id}/generate-sessions",
            headers=headers,
            params={
                "parallel_fields": parallel_fields,
                "session_duration_minutes": session_duration_minutes,
                "break_minutes": break_minutes
            }
        )

        assert response.status_code == 200, f"Failed to generate sessions: {response.text}"

        return response.json()

    return _generate_sessions
