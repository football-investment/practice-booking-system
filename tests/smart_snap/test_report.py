"""SS-REP: Report generation smoke tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.smart_snap_poc1.config import TARGET_CATEGORIES


def _make_minimal_benchmark_results() -> dict:
    return {
        "generated_at": "2026-06-20T10:00:00+00:00",
        "poc": "smart_snap_poc1",
        "schema_version": "1.0",
        "summary": {
            "total_frames": 5,
            "frames_with_gt": 3,
            "no_ball_frames": 1,
            "algorithms": ["M3_stored_ssd", "M4_contour"],
        },
        "per_frame": [
            {
                "frame_id": "test_0001000ms",
                "type": "A",
                "category": "clear_ball",
                "auto_category_hints": ["high_conf"],
                "has_gt": True,
                "is_no_ball": False,
                "gt_provenance": "seeded_from_db_round1",
                "gt_agreement_px": 5.0,
                "gt_review_required": False,
                "img_w": 640,
                "img_h": 480,
                "methods": {
                    "M1_synthetic_raw_tap": {"method": "M1_synthetic_raw_tap", "data_source": "SYNTHETIC", "mean": 50.0, "n": 100},
                    "M3_stored_ssd": {"method": "M3_stored_ssd", "found": True, "pixel_error": 12.0, "latency_ms": 0.1},
                    "M4_contour": {"method": "M4_contour", "found": True, "pixel_error": 8.0, "latency_ms": 3.0},
                },
            },
            {
                "frame_id": "test_0002000ms",
                "type": "A",
                "category": None,
                "auto_category_hints": [],
                "has_gt": False,
                "is_no_ball": True,
                "gt_provenance": "marked_no_ball",
                "gt_agreement_px": None,
                "gt_review_required": False,
                "img_w": 640,
                "img_h": 480,
                "methods": {
                    "M3_stored_ssd": {"method": "M3_stored_ssd", "found": False, "false_positive": False, "latency_ms": 0.1},
                    "M4_contour": {"method": "M4_contour", "found": False, "false_positive": False, "latency_ms": 2.0},
                },
            },
        ],
        "aggregated": {
            "M1_synthetic_raw_tap": {
                "overall": {"mean": 50.0, "median": 50.0, "p90": 60.0, "p95": 65.0, "n": 1},
                "by_category": {},
                "latency": {"p50_ms": None, "p95_ms": None, "n": 0},
                "wrong_snap_rate_vs_m1": None,
                "false_positive_rate": None,
                "false_refusal_rate": None,
            },
            "M3_stored_ssd": {
                "overall": {"mean": 12.0, "median": 12.0, "p90": 12.0, "p95": 12.0, "n": 1},
                "by_category": {"clear_ball": {"mean": 12.0, "median": 12.0, "p90": 12.0, "p95": 12.0, "n": 1}},
                "latency": {"p50_ms": 0.1, "p95_ms": 0.1, "n": 2},
                "wrong_snap_rate_vs_m1": 0.0,
                "false_positive_rate": 0.0,
                "false_refusal_rate": 0.5,
            },
            "M4_contour": {
                "overall": {"mean": 8.0, "median": 8.0, "p90": 8.0, "p95": 8.0, "n": 1},
                "by_category": {"clear_ball": {"mean": 8.0, "median": 8.0, "p90": 8.0, "p95": 8.0, "n": 1}},
                "latency": {"p50_ms": 2.5, "p95_ms": 3.0, "n": 2},
                "wrong_snap_rate_vs_m1": 0.0,
                "false_positive_rate": 0.0,
                "false_refusal_rate": 0.5,
            },
        },
    }


class TestReportGeneration:
    def test_SS_REP_01_report_is_string(self):
        """SS-REP-01: build_report returns a non-empty string."""
        from scripts.smart_snap_poc1.report_builder import build_report
        results = _make_minimal_benchmark_results()
        report = build_report(results, None, None)
        assert isinstance(report, str)
        assert len(report) > 100

    def test_SS_REP_02_report_contains_verdict(self):
        """SS-REP-02: Report contains one of the three verdict strings."""
        from scripts.smart_snap_poc1.report_builder import build_report
        results = _make_minimal_benchmark_results()
        report = build_report(results, None, None)
        verdicts = ["PROCEED TO POC-2", "NEED MORE DATA", "REJECT APPROACH"]
        assert any(v in report for v in verdicts), "No verdict found in report"

    def test_SS_REP_03_report_has_measured_section(self):
        """SS-REP-03: Report contains measured/estimated/hypotheses sections."""
        from scripts.smart_snap_poc1.report_builder import build_report
        results = _make_minimal_benchmark_results()
        report = build_report(results, None, None)
        assert "TÉNYLEGESEN MÉRT" in report or "Measured" in report

    def test_SS_REP_04_ios_latency_na(self):
        """SS-REP-04: Report states iOS latency as N/A or POC-2."""
        from scripts.smart_snap_poc1.report_builder import build_report
        results = _make_minimal_benchmark_results()
        report = build_report(results, None, None)
        assert "N/A" in report or "POC-2" in report

    def test_SS_REP_05_no_hardcoded_merge_permission(self):
        """SS-REP-05: Report does not claim merge is approved."""
        from scripts.smart_snap_poc1.report_builder import build_report
        results = _make_minimal_benchmark_results()
        report = build_report(results, None, None)
        assert "merged to main" not in report.lower()
        assert "merge approved" not in report.lower()

    def test_SS_REP_06_report_contains_acceptance_gate_table(self):
        """SS-REP-06: Report includes acceptance gate evaluation table."""
        from scripts.smart_snap_poc1.report_builder import build_report
        results = _make_minimal_benchmark_results()
        report = build_report(results, None, None)
        assert "Acceptance Gate" in report or "acceptance gate" in report.lower()

    def test_SS_REP_07_need_more_data_when_insufficient_gt(self):
        """SS-REP-07: Verdict is NEED MORE DATA when frames_with_gt < threshold."""
        from scripts.smart_snap_poc1.report_builder import build_report
        results = _make_minimal_benchmark_results()
        results["summary"]["frames_with_gt"] = 0
        report = build_report(results, None, None)
        assert "NEED MORE DATA" in report
