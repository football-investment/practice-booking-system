"""
Lock timing metrics sanity check — daily run

Reads recent application logs and computes P50/P95 lock hold times,
IntegrityError→409 rate, and deadlock count across all four hardened pipelines.

Usage (from project root)
-------------------------
    python scripts/validate_lock_metrics.py [--log-file PATH] [--since-hours N] [--strict]

    # Point at your log file explicitly:
    python scripts/validate_lock_metrics.py --log-file logs/app.log

    # Look back 48 hours instead of default 24:
    python scripts/validate_lock_metrics.py --log-file logs/app.log --since-hours 48

    # Exit 1 on warnings (strict mode):
    python scripts/validate_lock_metrics.py --log-file logs/app.log --strict

Log format expected
-------------------
This script parses lines emitted by ``app.utils.lock_logger.lock_timer``.
Each ``lock_released`` event is a JSON object embedded in a log line, e.g.::

    2026-02-19 10:15:32,456 INFO ... {"event": "lock_released", "pipeline": "reward",
        "entity_type": "Semester", "entity_id": 7,
        "lock_released_at": "2026-02-19T10:15:32.456000+00:00", "duration_ms": 42.3}

Also counts lines containing ``IntegrityError`` and ``deadlock detected``
(PostgreSQL's deadlock error message).

Thresholds
----------
  MET-L01  P95 lock hold time ≤ 500 ms per pipeline (WARNING if exceeded)
  MET-L02  Deadlock count = 0 in window (ERROR if > 0)
  MET-L03  IntegrityError rate ≤ 5 % of lock_released events (WARNING if exceeded)

Exits 0 if all checks pass (warnings do not cause exit 1 unless --strict).
Exits 1 on errors or (in strict mode) warnings.

Run daily (CI cron or manual):
    0 8 * * * cd /path/to/project && \\
        python scripts/validate_lock_metrics.py --log-file logs/app.log \\
        >> logs/lock_metrics_daily.log 2>&1

Complements:
    scripts/validate_skill_pipeline.py   — skill progression DB-level invariants
    scripts/validate_reward_pipeline.py  — reward/XP DB-level invariants
    scripts/validate_enrollment_pipeline.py — enrollment DB-level invariants
"""
from __future__ import annotations

import sys
import os
import json
import re
import argparse
import statistics
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import DefaultDict, List

parser = argparse.ArgumentParser(
    description="Lock timing metrics sanity check (daily)"
)
parser.add_argument("--log-file",    type=str,  default=None,
                    help="Path to the application log file. "
                         "If omitted, reads from stdin.")
parser.add_argument("--since-hours", type=int,  default=24,
                    help="Look at events in the last N hours (default: 24)")
parser.add_argument("--strict",      action="store_true",
                    help="Exit 1 on warnings as well as errors")
args = parser.parse_args()

errors:   list[str] = []
warnings: list[str] = []

since = datetime.now(tz=timezone.utc) - timedelta(hours=args.since_hours)

print("=" * 65)
print("LOCK TIMING METRICS SANITY CHECK")
print(f"Run at : {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
print(f"Window : last {args.since_hours}h  (since {since.strftime('%Y-%m-%d %H:%M UTC')})")
print(f"Source : {args.log_file or 'stdin'}")
print("=" * 65)


# ─── Collect log lines ────────────────────────────────────────────────────────

if args.log_file:
    if not os.path.exists(args.log_file):
        print(f"\n⚠️  Log file not found: {args.log_file}")
        print("    This is expected if the application has not yet written any logs.")
        print("    Skipping metric analysis — exiting 0.")
        sys.exit(0)
    with open(args.log_file, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
else:
    lines = sys.stdin.readlines()

print(f"\n  Read {len(lines):,} log lines.")


# ─── Parse lock_released events ───────────────────────────────────────────────

# Counters per pipeline
durations_by_pipeline: DefaultDict[str, List[float]] = defaultdict(list)
total_lock_events = 0

# Global counters
integrity_error_count = 0
deadlock_count = 0

_JSON_RE = re.compile(r'\{.*"event"\s*:\s*"lock_released".*\}')

for raw_line in lines:
    line = raw_line.rstrip()

    # Count IntegrityError mentions (R02/R05/R06 SAVEPOINT paths)
    if "IntegrityError" in line:
        integrity_error_count += 1

    # Count PostgreSQL deadlock detections
    if "deadlock detected" in line.lower():
        deadlock_count += 1

    # Try to extract a lock_released JSON object
    m = _JSON_RE.search(line)
    if not m:
        continue

    try:
        event = json.loads(m.group(0))
    except json.JSONDecodeError:
        continue

    if event.get("event") != "lock_released":
        continue

    # Apply time-window filter using lock_released_at
    released_at_raw = event.get("lock_released_at")
    if released_at_raw:
        try:
            released_at = datetime.fromisoformat(released_at_raw)
            if released_at.tzinfo is None:
                released_at = released_at.replace(tzinfo=timezone.utc)
            if released_at < since:
                continue
        except (ValueError, TypeError):
            pass  # malformed timestamp — include it anyway

    pipeline    = event.get("pipeline", "unknown")
    duration_ms = event.get("duration_ms")

    if duration_ms is not None:
        try:
            durations_by_pipeline[pipeline].append(float(duration_ms))
            total_lock_events += 1
        except (TypeError, ValueError):
            pass

print(f"  lock_released events in window: {total_lock_events}")
print(f"  IntegrityError mentions : {integrity_error_count}")
print(f"  Deadlock mentions       : {deadlock_count}")


# ─── MET-L02: Deadlock count ──────────────────────────────────────────────────

print(f"\n[MET-L02] Deadlock check…")
if deadlock_count == 0:
    print("  ✅ No deadlocks detected in window.")
else:
    errors.append(
        f"DEADLOCK DETECTED: {deadlock_count} 'deadlock detected' mention(s) in log — "
        f"review lock ordering against SYSTEM_CONCURRENCY_ARCHITECTURE_2026.md §4"
    )
    print(f"  ❌ {deadlock_count} deadlock mention(s) found — immediate investigation required.")


# ─── MET-L01: P50/P95 lock hold time per pipeline ────────────────────────────

P95_WARN_MS = 500.0   # warn if P95 > 500 ms
P95_ERR_MS  = 2000.0  # error if P95 > 2 s

print(f"\n[MET-L01] Lock hold time per pipeline (threshold: P95 ≤ {P95_WARN_MS:.0f} ms)…")

ALL_PIPELINES = ["enrollment", "booking", "reward", "skill"]

if not durations_by_pipeline:
    print("  ℹ️  No lock_released events found — no metrics to compute.")
    print("     Possible causes: log file has no entries yet, or lock_logger not yet active.")
else:
    for pipeline in ALL_PIPELINES:
        durations = durations_by_pipeline.get(pipeline, [])
        if not durations:
            print(f"  ℹ️  {pipeline:<12} — no events in window")
            continue

        p50 = statistics.median(durations)
        p95 = statistics.quantiles(durations, n=20)[18] if len(durations) >= 2 else durations[0]
        p_max = max(durations)
        count = len(durations)

        print(
            f"  {pipeline:<12}  count={count:>5}  "
            f"P50={p50:>7.1f} ms  P95={p95:>7.1f} ms  max={p_max:>7.1f} ms"
        )

        if p95 > P95_ERR_MS:
            errors.append(
                f"P95 LOCK HOLD TIME CRITICAL ({pipeline}): {p95:.1f} ms > {P95_ERR_MS:.0f} ms — "
                f"severe lock contention or O(N×M) query inside lock scope"
            )
        elif p95 > P95_WARN_MS:
            warnings.append(
                f"P95 LOCK HOLD TIME ELEVATED ({pipeline}): {p95:.1f} ms > {P95_WARN_MS:.0f} ms — "
                f"consider Performance sprint (Option A)"
            )

    # Also report any pipeline not in the known list
    unknown = set(durations_by_pipeline) - set(ALL_PIPELINES)
    for pipeline in sorted(unknown):
        durations = durations_by_pipeline[pipeline]
        p50 = statistics.median(durations)
        p95 = statistics.quantiles(durations, n=20)[18] if len(durations) >= 2 else durations[0]
        print(
            f"  {pipeline:<12}  count={len(durations):>5}  "
            f"P50={p50:>7.1f} ms  P95={p95:>7.1f} ms  "
            f"[unknown pipeline — verify lock_timer() call site]"
        )


# ─── MET-L03: IntegrityError rate ────────────────────────────────────────────

INTEGRITY_RATE_WARN = 5.0  # warn if IntegrityError% > 5%

print(f"\n[MET-L03] IntegrityError rate (threshold: ≤ {INTEGRITY_RATE_WARN:.0f}% of lock events)…")

if total_lock_events == 0:
    print("  ℹ️  No lock events — skipping rate check.")
else:
    ie_rate = round(integrity_error_count / total_lock_events * 100, 2)
    print(f"  IntegrityError : {integrity_error_count} ({ie_rate:.2f}% of {total_lock_events} lock events)")
    if ie_rate > INTEGRITY_RATE_WARN:
        warnings.append(
            f"HIGH IntegrityError RATE: {ie_rate:.2f}% ({integrity_error_count}/{total_lock_events}) — "
            f"SAVEPOINT paths (R02/R05/R06) being hit frequently; review unique constraint coverage"
        )
        print(f"  ⚠️  Rate {ie_rate:.2f}% exceeds {INTEGRITY_RATE_WARN:.0f}% threshold")
    else:
        print(f"  ✅ IntegrityError rate {ie_rate:.2f}% within threshold (≤ {INTEGRITY_RATE_WARN:.0f}%)")


# ─── Final result ─────────────────────────────────────────────────────────────

print("\n" + "=" * 65)

if errors:
    print(f"❌  FAILED — {len(errors)} ERROR(S), {len(warnings)} WARNING(S)")
    for e in errors:
        print(f"   ERROR   : {e}")
    for w in warnings:
        print(f"   WARNING : {w}")
    sys.exit(1)
elif warnings and args.strict:
    print(f"⚠️   STRICT MODE FAIL — 0 errors, {len(warnings)} warning(s)")
    for w in warnings:
        print(f"   WARNING : {w}")
    sys.exit(1)
elif warnings:
    print(f"⚠️   PASSED WITH WARNINGS — 0 errors, {len(warnings)} warning(s)")
    for w in warnings:
        print(f"   WARNING : {w}")
    sys.exit(0)
else:
    print("✅  ALL CHECKS PASSED — lock timing metrics within thresholds")
    sys.exit(0)
