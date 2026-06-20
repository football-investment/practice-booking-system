"""
M3 — Stored SSD prediction.

Returns the model's stored ball_x / ball_y from the trajectory table,
ignoring the tap position entirely. No image processing is done.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from .base import BaseSnapAlgorithm, SnapResult


class M3StoredSSD(BaseSnapAlgorithm):
    """Return the stored model prediction unchanged."""

    name = "M3_stored_ssd"

    def snap(
        self,
        img_rgb: np.ndarray,
        tap_x_norm: float,
        tap_y_norm: float,
        model_x: Optional[float] = None,
        model_y: Optional[float] = None,
        model_confidence: Optional[float] = None,
        **kwargs,
    ) -> SnapResult:
        if model_x is None or model_y is None:
            return SnapResult(found=False, refusal_reason="no_model_prediction")
        conf = float(model_confidence) if model_confidence is not None else 0.0
        return SnapResult(
            found=True,
            refined_x=float(model_x),
            refined_y=float(model_y),
            confidence=conf,
        )
