"""
Integration tests — Multi-campus round-robin session assignment

Validates the campus infrastructure refactoring (2026-02-18):
  1. pick_campus() round-robin logic
  2. Every session produced by each format generator carries a campus_id
     when campus_ids are provided
  3. Round-robin distribution is correct (sessions rotate through campuses)
  4. No campus_id when campus_ids is empty/None (backward-compat)
  5. OpsScenarioRequest rejects missing campus_ids (ValidationError)
  6. status_validator rejects ENROLLMENT_OPEN without campus_id

DB-free: all generators are called with mock DB / tournament objects.

Test matrix:
  R-01  pick_campus — round-robin with 3 campuses
  R-02  pick_campus — single campus (index always 0)
  R-03  pick_campus — empty/None → returns None
  L-01  LeagueGenerator (INDIVIDUAL_RANKING) — 3 campuses, 4 rounds
        → all sessions have campus_id, round-robin distribution
  L-02  LeagueGenerator (HEAD_TO_HEAD) — 3 campuses, 4 players
        → all sessions have campus_id, round-robin distribution
  K-01  KnockoutGenerator — 3 campuses, 8 players
        → all sessions have campus_id
  K-02  KnockoutGenerator + 3rd-place playoff — campus_id present
  S-01  SwissGenerator (HEAD_TO_HEAD) — 3 campuses, 4 players
        → all sessions have campus_id
  S-02  SwissGenerator (INDIVIDUAL_RANKING) — 3 campuses, 8 players
        → all sessions have campus_id
  IR-01 IndividualRankingGenerator — 3 campuses, 1 round
        → single session has campus_id == campus_ids[0]
  BC-01 Backward-compat: campus_ids=None → campus_id is None in all sessions
  BC-02 Backward-compat: campus_ids=[]   → campus_id is None in all sessions
  OPS-1 OpsScenarioRequest without campus_ids → pydantic.ValidationError
  OPS-2 OpsScenarioRequest with campus_ids=[1,2] → no error
  SV-01 status_validator: ENROLLMENT_OPEN without campus_id → False
  SV-02 status_validator: ENROLLMENT_OPEN with campus_id    → passes campus check
"""

import pytest
from collections import Counter
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

# ─── Helpers ──────────────────────────────────────────────────────────────────

CAMPUS_IDS_3 = [101, 202, 303]
START_DATE = datetime(2026, 3, 1, 9, 0)


def _enrollment(user_id: int):
    return SimpleNamespace(
        id=user_id * 100,
        user_id=user_id,
        semester_id=1,
        is_active=True,
        request_status="approved",
        tournament_checked_in_at=None,
    )


def _tournament(
    format_: str = "INDIVIDUAL_RANKING",
    scoring_type: str = "SCORE_BASED",
    campus_id=None,
):
    return SimpleNamespace(
        id=1,
        name="Test Cup",
        start_date=START_DATE,
        format=format_,
        scoring_type=scoring_type,
        campus=None,
        location=None,
        campus_id=campus_id,
        master_instructor_id=99,
        max_players=32,
        enrollments=[],
    )


def _tournament_type(code: str = "league"):
    config = {
        "league": {"ranking_rounds": 3, "round_names": {}},
        "knockout": {"round_names": {}, "third_place_playoff": False},
        "knockout_3p": {"round_names": {}, "third_place_playoff": True},
        "swiss": {"pod_size": 4, "round_names": {}},
    }.get(code, {})
    return SimpleNamespace(
        id=1,
        code=code,
        config=config,
        min_players=2,
    )


def _build_db(player_ids: list) -> MagicMock:
    """Minimal mock DB serving SemesterEnrollment.filter().all()"""
    enrollments = [_enrollment(uid) for uid in player_ids]

    mock_db = MagicMock()

    def _query(model):
        q = MagicMock()
        inner = MagicMock()
        inner.filter.return_value = inner
        inner.order_by.return_value = inner
        inner.all.return_value = enrollments
        inner.count.return_value = len(enrollments)
        q.filter.return_value = inner
        return q

    mock_db.query.side_effect = _query
    return mock_db


# ─── pick_campus unit tests ───────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestPickCampus:
    """R-01 through R-03"""

    def test_round_robin_3_campuses(self):
        """R-01: 7 sessions across 3 campuses → correct rotation."""
        from app.services.tournament.session_generation.utils import pick_campus
        expected = [101, 202, 303, 101, 202, 303, 101]
        result = [pick_campus(i, CAMPUS_IDS_3) for i in range(7)]
        assert result == expected

    def test_single_campus_always_same(self):
        """R-02: single campus → every session gets that campus."""
        from app.services.tournament.session_generation.utils import pick_campus
        for i in range(5):
            assert pick_campus(i, [42]) == 42

    def test_none_campus_ids(self):
        """R-03a: campus_ids=None → None."""
        from app.services.tournament.session_generation.utils import pick_campus
        assert pick_campus(0, None) is None

    def test_empty_campus_ids(self):
        """R-03b: campus_ids=[] → None."""
        from app.services.tournament.session_generation.utils import pick_campus
        assert pick_campus(0, []) is None


# ─── LeagueGenerator ─────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestLeagueGeneratorMultiCampus:
    """L-01 and L-02"""

    def _make_generator(self, player_ids):
        from app.services.tournament.session_generation.formats.league_generator import LeagueGenerator
        db = _build_db(player_ids)
        gen = LeagueGenerator(db)
        return gen

    def test_individual_ranking_all_sessions_have_campus_id(self):
        """L-01: INDIVIDUAL_RANKING + 3 campuses → every session has campus_id."""
        player_ids = list(range(1, 5))
        gen = self._make_generator(player_ids)
        t = _tournament(format_="INDIVIDUAL_RANKING")
        tt = _tournament_type("league")  # config has ranking_rounds=3

        sessions = gen.generate(
            tournament=t,
            tournament_type=tt,
            player_count=4,
            parallel_fields=1,
            session_duration=60,
            break_minutes=10,
            campus_ids=CAMPUS_IDS_3,
        )

        assert len(sessions) > 0, "Expected at least 1 session"
        for s in sessions:
            assert "campus_id" in s, f"Missing campus_id in session: {s.get('title')}"
            assert s["campus_id"] is not None, f"campus_id is None in session: {s.get('title')}"
            assert s["campus_id"] in CAMPUS_IDS_3

    def test_individual_ranking_round_robin_distribution(self):
        """L-01b: Round-robin distribution across 3 campuses."""
        player_ids = list(range(1, 5))
        gen = self._make_generator(player_ids)
        t = _tournament(format_="INDIVIDUAL_RANKING")
        tt = _tournament_type("league")

        sessions = gen.generate(
            tournament=t,
            tournament_type=tt,
            player_count=4,
            parallel_fields=1,
            session_duration=60,
            break_minutes=10,
            campus_ids=CAMPUS_IDS_3,
        )

        counts = Counter(s["campus_id"] for s in sessions)
        # All 3 campuses must appear (with 3 rounds each campus appears once)
        assert set(counts.keys()) == set(CAMPUS_IDS_3)

    def test_head_to_head_all_sessions_have_campus_id(self):
        """L-02: HEAD_TO_HEAD league + 3 campuses → every session has campus_id."""
        player_ids = list(range(1, 5))
        gen = self._make_generator(player_ids)
        t = _tournament(format_="HEAD_TO_HEAD")
        tt = _tournament_type("league")

        sessions = gen.generate(
            tournament=t,
            tournament_type=tt,
            player_count=4,
            parallel_fields=1,
            session_duration=60,
            break_minutes=10,
            campus_ids=CAMPUS_IDS_3,
        )

        assert len(sessions) > 0
        for s in sessions:
            assert "campus_id" in s
            assert s["campus_id"] in CAMPUS_IDS_3

    def test_no_campus_ids_gives_none(self):
        """BC-01 (league): campus_ids=None → campus_id=None in all sessions."""
        player_ids = list(range(1, 5))
        gen = self._make_generator(player_ids)
        t = _tournament(format_="INDIVIDUAL_RANKING")
        tt = _tournament_type("league")

        sessions = gen.generate(
            tournament=t,
            tournament_type=tt,
            player_count=4,
            parallel_fields=1,
            session_duration=60,
            break_minutes=10,
            campus_ids=None,
        )

        for s in sessions:
            assert s.get("campus_id") is None, f"Expected None, got {s.get('campus_id')}"


# ─── KnockoutGenerator ───────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestKnockoutGeneratorMultiCampus:
    """K-01, K-02"""

    def _make_generator(self, player_ids):
        from app.services.tournament.session_generation.formats.knockout_generator import KnockoutGenerator
        db = _build_db(player_ids)
        return KnockoutGenerator(db)

    def test_all_sessions_have_campus_id(self):
        """K-01: 8 players, 3 campuses → all 7 sessions have campus_id."""
        player_ids = list(range(1, 9))
        gen = self._make_generator(player_ids)
        t = _tournament(format_="HEAD_TO_HEAD")
        tt = _tournament_type("knockout")

        sessions = gen.generate(
            tournament=t,
            tournament_type=tt,
            player_count=8,
            parallel_fields=1,
            session_duration=60,
            break_minutes=10,
            campus_ids=CAMPUS_IDS_3,
        )

        assert len(sessions) == 7, f"Expected 7 sessions (8-1), got {len(sessions)}"
        for s in sessions:
            assert "campus_id" in s
            assert s["campus_id"] in CAMPUS_IDS_3

    def test_third_place_playoff_has_campus_id(self):
        """K-02: third_place_playoff=True → playoff session also has campus_id."""
        player_ids = list(range(1, 5))
        gen = self._make_generator(player_ids)
        t = _tournament(format_="HEAD_TO_HEAD")
        tt = _tournament_type("knockout_3p")

        sessions = gen.generate(
            tournament=t,
            tournament_type=tt,
            player_count=4,
            parallel_fields=1,
            session_duration=60,
            break_minutes=10,
            campus_ids=CAMPUS_IDS_3,
        )

        playoff = [s for s in sessions if s.get("tournament_match_number") == 999]
        assert len(playoff) == 1, "Expected exactly 1 3rd-place playoff session"
        assert playoff[0]["campus_id"] in CAMPUS_IDS_3

    def test_no_campus_ids_gives_none(self):
        """BC-01 (knockout): campus_ids=None → all campus_id=None."""
        player_ids = list(range(1, 5))
        gen = self._make_generator(player_ids)
        t = _tournament(format_="HEAD_TO_HEAD")
        tt = _tournament_type("knockout")

        sessions = gen.generate(
            tournament=t,
            tournament_type=tt,
            player_count=4,
            parallel_fields=1,
            session_duration=60,
            break_minutes=10,
            campus_ids=None,
        )

        for s in sessions:
            assert s.get("campus_id") is None

    def test_round_robin_distribution_knockout(self):
        """K-01b: 8 players, 3 campuses → round-robin assignment (index-based)."""
        player_ids = list(range(1, 9))
        gen = self._make_generator(player_ids)
        t = _tournament(format_="HEAD_TO_HEAD")
        tt = _tournament_type("knockout")

        sessions = gen.generate(
            tournament=t,
            tournament_type=tt,
            player_count=8,
            parallel_fields=1,
            session_duration=60,
            break_minutes=10,
            campus_ids=CAMPUS_IDS_3,
        )

        # Verify: session i gets campus_ids[i % 3]
        for i, s in enumerate(sessions):
            expected = CAMPUS_IDS_3[i % len(CAMPUS_IDS_3)]
            assert s["campus_id"] == expected, (
                f"Session {i}: expected campus {expected}, got {s['campus_id']}"
            )


# ─── SwissGenerator ──────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestSwissGeneratorMultiCampus:
    """S-01 and S-02"""

    def _make_generator(self, player_ids):
        from app.services.tournament.session_generation.formats.swiss_generator import SwissGenerator
        db = _build_db(player_ids)
        return SwissGenerator(db)

    def test_head_to_head_all_sessions_have_campus_id(self):
        """S-01: HEAD_TO_HEAD swiss, 3 campuses → all sessions have campus_id."""
        player_ids = list(range(1, 5))
        gen = self._make_generator(player_ids)
        t = _tournament(format_="HEAD_TO_HEAD")
        tt = _tournament_type("swiss")

        sessions = gen.generate(
            tournament=t,
            tournament_type=tt,
            player_count=4,
            parallel_fields=1,
            session_duration=60,
            break_minutes=10,
            campus_ids=CAMPUS_IDS_3,
        )

        assert len(sessions) > 0
        for s in sessions:
            assert "campus_id" in s
            assert s["campus_id"] in CAMPUS_IDS_3

    def test_individual_ranking_pods_all_have_campus_id(self):
        """S-02: INDIVIDUAL_RANKING swiss (pods), 3 campuses → all sessions have campus_id."""
        player_ids = list(range(1, 9))
        gen = self._make_generator(player_ids)
        t = _tournament(format_="INDIVIDUAL_RANKING")
        tt = _tournament_type("swiss")

        sessions = gen.generate(
            tournament=t,
            tournament_type=tt,
            player_count=8,
            parallel_fields=1,
            session_duration=60,
            break_minutes=10,
            campus_ids=CAMPUS_IDS_3,
        )

        assert len(sessions) > 0
        for s in sessions:
            assert "campus_id" in s
            assert s["campus_id"] in CAMPUS_IDS_3

    def test_no_campus_ids_gives_none(self):
        """BC-02 (swiss): campus_ids=[] → all campus_id=None."""
        player_ids = list(range(1, 5))
        gen = self._make_generator(player_ids)
        t = _tournament(format_="HEAD_TO_HEAD")
        tt = _tournament_type("swiss")

        sessions = gen.generate(
            tournament=t,
            tournament_type=tt,
            player_count=4,
            parallel_fields=1,
            session_duration=60,
            break_minutes=10,
            campus_ids=[],
        )

        for s in sessions:
            assert s.get("campus_id") is None


# ─── IndividualRankingGenerator ───────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestIndividualRankingGeneratorMultiCampus:
    """IR-01"""

    def _make_generator(self, player_ids):
        from app.services.tournament.session_generation.formats.individual_ranking_generator import IndividualRankingGenerator
        db = _build_db(player_ids)
        return IndividualRankingGenerator(db)

    def test_single_session_gets_first_campus(self):
        """IR-01: single session → campus_ids[0]."""
        player_ids = list(range(1, 9))
        gen = self._make_generator(player_ids)
        t = _tournament(format_="INDIVIDUAL_RANKING", scoring_type="SCORE_BASED")

        sessions = gen.generate(
            tournament=t,
            tournament_type=None,
            player_count=8,
            parallel_fields=1,
            session_duration=90,
            break_minutes=15,
            campus_ids=CAMPUS_IDS_3,
        )

        assert len(sessions) == 1
        assert sessions[0]["campus_id"] == CAMPUS_IDS_3[0]

    def test_no_campus_ids_gives_none(self):
        """BC-01 (IR): campus_ids=None → campus_id=None."""
        player_ids = list(range(1, 5))
        gen = self._make_generator(player_ids)
        t = _tournament(format_="INDIVIDUAL_RANKING", scoring_type="SCORE_BASED")

        sessions = gen.generate(
            tournament=t,
            tournament_type=None,
            player_count=4,
            parallel_fields=1,
            session_duration=90,
            break_minutes=15,
            campus_ids=None,
        )

        assert len(sessions) == 1
        assert sessions[0].get("campus_id") is None


# ─── OpsScenarioRequest schema validation ────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestOpsScenarioRequestCampusValidation:
    """OPS-1, OPS-2"""

    def test_missing_campus_ids_raises_validation_error(self):
        """OPS-1: campus_ids absent → pydantic.ValidationError."""
        import pydantic
        from app.api.api_v1.endpoints.tournaments.ops_scenario import OpsScenarioRequest

        with pytest.raises(pydantic.ValidationError) as exc_info:
            OpsScenarioRequest(
                scenario="smoke_test",
                player_count=8,
                tournament_format="HEAD_TO_HEAD",
                simulation_mode="manual",
                # campus_ids intentionally missing
            )
        err_str = str(exc_info.value)
        assert "campus_ids" in err_str, f"Expected 'campus_ids' in error, got: {err_str}"

    def test_empty_campus_ids_raises_validation_error(self):
        """OPS-1b: campus_ids=[] → ValidationError (min_length=1)."""
        import pydantic
        from app.api.api_v1.endpoints.tournaments.ops_scenario import OpsScenarioRequest

        with pytest.raises(pydantic.ValidationError) as exc_info:
            OpsScenarioRequest(
                scenario="smoke_test",
                player_count=8,
                tournament_format="HEAD_TO_HEAD",
                simulation_mode="manual",
                campus_ids=[],
            )
        err_str = str(exc_info.value)
        assert "campus_ids" in err_str

    def test_valid_campus_ids_accepted(self):
        """OPS-2: campus_ids=[1, 2] → no error."""
        from app.api.api_v1.endpoints.tournaments.ops_scenario import OpsScenarioRequest

        req = OpsScenarioRequest(
            scenario="smoke_test",
            player_count=8,
            tournament_format="HEAD_TO_HEAD",
            simulation_mode="manual",
            campus_ids=[1, 2],
        )
        assert req.campus_ids == [1, 2]

    def test_single_campus_accepted(self):
        """OPS-2b: campus_ids=[42] (min 1) → accepted."""
        from app.api.api_v1.endpoints.tournaments.ops_scenario import OpsScenarioRequest

        req = OpsScenarioRequest(
            scenario="smoke_test",
            player_count=8,
            tournament_format="HEAD_TO_HEAD",
            simulation_mode="manual",
            campus_ids=[42],
        )
        assert req.campus_ids == [42]


# ─── status_validator campus precondition ────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestStatusValidatorCampusPrecondition:
    """SV-01, SV-02"""

    def _tournament_for_validator(self, campus_id=None):
        """Minimal Semester-like object for the validator."""
        return SimpleNamespace(
            id=1,
            name="Cup",
            start_date=datetime(2026, 3, 1),
            end_date=datetime(2026, 3, 31),
            tournament_status="INSTRUCTOR_CONFIRMED",
            master_instructor_id=99,  # instructor assigned
            max_players=32,
            campus_id=campus_id,
            sessions=[SimpleNamespace(id=1)],
            enrollments=[],
            tournament_type_id=None,
        )

    def test_enrollment_open_without_campus_blocked(self):
        """SV-01: campus_id=None → ENROLLMENT_OPEN transition rejected."""
        from app.services.tournament.status_validator import validate_status_transition

        t = self._tournament_for_validator(campus_id=None)
        ok, msg = validate_status_transition("INSTRUCTOR_CONFIRMED", "ENROLLMENT_OPEN", t)

        assert ok is False
        assert "campus" in msg.lower(), f"Expected campus error, got: {msg}"

    def test_enrollment_open_with_campus_passes_campus_check(self):
        """SV-02: campus_id=5 → campus precondition passes (other checks may still fail)."""
        from app.services.tournament.status_validator import validate_status_transition

        t = self._tournament_for_validator(campus_id=5)
        ok, msg = validate_status_transition("INSTRUCTOR_CONFIRMED", "ENROLLMENT_OPEN", t)

        # Campus check passes; any remaining failure must NOT be about campus
        if not ok:
            assert "campus" not in msg.lower(), (
                f"Campus check should have passed but got: {msg}"
            )

    def test_enrollment_open_zero_campus_id_blocked(self):
        """SV-01b: campus_id=0 (falsy) → treated as unset → rejected."""
        from app.services.tournament.status_validator import validate_status_transition

        t = self._tournament_for_validator(campus_id=0)
        ok, msg = validate_status_transition("INSTRUCTOR_CONFIRMED", "ENROLLMENT_OPEN", t)

        assert ok is False
        assert "campus" in msg.lower()

    def test_other_transitions_unaffected(self):
        """SV-03: DRAFT→SEEKING_INSTRUCTOR not affected by campus check."""
        from app.services.tournament.status_validator import validate_status_transition

        t = self._tournament_for_validator(campus_id=None)
        # DRAFT→SEEKING_INSTRUCTOR has its own preconditions (sessions, name, dates)
        # but campus_id is NOT one of them — confirm no campus error
        ok, msg = validate_status_transition("DRAFT", "SEEKING_INSTRUCTOR", t)

        if not ok:
            assert "campus" not in msg.lower(), (
                f"campus check leaked into SEEKING_INSTRUCTOR transition: {msg}"
            )
