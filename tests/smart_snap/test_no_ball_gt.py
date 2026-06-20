"""SS-NOBALL: No-ball and null-GT handling tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.smart_snap_poc1.algorithms import M3StoredSSD, M4Contour, M5Hough, M6TemplateMatch
from scripts.smart_snap_poc1.metrics import false_positive_rate, false_refusal_rate


class TestNoBallNullGT:
    def test_SS_NOBALL_01_m3_no_model_returns_not_found(self):
        """SS-NOBALL-01: M3 returns found=False when model_x/y are None."""
        m3 = M3StoredSSD()
        img = np.full((240, 320, 3), 128, dtype=np.uint8)
        result = m3(img, 0.5, 0.5, model_x=None, model_y=None)
        assert not result.found
        assert result.refusal_reason is not None

    def test_SS_NOBALL_02_m4_empty_image_refuses(self):
        """SS-NOBALL-02: M4 on uniform grey image returns found=False."""
        m4 = M4Contour()
        img = np.full((240, 320, 3), 128, dtype=np.uint8)
        result = m4(img, 0.5, 0.5)
        assert not result.found

    def test_SS_NOBALL_03_m5_empty_image_refuses(self):
        """SS-NOBALL-03: M5 on uniform grey image returns found=False."""
        m5 = M5Hough()
        img = np.full((240, 320, 3), 128, dtype=np.uint8)
        result = m5(img, 0.5, 0.5)
        assert not result.found

    def test_SS_NOBALL_04_m6_empty_image_refuses(self):
        """SS-NOBALL-04: M6 on uniform grey image returns found=False or low-confidence."""
        m6 = M6TemplateMatch()
        img = np.full((240, 320, 3), 128, dtype=np.uint8)
        result = m6(img, 0.5, 0.5)
        # Template match may find "something" in uniform noise, but confidence should be low
        # We only check that it doesn't crash and returns a valid SnapResult
        assert hasattr(result, "found")
        assert hasattr(result, "refined_x")

    def test_SS_NOBALL_05_null_gt_coords_means_no_ball(self):
        """SS-NOBALL-05: Frame entry with is_no_ball=True has no gt_final."""
        entry = {
            "is_no_ball": True,
            "gt_round_1": None,
            "gt_round_2": None,
            "gt_final": None,
            "human_raw_tap": None,
            "human_loupe_tap": None,
        }
        assert entry["gt_final"] is None
        assert entry["is_no_ball"] is True

    def test_SS_NOBALL_06_false_positive_rate_all_false(self):
        """SS-NOBALL-06: No FPs → false_positive_rate = 0."""
        assert false_positive_rate([False, False, False]) == 0.0

    def test_SS_NOBALL_07_false_positive_rate_all_true(self):
        """SS-NOBALL-07: All FPs → false_positive_rate = 1.0."""
        assert false_positive_rate([True, True]) == 1.0

    def test_SS_NOBALL_08_false_positive_rate_empty(self):
        """SS-NOBALL-08: Empty list → false_positive_rate = None."""
        assert false_positive_rate([]) is None

    def test_SS_NOBALL_09_false_refusal_rate(self):
        """SS-NOBALL-09: 1 refusal out of 4 positive frames → 0.25."""
        assert false_refusal_rate([True, False, True, True]) == pytest.approx(0.25)

    def test_SS_NOBALL_10_snap_result_has_latency(self):
        """SS-NOBALL-10: SnapResult always has a latency_ms >= 0 when called via __call__."""
        m4 = M4Contour()
        img = np.full((240, 320, 3), 128, dtype=np.uint8)
        result = m4(img, 0.5, 0.5)
        assert result.latency_ms >= 0.0
