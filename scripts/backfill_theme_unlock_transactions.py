"""
Backfill missing THEME_UNLOCK CreditTransaction records.

Context
-------
card_theme_service.unlock_theme() did not log CreditTransaction records before
the P0 fix was deployed.  This script creates the missing audit records for every
user whose unlocked_card_themes list contains themes that have no matching CT.

Safety guarantees
-----------------
* Idempotent  — checks for existing keys before inserting; safe to re-run.
* Read-only by default  — pass --commit to actually write to the DB.
* Does NOT modify credit_balance  — the balance is already correct on users.credit_balance;
  this script only fills in the missing audit trail.
* balance_after is RECONSTRUCTED (estimated) and is clearly marked in the description.
* A full dry-run summary is printed before any writes.

Reconstruction logic
--------------------
Starting balance = last known CT balance_after (or current balance if no CTs exist).
Working backwards through the theme list:
  balance_after[last_theme]  = current balance
  balance_after[second_last] = current_balance + theme_cost
  ...
  balance_after[first_theme] = current_balance + sum(all_theme_costs) - first_theme_cost

Confidence levels
-----------------
  HIGH   — reconstructed chain closes: start + all_rewards - all_theme_costs = current_balance
  MEDIUM — chain closes but theme unlock order is assumed
  LOW    — chain does NOT close (other unlogged deductions exist)

Usage
-----
  # Dry-run (default — no DB writes):
  PYTHONPATH=. python scripts/backfill_theme_unlock_transactions.py

  # Commit to DB:
  PYTHONPATH=. python scripts/backfill_theme_unlock_transactions.py --commit

  # Specific DB:
  DATABASE_URL="postgresql://..." PYTHONPATH=. python scripts/backfill_theme_unlock_transactions.py --commit
"""

import os
import sys
import argparse
from datetime import datetime, timedelta, timezone

# ── Path setup ────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.models.user import User
from app.models.license import UserLicense
from app.models.credit_transaction import CreditTransaction
from app.services.card_theme_service import THEMES


# ── DB connection ─────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres@localhost:5432/lfa_intern_system",
)


def _make_session():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()


# ── Core logic ────────────────────────────────────────────────────────────────

BACKFILL_KEY_PREFIX = "theme_unlock_backfill"
FORWARD_KEY_PREFIX = "theme_unlock"


def _theme_cost(theme_id: str) -> int:
    theme = THEMES.get(theme_id)
    return theme.credit_cost if theme else 500  # 500 CR is the standard premium cost


def _theme_label(theme_id: str) -> str:
    theme = THEMES.get(theme_id)
    return theme.label if theme else theme_id.title()


def _existing_key(db, key: str) -> bool:
    return db.query(CreditTransaction).filter(
        CreditTransaction.idempotency_key == key
    ).first() is not None


def _reconstruct_chain(current_balance: int, last_ct_balance_after: int | None, theme_ids: list[str]):
    """
    Reconstruct balance_after values for each theme unlock working backwards.

    Returns (chain, confidence) where:
      chain = list of (theme_id, balance_after) in chronological order
      confidence = "HIGH" | "MEDIUM" | "LOW"
    """
    total_cost = sum(_theme_cost(t) for t in theme_ids)

    if last_ct_balance_after is not None:
        reconstructed_start = last_ct_balance_after
    else:
        # No CT at all → assume start = current_balance + total_cost
        reconstructed_start = current_balance + total_cost

    # Check if the chain closes
    expected_end = reconstructed_start - total_cost
    if expected_end == current_balance:
        confidence = "HIGH"
    elif abs(expected_end - current_balance) <= 10:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    # Build chain: last theme has balance_after = current_balance,
    # second-to-last = current_balance + cost_of_last, etc.
    chain = []
    running = current_balance
    for theme_id in reversed(theme_ids):
        chain.append((theme_id, running))
        running += _theme_cost(theme_id)
    chain.reverse()  # back to chronological order

    return chain, confidence, reconstructed_start


def _find_missing_records(db) -> list[dict]:
    """Return list of planned backfill records (no DB writes)."""
    records = []

    users_with_themes = (
        db.query(User, UserLicense)
        .join(UserLicense, UserLicense.user_id == User.id)
        .filter(UserLicense.unlocked_card_themes.isnot(None))
        .all()
    )

    for user, lic in users_with_themes:
        theme_ids: list = list(lic.unlocked_card_themes or [])
        if not theme_ids:
            continue

        # Only premium themes need CT records
        premium_theme_ids = [t for t in theme_ids if THEMES.get(t) and THEMES[t].is_premium]
        if not premium_theme_ids:
            continue

        # Find which themes are missing a CT (forward or backfill key)
        missing = []
        for theme_id in premium_theme_ids:
            forward_key = f"{FORWARD_KEY_PREFIX}_{user.id}_{theme_id}"
            backfill_key = f"{BACKFILL_KEY_PREFIX}_{user.id}_{theme_id}"
            if not _existing_key(db, forward_key) and not _existing_key(db, backfill_key):
                missing.append(theme_id)

        if not missing:
            continue

        # Get last known CT balance_after for this user
        last_ct = (
            db.query(CreditTransaction)
            .filter(CreditTransaction.user_id == user.id)
            .order_by(CreditTransaction.created_at.desc())
            .first()
        )
        last_ct_balance_after = last_ct.balance_after if last_ct else None

        chain, confidence, reconstructed_start = _reconstruct_chain(
            current_balance=user.credit_balance,
            last_ct_balance_after=last_ct_balance_after,
            theme_ids=missing,
        )

        # Anchor date: use license created_at + small offsets for ordering
        anchor_dt = lic.created_at or datetime.now(timezone.utc)
        if hasattr(anchor_dt, "tzinfo") and anchor_dt.tzinfo is None:
            anchor_dt = anchor_dt.replace(tzinfo=timezone.utc)

        for idx, (theme_id, balance_after) in enumerate(chain):
            records.append({
                "user_id": user.id,
                "user_email": user.email,
                "theme_id": theme_id,
                "theme_label": _theme_label(theme_id),
                "cost": _theme_cost(theme_id),
                "balance_after": balance_after,
                "idempotency_key": f"{BACKFILL_KEY_PREFIX}_{user.id}_{theme_id}",
                "description": (
                    f"[BACKFILL][balance_after:estimated] "
                    f"Card theme unlock: {_theme_label(theme_id)}"
                ),
                "created_at": anchor_dt + timedelta(seconds=idx),
                "confidence": confidence,
                "reconstructed_start": reconstructed_start,
            })

    return records


def run(commit: bool):
    db = _make_session()
    try:
        records = _find_missing_records(db)

        if not records:
            print("✅ No missing THEME_UNLOCK records found. Nothing to backfill.")
            return

        # ── Print dry-run summary ─────────────────────────────────────────
        print(f"\n{'─'*70}")
        print(f"  Backfill plan — {'COMMIT MODE' if commit else 'DRY-RUN (pass --commit to write)'}")
        print(f"{'─'*70}")

        by_user: dict[int, list] = {}
        for r in records:
            by_user.setdefault(r["user_id"], []).append(r)

        for uid, recs in by_user.items():
            first = recs[0]
            total_cost = sum(r["cost"] for r in recs)
            print(f"\n  User {uid} ({first['user_email']})")
            print(f"    Reconstructed start balance : {first['reconstructed_start']} CR")
            print(f"    Total theme cost to backfill: {total_cost} CR")
            print(f"    Confidence                  : {first['confidence']}")
            if first["confidence"] == "LOW":
                print("    ⚠️  LOW CONFIDENCE — chain does not close; other unlogged deductions exist.")
            print(f"    Records to insert ({len(recs)}):")
            for r in recs:
                print(
                    f"      {r['theme_label']:12s}  cost={r['cost']:4d}  "
                    f"balance_after={r['balance_after']:6d}  "
                    f"date={r['created_at'].isoformat()[:19]}  "
                    f"key={r['idempotency_key']}"
                )

        print(f"\n{'─'*70}")
        print(f"  Total: {len(records)} INSERT(s) across {len(by_user)} user(s)")
        print(f"  credit_balance on users table: NOT modified")
        print(f"{'─'*70}\n")

        if not commit:
            print("  ↳ Dry-run complete. No writes made. Pass --commit to apply.")
            return

        # ── Commit ────────────────────────────────────────────────────────
        inserted = 0
        try:
            for r in records:
                # Double-check idempotency inside the same transaction
                if _existing_key(db, r["idempotency_key"]):
                    print(f"  ⏭  SKIP (already exists): {r['idempotency_key']}")
                    continue

                ct = CreditTransaction(
                    user_id=r["user_id"],
                    user_license_id=None,
                    transaction_type="THEME_UNLOCK",
                    amount=-r["cost"],
                    balance_after=r["balance_after"],
                    description=r["description"],
                    idempotency_key=r["idempotency_key"],
                    created_at=r["created_at"],
                )
                db.add(ct)
                inserted += 1

            db.commit()
            print(f"✅ Backfill committed: {inserted} record(s) inserted.")

        except Exception as exc:
            db.rollback()
            print(f"❌ Error during commit — full rollback applied: {exc}")
            raise

    finally:
        db.close()


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--commit",
        action="store_true",
        default=False,
        help="Write records to the database. Without this flag the script is read-only.",
    )
    args = parser.parse_args()
    run(commit=args.commit)
