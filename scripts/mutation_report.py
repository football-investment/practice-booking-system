#!/usr/bin/env python3
"""
Mutation Testing Report — reads .mutmut-cache SQLite directly.

Why not `mutmut results`?
  mutmut 2.4.4's `results` CLI crashes with a pony ORM error when called from
  the command line. Reading the SQLite cache directly is the reliable alternative.

Usage:
  python scripts/mutation_report.py                   # print to stdout
  python scripts/mutation_report.py --check-regression # exit 1 if combined kill rate
                                                       # dropped ≥2pp from last baseline
                                                       # or per-module dropped ≥3pp

In CI this script also writes Markdown to $GITHUB_STEP_SUMMARY when that
environment variable is set (GitHub Actions). Always exits 0 unless
--check-regression is passed (non-blocking by default).

Dashboard:
  Sprint trend bar chart (ASCII) is appended to the report for visual tracking.
  Long-term milestone target is read from baseline['milestone_kill_rate'].
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
    "app/services/license_authorization_service.py": "license_authorization_service",
    "app/services/gamification/xp_service.py": "xp_service",
    "app/services/enrollment_conflict_service.py": "enrollment_conflict_service",
    "app/services/license_renewal_service.py": "license_renewal_service",
}

# Regression tolerances
_COMBINED_TOLERANCE = 0.02   # 2pp: combined kill rate may drop at most 2pp from baseline
_MODULE_TOLERANCE = 0.03     # 3pp: per-module effective kill rate may drop at most 3pp


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


def _effective_rate(killed, total, acceptable):
    effective_total = total - acceptable
    effective_killed = min(killed, effective_total)
    return _pct(effective_killed, effective_total), effective_total


def _bar(rate_pct, width=20):
    """ASCII progress bar: ████████████░░░░░░░░ for a given percentage (0–100)."""
    filled = round(rate_pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


def build_dashboard(baseline, current_combined_rate=None, current_total_killed=None, current_total_all=None):
    """
    Build an ASCII bar chart showing the sprint-by-sprint combined kill rate trend.
    Includes the long-term milestone target line if defined in baseline.
    Returns a Markdown code block string.
    """
    if not baseline or not baseline.get("history"):
        return ""

    milestone = baseline.get("milestone_kill_rate")  # e.g. 0.80
    target = baseline.get("project_target_kill_rate", 0.70)

    lines = []
    lines.append("### Kill Rate Trend Dashboard")
    lines.append("")
    lines.append("```")
    lines.append(f"  Combined kill rate — target ≥{int(target * 100)}%"
                 + (f"  |  milestone ≥{int(milestone * 100)}%" if milestone else ""))
    lines.append("")

    for entry in baseline["history"]:
        sp = entry["sprint"]
        r = entry["combined_kill_rate"] * 100
        bar = _bar(r)
        lines.append(f"  Sprint {sp:>2}  {bar}  {r:.1f}%")

    # Current run row (from live cache)
    if current_total_all and current_total_all > 0:
        r = current_combined_rate
        bar = _bar(r)
        lines.append(f"  Current   {bar}  {r:.1f}%  ({current_total_killed}/{current_total_all})")

    lines.append("")
    # Target line
    target_bar = _bar(target * 100)
    lines.append(f"  Target    {target_bar}  {int(target * 100)}%  (per-module minimum)")
    if milestone:
        m_bar = _bar(milestone * 100)
        lines.append(f"  Milestone {m_bar}  {int(milestone * 100)}%  (long-term goal)")
    lines.append("```")
    lines.append("")

    if milestone:
        gap = milestone * 100 - (current_combined_rate or 0)
        if gap > 0 and current_total_all:
            lines.append(f"> Milestone gap: **{gap:.1f}pp** to reach ≥{int(milestone * 100)}% "
                         f"combined kill rate.")
        elif current_total_all:
            lines.append(f"> Milestone **≥{int(milestone * 100)}%** achieved! 🎯")

    return "\n".join(lines)


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
        eff_rate, _ = _effective_rate(killed, total, acceptable)
        baseline_rate = bmod.get("kill_rate")

        if total == 0:
            status_str = "⏳ pending first run"
            meets = True  # not yet measured — don't flag as failure
        elif acceptable > 0:
            status_str = (
                f"⚠️ {rate}% raw · {eff_rate}% eff. "
                f"({acceptable}/{survived} acceptable)"
            )
            meets = eff_rate >= target_pct
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
    milestone = (baseline or {}).get("milestone_kill_rate", 0.70)
    milestone_pct = int(milestone * 100)
    combined_status = "✅" if combined_rate >= milestone_pct else f"⬆️ milestone ≥{milestone_pct}%"
    lines.append(
        f"| **Combined** | **{total_all}** | **{total_killed}** | **{total_survived}** "
        f"| **{combined_rate}%** | ≥{milestone_pct}% | {combined_status} |"
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

    # ASCII bar chart dashboard
    dashboard = build_dashboard(
        baseline,
        current_combined_rate=combined_rate if total_all > 0 else None,
        current_total_killed=total_killed if total_all > 0 else None,
        current_total_all=total_all if total_all > 0 else None,
    )
    if dashboard:
        lines.append(dashboard)

    lines.append("> **Non-blocking:** surviving mutants do not prevent PRs from merging.")
    lines.append("> Track kill rate trends in `TESTING.md` — Mutation Testing section.")

    return "\n".join(lines), any_below


def build_regression_report(cache, baseline):
    """
    Compare current kill rates against the last recorded sprint baseline.
    Returns (report_text, has_regression).
    """
    if not baseline or not baseline.get("history"):
        return "No baseline history — skipping regression check.", False

    last_sprint = baseline["history"][-1]
    last_combined = last_sprint["combined_kill_rate"]
    combined_threshold = last_combined - _COMBINED_TOLERANCE

    lines = []
    lines.append("### Regression Check")
    lines.append("")
    lines.append(f"> Last baseline (Sprint {last_sprint['sprint']}): "
                 f"**{last_combined * 100:.1f}%** combined")
    lines.append(f"> Regression threshold: **≥{combined_threshold * 100:.1f}%** "
                 f"(tolerance: {_COMBINED_TOLERANCE * 100:.0f}pp)")
    lines.append("")

    # Per-module regression table
    lines.append("| Module | Baseline | Current | Delta | Status |")
    lines.append("|--------|----------|---------|-------|--------|")

    has_regression = False

    # Track totals for combined check
    total_killed = total_all = 0

    for filename in sorted(_SHORT.keys()):
        label = _SHORT[filename]
        data = cache.get(filename, {})
        killed = data.get("killed", 0)
        total = data.get("total", 0)

        total_killed += killed
        total_all += total

        bmod = (baseline or {}).get("modules", {}).get(filename, {})
        baseline_kill_rate = bmod.get("kill_rate")  # last confirmed rate
        acceptable = bmod.get("acceptable_survivor_count", 0)

        if total == 0 or baseline_kill_rate is None:
            lines.append(f"| `{label}` | — | — | — | ⏳ pending |")
            continue

        eff_rate, _ = _effective_rate(killed, total, acceptable)
        eff_rate_frac = eff_rate / 100
        # Use effective rate vs baseline kill_rate for comparison
        baseline_eff = bmod.get("effective_kill_rate", baseline_kill_rate)
        threshold = baseline_eff - _MODULE_TOLERANCE
        delta_pp = (eff_rate_frac - baseline_eff) * 100
        sign = "+" if delta_pp >= 0 else ""
        delta_str = f"{sign}{delta_pp:.1f}pp"

        if eff_rate_frac < threshold:
            has_regression = True
            status = f"❌ REGRESSION (threshold: ≥{threshold * 100:.1f}%)"
        else:
            status = "✅"

        lines.append(
            f"| `{label}` | {baseline_eff * 100:.1f}% | {eff_rate}% | {delta_str} | {status} |"
        )

    # Combined regression check
    if total_all > 0:
        combined_rate = total_killed / total_all
        delta_pp = (combined_rate - last_combined) * 100
        sign = "+" if delta_pp >= 0 else ""
        combined_delta = f"{sign}{delta_pp:.1f}pp"

        if combined_rate < combined_threshold:
            has_regression = True
            combined_status = f"❌ REGRESSION (threshold: ≥{combined_threshold * 100:.1f}%)"
        else:
            combined_status = "✅"

        lines.append(
            f"| **Combined** | **{last_combined * 100:.1f}%** | **{combined_rate * 100:.1f}%** "
            f"| **{combined_delta}** | {combined_status} |"
        )

    lines.append("")
    if has_regression:
        lines.append("> ❌ **Regression detected.** Kill rate dropped beyond tolerance.")
        lines.append("> Investigate surviving mutants with `python scripts/mutation_report.py`")
        lines.append("> and `python -m mutmut show <id>` for specific mutant diffs.")
    else:
        lines.append("> ✅ **No regression.** Kill rate is within tolerance of baseline.")

    return "\n".join(lines), has_regression


def main():
    check_regression = "--check-regression" in sys.argv

    cache = _query_cache()
    baseline = _load_baseline()
    report, any_below = build_report(cache, baseline)

    output_parts = [report]

    if check_regression:
        reg_report, has_regression = build_regression_report(cache, baseline)
        output_parts.append(reg_report)
    else:
        has_regression = False

    full_output = "\n\n".join(output_parts)
    print(full_output)

    # Write to GitHub Step Summary if running in CI
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a") as f:
            f.write(full_output + "\n")

    if check_regression and has_regression:
        print("\n[mutation_report] Regression detected — kill rate dropped beyond tolerance.",
              file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
