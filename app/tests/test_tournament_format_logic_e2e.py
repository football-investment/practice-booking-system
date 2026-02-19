"""
E2E Test: Tournament Format Logic (INDIVIDUAL_RANKING vs HEAD_TO_HEAD)

Tests the architectural refactor that separates:
- INDIVIDUAL_RANKING: Simple competition format (no tournament type needed)
- HEAD_TO_HEAD: 1v1 matches with tournament structure (Swiss, League, Knockout, etc.)
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User, UserRole
from app.models.specialization import SpecializationType
from app.services.tournament_session_generator import TournamentSessionGenerator


def test_individual_ranking_tournament_creation_and_validation(client: TestClient, db_session, admin_token: str):
    """
    Test INDIVIDUAL_RANKING tournament:
    1. tournament_type_id MUST be NULL
    2. Validation rejects tournament_type_id if format is INDIVIDUAL_RANKING
    3. Session generation creates single competition session
    """
    db = db_session
    # ============================================================================
    # STEP 1: Create INDIVIDUAL_RANKING tournament with tournament_type_id (SHOULD FAIL)
    # ============================================================================
    response = client.post(
        "/api/v1/tournaments/generate",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "date": "2026-02-01",
            "name": "Speed Test Championship",
            "specialization_type": "LFA_FOOTBALL_PLAYER",
            "age_group": "YOUTH",
            "location_id": 1,
            "assignment_type": "APPLICATION_BASED",
            "max_players": 20,
            "enrollment_cost": 100,
            "format": "INDIVIDUAL_RANKING",
            "scoring_type": "TIME_BASED",
            "tournament_type_id": 1,  # ❌ INVALID: INDIVIDUAL_RANKING cannot have type
            "sessions": []
        }
    )

    assert response.status_code == 422, "Should reject INDIVIDUAL_RANKING with tournament_type_id"
    assert "cannot have a tournament_type" in response.json()["detail"][0]["msg"].lower()

    # ============================================================================
    # STEP 2: Create valid INDIVIDUAL_RANKING tournament (tournament_type_id = NULL)
    # ============================================================================
    response = client.post(
        "/api/v1/tournaments/generate",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "date": "2026-02-01",
            "name": "Speed Test Championship",
            "specialization_type": "LFA_FOOTBALL_PLAYER",
            "age_group": "YOUTH",
            "location_id": 1,
            "assignment_type": "APPLICATION_BASED",
            "max_players": 20,
            "enrollment_cost": 100,
            "format": "INDIVIDUAL_RANKING",
            "scoring_type": "TIME_BASED",
            "tournament_type_id": None,  # ✅ VALID: NULL for INDIVIDUAL_RANKING
            "sessions": []
        }
    )

    assert response.status_code == 201, f"Failed to create INDIVIDUAL_RANKING tournament: {response.json()}"
    tournament_data = response.json()
    tournament_id = tournament_data["tournament_id"]

    # Verify tournament format and scoring_type
    tournament_response = client.get(
        f"/api/v1/semesters/{tournament_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    tournament = tournament_response.json()
    assert tournament["format"] == "INDIVIDUAL_RANKING"
    assert tournament["scoring_type"] == "TIME_BASED"
    assert tournament["tournament_type_id"] is None

    # ============================================================================
    # STEP 3: Enroll players (need at least 2 for INDIVIDUAL_RANKING)
    # ============================================================================
    # Create 5 players
    player_ids = []
    for i in range(5):
        player = User(
            email=f"player{i}@test.com",
            name=f"Player {i}",
            role=UserRole.STUDENT,
            hashed_password="test_hash",
            specialization=SpecializationType.LFA_FOOTBALL_PLAYER.value
        )
        db.add(player)
        db.commit()
        db.refresh(player)
        player_ids.append(player.id)

        # Create user license for each player
        from app.models.license import UserLicense
        license = UserLicense(
            user_id=player.id,
            specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER.value,
            credit_balance=1000,
            onboarding_completed=True
        )
        db.add(license)
        db.commit()

    # Enroll all players
    for player_id in player_ids:
        enroll_response = client.post(
            f"/api/v1/tournaments/{tournament_id}/enroll",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"user_id": player_id}
        )
        assert enroll_response.status_code in [200, 201]

    # Approve all enrollments (admin)
    enrollments_response = client.get(
        f"/api/v1/tournaments/{tournament_id}/enrollments",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    enrollments = enrollments_response.json()
    for enrollment in enrollments:
        approve_response = client.post(
            f"/api/v1/tournaments/{tournament_id}/enrollments/{enrollment['id']}/approve",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert approve_response.status_code == 200

    # ============================================================================
    # STEP 4: Move tournament to IN_PROGRESS status
    # ============================================================================
    # Assign instructor and move to IN_PROGRESS
    # (Simplified - in real flow this involves instructor assignment)
    from app.models.semester import Semester
    tournament_obj = db.query(Semester).filter(Semester.id == tournament_id).first()
    tournament_obj.tournament_status = "IN_PROGRESS"
    db.commit()

    # ============================================================================
    # STEP 5: Generate sessions (should create single INDIVIDUAL_RANKING session)
    # ============================================================================
    generator = TournamentSessionGenerator(db)
    success, message, sessions = generator.generate_sessions(
        tournament_id=tournament_id,
        parallel_fields=1,
        session_duration_minutes=90,
        break_minutes=15
    )

    assert success, f"Session generation failed: {message}"
    assert len(sessions) == 1, f"INDIVIDUAL_RANKING should create 1 session, got {len(sessions)}"

    session = sessions[0]
    assert session["match_format"] == "INDIVIDUAL_RANKING"
    assert session["scoring_type"] == "TIME_BASED"
    assert session["tournament_phase"] == "INDIVIDUAL_RANKING"
    assert len(session["participant_user_ids"]) == 5, "All 5 players should participate"
    assert "lowest time wins" in session["description"].lower()


def test_head_to_head_tournament_requires_type(client: TestClient, db_session, admin_token: str):
    """
    Test HEAD_TO_HEAD tournament:
    1. tournament_type_id is REQUIRED
    2. Validation rejects NULL tournament_type_id if format is HEAD_TO_HEAD
    """
    db = db_session
    # ============================================================================
    # STEP 1: Create HEAD_TO_HEAD without tournament_type_id (SHOULD FAIL)
    # ============================================================================
    response = client.post(
        "/api/v1/tournaments/generate",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "date": "2026-02-02",
            "name": "1v1 Championship",
            "specialization_type": "LFA_FOOTBALL_PLAYER",
            "age_group": "YOUTH",
            "location_id": 1,
            "assignment_type": "APPLICATION_BASED",
            "max_players": 8,
            "enrollment_cost": 100,
            "format": "HEAD_TO_HEAD",
            "scoring_type": "SCORE_BASED",
            "tournament_type_id": None,  # ❌ INVALID: HEAD_TO_HEAD requires type
            "sessions": []
        }
    )

    assert response.status_code == 422, "Should reject HEAD_TO_HEAD without tournament_type_id"
    assert "must have a tournament_type" in response.json()["detail"][0]["msg"].lower()

    # ============================================================================
    # STEP 2: Create valid HEAD_TO_HEAD tournament with Swiss type
    # ============================================================================
    response = client.post(
        "/api/v1/tournaments/generate",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "date": "2026-02-02",
            "name": "1v1 Championship",
            "specialization_type": "LFA_FOOTBALL_PLAYER",
            "age_group": "YOUTH",
            "location_id": 1,
            "assignment_type": "APPLICATION_BASED",
            "max_players": 8,
            "enrollment_cost": 100,
            "format": "HEAD_TO_HEAD",
            "scoring_type": "SCORE_BASED",
            "tournament_type_id": 4,  # ✅ VALID: Swiss type
            "sessions": []
        }
    )

    assert response.status_code == 201, f"Failed to create HEAD_TO_HEAD tournament: {response.json()}"
    tournament_data = response.json()
    tournament_id = tournament_data["tournament_id"]

    # Verify tournament has type
    tournament_response = client.get(
        f"/api/v1/semesters/{tournament_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    tournament = tournament_response.json()
    assert tournament["format"] == "HEAD_TO_HEAD"
    assert tournament["tournament_type_id"] == 4
