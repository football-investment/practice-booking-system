#!/usr/bin/env python3
"""
Stepped Ramp Load Test — Phase 6.3 capacity curve measurement
==============================================================
Runs SoakBurstUser at fixed VU levels (no Phase63LoadShape) to produce a
clean capacity curve for infrastructure sizing decisions.

Protocol:
  Levels : 50 → 100 → 200 → 300 → 500 VUs
  Hold   : 5 minutes per level (steady-state measurement window)
  Cooldown: 15 s between levels (allow pool to drain)
  Workers: 4 uvicorn workers, ENABLE_RATE_LIMITING=false

Output:
  tests/performance/results/stepped_ramp_YYYYMMDD_HHMM/
    level_<N>_stats.csv          — per-endpoint p50/p95/p99/error counts
    level_<N>_failures.csv       — failure details
  tests/performance/LOAD_REPORT_STEPPED_RAMP.md  — consolidated report

Breaking point definition:
  ANY of:  p95 > 1000ms on Browse (threshold 500ms, 2× slack)
           p95 > 2000ms on Enroll or Withdraw (threshold 1000ms, 2× slack)
           error rate > 5% (total [P63] requests)
           Login 5xx > 2% (proxy for DB pool exhaustion)
"""
import csv
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
VU_LEVELS     = [50, 100, 200, 300, 500]
HOLD_SECONDS  = 300   # 5 min per level
COOLDOWN_S    = 15    # drain between levels
PORT          = 8002  # avoids dev (8000) + run_phase63_load.sh (8001)
WORKERS       = 4
SPAWN_RATE    = 50    # max 50 VU/s spawn — prevents thundering-herd on ramp-up
HOST          = f"http://127.0.0.1:{PORT}"
PROJECT_ROOT  = Path(__file__).parent.parent
RESULTS_STAMP = time.strftime("%Y%m%d_%H%M")
RESULTS_DIR   = PROJECT_ROOT / "tests/performance/results" / f"stepped_ramp_{RESULTS_STAMP}"
REPORT_PATH   = PROJECT_ROOT / "tests/performance/LOAD_REPORT_STEPPED_RAMP.md"
SEMESTER_IDS  = os.environ.get("LOAD_SEMESTER_IDS", "9932")
EVENT_IDS     = os.environ.get("LOAD_EVENT_IDS", "1,31,2,3,33")

# Breaking point thresholds
BP_BROWSE_P95_MS   = 1000   # 2× CI threshold (500ms)
BP_ENROLL_P95_MS   = 2000   # 2× CI threshold (1000ms)
BP_WITHDRAW_P95_MS = 2000
BP_ERROR_RATE_PCT  = 5.0
BP_LOGIN_5XX_PCT   = 2.0

# ── Helpers ──────────────────────────────────────────────────────────────────

def die(msg: str) -> None:
    print(f"\n❌ {msg}", file=sys.stderr)
    sys.exit(2)


def wait_for_server(url: str, timeout: float = 20.0) -> None:
    import urllib.request, urllib.error
    deadline = time.monotonic() + timeout
    print(f"   Waiting for server at {url} ", end="", flush=True)
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=2) as r:
                if r.status == 200:
                    print(" ✅")
                    return
        except Exception:
            pass
        print(".", end="", flush=True)
        time.sleep(0.5)
    die(f"Server did not start within {timeout}s")


def fetch_metrics(url: str) -> dict[str, float]:
    """Parse Prometheus text format from /metrics endpoint."""
    import urllib.request
    result: dict[str, float] = {}
    try:
        with urllib.request.urlopen(f"{url}/metrics?format=prometheus", timeout=5) as r:
            for line in r.read().decode().splitlines():
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.rsplit(" ", 1)
                if len(parts) == 2:
                    try:
                        result[parts[0].strip()] = float(parts[1])
                    except ValueError:
                        pass
    except Exception:
        pass
    return result


def parse_stats(csv_path: Path) -> dict[str, dict]:
    """Parse Locust stats CSV into {endpoint_name: {metric: value}} dict."""
    result: dict[str, dict] = {}
    if not csv_path.exists():
        return result
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("Name", "")
            try:
                result[name] = {
                    "requests":  int(row["Request Count"]),
                    "failures":  int(row["Failure Count"]),
                    "rps":       float(row["Requests/s"]),
                    "p50":       float(row["50%"]),
                    "p95":       float(row["95%"]),
                    "p99":       float(row["99%"]),
                    "p_max":     float(row["100%"]),
                }
            except (ValueError, KeyError):
                pass
    return result


def parse_failure_codes(csv_path: Path) -> dict[str, int]:
    """Tally failure occurrences by error message (extracts HTTP code)."""
    counts: dict[str, int] = {}
    if not csv_path.exists():
        return counts
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            err = row.get("Error", "")
            occ = int(row.get("Occurrences", 1) or 1)
            m = re.search(r"(\d{3})", err)
            code = m.group(1) if m else "unknown"
            counts[code] = counts.get(code, 0) + occ
    return counts


def check_breaking_point(vu: int, stats: dict, fail_codes: dict) -> list[str]:
    """Return list of threshold violations (empty = stable)."""
    violations = []
    agg = stats.get("Aggregated", {})
    total_req = agg.get("requests", 0)
    total_fail = agg.get("failures", 0)
    error_pct = 100 * total_fail / total_req if total_req else 0

    if error_pct > BP_ERROR_RATE_PCT:
        violations.append(f"error_rate={error_pct:.1f}% > {BP_ERROR_RATE_PCT}%")

    for ep, threshold, label in [
        ("[P63] Browse event",   BP_BROWSE_P95_MS,   "Browse p95"),
        ("[P63] Enroll",         BP_ENROLL_P95_MS,   "Enroll p95"),
        ("[P63] Withdraw",       BP_WITHDRAW_P95_MS, "Withdraw p95"),
    ]:
        p95 = stats.get(ep, {}).get("p95", 0)
        if p95 > threshold:
            violations.append(f"{label}={p95:.0f}ms > {threshold}ms")

    login_req = stats.get("[P63] Login", {}).get("requests", 0)
    login_fail = stats.get("[P63] Login", {}).get("failures", 0)
    fivex = sum(v for k, v in fail_codes.items() if k.startswith("5"))
    login_5xx_pct = 100 * fivex / login_req if login_req else 0
    if login_5xx_pct > BP_LOGIN_5XX_PCT:
        violations.append(f"Login 5xx={login_5xx_pct:.1f}% > {BP_LOGIN_5XX_PCT}% (DB pool)")

    return violations


# ── Temp locustfile (no Phase63LoadShape → fixed --users/--spawn-rate) ───────

TEMP_LOCUSTFILE_CONTENT = textwrap.dedent("""\
    # Stepped-ramp temp locustfile — measurement infrastructure only.
    # Imports SoakBurstUser WITHOUT Phase63LoadShape so Locust respects
    # --users and --spawn-rate directly for per-level steady-state holds.
    import sys, os
    sys.path.insert(0, {root!r})
    from tests.performance.locustfile import SoakBurstUser  # noqa: F401
    # Phase63LoadShape intentionally NOT imported — fixed VU mode
""")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    os.chdir(PROJECT_ROOT)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Pre-flight
    if not shutil.which("locust"):
        die("locust not found — pip install locust")
    if not shutil.which("uvicorn"):
        die("uvicorn not found")

    # Write temp locustfile
    tmp_lf = tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", prefix="stepped_ramp_",
        dir="/tmp", delete=False
    )
    tmp_lf.write(TEMP_LOCUSTFILE_CONTENT.format(root=str(PROJECT_ROOT)))
    tmp_lf.close()

    # Start uvicorn (4 workers, rate limiting off)
    print(f"\n{'═'*68}")
    print(f" Stepped Ramp Test — {RESULTS_STAMP}")
    print(f" Levels: {VU_LEVELS} VUs  |  Hold: {HOLD_SECONDS}s each")
    print(f" Workers: {WORKERS}  |  Port: {PORT}  |  Semester: {SEMESTER_IDS}")
    print(f"{'═'*68}\n")
    print("── Starting uvicorn ──────────────────────────────────────────────────")

    env = {
        **os.environ,
        "ENABLE_RATE_LIMITING": "false",
        "DB_STATEMENT_TIMEOUT_MS": "8000",
    }
    server_proc = subprocess.Popen(
        [
            "uvicorn", "app.main:app",
            "--host", "127.0.0.1",
            "--port", str(PORT),
            "--workers", str(WORKERS),
            "--log-level", "warning",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    def cleanup():
        server_proc.send_signal(signal.SIGTERM)
        try:
            server_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server_proc.kill()
        os.unlink(tmp_lf.name)

    wait_for_server(HOST)

    # Per-level results accumulator
    level_results: list[dict] = []

    try:
        for vu in VU_LEVELS:
            print(f"\n── Level {vu:4d} VUs ─────────────────────────────────────────────────")
            csv_prefix = str(RESULTS_DIR / f"level_{vu:04d}")

            # DB metrics before
            metrics_before = fetch_metrics(HOST)

            t_start = time.monotonic()
            locust_env = {
                **env,
                "LOAD_SEMESTER_IDS": SEMESTER_IDS,
                "LOAD_EVENT_IDS": EVENT_IDS,
                "LOAD_USERS_COUNT": "100",
                "LOAD_PEAK_VUS": str(vu),
            }
            proc = subprocess.run(
                [
                    "locust",
                    "-f", tmp_lf.name,
                    "SoakBurstUser",
                    "--headless",
                    "--host", HOST,
                    "--users", str(vu),
                    "--spawn-rate", str(min(vu, SPAWN_RATE)),
                    "--run-time", f"{HOLD_SECONDS}s",
                    "--csv", csv_prefix,
                    "--loglevel", "WARNING",
                ],
                env=locust_env,
                capture_output=True,
                text=True,
            )
            elapsed = time.monotonic() - t_start

            # DB metrics after
            metrics_after = fetch_metrics(HOST)
            slow_q_delta = (
                metrics_after.get("slow_queries_total", 0)
                - metrics_before.get("slow_queries_total", 0)
            )
            inv_viol = (
                metrics_after.get("invariant_violations_total", 0)
                - metrics_before.get("invariant_violations_total", 0)
            )
            pool_503 = sum(
                v for k, v in (metrics_after.items())
                if "pool" in k.lower() or "503" in k
            )

            stats     = parse_stats(Path(f"{csv_prefix}_stats.csv"))
            fail_codes = parse_failure_codes(Path(f"{csv_prefix}_failures.csv"))
            violations = check_breaking_point(vu, stats, fail_codes)

            agg = stats.get("Aggregated", {})
            total_req  = agg.get("requests", 0)
            total_fail = agg.get("failures", 0)
            error_pct  = 100 * total_fail / total_req if total_req else 0
            rps        = agg.get("rps", 0)

            print(f"   Runtime: {elapsed:.0f}s  |  Requests: {total_req}  |  RPS: {rps:.1f}")
            print(f"   Failures: {total_fail} ({error_pct:.1f}%)")
            print(f"   slow_queries Δ={slow_q_delta:.0f}  invariant_violations Δ={inv_viol:.0f}")
            for ep in ["[P63] Browse event", "[P63] Enroll", "[P63] Withdraw", "[P63] Login"]:
                s = stats.get(ep, {})
                if s:
                    req_ep = s.get("requests", 0)
                    fail_ep = s.get("failures", 0)
                    fp = 100 * fail_ep / req_ep if req_ep else 0
                    print(f"   {ep:42s}  p95={s.get('p95',0):6.0f}ms  p99={s.get('p99',0):6.0f}ms  err={fp:.1f}%")

            if violations:
                bp_str = "❌ THRESHOLD EXCEEDED"
                print(f"   {bp_str}: {', '.join(violations)}")
            else:
                print(f"   ✅ STABLE at {vu} VUs")

            level_results.append({
                "vu": vu,
                "total_req": total_req,
                "total_fail": total_fail,
                "error_pct": error_pct,
                "rps": rps,
                "stats": stats,
                "fail_codes": fail_codes,
                "violations": violations,
                "slow_q_delta": slow_q_delta,
                "inv_viol": inv_viol,
            })

            if violations:
                print(f"\n   Breaking point reached at {vu} VUs — continuing to confirm.")

            if vu < VU_LEVELS[-1]:
                print(f"   Cooldown {COOLDOWN_S}s …", end="", flush=True)
                time.sleep(COOLDOWN_S)
                print(" done")

    finally:
        cleanup()
        os.unlink(tmp_lf.name) if Path(tmp_lf.name).exists() else None

    # ── Produce report ───────────────────────────────────────────────────────
    _write_report(level_results)
    print(f"\n{'═'*68}")
    print(f" Report: {REPORT_PATH}")
    print(f"{'═'*68}\n")
    return 0


def _write_report(results: list[dict]) -> None:
    # Find breaking point (first level with violations)
    bp_vu = next((r["vu"] for r in results if r["violations"]), None)
    prev_vu = None
    if bp_vu:
        idx = [r["vu"] for r in results].index(bp_vu)
        prev_vu = results[idx - 1]["vu"] if idx > 0 else None

    # Determine bottleneck type
    bottleneck = "Unknown"
    if bp_vu:
        bp_r = next(r for r in results if r["vu"] == bp_vu)
        viols = bp_r["violations"]
        if any("DB pool" in v or "5xx" in v for v in viols):
            bottleneck = "DB connection pool exhaustion (Login 5xx spike)"
        elif any("p95" in v for v in viols):
            bottleneck = "Application latency (query contention or lock wait)"
        elif any("error_rate" in v for v in viols):
            bottleneck = "General error rate (mixed pool + query timeouts)"

    lines = [
        "# Phase 6.3 — Stepped Ramp Capacity Report",
        "",
        f"**Generated:** {time.strftime('%Y-%m-%d %H:%M')} local",
        f"**Protocol:** {len(VU_LEVELS)} levels × {HOLD_SECONDS}s hold, {COOLDOWN_S}s cooldown",
        f"**Workers:** {WORKERS} uvicorn, 1 PostgreSQL 14, rate-limiting OFF",
        f"**Breaking point thresholds:** Browse p95>{BP_BROWSE_P95_MS}ms OR Enroll/Withdraw p95>{BP_ENROLL_P95_MS}ms OR error>{BP_ERROR_RATE_PCT}% OR Login 5xx>{BP_LOGIN_5XX_PCT}%",
        "",
        "---",
        "",
        "## Capacity Curve",
        "",
        "| VUs | Requests | RPS | Error% | Browse p95 | Enroll p95 | Withdraw p95 | Login p95 | slow_q Δ | Status |",
        "|-----|----------|-----|--------|-----------|-----------|-------------|----------|---------|--------|",
    ]

    for r in results:
        s = r["stats"]
        br_p95 = s.get("[P63] Browse event", {}).get("p95", 0)
        en_p95 = s.get("[P63] Enroll", {}).get("p95", 0)
        wd_p95 = s.get("[P63] Withdraw", {}).get("p95", 0)
        lo_p95 = s.get("[P63] Login", {}).get("p95", 0)
        status = "❌ BROKEN" if r["violations"] else "✅ Stable"
        lines.append(
            f"| {r['vu']:3d} | {r['total_req']:8d} | {r['rps']:5.1f} | {r['error_pct']:5.1f}% "
            f"| {br_p95:9.0f}ms | {en_p95:9.0f}ms | {wd_p95:10.0f}ms | {lo_p95:8.0f}ms "
            f"| {r['slow_q_delta']:8.0f} | {status} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Breaking Point",
        "",
    ]

    if bp_vu:
        bp_r = next(r for r in results if r["vu"] == bp_vu)
        lines += [
            f"**Breaking point: {bp_vu} VUs**",
            f"**Last stable level: {prev_vu} VUs**" if prev_vu else "**No stable level found**",
            f"**Bottleneck:** {bottleneck}",
            "",
            "Threshold violations at breaking point:",
        ]
        for v in bp_r["violations"]:
            lines.append(f"- {v}")
    else:
        lines += [
            f"**No breaking point detected** — system stable through {VU_LEVELS[-1]} VUs.",
            "Consider extending the ramp to higher VU counts.",
        ]

    lines += [
        "",
        "---",
        "",
        "## Bottleneck Confirmation",
        "",
    ]

    # Bottleneck analysis per metric trend
    if len(results) >= 2:
        lines.append("### Latency Trend (Browse p95 across levels)")
        lines.append("")
        lines.append("| VUs | Browse p95 | Δ from prev |")
        lines.append("|-----|-----------|------------|")
        prev_p95 = None
        for r in results:
            p95 = r["stats"].get("[P63] Browse event", {}).get("p95", 0)
            delta = f"+{p95 - prev_p95:.0f}ms" if prev_p95 is not None else "—"
            lines.append(f"| {r['vu']:3d} | {p95:9.0f}ms | {delta} |")
            prev_p95 = p95
        lines.append("")

    # DB pool signal
    lines += [
        "### DB Pool Signal (Login 5xx rate)",
        "",
        "| VUs | Login reqs | Login fails | 5xx codes | 5xx% |",
        "|-----|-----------|------------|-----------|------|",
    ]
    for r in results:
        ls = r["stats"].get("[P63] Login", {})
        lr = ls.get("requests", 0)
        lf = ls.get("failures", 0)
        fivex = sum(v for k, v in r["fail_codes"].items() if k.startswith("5"))
        fpct = 100 * fivex / lr if lr else 0
        lines.append(f"| {r['vu']:3d} | {lr:9d} | {lf:10d} | {fivex:9d} | {fpct:3.1f}% |")

    lines += [
        "",
        "---",
        "",
        "## Infrastructure Decision",
        "",
    ]

    # Infra recommendations
    if bp_vu and bp_vu <= 200:
        pool_rec = "pool_size=50, max_overflow=100 — current default (~5–20) exhausted below 200 VUs"
        pgbouncer = "YES — mandatory before production; transaction pooling mode"
        priority = "CRITICAL"
    elif bp_vu and bp_vu <= 300:
        pool_rec = "pool_size=30, max_overflow=60 — moderate increase sufficient for 200–300 VU range"
        pgbouncer = "RECOMMENDED — add before scaling beyond 300 VUs"
        priority = "HIGH"
    elif bp_vu and bp_vu <= 500:
        pool_rec = "pool_size=50, max_overflow=100 — increase to target 500+ VU capacity"
        pgbouncer = "RECOMMENDED — needed to exceed current PostgreSQL max_connections"
        priority = "MEDIUM"
    else:
        pool_rec = "No change required at current scale"
        pgbouncer = "NOT REQUIRED — system stable through tested range"
        priority = "LOW"

    lines += [
        f"| Decision | Recommendation | Priority |",
        f"|----------|---------------|----------|",
        f"| DB pool_size / max_overflow | {pool_rec} | {priority} |",
        f"| PgBouncer | {pgbouncer} | {priority} |",
        f"| Breaking point to report | {bp_vu} VUs (last stable: {prev_vu} VUs) | — |" if bp_vu else "| Breaking point | Not reached — extend test | — |",
        "",
        "### Next Steps",
        "",
        f"1. **Increase pool_size**: `create_engine(..., pool_size=50, max_overflow=100)` → re-run stepped ramp to validate shift in breaking point",
        f"2. **PgBouncer**: add transaction-mode pooler → allows 10× more app connections with same PG max_connections",
        f"3. **Index audit**: run `EXPLAIN ANALYZE` on Browse + Enroll under load — high p95 may indicate missing index",
        f"4. **Re-measure**: stepped ramp after each infra change to track capacity curve improvement",
    ]

    REPORT_PATH.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
