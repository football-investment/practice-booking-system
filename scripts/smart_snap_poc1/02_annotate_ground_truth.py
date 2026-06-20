#!/usr/bin/env python3
"""
02_annotate_ground_truth.py — Smart Snap POC-1 interactive annotator.

Protocol:
  Round 1 (GT):       Click ball centre WITHOUT seeing model prediction.
  Round 2 (GT):       Re-annotate the same frame for inter-rater agreement.
  Raw tap (M1):       Click as you would on a phone without a loupe.
  Loupe tap (M2):     Click as if using a loupe magnifier (careful precision).

The model prediction is revealed ONLY after Round 2 is saved.

For Type A frames, corrected_x/y from the DB is shown as a reference after
Round 2 — it is NOT pre-loaded as Ground Truth.

Saves incrementally to ground_truth.json after each frame.

Usage:
    python scripts/smart_snap_poc1/02_annotate_ground_truth.py
    python scripts/smart_snap_poc1/02_annotate_ground_truth.py --seed-from-db
    python scripts/smart_snap_poc1/02_annotate_ground_truth.py --frame <frame_id>

--seed-from-db:
  Seeds Round 1 from existing corrected_x/y (Type A frames) and marks
  these frames with gt_provenance="seeded_from_db_round1".
  Round 2 is still required interactively.

--no-ball <frame_id>:
  Mark a frame as no-ball without clicking.

Requires matplotlib (dev dependency):
    pip install matplotlib>=3.7.0
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt
    from matplotlib.backend_bases import MouseButton
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed.", file=sys.stderr)
    sys.exit(1)

import numpy as np

from scripts.smart_snap_poc1.config import (
    DATASET_DIR,
    GROUND_TRUTH_PATH,
    GT_AGREEMENT_THRESHOLD_PX,
    MANIFEST_PATH,
)

# ── Persistence helpers ───────────────────────────────────────────────────────

def load_gt() -> dict:
    if os.path.isfile(GROUND_TRUTH_PATH):
        with open(GROUND_TRUTH_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    return {"schema_version": "1.0", "poc": "smart_snap_poc1", "frames": {}}


def save_gt(gt: dict) -> None:
    with open(GROUND_TRUTH_PATH, "w", encoding="utf-8") as fh:
        json.dump(gt, fh, indent=2, default=str)


def load_manifest() -> dict:
    with open(MANIFEST_PATH, encoding="utf-8") as fh:
        return json.load(fh)


# ── GT agreement check ────────────────────────────────────────────────────────

def _agreement_px(
    x1: float, y1: float,
    x2: float, y2: float,
    img_w: int, img_h: int,
) -> float:
    dx = (x1 - x2) * img_w
    dy = (y1 - y2) * img_h
    return (dx ** 2 + dy ** 2) ** 0.5


# ── Matplotlib annotation session ────────────────────────────────────────────

class AnnotationSession:
    """
    Single-frame annotation session with matplotlib.

    Mode sequence: GT_R1 → GT_R2 → RAW_TAP → LOUPE_TAP
    """
    MODES = ["GT_R1", "GT_R2", "RAW_TAP", "LOUPE_TAP"]
    PROMPTS = {
        "GT_R1":      "GT Round 1: Click ball centre (model prediction HIDDEN).",
        "GT_R2":      "GT Round 2: Re-annotate independently for agreement check.",
        "RAW_TAP":    "Raw Tap (M1): Click as on phone without loupe (quick).",
        "LOUPE_TAP":  "Loupe Tap (M2): Click with loupe precision (careful).",
    }
    COLORS = {
        "GT_R1":     "#00FF00",   # green
        "GT_R2":     "#00CCFF",   # cyan
        "RAW_TAP":   "#FF6600",   # orange
        "LOUPE_TAP": "#FF00FF",   # magenta
    }

    def __init__(
        self,
        frame_id: str,
        img_path: str,
        img_w: int,
        img_h: int,
        existing: Optional[dict] = None,
        model_x: Optional[float] = None,
        model_y: Optional[float] = None,
        db_corrected_x: Optional[float] = None,
        db_corrected_y: Optional[float] = None,
        seed_r1_from_db: bool = False,
    ) -> None:
        self.frame_id = frame_id
        self.img_path = img_path
        self.img_w = img_w
        self.img_h = img_h
        self.model_x = model_x
        self.model_y = model_y
        self.db_corrected_x = db_corrected_x
        self.db_corrected_y = db_corrected_y
        self.seed_r1_from_db = seed_r1_from_db

        # Start from existing partial annotation if present
        self.result: dict = existing.copy() if existing else {}
        self._clicks: dict[str, tuple[float, float]] = {}

        # Determine which modes are still needed
        done = set(self.result.get("completed_modes", []))
        self.pending = [m for m in self.MODES if m not in done]

    def run(self) -> dict:
        """Run annotation for all pending modes.  Returns the completed annotation dict."""
        if not self.pending:
            print(f"  [{self.frame_id}] All modes already annotated, skipping.")
            return self.result

        img = np.array(Image.open(self.img_path))
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.imshow(img)
        ax.set_title(f"Frame: {self.frame_id}", fontsize=10, pad=4)
        ax.axis("off")

        completed_modes = list(self.result.get("completed_modes", []))

        for mode in self.pending:
            self._set_prompt(fig, mode, completed_modes)
            show_model = mode not in ("GT_R1", "GT_R2")

            if show_model and self.model_x is not None:
                self._draw_model(ax)

            if mode == "GT_R2" and "GT_R1" in completed_modes:
                # Show Round 1 point as faint reference
                r1x = self.result["gt_round_1"]["x"]
                r1y = self.result["gt_round_1"]["y"]
                ax.plot(r1x * self.img_w, r1y * self.img_h, "+",
                        color="#00FF00", ms=14, mew=2, alpha=0.5, label="GT R1")

            plt.draw()
            pts = plt.ginput(1, timeout=300)
            if not pts:
                print(f"\n  Timeout/cancel — stopping at mode {mode}.")
                break

            px_x, px_y = pts[0]
            nx = max(0.0, min(1.0, px_x / self.img_w))
            ny = max(0.0, min(1.0, px_y / self.img_h))

            ts = datetime.now(timezone.utc).isoformat()
            self.result[self._mode_key(mode)] = {"x": nx, "y": ny, "annotated_at": ts}
            completed_modes.append(mode)

            # Draw the confirmed point
            ax.plot(px_x, px_y, "x",
                    color=self.COLORS[mode], ms=14, mew=3,
                    label=mode)
            plt.draw()

            # After GT_R2: check agreement
            if mode == "GT_R2" and "GT_R1" in completed_modes:
                r1 = self.result["gt_round_1"]
                r2 = self.result["gt_round_2"]
                gap = _agreement_px(r1["x"], r1["y"], r2["x"], r2["y"], self.img_w, self.img_h)
                self.result["gt_agreement_px"] = round(gap, 2)
                self.result["gt_review_required"] = gap > GT_AGREEMENT_THRESHOLD_PX
                if self.result["gt_review_required"]:
                    print(f"\n  ⚠ Agreement gap {gap:.1f}px > {GT_AGREEMENT_THRESHOLD_PX}px → MANUAL REVIEW FLAG")
                # Reveal model prediction
                if self.model_x is not None:
                    self._draw_model(ax)
                    plt.draw()
                # Reveal DB corrected point if available
                if self.db_corrected_x is not None:
                    ax.plot(
                        self.db_corrected_x * self.img_w,
                        self.db_corrected_y * self.img_h,
                        "D", color="#FFFF00", ms=8,
                        label="DB corrected (ref)",
                    )
                    ax.legend(loc="upper right", fontsize=7)
                    plt.draw()

        # Compute final GT as average of R1 and R2
        if "gt_round_1" in self.result and "gt_round_2" in self.result:
            r1 = self.result["gt_round_1"]
            r2 = self.result["gt_round_2"]
            self.result["gt_final"] = {
                "x": (r1["x"] + r2["x"]) / 2,
                "y": (r1["y"] + r2["y"]) / 2,
            }
            self.result["gt_provenance"] = "two_round_average"

        self.result["completed_modes"] = completed_modes
        self.result["is_no_ball"] = False
        plt.close(fig)
        return self.result

    def _mode_key(self, mode: str) -> str:
        return {
            "GT_R1":     "gt_round_1",
            "GT_R2":     "gt_round_2",
            "RAW_TAP":   "human_raw_tap",
            "LOUPE_TAP": "human_loupe_tap",
        }[mode]

    def _set_prompt(self, fig, mode: str, done: list[str]) -> None:
        done_str = " | ".join(done) if done else "—"
        fig.suptitle(
            f"{self.PROMPTS[mode]}\n"
            f"Done: {done_str}\n"
            f"[Esc/timeout = stop]",
            fontsize=9, color=self.COLORS[mode],
        )

    def _draw_model(self, ax) -> None:
        if self.model_x is None:
            return
        ax.plot(
            self.model_x * self.img_w,
            self.model_y * self.img_h,
            "o", color="#FFFF00", ms=10, mew=2,
            markerfacecolor="none",
            label="Model pred",
        )


# ── Seed from DB ──────────────────────────────────────────────────────────────

def seed_from_db(manifest: dict, gt: dict) -> int:
    """
    Pre-populate GT Round 1 from existing corrected_x/y in the DB (Type A frames).

    Marks provenance as 'seeded_from_db_round1'.
    Round 2 must still be done interactively.
    Returns number of frames seeded.
    """
    seeded = 0
    for frame in manifest["frames"]:
        frame_id = frame["frame_id"]
        if frame["type"] != "A":
            continue
        if frame.get("human_loupe_x") is None:
            continue
        if frame_id in gt["frames"] and "gt_round_1" in gt["frames"][frame_id]:
            continue  # already has R1
        ts = datetime.now(timezone.utc).isoformat()
        entry = gt["frames"].setdefault(frame_id, {})
        entry["gt_round_1"] = {
            "x": frame["human_loupe_x"],
            "y": frame["human_loupe_y"],
            "annotated_at": ts,
        }
        entry["gt_provenance"] = "seeded_from_db_round1"
        entry["completed_modes"] = list(entry.get("completed_modes", [])) + ["GT_R1"]
        seeded += 1
    save_gt(gt)
    return seeded


# ── Main ─────────────────────────────────────────────────────────────────────

def run(target_frame: Optional[str] = None, seed_db: bool = False, no_ball_id: Optional[str] = None) -> None:
    if not HAS_MATPLOTLIB:
        print("ERROR: matplotlib not installed.  Run: pip install matplotlib>=3.7.0", file=sys.stderr)
        print("Alternatively, seed from DB with --seed-from-db and skip interactive modes.", file=sys.stderr)
        sys.exit(1)

    manifest = load_manifest()
    gt = load_gt()

    if seed_db:
        n = seed_from_db(manifest, gt)
        print(f"Seeded {n} Type A frames with DB corrected_x/y as GT Round 1.")

    if no_ball_id:
        ts = datetime.now(timezone.utc).isoformat()
        gt["frames"][no_ball_id] = {
            "is_no_ball": True,
            "gt_round_1": None,
            "gt_round_2": None,
            "gt_final": None,
            "human_raw_tap": None,
            "human_loupe_tap": None,
            "completed_modes": ["GT_R1", "GT_R2", "RAW_TAP", "LOUPE_TAP"],
            "gt_provenance": "marked_no_ball",
            "annotated_at": ts,
        }
        save_gt(gt)
        print(f"Marked {no_ball_id} as no-ball.")
        return

    frames = manifest["frames"]
    if target_frame:
        frames = [f for f in frames if f["frame_id"] == target_frame]
        if not frames:
            print(f"ERROR: frame_id '{target_frame}' not in manifest.", file=sys.stderr)
            sys.exit(1)

    for frame in frames:
        frame_id = frame["frame_id"]
        img_path = os.path.join(DATASET_DIR, f"{frame_id}.jpg")
        if not os.path.isfile(img_path):
            print(f"  SKIP {frame_id}: image not extracted (run 01_extract_frames.py first)")
            continue

        existing = gt["frames"].get(frame_id, {})
        if set(existing.get("completed_modes", [])) >= set(AnnotationSession.MODES):
            print(f"  SKIP {frame_id}: fully annotated")
            continue

        session = AnnotationSession(
            frame_id=frame_id,
            img_path=img_path,
            img_w=frame["image_width_px"] or 640,
            img_h=frame["image_height_px"] or 480,
            existing=existing,
            model_x=frame.get("model_x"),
            model_y=frame.get("model_y"),
            db_corrected_x=frame.get("human_loupe_x"),
            db_corrected_y=frame.get("human_loupe_y"),
            seed_r1_from_db=seed_db,
        )
        result = session.run()
        gt["frames"][frame_id] = result
        save_gt(gt)
        print(f"  Saved {frame_id}: modes={result.get('completed_modes', [])}")

    # Summary
    total = len(manifest["frames"])
    fully_done = sum(
        1 for fid, fdata in gt["frames"].items()
        if set(fdata.get("completed_modes", [])) >= set(AnnotationSession.MODES)
    )
    print(f"\nAnnotation status: {fully_done}/{total} frames fully annotated.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive GT annotation tool.")
    parser.add_argument("--frame", metavar="FRAME_ID", help="Annotate a single frame.")
    parser.add_argument("--seed-from-db", action="store_true",
                        help="Pre-populate GT R1 from DB corrected_x/y (Type A frames).")
    parser.add_argument("--no-ball", metavar="FRAME_ID",
                        help="Mark a single frame as no-ball without clicking.")
    args = parser.parse_args()
    run(
        target_frame=args.frame,
        seed_db=args.seed_from_db,
        no_ball_id=args.no_ball,
    )
