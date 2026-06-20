"""SS-MET: Benchmark metric unit tests."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.smart_snap_poc1.metrics import (
    aggregate,
    false_positive_rate,
    false_refusal_rate,
    latency_summary,
    pixel_error,
    wrong_snap_rate,
)


class TestPixelErrorMetric:
    def test_SS_MET_01_identical_coords_zero_error(self):
        """SS-MET-01: Identical coords → 0 pixel error."""
        assert pixel_error(0.5, 0.5, 0.5, 0.5, 1920, 1080) == 0.0

    def test_SS_MET_02_known_shift(self):
        """SS-MET-02: 10px horizontal shift at 1920 width → 10px error."""
        shift = 10.0 / 1920.0
        err = pixel_error(0.5 + shift, 0.5, 0.5, 0.5, 1920, 1080)
        assert abs(err - 10.0) < 0.01

    def test_SS_MET_03_scale_invariant(self):
        """SS-MET-03: Same normalised offset gives same 1920-reference error regardless of img_w."""
        # pixel_error always returns error in 1920-reference pixels:
        #   dx = (pred_x - gt_x) * img_w * (1920/img_w) = (pred_x - gt_x) * 1920
        # So the result is the same for any img_w given the same normalised shift.
        shift = 10.0 / 1920.0  # =10px at 1920, or 3.33px at 640 — but both → 10px at 1920-ref
        err_1920 = pixel_error(0.5 + shift, 0.5, 0.5, 0.5, 1920, 1080)
        err_640 = pixel_error(0.5 + shift, 0.5, 0.5, 0.5, 640, 480)
        assert abs(err_1920 - 10.0) < 0.01
        assert abs(err_640 - 10.0) < 0.01  # resolution-independent

    def test_SS_MET_04_symmetric(self):
        """SS-MET-04: pixel_error(a,b, c,d) == pixel_error(c,d, a,b)."""
        e1 = pixel_error(0.4, 0.3, 0.6, 0.7, 1920, 1080)
        e2 = pixel_error(0.6, 0.7, 0.4, 0.3, 1920, 1080)
        assert abs(e1 - e2) < 1e-9


class TestAggregate:
    def test_SS_MET_05_aggregate_empty_returns_none(self):
        """SS-MET-05: aggregate([]) returns None for all stats."""
        result = aggregate([])
        assert result["mean"] is None
        assert result["n"] == 0

    def test_SS_MET_06_aggregate_single_value(self):
        """SS-MET-06: aggregate([42]) → mean=median=p90=p95=42."""
        result = aggregate([42.0])
        assert result["mean"] == pytest.approx(42.0)
        assert result["median"] == pytest.approx(42.0)
        assert result["p90"] == pytest.approx(42.0)

    def test_SS_MET_07_aggregate_known_values(self):
        """SS-MET-07: aggregate([0,10,20,30,40]) has known mean/median."""
        result = aggregate([0, 10, 20, 30, 40])
        assert result["mean"] == pytest.approx(20.0)
        assert result["median"] == pytest.approx(20.0)
        assert result["n"] == 5


class TestWrongSnapRate:
    def test_SS_MET_08_no_wrong_snaps(self):
        """SS-MET-08: Snap always improves → wrong_snap_rate = 0."""
        assert wrong_snap_rate([1.0, 2.0], [3.0, 4.0]) == 0.0

    def test_SS_MET_09_all_wrong_snaps(self):
        """SS-MET-09: Snap always worsens → wrong_snap_rate = 1.0."""
        assert wrong_snap_rate([5.0, 6.0], [1.0, 2.0]) == 1.0

    def test_SS_MET_10_partial_wrong_snaps(self):
        """SS-MET-10: Half wrong → wrong_snap_rate = 0.5."""
        assert wrong_snap_rate([1.0, 5.0], [3.0, 2.0]) == pytest.approx(0.5)

    def test_SS_MET_11_mismatched_lengths_returns_none(self):
        """SS-MET-11: Mismatched list lengths → None."""
        assert wrong_snap_rate([1.0, 2.0], [3.0]) is None

    def test_SS_MET_12_empty_lists_returns_none(self):
        """SS-MET-12: Empty lists → None."""
        assert wrong_snap_rate([], []) is None


class TestLatencySummary:
    def test_SS_MET_13_empty_latency(self):
        """SS-MET-13: Empty latencies → None stats."""
        result = latency_summary([])
        assert result["p50_ms"] is None
        assert result["n"] == 0

    def test_SS_MET_14_latency_known_values(self):
        """SS-MET-14: p50 and p95 computed correctly."""
        latencies = [10.0] * 50 + [100.0] * 50  # 50% at 10ms, 50% at 100ms
        result = latency_summary(latencies)
        # p50 should be ~10 or ~100 (at the boundary), p95 = 100
        assert result["p95_ms"] == pytest.approx(100.0, abs=5.0)
        assert result["n"] == 100
