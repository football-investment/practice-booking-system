"""
M6 — Template matching experiment.

Builds a synthetic filled-circle template and runs cv2.matchTemplate
(TM_CCOEFF_NORMED) within a tap-centred ROI.

NOTE: This is a template matching experiment — NOT a stored SSD inference.
It uses a synthetic 2-D circle template, not a trained neural network.
"""
from __future__ import annotations

import cv2
import numpy as np

from ..config import M6_ROI_RATIO, M6_TEMPLATE_RADIUS_PX
from .base import BaseSnapAlgorithm, SnapResult, compute_roi

_TEMPLATE_SCORE_THRESHOLD = 0.3  # TM_CCOEFF_NORMED below this → refusal


def _build_circle_template(radius_px: int) -> np.ndarray:
    """Return a uint8 grayscale image with a filled white circle on black."""
    side = radius_px * 2 + 4
    template = np.zeros((side, side), dtype=np.uint8)
    cv2.circle(template, (side // 2, side // 2), radius_px, 255, -1)
    return template


class M6TemplateMatch(BaseSnapAlgorithm):
    """Template matching snap: synthetic circle against ROI greyscale."""

    name = "M6_template_match"

    def __init__(self, template_radius_px: int = M6_TEMPLATE_RADIUS_PX) -> None:
        self._template = _build_circle_template(template_radius_px)
        self._template_radius = template_radius_px

    def snap(
        self,
        img_rgb: np.ndarray,
        tap_x_norm: float,
        tap_y_norm: float,
        **kwargs,
    ) -> SnapResult:
        h, w = img_rgb.shape[:2]
        x1, y1, x2, y2 = compute_roi(tap_x_norm, tap_y_norm, M6_ROI_RATIO, w, h)
        if x2 <= x1 or y2 <= y1:
            return SnapResult(found=False, refusal_reason="roi_degenerate")

        roi = img_rgb[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)

        th, tw = self._template.shape
        if gray.shape[0] < th or gray.shape[1] < tw:
            return SnapResult(found=False, refusal_reason="roi_smaller_than_template")

        result = cv2.matchTemplate(gray, self._template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val < _TEMPLATE_SCORE_THRESHOLD:
            return SnapResult(
                found=False,
                refusal_reason=f"low_match_score_{max_val:.3f}",
                confidence=max_val,
            )

        # max_loc is top-left of template match; centre = max_loc + template_half
        cx_roi = max_loc[0] + tw // 2
        cy_roi = max_loc[1] + th // 2
        cx_norm = (cx_roi + x1) / w
        cy_norm = (cy_roi + y1) / h

        return SnapResult(
            found=True,
            refined_x=cx_norm,
            refined_y=cy_norm,
            confidence=max_val,
        )
