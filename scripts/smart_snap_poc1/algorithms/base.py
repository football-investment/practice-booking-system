"""Shared types for all snap algorithms."""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

from ..config import (
    M4_ROI_RATIO, M5_ROI_RATIO, M6_ROI_RATIO,
)


@dataclass
class SnapResult:
    """Uniform output for every snap algorithm."""
    found: bool
    refined_x: Optional[float] = None      # normalised [0,1]; None if not found
    refined_y: Optional[float] = None
    confidence: float = 0.0                # algorithm-specific quality score
    refusal_reason: Optional[str] = None   # set when found=False
    latency_ms: float = 0.0               # wall-clock time for the snap call


def compute_roi(
    tap_x_norm: float,
    tap_y_norm: float,
    roi_ratio: float,
    img_w: int,
    img_h: int,
) -> tuple[int, int, int, int]:
    """
    Compute a clamped square ROI around a normalised tap point.

    Returns (x1, y1, x2, y2) in pixel coordinates, always within [0, img_w] × [0, img_h].
    The half-side is roi_ratio × min(img_w, img_h).
    """
    cx_px = tap_x_norm * img_w
    cy_px = tap_y_norm * img_h
    half = roi_ratio * min(img_w, img_h)
    x1 = max(0, int(cx_px - half))
    y1 = max(0, int(cy_px - half))
    x2 = min(img_w, int(cx_px + half))
    y2 = min(img_h, int(cy_px + half))
    return x1, y1, x2, y2


class BaseSnapAlgorithm:
    """Callable mixin that wraps snap() with timing."""

    name: str = "base"

    def snap(
        self,
        img_rgb: np.ndarray,
        tap_x_norm: float,
        tap_y_norm: float,
        **kwargs,
    ) -> SnapResult:
        raise NotImplementedError

    def __call__(
        self,
        img_rgb: np.ndarray,
        tap_x_norm: float,
        tap_y_norm: float,
        **kwargs,
    ) -> SnapResult:
        t0 = time.perf_counter()
        result = self.snap(img_rgb, tap_x_norm, tap_y_norm, **kwargs)
        result.latency_ms = (time.perf_counter() - t0) * 1000.0
        return result
