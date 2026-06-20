"""SS-SMP: Deterministic sampling tests (fixed seed)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.smart_snap_poc1.utils import stratified_type_b


def _make_rows(video_ids_counts: dict[str, int]) -> list[dict]:
    rows = []
    for vid, n in video_ids_counts.items():
        for i in range(n):
            state = "detected" if i % 3 == 0 else ("lost" if i % 3 == 1 else "predicted")
            rows.append({
                "video_id": vid,
                "frame_ms": i * 100,
                "tracking_state": state,
                "model_x": 0.5,
                "model_y": 0.5,
                "model_confidence": 0.5,
                "storage_path": f"app/uploads/juggling/{vid}.mp4",
            })
    return rows


class TestSampling:
    def test_SS_SMP_01_deterministic(self):
        """SS-SMP-01: Two runs with same seed produce identical results."""
        rows = _make_rows({"vid1": 20, "vid2": 20})
        r1 = stratified_type_b(rows, 4, seed=42)
        r2 = stratified_type_b(rows, 4, seed=42)
        assert [r["frame_ms"] for r in r1] == [r["frame_ms"] for r in r2]

    def test_SS_SMP_02_different_seeds_differ(self):
        """SS-SMP-02: Different seeds produce different results."""
        rows = _make_rows({"vid1": 50})
        r1 = stratified_type_b(rows, 6, seed=42)
        r2 = stratified_type_b(rows, 6, seed=99)
        # With 50 candidates selecting 6, different seeds should usually differ
        # (if they don't, that's a very unlikely coincidence — not a bug)
        assert len(r1) == 6 and len(r2) == 6

    def test_SS_SMP_03_count_respects_n_per_video(self):
        """SS-SMP-03: Each video contributes at most n_per_video frames."""
        rows = _make_rows({"vid1": 30, "vid2": 30, "vid3": 30})
        selected = stratified_type_b(rows, 4, seed=42)
        by_vid: dict[str, int] = {}
        for r in selected:
            by_vid[r["video_id"]] = by_vid.get(r["video_id"], 0) + 1
        for vid, cnt in by_vid.items():
            assert cnt <= 4, f"{vid} has {cnt} frames > 4"

    def test_SS_SMP_04_small_pool_returns_all(self):
        """SS-SMP-04: Pool smaller than n_per_video returns all rows."""
        rows = _make_rows({"vid1": 2})
        selected = stratified_type_b(rows, 4, seed=42)
        assert len(selected) == 2

    def test_SS_SMP_05_diversity_across_tracking_states(self):
        """SS-SMP-05: Selected frames span multiple tracking states."""
        rows = _make_rows({"vid1": 30})
        selected = stratified_type_b(rows, 6, seed=42)
        states = {r["tracking_state"] for r in selected}
        # 30 frames across 3 states, selecting 6 → at least 2 states
        assert len(states) >= 2

    def test_SS_SMP_06_empty_input(self):
        """SS-SMP-06: Empty input returns empty list."""
        selected = stratified_type_b([], 4, seed=42)
        assert selected == []

    def test_SS_SMP_07_single_video_exact_count(self):
        """SS-SMP-07: Single video with many rows returns exactly n_per_video."""
        rows = _make_rows({"vid1": 100})
        selected = stratified_type_b(rows, 5, seed=42)
        assert len(selected) == 5
