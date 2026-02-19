"""
Production monitoring — booking pipeline integrity checks

Usage (from project root):
    python scripts/validate_booking_pipeline.py [--since-days N] [--strict]

Verifies that the seven booking concurrency guards introduced in the
2026-02-19 sprint (Phase B+C) are holding in production:

  INV-B01  No session has confirmed_count > capacity (overbooking)
           Guards RACE-B02 (capacity TOCTOU) and RACE-B06 (admin confirm w/o check)

  INV-B02  No (user_id, session_id) pair has >1 non-cancelled booking
           Guards RACE-B01 (duplicate booking TOCTOU)
           DB constraint: uq_active_booking (WHERE status != 'CANCELLED')

  INV-B03  No (session_id, waitlist_position) collision in WAITLISTED bookings
           Guards RACE-B03 (waitlist position collision)
           DB constraint: uq_waitlist_position (WHERE status = 'WAITLISTED')

  INV-B04  No booking has >1 attendance record
           Guards RACE-B07 (duplicate attendance TOCTOU)
           DB constraint: uq_booking_attendance (unique booking_id)

  INV-B05  DB constraints from migration bk01concurr00 confirmed live
           (uq_active_booking, uq_waitlist_position, uq_booking_attendance)

Exits 0 if all invariants hold, 1 if any anomaly is detected.

Run weekly (CI cron or manual):
    0 9 * * 1 cd /path/to/project && python scripts/validate_booking_pipeline.py >> logs/booking_pipeline_weekly.log 2>&1

Complements:
    scripts/validate_enrollment_pipeline.py  — enrollment concurrency checks
    scripts/validate_campus_distribution.py  — campus distribution check
    scripts/validate_system_events_24h.py    — system event pipeline check
"""
import sys
import os
import argparse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

parser = argparse.ArgumentParser(
    description="Booking pipeline integrity monitor (weekly)"
)
parser.add_argument(
    "--since-days", type=int, default=7,
    help="Look at bookings created in the last N days (default: 7)"
)
parser.add_argument(
    "--strict", action="store_true",
    help="Exit 1 on warnings as well as errors"
)
args = parser.parse_args()

errors = []
warnings = []

HARDENING_DATE = datetime(2026, 2, 19, tzinfo=timezone.utc)
since = datetime.now(tz=timezone.utc) - timedelta(days=args.since_days)
window_start = max(since, HARDENING_DATE)

print("=" * 65)
print("BOOKING PIPELINE INTEGRITY CHECK — post 2026-02-19 hardening")
print(f"Run at : {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
print(f"Window : {window_start.strftime('%Y-%m-%d')} → now  ({args.since_days}d)")
print("=" * 65)

from app.database import engine
from sqlalchemy import text


# ─────────────────────────────────────────────────────────────────────────────
# INV-B05: Migration bk01concurr00 applied (all three constraints live)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-B05] Checking DB constraints from migration bk01concurr00…")

with engine.connect() as conn:
    uq_active_booking = conn.execute(text(
        "SELECT 1 FROM pg_indexes WHERE indexname = 'uq_active_booking'"
    )).fetchone()

    uq_waitlist = conn.execute(text(
        "SELECT 1 FROM pg_indexes WHERE indexname = 'uq_waitlist_position'"
    )).fetchone()

    uq_attendance = conn.execute(text(
        "SELECT 1 FROM information_schema.table_constraints "
        "WHERE constraint_name = 'uq_booking_attendance' "
        "  AND table_name = 'attendance'"
    )).fetchone()

if uq_active_booking:
    print("  ✅ uq_active_booking partial unique index (C-01): PRESENT")
else:
    errors.append(
        "CRITICAL: uq_active_booking index MISSING — "
        "run 'alembic upgrade head' (migration bk01concurr00)"
    )
    print("  ❌ uq_active_booking (C-01): MISSING")

if uq_waitlist:
    print("  ✅ uq_waitlist_position partial unique index (C-02): PRESENT")
else:
    errors.append(
        "CRITICAL: uq_waitlist_position index MISSING — "
        "run 'alembic upgrade head' (migration bk01concurr00)"
    )
    print("  ❌ uq_waitlist_position (C-02): MISSING")

if uq_attendance:
    print("  ✅ uq_booking_attendance unique constraint (C-03): PRESENT")
else:
    errors.append(
        "CRITICAL: uq_booking_attendance constraint MISSING — "
        "run 'alembic upgrade head' (migration bk01concurr00)"
    )
    print("  ❌ uq_booking_attendance (C-03): MISSING")


# ─────────────────────────────────────────────────────────────────────────────
# INV-B01: No session overbooked (confirmed_count > capacity)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-B01] Checking for overbooked sessions (RACE-B02 / RACE-B06 guard)…")

with engine.connect() as conn:
    overbooked = conn.execute(text("""
        SELECT
            b.session_id,
            s.capacity,
            COUNT(*) AS confirmed_count
        FROM bookings b
        JOIN sessions s ON s.id = b.session_id
        WHERE b.status = 'CONFIRMED'
        GROUP BY b.session_id, s.capacity
        HAVING COUNT(*) > s.capacity
        ORDER BY confirmed_count DESC
        LIMIT 20
    """)).fetchall()

if not overbooked:
    print("  ✅ No overbooked sessions found")
else:
    for row in overbooked:
        errors.append(
            f"OVERBOOKED SESSION: session_id={row[0]}, capacity={row[1]}, "
            f"confirmed_count={row[2]} (excess: +{row[2] - row[1]})"
        )
    print(f"  ❌ {len(overbooked)} overbooked session(s) — RACE-B02/B06 invariant broken")


# ─────────────────────────────────────────────────────────────────────────────
# INV-B02: No (user_id, session_id) with >1 non-cancelled booking
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-B02] Checking for duplicate active bookings (RACE-B01 guard)…")

with engine.connect() as conn:
    dups = conn.execute(text("""
        SELECT user_id, session_id, COUNT(*) AS cnt
        FROM bookings
        WHERE status != 'CANCELLED'
        GROUP BY user_id, session_id
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        LIMIT 20
    """)).fetchall()

if not dups:
    print("  ✅ No duplicate active bookings found")
else:
    for row in dups:
        errors.append(
            f"DUPLICATE ACTIVE BOOKING: user_id={row[0]}, session_id={row[1]}, "
            f"non-cancelled_count={row[2]}"
        )
    print(
        f"  ❌ {len(dups)} duplicate booking pair(s) — "
        "uq_active_booking may be missing or bypassed"
    )


# ─────────────────────────────────────────────────────────────────────────────
# INV-B03: No waitlist position collision within same session
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-B03] Checking for waitlist position collisions (RACE-B03 guard)…")

with engine.connect() as conn:
    collisions = conn.execute(text("""
        SELECT session_id, waitlist_position, COUNT(*) AS cnt
        FROM bookings
        WHERE status = 'WAITLISTED'
          AND waitlist_position IS NOT NULL
        GROUP BY session_id, waitlist_position
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        LIMIT 20
    """)).fetchall()

    # Also check for unexpected gaps in waitlist positions
    # (positions should be contiguous: 1, 2, 3, ... without gaps)
    gaps = conn.execute(text("""
        SELECT
            session_id,
            MAX(waitlist_position) AS max_pos,
            COUNT(*) AS actual_count,
            MAX(waitlist_position) - COUNT(*) AS gap_count
        FROM bookings
        WHERE status = 'WAITLISTED'
          AND waitlist_position IS NOT NULL
        GROUP BY session_id
        HAVING MAX(waitlist_position) != COUNT(*)
        LIMIT 20
    """)).fetchall()

if not collisions:
    print("  ✅ No waitlist position collisions found")
else:
    for row in collisions:
        errors.append(
            f"WAITLIST POSITION COLLISION: session_id={row[0]}, position={row[1]}, "
            f"count={row[2]} — uq_waitlist_position may be missing"
        )
    print(f"  ❌ {len(collisions)} collision(s) — RACE-B03 invariant broken")

if gaps:
    for row in gaps:
        warnings.append(
            f"WAITLIST POSITION GAP: session_id={row[0]}, max_pos={row[1]}, "
            f"actual_count={row[2]}, gap={row[3]} "
            f"— may indicate a cancelled WAITLISTED booking whose position was not compacted"
        )
    print(f"  ⚠️  {len(gaps)} session(s) with waitlist position gaps")
else:
    print("  ✅ No waitlist position gaps found")


# ─────────────────────────────────────────────────────────────────────────────
# INV-B04: No booking with >1 attendance record
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-B04] Checking for duplicate attendance records (RACE-B07 guard)…")

with engine.connect() as conn:
    dup_attendance = conn.execute(text("""
        SELECT booking_id, COUNT(*) AS cnt
        FROM attendance
        GROUP BY booking_id
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        LIMIT 20
    """)).fetchall()

if not dup_attendance:
    print("  ✅ No duplicate attendance records found")
else:
    for row in dup_attendance:
        errors.append(
            f"DUPLICATE ATTENDANCE: booking_id={row[0]}, attendance_count={row[1]} "
            f"— uq_booking_attendance may be missing"
        )
    print(
        f"  ❌ {len(dup_attendance)} booking(s) with duplicate attendance — "
        "RACE-B07 invariant broken"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Additional: WAITLISTED bookings with NULL waitlist_position (data integrity)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[INV-B03x] Checking WAITLISTED bookings with NULL position (data integrity)…")

with engine.connect() as conn:
    null_pos = conn.execute(text("""
        SELECT id, user_id, session_id
        FROM bookings
        WHERE status = 'WAITLISTED'
          AND waitlist_position IS NULL
        LIMIT 20
    """)).fetchall()

if not null_pos:
    print("  ✅ No WAITLISTED bookings with NULL position")
else:
    for row in null_pos:
        warnings.append(
            f"WAITLISTED WITH NULL POSITION: booking_id={row[0]}, user_id={row[1]}, "
            f"session_id={row[2]} — auto_promote_from_waitlist ordering may be affected"
        )
    print(f"  ⚠️  {len(null_pos)} WAITLISTED booking(s) with NULL position")


# ─────────────────────────────────────────────────────────────────────────────
# Summary statistics (informational)
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[INFO] Booking statistics (last {args.since_days}d)…")

with engine.connect() as conn:
    stats = conn.execute(text("""
        SELECT
            COUNT(*)                                                       AS total_bookings,
            COUNT(*) FILTER (WHERE status = 'CONFIRMED')                   AS confirmed,
            COUNT(*) FILTER (WHERE status = 'WAITLISTED')                  AS waitlisted,
            COUNT(*) FILTER (WHERE status = 'CANCELLED')                   AS cancelled,
            COUNT(*) FILTER (WHERE status = 'PENDING')                     AS pending,
            COUNT(DISTINCT user_id)                                        AS unique_users,
            COUNT(DISTINCT session_id)                                     AS unique_sessions
        FROM bookings
        WHERE created_at >= :since
    """), {"since": window_start}).fetchone()

    attendance_stats = conn.execute(text("""
        SELECT COUNT(*) AS total_attendance_records
        FROM attendance
        WHERE created_at >= :since
    """), {"since": window_start}).fetchone()

if stats:
    print(f"  Total bookings     : {stats[0]}")
    print(f"  Confirmed          : {stats[1]}")
    print(f"  Waitlisted         : {stats[2]}")
    print(f"  Cancelled          : {stats[3]}")
    print(f"  Pending            : {stats[4]}")
    print(f"  Unique users       : {stats[5]}")
    print(f"  Unique sessions    : {stats[6]}")
    if attendance_stats:
        print(f"  Attendance records : {attendance_stats[0]}")


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
    print("✅  ALL CHECKS PASSED — booking pipeline integrity confirmed")
    sys.exit(0)
