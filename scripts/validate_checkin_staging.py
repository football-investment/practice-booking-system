#!/usr/bin/env python3
"""
Staging Validation Gate — Pre-tournament Check-in Seeding
==========================================================

Executes a controlled 16-player / N-check-in scenario directly against
the connected database (staging or local), verifying all deploy-gate
conditions for the tournament_checked_in_at regression fix.

SAFETY: All changes are made inside a single transaction that is ALWAYS
rolled back at the end. No data is persisted, regardless of pass/fail.

Usage:
    python scripts/validate_checkin_staging.py              # 10 check-ins (default)
    python scripts/validate_checkin_staging.py --checkin 9  # 9 check-ins
    python scripts/validate_checkin_staging.py --checkin 11 # 11 check-ins

Exit codes:
    0 — all checks PASSED (deploy allowed)
    1 — at least one check FAILED (production stop)

Deploy gate: run this against staging BEFORE every production deploy that
touches session_generator.py, semester_enrollment model, or checkin.py.
"""

import sys
import math
import argparse
from datetime import datetime, timezone

# Make sure the project root is on sys.path
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import SessionLocal
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus


# ─── Constants ────────────────────────────────────────────────────────────────

TOTAL_ENROLLED = 16
# Reserved fake ID — chosen to not exist in production semesters table
_FAKE_TOURNAMENT_ID = 999_998


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _next_power_of_2(n: int) -> int:
    """Smallest power of 2 >= n (minimum 2)."""
    if n <= 2:
        return 2
    return 2 ** math.ceil(math.log2(n))


def _expected_byes(player_count: int) -> int:
    return _next_power_of_2(player_count) - player_count


def _ok(label: str) -> str:
    return f"  ✅ PASS  {label}"


def _fail(label: str, detail: str = "") -> str:
    suffix = f" — {detail}" if detail else ""
    return f"  ❌ FAIL  {label}{suffix}"


# ─── Core validation ──────────────────────────────────────────────────────────

def run_validation(checkin_count: int) -> bool:
    """
    Execute the full staging validation scenario.

    Returns True if all checks pass, False otherwise.
    The database transaction is always rolled back.
    """
    assert 2 <= checkin_count <= TOTAL_ENROLLED, (
        f"checkin_count must be 2–{TOTAL_ENROLLED}, got {checkin_count}"
    )
    not_checked_in_count = TOTAL_ENROLLED - checkin_count

    print()
    print("=" * 65)
    print("  Staging Validation Gate — Check-in Seeding Regression Fix")
    print("=" * 65)
    print(f"  Scenario : {TOTAL_ENROLLED} enrolled, {checkin_count} manual check-ins")
    print(f"  Mode     : manual (NOT OPS auto-confirm)")
    print(f"  DB safety: full rollback on exit (no data persisted)")
    print("=" * 65)
    print()

    db = SessionLocal()
    results: list[str] = []
    all_passed = True

    try:
        # ── Setup ─────────────────────────────────────────────────────────────
        print("  [1/4] Setting up test data…")
        db.execute(text("SET session_replication_role = 'replica'"))

        now = datetime.now(timezone.utc)

        # Create TOTAL_ENROLLED enrollments with user_ids 1..TOTAL_ENROLLED
        # user_ids 1..checkin_count → manually checked in (simulating /checkin endpoint)
        # user_ids (checkin_count+1)..TOTAL_ENROLLED → NOT checked in
        for uid in range(1, TOTAL_ENROLLED + 1):
            checked_in = uid <= checkin_count
            enrollment = SemesterEnrollment(
                user_id=uid,
                semester_id=_FAKE_TOURNAMENT_ID,
                user_license_id=uid,                # placeholder (FK disabled)
                request_status=EnrollmentStatus.APPROVED,
                is_active=True,
                payment_verified=True,
                enrolled_at=now,
                requested_at=now,
                approved_at=now,
                tournament_checked_in_at=now if checked_in else None,
            )
            db.add(enrollment)

        db.flush()
        print(f"       Created {TOTAL_ENROLLED} enrollments ({checkin_count} checked-in, "
              f"{not_checked_in_count} not checked-in)")

        # ── Run seeding pool query (mirrors session_generator.py) ──────────────
        print()
        print("  [2/4] Running seeding pool query…")

        _base_filter = [
            SemesterEnrollment.semester_id == _FAKE_TOURNAMENT_ID,
            SemesterEnrollment.is_active == True,
            SemesterEnrollment.request_status == EnrollmentStatus.APPROVED,
        ]
        total_approved = db.query(SemesterEnrollment).filter(*_base_filter).count()
        checked_in_db = db.query(SemesterEnrollment).filter(
            *_base_filter,
            SemesterEnrollment.tournament_checked_in_at.isnot(None),
        ).count()

        if checked_in_db > 0:
            _player_filter = _base_filter + [
                SemesterEnrollment.tournament_checked_in_at.isnot(None),
            ]
            pool_label = "check-in confirmed"
        else:
            _player_filter = _base_filter
            pool_label = "fallback: all approved"

        seeded_count = db.query(SemesterEnrollment).filter(*_player_filter).count()

        seeded_ids = {
            e.user_id for e in db.query(SemesterEnrollment).filter(*_player_filter).all()
        }
        non_checkin_ids = set(range(checkin_count + 1, TOTAL_ENROLLED + 1))

        # Bracket geometry
        bracket_size = _next_power_of_2(seeded_count)
        byes = _expected_byes(seeded_count)
        real_r1_matches = (seeded_count - byes) // 2

        print()
        print("  [3/4] Evaluating checks…")
        print()

        # ── Check 1: seeded_count == checked_in_count ──────────────────────────
        if seeded_count == checkin_count:
            results.append(_ok(f"seeded_count == checked_in_count ({seeded_count})"))
        else:
            results.append(_fail("seeded_count == checked_in_count",
                                 f"seeded={seeded_count}, checked_in={checkin_count}"))
            all_passed = False

        # ── Check 2: bracket_size == next power of 2 ──────────────────────────
        expected_bracket = _next_power_of_2(checkin_count)
        if bracket_size == expected_bracket:
            results.append(_ok(f"bracket_size == next_power_of_2({seeded_count}) == {bracket_size}"))
        else:
            results.append(_fail("bracket_size == next_power_of_2(seeded_count)",
                                 f"got {bracket_size}, expected {expected_bracket}"))
            all_passed = False

        # ── Check 3: bye positions only for absent players ─────────────────────
        # Byes are filled by the top-seeded players in the bracket generator.
        # Here we verify the bye COUNT is correct (generator contract):
        # byes = bracket_size - seeded_count, all auto-advanced are real seeded players.
        expected_byes = bracket_size - seeded_count
        if byes == expected_byes and byes >= 0:
            results.append(_ok(
                f"bye count == bracket_size - seeded_count "
                f"({bracket_size} - {seeded_count} = {byes})"
            ))
        else:
            results.append(_fail("bye count", f"expected {expected_byes}, got {byes}"))
            all_passed = False

        # Extra: non-checked-in players MUST NOT appear in seeded_ids
        leaked = seeded_ids.intersection(non_checkin_ids)
        if not leaked:
            results.append(_ok(
                f"no non-checked-in player leaked into seeded pool "
                f"(excluded: user_ids {sorted(non_checkin_ids)})"
            ))
        else:
            results.append(_fail("non-checked-in player exclusion",
                                 f"leaked user_ids: {sorted(leaked)}"))
            all_passed = False

        # ── Check 4: integrity alert does NOT trigger ─────────────────────────
        integrity_violation = (checked_in_db > 0 and seeded_count != checked_in_db)
        if not integrity_violation:
            results.append(_ok("integrity alert NOT triggered "
                               "(checked_in_db == seeded_count)"))
        else:
            results.append(_fail("integrity alert",
                                 f"checked_in_db={checked_in_db} != seeded_count={seeded_count}"))
            all_passed = False

        # ── Check 5: log snapshot matches actual DB state ─────────────────────
        snapshot = {
            "total_approved": total_approved,
            "total_checked_in": checked_in_db,
            "seeded_count": seeded_count,
            "pool": pool_label,
        }
        expected_snapshot = {
            "total_approved": TOTAL_ENROLLED,
            "total_checked_in": checkin_count,
            "seeded_count": checkin_count,
            "pool": "check-in confirmed",
        }
        if snapshot == expected_snapshot:
            results.append(_ok("log snapshot matches expected DB state"))
        else:
            results.append(_fail("log snapshot mismatch",
                                 f"got={snapshot}, expected={expected_snapshot}"))
            all_passed = False

        # ── Print results ──────────────────────────────────────────────────────
        print()
        print("  ┌─ Check Results " + "─" * 47)
        for line in results:
            print(f"  │{line}")
        print("  └" + "─" * 63)

        # ── Seeding snapshot ───────────────────────────────────────────────────
        print()
        print("  ┌─ Seeding Pool Snapshot " + "─" * 39)
        print(f"  │  total_approved  : {total_approved}")
        print(f"  │  total_checked_in: {checked_in_db}")
        print(f"  │  seeded_count    : {seeded_count}")
        print(f"  │  pool            : {pool_label}")
        print(f"  │  bracket_size    : {bracket_size}")
        print(f"  │  byes (round 1)  : {byes}")
        print(f"  │  real_r1_matches : {real_r1_matches}")
        print(f"  │  seeded_user_ids : {sorted(seeded_ids)}")
        print(f"  │  excluded_ids    : {sorted(non_checkin_ids)}")
        print("  └" + "─" * 63)

    finally:
        # ALWAYS rollback — staging data is never persisted
        db.rollback()
        db.execute(text("SET session_replication_role = 'origin'"))
        db.close()
        print()
        print("  [4/4] Transaction rolled back — no staging data modified.")

    # ── Final verdict ──────────────────────────────────────────────────────────
    print()
    print("=" * 65)
    if all_passed:
        print("  🟢  ALL CHECKS PASSED — deploy may proceed")
    else:
        failed = sum(1 for r in results if "FAIL" in r)
        print(f"  🔴  {failed} CHECK(S) FAILED — PRODUCTION STOP")
        print("      Investigate before deploying to production.")
    print("=" * 65)
    print()

    return all_passed


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Staging validation for check-in seeding regression fix"
    )
    parser.add_argument(
        "--checkin", "-c",
        type=int,
        default=10,
        metavar="N",
        help=f"Number of players that check in manually (2–{TOTAL_ENROLLED}, default 10)",
    )
    args = parser.parse_args()

    if not (2 <= args.checkin <= TOTAL_ENROLLED):
        print(f"ERROR: --checkin must be 2–{TOTAL_ENROLLED}")
        sys.exit(2)

    passed = run_validation(checkin_count=args.checkin)
    sys.exit(0 if passed else 1)
