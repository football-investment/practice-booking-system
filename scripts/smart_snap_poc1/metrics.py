"""
Metric calculation for Smart Snap POC-1 benchmark.

All pixel-error metrics use a 1920-pixel reference width so numbers are
comparable across frames of different resolutions.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np

REF_WIDTH_PX = 1920.0  # normalisation reference


def pixel_error(
    pred_x: float,
    pred_y: float,
    gt_x: float,
    gt_y: float,
    img_w: int,
    img_h: int,
) -> float:
    """
    Euclidean error in pixels, scaled to a 1920-wide reference frame.

    Normalised coords [0,1] × [0,1] are expanded to actual pixel coords
    using img_w/img_h, then the error is re-scaled so results are
    resolution-independent and comparable to "how big is the ball on screen."
    """
    scale = REF_WIDTH_PX / img_w
    dx = (pred_x - gt_x) * img_w * scale
    dy = (pred_y - gt_y) * img_h * scale
    return math.hypot(dx, dy)


def aggregate(values: list[float]) -> dict:
    """Return mean/median/p90/p95 for a list of numeric values."""
    if not values:
        return {"mean": None, "median": None, "p90": None, "p95": None, "n": 0}
    arr = np.array(values, dtype=float)
    return {
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "p90": float(np.percentile(arr, 90)),
        "p95": float(np.percentile(arr, 95)),
        "n": len(values),
    }


def wrong_snap_rate(
    snap_errors: list[float],
    baseline_errors: list[float],
) -> Optional[float]:
    """
    Fraction of frames where the snap INCREASED error vs the baseline.

    A wrong-snap occurs when snap_error > baseline_error for the same frame.
    Returns None if lists are empty or mismatched.
    """
    if not snap_errors or len(snap_errors) != len(baseline_errors):
        return None
    wrong = sum(
        1 for s, b in zip(snap_errors, baseline_errors) if s > b
    )
    return wrong / len(snap_errors)


def false_positive_rate(
    no_ball_results: list[bool],
) -> Optional[float]:
    """
    Fraction of no-ball frames where the algorithm returned found=True.
    """
    if not no_ball_results:
        return None
    return sum(no_ball_results) / len(no_ball_results)


def false_refusal_rate(
    positive_results: list[bool],
) -> Optional[float]:
    """
    Fraction of positive (has-ball) frames where the algorithm returned found=False.
    """
    if not positive_results:
        return None
    refusals = sum(1 for found in positive_results if not found)
    return refusals / len(positive_results)


def latency_summary(latencies_ms: list[float]) -> dict:
    """p50 / p95 latency from a list of millisecond timings."""
    if not latencies_ms:
        return {"p50_ms": None, "p95_ms": None, "n": 0}
    arr = np.array(latencies_ms, dtype=float)
    return {
        "p50_ms": float(np.percentile(arr, 50)),
        "p95_ms": float(np.percentile(arr, 95)),
        "n": len(latencies_ms),
    }
