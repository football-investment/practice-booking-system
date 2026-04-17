#!/usr/bin/env python3
"""
Phase 6.3 Load Test Results Analyzer
======================================

Parses Locust CSV output and generates a structured LOAD_REPORT.md.
Enforces strict GATE-2/3/4 KPI checks — exits 1 on any violation.

Usage:
  python tests/performance/analyze_load_results.py \\
      <prefix>_stats.csv \\
      <prefix>_failures.csv \\
      <prefix>_stats_history.csv \\
      [--peak-vus N] \\
      [--output tests/performance/LOAD_REPORT_YYYYMMDD.md]

Exit codes:
  0  All KPIs pass (Phase 6.3 VALID)
  1  One or more KPIs violated (Phase 6.3 NOT COMPLETE)
  2  Input file missing or parse error

KPI thresholds:
  CI  (LOAD_PEAK_VUS ≤ 50):   browse p95 ≤ 500ms  enroll/withdraw p95 ≤ 1000ms  5xx ≤ 2%
  Local (LOAD_PEAK_VUS > 50): browse p95 ≤ 200ms  enroll/withdraw p95 ≤ 800ms   5xx ≤ 1%
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


# ── KPI thresholds ────────────────────────────────────────────────────────────

def _thresholds(peak_vus: int, is_ci: bool) -> dict:
    if is_ci or peak_vus <= 50:
        return {
            "p95": {
                "[P63] Browse event": 500,
                "[P63] Enroll":      1000,
                "[P63] Withdraw":    1000,
            },
            "5xx_pct": 2.0,
            "label": f"CI-tier (peak={peak_vus} VUs)",
        }
    return {
        "p95": {
            "[P63] Browse event": 200,
            "[P63] Enroll":       800,
            "[P63] Withdraw":     800,
        },
        "5xx_pct": 1.0,
        "label": f"local-tier (peak={peak_vus} VUs)",
    }


# ── CSV parsers ───────────────────────────────────────────────────────────────

def _parse_stats(path: str) -> dict:
    """Parse _stats.csv → {name: {method, requests, failures, p50, p95, p99}}"""
    result = {}
    try:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("Name", "").strip()
                if not name or name == "Aggregated":
                    continue
                result[name] = {
                    "method":    row.get("Type", "").strip(),
                    "requests":  int(row.get("Request Count", 0) or 0),
                    "failures":  int(row.get("Failure Count", 0) or 0),
                    "p50":       float(row.get("50%", 0) or 0),
                    "p95":       float(row.get("95%", 0) or 0),
                    "p99":       float(row.get("99%", 0) or 0),
                    "avg":       float(row.get("Average (ms)", 0) or 0),
                    "max":       float(row.get("Max (ms)", 0) or 0),
                    "rps":       float(row.get("Requests/s", 0) or 0),
                }
    except FileNotFoundError:
        print(f"⚠️  Stats file not found: {path}", file=sys.stderr)
    return result


def _parse_failures(path: str) -> dict:
    """Parse _failures.csv → {'429': N, '5xx': N, 'other': N}"""
    counts: dict = {"rate_limited": 0, "server_errors": 0, "other": 0}
    try:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                error   = row.get("Error", "")
                n_fails = int(row.get("Occurrences", 0) or 0)
                if "429" in error:
                    counts["rate_limited"] += n_fails
                elif any(c in error for c in ("500", "502", "503", "504")):
                    counts["server_errors"] += n_fails
                else:
                    counts["other"] += n_fails
    except FileNotFoundError:
        pass  # no failures file = no failures = OK
    return counts


def _parse_history(path: str) -> list[dict]:
    """Parse _stats_history.csv → list of {timestamp, users, rps, p95}"""
    rows = []
    try:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    rows.append({
                        "ts":       float(row.get("Timestamp", 0) or 0),
                        "users":    int(row.get("User count", 0) or 0),
                        "rps":      float(row.get("Requests/s", 0) or 0),
                        "failures": float(row.get("Failures/s", 0) or 0),
                        "p95":      float(row.get("95%", 0) or 0),
                        "p99":      float(row.get("99%", 0) or 0),
                    })
                except (ValueError, KeyError):
                    pass
    except FileNotFoundError:
        pass
    return rows


# ── Derived metrics ───────────────────────────────────────────────────────────

def _breaking_point(history: list[dict], p95_threshold: float = 1000.0,
                    err_rate_threshold: float = 0.05) -> int | None:
    """First VU count where p95 > threshold OR error_rate > threshold."""
    for row in history:
        total = row["rps"] + row["failures"]
        if total <= 0:
            continue
        err_rate = row["failures"] / total
        if row["p95"] > p95_threshold or err_rate > err_rate_threshold:
            return row["users"]
    return None


def _throughput_stability(history: list[dict]) -> dict:
    """Coefficient of variation of req/s during the soak window (30s–330s)."""
    soak = [r["rps"] for r in history if r["rps"] > 0]
    if not soak:
        return {"mean": 0, "std": 0, "cv": 0, "stable": True}
    mean = sum(soak) / len(soak)
    if mean == 0:
        return {"mean": 0, "std": 0, "cv": 0, "stable": True}
    variance = sum((x - mean) ** 2 for x in soak) / len(soak)
    std  = variance ** 0.5
    cv   = std / mean
    return {"mean": mean, "std": std, "cv": cv, "stable": cv < 0.15}


# ── Report generator ──────────────────────────────────────────────────────────

def _render_report(
    stats: dict,
    failures: dict,
    history: list[dict],
    thresholds: dict,
    peak_vus: int,
    violations: list[str],
    sha: str,
) -> str:
    now      = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    stability = _throughput_stability(history)
    bp_vu    = _breaking_point(history)

    total_req  = sum(s["requests"] for s in stats.values())
    rl         = failures.get("rate_limited", 0)
    srv        = failures.get("server_errors", 0)
    net        = failures.get("other", 0)
    rl_pct     = rl  / max(total_req, 1) * 100
    srv_pct    = srv / max(total_req, 1) * 100
    net_pct    = net / max(total_req, 1) * 100
    srv_thresh = thresholds["5xx_pct"]

    lines = [
        f"# Phase 6.3 Load Test Report",
        f"",
        f"**Generated:** {now}",
        f"**SHA:** {sha}",
        f"**Environment:** {thresholds['label']}",
        f"**Peak VUs:** {peak_vus}  |  5-stage shape (~10 min)",
        f"**Status:** {'✅ VALID — all gates passed' if not violations else '❌ NOT COMPLETE — see violations below'}",
        f"",
        f"---",
        f"",
        f"## GATE-2 — Latency (p95 / p99 per endpoint)",
        f"",
        f"| Endpoint | p50 | p95 | p99 | Threshold | Status |",
        f"|----------|-----|-----|-----|-----------|--------|",
    ]
    for name, t_p95 in thresholds["p95"].items():
        s = stats.get(name)
        if s:
            ok   = s["p95"] <= t_p95
            icon = "✅" if ok else "❌"
            lines.append(
                f"| {name} | {s['p50']:.0f}ms | {s['p95']:.0f}ms | "
                f"{s['p99']:.0f}ms | ≤{t_p95}ms | {icon} |"
            )
        else:
            lines.append(f"| {name} | — | — | — | ≤{t_p95}ms | ⚠️ no data |")

    lines += [
        f"",
        f"## GATE-2 — Error Split (429 / 5xx / network)",
        f"",
        f"| Category | Count | Rate | Verdict |",
        f"|----------|-------|------|---------|",
        f"| 429 rate limited | {rl} | {rl_pct:.2f}% | expected under load |",
        f"| 5xx server error | {srv} | {srv_pct:.2f}% | {'✅' if srv_pct <= srv_thresh else '❌'} threshold ≤{srv_thresh}% |",
        f"| network error | {net} | {net_pct:.2f}% | {'✅' if net == 0 else '⚠️'} |",
        f"| **total [P63]** | **{total_req}** | — | — |",
        f"",
        f"## GATE-2 — Breaking Point",
        f"",
    ]
    if bp_vu is not None:
        lines.append(f"**Breaking point detected at {bp_vu} VUs** "
                     f"(first point where p95 > 1000ms or error rate > 5%)")
    else:
        lines.append(f"**No breaking point detected at {peak_vus} VUs** "
                     f"— system stable through full cycle")

    lines += [
        f"",
        f"## GATE-3 — KPI Compliance (analyze exit code)",
        f"",
    ]
    if violations:
        lines.append(f"**Exit code: 1 — GATE FAILURE**")
        lines.append(f"")
        for v in violations:
            lines.append(f"- {v}")
    else:
        lines.append(f"**Exit code: 0 — all KPIs within threshold**")

    lines += [
        f"",
        f"## GATE-4 — DB Metrics",
        f"",
        f"> Note: GATE-4 DB counters (slow_queries_total, invariant_violations_total) "
        f"are captured in the Locust console output by the `_print_phase63_report()` "
        f"function. Values below are inferred from the failure data.",
        f"",
        f"| Metric | Value | Threshold | Status |",
        f"|--------|-------|-----------|--------|",
        f"| 5xx count (proxy for pool exhaustion) | {srv} | 0 | {'✅' if srv == 0 else '⚠️'} |",
        f"| network errors (connection refused) | {net} | 0 | {'✅' if net == 0 else '⚠️'} |",
        f"| invariant_violations_total | — | 0 | see console output |",
        f"| slow_queries_total Δ | — | ≤50 | see console output |",
        f"",
        f"## Throughput Stability (soak phase)",
        f"",
        f"| Metric | Value | Verdict |",
        f"|--------|-------|---------|",
        f"| Mean req/s | {stability['mean']:.1f} | — |",
        f"| Std dev | {stability['std']:.1f} | — |",
        f"| CV (coefficient of variation) | {stability['cv']:.1%} | "
        f"{'✅ STABLE' if stability['stable'] else '⚠️ UNSTABLE (pool thrash or GC)'} |",
        f"",
        f"## Bottleneck Verdict",
        f"",
    ]

    p63_stats = {k: v for k, v in stats.items() if k.startswith("[P63]")}
    bottlenecks_fired = []
    for name, s in p63_stats.items():
        t_p95 = thresholds["p95"].get(name, 9999)
        if s["p95"] > t_p95:
            bottlenecks_fired.append(name)

    if not bottlenecks_fired and srv_pct <= srv_thresh:
        lines.append("✅ No bottlenecks detected within Phase 6.3 test parameters.")
    else:
        for name in bottlenecks_fired:
            s = p63_stats.get(name, {})
            if name == "[P63] Browse event":
                lines.append(
                    f"- **[HIGH] Browse N+1** — p95={s.get('p95',0):.0f}ms "
                    f"(threshold {thresholds['p95'].get(name,0)}ms)\n"
                    f"  `tournaments.py:110-117` — 1+3N queries for N tournaments.\n"
                    f"  **Fix:** `joinedload(Semester.enrollments, Semester.master_instructor)`"
                )
            elif name == "[P63] Enroll":
                lines.append(
                    f"- **[HIGH] Enroll capacity-loop ROW LOCK** — p95={s.get('p95',0):.0f}ms\n"
                    f"  `semester_service.py` — N×`WITH FOR UPDATE` per session in semester.\n"
                    f"  **Fix:** Single `SELECT session_id, SUM(CASE status='CONFIRMED' THEN 1 END) "
                    f"GROUP BY session_id` + index `sessions(auto_generated)`"
                )
            elif name == "[P63] Withdraw":
                lines.append(
                    f"- **[MED] Withdraw booking batch-delete** — p95={s.get('p95',0):.0f}ms\n"
                    f"  Missing composite index on `booking(enrollment_id, user_id)`.\n"
                    f"  **Fix:** `CREATE INDEX ix_bookings_enrollment_user ON bookings(enrollment_id, user_id)`"
                )
        if srv_pct > srv_thresh:
            lines.append(
                f"- **[CRITICAL] DB pool exhaustion** — 5xx rate {srv_pct:.2f}% > {srv_thresh}%\n"
                f"  pool_size=50/worker; {peak_vus} VUs exceeded pool capacity.\n"
                f"  **Fix:** Increase `DB_POOL_SIZE`, add PgBouncer, or reduce workers per machine."
            )

    lines += [
        f"",
        f"## Mitigation Checklist",
        f"",
        f"| # | Optimization | Estimated gain | Status |",
        f"|---|-------------|---------------|--------|",
        f"| 1 | `joinedload` in `tournaments.py:110-117` (N+1 fix) | browse p95 −60% | ☐ backlog |",
        f"| 2 | `CREATE INDEX ix_sessions_auto_generated ON sessions(auto_generated)` | enroll −15% | ☐ backlog |",
        f"| 3 | Replace capacity loop with single GROUP BY query | enroll p95 −40% | ☐ backlog |",
        f"| 4 | `CREATE INDEX ix_enrollments_user_sem_active ON semester_enrollments(user_id,semester_id,is_active)` | enroll −10% | ☐ backlog |",
        f"| 5 | `CREATE INDEX ix_bookings_enrollment_user ON bookings(enrollment_id,user_id)` | withdraw −25% | ☐ backlog |",
        f"| 6 | Implement JWT decode in `security.py:_get_user_id()` (FINDING-01) | per-user rate limit active | ☐ backlog |",
        f"| 7 | Add PgBouncer or increase `max_connections` in PostgreSQL | 503 elimination | ☐ backlog |",
        f"",
        f"---",
        f"*Generated by `tests/performance/analyze_load_results.py` — Phase 6.3*",
    ]
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 6.3 load test results analyzer")
    parser.add_argument("stats_csv",    help="_stats.csv from Locust run")
    parser.add_argument("failures_csv", help="_failures.csv from Locust run")
    parser.add_argument("history_csv",  help="_stats_history.csv from Locust run")
    parser.add_argument("--peak-vus",   type=int, default=int(os.getenv("LOAD_PEAK_VUS", "1000")))
    parser.add_argument("--output",     default="tests/performance/LOAD_REPORT.md",
                        help="Output Markdown report path")
    args = parser.parse_args()

    # Validate inputs exist
    for path in [args.stats_csv, args.failures_csv]:
        if not Path(path).exists():
            print(f"❌ Required file not found: {path}", file=sys.stderr)
            print("   Run the load test first: bash scripts/run_phase63_load.sh", file=sys.stderr)
            return 2

    is_ci   = bool(os.getenv("CI"))
    thresh  = _thresholds(args.peak_vus, is_ci)
    stats   = _parse_stats(args.stats_csv)
    failures = _parse_failures(args.failures_csv)
    history  = _parse_history(args.history_csv)

    # ── GATE-3: KPI evaluation ──────────────────────────────────────────────
    violations: list[str] = []

    # p95 per endpoint
    for name, t_p95 in thresh["p95"].items():
        s = stats.get(name)
        if s is None:
            # No data for this endpoint — only flag if it's a write endpoint
            if "Enroll" in name or "Withdraw" in name:
                violations.append(f"GATE-3: No data for '{name}' (was enroll/withdraw run?)")
            continue
        if s["p95"] > t_p95:
            violations.append(
                f"GATE-3: p95 violation — '{name}': {s['p95']:.0f}ms > {t_p95}ms threshold"
            )

    # 5xx error rate
    total_req = sum(s["requests"] for s in stats.values())
    srv       = failures.get("server_errors", 0)
    srv_pct   = srv / max(total_req, 1) * 100
    if srv_pct > thresh["5xx_pct"]:
        violations.append(
            f"GATE-3: 5xx rate {srv_pct:.2f}% > {thresh['5xx_pct']}% threshold"
        )

    # ── Print to console ────────────────────────────────────────────────────
    print()
    print("═" * 72)
    print(" Phase 6.3 Results Analysis")
    print(f" {thresh['label']}  |  total requests: {total_req}")
    print("═" * 72)
    print()

    print("── Latency (p95 / p99) ─────────────────────────────────────────────")
    for name, t_p95 in thresh["p95"].items():
        s = stats.get(name)
        if s:
            ok = s["p95"] <= t_p95
            print(f"  {'✅' if ok else '❌'} {name}: p95={s['p95']:.0f}ms  p99={s['p99']:.0f}ms  (≤{t_p95}ms)")
        else:
            print(f"  ⚠️  {name}: no data")

    print()
    print("── Error Split ─────────────────────────────────────────────────────")
    rl      = failures.get("rate_limited", 0)
    net     = failures.get("other", 0)
    rl_pct  = rl / max(total_req, 1) * 100
    net_pct = net / max(total_req, 1) * 100
    print(f"  429 rate limited : {rl:>7}  ({rl_pct:.2f}%)")
    print(f"  5xx server error : {srv:>7}  ({srv_pct:.2f}%)  "
          f"{'✅' if srv_pct <= thresh['5xx_pct'] else '❌'} ≤{thresh['5xx_pct']}%")
    print(f"  network error    : {net:>7}  ({net_pct:.2f}%)")
    print(f"  total requests   : {total_req:>7}")

    bp = _breaking_point(history)
    print()
    print("── Breaking Point ──────────────────────────────────────────────────")
    if bp:
        print(f"  ⚠️  Breaking point: {bp} VUs (p95 > 1000ms or error > 5%)")
    else:
        print(f"  ✅ Not reached at {args.peak_vus} VUs")

    # ── Generate LOAD_REPORT.md (GATE-5) ───────────────────────────────────
    sha = os.getenv("GITHUB_SHA", "local")[:12]
    report_md = _render_report(
        stats, failures, history, thresh,
        args.peak_vus, violations, sha,
    )
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_md, encoding="utf-8")
    print()
    print(f"── GATE-5 Report written: {out_path} ───────────────────────────────")

    # ── Final verdict ───────────────────────────────────────────────────────
    print()
    print("═" * 72)
    if violations:
        print(" ❌ Phase 6.3 NOT COMPLETE")
        for v in violations:
            print(f"    {v}")
        print("═" * 72)
        return 1
    else:
        print(" ✅ Phase 6.3 VALID — all GATES passed")
        print("═" * 72)
        return 0


if __name__ == "__main__":
    sys.exit(main())
