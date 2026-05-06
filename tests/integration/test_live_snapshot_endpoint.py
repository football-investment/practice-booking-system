"""Integration tests for /admin/tournaments/{id}/live-snapshot — PR Live-2.

LI-01  authenticated admin GET returns 200 JSON with expected keys
LI-02  missing Authorization header returns 401 JSON
"""
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User, UserRole
from app.database import get_db


# ── LI-01 ─────────────────────────────────────────────────────────────────────

def test_li_01_authenticated_snapshot_returns_200():
    admin = MagicMock(spec=User)
    admin.id = 1
    admin.role = UserRole.ADMIN
    admin.is_active = True
    admin.email = "admin@test.com"

    fake_tournament = MagicMock()
    fake_tournament.id = 99
    fake_tournament.name = "Test Tournament"
    fake_tournament.tournament_status = "IN_PROGRESS"
    fake_tournament.organizer_sponsor = None
    fake_tournament.organizer_campaign = None
    fake_tournament.tournament_config_obj = None
    fake_tournament.game_config_obj = None

    fake_live_model = {
        "format_type": "league",
        "tournament_status": "IN_PROGRESS",
        "summary": {
            "tournament_id": 99,
            "tournament_name": "Test Tournament",
            "tournament_status": "IN_PROGRESS",
            "total_sessions": 0,
            "completed_sessions": 0,
            "progress_pct": 0.0,
            "enrollment_count": 0,
            "checkin_count": 0,
        },
        "instructor_roster": [],
        "sponsor_context": None,
        "group_stage": None,
        "knockout_bracket": None,
        "league_rounds": None,
        "league_standings": None,
    }

    user_q = MagicMock()
    user_q.filter.return_value.first.return_value = admin

    tournament_q = MagicMock()
    tournament_q.filter.return_value.first.return_value = fake_tournament

    db_mock = MagicMock()

    def _db_query(model):
        from app.models.user import User as UserModel
        from app.models.semester import Semester
        if model is UserModel:
            return user_q
        return tournament_q

    db_mock.query.side_effect = _db_query

    app.dependency_overrides[get_db] = lambda: db_mock

    try:
        with patch("app.api.web_routes.tournament_live.verify_token", return_value="admin@test.com"), \
             patch("app.api.web_routes.tournament_live.build_live_model", return_value=fake_live_model), \
             patch("app.services.tournament.instructor_planning_service.get_roster", return_value=[]):

            client = TestClient(app, raise_server_exceptions=True)
            response = client.get(
                "/admin/tournaments/99/live-snapshot",
                headers={"Authorization": "Bearer fake-token"},
            )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert "format_type" in data
    assert "summary" in data


# ── LI-02 ─────────────────────────────────────────────────────────────────────

def test_li_02_unauthenticated_snapshot_returns_401():
    client = TestClient(app, raise_server_exceptions=True)
    response = client.get("/admin/tournaments/99/live-snapshot")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
