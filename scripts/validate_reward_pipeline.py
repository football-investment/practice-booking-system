"""
Production monitoring — reward/XP pipeline integrity checks

Usage (from project root):
    python scripts/validate_reward_pipeline.py [--since-days N] [--strict]

Verifies that the seven concurrency guards introduced in the
2026-02-19 sprint are holding in production:

  INV-R01  No (user_id, semester_id) pair has more than one TournamentParticipation
           (uq_user_semester_participation unique constraint must be live)

  INV-R02  No (user_id, semester_id, badge_type) triple has more than one TournamentBadge
           (uq_user_tournament_badge unique index must be live — added migration rw01concurr00)

  INV-R03  XP balance integrity: SUM(xp_transactions) ≈ users.xp_balance (drift ≤ 0)
           (atomic SQL UPDATE pattern — RACE-R07 guard)

  INV-R04  Credit reward integrity: no (user_id, semester_id) pair with >1 TOURNAMENT_REWARD
           credit transaction having different idempotency_keys
           (idempotency_key on CreditTransaction — RACE-R06 guard)

  INV-R05  XP transaction idempotency: no duplicate idempotency_keys in xp_transactions
           (uq_xp_transaction_idempotency unique partial index must be live)

  INV-R06  DB constraints confirmed live: all three rw01concurr00 objects present

Exits 0 if all invariants hold, 1 if any anomaly detected.

Run weekly (CI cron or manual):
    0 9 * * 1 cd /path/to/project && python scripts/validate_reward_pipeline.py >> logs/reward_pipeline_weekly.log 2>&1

Complements:
    scripts/validate_enrollment_pipeline.py  — enrollment pipeline check
    scripts/validate_booking_pipeline.py     — booking pipeline check
"""
import sys
import os
import argparse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

parser = argparse.ArgumentParser(
    description="Reward/XP pipeline integrity monitor (weekly)"
)
parser.add_argument("--since-days", type=int, default=7,
                    help="Look at tournaments completed in the last N days (default: 7)")
parser.add_argument("--strict", action="store_true",
                    help="Exit 1 on warnings as well as errors")
args = parser.parse_args()

errors = []
warnings = []

HARDENING_DATE = datetime(2026, 2, 19, tzinfo=timezone.utc)
since = datetime.now(tz=timezone.utc) - timedelta(days=args.since_days)
window_start = max(since, HARDENING_DATE)

print("=" * 65)
print("REWARD/XP PIPELINE INTEGRITY CHECK — post 2026-02-19 hardening")
print(f"Run at : {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
print(f"Window : {window_start.strftime('%Y-%m-%d')} → now  ({args.since_days}d)")
print("=" * 65)

from app.database import engine
from sqlalchemy import text


# ─────────────────────────────────────────────────────────────────────────────
# INV-R06: DB constraints from migration rw01concurr00 are live
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-R06] Checking DB constraints from migration rw01concurr00…")

with engine.connect() as conn:
    uq_participation = conn.execute(text(
        "SELECT 1 FROM pg_indexes WHERE indexname = 'uq_user_semester_participation'"
    )).fetchone()

    uq_badge = conn.execute(text(
        "SELECT 1 FROM pg_indexes WHERE indexname = 'uq_user_tournament_badge'"
    )).fetchone()

    uq_xp = conn.execute(text(
        "SELECT 1 FROM pg_indexes WHERE indexname = 'uq_xp_transaction_idempotency'"
    )).fetchone()

    xp_idempotency_col = conn.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'xp_transactions' AND column_name = 'idempotency_key'"
    )).fetchone()

for name, row in [
    ("uq_user_semester_participation", uq_participation),
    ("uq_user_tournament_badge (rw01)", uq_badge),
    ("uq_xp_transaction_idempotency (rw01)", uq_xp),
    ("xp_transactions.idempotency_key column (rw01)", xp_idempotency_col),
]:
    if row:
        print(f"  ✅ {name}: PRESENT")
    else:
        errors.append(
            f"CRITICAL: {name} MISSING — run 'alembic upgrade head' (migration rw01concurr00)"
        )
        print(f"  ❌ {name}: MISSING")


# ─────────────────────────────────────────────────────────────────────────────
# INV-R01: No duplicate TournamentParticipation per (user_id, semester_id)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-R01] Checking for duplicate TournamentParticipation rows (RACE-R01/R02 guard)…")

with engine.connect() as conn:
    violations = conn.execute(text("""
        SELECT user_id, semester_id, COUNT(*) AS cnt
        FROM tournament_participations
        GROUP BY user_id, semester_id
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        LIMIT 20
    """)).fetchall()

if not violations:
    print("  ✅ No duplicate TournamentParticipation rows found")
else:
    for row in violations:
        errors.append(
            f"DUPLICATE PARTICIPATION: user_id={row[0]}, semester_id={row[1]}, "
            f"count={row[2]} — uq_user_semester_participation may be missing or bypassed"
        )
    print(f"  ❌ {len(violations)} violation(s) found — double reward distribution detected")


# ─────────────────────────────────────────────────────────────────────────────
# INV-R02: No duplicate badges per (user_id, semester_id, badge_type)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-R02] Checking for duplicate TournamentBadge rows (RACE-R05 guard)…")

with engine.connect() as conn:
    badge_violations = conn.execute(text("""
        SELECT user_id, semester_id, badge_type, COUNT(*) AS cnt
        FROM tournament_badges
        GROUP BY user_id, semester_id, badge_type
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        LIMIT 20
    """)).fetchall()

if not badge_violations:
    print("  ✅ No duplicate badge rows found")
else:
    for row in badge_violations:
        errors.append(
            f"DUPLICATE BADGE: user_id={row[0]}, semester_id={row[1]}, "
            f"badge_type={row[2]}, count={row[3]} — RACE-R05 not closed"
        )
    print(f"  ❌ {len(badge_violations)} violation(s) — badge double-award detected")


# ─────────────────────────────────────────────────────────────────────────────
# INV-R03: XP balance drift check (RACE-R07 guard)
# Users with xp_balance that doesn't match SUM(xp_transactions)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-R03] Checking XP balance drift (RACE-R07 atomic update guard)…")

with engine.connect() as conn:
    # Only check users who have at least one xp_transaction (tx_sum > 0).
    # Pre-hardening seeded balances with zero transactions are expected and benign.
    # R07 guard detects: concurrent updates that cause xp_balance < tx_sum (lost update)
    # or xp_balance significantly > tx_sum when transactions exist (inflated balance).
    drift_rows = conn.execute(text("""
        SELECT u.id, u.email, u.xp_balance,
               COALESCE(SUM(xt.amount), 0) AS tx_sum,
               u.xp_balance - COALESCE(SUM(xt.amount), 0) AS drift
        FROM users u
        JOIN xp_transactions xt ON xt.user_id = u.id
        GROUP BY u.id, u.email, u.xp_balance
        HAVING u.xp_balance != COALESCE(SUM(xt.amount), 0)
        ORDER BY ABS(u.xp_balance - COALESCE(SUM(xt.amount), 0)) DESC
        LIMIT 20
    """)).fetchall()

if not drift_rows:
    print("  ✅ No XP balance drift detected among users with XP transactions")
else:
    for row in drift_rows:
        msg = (
            f"XP DRIFT: user_id={row[0]}, email={row[1]}, "
            f"balance={row[2]}, tx_sum={row[3]}, drift={row[4]}"
        )
        # Negative drift (balance < tx_sum) is always a lost-update error
        # Large positive drift is also suspicious
        if row[4] < 0 or abs(row[4]) > 500:
            errors.append(msg)
        else:
            warnings.append(msg)
    error_count = sum(1 for r in drift_rows if r[4] < 0 or abs(r[4]) > 500)
    warn_count = len(drift_rows) - error_count
    print(f"  {'❌' if error_count else '⚠️'} {len(drift_rows)} user(s) with XP drift "
          f"({error_count} errors, {warn_count} warnings)")


# ─────────────────────────────────────────────────────────────────────────────
# INV-R04: Credit reward idempotency — no duplicate TOURNAMENT_REWARD transactions
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-R04] Checking credit idempotency (RACE-R06 guard — TOURNAMENT_REWARD transactions)…")

with engine.connect() as conn:
    credit_dups = conn.execute(text("""
        SELECT user_id, semester_id, COUNT(*) AS cnt
        FROM credit_transactions
        WHERE transaction_type = 'TOURNAMENT_REWARD'
          AND semester_id IS NOT NULL
        GROUP BY user_id, semester_id
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        LIMIT 20
    """)).fetchall()

if not credit_dups:
    print("  ✅ No duplicate TOURNAMENT_REWARD credit transactions found")
else:
    for row in credit_dups:
        errors.append(
            f"DUPLICATE CREDIT TX: user_id={row[0]}, semester_id={row[1]}, "
            f"count={row[2]} — possible double credit grant (RACE-R06)"
        )
    print(f"  ❌ {len(credit_dups)} violation(s) — duplicate reward credit transactions")


# ─────────────────────────────────────────────────────────────────────────────
# INV-R05: XP idempotency key uniqueness
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-R05] Checking XP transaction idempotency key uniqueness (RACE-R06 guard)…")

with engine.connect() as conn:
    xp_key_dups = conn.execute(text("""
        SELECT idempotency_key, COUNT(*) AS cnt
        FROM xp_transactions
        WHERE idempotency_key IS NOT NULL
        GROUP BY idempotency_key
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        LIMIT 20
    """)).fetchall()

if not xp_key_dups:
    print("  ✅ No duplicate XP transaction idempotency keys found")
else:
    for row in xp_key_dups:
        errors.append(
            f"DUPLICATE XP IDEMPOTENCY KEY: key={row[0]}, count={row[1]} "
            "— uq_xp_transaction_idempotency partial index may be missing"
        )
    print(f"  ❌ {len(xp_key_dups)} violation(s) — XP double-grant detected")


# ─────────────────────────────────────────────────────────────────────────────
# Summary statistics (informational)
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[INFO] Reward statistics (last {args.since_days}d)…")

with engine.connect() as conn:
    stats = conn.execute(text("""
        SELECT
            COUNT(*)                                           AS total_participations,
            COUNT(DISTINCT user_id)                           AS unique_users,
            COUNT(DISTINCT semester_id)                       AS unique_tournaments,
            COUNT(*) FILTER (WHERE placement = 1)             AS first_place_count,
            COUNT(*) FILTER (WHERE placement = 2)             AS second_place_count,
            COUNT(*) FILTER (WHERE placement = 3)             AS third_place_count,
            COUNT(*) FILTER (WHERE placement IS NULL)         AS participant_count
        FROM tournament_participations
        WHERE achieved_at >= :since
    """), {"since": window_start}).fetchone()

    badge_stats = conn.execute(text("""
        SELECT COUNT(*) AS total_badges, COUNT(DISTINCT badge_type) AS distinct_types
        FROM tournament_badges
        WHERE earned_at >= :since
    """), {"since": window_start}).fetchone()

    xp_sum = conn.execute(text("""
        SELECT COALESCE(SUM(amount), 0)
        FROM xp_transactions
        WHERE created_at >= :since
    """), {"since": window_start}).scalar()

    credit_sum = conn.execute(text("""
        SELECT COALESCE(SUM(amount), 0)
        FROM credit_transactions
        WHERE transaction_type = 'TOURNAMENT_REWARD'
          AND created_at >= :since
    """), {"since": window_start}).scalar()

if stats:
    print(f"  Total participations   : {stats[0]}")
    print(f"  Unique users           : {stats[1]}")
    print(f"  Unique tournaments     : {stats[2]}")
    print(f"  Placements 1st/2nd/3rd : {stats[3]}/{stats[4]}/{stats[5]}")
    print(f"  Participants (no rank) : {stats[6]}")
    print(f"  Total badges awarded   : {badge_stats[0]} ({badge_stats[1]} distinct types)")
    print(f"  Total XP granted       : {xp_sum:+d}")
    print(f"  Total reward credits   : {credit_sum:+d}")


# ─────────────────────────────────────────────────────────────────────────────
# Final result
# ─────────────────────────────────────────────────────────────────────────────
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
    print("✅  ALL CHECKS PASSED — reward/XP pipeline integrity confirmed")
    sys.exit(0)
