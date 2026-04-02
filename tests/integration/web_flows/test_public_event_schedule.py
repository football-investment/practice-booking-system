"""
Public Event Page — Schedule Rendering Integration Tests

PES-01  Swiss INDIVIDUAL (participant_user_ids) → player names in schedule, no TBD
PES-02  TEAM HEAD_TO_HEAD (participant_team_ids) → team names in schedule, no TBD
PES-03  Missing participant data fallback → 200, schedule shows "TBD", no crash
PES-04  INDIVIDUAL with scores in rounds_data → scores rendered in schedule
PES-05  TEAM with scores in rounds_data → scores rendered in schedule
PES-06  Multi-round INDIVIDUAL → round headers present
PES-07  Swiss INDIVIDUAL 36 players seed-replay — all names visible, no TBD
PES-08  Legacy TEAM session (participant_team_ids=None) → team names from rounds_data
PES-09  Mixed sessions: legacy (no participant_team_ids) + new (with it) → both resolve
PES-10  3-team round-robin all-legacy — exact reproduction of dev-DB regression case

PES-08/09/10 exercise the backward-compatibility fix in public_tournament.py:
old sessions had participant_team_ids=None; results were stored only as
'team_{id}' keys in rounds_data.  Before the fix all rounds showed 'TBD vs TBD'.

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
from app.models.tournament_ranking import TournamentRanking
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


def _tt(
    db: Session,
    fmt: str = "HEAD_TO_HEAD",
    ranking_type: str | None = None,
) -> TournamentType:
    """Create a TournamentType.  ranking_type explicitly sets SCORING_ONLY / WDL_BASED."""
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
        ranking_type=ranking_type,  # None → falls back to Semester.ranking_type derivation
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

    # ── PES-08: Legacy session (participant_team_ids=None) — names from rounds_data
    def test_PES_08_legacy_team_session_name_from_rounds_data(self, test_db: Session):
        """
        REGRESSION guard for the 'TBD vs TBD' bug.

        Old TEAM sessions (created before participant_team_ids was actively set
        by the session generator) have participant_team_ids=None.  Team identity
        is preserved only as 'team_{id}' keys in rounds_data.

        Before fix: route checked participant_team_ids only → empty → 'TBD vs TBD'
        After fix:  route falls back to rounds_data keys → resolves real team names.

        This test would fail on the un-patched route (returns 'TBD' instead of names).
        """
        team_a = _team(test_db, name="Legacy Alpha")
        team_b = _team(test_db, name="Legacy Beta")
        t = _tournament(test_db, participant_type="TEAM",
                        tournament_status="REWARDS_DISTRIBUTED")
        _session(
            test_db, t,
            # participant_team_ids intentionally absent — simulates legacy row
            participant_team_ids=None,
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
        html = resp.text
        assert "Match Schedule" in html
        assert "Legacy Alpha" in html, \
            "Team A name must be resolved from rounds_data keys — not 'TBD'"
        assert "Legacy Beta" in html, \
            "Team B name must be resolved from rounds_data keys — not 'TBD'"
        # Scores must also be present (3–1)
        assert "3" in html, "Score for team_a missing"
        assert "1" in html, "Score for team_b missing"
        # The regression check: TBD must NOT appear for matched rounds_data entries
        tbd_count = html.count(">TBD<")
        assert tbd_count == 0, \
            f"TBD appeared {tbd_count} time(s) — legacy team IDs were not resolved"

    # ── PES-09: Mixed legacy + new sessions in same tournament ────────────────
    def test_PES_09_mixed_legacy_and_new_sessions(self, test_db: Session):
        """
        A tournament may contain a mix:
          - Sessions with participant_team_ids populated (new generator)
          - Sessions with participant_team_ids=None (legacy / backfilled)

        Both must render correctly in the same schedule — no TBD for either.
        """
        team_a = _team(test_db, name="Mix Team A")
        team_b = _team(test_db, name="Mix Team B")
        team_c = _team(test_db, name="Mix Team C")
        t = _tournament(test_db, participant_type="TEAM",
                        tournament_status="COMPLETED")

        # Session 1: new-style — participant_team_ids populated
        _session(
            test_db, t,
            round_number=1,
            participant_team_ids=[team_a.id, team_b.id],
            rounds_data={"total_rounds": 1, "round_results": {"1": {
                f"team_{team_a.id}": "2",
                f"team_{team_b.id}": "0",
            }}},
        )
        # Session 2: legacy-style — participant_team_ids=None
        _session(
            test_db, t,
            round_number=2,
            participant_team_ids=None,
            rounds_data={"total_rounds": 1, "round_results": {"1": {
                f"team_{team_a.id}": "1",
                f"team_{team_c.id}": "1",
            }}},
        )

        with _public_client(test_db) as client:
            resp = client.get(f"/events/{t.id}")

        assert resp.status_code == 200, resp.text
        html = resp.text
        assert "Match Schedule" in html
        # All three teams must resolve from their respective sources
        assert "Mix Team A" in html, "Team A missing (should appear in both sessions)"
        assert "Mix Team B" in html, "Team B missing (new-style session)"
        assert "Mix Team C" in html, "Team C missing (legacy session)"
        # No TBD for either session
        assert html.count(">TBD<") == 0, \
            "TBD appeared — one of the sessions failed to resolve team names"

    # ── PES-10: 3-team round-robin all legacy — exact dev-DB regression scenario
    def test_PES_10_three_team_league_all_legacy(self, test_db: Session):
        """
        Exact reproduction of the failing scenario from the live dev database:

            Tournament: 'H2H League — Rewards Distributed 2026'  (id=1850)
            Sessions 5271/5272/5273: participant_team_ids=None for ALL sessions.
            Results stored as rounds_data['round_results']['1']['team_550'] etc.
            User reported: schedule showed 'TBD vs TBD' for every round.

        This test creates an identical data shape and verifies:
          - All 3 rounds display real team names and scores
          - No TBD appears in the schedule
          - The Full Results table (WDL_BASED) shows correct W/D/L columns
        """
        team_u15   = _team(test_db, name="LFA U15 (legacy)")
        team_u18   = _team(test_db, name="LFA U18 (legacy)")
        team_adult = _team(test_db, name="LFA Adult (legacy)")

        tt = _tt(test_db, fmt="HEAD_TO_HEAD", ranking_type="WDL_BASED")
        t = _tournament(test_db, participant_type="TEAM",
                        tt=tt, tournament_status="REWARDS_DISTRIBUTED")

        # 3-team round-robin: C(3,2)=3 matches, all with participant_team_ids=None
        matches = [
            (team_u15, team_u18,   "3", "2"),   # Round 1
            (team_u15, team_adult, "2", "3"),   # Round 2
            (team_u18, team_adult, "2", "3"),   # Round 3
        ]
        for rnd, (ta, tb, sa, sb) in enumerate(matches, 1):
            _session(
                test_db, t,
                round_number=rnd,
                participant_team_ids=None,   # ← legacy: no participant_team_ids
                rounds_data={"total_rounds": 1, "round_results": {"1": {
                    f"team_{ta.id}": sa,
                    f"team_{tb.id}": sb,
                }}},
            )

        # Add WDL_BASED rankings to trigger 'Full Results' display
        from app.models.tournament_ranking import TournamentRanking as TR
        for rank, (team, pts, w, d, l, gf, ga) in enumerate([
            (team_adult, 6, 2, 0, 0, 6, 4),
            (team_u15,   3, 1, 0, 1, 5, 5),
            (team_u18,   0, 0, 0, 2, 4, 6),
        ], 1):
            test_db.add(TR(
                tournament_id=t.id, team_id=team.id,
                participant_type="TEAM",
                rank=rank, points=float(pts),
                wins=w, draws=d, losses=l,
                goals_for=gf, goals_against=ga,
            ))
        test_db.flush()

        with _public_client(test_db) as client:
            resp = client.get(f"/events/{t.id}")

        assert resp.status_code == 200, resp.text
        html = resp.text

        # ── Schedule section ──────────────────────────────────────────────────
        assert "Match Schedule" in html
        # All 3 rounds must show real team names, not TBD
        assert "LFA U15 (legacy)"   in html, "U15 name missing from schedule"
        assert "LFA U18 (legacy)"   in html, "U18 name missing from schedule"
        assert "LFA Adult (legacy)" in html, "Adult name missing from schedule"
        assert html.count(">TBD<") == 0, \
            "TBD appeared — legacy team IDs not resolved from rounds_data"

        # Score spot-checks: Round 1 = 3–2, Round 3 = 2–3
        assert "3" in html, "Score '3' missing from schedule"
        assert "2" in html, "Score '2' missing from schedule"

        # Round headers: 3 rounds
        for r in range(1, 4):
            assert f"Round {r}" in html, f"Round {r} header missing"

        # ── Full Results table (WDL_BASED) ────────────────────────────────────
        assert "Full Results" in html, "Full Results section missing"
        assert ">W<" in html, "W column missing (WDL_BASED)"
        assert ">D<" in html, "D column missing (WDL_BASED)"
        assert ">L<" in html, "L column missing (WDL_BASED)"
        assert "LFA Adult (legacy)" in html, "Leader team missing from Full Results"

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


# ─────────────────────────────────────────────────────────────────────────────
# Full Results / Rankings presentation layer tests
#
# FR-01  Swiss INDIVIDUAL: rankings exist, W/D/L all zero → W/D/L cols hidden
# FR-02  Group Knockout INDIVIDUAL: rankings have W/D/L → W/D/L cols shown
# FR-03  COMPLETED event with sessions but no rankings → standings-pending placeholder
# FR-04  Full Results title only on COMPLETED/REWARDS_DISTRIBUTED
# FR-05  INDIVIDUAL H2H: rank, name, pts-badge all present for each row
# ─────────────────────────────────────────────────────────────────────────────

def _ranking(
    db: Session,
    tournament_id: int,
    user_id: int,
    rank: int,
    points: float,
    wins: int = 0,
    draws: int = 0,
    losses: int = 0,
    goals_for: int = 0,
    goals_against: int = 0,
) -> TournamentRanking:
    row = TournamentRanking(
        tournament_id=tournament_id,
        user_id=user_id,
        participant_type="INDIVIDUAL",
        rank=rank,
        points=points,
        wins=wins,
        draws=draws,
        losses=losses,
        goals_for=goals_for,
        goals_against=goals_against,
    )
    db.add(row)
    db.flush()
    return row


class TestFullResultsPresentation:
    """
    FR tests use EXPLICIT ranking_type on TournamentType, not ad-hoc value inspection.
    The UI should read domain state, never infer it from raw W/D/L field values.
    """

    # ── FR-01: SCORING_ONLY → W/D/L columns absent ───────────────────────────
    def test_FR_01_scoring_only_no_wdl_columns(self, test_db: Session):
        """
        TournamentType with ranking_type=SCORING_ONLY (Swiss, IR).
        The Full Results table must NOT render W/D/L/GF/GA columns.
        Regression: ad-hoc check on zero W/D/L values was fragile; now the
        domain flag drives the decision unconditionally.
        """
        tt = _tt(test_db, fmt="HEAD_TO_HEAD", ranking_type="SCORING_ONLY")
        t = _tournament(test_db, participant_type="INDIVIDUAL", tt=tt,
                        tournament_status="REWARDS_DISTRIBUTED")
        p1 = _player(test_db, name="Swiss Winner")
        p2 = _player(test_db, name="Swiss Runner")
        _ranking(test_db, t.id, p1.id, rank=1, points=100.0)
        _ranking(test_db, t.id, p2.id, rank=2, points=98.0)

        with _public_client(test_db) as client:
            resp = client.get(f"/events/{t.id}")

        assert resp.status_code == 200, resp.text
        html = resp.text
        # standings_state=FINAL → "Full Results" title
        assert "Full Results" in html, "Full Results title missing"
        assert "Swiss Winner" in html, "Rank-1 player name missing"
        assert "Swiss Runner" in html, "Rank-2 player name missing"
        assert "100" in html
        assert "98" in html
        # W/D/L column headers must NOT appear — driven by ranking_type, not data
        assert ">W<" not in html, "W column must be absent for SCORING_ONLY"
        assert ">D<" not in html, "D column must be absent for SCORING_ONLY"
        assert ">L<" not in html, "L column must be absent for SCORING_ONLY"

    # ── FR-02: WDL_BASED → W/D/L columns present ─────────────────────────────
    def test_FR_02_wdl_based_columns_shown(self, test_db: Session):
        """
        TournamentType with ranking_type=WDL_BASED (League, Group Knockout).
        The Full Results table MUST render W/D/L/GF/GA columns.
        The decision is driven by the domain flag, not by inspecting row values.
        """
        tt = _tt(test_db, fmt="HEAD_TO_HEAD", ranking_type="WDL_BASED")
        t = _tournament(test_db, participant_type="INDIVIDUAL", tt=tt,
                        tournament_status="COMPLETED")
        p1 = _player(test_db, name="GK Alpha")
        p2 = _player(test_db, name="GK Beta")
        _ranking(test_db, t.id, p1.id, rank=1, points=9.0,
                 wins=3, draws=0, losses=0, goals_for=9, goals_against=2)
        _ranking(test_db, t.id, p2.id, rank=2, points=6.0,
                 wins=2, draws=0, losses=1, goals_for=6, goals_against=4)

        with _public_client(test_db) as client:
            resp = client.get(f"/events/{t.id}")

        assert resp.status_code == 200, resp.text
        html = resp.text
        assert "Full Results" in html
        assert "GK Alpha" in html
        # W/D/L column headers must appear — driven by ranking_type=WDL_BASED
        assert ">W<" in html, "W column header missing for WDL_BASED"
        assert ">D<" in html, "D column header missing for WDL_BASED"
        assert ">L<" in html, "L column header missing for WDL_BASED"

    # ── FR-03: standings_state=PENDING → placeholder visible ─────────────────
    def test_FR_03_standings_state_pending_shows_placeholder(self, test_db: Session):
        """
        standings_state=PENDING: sessions exist but no TournamentRanking rows.
        The UI must render a 'Current Standings' placeholder — not silently hide
        the section. Before the fix, users saw match scores in the schedule but
        no standings section at all.
        """
        tt = _tt(test_db, fmt="HEAD_TO_HEAD", ranking_type="SCORING_ONLY")
        t = _tournament(test_db, participant_type="INDIVIDUAL", tt=tt,
                        tournament_status="IN_PROGRESS")
        p1 = _player(test_db, name="Pending Player A")
        p2 = _player(test_db, name="Pending Player B")
        _session(test_db, t,
                 participant_user_ids=[p1.id, p2.id],
                 rounds_data={"round_results": {"1": {str(p1.id): 5, str(p2.id): 3}}})
        # No TournamentRanking rows → standings_state = PENDING

        with _public_client(test_db) as client:
            resp = client.get(f"/events/{t.id}")

        assert resp.status_code == 200, resp.text
        html = resp.text
        assert "Match Schedule" in html
        assert "Pending Player A" in html
        # standings_state=PENDING placeholder
        assert "Current Standings" in html, \
            "Standings placeholder missing for standings_state=PENDING"
        assert "Rankings will be published" in html, \
            "Pending message missing"

    # ── FR-04: standings_state drives section title ───────────────────────────
    def test_FR_04_standings_state_drives_title(self, test_db: Session):
        """
        standings_state=FINAL  → '📋 Full Results'   (COMPLETED / REWARDS_DISTRIBUTED)
        standings_state=LIVE   → '📊 Current Standings' (IN_PROGRESS)
        Title is driven by standings_state, not raw status string comparison.
        """
        tt = _tt(test_db, fmt="HEAD_TO_HEAD", ranking_type="SCORING_ONLY")

        for status, expected_title in [
            ("COMPLETED",           "Full Results"),
            ("REWARDS_DISTRIBUTED", "Full Results"),
            ("IN_PROGRESS",         "Current Standings"),
        ]:
            t = _tournament(test_db, participant_type="INDIVIDUAL", tt=tt,
                            tournament_status=status)
            p = _player(test_db, name=f"Title Player {status}")
            _ranking(test_db, t.id, p.id, rank=1, points=50.0)

            with _public_client(test_db) as client:
                resp = client.get(f"/events/{t.id}")

            assert resp.status_code == 200
            assert expected_title in resp.text, \
                f"Expected '{expected_title}' for status={status} (standings_state mapping)"

    # ── FR-05: Every ranking row renders rank, name, pts-badge ────────────────
    def test_FR_05_ranking_rows_render_correctly(self, test_db: Session):
        """
        Each TournamentRanking row must appear as a table row with:
        - rank number / medal emoji
        - player name
        - pts-badge with correct integer value
        """
        tt = _tt(test_db, fmt="HEAD_TO_HEAD", ranking_type="SCORING_ONLY")
        t = _tournament(test_db, participant_type="INDIVIDUAL", tt=tt,
                        tournament_status="REWARDS_DISTRIBUTED")
        players = [_player(test_db, name=f"FR Player {i}") for i in range(1, 4)]
        for i, p in enumerate(players, 1):
            _ranking(test_db, t.id, p.id, rank=i, points=float(100 - (i - 1) * 10))

        with _public_client(test_db) as client:
            resp = client.get(f"/events/{t.id}")

        assert resp.status_code == 200, resp.text
        html = resp.text
        assert "Full Results" in html
        for i, p in enumerate(players, 1):
            assert f"FR Player {i}" in html, f"Rank-{i} player name missing"
        # Points: 100, 90, 80
        assert "100" in html
        assert "90" in html
        assert "80" in html
        # Medal emojis for top 3
        assert "🥇" in html
        assert "🥈" in html
        assert "🥉" in html
