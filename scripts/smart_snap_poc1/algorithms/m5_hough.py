"""
M5 — ROI Hough circle detector.

Applies HoughCircles within a tap-centred ROI.
Returns the circle centre closest to the tap point.
"""
from __future__ import annotations

import math

import cv2
import numpy as np

from ..config import (
    M5_HOUGH_DP,
    M5_HOUGH_MAX_RADIUS_PX,
    M5_HOUGH_MIN_RADIUS_PX,
    M5_HOUGH_PARAM1,
    M5_HOUGH_PARAM2,
    M5_ROI_RATIO,
)
from .base import BaseSnapAlgorithm, SnapResult, compute_roi


class M5Hough(BaseSnapAlgorithm):
    """HoughCircles snap within a tap-centred ROI."""

    name = "M5_hough"

    def snap(
        self,
        img_rgb: np.ndarray,
        tap_x_norm: float,
        tap_y_norm: float,
        **kwargs,
    ) -> SnapResult:
        h, w = img_rgb.shape[:2]
        x1, y1, x2, y2 = compute_roi(tap_x_norm, tap_y_norm, M5_ROI_RATIO, w, h)
        if x2 <= x1 or y2 <= y1:
            return SnapResult(found=False, refusal_reason="roi_degenerate")

        roi = img_rgb[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
        blur = cv2.GaussianBlur(gray, (9, 9), 2)

        circles = cv2.HoughCircles(
            blur,
            cv2.HOUGH_GRADIENT,
            dp=M5_HOUGH_DP,
            minDist=max(1, blur.shape[0] // 4),
            param1=M5_HOUGH_PARAM1,
            param2=M5_HOUGH_PARAM2,
            minRadius=M5_HOUGH_MIN_RADIUS_PX,
            maxRadius=min(M5_HOUGH_MAX_RADIUS_PX, blur.shape[0] // 2),
        )

        if circles is None:
            return SnapResult(found=False, refusal_reason="no_hough_circles")

        circles = np.round(circles[0]).astype(int)
        tap_px_roi = np.array([
            tap_x_norm * w - x1,
            tap_y_norm * h - y1,
        ])

        best_circle = min(
            circles,
            key=lambda c: math.hypot(c[0] - tap_px_roi[0], c[1] - tap_px_roi[1]),
        )
        cx_norm = (best_circle[0] + x1) / w
        cy_norm = (best_circle[1] + y1) / h
        radius_norm = best_circle[2] / min(w, h)

        return SnapResult(
            found=True,
            refined_x=cx_norm,
            refined_y=cy_norm,
            confidence=radius_norm,
        )
