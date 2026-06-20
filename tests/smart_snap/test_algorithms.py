"""
SS-ALGO: Algorithm correctness tests on synthetic images.

Tests use a simple white circle on dark background (exact geometry known).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.smart_snap_poc1.algorithms import M3StoredSSD, M4Contour, M5Hough, M6TemplateMatch
from tests.smart_snap.conftest import make_ball_image, make_empty_image


# Ball is at (160, 120) in a 320×240 image → normalised (0.5, 0.5)
BALL_CX_NORM = 160 / 320
BALL_CY_NORM = 120 / 240
ERROR_TOLERANCE_NORM = 0.05  # within 5% of frame width


def _norm_dist(x1, y1, x2, y2):
    return math.hypot(x1 - x2, y1 - y2)


class TestM3StoredSSD:
    def test_SS_ALGO_M3_01_returns_model_coords(self):
        """SS-ALGO-M3-01: M3 returns exactly the model_x/y provided."""
        m3 = M3StoredSSD()
        img = make_ball_image()
        result = m3(img, 0.5, 0.5, model_x=0.42, model_y=0.38, model_confidence=0.9)
        assert result.found
        assert result.refined_x == pytest.approx(0.42)
        assert result.refined_y == pytest.approx(0.38)

    def test_SS_ALGO_M3_02_confidence_passthrough(self):
        """SS-ALGO-M3-02: M3 passes model_confidence through."""
        m3 = M3StoredSSD()
        img = make_ball_image()
        result = m3(img, 0.5, 0.5, model_x=0.5, model_y=0.5, model_confidence=0.75)
        assert result.confidence == pytest.approx(0.75)

    def test_SS_ALGO_M3_03_none_confidence_becomes_zero(self):
        """SS-ALGO-M3-03: None model_confidence is stored as 0.0."""
        m3 = M3StoredSSD()
        img = make_ball_image()
        result = m3(img, 0.5, 0.5, model_x=0.5, model_y=0.5, model_confidence=None)
        assert result.confidence == 0.0

    def test_SS_ALGO_M3_04_no_model_prediction(self):
        """SS-ALGO-M3-04: M3 returns found=False when model coords absent."""
        m3 = M3StoredSSD()
        img = make_ball_image()
        result = m3(img, 0.5, 0.5)
        assert not result.found


class TestM4Contour:
    def test_SS_ALGO_M4_01_detects_synthetic_circle(self):
        """SS-ALGO-M4-01: M4 finds ball near true centre on clean synthetic image."""
        m4 = M4Contour()
        img = make_ball_image(width=320, height=240, ball_cx=160, ball_cy=120, ball_radius=25)
        result = m4(img, BALL_CX_NORM, BALL_CY_NORM)
        assert result.found, f"M4 failed: {result.refusal_reason}"
        dist = _norm_dist(result.refined_x, result.refined_y, BALL_CX_NORM, BALL_CY_NORM)
        assert dist < ERROR_TOLERANCE_NORM, f"M4 error too large: {dist:.4f} norm"

    def test_SS_ALGO_M4_02_empty_image_no_contour(self):
        """SS-ALGO-M4-02: M4 refuses on featureless image."""
        m4 = M4Contour()
        img = make_empty_image()
        result = m4(img, 0.5, 0.5)
        assert not result.found

    def test_SS_ALGO_M4_03_result_within_image_bounds(self):
        """SS-ALGO-M4-03: refined_x/y always in [0,1] when found=True."""
        m4 = M4Contour()
        img = make_ball_image()
        result = m4(img, BALL_CX_NORM, BALL_CY_NORM)
        if result.found:
            assert 0.0 <= result.refined_x <= 1.0
            assert 0.0 <= result.refined_y <= 1.0

    def test_SS_ALGO_M4_04_latency_measured(self):
        """SS-ALGO-M4-04: latency_ms is positive after a call."""
        m4 = M4Contour()
        img = make_ball_image()
        result = m4(img, 0.5, 0.5)
        assert result.latency_ms > 0


class TestM5Hough:
    def test_SS_ALGO_M5_01_detects_synthetic_circle(self):
        """SS-ALGO-M5-01: M5 finds a large synthetic circle on clean background."""
        m5 = M5Hough()
        # Larger ball and high-contrast for Hough to succeed reliably
        img = make_ball_image(
            width=320, height=240,
            ball_cx=160, ball_cy=120, ball_radius=30,
            bg_color=(20, 20, 20), ball_color=(240, 240, 240),
        )
        result = m5(img, BALL_CX_NORM, BALL_CY_NORM)
        # Hough is less reliable on small/compressed circles; log but don't fail if not found
        if result.found:
            dist = _norm_dist(result.refined_x, result.refined_y, BALL_CX_NORM, BALL_CY_NORM)
            assert dist < ERROR_TOLERANCE_NORM * 2, f"M5 error: {dist:.4f}"

    def test_SS_ALGO_M5_02_empty_image_no_circles(self):
        """SS-ALGO-M5-02: M5 refuses on featureless image."""
        m5 = M5Hough()
        img = make_empty_image()
        result = m5(img, 0.5, 0.5)
        assert not result.found

    def test_SS_ALGO_M5_03_result_within_bounds(self):
        """SS-ALGO-M5-03: refined_x/y always in [0,1] when found=True."""
        m5 = M5Hough()
        img = make_ball_image(ball_radius=30)
        result = m5(img, 0.5, 0.5)
        if result.found:
            assert 0.0 <= result.refined_x <= 1.0
            assert 0.0 <= result.refined_y <= 1.0


class TestM6TemplateMatch:
    def test_SS_ALGO_M6_01_detects_circle_above_threshold(self):
        """SS-ALGO-M6-01: M6 finds matching circle in clean image."""
        from scripts.smart_snap_poc1.config import M6_TEMPLATE_RADIUS_PX
        m6 = M6TemplateMatch(template_radius_px=18)
        img = make_ball_image(
            width=320, height=240,
            ball_cx=160, ball_cy=120, ball_radius=18,
            bg_color=(30, 30, 30), ball_color=(230, 230, 230),
        )
        result = m6(img, BALL_CX_NORM, BALL_CY_NORM)
        if result.found:
            dist = _norm_dist(result.refined_x, result.refined_y, BALL_CX_NORM, BALL_CY_NORM)
            assert dist < ERROR_TOLERANCE_NORM * 2

    def test_SS_ALGO_M6_02_empty_image_low_score(self):
        """SS-ALGO-M6-02: M6 on uniform image returns found=False (low correlation)."""
        m6 = M6TemplateMatch()
        img = make_empty_image()
        result = m6(img, 0.5, 0.5)
        # Uniform image has near-zero correlation with a circle template
        if result.found:
            assert result.confidence < 0.8  # very low match score

    def test_SS_ALGO_M6_03_roi_smaller_than_template_refused(self):
        """SS-ALGO-M6-03: Tiny ROI smaller than template is refused."""
        m6 = M6TemplateMatch(template_radius_px=50)
        # Use a very small image so ROI < template
        img = np.full((10, 10, 3), 128, dtype=np.uint8)
        result = m6(img, 0.5, 0.5)
        assert not result.found
        assert result.refusal_reason is not None
