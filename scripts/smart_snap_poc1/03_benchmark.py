#!/usr/bin/env python3
"""
03_benchmark.py — Smart Snap POC-1

Runs all 6 methods against the annotated ground truth and emits
benchmark_results.json.

Methods:
  M1  Synthetic raw tap   — model_predicted_x/y + Gaussian noise (100 draws)
                            INPUT: model prediction + noise (SYNTHETIC)
  M2  Human loupe tap     — human_loupe_tap from ground_truth.json
                            Requires full annotation (loupe mode completed)
  M3  Stored SSD          — model_predicted_x/y (no image processing)
  M4  Local contour snap  — opencv findContours within ROI
  M5  ROI Hough circles   — opencv HoughCircles within ROI
  M6  Template matching   — synthetic circle template within ROI

For frames where gt_final is available, pixel error vs GT is computed.
For frames without gt_final (pending annotation), algorithms still run
but no error metric is computed (latency only).

Usage:
    python scripts/smart_snap_poc1/03_benchmark.py
    python scripts/smart_snap_poc1/03_benchmark.py --no-m6   # skip template matching
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
from PIL import Image

from scripts.smart_snap_poc1.algorithms import (
    M3StoredSSD, M4Contour, M5Hough, M6TemplateMatch, SnapResult,
)
from scripts.smart_snap_poc1.config import (
    BENCHMARK_RESULTS_PATH,
    DATASET_DIR,
    GROUND_TRUTH_PATH,
    M1_N_SIMULATIONS,
    M1_SIGMA_NORM,
    MANIFEST_PATH,
)
from scripts.smart_snap_poc1.metrics import (
    aggregate,
    false_positive_rate,
    false_refusal_rate,
    latency_summary,
    pixel_error,
    wrong_snap_rate,
)

# ── Loaders ──────────────────────────────────────────────────────────────────

def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_image(frame_id: str) -> Optional[np.ndarray]:
    path = os.path.join(DATASET_DIR, f"{frame_id}.jpg")
    if not os.path.isfile(path):
        return None
    return np.array(Image.open(path))


# ── M1: synthetic raw tap ─────────────────────────────────────────────────────

def run_m1_synthetic(
    model_x: float,
    model_y: float,
    gt_x: float,
    gt_y: float,
    img_w: int,
    img_h: int,
    rng: random.Random,
) -> dict:
    """
    Simulate N raw taps drawn from Normal(model_pred, σ) and compute
    mean pixel error against GT.  Returns per-draw errors and aggregated stats.
    """
    errors: list[float] = []
    for _ in range(M1_N_SIMULATIONS):
        tx = model_x + rng.gauss(0, M1_SIGMA_NORM)
        ty = model_y + rng.gauss(0, M1_SIGMA_NORM)
        tx = max(0.0, min(1.0, tx))
        ty = max(0.0, min(1.0, ty))
        errors.append(pixel_error(tx, ty, gt_x, gt_y, img_w, img_h))
    stats = aggregate(errors)
    return {
        "method": "M1_synthetic_raw_tap",
        "data_source": "SYNTHETIC",
        "n_draws": M1_N_SIMULATIONS,
        "sigma_norm": M1_SIGMA_NORM,
        **stats,
    }


# ── Per-frame benchmark ────────────────────────────────────────────────────────

def benchmark_frame(
    frame_id: str,
    manifest_frame: dict,
    gt_entry: Optional[dict],
    algorithms: list,
    rng: random.Random,
) -> dict:
    img = load_image(frame_id)
    img_w = manifest_frame.get("image_width_px") or 640
    img_h = manifest_frame.get("image_height_px") or 480

    has_gt = (
        gt_entry is not None
        and gt_entry.get("gt_final") is not None
        and not gt_entry.get("is_no_ball", False)
    )
    is_no_ball = (gt_entry or {}).get("is_no_ball", False)

    gt_x = gt_entry["gt_final"]["x"] if has_gt else None
    gt_y = gt_entry["gt_final"]["y"] if has_gt else None
    gt_provenance = (gt_entry or {}).get("gt_provenance", "none")
    gt_agreement_px = (gt_entry or {}).get("gt_agreement_px")
    gt_review_required = (gt_entry or {}).get("gt_review_required", False)

    model_x = manifest_frame.get("model_x")
    model_y = manifest_frame.get("model_y")
    model_conf = manifest_frame.get("model_confidence")

    results: dict = {
        "frame_id": frame_id,
        "type": manifest_frame["type"],
        "category": manifest_frame.get("category"),
        "auto_category_hints": manifest_frame.get("auto_category_hints", []),
        "has_gt": has_gt,
        "is_no_ball": is_no_ball,
        "gt_provenance": gt_provenance,
        "gt_agreement_px": gt_agreement_px,
        "gt_review_required": gt_review_required,
        "img_w": img_w,
        "img_h": img_h,
        "methods": {},
    }

    # ── M1: synthetic raw tap ────────────────────────────────────────────
    if has_gt and model_x is not None:
        results["methods"]["M1_synthetic_raw_tap"] = run_m1_synthetic(
            model_x, model_y, gt_x, gt_y, img_w, img_h, rng
        )
    else:
        results["methods"]["M1_synthetic_raw_tap"] = {
            "method": "M1_synthetic_raw_tap",
            "skipped": True,
            "reason": "no_model_prediction" if model_x is None else "no_gt",
        }

    # ── M2: human loupe tap ──────────────────────────────────────────────
    human_loupe = (gt_entry or {}).get("human_loupe_tap")
    if human_loupe and has_gt:
        err = pixel_error(human_loupe["x"], human_loupe["y"], gt_x, gt_y, img_w, img_h)
        results["methods"]["M2_human_loupe_tap"] = {
            "method": "M2_human_loupe_tap",
            "data_source": "HUMAN_MEASURED",
            "pixel_error": err,
            "found": True,
        }
    else:
        results["methods"]["M2_human_loupe_tap"] = {
            "method": "M2_human_loupe_tap",
            "skipped": True,
            "reason": "no_human_loupe_annotation" if not human_loupe else "no_gt",
        }

    # ── M3–M6: algorithm-based methods ──────────────────────────────────
    # Use model prediction as the input "tap" for all algorithm methods
    tap_x = model_x if model_x is not None else 0.5
    tap_y = model_y if model_y is not None else 0.5

    for algo in algorithms:
        algo_name = algo.name
        if img is None:
            results["methods"][algo_name] = {
                "method": algo_name,
                "skipped": True,
                "reason": "image_not_extracted",
            }
            continue

        snap_result: SnapResult = algo(
            img,
            tap_x,
            tap_y,
            model_x=model_x,
            model_y=model_y,
            model_confidence=model_conf,
        )

        entry: dict = {
            "method": algo_name,
            "data_source": "ALGORITHM",
            "found": snap_result.found,
            "refined_x": snap_result.refined_x,
            "refined_y": snap_result.refined_y,
            "confidence": snap_result.confidence,
            "refusal_reason": snap_result.refusal_reason,
            "latency_ms": snap_result.latency_ms,
        }

        if has_gt and snap_result.found and snap_result.refined_x is not None:
            entry["pixel_error"] = pixel_error(
                snap_result.refined_x, snap_result.refined_y,
                gt_x, gt_y, img_w, img_h,
            )

        # For no-ball frames: track false positive
        if is_no_ball:
            entry["false_positive"] = snap_result.found

        results["methods"][algo_name] = entry

    return results


# ── Aggregate across all frames ────────────────────────────────────────────────

def aggregate_results(frame_results: list[dict]) -> dict:
    method_names = set()
    for fr in frame_results:
        method_names.update(fr["methods"].keys())

    aggregated: dict = {}
    categories = list({fr.get("category") or "unassigned" for fr in frame_results})

    for method in sorted(method_names):
        errors_all: list[float] = []
        errors_by_cat: dict[str, list[float]] = {c: [] for c in categories}
        latencies: list[float] = []
        no_ball_fp: list[bool] = []
        positive_found: list[bool] = []
        m1_means: list[float] = []  # for M1: use mean of simulation

        for fr in frame_results:
            m = fr["methods"].get(method, {})
            if m.get("skipped"):
                continue

            lat = m.get("latency_ms")
            if lat is not None:
                latencies.append(lat)

            if fr.get("is_no_ball"):
                fp = m.get("false_positive")
                if fp is not None:
                    no_ball_fp.append(fp)
                continue

            if fr.get("has_gt"):
                err = m.get("pixel_error") or m.get("mean")  # M1 uses 'mean'
                if err is not None:
                    errors_all.append(err)
                    cat = fr.get("category") or "unassigned"
                    errors_by_cat.setdefault(cat, []).append(err)

            found = m.get("found")
            if found is not None:
                positive_found.append(bool(found))

        # M1 baseline for wrong_snap comparison
        m1_baseline = [
            fr["methods"].get("M1_synthetic_raw_tap", {}).get("mean")
            for fr in frame_results
            if fr.get("has_gt") and not fr.get("is_no_ball")
            and not fr["methods"].get(method, {}).get("skipped")
        ]
        snap_for_wsr = [
            fr["methods"].get(method, {}).get("pixel_error")
            or fr["methods"].get(method, {}).get("mean")
            for fr in frame_results
            if fr.get("has_gt") and not fr.get("is_no_ball")
            and not fr["methods"].get(method, {}).get("skipped")
        ]
        # Filter paired None
        paired = [(s, b) for s, b in zip(snap_for_wsr, m1_baseline) if s is not None and b is not None]
        snap_list = [p[0] for p in paired]
        base_list = [p[1] for p in paired]

        aggregated[method] = {
            "overall": aggregate(errors_all),
            "by_category": {cat: aggregate(vals) for cat, vals in errors_by_cat.items() if vals},
            "latency": latency_summary(latencies),
            "wrong_snap_rate_vs_m1": wrong_snap_rate(snap_list, base_list),
            "false_positive_rate": false_positive_rate(no_ball_fp) if no_ball_fp else None,
            "false_refusal_rate": false_refusal_rate(positive_found) if positive_found else None,
        }

    return aggregated


# ── Main ─────────────────────────────────────────────────────────────────────

def run(include_m6: bool = True) -> None:
    if not os.path.isfile(MANIFEST_PATH):
        print("ERROR: manifest.json missing. Run 00_audit_eligible_frames.py.", file=sys.stderr)
        sys.exit(1)

    manifest = load_json(MANIFEST_PATH)
    gt: dict = {}
    if os.path.isfile(GROUND_TRUTH_PATH):
        gt = load_json(GROUND_TRUTH_PATH).get("frames", {})

    algorithms = [M3StoredSSD(), M4Contour(), M5Hough()]
    if include_m6:
        algorithms.append(M6TemplateMatch())

    rng = random.Random(42)
    frame_results: list[dict] = []

    for frame in manifest["frames"]:
        frame_id = frame["frame_id"]
        gt_entry = gt.get(frame_id)
        print(f"  Processing {frame_id} (type={frame['type']}, gt={'✓' if gt_entry else '—'})")
        fr = benchmark_frame(frame_id, frame, gt_entry, algorithms, rng)
        frame_results.append(fr)

    agg = aggregate_results(frame_results)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "poc": "smart_snap_poc1",
        "schema_version": "1.0",
        "summary": {
            "total_frames": len(frame_results),
            "frames_with_gt": sum(1 for fr in frame_results if fr["has_gt"]),
            "no_ball_frames": sum(1 for fr in frame_results if fr["is_no_ball"]),
            "algorithms": [a.name for a in algorithms],
        },
        "per_frame": frame_results,
        "aggregated": agg,
    }

    with open(BENCHMARK_RESULTS_PATH, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2, default=str)

    print(f"\nBenchmark complete → benchmark_results.json")
    print(f"  Frames: {output['summary']['total_frames']} total, "
          f"{output['summary']['frames_with_gt']} with GT, "
          f"{output['summary']['no_ball_frames']} no-ball")
    print("\n  Method overview (mean pixel error on GT frames):")
    for method, stats in agg.items():
        overall = stats["overall"]
        mean_str = f"{overall['mean']:.1f}px" if overall["mean"] is not None else "N/A"
        wsr_str = f"{stats['wrong_snap_rate_vs_m1']:.1%}" if stats["wrong_snap_rate_vs_m1"] is not None else "N/A"
        print(f"    {method:<30} mean={mean_str:<10} wrong_snap_rate={wsr_str}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Smart Snap POC-1 benchmark.")
    parser.add_argument("--no-m6", action="store_true", help="Skip M6 template matching.")
    args = parser.parse_args()
    run(include_m6=not args.no_m6)
