"""DB state inspector for Get Card Entitlement manual QA.

Shows credit balance, CardDesignOwnership rows, and CARD_DESIGN_UNLOCK
CreditTransactions for the two QA test users.

Usage:
    python scripts/dev_qa_check_get_card.py
    python scripts/dev_qa_check_get_card.py --user-id 9
    python scripts/dev_qa_check_get_card.py --all
"""
import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

QA_USERS = {
    9:    "seed.player.1@promo-seed.test",
    3617: "johny7@lfa.com",
}


def _check_user(db, user_id: int, email: str) -> None:
    from app.models.card_design_ownership import CardDesignOwnership
    from app.models.credit_transaction import CreditTransaction
    from app.models.user import User

    u = db.query(User).filter_by(id=user_id).first()
    if not u:
        print(f"  ❌  user id={user_id} not found")
        return

    print(f"  ─────────────────────────────────────────────────")
    print(f"  User: {u.email}  (id={u.id})")
    print(f"  Credit balance: {u.credit_balance} CR")

    # CardDesignOwnership rows
    ownerships = (
        db.query(CardDesignOwnership)
        .filter_by(user_id=user_id)
        .order_by(CardDesignOwnership.acquired_at)
        .all()
    )
    if ownerships:
        print(f"  Owned designs ({len(ownerships)}):")
        for o in ownerships:
            print(
                f"    • card_type_id={o.card_type_id!r:20s} "
                f"design_id={o.design_id!r:15s} "
                f"source={o.source!r:15s} "
                f"ct_id={o.credit_transaction_id}"
            )
    else:
        print(f"  No CardDesignOwnership rows")

    # CARD_DESIGN_UNLOCK transactions
    txns = (
        db.query(CreditTransaction)
        .filter_by(user_id=user_id, transaction_type="CARD_DESIGN_UNLOCK")
        .order_by(CreditTransaction.created_at)
        .all()
    )
    if txns:
        print(f"  CARD_DESIGN_UNLOCK transactions ({len(txns)}):")
        for t in txns:
            print(
                f"    • id={t.id:6d}  amount={t.amount:+5d}  "
                f"balance_after={t.balance_after}  "
                f"idempotency_key={t.idempotency_key}"
            )
    else:
        print(f"  No CARD_DESIGN_UNLOCK transactions")
    print()


def _run(user_ids: list[int]) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.config import settings

    engine = create_engine(settings.DATABASE_URL)
    db = sessionmaker(bind=engine)()

    try:
        print("\n=== Get Card Entitlement — QA DB State ===\n")
        for uid in user_ids:
            email = QA_USERS.get(uid, f"user_{uid}")
            _check_user(db, uid, email)

        # Uniqueness sanity check
        from app.models.card_design_ownership import CardDesignOwnership
        for uid in user_ids:
            rows = db.query(CardDesignOwnership).filter_by(user_id=uid).all()
            seen = set()
            dups = []
            for r in rows:
                key = (r.card_type_id, r.design_id)
                if key in seen:
                    dups.append(key)
                seen.add(key)
            if dups:
                print(f"  ❌  DUPLICATE ownership rows for user {uid}: {dups}")
            else:
                if rows:
                    print(f"  ✅  No duplicate ownership rows for user {uid}")

    finally:
        db.close()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--user-id", type=int, help="Check a specific user_id")
    p.add_argument("--all", action="store_true", help="Show all CDO rows in the system")
    args = p.parse_args()

    if args.all:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.config import settings
        engine = create_engine(settings.DATABASE_URL)
        db = sessionmaker(bind=engine)()
        try:
            from app.models.card_design_ownership import CardDesignOwnership
            rows = db.query(CardDesignOwnership).order_by(CardDesignOwnership.user_id).all()
            print(f"\n=== All CardDesignOwnership rows ({len(rows)}) ===\n")
            for r in rows:
                print(
                    f"  id={r.id:6d}  user={r.user_id:6d}  "
                    f"type={r.card_type_id:20s}  design={r.design_id:15s}  "
                    f"source={r.source:10s}  ct={r.credit_transaction_id}"
                )
        finally:
            db.close()
        return

    if args.user_id:
        _run([args.user_id])
    else:
        _run(list(QA_USERS.keys()))


if __name__ == "__main__":
    main()
