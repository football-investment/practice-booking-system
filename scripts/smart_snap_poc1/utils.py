"""
Shared utility functions used by multiple POC-1 scripts.

Exported here so tests can import directly without running the main scripts.
"""
from __future__ import annotations

import random
from typing import Optional


def stratified_type_b(rows: list[dict], n_per_video: int, seed: int = 42) -> list[dict]:
    """
    Deterministically sample n_per_video frames per video from rows.

    Prioritises diversity: partitions each video's rows into (detected, lost, other)
    and draws proportionally from each bucket, then fills from remaining rows.
    """
    rng = random.Random(seed)
    by_video: dict[str, list[dict]] = {}
    for row in rows:
        vid = row["video_id"]
        by_video.setdefault(vid, []).append(row)

    selected: list[dict] = []
    for vid in sorted(by_video.keys()):
        vrows = by_video[vid]
        if len(vrows) <= n_per_video:
            selected.extend(vrows)
            continue
        detected = [r for r in vrows if r.get("tracking_state") == "detected"]
        lost = [r for r in vrows if r.get("tracking_state") == "lost"]
        others = [r for r in vrows if r.get("tracking_state") not in ("detected", "lost")]

        pool: list[dict] = []
        per_bucket = max(1, n_per_video // 3)
        for bucket in (detected, lost, others):
            shuffled = list(bucket)
            rng.shuffle(shuffled)
            pool.extend(shuffled[:per_bucket])
        already = set(id(r) for r in pool)
        remaining = [r for r in vrows if id(r) not in already]
        rng.shuffle(remaining)
        pool.extend(remaining[: n_per_video - len(pool)])
        selected.extend(pool[:n_per_video])

    return selected


def build_frame_id(video_id: str, frame_ms: int) -> str:
    """Canonical frame identifier: first 8 chars of UUID + zero-padded ms."""
    return f"{video_id[:8]}_{frame_ms:07d}ms"


def auto_category_hints(
    tracking_state: Optional[str],
    confidence: Optional[float],
    ball_x: Optional[float],
    ball_y: Optional[float],
    edge_threshold: float = 0.12,
    high_conf_threshold: float = 0.70,
    low_conf_threshold: float = 0.40,
) -> list[str]:
    hints: list[str] = []
    if tracking_state == "lost":
        hints.append("no_ball_candidate")
    if confidence is not None:
        if confidence >= high_conf_threshold:
            hints.append("high_conf")
        elif confidence < low_conf_threshold:
            hints.append("low_conf")
        else:
            hints.append("mid_conf")
    if ball_x is not None and ball_y is not None:
        if (ball_x < edge_threshold or ball_x > 1 - edge_threshold
                or ball_y < edge_threshold or ball_y > 1 - edge_threshold):
            hints.append("edge_of_frame")
    return hints
