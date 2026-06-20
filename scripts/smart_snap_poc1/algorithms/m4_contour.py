"""
M4 — Local contour snap.

Extracts a square ROI around the input tap, applies Canny edge detection,
finds contours, and picks the most circular contour closest to the tap.
"""
from __future__ import annotations

import math

import cv2
import numpy as np

from ..config import (
    M4_CANNY_HIGH,
    M4_CANNY_LOW,
    M4_CIRCULARITY_MIN,
    M4_MIN_CONTOUR_AREA_PX,
    M4_ROI_RATIO,
)
from .base import BaseSnapAlgorithm, SnapResult, compute_roi


class M4Contour(BaseSnapAlgorithm):
    """Canny + findContours snap within a tap-centred ROI."""

    name = "M4_contour"

    def snap(
        self,
        img_rgb: np.ndarray,
        tap_x_norm: float,
        tap_y_norm: float,
        **kwargs,
    ) -> SnapResult:
        h, w = img_rgb.shape[:2]
        x1, y1, x2, y2 = compute_roi(tap_x_norm, tap_y_norm, M4_ROI_RATIO, w, h)
        if x2 <= x1 or y2 <= y1:
            return SnapResult(found=False, refusal_reason="roi_degenerate")

        roi = img_rgb[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, M4_CANNY_LOW, M4_CANNY_HIGH)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return SnapResult(found=False, refusal_reason="no_contours")

        tap_px_roi = np.array([
            tap_x_norm * w - x1,
            tap_y_norm * h - y1,
        ])

        best_result = None
        best_score = float("inf")

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < M4_MIN_CONTOUR_AREA_PX:
                continue
            perimeter = cv2.arcLength(cnt, True)
            if perimeter == 0:
                continue
            circularity = 4.0 * math.pi * area / (perimeter ** 2)
            if circularity < M4_CIRCULARITY_MIN:
                continue
            M = cv2.moments(cnt)
            if M["m00"] == 0:
                continue
            cx_roi = M["m10"] / M["m00"]
            cy_roi = M["m01"] / M["m00"]
            dist = math.hypot(cx_roi - tap_px_roi[0], cy_roi - tap_px_roi[1])
            # Lower score = closer + more circular
            score = dist / circularity
            if score < best_score:
                best_score = score
                # Back-project to full-frame pixel, then normalise
                cx_full = (cx_roi + x1) / w
                cy_full = (cy_roi + y1) / h
                best_result = (cx_full, cy_full, circularity)

        if best_result is None:
            return SnapResult(found=False, refusal_reason="no_circular_contour")

        cx_norm, cy_norm, circ = best_result
        return SnapResult(
            found=True,
            refined_x=cx_norm,
            refined_y=cy_norm,
            confidence=circ,
        )
