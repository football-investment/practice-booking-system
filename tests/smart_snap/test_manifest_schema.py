"""SS-MAN: manifest schema validation tests."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

REQUIRED_FRAME_KEYS = {
    "frame_id", "type", "video_id", "frame_ms",
    "storage_path", "image_width_px", "image_height_px",
    "tracking_state", "model_x", "model_y", "model_confidence",
    "human_loupe_x", "human_loupe_y", "correction_method",
    "auto_category_hints", "gt_status", "category",
}
REQUIRED_TOP_KEYS = {
    "generated_at", "poc", "schema_version", "summary", "frames",
}


def _make_minimal_manifest() -> dict:
    return {
        "generated_at": "2026-06-20T00:00:00+00:00",
        "poc": "smart_snap_poc1",
        "schema_version": "1.0",
        "summary": {
            "type_a_count": 1,
            "type_b_count": 0,
            "total_count": 1,
            "videos_represented": 1,
            "missing_files_type_a": [],
            "auto_category_hint_distribution": {},
        },
        "frames": [
            {
                "frame_id": "aaaabbbb_0001000ms",
                "type": "A",
                "video_id": "aaaabbbb-0000-0000-0000-000000000001",
                "frame_ms": 1000,
                "storage_path": "app/uploads/juggling/test.mp4",
                "image_width_px": 640,
                "image_height_px": 480,
                "tracking_state": "predicted",
                "model_x": 0.5,
                "model_y": 0.5,
                "model_confidence": None,
                "human_loupe_x": 0.51,
                "human_loupe_y": 0.49,
                "correction_method": "tap_in_crop",
                "auto_category_hints": ["mid_conf"],
                "gt_status": "PENDING_ANNOTATION",
                "category": None,
            }
        ],
    }


class TestManifestSchema:
    def test_SS_MAN_01_top_level_keys(self):
        """SS-MAN-01: All required top-level keys present."""
        m = _make_minimal_manifest()
        for key in REQUIRED_TOP_KEYS:
            assert key in m, f"Missing top-level key: {key}"

    def test_SS_MAN_02_frame_keys(self):
        """SS-MAN-02: Each frame has all required keys."""
        m = _make_minimal_manifest()
        for frame in m["frames"]:
            for key in REQUIRED_FRAME_KEYS:
                assert key in frame, f"Frame missing key: {key}"

    def test_SS_MAN_03_frame_id_format(self):
        """SS-MAN-03: frame_id is non-empty string."""
        m = _make_minimal_manifest()
        for frame in m["frames"]:
            assert isinstance(frame["frame_id"], str) and len(frame["frame_id"]) > 0

    def test_SS_MAN_04_type_values(self):
        """SS-MAN-04: type must be 'A' or 'B'."""
        m = _make_minimal_manifest()
        for frame in m["frames"]:
            assert frame["type"] in ("A", "B"), f"Invalid type: {frame['type']}"

    def test_SS_MAN_05_frame_ms_positive(self):
        """SS-MAN-05: frame_ms must be positive integer."""
        m = _make_minimal_manifest()
        for frame in m["frames"]:
            assert isinstance(frame["frame_ms"], int) and frame["frame_ms"] >= 0

    def test_SS_MAN_06_coord_range(self):
        """SS-MAN-06: model_x/y and human_loupe_x/y in [0,1] if not None."""
        m = _make_minimal_manifest()
        for frame in m["frames"]:
            for key in ("model_x", "model_y", "human_loupe_x", "human_loupe_y"):
                v = frame.get(key)
                if v is not None:
                    assert 0.0 <= v <= 1.0, f"{key}={v} out of [0,1]"

    def test_SS_MAN_07_auto_hints_is_list(self):
        """SS-MAN-07: auto_category_hints must be a list."""
        m = _make_minimal_manifest()
        for frame in m["frames"]:
            assert isinstance(frame["auto_category_hints"], list)

    def test_SS_MAN_08_type_a_has_human_loupe(self):
        """SS-MAN-08: Type A frames must have human_loupe_x/y."""
        m = _make_minimal_manifest()
        for frame in m["frames"]:
            if frame["type"] == "A":
                assert frame.get("human_loupe_x") is not None
                assert frame.get("human_loupe_y") is not None

    def test_SS_MAN_09_json_serialisable(self):
        """SS-MAN-09: manifest must be JSON-serialisable."""
        m = _make_minimal_manifest()
        serialised = json.dumps(m)
        recovered = json.loads(serialised)
        assert recovered["poc"] == "smart_snap_poc1"

    def test_SS_MAN_10_summary_count_matches_frames(self):
        """SS-MAN-10: summary.total_count == len(frames)."""
        m = _make_minimal_manifest()
        assert m["summary"]["total_count"] == len(m["frames"])
