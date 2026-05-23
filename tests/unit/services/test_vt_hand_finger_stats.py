"""Hand/Finger Stats service tests — Phase 2.4 (PR #158).

HFS-01  0 attempts → all 4 finger_rows has_data=False, attempt_count=0
HFS-02  < _MIN_SAMPLES (2 attempts RI) → has_data=False, attempt_count=2
HFS-03  >= _MIN_SAMPLES (3 attempts RI) → has_data=True
HFS-04  all 4 combos ≥3 attempts → 4 rows all has_data=True
HFS-05  finger_rows canonical order: RI, RT, LI, LT
HFS-06  return dict has all required keys
HFS-07  min_samples == 3
HFS-08  game_id=None → no gid param sent to SQL
HFS-09  game_id=42 → gid=42 in SQL params
HFS-10  SQL filters on is_valid + assignment_source (no v1/v2/free bleed)
HFS-11  by_hand right has_data=True when cnt >= 3
HFS-12  by_hand left has_data=False when cnt == 0
HFS-13  skill_totals accumulated correctly across two rows
HFS-14  skill_totals empty when no valid skill_deltas rows
HFS-15  game_id filter is forwarded to all 3 SQL execute calls
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, call

from app.services.virtual_training_service import VirtualTrainingService, _MIN_SAMPLES


# ── row factories ─────────────────────────────────────────────────────────────

def _fr(hand: str, finger: str, count: int, label: str | None = None, **kw) -> MagicMock:
    """Build a finger-aggregate row mock."""
    r = MagicMock()
    r.hand = hand
    r.finger = finger
    r.label = label or f"{hand.capitalize()} {finger.capitalize()}"
    r.attempt_count = count
    r.avg_score     = kw.get("avg_score", 85.0)
    r.avg_rt_ms     = kw.get("avg_rt_ms", 420)
    r.best_rt_ms    = kw.get("best_rt_ms", 310)
    r.accuracy_pct  = kw.get("accuracy_pct", 90.0)
    r.miss_pct      = kw.get("miss_pct", 5.0)
    r.wrong_pct     = kw.get("wrong_pct", 5.0)
    r.late_pct      = kw.get("late_pct", 3.0)
    return r


def _hr(hand: str, count: int, **kw) -> MagicMock:
    """Build a hand-aggregate row mock."""
    r = MagicMock()
    r.hand = hand
    r.attempt_count = count
    r.avg_score     = kw.get("avg_score", 85.0)
    r.avg_rt_ms     = kw.get("avg_rt_ms", 420)
    r.accuracy_pct  = kw.get("accuracy_pct", 90.0)
    return r


def _dr(hand: str, finger: str, skill_deltas: dict | None) -> MagicMock:
    """Build a delta row mock."""
    r = MagicMock()
    r.hand = hand
    r.finger = finger
    r.skill_deltas = skill_deltas
    return r


def _make_db(
    finger_rows: list,
    hand_rows: list,
    delta_rows: list,
) -> MagicMock:
    """Return a DB mock that cycles execute results: finger → hand → delta."""
    db = MagicMock()
    call_count = 0

    def _execute(sql, params):
        nonlocal call_count
        call_count += 1
        m = MagicMock()
        if call_count == 1:
            m.fetchall.return_value = finger_rows
        elif call_count == 2:
            m.fetchall.return_value = hand_rows
        else:
            m.fetchall.return_value = delta_rows
        return m

    db.execute.side_effect = _execute
    return db


def _call(finger_rows, hand_rows, delta_rows=None, game_id=None, user_id=202):
    db = _make_db(finger_rows, hand_rows, delta_rows or [])
    return VirtualTrainingService.get_hand_finger_stats(db, user_id=user_id, game_id=game_id)


# ── HFS-01: 0 attempts ───────────────────────────────────────────────────────

class TestZeroAttempts:

    def test_hfs01_zero_attempts_all_rows_no_data(self):
        """HFS-01: 0 attempts → all 4 finger_rows has_data=False, attempt_count=0."""
        result = _call([], [], [])
        rows = result["finger_rows"]
        assert len(rows) == 4
        for row in rows:
            assert row["has_data"] is False
            assert row["attempt_count"] == 0

    def test_hfs01b_zero_attempts_by_hand_no_data(self):
        """HFS-01b: 0 attempts → both hands has_data=False."""
        result = _call([], [], [])
        assert result["by_hand"]["right"]["has_data"] is False
        assert result["by_hand"]["left"]["has_data"] is False

    def test_hfs01c_zero_attempts_skill_totals_empty(self):
        """HFS-01c: 0 attempts → skill_totals == {}."""
        result = _call([], [], [])
        assert result["skill_totals"] == {}


# ── HFS-02/03: _MIN_SAMPLES threshold ────────────────────────────────────────

class TestMinSamplesThreshold:

    def test_hfs02_below_threshold_has_data_false(self):
        """HFS-02: 2 RI attempts → has_data=False."""
        result = _call(
            [_fr("right", "index", 2)],
            [_hr("right", 2)],
        )
        ri = next(r for r in result["finger_rows"] if r["hand"] == "right" and r["finger"] == "index")
        assert ri["has_data"] is False
        assert ri["attempt_count"] == 2

    def test_hfs03_at_threshold_has_data_true(self):
        """HFS-03: 3 RI attempts → has_data=True."""
        result = _call(
            [_fr("right", "index", 3)],
            [_hr("right", 3)],
        )
        ri = next(r for r in result["finger_rows"] if r["hand"] == "right" and r["finger"] == "index")
        assert ri["has_data"] is True
        assert ri["attempt_count"] == 3

    def test_hfs03b_above_threshold_has_data_true(self):
        """HFS-03b: 10 LT attempts → has_data=True."""
        result = _call(
            [_fr("left", "thumb", 10)],
            [_hr("left", 10)],
        )
        lt = next(r for r in result["finger_rows"] if r["hand"] == "left" and r["finger"] == "thumb")
        assert lt["has_data"] is True


# ── HFS-04: all 4 combos ─────────────────────────────────────────────────────

class TestAllFourCombos:

    def test_hfs04_all_combos_have_data(self):
        """HFS-04: all 4 combos ≥3 attempts → 4 rows all has_data=True."""
        finger_rows = [
            _fr("right", "index", 5),
            _fr("right", "thumb", 4),
            _fr("left",  "index", 3),
            _fr("left",  "thumb", 6),
        ]
        result = _call(
            finger_rows,
            [_hr("right", 9), _hr("left", 9)],
        )
        for row in result["finger_rows"]:
            assert row["has_data"] is True, f"{row['label']} should have data"


# ── HFS-05: canonical order ───────────────────────────────────────────────────

class TestCanonicalOrder:

    def test_hfs05_finger_rows_canonical_order(self):
        """HFS-05: finger_rows[0..3] = RI, RT, LI, LT regardless of DB return order."""
        # DB returns in reverse order
        finger_rows = [
            _fr("left",  "thumb",  4),
            _fr("left",  "index",  3),
            _fr("right", "thumb",  5),
            _fr("right", "index",  6),
        ]
        result = _call(finger_rows, [])
        rows = result["finger_rows"]
        assert rows[0]["hand"] == "right" and rows[0]["finger"] == "index"
        assert rows[1]["hand"] == "right" and rows[1]["finger"] == "thumb"
        assert rows[2]["hand"] == "left"  and rows[2]["finger"] == "index"
        assert rows[3]["hand"] == "left"  and rows[3]["finger"] == "thumb"


# ── HFS-06/07: structure ─────────────────────────────────────────────────────

class TestReturnStructure:

    def test_hfs06_all_required_keys_present(self):
        """HFS-06: return dict has all required keys."""
        result = _call([], [], [])
        for key in ("min_samples", "finger_rows", "by_hand", "skill_totals"):
            assert key in result, f"Missing key: {key}"

    def test_hfs07_min_samples_equals_3(self):
        """HFS-07: min_samples == 3 (matches _MIN_SAMPLES constant)."""
        result = _call([], [], [])
        assert result["min_samples"] == 3
        assert result["min_samples"] == _MIN_SAMPLES


# ── HFS-08/09: game_id param ─────────────────────────────────────────────────

class TestGameIdParam:

    def _capture_params(self, game_id):
        db = MagicMock()
        captured = []

        def _execute(sql, params):
            captured.append(params.copy())
            m = MagicMock()
            m.fetchall.return_value = []
            return m

        db.execute.side_effect = _execute
        VirtualTrainingService.get_hand_finger_stats(db, user_id=303, game_id=game_id)
        return captured

    def test_hfs08_no_game_id_no_gid_in_params(self):
        """HFS-08: game_id=None → no gid key in SQL params."""
        params_list = self._capture_params(game_id=None)
        for params in params_list:
            assert "gid" not in params

    def test_hfs09_game_id_forwarded_to_sql(self):
        """HFS-09: game_id=42 → gid=42 in all 3 SQL execute calls."""
        params_list = self._capture_params(game_id=42)
        assert len(params_list) == 3
        for params in params_list:
            assert params.get("gid") == 42


# ── HFS-10: SQL filter content ───────────────────────────────────────────────

class TestSQLFilterContent:

    def test_hfs10_sql_contains_is_valid_and_assignment_source(self):
        """HFS-10: SQL filters on is_valid and assignment_source = system."""
        db = MagicMock()
        sql_strings: list[str] = []

        def _execute(sql, params):
            sql_strings.append(str(sql))
            m = MagicMock()
            m.fetchall.return_value = []
            return m

        db.execute.side_effect = _execute
        VirtualTrainingService.get_hand_finger_stats(db, user_id=404, game_id=None)

        for sql_str in sql_strings:
            assert "is_valid" in sql_str, "SQL must filter on is_valid"
            assert "assignment_source" in sql_str, "SQL must filter on assignment_source"


# ── HFS-11/12: by_hand ────────────────────────────────────────────────────────

class TestByHand:

    def test_hfs11_right_hand_has_data_true(self):
        """HFS-11: right 3 attempts → by_hand[right] has_data=True."""
        result = _call(
            [_fr("right", "index", 3)],
            [_hr("right", 3)],
        )
        assert result["by_hand"]["right"]["has_data"] is True
        assert result["by_hand"]["right"]["attempt_count"] == 3

    def test_hfs12_left_hand_has_data_false_when_zero(self):
        """HFS-12: left 0 attempts → by_hand[left] has_data=False."""
        result = _call(
            [_fr("right", "index", 5)],
            [_hr("right", 5)],
        )
        assert result["by_hand"]["left"]["has_data"] is False
        assert result["by_hand"]["left"]["attempt_count"] == 0


# ── HFS-13/14: skill_totals ───────────────────────────────────────────────────

class TestSkillTotals:

    def test_hfs13_skill_totals_accumulated(self):
        """HFS-13: two RI delta rows → reactions sums to 0.3 (0.1 + 0.2)."""
        delta_rows = [
            _dr("right", "index", {"reactions": 0.1, "decisions": 0.05}),
            _dr("right", "index", {"reactions": 0.2, "decisions": 0.10}),
        ]
        result = _call([], [], delta_rows)
        ri_totals = result["skill_totals"].get("right_index", {})
        assert abs(ri_totals.get("reactions", 0) - 0.3) < 1e-6
        assert abs(ri_totals.get("decisions", 0) - 0.15) < 1e-6

    def test_hfs13b_multiple_combos_independent_accumulation(self):
        """HFS-13b: RI and LT accumulate independently."""
        delta_rows = [
            _dr("right", "index", {"reactions": 0.5}),
            _dr("left",  "thumb", {"composure": 0.3}),
        ]
        result = _call([], [], delta_rows)
        assert abs(result["skill_totals"]["right_index"]["reactions"] - 0.5) < 1e-6
        assert abs(result["skill_totals"]["left_thumb"]["composure"] - 0.3) < 1e-6
        assert "right_index" not in result["skill_totals"].get("left_thumb", {})

    def test_hfs14_no_skill_deltas_returns_empty(self):
        """HFS-14: delta rows with None/empty skill_deltas → skill_totals == {}."""
        delta_rows = [
            _dr("right", "index", None),
            _dr("right", "thumb", {}),
        ]
        result = _call([], [], delta_rows)
        assert result["skill_totals"] == {}


# ── HFS-15: game_id in all 3 queries ─────────────────────────────────────────

class TestGameIdIsolation:

    def test_hfs15_game_id_in_all_three_queries(self):
        """HFS-15: game_id filter forwarded to all 3 SQL execute calls."""
        db = MagicMock()
        call_params: list[dict] = []

        def _execute(sql, params):
            call_params.append(dict(params))
            m = MagicMock()
            m.fetchall.return_value = []
            return m

        db.execute.side_effect = _execute
        VirtualTrainingService.get_hand_finger_stats(db, user_id=505, game_id=7)

        assert len(call_params) == 3, "Expected exactly 3 SQL execute calls"
        for idx, params in enumerate(call_params):
            assert params.get("gid") == 7, f"gid missing from query {idx + 1}"
            assert params.get("uid") == 505
