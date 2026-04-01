"""
Unit tests for multi-leg round-robin session generation.

LEGS-01  number_of_legs=1  → session count unchanged vs baseline
LEGS-02  number_of_legs=2 (4 players) → exactly 2× sessions vs legs=1
LEGS-03  number_of_legs=2, track_home_away=True → leg 2 pairings are reversed from leg 1
LEGS-04  All sessions carry leg_number field (1 for single-leg, 1 or 2 for double-leg)
LEGS-05  group_knockout group stage with number_of_legs=2 → 2× group-stage sessions
"""
import pytest
from datetime import date, datetime
from unittest.mock import MagicMock

from app.services.tournament.session_generation.formats.league_generator import LeagueGenerator
from app.services.tournament.session_generation.formats.group_knockout_generator import GroupKnockoutGenerator
from app.services.tournament.session_generation.algorithms import RoundRobinPairing


# ── helpers ──────────────────────────────────────────────────────────────────


def _h2h_tournament(name="Test League"):
    t = MagicMock()
    t.id = 1
    t.name = name
    t.format = "HEAD_TO_HEAD"
    t.scoring_type = "PLACEMENT"
    t.start_date = datetime(2026, 6, 1, 9, 0)
    t.end_date = datetime(2026, 6, 30)
    t.campus = None
    t.location = None
    t.campus_id = None
    return t


def _h2h_tournament_type():
    tt = MagicMock()
    tt.format = "HEAD_TO_HEAD"
    tt.code = "league"
    return tt


def _db_with_enrollments(player_ids):
    """DB mock that returns SemesterEnrollment rows for the given player IDs."""
    db = MagicMock()
    enrollments = []
    for uid in player_ids:
        e = MagicMock()
        e.user_id = uid
        enrollments.append(e)
    q = MagicMock()
    q.filter.return_value = q
    q.all.return_value = enrollments
    db.query.return_value = q
    return db


def _expected_single_leg_count(n_players: int) -> int:
    """Number of matches in 1 full round robin for n_players (excl. byes)."""
    return n_players * (n_players - 1) // 2


# ── tests ─────────────────────────────────────────────────────────────────────


class TestLegsGeneration:

    def _gen_sessions(self, player_ids, number_of_legs=1, track_home_away=False):
        db = _db_with_enrollments(player_ids)
        gen = LeagueGenerator(db)
        t = _h2h_tournament()
        tt = _h2h_tournament_type()
        return gen._generate_head_to_head_pairings(
            tournament=t,
            config=tt,
            player_count=len(player_ids),
            parallel_fields=1,
            session_duration=60,
            break_minutes=10,
            number_of_legs=number_of_legs,
            track_home_away=track_home_away,
        )

    def test_LEGS_01_single_leg_baseline(self):
        """LEGS-01: number_of_legs=1 produces the standard round-robin count."""
        player_ids = [1, 2, 3, 4]
        sessions = self._gen_sessions(player_ids, number_of_legs=1)
        expected = _expected_single_leg_count(len(player_ids))
        assert len(sessions) == expected, f"Expected {expected} sessions, got {len(sessions)}"

    def test_LEGS_02_double_leg_doubles_count(self):
        """LEGS-02: number_of_legs=2 → exactly 2× the single-leg session count."""
        player_ids = [1, 2, 3, 4]
        single = self._gen_sessions(player_ids, number_of_legs=1)
        double = self._gen_sessions(player_ids, number_of_legs=2)
        assert len(double) == 2 * len(single), (
            f"Expected 2×{len(single)}={2*len(single)} sessions for 2 legs, got {len(double)}"
        )

    def test_LEGS_03_home_away_reverses_leg2_pairings(self):
        """LEGS-03: track_home_away=True reverses participant order in even legs."""
        player_ids = [10, 20, 30, 40]
        sessions = self._gen_sessions(player_ids, number_of_legs=2, track_home_away=True)

        # Split by leg
        leg1 = [s for s in sessions if s["leg_number"] == 1]
        leg2 = [s for s in sessions if s["leg_number"] == 2]
        assert len(leg1) == len(leg2)

        # Build pairing sets for each leg
        def pairing(s):
            ids = s.get("participant_user_ids") or []
            return tuple(ids)

        leg1_pairings = [pairing(s) for s in leg1]
        leg2_pairings = [pairing(s) for s in leg2]

        # Every leg-1 pairing should appear reversed in leg-2
        leg1_reversed = {(b, a) for a, b in leg1_pairings}
        leg2_set = set(leg2_pairings)
        assert leg1_reversed == leg2_set, (
            f"Expected leg-2 pairings to be leg-1 reversed.\n"
            f"Leg1 reversed: {leg1_reversed}\nLeg2: {leg2_set}"
        )

    def test_LEGS_04_leg_number_populated(self):
        """LEGS-04: all sessions carry the correct leg_number field."""
        player_ids = [1, 2, 3]
        # Single leg
        single = self._gen_sessions(player_ids, number_of_legs=1)
        assert all(s["leg_number"] == 1 for s in single), "All single-leg sessions should have leg_number=1"

        # Double leg
        double = self._gen_sessions(player_ids, number_of_legs=2)
        leg_numbers = {s["leg_number"] for s in double}
        assert leg_numbers == {1, 2}, f"Expected leg_numbers {{1,2}}, got {leg_numbers}"

    def test_LEGS_05_triple_leg(self):
        """3 legs → 3× the single-leg count."""
        player_ids = [1, 2, 3, 4]
        single_count = _expected_single_leg_count(len(player_ids))
        triple = self._gen_sessions(player_ids, number_of_legs=3)
        assert len(triple) == 3 * single_count

    def test_LEGS_title_includes_leg_label_when_multi_leg(self):
        """Session titles include '(Leg N)' when number_of_legs > 1."""
        player_ids = [1, 2, 3, 4]
        double = self._gen_sessions(player_ids, number_of_legs=2)
        leg1_titles = [s["title"] for s in double if s["leg_number"] == 1]
        leg2_titles = [s["title"] for s in double if s["leg_number"] == 2]
        assert all("(Leg 1)" in t for t in leg1_titles)
        assert all("(Leg 2)" in t for t in leg2_titles)

    def test_LEGS_single_leg_has_no_leg_label_in_title(self):
        """Single-leg sessions should NOT have a leg label in the title."""
        player_ids = [1, 2, 3, 4]
        sessions = self._gen_sessions(player_ids, number_of_legs=1)
        assert all("(Leg" not in s["title"] for s in sessions)

    def test_LEGS_structure_config_contains_leg_info(self):
        """structure_config['leg_number'] should be set."""
        player_ids = [1, 2, 3]
        sessions = self._gen_sessions(player_ids, number_of_legs=2, track_home_away=True)
        for s in sessions:
            sc = s.get("structure_config", {})
            assert "leg_number" in sc
            assert sc["leg_number"] == s["leg_number"]
            assert "is_home_game" in sc
            # leg 1 → home, leg 2 → away
            if s["leg_number"] == 1:
                assert sc["is_home_game"] is True
            else:
                assert sc["is_home_game"] is False


class TestGroupKnockoutLegsGeneration:
    """LEGS-05: group_knockout group stage doubles with number_of_legs=2."""

    def _run_group_knockout(self, n_players: int, number_of_legs: int = 1) -> list:
        """Run GroupKnockoutGenerator with mocked DB and return all sessions."""
        from app.models.tournament_enums import TournamentPhase

        # Build enrolled players list
        player_ids = list(range(101, 101 + n_players))

        db = MagicMock()
        enrollments = []
        for uid in player_ids:
            e = MagicMock()
            e.user_id = uid
            enrollments.append(e)
        q = MagicMock()
        q.filter.return_value = q
        q.all.return_value = enrollments
        q.count.return_value = n_players
        db.query.return_value = q

        t = MagicMock()
        t.id = 99
        t.name = "Group Knockout Test"
        t.format = "HEAD_TO_HEAD"
        t.scoring_type = "PLACEMENT"
        t.start_date = datetime(2026, 6, 1, 9, 0)
        t.end_date = datetime(2026, 6, 30)
        t.campus = None
        t.location = None
        t.campus_id = None

        tt = MagicMock()
        tt.format = "HEAD_TO_HEAD"
        tt.code = "group_knockout"
        tt.config = {"groups": 2, "advancement_spots": 2}

        gen = GroupKnockoutGenerator(db)
        sessions = gen.generate(
            tournament=t,
            tournament_type=tt,
            player_count=n_players,
            parallel_fields=1,
            session_duration=60,
            break_minutes=10,
            number_of_legs=number_of_legs,
            track_home_away=False,
        )
        return sessions

    def test_LEGS_05_group_knockout_double_leg_doubles_group_stage(self):
        """LEGS-05: 8 players, group_knockout, legs=2 → 2× group-stage sessions vs legs=1."""
        from app.models.tournament_enums import TournamentPhase

        # 8 players, 2 groups of 4 → 3 rounds × 2 matches = 6 group-stage matches per leg
        single = self._run_group_knockout(n_players=8, number_of_legs=1)
        double = self._run_group_knockout(n_players=8, number_of_legs=2)

        # Count only group stage sessions
        single_gs = [s for s in single if s.get("ranking_mode") == "GROUP_ISOLATED"]
        double_gs = [s for s in double if s.get("ranking_mode") == "GROUP_ISOLATED"]

        assert len(double_gs) == 2 * len(single_gs), (
            f"Expected 2×{len(single_gs)} group-stage sessions, got {len(double_gs)}"
        )

    def test_LEGS_05_group_knockout_leg_numbers_populated(self):
        """Group-stage sessions in a double-leg group_knockout have leg_number set."""
        double = self._run_group_knockout(n_players=8, number_of_legs=2)
        gs = [s for s in double if s.get("ranking_mode") == "GROUP_ISOLATED"]
        leg_numbers = {s.get("leg_number") for s in gs}
        assert leg_numbers == {1, 2}, f"Expected {{1,2}}, got {leg_numbers}"
