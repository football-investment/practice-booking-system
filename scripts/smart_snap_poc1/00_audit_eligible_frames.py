#!/usr/bin/env python3
"""
00_audit_eligible_frames.py — Smart Snap POC-1

Read-only DB audit.  Builds manifest.json that catalogues:
  - Type A: frames with existing human-corrected feedback (corrected_x/y in DB)
  - Type B: candidate frames from other videos (require fresh human annotation)

No data is written to the database.  No personal identifiers in the output.

Usage:
    DB_PASSWORD=postgres python scripts/smart_snap_poc1/00_audit_eligible_frames.py
    DB_PASSWORD=postgres python scripts/smart_snap_poc1/00_audit_eligible_frames.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("ERROR: psycopg2 not installed.", file=sys.stderr)
    sys.exit(1)

from scripts.smart_snap_poc1.config import (
    DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER,
    EDGE_THRESHOLD,
    HIGH_CONF_THRESHOLD,
    LOW_CONF_THRESHOLD,
    MANIFEST_PATH,
    PROJECT_ROOT,
    TYPE_B_PER_VIDEO,
)
from scripts.smart_snap_poc1.utils import auto_category_hints, build_frame_id, stratified_type_b

# ── Queries ──────────────────────────────────────────────────────────────────

_TYPE_A_QUERY = """
SELECT
    jf.video_id::text,
    jf.frame_ms,
    jf.corrected_x,
    jf.corrected_y,
    jf.model_predicted_x,
    jf.model_predicted_y,
    jf.model_confidence,
    jf.correction_method,
    jt.tracking_state,
    jt.image_width_px,
    jt.image_height_px,
    jv.storage_path
FROM juggling_ball_feedback jf
JOIN juggling_ball_trajectories jt
    ON jt.video_id = jf.video_id AND jt.frame_ms = jf.frame_ms
JOIN juggling_videos jv ON jv.id = jf.video_id
WHERE jf.decision = 'corrected'
  AND jt.image_width_px IS NOT NULL
  AND jv.storage_path IS NOT NULL
ORDER BY jf.video_id, jf.frame_ms
"""

_TYPE_B_CANDIDATES_QUERY = """
SELECT
    jt.video_id::text,
    jt.frame_ms,
    jt.ball_x          AS model_x,
    jt.ball_y          AS model_y,
    jt.confidence       AS model_confidence,
    jt.tracking_state,
    jt.image_width_px,
    jt.image_height_px,
    jv.storage_path
FROM juggling_ball_trajectories jt
JOIN juggling_videos jv ON jv.id = jt.video_id
WHERE jv.status = 'analyzed'
  AND jt.image_width_px IS NOT NULL
  AND jv.storage_path IS NOT NULL
  AND jt.video_id NOT IN (
      SELECT DISTINCT video_id FROM juggling_ball_feedback WHERE decision='corrected'
  )
ORDER BY jt.video_id, jt.frame_ms
"""

# ── Helpers ──────────────────────────────────────────────────────────────────

def _db_connect():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD, dbname=DB_NAME,
    )


def _abs_storage_path(rel_path: str) -> str:
    return os.path.join(PROJECT_ROOT, rel_path)


def _file_exists(rel_path: str) -> bool:
    return os.path.isfile(_abs_storage_path(rel_path))


# ── Main ─────────────────────────────────────────────────────────────────────

def run(dry_run: bool = False) -> dict:
    conn = _db_connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(_TYPE_A_QUERY)
            type_a_rows = cur.fetchall()

            cur.execute(_TYPE_B_CANDIDATES_QUERY)
            type_b_candidates = cur.fetchall()
    finally:
        conn.close()

    # ── Type A frames ─────────────────────────────────────────────────────
    type_a_frames: list[dict] = []
    missing_files_a: list[str] = []

    for row in type_a_rows:
        rel = row["storage_path"]
        if not _file_exists(rel):
            missing_files_a.append(rel)
            continue
        frame_id = build_frame_id(row["video_id"], row["frame_ms"])
        hints = auto_category_hints(
            row["tracking_state"],
            row["model_confidence"],
            row["model_predicted_x"],
            row["model_predicted_y"],
            edge_threshold=EDGE_THRESHOLD,
            high_conf_threshold=HIGH_CONF_THRESHOLD,
            low_conf_threshold=LOW_CONF_THRESHOLD,
        )
        type_a_frames.append({
            "frame_id": frame_id,
            "type": "A",
            "video_id": row["video_id"],
            "frame_ms": row["frame_ms"],
            "storage_path": rel,
            "image_width_px": row["image_width_px"],
            "image_height_px": row["image_height_px"],
            "tracking_state": row["tracking_state"],
            "model_x": row["model_predicted_x"],
            "model_y": row["model_predicted_y"],
            "model_confidence": row["model_confidence"],
            "human_loupe_x": row["corrected_x"],
            "human_loupe_y": row["corrected_y"],
            "correction_method": row["correction_method"],
            "auto_category_hints": hints,
            "gt_status": "PENDING_ANNOTATION",
            "category": None,
        })

    # ── Type B frames ─────────────────────────────────────────────────────
    # Exclude videos that already have Type A data
    type_a_video_ids = {f["video_id"] for f in type_a_frames}
    b_candidates_filtered = [
        dict(r) for r in type_b_candidates
        if r["video_id"] not in type_a_video_ids and _file_exists(r["storage_path"])
    ]

    type_b_selected = stratified_type_b(b_candidates_filtered, TYPE_B_PER_VIDEO)
    type_b_frames: list[dict] = []

    for row in type_b_selected:
        frame_id = build_frame_id(row["video_id"], row["frame_ms"])
        hints = auto_category_hints(
            row["tracking_state"],
            row.get("model_confidence"),
            row.get("model_x"),
            row.get("model_y"),
            edge_threshold=EDGE_THRESHOLD,
            high_conf_threshold=HIGH_CONF_THRESHOLD,
            low_conf_threshold=LOW_CONF_THRESHOLD,
        )
        type_b_frames.append({
            "frame_id": frame_id,
            "type": "B",
            "video_id": row["video_id"],
            "frame_ms": row["frame_ms"],
            "storage_path": row["storage_path"],
            "image_width_px": row["image_width_px"],
            "image_height_px": row["image_height_px"],
            "tracking_state": row["tracking_state"],
            "model_x": row.get("model_x"),
            "model_y": row.get("model_y"),
            "model_confidence": row.get("model_confidence"),
            "human_loupe_x": None,
            "human_loupe_y": None,
            "correction_method": None,
            "auto_category_hints": hints,
            "gt_status": "PENDING_ANNOTATION",
            "category": None,
        })

    # ── Summary stats ──────────────────────────────────────────────────────
    all_frames = type_a_frames + type_b_frames
    video_ids_represented = len({f["video_id"] for f in all_frames})

    hint_counts: dict[str, int] = {}
    for f in all_frames:
        for h in f["auto_category_hints"]:
            hint_counts[h] = hint_counts.get(h, 0) + 1

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "poc": "smart_snap_poc1",
        "schema_version": "1.0",
        "summary": {
            "type_a_count": len(type_a_frames),
            "type_b_count": len(type_b_frames),
            "total_count": len(all_frames),
            "videos_represented": video_ids_represented,
            "missing_files_type_a": missing_files_a,
            "auto_category_hint_distribution": hint_counts,
        },
        "frames": all_frames,
    }

    if not dry_run:
        with open(MANIFEST_PATH, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, default=str)
        print(f"manifest.json written: {len(all_frames)} frames "
              f"(A={len(type_a_frames)}, B={len(type_b_frames)})")

    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build POC-1 frame manifest from DB.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print summary without writing manifest.json")
    args = parser.parse_args()
    manifest = run(dry_run=args.dry_run)
    s = manifest["summary"]
    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Audit complete:")
    print(f"  Type A (human-corrected) : {s['type_a_count']} frames")
    print(f"  Type B (fresh)           : {s['type_b_count']} frames")
    print(f"  Total                    : {s['total_count']} frames")
    print(f"  Videos represented       : {s['videos_represented']}")
    print(f"  Hint distribution        : {s['auto_category_hint_distribution']}")
    if s["missing_files_type_a"]:
        print(f"\n  WARNING: {len(s['missing_files_type_a'])} Type A video files missing:")
        for p in s["missing_files_type_a"]:
            print(f"    {p}")
