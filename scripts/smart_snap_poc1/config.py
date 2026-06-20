"""Shared configuration for Smart Snap POC-1 scripts."""
from __future__ import annotations

import os

# ── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

DATASET_DIR = os.path.join(BASE_DIR, "dataset", "raw")
MANIFEST_PATH = os.path.join(BASE_DIR, "manifest.json")
GROUND_TRUTH_PATH = os.path.join(BASE_DIR, "ground_truth.json")
BENCHMARK_RESULTS_PATH = os.path.join(BASE_DIR, "benchmark_results.json")
REPORT_PATH = os.path.join(BASE_DIR, "report.md")

# ── Database ─────────────────────────────────────────────────────────────────
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")
DB_NAME = os.environ.get("DB_NAME", "lfa_intern_system")

# ── Dataset targets ──────────────────────────────────────────────────────────
TARGET_TOTAL_FRAMES = 50
MIN_TOTAL_FRAMES = 30

# Type A = frames with existing human-corrected feedback (from DB)
# Type B = fresh frames from other videos (require human annotation via 02_annotate)
TYPE_B_PER_VIDEO = 4    # frames to extract from each of the non-A videos
TARGET_CATEGORIES = [
    "clear_ball",
    "motion_blur",
    "partial_occlusion",
    "edge_of_frame",
    "small_ball",
    "low_contrast",
    "no_ball",
]

# ── Frame extraction ─────────────────────────────────────────────────────────
FRAME_JPEG_QUALITY = 85

# ── ROI settings ─────────────────────────────────────────────────────────────
# M4: local contour snap — ROI half-side = M4_ROI_RATIO × min(W, H)
M4_ROI_RATIO = 0.12
# M5: ROI Hough circles — ROI half-side = M5_ROI_RATIO × min(W, H)
M5_ROI_RATIO = 0.15
# M6: template match — ROI half-side = M6_ROI_RATIO × min(W, H)
M6_ROI_RATIO = 0.15
# M6 synthetic circle template radius (px)
M6_TEMPLATE_RADIUS_PX = 18

# ── M4 contour thresholds ────────────────────────────────────────────────────
M4_CANNY_LOW = 30
M4_CANNY_HIGH = 120
M4_MIN_CONTOUR_AREA_PX = 15
M4_CIRCULARITY_MIN = 0.2

# ── M5 Hough thresholds ──────────────────────────────────────────────────────
M5_HOUGH_DP = 1.2
M5_HOUGH_PARAM1 = 60
M5_HOUGH_PARAM2 = 18
M5_HOUGH_MIN_RADIUS_PX = 4
M5_HOUGH_MAX_RADIUS_PX = 60

# ── M1 synthetic raw tap simulation ─────────────────────────────────────────
M1_SIGMA_NORM = 0.03    # Gaussian sigma in normalised [0,1] coords (~3% of frame width)
M1_N_SIMULATIONS = 100  # Monte Carlo draws per frame

# ── GT agreement ────────────────────────────────────────────────────────────
# If the two GT annotation rounds differ by more than this (pixels, 1920-ref),
# the frame is flagged for mandatory manual review.
GT_AGREEMENT_THRESHOLD_PX = 20

# ── Auto category thresholds ─────────────────────────────────────────────────
EDGE_THRESHOLD = 0.12        # ball within 12% of any edge → edge_of_frame
LOW_CONF_THRESHOLD = 0.40    # model confidence < 0.40 → low_contrast candidate
HIGH_CONF_THRESHOLD = 0.70   # model confidence ≥ 0.70 → clear_ball candidate
