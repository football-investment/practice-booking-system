"""
Unit tests for AdvancementCalculator.apply_crossover_seeding

Covers the N-group generalization bug fix:
- Before fix: only seeded 2 sessions (hardcoded for 2 groups A+B)
- After fix: seeds ALL first-round sessions for 2/4/8 groups

Tournament size matrix:
    8p  → 2 groups × top 2  → 2 sessions round 1 (Semis)
    16p → 4 groups × top 2  → 4 sessions round 1 (QF)
    32p → 8 groups × top 2  → 8 sessions round 1 (R16)

No DB or network required — SessionModel is mocked with SimpleNamespace.
"""

import pytest
from types import SimpleNamespace
from typing import List, Dict, Any

from app.services.tournament.results.calculators.advancement_calculator import AdvancementCalculator


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_sessions(count: int, tournament_round: int = 1) -> List[SimpleNamespace]:
    return [
        SimpleNamespace(tournament_round=tournament_round, participant_user_ids=None)
        for _ in range(count)
    ]


def _standings(user_ids: List[int]) -> List[Dict[str, Any]]:
    return [{"user_id": uid, "rank": i + 1} for i, uid in enumerate(user_ids)]


def _calc() -> AdvancementCalculator:
    return AdvancementCalculator(db=None)  # db not used by apply_crossover_seeding


# ─── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestApplyCrossoverSeeding:

    # ── 2 groups (8p) ─────────────────────────────────────────────────────────

    def test_two_groups_seeds_both_sf_sessions(self):
        """2 groups × top 2 → 2 SF sessions seeded (legacy behaviour preserved)."""
        group_standings = {
            "Group A": _standings([1, 2, 3, 4]),
            "Group B": _standings([5, 6, 7, 8]),
        }
        ko_sessions = _make_sessions(2, tournament_round=1) + _make_sessions(1, tournament_round=2)

        updated = _calc().apply_crossover_seeding(group_standings, ko_sessions)

        assert updated == 2
        sf1, sf2 = ko_sessions[0], ko_sessions[1]
        # seeded = [A1,B1,A2,B2] = [1,5,2,6]  → SF1: 1 vs 6, SF2: 5 vs 2
        assert sf1.participant_user_ids == [1, 6]
        assert sf2.participant_user_ids == [5, 2]

    def test_two_groups_final_stays_empty(self):
        """Final (round 2) must NOT be pre-seeded."""
        group_standings = {
            "Group A": _standings([1, 2]),
            "Group B": _standings([3, 4]),
        }
        ko_sessions = _make_sessions(1, tournament_round=1) + _make_sessions(1, tournament_round=2)
        _calc().apply_crossover_seeding(group_standings, ko_sessions)

        assert ko_sessions[1].participant_user_ids is None

    # ── 4 groups (16p) ────────────────────────────────────────────────────────

    def test_four_groups_seeds_all_four_qf_sessions(self):
        """
        4 groups × top 2 → ALL 4 QF sessions seeded (was the bug: only 2 seeded).

        seeded = [A1,B1,C1,D1, A2,B2,C2,D2]
                  [ 1, 5, 9,13,  2, 6,10,14]

        Bracket seed[i] vs seed[7-i]:
          QF1: 1  vs 14
          QF2: 5  vs 10
          QF3: 9  vs  6
          QF4: 13 vs  2
        """
        group_standings = {
            "Group A": _standings([1,  2,  3,  4]),
            "Group B": _standings([5,  6,  7,  8]),
            "Group C": _standings([9,  10, 11, 12]),
            "Group D": _standings([13, 14, 15, 16]),
        }
        ko_sessions = (
            _make_sessions(4, tournament_round=1)
            + _make_sessions(2, tournament_round=2)
            + _make_sessions(1, tournament_round=3)
        )

        updated = _calc().apply_crossover_seeding(group_standings, ko_sessions)

        assert updated == 4
        qf1, qf2, qf3, qf4 = ko_sessions[:4]
        assert qf1.participant_user_ids == [1,  14]
        assert qf2.participant_user_ids == [5,  10]
        assert qf3.participant_user_ids == [9,  6]
        assert qf4.participant_user_ids == [13, 2]

    def test_four_groups_later_rounds_stay_empty(self):
        """SF and Final sessions must NOT be seeded at advancement time."""
        group_standings = {
            f"Group {c}": _standings(list(range(i * 4 + 1, i * 4 + 5)))
            for i, c in enumerate("ABCD")
        }
        ko_sessions = (
            _make_sessions(4, tournament_round=1)
            + _make_sessions(2, tournament_round=2)
            + _make_sessions(1, tournament_round=3)
        )
        _calc().apply_crossover_seeding(group_standings, ko_sessions)

        for sess in ko_sessions[4:]:
            assert sess.participant_user_ids is None

    # ── 8 groups (32p) ────────────────────────────────────────────────────────

    def test_eight_groups_seeds_all_eight_r16_sessions(self):
        """8 groups × top 2 → all 8 R16 sessions seeded."""
        groups = {
            f"Group {chr(ord('A') + i)}": _standings([i * 4 + 1, i * 4 + 2, i * 4 + 3, i * 4 + 4])
            for i in range(8)
        }
        ko_sessions = _make_sessions(8, tournament_round=1) + _make_sessions(4, tournament_round=2)

        updated = _calc().apply_crossover_seeding(groups, ko_sessions)

        assert updated == 8
        # seeded = [1,5,9,13,17,21,25,29, 2,6,10,14,18,22,26,30]
        seeded = [i * 4 + 1 for i in range(8)] + [i * 4 + 2 for i in range(8)]
        assert ko_sessions[0].participant_user_ids == [seeded[0],  seeded[15]]
        assert ko_sessions[7].participant_user_ids == [seeded[7],  seeded[8]]

    # ── Edge cases ────────────────────────────────────────────────────────────

    def test_single_group_returns_zero(self):
        group_standings = {"Group A": _standings([1, 2, 3, 4])}
        ko_sessions = _make_sessions(2, tournament_round=1)

        assert _calc().apply_crossover_seeding(group_standings, ko_sessions) == 0
        assert all(s.participant_user_ids is None for s in ko_sessions)

    def test_no_first_round_sessions_returns_zero(self):
        group_standings = {
            "Group A": _standings([1, 2]),
            "Group B": _standings([3, 4]),
        }
        ko_sessions = _make_sessions(1, tournament_round=2)  # Only Final, no round-1

        assert _calc().apply_crossover_seeding(group_standings, ko_sessions) == 0

    def test_insufficient_standings_returns_zero(self):
        group_standings = {
            "Group A": _standings([1]),   # only 1 player
            "Group B": _standings([]),    # empty
        }
        ko_sessions = _make_sessions(2, tournament_round=1)

        assert _calc().apply_crossover_seeding(group_standings, ko_sessions) == 0

    def test_seeding_is_deterministic(self):
        """Same input always produces the same seeding."""
        group_standings = {
            "Group A": _standings([10, 20, 30]),
            "Group B": _standings([40, 50, 60]),
        }
        sessions_a = _make_sessions(3, tournament_round=1)
        sessions_b = _make_sessions(3, tournament_round=1)

        _calc().apply_crossover_seeding(group_standings, sessions_a)
        _calc().apply_crossover_seeding(group_standings, sessions_b)

        for sa, sb in zip(sessions_a, sessions_b):
            assert sa.participant_user_ids == sb.participant_user_ids

    def test_sessions_updated_count_matches_first_round(self):
        """Return value = number of round-1 sessions updated."""
        group_standings = {
            "Group A": _standings([1, 2]),
            "Group B": _standings([3, 4]),
        }
        ko_sessions = _make_sessions(2, tournament_round=1)
        updated = _calc().apply_crossover_seeding(group_standings, ko_sessions)
        assert updated == 2  # Exactly 2 sessions seeded

    def test_participant_ids_not_none_after_seeding(self):
        """Ensure participant_user_ids is assigned (not None) for seeded sessions."""
        group_standings = {
            "Group A": _standings([10, 20]),
            "Group B": _standings([30, 40]),
        }
        ko_sessions = _make_sessions(2, tournament_round=1)
        _calc().apply_crossover_seeding(group_standings, ko_sessions)

        for sess in ko_sessions:
            assert sess.participant_user_ids is not None
            assert len(sess.participant_user_ids) == 2
            assert all(isinstance(uid, int) for uid in sess.participant_user_ids)

    def test_four_groups_explicit_crossover_pattern(self):
        """
        Verify exact crossover pattern for 4 groups:
          A1 vs D2, B1 vs C2, C1 vs B2, D1 vs A2

        Group A top 2: [101, 102]
        Group B top 2: [201, 202]
        Group C top 2: [301, 302]
        Group D top 2: [401, 402]

        seeded list = [A1,B1,C1,D1, A2,B2,C2,D2]
                    = [101,201,301,401, 102,202,302,402]

        Bracket pairing: seeded[i] vs seeded[7-i]
          QF1: 101 vs 402  (A1 vs D2)
          QF2: 201 vs 302  (B1 vs C2)
          QF3: 301 vs 202  (C1 vs B2)
          QF4: 401 vs 102  (D1 vs A2)
        """
        group_standings = {
            "Group A": _standings([101, 102]),
            "Group B": _standings([201, 202]),
            "Group C": _standings([301, 302]),
            "Group D": _standings([401, 402]),
        }
        ko_sessions = _make_sessions(4, tournament_round=1)
        updated = _calc().apply_crossover_seeding(group_standings, ko_sessions)

        assert updated == 4
        assert set(ko_sessions[0].participant_user_ids) == {101, 402}  # A1 vs D2
        assert set(ko_sessions[1].participant_user_ids) == {201, 302}  # B1 vs C2
        assert set(ko_sessions[2].participant_user_ids) == {301, 202}  # C1 vs B2
        assert set(ko_sessions[3].participant_user_ids) == {401, 102}  # D1 vs A2

    def test_uneven_group_sizes_handled_gracefully(self):
        """Groups with different number of players → still seeds correctly."""
        group_standings = {
            "Group A": _standings([1, 2, 3, 4, 5]),  # 5 players
            "Group B": _standings([6, 7]),            # 2 players
        }
        ko_sessions = _make_sessions(2, tournament_round=1)
        updated = _calc().apply_crossover_seeding(group_standings, ko_sessions)

        assert updated == 2
        # Should take top 2 from each: [1,6,2,7]
        assert ko_sessions[0].participant_user_ids == [1, 7]  # A1 vs B2
        assert ko_sessions[1].participant_user_ids == [6, 2]  # B1 vs A2


@pytest.mark.unit
class TestGetQualifiedParticipants:

    def test_top_two_per_group(self):
        group_standings = {
            "Group A": _standings([1, 2, 3, 4]),
            "Group B": _standings([5, 6, 7, 8]),
        }
        result = AdvancementCalculator.get_qualified_participants(group_standings, top_n=2)
        assert set(result) == {1, 2, 5, 6}
        assert len(result) == 4

    def test_top_one_per_group(self):
        group_standings = {
            "Group A": _standings([1, 2]),
            "Group B": _standings([3, 4]),
        }
        result = AdvancementCalculator.get_qualified_participants(group_standings, top_n=1)
        assert set(result) == {1, 3}

    def test_four_groups_top_two(self):
        group_standings = {
            f"Group {c}": _standings([i * 4 + 1, i * 4 + 2, i * 4 + 3, i * 4 + 4])
            for i, c in enumerate("ABCD")
        }
        result = AdvancementCalculator.get_qualified_participants(group_standings, top_n=2)
        assert len(result) == 8
        assert set(result) == {1, 2, 5, 6, 9, 10, 13, 14}
