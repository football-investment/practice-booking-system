#!/usr/bin/env python3
"""
Mutation Testing Report — reads .mutmut-cache SQLite directly.

Why not `mutmut results`?
  mutmut 2.4.4's `results` CLI crashes with a pony ORM error when called from
  the command line. Reading the SQLite cache directly is the reliable alternative.

Usage:
  python scripts/mutation_report.py                  # print to stdout
  python scripts/mutation_report.py --check-baseline # exit 1 if any module
                                                     # is below effective target

In CI this script also writes Markdown to $GITHUB_STEP_SUMMARY when that
environment variable is set (GitHub Actions). Always exits 0 unless
--check-baseline is passed (non-blocking by default).
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
CACHE_PATH = ROOT / ".mutmut-cache"
BASELINE_PATH = ROOT / "tests" / "snapshots" / "mutation_baseline.json"

# Canonical module name → short label for table display
_SHORT = {
    "app/services/sandbox_verdict_calculator.py": "sandbox_verdict_calculator",
    "app/services/specialization_validation.py": "specialization_validation",
    "app/services/credit_service.py": "credit_service",
}


def _load_baseline():
    if not BASELINE_PATH.exists():
        return None
    with open(BASELINE_PATH) as f:
        return json.load(f)


def _query_cache():
    """Return {filename: {killed, survived, suspicious, total}} from SQLite."""
    if not CACHE_PATH.exists():
        return {}
    conn = sqlite3.connect(CACHE_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT sf.filename, m.status, COUNT(*) cnt
          FROM Mutant m
          JOIN Line l ON m.line = l.id
          JOIN SourceFile sf ON l.sourcefile = sf.id
         GROUP BY sf.filename, m.status
         ORDER BY sf.filename, m.status
        """
    )
    rows = cur.fetchall()
    conn.close()

    result = {}
    for filename, status, cnt in rows:
        if filename not in result:
            result[filename] = {"killed": 0, "survived": 0, "suspicious": 0, "total": 0}
        if status == "ok_killed":
            result[filename]["killed"] += cnt
        elif status == "bad_survived":
            result[filename]["survived"] += cnt
        elif status == "ok_suspicious":
            result[filename]["suspicious"] += cnt
        result[filename]["total"] += cnt
    return result


def _pct(n, d):
    if d == 0:
        return 0.0
    return round(n / d * 100, 1)


def _delta_str(current_rate, baseline_rate):
    if baseline_rate is None:
        return "—"
    delta = current_rate - baseline_rate * 100
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.1f}pp"


def build_report(cache, baseline):
    lines = []
    lines.append("## Mutation Testing Report")
    lines.append("")

    if not cache:
        lines.append("> No `.mutmut-cache` found. Run `bash scripts/run_mutation_tests.sh` first.")
        return "\n".join(lines), True

    if baseline:
        lines.append(f"> Baseline version: **{baseline['version']}** "
                     f"| last updated: {baseline['last_updated']}")
        lines.append(f"> Project target: **≥{int(baseline['project_target_kill_rate'] * 100)}%** "
                     f"kill rate per module")
    lines.append("")

    # Per-module table
    header = "| Module | Total | Killed | Survived | Kill Rate | Target | Status |"
    sep =    "|--------|-------|--------|----------|-----------|--------|--------|"
    lines.append(header)
    lines.append(sep)

    total_killed = total_survived = total_all = 0
    any_below = False

    for filename in sorted(_SHORT.keys()):
        label = _SHORT[filename]
        data = cache.get(filename, {})
        killed = data.get("killed", 0)
        survived = data.get("survived", 0)
        total = data.get("total", 0)
        rate = _pct(killed, total)

        total_killed += killed
        total_survived += survived
        total_all += total

        bmod = (baseline or {}).get("modules", {}).get(filename, {})
        target = bmod.get("target", 0.70)
        target_pct = int(target * 100)
        acceptable = bmod.get("acceptable_survivor_count", 0)
        effective_total = total - acceptable
        effective_killed = min(killed, effective_total)
        effective_rate = _pct(effective_killed, effective_total)
        baseline_rate = bmod.get("kill_rate")

        if acceptable > 0:
            status_str = (
                f"⚠️ {rate}% raw · {effective_rate}% eff. "
                f"({acceptable}/{survived} acceptable)"
            )
            # Use effective rate for target check
            meets = effective_rate >= target_pct
        else:
            status_str = "✅" if rate >= target_pct else "❌"
            meets = rate >= target_pct

        if not meets:
            any_below = True

        lines.append(
            f"| `{label}` | {total} | {killed} | {survived} | {rate}% | ≥{target_pct}% | {status_str} |"
        )

    # Combined row
    combined_rate = _pct(total_killed, total_all)
    lines.append(
        f"| **Combined** | **{total_all}** | **{total_killed}** | **{total_survived}** "
        f"| **{combined_rate}%** | ≥70% | {'✅' if combined_rate >= 70 else '❌'} |"
    )
    lines.append("")

    # Sprint trend table
    if baseline and baseline.get("history"):
        lines.append("### Sprint Trend")
        lines.append("")
        lines.append("| Sprint | Killed | Total | Combined Rate | Delta |")
        lines.append("|--------|--------|-------|---------------|-------|")
        prev_rate = None
        for entry in baseline["history"]:
            sp = entry["sprint"]
            k = entry["killed"]
            t = entry["total"]
            r = round(entry["combined_kill_rate"] * 100, 1)
            delta = _delta_str(r, prev_rate) if prev_rate is not None else "—"
            lines.append(f"| Sprint {sp} | {k} | {t} | {r}% | {delta} |")
            prev_rate = entry["combined_kill_rate"]
        # current run (from cache)
        if total_all > 0:
            delta = _delta_str(combined_rate, prev_rate)
            lines.append(f"| **Current** | **{total_killed}** | **{total_all}** "
                         f"| **{combined_rate}%** | {delta} |")
        lines.append("")

    lines.append("> **Non-blocking:** surviving mutants do not prevent PRs from merging.")
    lines.append("> Track kill rate trends in `TESTING.md` — Mutation Testing section.")

    return "\n".join(lines), any_below


def main():
    check_baseline = "--check-baseline" in sys.argv

    cache = _query_cache()
    baseline = _load_baseline()
    report, any_below = build_report(cache, baseline)

    print(report)

    # Write to GitHub Step Summary if running in CI
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a") as f:
            f.write(report + "\n")

    if check_baseline and any_below:
        print("\n[mutation_report] One or more modules are below effective target.", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
