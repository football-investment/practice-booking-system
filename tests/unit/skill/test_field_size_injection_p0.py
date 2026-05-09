"""
P0 Fix A — field_size injection tests (BUG-P0-CARD-01)

Verifies that compute_single_tournament_skill_delta uses field_size when provided
instead of the partial DB count, and that existing callers without field_size are
unaffected (backward-compatible Optional[int] = None default).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

import pytest

# ─── patch base ──────────────────────────────────────────────────────────────

_BASE = "app.services.skill_progression._ema_engine"


# ─── helpers ─────────────────────────────────────────────────────────────────


def _make_db_returning_participations(participations):
    """
    Return a MagicMock db whose query chain ends in participations.

    Handles:
      db.query(TournamentParticipation).filter(...).order_by(...).all() → participations
      db.query(...).filter(...).first() → None   (baseline fallback)
      db.query(...).filter(...).count() → 0       (fallback — should not be reached
                                                    when field_size is injected)
    """
    db = MagicMock()

    # Default: .first() returns a license-like object with no football_skills
    db.query.return_value.filter.return_value.first.return_value = MagicMock(
        football_skills=None
    )
    # Default: .count() — should NOT be called for target tournament when field_size set
    db.query.return_value.filter.return_value.count.return_value = 0
    db.query.return_value.filter.return_value.distinct.return_value.count.return_value = 0
    # Participation list
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
        participations
    )
    return db


def _make_participation(tournament_id: int, placement: int, user_id: int = 42):
    """Minimal TournamentParticipation-like mock."""
    p = MagicMock()
    t = MagicMock()
    t.id = tournament_id
    t.semester_id = tournament_id
    t.participant_type = "INDIVIDUAL"
    t.game_preset = None
    p.tournament = t
    p.placement = placement
    p.user_id = user_id
    p.semester_id = tournament_id
    p.achieved_at = None
    p.id = 1
    return p


# ─── Test 1: field_size overrides DB count for target tournament ──────────────


class TestFieldSizeOverridesDbCount:
    """
    FIX-A-01: When field_size is passed, compute_single does NOT call db.count()
    for the target tournament — it uses field_size directly.
    """

    def test_field_size_overrides_db_count(self):
        from app.services.skill_progression._ema_engine import (
            compute_single_tournament_skill_delta,
        )

        target_id = 99
        p = _make_participation(target_id, placement=2)
        db = _make_db_returning_participations([p])

        count_calls_before = db.query.return_value.filter.return_value.count.call_count

        with (
            patch(f"{_BASE}.get_baseline_skills", return_value={"sprint_speed": 60.0}),
            patch(f"{_BASE}.get_all_skill_keys", return_value=["sprint_speed"]),
            patch(f"{_BASE}._extract_tournament_skills", return_value={"sprint_speed": 1.0}),
            patch(f"{_BASE}._compute_opponent_factor", return_value=1.0),
            patch(f"{_BASE}._compute_match_performance_modifier", return_value=1.0),
            patch(f"{_BASE}.calculate_skill_value_from_placement", return_value=65.0),
        ):
            result = compute_single_tournament_skill_delta(
                db, user_id=42, tournament_id=target_id, field_size=9
            )

        # count() must NOT have been called for the target tournament when field_size given
        count_calls_after = db.query.return_value.filter.return_value.count.call_count
        assert count_calls_after == count_calls_before, (
            "db.count() was called even though field_size was provided — "
            "BUG-P0-CARD-01 fix not active"
        )

        # Result should be a dict (non-empty because calculate_skill_value_from_placement=65 > 60)
        assert isinstance(result, dict)


# ─── Test 2: field_size=None falls back to DB count (backward-compatible) ────


class TestFieldSizeNoneBackwardCompatible:
    """
    FIX-A-02: field_size=None (default) must fall through to the existing DB count path.
    Existing callers (tests, endpoints) that do not pass field_size are unaffected.
    """

    def test_field_size_none_uses_db_count(self):
        from app.services.skill_progression._ema_engine import (
            compute_single_tournament_skill_delta,
        )

        target_id = 99
        p = _make_participation(target_id, placement=2)
        db = _make_db_returning_participations([p])
        # Return a non-zero count so processing continues
        db.query.return_value.filter.return_value.count.return_value = 9

        with (
            patch(f"{_BASE}.get_baseline_skills", return_value={"sprint_speed": 60.0}),
            patch(f"{_BASE}.get_all_skill_keys", return_value=["sprint_speed"]),
            patch(f"{_BASE}._extract_tournament_skills", return_value={"sprint_speed": 1.0}),
            patch(f"{_BASE}._compute_opponent_factor", return_value=1.0),
            patch(f"{_BASE}._compute_match_performance_modifier", return_value=1.0),
            patch(f"{_BASE}.calculate_skill_value_from_placement", return_value=65.0),
        ):
            # No field_size — backward-compatible call
            result = compute_single_tournament_skill_delta(
                db, user_id=42, tournament_id=target_id
            )

        # db.count() must have been invoked for the total_players path
        assert db.query.return_value.filter.return_value.count.called, (
            "db.count() was NOT called when field_size=None — backward-compat broken"
        )


# ─── Test 3: rank-1 delta unchanged by field_size ────────────────────────────


class TestRank1DeltaUnchangedByFieldSize:
    """
    FIX-A-03: Rank-1 (placement=1) percentile = (1-1)/(N-1) = 0 for any N ≥ 2.
    field_size injection has zero effect on rank-1 delta.
    """

    def test_rank1_delta_same_with_or_without_field_size(self):
        from app.services.skill_progression._ema_engine import (
            compute_single_tournament_skill_delta,
        )

        target_id = 99
        p = _make_participation(target_id, placement=1)
        db_a = _make_db_returning_participations([p])
        db_b = _make_db_returning_participations([p])
        db_a.query.return_value.filter.return_value.count.return_value = 9
        db_b.query.return_value.filter.return_value.count.return_value = 9

        common_patches = dict(
            get_baseline_skills={"sprint_speed": 60.0},
            get_all_skill_keys=["sprint_speed"],
            _extract_tournament_skills={"sprint_speed": 1.0},
            _compute_opponent_factor=1.0,
            _compute_match_performance_modifier=1.0,
        )

        captured = {}

        def _capture_and_return(**kwargs):
            captured[kwargs.get("field_size_key", "val")] = kwargs
            return 80.0  # fixed return so delta = 80-60 = +20

        with (
            patch(f"{_BASE}.get_baseline_skills", return_value={"sprint_speed": 60.0}),
            patch(f"{_BASE}.get_all_skill_keys", return_value=["sprint_speed"]),
            patch(f"{_BASE}._extract_tournament_skills", return_value={"sprint_speed": 1.0}),
            patch(f"{_BASE}._compute_opponent_factor", return_value=1.0),
            patch(f"{_BASE}._compute_match_performance_modifier", return_value=1.0),
            patch(f"{_BASE}.calculate_skill_value_from_placement", return_value=80.0) as mock_calc,
        ):
            result_no_fs = compute_single_tournament_skill_delta(
                db_a, user_id=42, tournament_id=target_id
            )
            calls_no_fs = mock_calc.call_args_list[:]

        with (
            patch(f"{_BASE}.get_baseline_skills", return_value={"sprint_speed": 60.0}),
            patch(f"{_BASE}.get_all_skill_keys", return_value=["sprint_speed"]),
            patch(f"{_BASE}._extract_tournament_skills", return_value={"sprint_speed": 1.0}),
            patch(f"{_BASE}._compute_opponent_factor", return_value=1.0),
            patch(f"{_BASE}._compute_match_performance_modifier", return_value=1.0),
            patch(f"{_BASE}.calculate_skill_value_from_placement", return_value=80.0) as mock_calc2,
        ):
            result_with_fs = compute_single_tournament_skill_delta(
                db_b, user_id=42, tournament_id=target_id, field_size=9
            )
            calls_with_fs = mock_calc2.call_args_list[:]

        # Both calls must pass the same total_players=9 to calculate_skill_value_from_placement
        tp_no_fs = calls_no_fs[0].kwargs.get("total_players") or calls_no_fs[0].args[1]
        tp_with_fs = calls_with_fs[0].kwargs.get("total_players") or calls_with_fs[0].args[1]
        assert tp_no_fs == tp_with_fs, (
            f"Rank-1 total_players differs: no_fs={tp_no_fs} vs with_fs={tp_with_fs}. "
            "field_size is corrupting rank-1 calculation."
        )
        assert result_no_fs == result_with_fs


# ─── Test 4: rank-2 correct delta with field_size=N ─────────────────────────


class TestRank2CorrectWithFieldSize:
    """
    FIX-A-04: Rank-2 in a 9-player tournament.

    Without fix: total_players=2 (only 1 TP committed before this user's distribution)
      → percentile = (2-1)/(2-1) = 1.0 → placement_skill=40 → negative delta

    With fix: total_players=9 (field_size injected)
      → percentile = (2-1)/(9-1) = 0.125 → placement_skill=90 → positive delta

    This test verifies that calculate_skill_value_from_placement receives
    total_players=9 (not 2) when field_size=9 is passed.
    """

    def test_rank2_receives_full_field_size(self):
        from app.services.skill_progression._ema_engine import (
            compute_single_tournament_skill_delta,
        )

        target_id = 99
        p = _make_participation(target_id, placement=2)
        db = _make_db_returning_participations([p])
        # Partial count: only 2 TPs visible at distribution time
        db.query.return_value.filter.return_value.count.return_value = 2

        with (
            patch(f"{_BASE}.get_baseline_skills", return_value={"sprint_speed": 60.0}),
            patch(f"{_BASE}.get_all_skill_keys", return_value=["sprint_speed"]),
            patch(f"{_BASE}._extract_tournament_skills", return_value={"sprint_speed": 1.0}),
            patch(f"{_BASE}._compute_opponent_factor", return_value=1.0),
            patch(f"{_BASE}._compute_match_performance_modifier", return_value=1.0),
            patch(f"{_BASE}.calculate_skill_value_from_placement", return_value=65.0) as mock_calc,
        ):
            compute_single_tournament_skill_delta(
                db, user_id=42, tournament_id=target_id, field_size=9
            )

        assert mock_calc.called, "calculate_skill_value_from_placement was never called"
        call_kwargs = mock_calc.call_args.kwargs
        actual_tp = call_kwargs.get("total_players")
        assert actual_tp == 9, (
            f"Expected total_players=9 (field_size), got {actual_tp}. "
            "BUG-P0-CARD-01 fix not propagating field_size correctly."
        )


# ─── Test 5: last-place rank-N delta unchanged by field_size ─────────────────


class TestRankNDeltaUnchangedByFieldSize:
    """
    FIX-A-05: Rank-N (last place) percentile = (N-1)/(N-1) = 1.0 for any N.
    field_size injection has zero effect on last-place delta — it was already correct.
    """

    def test_rank_last_receives_correct_total_players(self):
        from app.services.skill_progression._ema_engine import (
            compute_single_tournament_skill_delta,
        )

        N = 9
        target_id = 99
        p = _make_participation(target_id, placement=N)
        db = _make_db_returning_participations([p])
        db.query.return_value.filter.return_value.count.return_value = N  # full count even without fix

        with (
            patch(f"{_BASE}.get_baseline_skills", return_value={"sprint_speed": 60.0}),
            patch(f"{_BASE}.get_all_skill_keys", return_value=["sprint_speed"]),
            patch(f"{_BASE}._extract_tournament_skills", return_value={"sprint_speed": 1.0}),
            patch(f"{_BASE}._compute_opponent_factor", return_value=1.0),
            patch(f"{_BASE}._compute_match_performance_modifier", return_value=1.0),
            patch(f"{_BASE}.calculate_skill_value_from_placement", return_value=45.0) as mock_calc,
        ):
            compute_single_tournament_skill_delta(
                db, user_id=42, tournament_id=target_id, field_size=N
            )

        assert mock_calc.called
        call_kwargs = mock_calc.call_args.kwargs
        actual_tp = call_kwargs.get("total_players")
        assert actual_tp == N, (
            f"Expected total_players={N}, got {actual_tp}."
        )
