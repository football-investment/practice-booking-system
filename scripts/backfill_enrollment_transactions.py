#!/usr/bin/env python3
"""
backfill_enrollment_transactions.py

Net-zero retroactive reconstruction of CreditTransaction records for
SemesterEnrollment rows that were created by lifecycle seed scripts,
bypassing CreditService.

Strategy: Strategy 1 — approved (net-zero reconstruction)
  For each affected user:
    1.  INSERT 1× SEED_GRANT CT            amount = +Σ_cost
    2.  INSERT N× TOURNAMENT_ENROLLMENT CT amount = -cost each
    Net credit_balance change: 0 (grant exactly offsets deductions)

Idempotency (batch-level guard):
  batch_id = sha256(user_id + sorted(se_ids))[:16]
  SEED_GRANT key  = f"seed_grant_batch_{user_id}_{batch_id}"
  Enrollment key  = f"seed_enrollment_{user_id}_{semester_id}"
  If SEED_GRANT key already exists → entire batch already processed, skip.

Ordering (deterministic, no ad-hoc offsets):
  SEED_GRANT is db.flush()-ed first → guaranteed lower auto-increment ID.
  Enrollment CTs are inserted in ORDER BY se.created_at, se.id.
  balance_after is computed at insert time in this order → chain correct
  by construction, independent of timestamp collisions.

Reconciliation (pre/post per user):
  PRE:  record balance_before
  POST: assert credit_balance == balance_before  (net-zero)
        assert Σ(new CT amounts) == 0
        assert no NULL balance_after in new CTs
        assert new CT count == 1 + len(enrollments)

Usage:
  PYTHONPATH=. python scripts/backfill_enrollment_transactions.py            # dry run
  PYTHONPATH=. python scripts/backfill_enrollment_transactions.py --commit   # write
"""
import argparse
import hashlib
import sys
import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres@localhost:5432/lfa_intern_system")

from app.models.user import User
from app.models.semester_enrollment import SemesterEnrollment
from app.models.semester import Semester
from app.models.credit_transaction import CreditTransaction


def _get_db():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _batch_id(user_id: int, se_ids: List[int]) -> str:
    """
    Deterministic 16-char hex string.
    Derived from user_id + sorted SemesterEnrollment IDs.
    Same input → always same batch_id → idempotency guard is stable across runs.
    """
    raw = f"{user_id}:{','.join(str(i) for i in sorted(se_ids))}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _covered_enrollment_ids(db) -> set:
    """
    Return SE ids that already have a TOURNAMENT_ENROLLMENT CreditTransaction.
    Covers both real web-enrollments (enrollment_id set) and any previous backfill run.
    """
    rows = (
        db.query(CreditTransaction.enrollment_id)
        .filter(
            CreditTransaction.transaction_type == "TOURNAMENT_ENROLLMENT",
            CreditTransaction.enrollment_id.isnot(None),
        )
        .all()
    )
    return {r.enrollment_id for r in rows}


def _find_affected_users(
    db,
) -> Dict[int, List[Tuple[SemesterEnrollment, Semester]]]:
    """
    Return {user_id: [(se, semester), ...]} for every user who has at least
    one SemesterEnrollment without a paired TOURNAMENT_ENROLLMENT CT.

    Only includes enrollments with enrollment_cost > 0 — free enrollments
    have no financial impact and need no CT.
    Ordered per user by (se.created_at, se.id) — deterministic insertion order.
    """
    covered = _covered_enrollment_ids(db)

    rows = (
        db.query(SemesterEnrollment, Semester)
        .join(Semester, SemesterEnrollment.semester_id == Semester.id)
        .filter(Semester.enrollment_cost > 0)
        .order_by(
            SemesterEnrollment.user_id,
            SemesterEnrollment.created_at,
            SemesterEnrollment.id,
        )
        .all()
    )

    result: Dict[int, List[Tuple[SemesterEnrollment, Semester]]] = defaultdict(list)
    for se, sem in rows:
        if se.id not in covered:
            result[se.user_id].append((se, sem))

    return dict(result)


# ─────────────────────────────────────────────────────────────────────────────
# Reconciliation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ReconciliationResult:
    user_id: int
    balance_before: int
    balance_after_op: int
    new_ct_count: int
    batch_net: int
    errors: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0


def _reconcile(
    db,
    user_id: int,
    balance_before: int,
    bid: str,
    expected_enrollment_count: int,
) -> ReconciliationResult:
    """
    Post-flush reconciliation for a single user's batch.
    Called before db.commit() — runs in the same transaction.

    Checks:
      1. credit_balance unchanged (net-zero guarantee)
      2. Σ(new CT amounts) == 0
      3. No NULL balance_after in new CTs
      4. New CT count == 1 (grant) + expected_enrollment_count
    """
    user = db.query(User).filter(User.id == user_id).first()
    errors = []

    balance_after_op = user.credit_balance if user else None

    # 1. Balance unchanged
    if balance_after_op != balance_before:
        errors.append(
            f"balance changed {balance_before} → {balance_after_op} (expected unchanged)"
        )

    # 2 + 3 + 4: collect new batch CTs
    grant_key = f"seed_grant_batch_{user_id}_{bid}"
    enroll_prefix = f"seed_enrollment_{user_id}_"

    new_grant = (
        db.query(CreditTransaction)
        .filter(CreditTransaction.idempotency_key == grant_key)
        .first()
    )
    new_enrollments = (
        db.query(CreditTransaction)
        .filter(CreditTransaction.idempotency_key.like(f"{enroll_prefix}%"))
        .all()
    )
    all_new = ([new_grant] if new_grant else []) + new_enrollments

    # 2. Net sum == 0
    batch_net = sum(ct.amount for ct in all_new)
    if batch_net != 0:
        errors.append(f"batch net sum = {batch_net} (expected 0)")

    # 3. No NULL balance_after (schema enforces NOT NULL, but double-check)
    null_ba = [ct.idempotency_key for ct in all_new if ct.balance_after is None]
    if null_ba:
        errors.append(f"NULL balance_after on: {null_ba}")

    # 4. Count
    expected = 1 + expected_enrollment_count
    if len(all_new) != expected:
        errors.append(f"expected {expected} new CTs, found {len(all_new)}")

    return ReconciliationResult(
        user_id=user_id,
        balance_before=balance_before,
        balance_after_op=balance_after_op or 0,
        new_ct_count=len(all_new),
        batch_net=batch_net,
        errors=errors,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def run(commit: bool) -> None:
    db = _get_db()
    try:
        affected = _find_affected_users(db)

        if not affected:
            print("✅ No missing TOURNAMENT_ENROLLMENT records found. Nothing to backfill.")
            return

        total_users = len(affected)
        total_enrollments = sum(len(v) for v in affected.values())
        total_cost = sum(
            sem.enrollment_cost for pairs in affected.values() for _, sem in pairs
        )

        print("─" * 72)
        print(f"  Backfill plan — {'COMMIT' if commit else 'DRY RUN'} MODE")
        print("─" * 72)
        print(f"  Affected users        : {total_users}")
        print(f"  Total enrollments     : {total_enrollments}")
        print(f"  Total SEED_GRANT CTs  : {total_users}  (one per user)")
        print(f"  Total ENROLLMENT CTs  : {total_enrollments}")
        print(f"  Total credit flow     : +{total_cost} CR grant / -{total_cost} CR deductions")
        print(f"  Net balance change    : 0 CR  (net-zero guarantee)")
        print("─" * 72)

        reconciliation_results: List[ReconciliationResult] = []

        for user_id, pairs in sorted(affected.items()):
            # Lock the user row to get a consistent balance snapshot
            user = (
                db.query(User)
                .filter(User.id == user_id)
                .with_for_update()
                .first()
            )
            if not user:
                print(f"\n  ⚠️  User {user_id} not found — skipping")
                continue

            balance_before = user.credit_balance
            se_ids = [se.id for se, _ in pairs]
            bid = _batch_id(user_id, se_ids)
            grant_key = f"seed_grant_batch_{user_id}_{bid}"

            # ── Batch-level idempotency guard ──────────────────────────────
            # If SEED_GRANT key already exists, the entire batch was already
            # committed in a previous run. Skip without touching the DB.
            existing_grant = (
                db.query(CreditTransaction)
                .filter(CreditTransaction.idempotency_key == grant_key)
                .first()
            )
            if existing_grant:
                print(
                    f"\n  ⏭  User {user_id} ({user.email}): "
                    f"batch {bid[:8]}… already processed — skipping"
                )
                continue

            batch_cost = sum(sem.enrollment_cost for _, sem in pairs)

            print(f"\n  User {user_id}  ({user.email})")
            print(f"    Current balance  : {balance_before:6d} CR")
            print(f"    Enrollments      : {len(pairs)}")
            print(f"    Batch cost       : {batch_cost:6d} CR")
            print(f"    Batch ID         : {bid}")
            print(f"    Records ({1 + len(pairs)}):")

            # ── Compute balance_after chain ────────────────────────────────
            # SEED_GRANT lifts balance by batch_cost, then each enrollment
            # brings it back down. Chain closes at exactly balance_before.
            running = balance_before + batch_cost

            # 1. SEED_GRANT — use earliest enrollment's created_at so the
            #    record is anchored to the seed run timestamp.
            #    Ordering within the batch is guaranteed by auto-increment ID:
            #    SEED_GRANT is flush()-ed first → lower ID → appears before
            #    enrollment CTs when sorted by (created_at, id).
            grant_ts = pairs[0][0].created_at  # min created_at (rows already sorted)

            print(
                f"      SEED_GRANT        +{batch_cost:5d} CR"
                f"  balance_after={running:6d}"
                f"  key={grant_key}"
            )

            if commit:
                grant_ct = CreditTransaction(
                    user_id=user_id,
                    transaction_type="SEED_GRANT",
                    amount=batch_cost,
                    balance_after=running,
                    description=(
                        f"[LIFECYCLE_SEED] Test credit grant for "
                        f"{len(pairs)} tournament enrollment(s)"
                    ),
                    idempotency_key=grant_key,
                    created_at=grant_ts,
                )
                db.add(grant_ct)
                # flush() assigns the auto-increment ID, guaranteeing
                # SEED_GRANT has a lower ID than all enrollment CTs below.
                db.flush()

            # 2. TOURNAMENT_ENROLLMENT CTs — in (created_at, id) order
            for se, sem in pairs:
                enroll_key = f"seed_enrollment_{user_id}_{sem.id}"
                running -= sem.enrollment_cost

                print(
                    f"      ENROLLMENT        -{sem.enrollment_cost:5d} CR"
                    f"  balance_after={running:6d}"
                    f"  {sem.name[:36]:<36}"
                    f"  key={enroll_key}"
                )

                if commit:
                    enroll_ct = CreditTransaction(
                        # Use user_license_id to mirror real enrollment CT shape
                        user_license_id=se.user_license_id,
                        transaction_type="TOURNAMENT_ENROLLMENT",
                        amount=-sem.enrollment_cost,
                        balance_after=running,
                        description=f"[LIFECYCLE_SEED] Enrolled in {sem.name}",
                        semester_id=sem.id,
                        enrollment_id=se.id,
                        idempotency_key=enroll_key,
                        created_at=se.created_at,
                    )
                    db.add(enroll_ct)

            # ── Chain closure assertion ────────────────────────────────────
            # running must equal balance_before; if not, the batch_cost
            # computation is wrong and we must abort before touching the DB.
            assert running == balance_before, (
                f"BUG: chain did not close for user {user_id}! "
                f"Expected {balance_before}, got {running}"
            )

            if commit:
                db.flush()
                result = _reconcile(db, user_id, balance_before, bid, len(pairs))
                reconciliation_results.append(result)
                if not result.passed:
                    print(f"\n    ❌ RECONCILIATION FAILED: {result.errors}")
                    db.rollback()
                    sys.exit(1)
                print(
                    f"    ✅ Pre-commit reconciliation: "
                    f"balance={balance_before} (unchanged)  "
                    f"net={result.batch_net}  new_cts={result.new_ct_count}"
                )

        # ── Summary ───────────────────────────────────────────────────────
        print("\n" + "─" * 72)
        print(
            f"  Total: {total_enrollments} TOURNAMENT_ENROLLMENT + "
            f"{total_users} SEED_GRANT INSERT(s)"
        )
        print(f"  credit_balance on users table: NOT modified (net-zero)")
        print("─" * 72)

        if commit:
            db.commit()
            print("\n✅ Backfill committed.")

            # ── Post-commit reconciliation summary ────────────────────────
            if reconciliation_results:
                print("\n  Post-commit reconciliation summary:")
                all_passed = True
                for r in reconciliation_results:
                    status = "✅" if r.passed else "❌"
                    print(
                        f"    {status}  user={r.user_id:5d}"
                        f"  balance={r.balance_before} (unchanged)"
                        f"  new_cts={r.new_ct_count}"
                        f"  net={r.batch_net}"
                    )
                    if not r.passed:
                        all_passed = False
                        for err in r.errors:
                            print(f"         ↳ {err}")

                if all_passed:
                    print(
                        f"\n  ✅ All {len(reconciliation_results)} reconciliation "
                        f"check(s) passed."
                    )
                else:
                    failed = sum(1 for r in reconciliation_results if not r.passed)
                    print(f"\n  ❌ {failed} reconciliation check(s) FAILED.")
                    sys.exit(1)
        else:
            print("\n  (dry run — no DB changes made)")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backfill TOURNAMENT_ENROLLMENT CreditTransactions for seed enrollments."
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Write to DB (default: dry run only)",
    )
    args = parser.parse_args()
    run(commit=args.commit)
