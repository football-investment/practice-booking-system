"""
Production monitoring — enrollment pipeline integrity checks

Usage (from project root):
    python scripts/validate_enrollment_pipeline.py [--since-days N]

Verifies that the four enrollment concurrency guards introduced in the
2026-02-18 sprint are holding in production:

  INV-01  No (user_id, semester_id) pair has more than one active enrollment
          (uq_active_enrollment partial unique index must be present and live)

  INV-02  No user has a negative credit_balance
          (chk_credit_balance_non_negative CHECK constraint must be live)

  INV-03  No enrollment is both WITHDRAWN and is_active=TRUE
          (unenroll endpoint invariant — FOR UPDATE + is_active=False atomicity)

  INV-04  Every credit deduction has a matching credit_transaction row
          (enrollment pipeline audit trail completeness)

  INV-05  DB constraints confirmed live (migration eb01concurr00 applied)

Exits 0 if all invariants hold, 1 if any anomaly is detected.

Run weekly (CI cron or manual):
    0 8 * * 1 cd /path/to/project && python scripts/validate_enrollment_pipeline.py >> logs/enrollment_pipeline_weekly.log 2>&1

Complements:
    scripts/validate_campus_distribution.py  — campus distribution check
    scripts/validate_system_events_24h.py    — system event pipeline check
"""
import sys
import os
import argparse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

parser = argparse.ArgumentParser(
    description="Enrollment pipeline integrity monitor (weekly)"
)
parser.add_argument("--since-days", type=int, default=7,
                    help="Look at enrollments created in the last N days (default: 7)")
parser.add_argument("--strict", action="store_true",
                    help="Exit 1 on warnings as well as errors")
args = parser.parse_args()

errors = []
warnings = []

HARDENING_DATE = datetime(2026, 2, 18, tzinfo=timezone.utc)
since = datetime.now(tz=timezone.utc) - timedelta(days=args.since_days)
window_start = max(since, HARDENING_DATE)

print("=" * 65)
print("ENROLLMENT PIPELINE INTEGRITY CHECK — post 2026-02-18 hardening")
print(f"Run at : {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
print(f"Window : {window_start.strftime('%Y-%m-%d')} → now  ({args.since_days}d)")
print("=" * 65)

from app.database import engine
from sqlalchemy import text


# ─────────────────────────────────────────────────────────────────────────────
# INV-05: Migration eb01concurr00 applied (constraints exist)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-05] Checking DB constraints from migration eb01concurr00…")

with engine.connect() as conn:
    b01 = conn.execute(text(
        "SELECT 1 FROM pg_indexes WHERE indexname = 'uq_active_enrollment'"
    )).fetchone()

    b04 = conn.execute(text(
        "SELECT 1 FROM information_schema.table_constraints "
        "WHERE constraint_name = 'chk_credit_balance_non_negative'"
    )).fetchone()

if b01:
    print("  ✅ uq_active_enrollment partial unique index: PRESENT")
else:
    errors.append(
        "CRITICAL: uq_active_enrollment index MISSING — "
        "run 'alembic upgrade head' (migration eb01concurr00)"
    )
    print("  ❌ uq_active_enrollment: MISSING")

if b04:
    print("  ✅ chk_credit_balance_non_negative CHECK constraint: PRESENT")
else:
    errors.append(
        "CRITICAL: chk_credit_balance_non_negative constraint MISSING — "
        "run 'alembic upgrade head' (migration eb01concurr00)"
    )
    print("  ❌ chk_credit_balance_non_negative: MISSING")


# ─────────────────────────────────────────────────────────────────────────────
# INV-01: No (user_id, semester_id) with two active enrollments
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-01] Checking for duplicate active enrollments (RACE-02 guard)…")

with engine.connect() as conn:
    violations = conn.execute(text("""
        SELECT user_id, semester_id, COUNT(*) AS cnt
        FROM semester_enrollments
        WHERE is_active = TRUE
        GROUP BY user_id, semester_id
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        LIMIT 20
    """)).fetchall()

if not violations:
    print("  ✅ No duplicate active enrollments found")
else:
    for row in violations:
        errors.append(
            f"DUPLICATE ACTIVE ENROLLMENT: user_id={row[0]}, semester_id={row[1]}, "
            f"active_count={row[2]}"
        )
    print(f"  ❌ {len(violations)} violation(s) found — uq_active_enrollment may be missing")


# ─────────────────────────────────────────────────────────────────────────────
# INV-02: No negative credit balances
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-02] Checking for negative credit balances (RACE-03 guard)…")

with engine.connect() as conn:
    negatives = conn.execute(text(
        "SELECT id, email, credit_balance FROM users WHERE credit_balance < 0 LIMIT 20"
    )).fetchall()

if not negatives:
    print("  ✅ No negative credit balances found")
else:
    for row in negatives:
        errors.append(
            f"NEGATIVE CREDIT BALANCE: user_id={row[0]}, email={row[1]}, "
            f"balance={row[2]}"
        )
    print(f"  ❌ {len(negatives)} user(s) with negative balance")


# ─────────────────────────────────────────────────────────────────────────────
# INV-03: No WITHDRAWN enrollment with is_active=TRUE
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-03] Checking unenroll invariant: WITHDRAWN → is_active=FALSE (RACE-04 guard)…")

with engine.connect() as conn:
    zombies = conn.execute(text("""
        SELECT se.id, se.user_id, se.semester_id
        FROM semester_enrollments se
        WHERE se.request_status = 'WITHDRAWN'
          AND se.is_active = TRUE
        LIMIT 20
    """)).fetchall()

if not zombies:
    print("  ✅ No zombie WITHDRAWN+active enrollments found")
else:
    for row in zombies:
        errors.append(
            f"ZOMBIE ENROLLMENT: id={row[0]}, user_id={row[1]}, semester_id={row[2]} "
            f"— WITHDRAWN but is_active=TRUE"
        )
    print(f"  ❌ {len(zombies)} zombie enrollment(s) — unenroll invariant broken")


# ─────────────────────────────────────────────────────────────────────────────
# INV-04: Every recent enrollment has a matching credit_transaction
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[INV-04] Checking audit trail: TOURNAMENT_ENROLLMENT transactions "
      f"(window: {window_start.strftime('%Y-%m-%d')} → now)…")

with engine.connect() as conn:
    orphans = conn.execute(text("""
        SELECT se.id, se.user_id, se.semester_id, se.enrolled_at
        FROM semester_enrollments se
        WHERE se.request_status = 'APPROVED'
          AND se.is_active = TRUE
          AND se.enrolled_at >= :since
          AND NOT EXISTS (
            SELECT 1 FROM credit_transactions ct
            WHERE ct.enrollment_id = se.id
              AND ct.transaction_type = 'TOURNAMENT_ENROLLMENT'
          )
        ORDER BY se.enrolled_at DESC
        LIMIT 20
    """), {"since": window_start}).fetchall()

if not orphans:
    print(f"  ✅ All recent active enrollments have credit_transaction audit rows")
else:
    for row in orphans:
        warnings.append(
            f"MISSING CREDIT_TRANSACTION: enrollment_id={row[0]}, user_id={row[1]}, "
            f"semester_id={row[2]}, enrolled_at={row[3]}"
        )
    print(f"  ⚠️  {len(orphans)} enrollment(s) missing credit_transaction audit row")


# ─────────────────────────────────────────────────────────────────────────────
# Summary statistics (informational)
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[INFO] Enrollment statistics (last {args.since_days}d)…")

with engine.connect() as conn:
    stats = conn.execute(text("""
        SELECT
            COUNT(*)                                                    AS total_enrollments,
            COUNT(*) FILTER (WHERE is_active = TRUE
                               AND request_status = 'APPROVED')        AS active_approved,
            COUNT(*) FILTER (WHERE request_status = 'WITHDRAWN')       AS withdrawn,
            COUNT(DISTINCT user_id)                                     AS unique_users,
            COUNT(DISTINCT semester_id)                                 AS unique_tournaments
        FROM semester_enrollments
        WHERE enrolled_at >= :since
    """), {"since": window_start}).fetchone()

    refund_sum = conn.execute(text("""
        SELECT COALESCE(SUM(amount), 0)
        FROM credit_transactions
        WHERE transaction_type = 'TOURNAMENT_UNENROLL_REFUND'
          AND created_at >= :since
    """), {"since": window_start}).scalar()

    deduct_sum = conn.execute(text("""
        SELECT COALESCE(SUM(amount), 0)
        FROM credit_transactions
        WHERE transaction_type = 'TOURNAMENT_ENROLLMENT'
          AND created_at >= :since
    """), {"since": window_start}).scalar()

if stats:
    print(f"  Total enrollments      : {stats[0]}")
    print(f"  Active+approved        : {stats[1]}")
    print(f"  Withdrawn              : {stats[2]}")
    print(f"  Unique users           : {stats[3]}")
    print(f"  Unique tournaments     : {stats[4]}")
    print(f"  Net credit flow        : {deduct_sum or 0:+d} (enroll) / {refund_sum or 0:+d} (refund)")


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
    print("✅  ALL CHECKS PASSED — enrollment pipeline integrity confirmed")
    sys.exit(0)
