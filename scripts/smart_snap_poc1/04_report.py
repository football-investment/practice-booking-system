#!/usr/bin/env python3
"""
04_report.py — Smart Snap POC-1 report generator (CLI wrapper).

Report logic is in report_builder.py (importable module).

Usage:
    python scripts/smart_snap_poc1/04_report.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.smart_snap_poc1.config import (
    BENCHMARK_RESULTS_PATH,
    GROUND_TRUTH_PATH,
    MANIFEST_PATH,
    REPORT_PATH,
)
from scripts.smart_snap_poc1.report_builder import _load, build_report


def run() -> None:
    results = _load(BENCHMARK_RESULTS_PATH)
    if results is None:
        print(f"ERROR: {BENCHMARK_RESULTS_PATH} not found. Run 03_benchmark.py first.", file=sys.stderr)
        sys.exit(1)

    manifest = _load(MANIFEST_PATH)
    gt_data = _load(GROUND_TRUTH_PATH)

    report = build_report(results, manifest, gt_data)

    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        fh.write(report)

    print(f"report.md written to {REPORT_PATH}")

    for line in report.split("\n"):
        if line.startswith("### ") and any(v in line for v in ("PROCEED", "NEED MORE", "REJECT")):
            print(f"\n{'='*60}")
            print(f"VERDICT: {line.replace('### ', '')}")
            print(f"{'='*60}\n")
            break


if __name__ == "__main__":
    run()
