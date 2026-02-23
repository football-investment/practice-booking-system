"""
Simple validation test for tournament format logic

Tests ONLY the API validation:
- INDIVIDUAL_RANKING cannot have tournament_type_id
- HEAD_TO_HEAD must have tournament_type_id
"""
import pytest
from fastapi.testclient import TestClient


def test_individual_ranking_rejects_tournament_type(client: TestClient, admin_token: str):
    """
    INDIVIDUAL_RANKING tournament CANNOT have tournament_type_id
    API should return 422 validation error
    """
    from datetime import datetime, timedelta, timezone
    future_date = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")

    response = client.post(
        "/api/v1/tournaments/generate",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "date": future_date,
            "name": "Speed Test",
            "specialization_type": "LFA_FOOTBALL_PLAYER",
            "assignment_type": "APPLICATION_BASED",
            "max_players": 20,
            "enrollment_cost": 100,
            "format": "INDIVIDUAL_RANKING",
            "scoring_type": "TIME_BASED",
            "tournament_type_id": 1,  # ❌ INVALID
        }
    )

    assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.json()}"
    error_detail = str(response.json())
    assert "cannot have a tournament_type" in error_detail.lower(), f"Wrong error message: {error_detail}"


def test_individual_ranking_accepts_null_type(client: TestClient, admin_token: str):
    """
    INDIVIDUAL_RANKING tournament with tournament_type_id=NULL should succeed
    """
    from datetime import datetime, timedelta, timezone
    future_date = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")

    response = client.post(
        "/api/v1/tournaments/generate",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "date": future_date,
            "name": "Speed Test",
            "specialization_type": "LFA_FOOTBALL_PLAYER",
            "assignment_type": "APPLICATION_BASED",
            "max_players": 20,
            "enrollment_cost": 100,
            "format": "INDIVIDUAL_RANKING",
            "scoring_type": "TIME_BASED",
            "tournament_type_id": None,  # ✅ VALID
        }
    )

    assert response.status_code == 201, f"Failed to create tournament: {response.json()}"
    data = response.json()
    assert data["tournament_id"] is not None


def test_head_to_head_requires_tournament_type(client: TestClient, admin_token: str):
    """
    HEAD_TO_HEAD tournament MUST have tournament_type_id
    API should return 422 validation error if NULL
    """
    from datetime import datetime, timedelta, timezone
    future_date = (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%d")

    response = client.post(
        "/api/v1/tournaments/generate",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "date": future_date,
            "name": "1v1 Championship",
            "specialization_type": "LFA_FOOTBALL_PLAYER",
            "assignment_type": "APPLICATION_BASED",
            "max_players": 8,
            "enrollment_cost": 100,
            "format": "HEAD_TO_HEAD",
            "scoring_type": "SCORE_BASED",
            "tournament_type_id": None,  # ❌ INVALID
        }
    )

    assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.json()}"
    error_detail = str(response.json())
    assert "must have a tournament_type" in error_detail.lower(), f"Wrong error message: {error_detail}"


def test_head_to_head_accepts_tournament_type(client: TestClient, admin_token: str, db_session):
    """
    HEAD_TO_HEAD tournament with tournament_type_id should succeed
    (Skipped if tournament_type_id=4 doesn't exist in test DB)
    """
    from datetime import datetime, timedelta, timezone
    future_date = (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%d")

    # First, check if tournament type exists
    from app.models.tournament_type import TournamentType
    tournament_type = db_session.query(TournamentType).filter(TournamentType.id == 4).first()

    if not tournament_type:
        pytest.skip("Tournament type ID=4 (Swiss) not found in test database")

    response = client.post(
        "/api/v1/tournaments/generate",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "date": future_date,
            "name": "1v1 Championship",
            "specialization_type": "LFA_FOOTBALL_PLAYER",
            "assignment_type": "APPLICATION_BASED",
            "max_players": 8,
            "enrollment_cost": 100,
            "format": "HEAD_TO_HEAD",
            "scoring_type": "SCORE_BASED",
            "tournament_type_id": 4,  # ✅ VALID (Swiss)
        }
    )

    assert response.status_code == 201, f"Failed to create tournament: {response.json()}"
    data = response.json()
    assert data["tournament_id"] is not None
