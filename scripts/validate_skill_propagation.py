"""
Production monitoring — tournament skill propagation health check

## Changelog (append a line when you modify this script)
# 2026-03-12  Initial version — INV-SP-01..04 (2026-03-12 sprint)
#             Author: backend-leads  Ref: docs/release_notes/2026-03-12_skill-propagation.md

Usage (from project root):
    python scripts/validate_skill_propagation.py [--since-days N] [--strict]

Verifies that the V3 EMA skill propagation pipeline introduced on 2026-03-12
is operating within expected thresholds.  Run after every batch of 3–5
tournaments, or schedule weekly (Monday 07:00 UTC).

  INV-SP-01  Every rewarded LFA Football Player has at least one
             FootballSkillAssessment row written in the window
             (skills_written=0 means Phase 3 ran but wrote nothing)

  INV-SP-02  Clamped-at-boundary rate ≤ 20% of all written assessments
             (high rate → skill weights may be misconfigured)

  INV-SP-03  No skill delta exceeds |20| in absolute value for a
             standard-weight (weight=1.0) tournament skill mapping
             (large deltas → check TournamentSkillMapping.weight)

  INV-SP-04  Average delta per placement is within ±30% of the expected
             EMA baseline (placement 1/1 → ~10.0; 4/4 → ~-6.0)
             (drift → learning-rate or formula regression)

Exits 0 if all invariants hold, 1 if any error is detected.
Warnings (INV-SP-02 above 10%, INV-SP-04 drift > 20%) do not cause
exit 1 unless --strict is passed.

Run weekly:
    0 7 * * 1 cd /path/to/project && python scripts/validate_skill_propagation.py >> logs/skill_propagation_weekly.log 2>&1

Complements:
    docs/operations/skill_propagation_monitoring.md — full ops guide
    scripts/validate_enrollment_pipeline.py         — enrollment guard
"""
import sys
import os
import argparse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

parser = argparse.ArgumentParser(
    description="Skill propagation pipeline health monitor (weekly)"
)
parser.add_argument("--since-days", type=int, default=7,
                    help="Look at data created in the last N days (default: 7)")
parser.add_argument("--strict", action="store_true",
                    help="Exit 1 on warnings as well as errors")
args = parser.parse_args()

errors = []
warnings = []

PROPAGATION_LAUNCH = datetime(2026, 3, 12, tzinfo=timezone.utc)
since = datetime.now(tz=timezone.utc) - timedelta(days=args.since_days)
window_start = max(since, PROPAGATION_LAUNCH)

print("=" * 65)
print("SKILL PROPAGATION PIPELINE HEALTH CHECK — post 2026-03-12")
print(f"Run at : {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
print(f"Window : {window_start.strftime('%Y-%m-%d')} → now  ({args.since_days}d)")
print("=" * 65)

from app.database import engine
from sqlalchemy import text


# ─────────────────────────────────────────────────────────────────────────────
# INV-SP-01: Every rewarded LFA player has at least one assessment
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-SP-01] Checking for rewarded players with no assessments written…")

with engine.connect() as conn:
    no_assessment_players = conn.execute(text("""
        SELECT tp.user_id, tp.semester_id, tp.placement,
               tp.skill_rating_delta
        FROM tournament_participations tp
        JOIN user_licenses ul
          ON ul.user_id = tp.user_id
         AND ul.specialization_type = 'LFA_FOOTBALL_PLAYER'
         AND ul.is_active = TRUE
        WHERE tp.skill_rating_delta IS NOT NULL
          AND tp.created_at >= :since
          AND NOT EXISTS (
              SELECT 1
              FROM football_skill_assessments fsa
              WHERE fsa.user_license_id = ul.id
                AND fsa.archived_reason LIKE 'tournament_progression_delta%%'
                AND fsa.archived_at >= tp.created_at - INTERVAL '1 minute'
                AND fsa.archived_at <= tp.created_at + INTERVAL '5 minutes'
          )
        ORDER BY tp.created_at DESC
        LIMIT 20
    """), {"since": window_start}).fetchall()

if not no_assessment_players:
    print("  ✅ All rewarded LFA players have matching assessment rows")
else:
    for row in no_assessment_players:
        errors.append(
            f"NO ASSESSMENT WRITTEN: user_id={row[0]}, semester_id={row[1]}, "
            f"placement={row[2]} — check Phase 3 logs for this participation"
        )
    print(f"  ❌ {len(no_assessment_players)} participation(s) with no matching assessment")


# ─────────────────────────────────────────────────────────────────────────────
# INV-SP-02: Clamped rate ≤ 20% of all written assessments
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-SP-02] Checking clamped-at-boundary rate…")

with engine.connect() as conn:
    row = conn.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE archived_reason LIKE 'tournament_progression_delta%%')
                AS total_written,
            COUNT(*) FILTER (
                WHERE archived_reason LIKE 'tournament_progression_delta%%'
                  AND percentage IN (40.0, 99.0)
            ) AS clamped_count
        FROM football_skill_assessments
        WHERE status = 'ARCHIVED'
          AND archived_at >= :since
    """), {"since": window_start}).fetchone()

total_written = row[0] or 0
clamped_count = row[1] or 0
clamped_rate = (clamped_count / total_written) if total_written > 0 else 0.0

print(f"  Total assessments written : {total_written}")
print(f"  Clamped at 40 or 99       : {clamped_count}  ({clamped_rate:.1%})")

if clamped_rate > 0.20:
    warnings.append(
        f"CLAMPED RATE HIGH: {clamped_rate:.1%} of assessments hit the 40/99 boundary "
        f"({clamped_count}/{total_written}) — review TournamentSkillMapping.weight values; "
        f"weights > 1.5 amplify steps significantly"
    )
    print(f"  ⚠️  Clamped rate {clamped_rate:.1%} exceeds 20% threshold")
elif clamped_rate > 0.10:
    warnings.append(
        f"CLAMPED RATE ELEVATED: {clamped_rate:.1%} — approaching threshold; monitor next cycle"
    )
    print(f"  ⚠️  Clamped rate {clamped_rate:.1%} is elevated (threshold: 20%)")
else:
    print(f"  ✅ Clamped rate {clamped_rate:.1%} is within normal range")


# ─────────────────────────────────────────────────────────────────────────────
# INV-SP-03: No delta > |20| for standard-weight skills
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-SP-03] Checking for anomalously large skill deltas (|delta| > 20)…")

with engine.connect() as conn:
    large_deltas = conn.execute(text("""
        SELECT fsa.user_license_id, fsa.skill_name, fsa.percentage,
               fsa.archived_reason, fsa.archived_at
        FROM football_skill_assessments fsa
        WHERE fsa.status = 'ARCHIVED'
          AND fsa.archived_reason LIKE 'tournament_progression_delta%%'
          AND fsa.archived_at >= :since
          AND ABS(
              CAST(
                  regexp_replace(fsa.archived_reason, '[^0-9.\\-+]', '', 'g')
                  AS numeric
              )
          ) > 20
        ORDER BY fsa.archived_at DESC
        LIMIT 20
    """), {"since": window_start}).fetchall()

if not large_deltas:
    print("  ✅ No deltas exceeding |20| found")
else:
    for row in large_deltas:
        errors.append(
            f"LARGE DELTA: license_id={row[0]}, skill={row[1]}, "
            f"reason='{row[3]}' at {row[4]} — "
            f"check TournamentSkillMapping.weight for this semester"
        )
    print(f"  ❌ {len(large_deltas)} assessment(s) with |delta| > 20 — "
          f"verify TournamentSkillMapping.weight values")


# ─────────────────────────────────────────────────────────────────────────────
# INV-SP-04: Average delta per placement within ±30% of EMA baseline
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-SP-04] Checking average delta drift by placement…")

# Expected midpoint deltas for a solo tournament at weight=1.0
# (generous ±30% tolerance to allow for opponent/performance modifiers)
EXPECTED_DELTAS = {
    1: 10.0,
    2:  4.5,
    3: -0.5,
    4: -6.5,
}
TOLERANCE = 0.30  # ±30% of expected magnitude

with engine.connect() as conn:
    placement_stats = conn.execute(text("""
        SELECT
            tp.placement,
            COUNT(*)                                   AS players,
            ROUND(
                AVG(
                    CAST(
                        regexp_replace(fsa.archived_reason, '[^0-9.\\-+]', '', 'g')
                        AS numeric
                    )
                ), 2
            )                                          AS avg_delta
        FROM football_skill_assessments fsa
        JOIN user_licenses ul ON fsa.user_license_id = ul.id
        JOIN tournament_participations tp
          ON tp.user_id = ul.user_id
         AND fsa.archived_at >= tp.created_at - INTERVAL '1 minute'
         AND fsa.archived_at <= tp.created_at + INTERVAL '5 minutes'
        WHERE fsa.status = 'ARCHIVED'
          AND fsa.archived_reason LIKE 'tournament_progression_delta%%'
          AND fsa.archived_at >= :since
          AND tp.placement BETWEEN 1 AND 4
        GROUP BY tp.placement
        HAVING COUNT(*) >= 5
        ORDER BY tp.placement
    """), {"since": window_start}).fetchall()

if not placement_stats:
    print("  ℹ️  Not enough data yet (need ≥ 5 players per placement in window)")
else:
    drift_found = False
    for row in placement_stats:
        placement, count, avg_delta = row
        avg_delta = float(avg_delta) if avg_delta is not None else None
        if avg_delta is None:
            continue

        expected = EXPECTED_DELTAS.get(placement)
        if expected is None:
            continue

        drift = abs(avg_delta - expected) / max(abs(expected), 1.0)
        status = "✅" if drift <= TOLERANCE else "⚠️ "
        print(f"  {status} Placement {placement}: avg_delta={avg_delta:+.2f} "
              f"(expected ~{expected:+.1f}, drift={drift:.0%}, n={count})")

        if drift > TOLERANCE:
            drift_found = True
            warnings.append(
                f"DELTA DRIFT: placement={placement}, avg={avg_delta:+.2f}, "
                f"expected={expected:+.1f}, drift={drift:.0%} — "
                f"review LEARNING_RATE in skill_progression_service.py"
            )

    if not drift_found:
        print("  ✅ All placement averages within ±30% of expected baseline")


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)

if warnings:
    print("WARNINGS:")
    for w in warnings:
        print(f"  ⚠️  {w}")

if errors:
    print("ERRORS:")
    for e in errors:
        print(f"  ❌ {e}")

if not errors and not warnings:
    print("✅ ALL CHECKS PASSED — skill propagation pipeline healthy")
elif not errors:
    print(f"⚠️  {len(warnings)} warning(s) — review recommended; no blocking errors")
else:
    print(f"❌ {len(errors)} error(s) detected — intervention required")
    print("   See: docs/operations/skill_propagation_monitoring.md")

print("=" * 65)

if errors:
    sys.exit(1)
if args.strict and warnings:
    sys.exit(1)
sys.exit(0)
