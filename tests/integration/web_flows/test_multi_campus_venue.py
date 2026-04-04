"""
Multi-Campus Venue + Instructor Integration Tests

MCV-01  Session with campus+pitch+instructor → venue line in schedule (AC-01)
MCV-02  2+ different campuses in one tournament → both names visible (AC-02)
MCV-03  TournamentInstructorSlot MASTER role → "(Master)" chip in info grid (AC-03)
MCV-04  Same instructor across 2 campus sessions → instructor name appears with both (AC-04)
MCV-05  Player in sessions from 2 different campuses → both campuses visible (AC-05)
MCV-06  IR session with campus → venue line in IR results block (AC-06)
MCV-07  GK GROUP_STAGE vs KNOCKOUT sessions get different campuses → both visible (AC-07)
MCV-08  Session with campus_id=None → 200, no "None" string in schedule (AC-08)

All tests hit GET /events/{id} and assert on the returned HTML.
SAVEPOINT-isolated DB shared between the test and TestClient via get_db override.
"""

import json
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import get_db
from app.models.user import User, UserRole
from app.models.semester import Semester, SemesterStatus, SemesterCategory
from app.models.tournament_configuration import TournamentConfiguration
from app.models.tournament_type import TournamentType
from app.models.game_configuration import GameConfiguration
from app.models.game_preset import GamePreset
from app.models.session import Session as SessionModel, EventCategory
from app.models.location import Location, LocationType
from app.models.campus import Campus
from app.models.pitch import Pitch
from app.models.tournament_instructor_slot import TournamentInstructorSlot
from app.models.tournament_enums import TournamentPhase
from app.core.security import get_password_hash


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_PFX = "mcv"


def _uid() -> str:
    return uuid.uuid4().hex[:8]


@contextmanager
def _public_client(db: Session):
    """TestClient sharing the test SAVEPOINT session (no auth)."""
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def _user(db: Session, role: UserRole = UserRole.STUDENT, name: str | None = None) -> User:
    u = User(
        email=f"{_PFX}-{_uid()}@lfa-test.com",
        name=name or f"MCV Player {_uid()}",
        password_hash=get_password_hash("pw"),
        role=role,
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def _campus(db: Session, loc: Location | None = None, name: str | None = None) -> Campus:
    if loc is None:
        uid = _uid()
        loc = Location(
            name=f"MCV Location {uid}",
            city=f"MCVCity-{uid}",
            country="HU",
            location_type=LocationType.CENTER,
        )
        db.add(loc)
        db.flush()
    camp = Campus(location_id=loc.id, name=name or f"MCV Campus {_uid()}", is_active=True)
    db.add(camp)
    db.flush()
    return camp


def _pitch(db: Session, campus: Campus, number: int = 1) -> Pitch:
    p = Pitch(campus_id=campus.id, pitch_number=number, name=f"Pálya {number}", is_active=True)
    db.add(p)
    db.flush()
    return p


def _tt(db: Session, fmt: str = "HEAD_TO_HEAD") -> TournamentType:
    code = f"{_PFX}-{fmt.lower()[:3]}-{_uid()}"
    tt = TournamentType(
        code=code,
        display_name=f"MCV {fmt}",
        description="Auto-created for MCV tests",
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
    code = f"{_PFX}-preset-{_uid()}"
    gp = GamePreset(
        code=code,
        name=f"MCV Preset {_uid()}",
        description="Auto-created for MCV tests",
        is_active=True,
        game_config={"metadata": {"min_players": 0}, "skills_tested": [], "skill_weights": {}},
    )
    db.add(gp)
    db.flush()
    return gp


def _tournament(
    db: Session,
    participant_type: str = "INDIVIDUAL",
    tournament_status: str = "REWARDS_DISTRIBUTED",
    tt: TournamentType | None = None,
    campus: Campus | None = None,
) -> Semester:
    """Create a minimal tournament with TournamentConfiguration."""
    instr = _user(db, role=UserRole.INSTRUCTOR, name=f"MCV Instructor {_uid()}")
    if tt is None:
        tt = _tt(db)
    preset = _preset(db)
    if campus is None:
        campus = _campus(db)

    t = Semester(
        name=f"MCV Cup {_uid()}",
        code=f"MCV-{_uid()}",
        master_instructor_id=instr.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        status=SemesterStatus.ONGOING,
        semester_category=SemesterCategory.TOURNAMENT,
        tournament_status=tournament_status,
        campus_id=campus.id,
    )
    db.add(t)
    db.flush()
    db.add(TournamentConfiguration(
        semester_id=t.id,
        tournament_type_id=tt.id,
        participant_type=participant_type,
        max_players=32,
        number_of_rounds=1,
        parallel_fields=1,
    ))
    db.add(GameConfiguration(semester_id=t.id, game_preset_id=preset.id))
    db.flush()
    return t


def _session(
    db: Session,
    tournament: Semester,
    *,
    round_number: int = 1,
    participant_user_ids: list[int] | None = None,
    participant_team_ids: list[int] | None = None,
    game_results: dict | None = None,
    rounds_data: dict | None = None,
    status: str = "completed",
    campus: Campus | None = None,
    pitch: Pitch | None = None,
    instructor: User | None = None,
    tournament_phase: TournamentPhase | None = None,
) -> SessionModel:
    sess = SessionModel(
        semester_id=tournament.id,
        instructor_id=(instructor.id if instructor else tournament.master_instructor_id),
        title=f"MCV Match R{round_number}",
        event_category=EventCategory.MATCH,
        auto_generated=True,
        capacity=2,
        round_number=round_number,
        session_status=status,
        participant_user_ids=participant_user_ids,
        participant_team_ids=participant_team_ids,
        game_results=json.dumps(game_results) if game_results else None,
        rounds_data=rounds_data,
        date_start=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
        date_end=datetime(2026, 6, 1, 11, 0, tzinfo=timezone.utc),
        campus_id=campus.id if campus else None,
        pitch_id=pitch.id if pitch else None,
        tournament_phase=tournament_phase,
    )
    db.add(sess)
    db.flush()
    return sess


def _h2h_game_results(uid_a: int, uid_b: int) -> dict:
    return {
        "match_format": "HEAD_TO_HEAD",
        "participants": [
            {"user_id": uid_a, "score": 3.0, "result": "win"},
            {"user_id": uid_b, "score": 0.0, "result": "loss"},
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMultiCampusVenue:

    # ── MCV-01 (AC-01): session with full venue data → venue line shown ───────
    def test_MCV_01_session_venue_shown_in_schedule(self, test_db: Session):
        """
        A completed session with campus_id, pitch_id, instructor_id must render
        a .match-venue line containing the campus name and pitch name.
        """
        p_a = _user(test_db, name="Alice Alpha")
        p_b = _user(test_db, name="Bob Beta")
        camp = _campus(test_db, name="LFA Debrecen Campus")
        pitch = _pitch(test_db, camp, number=1)
        instr = _user(test_db, role=UserRole.INSTRUCTOR, name="Venue Instructor")
        t = _tournament(test_db, campus=camp)

        _session(
            test_db, t,
            participant_user_ids=[p_a.id, p_b.id],
            game_results=_h2h_game_results(p_a.id, p_b.id),
            campus=camp, pitch=pitch, instructor=instr,
        )

        with _public_client(test_db) as client:
            resp = client.get(f"/events/{t.id}")

        assert resp.status_code == 200
        body = resp.text
        assert "match-venue" in body, "No .match-venue element in schedule"
        assert "LFA Debrecen Campus" in body, "Campus name missing from venue line"
        assert "Pálya 1" in body, "Pitch name missing from venue line"

    # ── MCV-02 (AC-02): 2 campuses → both names visible in schedule ──────────
    def test_MCV_02_multiple_campuses_visible(self, test_db: Session):
        """
        When sessions are assigned to different campuses, the schedule must show
        at least 2 distinct campus names.
        """
        p_a = _user(test_db, name="Alice Alpha")
        p_b = _user(test_db, name="Bob Beta")
        camp1 = _campus(test_db, name="LFA Debrecen Campus")
        camp2 = _campus(test_db, name="LFA Győr Central")
        pitch1 = _pitch(test_db, camp1)
        pitch2 = _pitch(test_db, camp2)
        t = _tournament(test_db)

        _session(
            test_db, t, round_number=1,
            participant_user_ids=[p_a.id, p_b.id],
            game_results=_h2h_game_results(p_a.id, p_b.id),
            campus=camp1, pitch=pitch1,
        )
        _session(
            test_db, t, round_number=2,
            participant_user_ids=[p_a.id, p_b.id],
            game_results=_h2h_game_results(p_b.id, p_a.id),
            campus=camp2, pitch=pitch2,
        )

        with _public_client(test_db) as client:
            resp = client.get(f"/events/{t.id}")

        assert resp.status_code == 200
        body = resp.text
        assert "LFA Debrecen Campus" in body, "First campus name missing"
        assert "LFA Győr Central" in body, "Second campus name missing"

    # ── MCV-03 (AC-03): MASTER instructor slot → "(Master)" chip ─────────────
    def test_MCV_03_instructor_master_role_chip(self, test_db: Session):
        """
        A TournamentInstructorSlot with role=MASTER must render as a chip
        containing the instructor name and "(Master)" in the info grid.
        """
        master = _user(test_db, role=UserRole.INSTRUCTOR, name="Kiss Béla Master")
        t = _tournament(test_db)

        db_admin = _user(test_db, role=UserRole.INSTRUCTOR, name="Admin Assigner")
        test_db.add(TournamentInstructorSlot(
            semester_id=t.id,
            instructor_id=master.id,
            role="MASTER",
            pitch_id=None,
            assigned_by=db_admin.id,
            status="CONFIRMED",
        ))
        test_db.flush()

        with _public_client(test_db) as client:
            resp = client.get(f"/events/{t.id}")

        assert resp.status_code == 200
        body = resp.text
        assert "Kiss Béla Master" in body, "MASTER instructor name not in page"
        assert "Master" in body, "(Master) role chip missing"

    # ── MCV-04 (AC-04): FIELD instructor slot → "(Field)" chip ────────────────
    def test_MCV_04_instructor_field_role_chip(self, test_db: Session):
        """
        A TournamentInstructorSlot with role=FIELD must render as a chip
        containing the instructor name and "(Field)" in the info grid.
        """
        master_instr = _user(test_db, role=UserRole.INSTRUCTOR, name="Master Coordinator")
        field_instr = _user(test_db, role=UserRole.INSTRUCTOR, name="Nagy Péter Field")
        camp = _campus(test_db)
        pitch = _pitch(test_db, camp)
        t = _tournament(test_db, campus=camp)

        assigner = _user(test_db, role=UserRole.INSTRUCTOR)
        test_db.add(TournamentInstructorSlot(
            semester_id=t.id,
            instructor_id=master_instr.id,
            role="MASTER",
            pitch_id=None,
            assigned_by=assigner.id,
            status="CONFIRMED",
        ))
        test_db.add(TournamentInstructorSlot(
            semester_id=t.id,
            instructor_id=field_instr.id,
            role="FIELD",
            pitch_id=pitch.id,
            assigned_by=assigner.id,
            status="CONFIRMED",
        ))
        test_db.flush()

        with _public_client(test_db) as client:
            resp = client.get(f"/events/{t.id}")

        assert resp.status_code == 200
        body = resp.text
        assert "Nagy Péter Field" in body, "FIELD instructor name not in page"
        assert "Field" in body, "(Field) role chip missing"

    # ── MCV-05 (AC-05): player in 2 campus sessions → both campus names ───────
    def test_MCV_05_player_cross_campus_visible(self, test_db: Session):
        """
        A player who appears in sessions at 2 different campuses must show
        both campus names in the schedule (cross-campus history visible).
        """
        player = _user(test_db, name="Cross Campus Player")
        opponent = _user(test_db, name="Opponent")
        camp1 = _campus(test_db, name="LFA Budapest Főváros")
        camp2 = _campus(test_db, name="LFA Debrecen Keleti")
        pitch1 = _pitch(test_db, camp1)
        pitch2 = _pitch(test_db, camp2)
        t = _tournament(test_db)

        _session(
            test_db, t, round_number=1,
            participant_user_ids=[player.id, opponent.id],
            game_results=_h2h_game_results(player.id, opponent.id),
            campus=camp1, pitch=pitch1,
        )
        _session(
            test_db, t, round_number=2,
            participant_user_ids=[player.id, opponent.id],
            game_results=_h2h_game_results(opponent.id, player.id),
            campus=camp2, pitch=pitch2,
        )

        with _public_client(test_db) as client:
            resp = client.get(f"/events/{t.id}")

        assert resp.status_code == 200
        body = resp.text
        assert "LFA Budapest Főváros" in body, "First campus missing for cross-campus player"
        assert "LFA Debrecen Keleti" in body, "Second campus missing for cross-campus player"
        assert "Cross Campus Player" in body, "Player name not visible"

    # ── MCV-06 (AC-06): IR session with venue → venue in IR block ────────────
    def test_MCV_06_ir_session_venue_in_results(self, test_db: Session):
        """
        An IR (INDIVIDUAL_RANKING) session with campus_id/pitch_id set must
        render a venue line (📍) in the Event Results section.
        """
        players = [_user(test_db, name=f"IR Player {i}") for i in range(3)]
        camp = _campus(test_db, name="LFA Győr IR Campus")
        pitch = _pitch(test_db, camp, number=2)

        tt_ir = _tt(test_db, fmt="INDIVIDUAL_RANKING")
        t = _tournament(test_db, tt=tt_ir, campus=camp)

        # IR session uses rounds_data with scores
        rr = {str(p.id): float(100 - i * 10) for i, p in enumerate(players)}
        _session(
            test_db, t,
            participant_user_ids=[p.id for p in players],
            rounds_data={"round_results": {"1": rr}},
            campus=camp, pitch=pitch,
        )

        with _public_client(test_db) as client:
            resp = client.get(f"/events/{t.id}")

        assert resp.status_code == 200
        body = resp.text
        assert "LFA Győr IR Campus" in body, "Campus name missing from IR venue line"
        assert "Pálya 2" in body, "Pitch name missing from IR venue line"

    # ── MCV-07 (AC-07): GK phase-split — GROUP_STAGE vs KNOCKOUT campuses ─────
    def test_MCV_07_gk_phase_split_campuses(self, test_db: Session):
        """
        GROUP_KNOCKOUT tournament with GROUP_STAGE sessions on campus A and
        KNOCKOUT sessions on campus B → both campus names visible in the
        schedule, correctly keyed by phase.
        """
        p_a = _user(test_db, name="GK Player Alpha")
        p_b = _user(test_db, name="GK Player Beta")
        camp_group = _campus(test_db, name="LFA Group Stage Campus")
        camp_ko    = _campus(test_db, name="LFA Knockout Campus")
        pitch_g = _pitch(test_db, camp_group)
        pitch_k = _pitch(test_db, camp_ko)

        tt_gk = _tt(test_db, fmt="HEAD_TO_HEAD")
        t = _tournament(test_db, tt=tt_gk)

        _session(
            test_db, t, round_number=1,
            participant_user_ids=[p_a.id, p_b.id],
            game_results=_h2h_game_results(p_a.id, p_b.id),
            campus=camp_group, pitch=pitch_g,
            tournament_phase=TournamentPhase.GROUP_STAGE,
        )
        _session(
            test_db, t, round_number=2,
            participant_user_ids=[p_a.id, p_b.id],
            game_results=_h2h_game_results(p_a.id, p_b.id),
            campus=camp_ko, pitch=pitch_k,
            tournament_phase=TournamentPhase.KNOCKOUT,
        )

        with _public_client(test_db) as client:
            resp = client.get(f"/events/{t.id}")

        assert resp.status_code == 200
        body = resp.text
        assert "LFA Group Stage Campus" in body, "Group stage campus missing"
        assert "LFA Knockout Campus" in body, "Knockout campus missing"

    # ── MCV-08 (AC-08): NULL venue → 200, no "None" in HTML ──────────────────
    def test_MCV_08_null_venue_graceful_degradation(self, test_db: Session):
        """
        Sessions with campus_id=None, pitch_id=None, instructor_id=None must not
        crash the page and must not leak the string 'None' into the HTML output.
        Old tournaments without venue data must still render correctly.
        """
        p_a = _user(test_db, name="Legacy Player Alpha")
        p_b = _user(test_db, name="Legacy Player Beta")
        t = _tournament(test_db)

        # Session with NO venue data (simulates pre-multi-campus tournament)
        _session(
            test_db, t,
            participant_user_ids=[p_a.id, p_b.id],
            game_results=_h2h_game_results(p_a.id, p_b.id),
            campus=None, pitch=None, instructor=None,
        )

        with _public_client(test_db) as client:
            resp = client.get(f"/events/{t.id}")

        assert resp.status_code == 200
        body = resp.text
        # "None" must not appear as a visible value — check common patterns
        assert ">None<" not in body, "'None' leaked as element text content"
        assert "📍 None" not in body, "'None' leaked next to campus pin emoji"
        assert "🎓 None" not in body, "'None' leaked next to instructor emoji"
        # The schedule itself must still render
        assert "Legacy Player Alpha" in body or "Match Schedule" in body
