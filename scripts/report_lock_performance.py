"""
Lock performance report — run after 3–5 days of production data collection.

Produces a structured, human-readable report with:
  - Per-pipeline: count, P50 / P95 / P99 / max lock hold time
  - Per-caller breakdown (lock frequency and timing per call site)
  - Decision threshold evaluation against Option A thresholds
  - Actionable next-step recommendation

Usage (from project root)
-------------------------
    # After collecting 5 days of logs (recommended):
    python scripts/report_lock_performance.py --log-file logs/app.log

    # Custom window:
    python scripts/report_lock_performance.py --log-file logs/app.log --since-days 5

    # Output as JSON for CI/dashboard ingestion:
    python scripts/report_lock_performance.py --log-file logs/app.log --json

Thresholds (from PERFORMANCE_AUDIT_PLAN_2026-02-19.md)
-------------------------------------------------------
  UserLicense lock P95 > 200 ms  → trigger batch-query optimisation (get_skill_profile N×M)
  Semester lock P95   > 500 ms   → investigate commit boundary narrowing in finalize()
  Any deadlock count  > 0        → immediate incident sprint
  IntegrityError rate > 5 %      → review SAVEPOINT path coverage

Exit codes
----------
  0  All thresholds met — no action required
  1  One or more thresholds breached — action required (see NEXT STEPS in output)
  2  Not enough data (< MIN_SAMPLE_SIZE events per pipeline)
"""
from __future__ import annotations

import sys
import os
import json
import re
import argparse
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import DefaultDict, Dict, List, Optional

# ─── CLI ──────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(
    description="Lock performance report (run after 3-5 days of production data)"
)
parser.add_argument("--log-file",    type=str, required=False, default=None,
                    help="Path to application log file (default: stdin)")
parser.add_argument("--since-days",  type=int, default=5,
                    help="Analyse events in the last N days (default: 5)")
parser.add_argument("--json",        action="store_true",
                    help="Output report as JSON (for CI/dashboard)")
args = parser.parse_args()

since = datetime.now(tz=timezone.utc) - timedelta(days=args.since_days)

# ─── Thresholds ───────────────────────────────────────────────────────────────

THRESHOLDS = {
    # (pipeline, entity_type or caller fragment): P95 warn threshold ms
    "skill.UserLicense.P95":       200.0,  # → batch-query optimisation
    "reward.Semester.P95":         500.0,  # → commit boundary investigation
    "default.P95":                 500.0,  # other pipelines
    "default.P95.critical":       2000.0,  # error (severe contention)
    "integrity_error_rate_warn":     5.0,  # %
    "min_sample_size":              20,    # events before thresholds apply
}

# ─── Read log lines ───────────────────────────────────────────────────────────

if args.log_file:
    if not os.path.exists(args.log_file):
        msg = f"Log file not found: {args.log_file}"
        if args.json:
            print(json.dumps({"error": msg, "exit": 2}))
        else:
            print(f"\n⚠️  {msg}")
            print("    Collect 3–5 days of production logs before running this report.")
        sys.exit(2)
    with open(args.log_file, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
else:
    lines = sys.stdin.readlines()

# ─── Parse events ─────────────────────────────────────────────────────────────

_JSON_RE = re.compile(r'\{.*"event"\s*:\s*"lock_released".*\}')

# pipeline → list[duration_ms]
durations_by_pipeline: DefaultDict[str, List[float]] = defaultdict(list)

# pipeline → caller → list[duration_ms]
durations_by_caller: DefaultDict[str, DefaultDict[str, List[float]]] = defaultdict(
    lambda: defaultdict(list)
)

# For Semester / UserLicense breakdown (cross-pipeline entity tracking)
durations_by_entity: DefaultDict[str, List[float]] = defaultdict(list)

total_events      = 0
integrity_errors  = 0
deadlocks         = 0

for raw in lines:
    line = raw.rstrip()

    if "IntegrityError" in line:
        integrity_errors += 1
    if "deadlock detected" in line.lower():
        deadlocks += 1

    m = _JSON_RE.search(line)
    if not m:
        continue

    try:
        ev = json.loads(m.group(0))
    except json.JSONDecodeError:
        continue

    if ev.get("event") != "lock_released":
        continue

    # Time-window filter
    raw_ts = ev.get("lock_released_at")
    if raw_ts:
        try:
            ts = datetime.fromisoformat(raw_ts)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts < since:
                continue
        except (ValueError, TypeError):
            pass

    pipeline    = ev.get("pipeline", "unknown")
    entity_type = ev.get("entity_type", "")
    caller      = ev.get("caller", "")
    dur_raw     = ev.get("duration_ms")

    if dur_raw is None:
        continue
    try:
        dur = float(dur_raw)
    except (TypeError, ValueError):
        continue

    durations_by_pipeline[pipeline].append(dur)
    durations_by_caller[pipeline][caller or "(no caller)"].append(dur)
    durations_by_entity[f"{pipeline}.{entity_type}"].append(dur)
    total_events += 1


# ─── Compute percentiles helper ───────────────────────────────────────────────

def _percentiles(data: List[float]) -> Dict[str, float]:
    n = len(data)
    if n == 0:
        return {"count": 0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0, "min": 0.0}
    p50 = statistics.median(data)
    p95 = statistics.quantiles(data, n=20)[18] if n >= 2 else data[0]
    p99 = statistics.quantiles(data, n=100)[98] if n >= 2 else data[0]
    return {
        "count": n,
        "p50":   round(p50, 1),
        "p95":   round(p95, 1),
        "p99":   round(p99, 1),
        "max":   round(max(data), 1),
        "min":   round(min(data), 1),
    }


# ─── Evaluate thresholds ──────────────────────────────────────────────────────

actions:   list[str] = []  # "action required"
notices:   list[str] = []  # informational
decisions: Dict[str, str] = {}  # pipeline → verdict

ALL_PIPELINES = ["enrollment", "booking", "reward", "skill"]

pipeline_stats: Dict[str, Dict] = {}
for p in ALL_PIPELINES:
    data = durations_by_pipeline.get(p, [])
    stats = _percentiles(data)
    pipeline_stats[p] = stats

    if stats["count"] == 0:
        decisions[p] = "NO_DATA"
        continue
    if stats["count"] < THRESHOLDS["min_sample_size"]:
        decisions[p] = "INSUFFICIENT_DATA"
        notices.append(
            f"{p}: only {stats['count']} events (need ≥ {THRESHOLDS['min_sample_size']}) — collect more data"
        )
        continue

    # Pipeline-specific P95 threshold
    if p == "skill":
        warn_ms = THRESHOLDS["skill.UserLicense.P95"]
    elif p == "reward":
        warn_ms = THRESHOLDS["reward.Semester.P95"]
    else:
        warn_ms = THRESHOLDS["default.P95"]

    crit_ms = THRESHOLDS["default.P95.critical"]

    if stats["p95"] > crit_ms:
        decisions[p] = "CRITICAL"
        actions.append(
            f"CRITICAL — {p} P95={stats['p95']:.0f} ms > {crit_ms:.0f} ms: "
            f"severe lock contention; immediate investigation."
        )
    elif stats["p95"] > warn_ms:
        decisions[p] = "ACTION_REQUIRED"
        if p == "skill":
            actions.append(
                f"ACTION — skill pipeline UserLicense P95={stats['p95']:.0f} ms > {warn_ms:.0f} ms: "
                f"start get_skill_profile batch-query optimisation (N×M elimination)."
            )
        elif p == "reward":
            actions.append(
                f"ACTION — reward pipeline Semester P95={stats['p95']:.0f} ms > {warn_ms:.0f} ms: "
                f"investigate commit boundary narrowing in TournamentFinalizer.finalize()."
            )
        else:
            actions.append(
                f"ACTION — {p} pipeline P95={stats['p95']:.0f} ms > {warn_ms:.0f} ms: "
                f"investigate lock contention."
            )
    else:
        decisions[p] = "OK"

if deadlocks > 0:
    actions.insert(0,
        f"CRITICAL — {deadlocks} deadlock(s) detected: IMMEDIATE INCIDENT SPRINT. "
        f"Review lock ordering: Semester → UserLicense → TournamentParticipation."
    )

ie_rate = round(integrity_errors / total_events * 100, 2) if total_events > 0 else 0.0
if ie_rate > THRESHOLDS["integrity_error_rate_warn"]:
    notices.append(
        f"IntegrityError rate {ie_rate:.2f}% > {THRESHOLDS['integrity_error_rate_warn']:.0f}% "
        f"— SAVEPOINT collision paths under load; review unique constraint coverage."
    )


# ─── Output ───────────────────────────────────────────────────────────────────

if args.json:
    report = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "window_days":  args.since_days,
        "total_events": total_events,
        "deadlocks":    deadlocks,
        "integrity_error_rate_pct": ie_rate,
        "pipelines":    pipeline_stats,
        "decisions":    decisions,
        "actions":      actions,
        "notices":      notices,
    }
    print(json.dumps(report, indent=2))
    sys.exit(1 if actions else 0)


# ─── Text report ──────────────────────────────────────────────────────────────

W = 70
print("=" * W)
print("LOCK PERFORMANCE REPORT — Option A Decision Gate")
print(f"Generated : {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
print(f"Window    : last {args.since_days} days  (since {since.strftime('%Y-%m-%d')})")
print(f"Source    : {args.log_file or 'stdin'}")
print(f"Events    : {total_events:,}  |  Deadlocks: {deadlocks}  |  IntegrityErrors: {integrity_errors}")
print("=" * W)

print(f"\n{'Pipeline':<12}  {'Count':>6}  {'P50':>8}  {'P95':>8}  {'P99':>8}  {'Max':>8}  Verdict")
print("-" * W)

for p in ALL_PIPELINES:
    s = pipeline_stats.get(p, {"count": 0})
    verdict = decisions.get(p, "NO_DATA")
    verdict_icon = {
        "OK": "✅", "ACTION_REQUIRED": "⚠️ ", "CRITICAL": "❌",
        "NO_DATA": "—", "INSUFFICIENT_DATA": "⏳",
    }.get(verdict, "?")

    if s["count"] == 0:
        print(f"  {p:<12}  {'—':>6}  {'—':>8}  {'—':>8}  {'—':>8}  {'—':>8}  {verdict_icon} {verdict}")
    else:
        print(
            f"  {p:<12}  {s['count']:>6}  "
            f"{s['p50']:>6.0f}ms  {s['p95']:>6.0f}ms  "
            f"{s['p99']:>6.0f}ms  {s['max']:>6.0f}ms  "
            f"{verdict_icon} {verdict}"
        )

print("-" * W)

# Per-caller breakdown
print(f"\n{'CALL SITE BREAKDOWN':}")
print("-" * W)
for p in ALL_PIPELINES:
    callers = durations_by_caller.get(p)
    if not callers:
        continue
    print(f"\n  {p}:")
    for caller, data in sorted(callers.items(), key=lambda x: -len(x[1])):
        s = _percentiles(data)
        print(
            f"    {caller:<50}  count={s['count']:>5}  "
            f"P95={s['p95']:>6.0f}ms  max={s['max']:>6.0f}ms"
        )

# Decision summary
print(f"\n{'=' * W}")
print("DECISION GATE SUMMARY")
print("-" * W)

if deadlocks > 0:
    print(f"\n  ❌  DEADLOCK(S) DETECTED: {deadlocks} — immediate action required.\n")

if not actions and not notices:
    print(f"\n  ✅  All thresholds met — no optimization required at this time.")
    print(f"      Next measurement window: collect 5 more days, then re-run.")
else:
    if actions:
        print(f"\n  Required actions ({len(actions)}):")
        for i, a in enumerate(actions, 1):
            print(f"    {i}. {a}")
    if notices:
        print(f"\n  Notices ({len(notices)}):")
        for n in notices:
            print(f"    ℹ️  {n}")

print(f"\n{'=' * W}")
print("OPTION A THRESHOLDS (ref: PERFORMANCE_AUDIT_PLAN_2026-02-19.md)")
print("-" * W)
print(f"  skill  UserLicense P95 > {THRESHOLDS['skill.UserLicense.P95']:.0f} ms  → batch get_skill_profile (N×M elimination)")
print(f"  reward Semester    P95 > {THRESHOLDS['reward.Semester.P95']:.0f} ms  → commit boundary narrowing in finalize()")
print(f"  any    deadlock    > 0       → immediate incident sprint")
print(f"  any    P95         > {THRESHOLDS['default.P95.critical']:.0f} ms  → critical — escalate immediately")
print("=" * W)

sys.exit(1 if actions else 0)
