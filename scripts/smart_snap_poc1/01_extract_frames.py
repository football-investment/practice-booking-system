#!/usr/bin/env python3
"""
01_extract_frames.py — Smart Snap POC-1

Reads manifest.json and extracts full-frame JPEG images for every listed
frame.  Skips frames whose output file already exists (re-run safe).

Output: dataset/raw/{frame_id}.jpg
        dataset/raw/frame_meta.json  (metadata index)

Usage:
    python scripts/smart_snap_poc1/01_extract_frames.py
    python scripts/smart_snap_poc1/01_extract_frames.py --force   # overwrite existing
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    import cv2
    import numpy as np
except ImportError:
    print("ERROR: opencv-python-headless not installed.", file=sys.stderr)
    sys.exit(1)

from PIL import Image

from scripts.smart_snap_poc1.config import (
    DATASET_DIR,
    FRAME_JPEG_QUALITY,
    MANIFEST_PATH,
    PROJECT_ROOT,
)


def extract_frame(video_path: str, frame_ms: int) -> tuple[np.ndarray, int, int]:
    """Extract a single frame at timestamp frame_ms (milliseconds)."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise OSError(f"Cannot open video: {video_path}")
    cap.set(cv2.CAP_PROP_POS_MSEC, float(frame_ms))
    ret, frame_bgr = cap.read()
    cap.release()
    if not ret or frame_bgr is None:
        raise ValueError(f"Frame at {frame_ms}ms not readable from {video_path}")
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    h, w = frame_rgb.shape[:2]
    return frame_rgb, w, h


def save_frame_jpeg(frame_rgb: np.ndarray, out_path: str, quality: int = FRAME_JPEG_QUALITY) -> None:
    img = Image.fromarray(frame_rgb)
    img.save(out_path, format="JPEG", quality=quality)


def run(force: bool = False) -> None:
    if not os.path.isfile(MANIFEST_PATH):
        print(f"ERROR: manifest.json not found at {MANIFEST_PATH}", file=sys.stderr)
        print("Run 00_audit_eligible_frames.py first.", file=sys.stderr)
        sys.exit(1)

    with open(MANIFEST_PATH, encoding="utf-8") as fh:
        manifest = json.load(fh)

    frames = manifest["frames"]
    os.makedirs(DATASET_DIR, exist_ok=True)

    extracted = 0
    skipped = 0
    errors: list[str] = []

    meta_index: list[dict] = []

    for frame in frames:
        frame_id = frame["frame_id"]
        out_path = os.path.join(DATASET_DIR, f"{frame_id}.jpg")

        if os.path.isfile(out_path) and not force:
            skipped += 1
            meta_index.append({
                "frame_id": frame_id,
                "jpg_path": out_path,
                "image_width_px": frame.get("image_width_px"),
                "image_height_px": frame.get("image_height_px"),
                "type": frame["type"],
                "video_id": frame["video_id"],
                "frame_ms": frame["frame_ms"],
                "auto_category_hints": frame.get("auto_category_hints", []),
            })
            continue

        abs_video = os.path.join(PROJECT_ROOT, frame["storage_path"])
        if not os.path.isfile(abs_video):
            errors.append(f"{frame_id}: video file missing: {frame['storage_path']}")
            continue

        try:
            frame_rgb, actual_w, actual_h = extract_frame(abs_video, frame["frame_ms"])
            save_frame_jpeg(frame_rgb, out_path)
            extracted += 1
            meta_index.append({
                "frame_id": frame_id,
                "jpg_path": out_path,
                "image_width_px": actual_w,
                "image_height_px": actual_h,
                "type": frame["type"],
                "video_id": frame["video_id"],
                "frame_ms": frame["frame_ms"],
                "auto_category_hints": frame.get("auto_category_hints", []),
            })
            print(f"  ✓ {frame_id}  ({actual_w}×{actual_h})")
        except Exception as exc:
            errors.append(f"{frame_id}: {exc}")
            print(f"  ✗ {frame_id}: {exc}", file=sys.stderr)

    # Write frame metadata index
    meta_path = os.path.join(DATASET_DIR, "frame_meta.json")
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta_index, fh, indent=2)

    print(f"\nExtraction complete: {extracted} extracted, {skipped} skipped, {len(errors)} errors")
    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract frames listed in manifest.json.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing JPEG files.")
    args = parser.parse_args()
    run(force=args.force)
