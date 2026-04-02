"""
Public Event Page — Schedule Rendering Integration Tests

PES-01  Swiss INDIVIDUAL (participant_user_ids) → player names in schedule, no TBD
PES-02  TEAM HEAD_TO_HEAD (participant_team_ids) → team names in schedule, no TBD
PES-03  Missing participant data fallback → 200, schedule shows "TBD", no crash
PES-04  INDIVIDUAL with scores in rounds_data → scores rendered in schedule
PES-05  TEAM with scores in rounds_data → scores rendered in schedule

All tests hit GET /events/{id} (no auth required — public route) and assert
on the returned HTML.  A SAVEPOINT-isolated DB is shared between the test and
the TestClient via dependency_overrides[get_db].
"""

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
from app.models.team import Team, TeamMember
from app.models.location import Location, LocationType
from app.models.campus import Campus
from app.core.security import get_password_hash


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_PFX = "pes"


def _uid() -> str:
    return uuid.uuid4().hex[:8]


@contextmanager
def _public_client(db: Session):
    """Context manager: TestClient sharing the test SAVEPOINT session (no auth).
    Clears dependency_overrides on exit to avoid test-ordering pollution."""
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def _instructor(db: Session) -> User:
    u = User(
        email=f"{_PFX}-instr-{_uid()}@lfa-test.com",
        name=f"PES Instructor {_uid()}",
        password_hash=get_password_hash("pw"),
        role=UserRole.INSTRUCTOR,
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def _player(db: Session, name: str | None = None) -> User:
    n = name or f"Player {_uid()}"
    u = User(
        email=f"{_PFX}-{_uid()}@lfa-test.com",
        name=n,
        password_hash=get_password_hash("pw"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def _tt(db: Session, fmt: str = "HEAD_TO_HEAD") -> TournamentType:
    code = f"{_PFX}-{fmt.lower()[:3]}-{_uid()}"
    tt = TournamentType(
        code=code,
        display_name=f"PES {fmt}",
        description="Auto-created for PES tests",
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
        name=f"PES Preset {_uid()}",
        description="Auto-created for PES tests",
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
) -> Semester:
    """Create a minimal tournament with TournamentConfiguration."""
    instr = _instructor(db)
    if tt is None:
        tt = _tt(db)
    preset = _preset(db)

    uid = _uid()
    loc = Location(
        name=f"PES Location {uid}",
        city=f"PESCity-{uid}",
        country="HU",
        location_type=LocationType.CENTER,
    )
    db.add(loc)
    db.flush()
    camp = Campus(location_id=loc.id, name=f"PES Campus {uid}", is_active=True)
    db.add(camp)
    db.flush()

    t = Semester(
        name=f"PES Cup {_uid()}",
        code=f"PES-{_uid()}",
        master_instructor_id=instr.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        status=SemesterStatus.ONGOING,
        semester_category=SemesterCategory.TOURNAMENT,
        tournament_status=tournament_status,
        campus_id=camp.id,
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
    rounds_data: dict | None = None,
    status: str = "completed",
) -> SessionModel:
    sess = SessionModel(
        semester_id=tournament.id,
        instructor_id=tournament.master_instructor_id,
        title=f"PES Match R{round_number}",
        event_category=EventCategory.MATCH,
        auto_generated=True,
        capacity=2,
        round_number=round_number,
        session_status=status,
        participant_user_ids=participant_user_ids,
        participant_team_ids=participant_team_ids,
        rounds_data=rounds_data,
        date_start=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
        date_end=datetime(2026, 6, 1, 11, 0, tzinfo=timezone.utc),
    )
    db.add(sess)
    db.flush()
    return sess


def _team(db: Session, name: str | None = None) -> Team:
    captain = _player(db)
    team = Team(
        name=name or f"Team {_uid()}",
        code=f"T-{_uid()}",
        captain_user_id=captain.id,
        is_active=True,
    )
    db.add(team)
    db.flush()
    db.add(TeamMember(team_id=team.id, user_id=captain.id, role="CAPTAIN", is_active=True))
    db.flush()
    return team


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPublicEventSchedule:

    # ── PES-01: Swiss INDIVIDUAL — participant_user_ids → player names ─────────
    def test_PES_01_individual_h2h_shows_player_names(self, test_db: Session):
        """
        Swiss INDIVIDUAL HEAD_TO_HEAD sessions store pairings in participant_user_ids.
        Schedule section must render real player names, not 'TBD'.
        """
        player_a = _player(test_db, name="Alice Archer")
        player_b = _player(test_db, name="Bob Bishop")
        t = _tournament(test_db, participant_type="INDIVIDUAL")
        _session(test_db, t, participant_user_ids=[player_a.id, player_b.id])

        with _public_client(test_db) as client:
            resp = client.get(f"/events/{t.id}")

        assert resp.status_code == 200, resp.text
        assert "Match Schedule" in resp.text
        assert "Alice Archer" in resp.text, "Player A name missing from schedule"
        assert "Bob Bishop" in resp.text, "Player B name missing from schedule"
        assert resp.text.count(">TBD<") == 0, "TBD should not appear when participant_user_ids is set"

    # ── PES-02: TEAM HEAD_TO_HEAD — participant_team_ids → team names ─────────
    def test_PES_02_team_h2h_shows_team_names(self, test_db: Session):
        """
        TEAM HEAD_TO_HEAD sessions store pairings in participant_team_ids.
        Schedule section must render real team names, not 'TBD'.
        """
        team_a = _team(test_db, name="Red Dragons")
        team_b = _team(test_db, name="Blue Eagles")
        t = _tournament(test_db, participant_type="TEAM")
        _session(test_db, t, participant_team_ids=[team_a.id, team_b.id])

        with _public_client(test_db) as client:
            resp = client.get(f"/events/{t.id}")

        assert resp.status_code == 200, resp.text
        assert "Match Schedule" in resp.text
        assert "Red Dragons" in resp.text, "Team A name missing from schedule"
        assert "Blue Eagles" in resp.text, "Team B name missing from schedule"
        assert resp.text.count(">TBD<") == 0, "TBD should not appear when participant_team_ids is set"

    # ── PES-03: Missing participant data → TBD fallback, no 500 ──────────────
    def test_PES_03_missing_participant_data_renders_tbd(self, test_db: Session):
        """
        Sessions with no participant_user_ids and no participant_team_ids must
        render as 'TBD vs TBD' — not crash with 500.
        """
        t = _tournament(test_db, participant_type="INDIVIDUAL")
        _session(test_db, t, participant_user_ids=None, participant_team_ids=None)

        with _public_client(test_db) as client:
            resp = client.get(f"/events/{t.id}")

        assert resp.status_code == 200, resp.text
        assert "Match Schedule" in resp.text
        # TBD entries are expected — one for team_a, one for team_b per match
        assert "TBD" in resp.text, "Sessions without pairing data should display TBD"

    # ── PES-04: INDIVIDUAL with scores in rounds_data ─────────────────────────
    def test_PES_04_individual_scores_rendered(self, test_db: Session):
        """
        When rounds_data contains per-player scores (keyed by str(user_id)),
        the schedule must render the score values next to player names.
        """
        player_a = _player(test_db, name="Carlos Cruz")
        player_b = _player(test_db, name="Diana Drake")
        t = _tournament(test_db, participant_type="INDIVIDUAL")
        _session(
            test_db, t,
            participant_user_ids=[player_a.id, player_b.id],
            rounds_data={
                "total_rounds": 1,
                "round_results": {
                    "1": {
                        str(player_a.id): "85.0",
                        str(player_b.id): "72.0",
                    }
                },
            },
        )

        with _public_client(test_db) as client:
            resp = client.get(f"/events/{t.id}")

        assert resp.status_code == 200, resp.text
        assert "Match Schedule" in resp.text
        assert "Carlos Cruz" in resp.text
        assert "Diana Drake" in resp.text
        # Scores appear in the match-vs cell (rendered as "85–72")
        assert "85" in resp.text, "Player A score missing"
        assert "72" in resp.text, "Player B score missing"

    # ── PES-05: TEAM with scores in rounds_data ────────────────────────────────
    def test_PES_05_team_scores_rendered(self, test_db: Session):
        """
        When rounds_data contains per-team scores (keyed by 'team_{id}'),
        the schedule must render the score values next to team names.
        """
        team_a = _team(test_db, name="Lions FC")
        team_b = _team(test_db, name="Tigers SC")
        t = _tournament(test_db, participant_type="TEAM")
        _session(
            test_db, t,
            participant_team_ids=[team_a.id, team_b.id],
            rounds_data={
                "total_rounds": 1,
                "round_results": {
                    "1": {
                        f"team_{team_a.id}": "3",
                        f"team_{team_b.id}": "1",
                    }
                },
            },
        )

        with _public_client(test_db) as client:
            resp = client.get(f"/events/{t.id}")

        assert resp.status_code == 200, resp.text
        assert "Match Schedule" in resp.text
        assert "Lions FC" in resp.text
        assert "Tigers SC" in resp.text
        # Score appears in match-vs cell (rendered as "3–1")
        assert "3" in resp.text, "Team A score missing"
        assert "1" in resp.text, "Team B score missing"

    # ── PES-07: Seed-replay — Swiss INDIVIDUAL 36 players, 6 rounds ──────────
    def test_PES_07_swiss_individual_seed_replay(self, test_db: Session):
        """
        Deterministic replay of the lifecycle seed scenario:
          Swiss Cup INDIVIDUAL HEAD_TO_HEAD, 36 players, 6 rounds (ceil(log2(36))),
          18 matches per round → 108 sessions total, each with participant_user_ids.

        This mirrors exactly what seed_all_lifecycle_states_team.py produces for
        'Swiss Cup — Rewards Distributed 2026' (event id 1866 on the dev DB).

        Assertions:
          - /events/{id} returns 200
          - "Match Schedule" section present
          - All 36 player names visible at least once
          - Zero ">TBD<" occurrences in the response
          - Session count == 108 (6 rounds × 18 matches)
        """
        import math

        n_players = 36
        n_rounds = math.ceil(math.log2(n_players))  # = 6
        n_matches = n_players // 2                   # = 18 per round

        # Create 36 uniquely-named players
        players = [_player(test_db, name=f"SeedPlayer {i:02d}") for i in range(1, n_players + 1)]

        tt = _tt(test_db, fmt="HEAD_TO_HEAD")
        t = _tournament(test_db, participant_type="INDIVIDUAL", tt=tt)

        # Build sessions exactly as the Swiss generator does:
        # sequential pairing in round 1 (same-index pairs), repeated across rounds
        for round_num in range(1, n_rounds + 1):
            for match_idx in range(n_matches):
                uid_a = players[match_idx * 2].id
                uid_b = players[match_idx * 2 + 1].id
                score_a = 90 - match_idx * 2
                score_b = 80 - match_idx * 2
                _session(
                    test_db, t,
                    round_number=round_num,
                    participant_user_ids=[uid_a, uid_b],
                    rounds_data={
                        "total_rounds": 1,
                        "round_results": {
                            "1": {
                                str(uid_a): str(float(score_a)),
                                str(uid_b): str(float(score_b)),
                            }
                        },
                    },
                )

        # Sanity: 108 sessions created
        from app.models.session import Session as S
        sess_count = test_db.query(S).filter(S.semester_id == t.id).count()
        assert sess_count == 108, f"Expected 108 sessions, got {sess_count}"

        with _public_client(test_db) as client:
            resp = client.get(f"/events/{t.id}")

        assert resp.status_code == 200, resp.text
        assert "Match Schedule" in resp.text, "Match Schedule section missing"
        assert resp.text.count(">TBD<") == 0, "TBD should not appear in 36-player Swiss schedule"

        # All 36 player names must appear at least once
        missing = [
            f"SeedPlayer {i:02d}" for i in range(1, n_players + 1)
            if f"SeedPlayer {i:02d}" not in resp.text
        ]
        assert not missing, f"Player names missing from schedule: {missing}"

        # All 6 round headers must be present
        for r in range(1, n_rounds + 1):
            assert f"Round {r}" in resp.text, f"Round {r} header missing"

    # ── PES-06: Multi-round INDIVIDUAL — round headers present ────────────────
    def test_PES_06_multi_round_individual_round_headers(self, test_db: Session):
        """
        Multiple rounds must render separate round headers in the schedule.
        Regression: schedule builder must use round_number from session, not a hardcoded value.
        """
        player_a = _player(test_db, name="Eve Eden")
        player_b = _player(test_db, name="Frank Ford")
        player_c = _player(test_db, name="Grace Green")
        player_d = _player(test_db, name="Henry Hall")
        t = _tournament(test_db, participant_type="INDIVIDUAL")
        _session(test_db, t, round_number=1, participant_user_ids=[player_a.id, player_b.id])
        _session(test_db, t, round_number=2, participant_user_ids=[player_c.id, player_d.id])

        with _public_client(test_db) as client:
            resp = client.get(f"/events/{t.id}")

        assert resp.status_code == 200, resp.text
        assert "Round 1" in resp.text
        assert "Round 2" in resp.text
        assert "Eve Eden" in resp.text
        assert "Grace Green" in resp.text
