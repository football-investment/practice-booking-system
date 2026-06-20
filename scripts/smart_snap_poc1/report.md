# Smart Snap POC-1 — Benchmark Report

Generated: 2026-06-20 11:08 UTC  
Source: `benchmark_results.json`

---

## 1. Dataset Overview

| Metric | Value |
|--------|-------|
| Total frames in manifest | 50 |
| Type A (human-corrected from DB) | 34 |
| Type B (fresh from other videos) | 16 |
| Frames with GT (gt_final available) | 34 |
| No-ball frames | 0 |

### Category distribution

| Category | Count | Coverage |
|----------|-------|----------|
| clear_ball | 0 | ⚠ MISSING |
| edge_of_frame | 0 | ⚠ MISSING |
| low_contrast | 0 | ⚠ MISSING |
| motion_blur | 0 | ⚠ MISSING |
| no_ball | 0 | ⚠ MISSING |
| no_ball | 0 | ⚠ MISSING |
| partial_occlusion | 0 | ⚠ MISSING |
| small_ball | 0 | ⚠ MISSING |
| unassigned | 50 |  |

---

## 2. Ground Truth Quality

| Metric | Value |
|--------|-------|
| GT frames | 34 |
| Avg inter-round agreement (px) | 0.0 |
| Frames requiring manual review | 0 |
| GT provenance — seeded_from_db_round1 | 34 |
| GT provenance — two_round_average | 0 |

> ⚠ **GT independence limitation**: Type A frames where Round 1 was seeded from
> `corrected_x/y` may be influenced by model overlay visible during original E2E session.
> Full independence requires a fresh human-annotation session without model reference.

---

## 3. Method Comparison — TÉNYLEGESEN MÉRT (Measured on extracted frames)

> iOS latency: **N/A** — Python/OpenCV benchmark only.  
> iOS VNDetectContoursRequest benchmark required in POC-2.

### 3a. Pixel Error (vs GT, 1920px-reference, lower = better)

| Method | Mean | Median | p90 | p95 | n |
|--------|------|--------|-----|-----|---|
| M1_synthetic_raw_tap *(SYNTHETIC)* | 125.4 | 103.8 | 203.2 | 261.4 | 34 |
| M2_human_loupe_tap | N/A | N/A | N/A | N/A | 0 |
| M3_stored_ssd | 100.8 | 78.8 | 188.1 | 256.8 | 34 |
| M4_contour | 112.7 | 103.8 | 236.7 | 254.3 | 16 |
| M5_hough | 85.7 | 87.2 | 162.4 | 191.5 | 32 |
| M6_template_match | 217.7 | 239.2 | 336.3 | 359.8 | 34 |

> M1 = Monte Carlo simulation (σ=3% frame width, N=100/frame). **Not from real human taps.**
> M2 = Human loupe tap from ground_truth.json.

### 3b. Wrong-snap rate & false positive/refusal

| Method | Wrong-snap vs M1 | FP rate (no-ball) | False-refusal (positive) |
|--------|-----------------|-------------------|--------------------------|
| M3_stored_ssd | 5.9% | N/A | 0.0% |
| M4_contour | 50.0% | N/A | 54.0% |
| M5_hough | 31.2% | N/A | 8.0% |
| M6_template_match | 85.3% | N/A | 8.0% |

---

## 4. Per-category Breakdown

### Category: `unassigned`

| Method | Mean px error | n |
|--------|--------------|---|
| M1_synthetic_raw_tap | 125.4 | 34 |
| M3_stored_ssd | 100.8 | 34 |
| M4_contour | 112.7 | 16 |
| M5_hough | 85.7 | 32 |
| M6_template_match | 217.7 | 34 |

---

## 5. Latency — TÉNYLEGESEN MÉRT (Python/OpenCV)

> **iOS VNDetectContoursRequest latency: N/A — POC-2 physical iPhone benchmark required.**

| Method | p50 (ms) | p95 (ms) | n |
|--------|----------|----------|---|
| M3_stored_ssd | 0.0 | 0.0 | 50 |
| M4_contour | 0.2 | 0.4 | 50 |
| M5_hough | 0.6 | 1.7 | 50 |
| M6_template_match | 0.6 | 0.6 | 50 |

---

## 6. Acceptance Gate Evaluation

| Gate | Threshold | Best Method | Value | Status |
|------|-----------|-------------|-------|--------|
| Improves over raw tap (mean px) | < M1=125.4px | M5_hough | 85.7px | ✅ PASS |
| Wrong-snap rate | < 5% | M3_stored_ssd | 5.9% | ❌ FAIL |
| No-ball FP rate | < 10% | — | N/A | N/A |
| Latency p95 (Python) | < 500ms | M3_stored_ssd | 0.0ms | ✅ PASS |
| iOS latency p95 | < 500ms | — | N/A | 🔲 POC-2 required |

> ⚠ **All gate evaluations above are on the Python/OpenCV benchmark.**
> **Production acceptance requires POC-2 (iOS VNDetectContoursRequest on physical device).**

---

## 7. Limitations & Open Gaps

### HIPOTÉZISEK (not measured in POC-1)

1. iOS latency — hypothesis: p95 < 200ms on iPhone 13+. Not measured.
2. Motion blur degrades Canny contour detection. Not categorised automatically.
3. Small ball (< 15px radius) may cause Hough failure. Headroom via MIN_RADIUS_PX=4.

### BECSLÉSEK (informed but not directly measured)

- M1 σ=0.03 normalised ≈ 58px at 1920×1080. Calibrated from typical touch jitter; **not from real E2E tap logs**.

### TÉNYLEGESEN MÉRT (directly measured)

- Pixel errors for M3/M4/M5/M6 on all GT frames.
- False-positive and false-refusal rates from algorithm outputs.
- Python/OpenCV latency p50/p95.

### Open dataset gaps

| Gap | Impact |
|-----|--------|
| GT Round 1 seeded from model overlay data | Bias risk — may underestimate M3 error |
| Only 1 video with Type A human-corrected data | Low diversity; position cluster near centre |
| Missing categories: clear_ball, motion_blur, partial_occlusion, edge_of_frame, small_ball, low_contrast | Coverage incomplete |
| M1 baseline is synthetic only | No real human raw tap data available |

---

## 8. Verdict

### NEED MORE DATA

**Missing categories: clear_ball, motion_blur, partial_occlusion, edge_of_frame, small_ball, low_contrast. Cannot assess robustness across all scenarios.**

Gate summary: 2 PASS | 1 FAIL | 1 N/A (Python benchmark only)

---

*Report generated by `04_report.py` | 2026-06-20 11:08 UTC*

> **CONSTRAINT**: Automatic snap production integration and merge only after separate explicit approval.