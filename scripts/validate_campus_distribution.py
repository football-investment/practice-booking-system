"""
Production monitoring — campus_id distribution in tournament sessions

Usage (from project root):
    python scripts/validate_campus_distribution.py [--since-days N]

Checks that sessions generated after the 2026-02-18 campus infrastructure
refactor have campus_id populated, and reports the per-campus distribution.

Exits 0 if all checks pass, 1 if anomalies are detected.

Freeze period: 2026-02-18 → end of sprint (campus logic must NOT be modified).
"""
import sys
import os
import argparse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

parser = argparse.ArgumentParser()
parser.add_argument("--since-days", type=int, default=7,
                    help="Look at sessions created in the last N days (default: 7)")
args = parser.parse_args()

errors = []
warnings = []

REFACTOR_DATE = datetime(2026, 2, 18, tzinfo=timezone.utc)
since = datetime.now(tz=timezone.utc) - timedelta(days=args.since_days)
window_start = max(since, REFACTOR_DATE)

print("=" * 60)
print("CAMPUS DISTRIBUTION HEALTH CHECK — post 2026-02-18 refactor")
print(f"Run at : {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
print(f"Window : {window_start.strftime('%Y-%m-%d')} → now")
print("=" * 60)

from app.database import engine
from sqlalchemy import text

# ── 1. Sessions without campus_id (post-refactor) ─────────────
print("\n[1] Sessions missing campus_id (generated after 2026-02-18)")
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT COUNT(*) as cnt
        FROM tournament_sessions
        WHERE campus_id IS NULL
          AND created_at >= :since
    """), {"since": window_start})
    null_count = result.scalar()

if null_count == 0:
    print(f"    ✅  0 sessions without campus_id — OK")
elif null_count <= 5:
    warnings.append(f"[W1] {null_count} sessions missing campus_id (may be legacy single-campus tournaments)")
    print(f"    ⚠️  {null_count} sessions without campus_id (see W1)")
else:
    errors.append(f"[E1] {null_count} sessions missing campus_id after refactor date — generator not passing campus_ids?")
    print(f"    ❌  {null_count} sessions without campus_id (see E1)")

# ── 2. Per-campus session distribution ────────────────────────
print("\n[2] Per-campus session distribution")
with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT
            ts.campus_id,
            c.name AS campus_name,
            COUNT(*) AS session_count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct
        FROM tournament_sessions ts
        LEFT JOIN campuses c ON c.id = ts.campus_id
        WHERE ts.campus_id IS NOT NULL
          AND ts.created_at >= :since
        GROUP BY ts.campus_id, c.name
        ORDER BY session_count DESC
    """), {"since": window_start}).fetchall()

if not rows:
    warnings.append("[W2] No sessions with campus_id found in window — is the window too narrow?")
    print("    ⚠️  No sessions with campus_id in window")
else:
    total = sum(r.session_count for r in rows)
    print(f"    {'campus_id':<12} {'name':<30} {'sessions':>8}  {'%':>5}")
    print(f"    {'-'*12} {'-'*30} {'-'*8}  {'-'*5}")
    for r in rows:
        name = (r.campus_name or "—")[:30]
        print(f"    {str(r.campus_id):<12} {name:<30} {r.session_count:>8}  {r.pct:>4}%")
    print(f"    {'':12} {'TOTAL':<30} {total:>8}")

    # Skew check: warn if any single campus > 60% of sessions
    for r in rows:
        if r.pct > 60.0 and len(rows) > 1:
            warnings.append(
                f"[W3] Campus {r.campus_id} ({r.campus_name}) holds {r.pct}% of sessions "
                f"— round-robin may be skewed or only one campus is in use"
            )

# ── 3. OPS scenario requests (campus_ids validation) ──────────
print("\n[3] System events — campus-related errors (last window)")
try:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM system_events
            WHERE event_type = 'OPS_SCENARIO_ERROR'
              AND detail ILIKE '%campus%'
              AND created_at >= :since
        """), {"since": window_start})
        campus_errors = result.scalar()
    if campus_errors == 0:
        print(f"    ✅  0 campus-related OPS errors in system_events — OK")
    else:
        warnings.append(f"[W4] {campus_errors} campus-related OPS errors in system_events — check operator input")
        print(f"    ⚠️  {campus_errors} campus-related OPS errors (see W4)")
except Exception:
    print("    —  system_events table not available or OPS_SCENARIO_ERROR type not used — skip")

# ── 4. Freeze guard ───────────────────────────────────────────
print("\n[4] Campus logic freeze status")
print("    🔒  FROZEN until end of sprint (2026-02-18 refactor)")
print("    Do NOT modify: pick_campus(), ENROLLMENT_OPEN gate, OpsScenarioRequest.campus_ids")
print("    Next review: start of next sprint")

# ── Summary ───────────────────────────────────────────────────
print("\n" + "=" * 60)
if errors:
    print("RESULT: ❌ FAILED")
    for e in errors:
        print(f"  {e}")
elif warnings:
    print("RESULT: ⚠️  PASS WITH WARNINGS")
    for w in warnings:
        print(f"  {w}")
else:
    print("RESULT: ✅ ALL CHECKS PASSED")
print("=" * 60)

sys.exit(1 if errors else 0)
