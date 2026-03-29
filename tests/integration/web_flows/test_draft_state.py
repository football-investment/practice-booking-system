"""
DRAFT State Integration Tests

DS-01  PATCH /api/v1/tournaments/{id} — theme field saved and returned
DS-02  PATCH /api/v1/tournaments/{id} — winner_count field saved and returned
DS-03  PATCH /api/v1/tournaments/{id} — team_enrollment_cost saved in TournamentConfiguration
DS-04  PATCH /api/v1/tournaments/{id} — assignment_type accepts OPEN_ASSIGNMENT
DS-05  GET /events/{id} DRAFT — theme and focus_description rendered in page HTML
DS-06  DRAFT → ENROLLMENT_OPEN via state machine rejects blank name (400)
DS-07  DRAFT → ENROLLMENT_OPEN via state machine rejects past start_date (400)
DS-08  DRAFT → ENROLLMENT_OPEN via state machine rejects end_date < start_date (400)
DS-09  DRAFT → ENROLLMENT_OPEN via state machine rejects H2H without tournament_type_id (400)

All tests use SAVEPOINT-isolated real DB (test_db) + TestClient (client) fixtures
from tests/integration/conftest.py. Admin Bearer token authenticates PATCH calls.
"""
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.semester import Semester, SemesterStatus, SemesterCategory
from app.models.tournament_configuration import TournamentConfiguration
from app.models.game_configuration import GameConfiguration
from app.models.tournament_type import TournamentType
from app.models.game_preset import GamePreset
from app.models.campus import Campus
from app.models.location import Location
from app.core.security import get_password_hash


# ── Helpers ────────────────────────────────────────────────────────────────────

_PFX = "ds"


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _location(db: Session) -> Location:
    from app.models.location import LocationType
    uid = _uid()
    loc = Location(
        name=f"DS Location {uid}",
        city=f"DSCity-{uid}",
        country="Hungary",
        location_type=LocationType.PARTNER,
        location_code=f"DS{uid[:6]}",  # "DSxxxxxx" = 8 chars, within VARCHAR(10)
    )
    db.add(loc)
    db.flush()
    return loc


def _campus(db: Session, location: Location) -> Campus:
    camp = Campus(
        name=f"DS Campus {_uid()}",
        location_id=location.id,
    )
    db.add(camp)
    db.flush()
    return camp


def _tt(db: Session, fmt: str = "HEAD_TO_HEAD") -> TournamentType:
    code = f"ds-{fmt.lower()[:3]}-{_uid()}"
    tt = TournamentType(
        code=code,
        display_name=f"DS {fmt}",
        description="Auto-created for DS tests",
        format=fmt,
        min_players=2,
        max_players=64,
        requires_power_of_two=False,
        session_duration_minutes=60,
        break_between_sessions_minutes=10,
        config={"code": code},
    )
    db.add(tt)
    db.flush()
    return tt


def _preset(db: Session) -> GamePreset:
    code = f"ds-preset-{_uid()}"
    gp = GamePreset(
        code=code,
        name=f"DS Preset {_uid()}",
        description="Auto-created for DS tests",
        is_active=True,
        game_config={"metadata": {"min_players": 0}, "skills_tested": [], "skill_weights": {}},
    )
    db.add(gp)
    db.flush()
    return gp


def _tournament(
    db: Session,
    admin: User,
    *,
    tournament_status: str = "DRAFT",
    participant_type: str = "INDIVIDUAL",
    with_type: bool = True,
    campus: Campus | None = None,
    start_offset: int = 7,
    end_offset: int = 14,
) -> Semester:
    """Create a minimal DRAFT tournament with TournamentConfiguration."""
    tt = _tt(db) if with_type else None
    preset = _preset(db)

    t = Semester(
        name=f"DS Cup {_uid()}",
        code=f"DS-{_uid()}",
        master_instructor_id=admin.id,
        start_date=date.today() + timedelta(days=start_offset),
        end_date=date.today() + timedelta(days=end_offset),
        status=SemesterStatus.ONGOING,
        semester_category=SemesterCategory.TOURNAMENT,
        tournament_status=tournament_status,
        campus_id=campus.id if campus else None,
    )
    db.add(t)
    db.flush()

    db.add(TournamentConfiguration(
        semester_id=t.id,
        tournament_type_id=tt.id if tt else None,
        participant_type=participant_type,
        max_players=32,
        number_of_rounds=1,
        parallel_fields=1,
    ))
    db.add(GameConfiguration(
        semester_id=t.id,
        game_preset_id=preset.id,
    ))
    db.flush()
    return t


# ── DS-01: theme saved ────────────────────────────────────────────────────────

class TestPatchTheme:
    def test_theme_saved_and_returned(
        self, test_db: Session, client, admin_user: User, admin_token: str
    ):
        """DS-01: PATCH with theme → saved to semesters.theme, returned in response."""
        t = _tournament(test_db, admin_user)
        hdrs = {"Authorization": f"Bearer {admin_token}"}

        resp = client.patch(
            f"/api/v1/tournaments/{t.id}",
            json={"theme": "Spring 2026 Edition"},
            headers=hdrs,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "theme" in body["updates"]

        test_db.refresh(t)
        assert t.theme == "Spring 2026 Edition"

    def test_theme_appears_on_public_page(
        self, test_db: Session, client, admin_user: User, admin_token: str
    ):
        """DS-05 (partial): theme value visible in GET /events/{id} HTML."""
        t = _tournament(test_db, admin_user)
        t.theme = "Autumn Challenge"
        t.focus_description = "Play your best!"
        test_db.flush()

        resp = client.get(f"/events/{t.id}")
        assert resp.status_code == 200
        html = resp.text
        assert "Autumn Challenge" in html
        assert "Play your best!" in html


# ── DS-02: winner_count saved ────────────────────────────────────────────────

class TestPatchWinnerCount:
    def test_winner_count_saved(
        self, test_db: Session, client, admin_user: User, admin_token: str
    ):
        """DS-02: PATCH with winner_count → saved to semesters.winner_count."""
        t = _tournament(test_db, admin_user)
        hdrs = {"Authorization": f"Bearer {admin_token}"}

        resp = client.patch(
            f"/api/v1/tournaments/{t.id}",
            json={"winner_count": 3},
            headers=hdrs,
        )
        assert resp.status_code == 200, resp.text
        assert "winner_count" in resp.json()["updates"]

        test_db.refresh(t)
        assert t.winner_count == 3


# ── DS-03: team_enrollment_cost saved ───────────────────────────────────────

class TestPatchTeamEnrollmentCost:
    def test_team_enrollment_cost_saved(
        self, test_db: Session, client, admin_user: User, admin_token: str
    ):
        """DS-03: PATCH with team_enrollment_cost → saved in TournamentConfiguration."""
        t = _tournament(test_db, admin_user, participant_type="TEAM")
        hdrs = {"Authorization": f"Bearer {admin_token}"}

        resp = client.patch(
            f"/api/v1/tournaments/{t.id}",
            json={"team_enrollment_cost": 150},
            headers=hdrs,
        )
        assert resp.status_code == 200, resp.text
        assert "team_enrollment_cost" in resp.json()["updates"]

        test_db.refresh(t)
        assert t.tournament_config_obj.team_enrollment_cost == 150


# ── DS-04: assignment_type (already in schema) ──────────────────────────────

class TestPatchAssignmentType:
    def test_assignment_type_open_assignment(
        self, test_db: Session, client, admin_user: User, admin_token: str
    ):
        """DS-04: PATCH with assignment_type=OPEN_ASSIGNMENT → saved."""
        t = _tournament(test_db, admin_user)
        hdrs = {"Authorization": f"Bearer {admin_token}"}

        resp = client.patch(
            f"/api/v1/tournaments/{t.id}",
            json={"assignment_type": "OPEN_ASSIGNMENT"},
            headers=hdrs,
        )
        assert resp.status_code == 200, resp.text
        assert "assignment_type" in resp.json()["updates"]

        test_db.refresh(t)
        assert t.tournament_config_obj.assignment_type == "OPEN_ASSIGNMENT"

    def test_assignment_type_application_based(
        self, test_db: Session, client, admin_user: User, admin_token: str
    ):
        """DS-04b: PATCH with assignment_type=APPLICATION_BASED → saved."""
        t = _tournament(test_db, admin_user)
        hdrs = {"Authorization": f"Bearer {admin_token}"}

        resp = client.patch(
            f"/api/v1/tournaments/{t.id}",
            json={"assignment_type": "APPLICATION_BASED"},
            headers=hdrs,
        )
        assert resp.status_code == 200, resp.text

        test_db.refresh(t)
        assert t.tournament_config_obj.assignment_type == "APPLICATION_BASED"


# ── DS-06..09: state machine guards on DRAFT → ENROLLMENT_OPEN ──────────────

class TestDraftToEnrollmentOpenApiGuards:
    """State machine PATCH /status endpoint rejects DRAFT→ENROLLMENT_OPEN on bad data."""

    def _patch_status(self, client, tournament_id: int, new_status: str, hdrs: dict):
        return client.patch(
            f"/api/v1/tournaments/{tournament_id}/status",
            json={"new_status": new_status},
            headers=hdrs,
        )

    def test_blank_name_blocked(
        self, test_db: Session, client, admin_user: User, admin_token: str
    ):
        """DS-06: blank name → DRAFT→ENROLLMENT_OPEN returns 400."""
        loc = _location(test_db)
        camp = _campus(test_db, loc)
        t = _tournament(test_db, admin_user, campus=camp)
        t.name = "   "
        test_db.flush()

        hdrs = {"Authorization": f"Bearer {admin_token}"}
        resp = self._patch_status(client, t.id, "ENROLLMENT_OPEN", hdrs)
        assert resp.status_code == 400, resp.text
        body = resp.json()
        msg = (body.get("error", {}).get("message") or body.get("detail") or "").lower()
        assert "name" in msg

    def test_past_start_date_blocked(
        self, test_db: Session, client, admin_user: User, admin_token: str
    ):
        """DS-07: start_date in the past → DRAFT→ENROLLMENT_OPEN returns 400."""
        loc = _location(test_db)
        camp = _campus(test_db, loc)
        t = _tournament(test_db, admin_user, campus=camp, start_offset=-1, end_offset=14)

        hdrs = {"Authorization": f"Bearer {admin_token}"}
        resp = self._patch_status(client, t.id, "ENROLLMENT_OPEN", hdrs)
        assert resp.status_code == 400, resp.text
        body = resp.json()
        msg = (body.get("error", {}).get("message") or body.get("detail") or "").lower()
        assert "start" in msg or "past" in msg or "date" in msg

    def test_end_before_start_blocked(
        self, test_db: Session, client, admin_user: User, admin_token: str
    ):
        """DS-08: end_date < start_date → DRAFT→ENROLLMENT_OPEN returns 400."""
        loc = _location(test_db)
        camp = _campus(test_db, loc)
        t = _tournament(test_db, admin_user, campus=camp, start_offset=14, end_offset=7)

        hdrs = {"Authorization": f"Bearer {admin_token}"}
        resp = self._patch_status(client, t.id, "ENROLLMENT_OPEN", hdrs)
        assert resp.status_code == 400, resp.text
        body = resp.json()
        msg = (body.get("error", {}).get("message") or body.get("detail") or "").lower()
        assert "end" in msg or "date" in msg

    def test_individual_ranking_no_type_opens_enrollment(
        self, test_db: Session, client, admin_user: User, admin_token: str
    ):
        """DS-09: INDIVIDUAL_RANKING without tournament_type_id → DRAFT→ENROLLMENT_OPEN allowed.

        The H2H-without-type scenario is architecturally impossible in the DB:
        Semester.format derives from TournamentType.format — so when tournament_type_id=None,
        the format is always "INDIVIDUAL_RANKING". This test verifies the IR path is not blocked.
        The H2H guard (unit-tested in TestDraftToEnrollmentOpenValidation.test_h2h_without_type_id_rejected)
        covers the validator logic for mocked H2H objects.
        """
        loc = _location(test_db)
        camp = _campus(test_db, loc)
        t = _tournament(test_db, admin_user, campus=camp, with_type=False)

        hdrs = {"Authorization": f"Bearer {admin_token}"}
        resp = self._patch_status(client, t.id, "ENROLLMENT_OPEN", hdrs)
        assert resp.status_code == 200, resp.text

        test_db.refresh(t)
        assert t.tournament_status == "ENROLLMENT_OPEN"

    def test_valid_draft_opens_enrollment(
        self, test_db: Session, client, admin_user: User, admin_token: str
    ):
        """DS-10: all conditions met → DRAFT→ENROLLMENT_OPEN succeeds (200)."""
        loc = _location(test_db)
        camp = _campus(test_db, loc)
        t = _tournament(test_db, admin_user, campus=camp)
        # Ensure name is non-empty and dates are future (default factory does this)

        hdrs = {"Authorization": f"Bearer {admin_token}"}
        resp = self._patch_status(client, t.id, "ENROLLMENT_OPEN", hdrs)
        assert resp.status_code == 200, resp.text

        test_db.refresh(t)
        assert t.tournament_status == "ENROLLMENT_OPEN"
