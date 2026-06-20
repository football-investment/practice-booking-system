"""SS-COORD: Coordinate normalisation and ROI clamping tests."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.smart_snap_poc1.algorithms.base import compute_roi
from scripts.smart_snap_poc1.metrics import pixel_error


class TestROIClamp:
    def test_SS_COORD_01_roi_within_image(self):
        """SS-COORD-01: ROI is always within image bounds."""
        for tap_x, tap_y in [(0.0, 0.0), (1.0, 1.0), (0.5, 0.5), (0.1, 0.9)]:
            x1, y1, x2, y2 = compute_roi(tap_x, tap_y, 0.12, 640, 480)
            assert x1 >= 0
            assert y1 >= 0
            assert x2 <= 640
            assert y2 <= 480

    def test_SS_COORD_02_roi_top_left_corner(self):
        """SS-COORD-02: Tap at (0,0) clamps ROI to image boundary."""
        x1, y1, x2, y2 = compute_roi(0.0, 0.0, 0.12, 640, 480)
        assert x1 == 0
        assert y1 == 0
        assert x2 > 0
        assert y2 > 0

    def test_SS_COORD_03_roi_bottom_right_corner(self):
        """SS-COORD-03: Tap at (1,1) clamps ROI to image boundary."""
        x1, y1, x2, y2 = compute_roi(1.0, 1.0, 0.12, 640, 480)
        assert x1 >= 0
        assert y1 >= 0
        assert x2 == 640
        assert y2 == 480

    def test_SS_COORD_04_roi_centred(self):
        """SS-COORD-04: ROI centred on tap is symmetric when not clamped."""
        x1, y1, x2, y2 = compute_roi(0.5, 0.5, 0.12, 640, 480)
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        assert abs(cx - 320) <= 2  # within 1px rounding
        assert abs(cy - 240) <= 2

    def test_SS_COORD_05_roi_is_square(self):
        """SS-COORD-05: ROI width == ROI height for square images."""
        x1, y1, x2, y2 = compute_roi(0.5, 0.5, 0.12, 480, 480)
        assert (x2 - x1) == (y2 - y1)

    def test_SS_COORD_06_roi_uses_min_side(self):
        """SS-COORD-06: ROI half-side uses min(W,H), not W or H independently."""
        # For a 640×480 image, min_side=480, half = 0.12 * 480 = 57.6 → 57
        x1, y1, x2, y2 = compute_roi(0.5, 0.5, 0.12, 640, 480)
        half = int(0.12 * min(640, 480))
        width = x2 - x1
        assert abs(width - 2 * half) <= 2


class TestPixelError:
    def test_SS_COORD_07_zero_error(self):
        """SS-COORD-07: Identical prediction and GT → 0 error."""
        err = pixel_error(0.5, 0.5, 0.5, 0.5, 640, 480)
        assert err == 0.0

    def test_SS_COORD_08_horizontal_shift(self):
        """SS-COORD-08: 1px horizontal shift at 1920-ref scale."""
        # 1px at 1920 = 1/1920 normalised
        shift = 1.0 / 1920.0
        err = pixel_error(0.5 + shift, 0.5, 0.5, 0.5, 1920, 1080)
        assert abs(err - 1.0) < 0.01

    def test_SS_COORD_09_diagonal_error_pythagoras(self):
        """SS-COORD-09: Diagonal error follows Euclidean distance."""
        # 3px + 4px diagonal → 5px
        shift_x = 3.0 / 1920.0
        shift_y = 4.0 / 1080.0
        err = pixel_error(0.5 + shift_x, 0.5 + shift_y, 0.5, 0.5, 1920, 1080)
        assert abs(err - 5.0) < 0.1

    def test_SS_COORD_10_resolution_scaled_to_1920(self):
        """SS-COORD-10: Error scales to 1920 reference regardless of actual resolution."""
        # 10px at 640 = 30px at 1920
        shift = 10.0 / 640.0
        err = pixel_error(0.5 + shift, 0.5, 0.5, 0.5, 640, 480)
        assert abs(err - 30.0) < 0.5
