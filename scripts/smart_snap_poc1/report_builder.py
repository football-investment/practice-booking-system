"""
report_builder.py — importable module for Smart Snap POC-1 report generation.

04_report.py is a thin CLI wrapper around build_report().
Tests import from here (module names starting with digits cannot be imported).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional

from scripts.smart_snap_poc1.config import TARGET_CATEGORIES

# Acceptance gate thresholds
GATE_WRONG_SNAP_MAX = 0.05          # < 5%
GATE_NO_BALL_FP_MAX = 0.10          # < 10%
GATE_LATENCY_P95_MS = 500.0         # < 500ms (Python benchmark; iOS gated on POC-2)
GATE_MIN_GT_FRAMES = 15             # minimum GT frames for meaningful verdict


def _load(path: str) -> Optional[dict]:
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _fmt(val, fmt=".1f", suffix=""):
    if val is None:
        return "N/A"
    return f"{val:{fmt}}{suffix}"


def _pct(val):
    if val is None:
        return "N/A"
    return f"{val:.1%}"


def _pass_fail(condition: Optional[bool], na_if_none: bool = True) -> str:
    if condition is None:
        return "N/A" if na_if_none else "UNKNOWN"
    return "✅ PASS" if condition else "❌ FAIL"


def build_report(
    results: dict,
    manifest: Optional[dict],
    gt_data: Optional[dict],
) -> str:
    """Build the full report.md content string from benchmark_results.json."""
    lines: list[str] = []
    agg = results.get("aggregated", {})
    per_frame = results.get("per_frame", [])
    summary = results.get("summary", {})

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    total_frames = summary.get("total_frames", 0)
    frames_with_gt = summary.get("frames_with_gt", 0)
    no_ball = summary.get("no_ball_frames", 0)
    type_a = sum(1 for f in per_frame if f.get("type") == "A")
    type_b = sum(1 for f in per_frame if f.get("type") == "B")

    lines += [
        "# Smart Snap POC-1 — Benchmark Report",
        "",
        f"Generated: {now}  ",
        "Source: `benchmark_results.json`",
        "",
        "---",
        "",
        "## 1. Dataset Overview",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total frames in manifest | {total_frames} |",
        f"| Type A (human-corrected from DB) | {type_a} |",
        f"| Type B (fresh from other videos) | {type_b} |",
        f"| Frames with GT (gt_final available) | {frames_with_gt} |",
        f"| No-ball frames | {no_ball} |",
        "",
    ]

    cat_counts: dict[str, int] = {}
    for f in per_frame:
        cat = f.get("category") or "unassigned"
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    lines += [
        "### Category distribution",
        "",
        "| Category | Count | Coverage |",
        "|----------|-------|----------|",
    ]
    for cat in sorted(TARGET_CATEGORIES + ["unassigned", "no_ball"]):
        n = cat_counts.get(cat, 0)
        note = "⚠ MISSING" if n == 0 and cat not in ("unassigned",) else ""
        lines.append(f"| {cat} | {n} | {note} |")

    # ── GT Quality ─────────────────────────────────────────────────────────
    provenances: dict[str, int] = {}
    agreements: list[float] = []
    review_required_count = 0
    for f in per_frame:
        prov = f.get("gt_provenance") or "none"
        provenances[prov] = provenances.get(prov, 0) + 1
        agr = f.get("gt_agreement_px")
        if agr is not None:
            agreements.append(agr)
        if f.get("gt_review_required"):
            review_required_count += 1

    avg_agreement = sum(agreements) / len(agreements) if agreements else None

    lines += [
        "",
        "---",
        "",
        "## 2. Ground Truth Quality",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| GT frames | {frames_with_gt} |",
        f"| Avg inter-round agreement (px) | {_fmt(avg_agreement)} |",
        f"| Frames requiring manual review | {review_required_count} |",
        f"| GT provenance — seeded_from_db_round1 | {provenances.get('seeded_from_db_round1', 0)} |",
        f"| GT provenance — two_round_average | {provenances.get('two_round_average', 0)} |",
        "",
        "> ⚠ **GT independence limitation**: Type A frames where Round 1 was seeded from",
        "> `corrected_x/y` may be influenced by model overlay visible during original E2E session.",
        "> Full independence requires a fresh human-annotation session without model reference.",
        "",
        "---",
        "",
        "## 3. Method Comparison — TÉNYLEGESEN MÉRT (Measured on extracted frames)",
        "",
        "> iOS latency: **N/A** — Python/OpenCV benchmark only.  ",
        "> iOS VNDetectContoursRequest benchmark required in POC-2.",
        "",
        "### 3a. Pixel Error (vs GT, 1920px-reference, lower = better)",
        "",
        "| Method | Mean | Median | p90 | p95 | n |",
        "|--------|------|--------|-----|-----|---|",
    ]

    method_order = [
        "M1_synthetic_raw_tap",
        "M2_human_loupe_tap",
        "M3_stored_ssd",
        "M4_contour",
        "M5_hough",
        "M6_template_match",
    ]

    for method in method_order:
        stats = agg.get(method, {})
        ov = stats.get("overall", {})
        n = ov.get("n", 0)
        source_tag = " *(SYNTHETIC)*" if method == "M1_synthetic_raw_tap" else ""
        lines.append(
            f"| {method}{source_tag} | "
            f"{_fmt(ov.get('mean'))} | "
            f"{_fmt(ov.get('median'))} | "
            f"{_fmt(ov.get('p90'))} | "
            f"{_fmt(ov.get('p95'))} | "
            f"{n} |"
        )

    lines += [
        "",
        "> M1 = Monte Carlo simulation (σ=3% frame width, N=100/frame). **Not from real human taps.**",
        "> M2 = Human loupe tap from ground_truth.json.",
        "",
        "### 3b. Wrong-snap rate & false positive/refusal",
        "",
        "| Method | Wrong-snap vs M1 | FP rate (no-ball) | False-refusal (positive) |",
        "|--------|-----------------|-------------------|--------------------------|",
    ]

    for method in method_order[2:]:
        stats = agg.get(method, {})
        wsr = stats.get("wrong_snap_rate_vs_m1")
        fpr = stats.get("false_positive_rate")
        frr = stats.get("false_refusal_rate")
        lines.append(f"| {method} | {_pct(wsr)} | {_pct(fpr)} | {_pct(frr)} |")

    # ── Per category ────────────────────────────────────────────────────────
    all_cats = sorted({
        cat
        for stats in agg.values()
        for cat in stats.get("by_category", {}).keys()
    })

    lines += ["", "---", "", "## 4. Per-category Breakdown", ""]
    for cat in all_cats:
        lines += [f"### Category: `{cat}`", "", "| Method | Mean px error | n |", "|--------|--------------|---|"]
        for method in method_order:
            s = agg.get(method, {}).get("by_category", {}).get(cat)
            if s:
                lines.append(f"| {method} | {_fmt(s.get('mean'))} | {s.get('n', 0)} |")
        lines.append("")

    # ── Latency ─────────────────────────────────────────────────────────────
    lines += [
        "---",
        "",
        "## 5. Latency — TÉNYLEGESEN MÉRT (Python/OpenCV)",
        "",
        "> **iOS VNDetectContoursRequest latency: N/A — POC-2 physical iPhone benchmark required.**",
        "",
        "| Method | p50 (ms) | p95 (ms) | n |",
        "|--------|----------|----------|---|",
    ]
    for method in method_order[2:]:
        lat = agg.get(method, {}).get("latency", {})
        lines.append(
            f"| {method} | {_fmt(lat.get('p50_ms'))} | {_fmt(lat.get('p95_ms'))} | {lat.get('n', 0)} |"
        )

    # ── Acceptance gates ────────────────────────────────────────────────────
    algo_methods = ["M3_stored_ssd", "M4_contour", "M5_hough", "M6_template_match"]

    m1_mean = agg.get("M1_synthetic_raw_tap", {}).get("overall", {}).get("mean")
    best_mean, best_for_mean = None, None
    best_wsr, best_for_wsr = None, None
    best_fpr_v, best_for_fpr = None, None
    best_lat_v, best_for_lat = None, None

    for m in algo_methods:
        v = agg.get(m, {}).get("overall", {}).get("mean")
        if v is not None and (best_mean is None or v < best_mean):
            best_mean, best_for_mean = v, m
        v = agg.get(m, {}).get("wrong_snap_rate_vs_m1")
        if v is not None and (best_wsr is None or v < best_wsr):
            best_wsr, best_for_wsr = v, m
        v = agg.get(m, {}).get("false_positive_rate")
        if v is not None and (best_fpr_v is None or v < best_fpr_v):
            best_fpr_v, best_for_fpr = v, m
        v = agg.get(m, {}).get("latency", {}).get("p95_ms")
        if v is not None and (best_lat_v is None or v < best_lat_v):
            best_lat_v, best_for_lat = v, m

    gate1 = bool(best_mean is not None and m1_mean is not None and best_mean < m1_mean)
    gate2 = bool(best_wsr is not None and best_wsr < GATE_WRONG_SNAP_MAX)
    gate3 = (bool(best_fpr_v < GATE_NO_BALL_FP_MAX) if best_fpr_v is not None else None)
    gate4 = bool(best_lat_v is not None and best_lat_v < GATE_LATENCY_P95_MS)

    lines += [
        "",
        "---",
        "",
        "## 6. Acceptance Gate Evaluation",
        "",
        "| Gate | Threshold | Best Method | Value | Status |",
        "|------|-----------|-------------|-------|--------|",
        f"| Improves over raw tap (mean px) | < M1={_fmt(m1_mean)}px | {best_for_mean or '—'} | {_fmt(best_mean)}px | {_pass_fail(gate1)} |",
        f"| Wrong-snap rate | < {GATE_WRONG_SNAP_MAX:.0%} | {best_for_wsr or '—'} | {_pct(best_wsr)} | {_pass_fail(gate2)} |",
        f"| No-ball FP rate | < {GATE_NO_BALL_FP_MAX:.0%} | {best_for_fpr or '—'} | {_pct(best_fpr_v)} | {_pass_fail(gate3)} |",
        f"| Latency p95 (Python) | < {GATE_LATENCY_P95_MS:.0f}ms | {best_for_lat or '—'} | {_fmt(best_lat_v)}ms | {_pass_fail(gate4)} |",
        "| iOS latency p95 | < 500ms | — | N/A | 🔲 POC-2 required |",
        "",
        "> ⚠ **All gate evaluations above are on the Python/OpenCV benchmark.**",
        "> **Production acceptance requires POC-2 (iOS VNDetectContoursRequest on physical device).**",
    ]

    # ── Limitations ─────────────────────────────────────────────────────────
    missing_cats = [c for c in TARGET_CATEGORIES if cat_counts.get(c, 0) == 0 and c != "no_ball"]
    lines += [
        "",
        "---",
        "",
        "## 7. Limitations & Open Gaps",
        "",
        "### HIPOTÉZISEK (not measured in POC-1)",
        "",
        "1. iOS latency — hypothesis: p95 < 200ms on iPhone 13+. Not measured.",
        "2. Motion blur degrades Canny contour detection. Not categorised automatically.",
        "3. Small ball (< 15px radius) may cause Hough failure. Headroom via MIN_RADIUS_PX=4.",
        "",
        "### BECSLÉSEK (informed but not directly measured)",
        "",
        "- M1 σ=0.03 normalised ≈ 58px at 1920×1080. Calibrated from typical touch jitter; **not from real E2E tap logs**.",
        "",
        "### TÉNYLEGESEN MÉRT (directly measured)",
        "",
        "- Pixel errors for M3/M4/M5/M6 on all GT frames.",
        "- False-positive and false-refusal rates from algorithm outputs.",
        "- Python/OpenCV latency p50/p95.",
        "",
        "### Open dataset gaps",
        "",
        "| Gap | Impact |",
        "|-----|--------|",
        "| GT Round 1 seeded from model overlay data | Bias risk — may underestimate M3 error |",
        "| Only 1 video with Type A human-corrected data | Low diversity; position cluster near centre |",
        f"| Missing categories: {', '.join(missing_cats) if missing_cats else 'none'} | Coverage incomplete |",
        "| M1 baseline is synthetic only | No real human raw tap data available |",
    ]

    # ── Verdict ─────────────────────────────────────────────────────────────
    gate_scores = [gate1, gate2, gate3, gate4]
    gates_passed = sum(1 for g in gate_scores if g is True)
    gates_failed = sum(1 for g in gate_scores if g is False)
    gates_na = sum(1 for g in gate_scores if g is None)
    not_enough_gt = frames_with_gt < GATE_MIN_GT_FRAMES

    if not_enough_gt:
        verdict = "NEED MORE DATA"
        verdict_detail = f"Only {frames_with_gt} GT frames — minimum {GATE_MIN_GT_FRAMES} required for meaningful evaluation."
    elif len(missing_cats) >= 3:
        verdict = "NEED MORE DATA"
        verdict_detail = f"Missing categories: {', '.join(missing_cats)}. Cannot assess robustness across all scenarios."
    elif gates_failed >= 2:
        verdict = "REJECT APPROACH"
        verdict_detail = f"{gates_failed} acceptance gates failed. Algorithms do not demonstrate reliable improvement over raw tap."
    elif gates_passed >= 3 and gates_failed == 0:
        verdict = "PROCEED TO POC-2"
        verdict_detail = f"{gates_passed}/4 Python gates passed. iOS Vision benchmark (POC-2) required before production integration."
    else:
        verdict = "NEED MORE DATA"
        verdict_detail = f"{gates_passed} gates passed, {gates_failed} failed, {gates_na} N/A — inconclusive."

    lines += [
        "",
        "---",
        "",
        "## 8. Verdict",
        "",
        f"### {verdict}",
        "",
        f"**{verdict_detail}**",
        "",
        f"Gate summary: {gates_passed} PASS | {gates_failed} FAIL | {gates_na} N/A (Python benchmark only)",
        "",
        "---",
        "",
        f"*Report generated by `04_report.py` | {now}*",
        "",
        "> **CONSTRAINT**: Automatic snap production integration and merge only after separate explicit approval.",
    ]

    return "\n".join(lines)
