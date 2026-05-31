"""Dev QA setup for Get Card Entitlement manual testing.

Sets up two test users so the tester can manually validate the full
purchase → export flow for all three card families:
  1. seed.player.1@promo-seed.test  (password: PromoSeed@2026)
     – primary QA user; 2495 CR pre-existing; already sufficient
     – used for: Player Card, Welcome Card shop purchase
     – VT challenge: no challenge; Challenge Card shop purchase only
  2. johny7@lfa.com  (password reset to: QaGetCard@2026)
     – is challenger in challenge #1 (challenger_id=3617)
     – used for: Challenge Card shop + export guard test
     – grants 500 CR (enough for challenge_card=150 + buffer)

Usage (safe to run multiple times — idempotent):
    python scripts/dev_qa_setup_get_card.py
    python scripts/dev_qa_setup_get_card.py --dry-run
"""
import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))


def _run(dry_run: bool) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.config import settings
    from app.core.security import get_password_hash
    from app.models.user import User
    from app.services.credit_service import CreditService

    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # ── User 1: seed.player.1@promo-seed.test ────────────────────────────
        u1 = db.query(User).filter_by(email="seed.player.1@promo-seed.test").first()
        if not u1:
            print("❌  seed.player.1@promo-seed.test not found — run seed_promotion_events.py first")
            sys.exit(1)

        print(f"✅  User 1: {u1.email}  (id={u1.id})")
        print(f"   credit_balance = {u1.credit_balance} CR")
        print(f"   password       = PromoSeed@2026  (original seed password — no change)")
        print()

        # ── User 2: johny7@lfa.com ────────────────────────────────────────────
        u2 = db.query(User).filter_by(email="johny7@lfa.com").first()
        if not u2:
            print("❌  johny7@lfa.com not found — no VT challenge user in DB")
            sys.exit(1)

        print(f"✅  User 2: {u2.email}  (id={u2.id})")
        print(f"   credit_balance before grant = {u2.credit_balance} CR")

        if not dry_run:
            # Reset password to known QA value
            u2.password_hash = get_password_hash("QaGetCard@2026")
            print(f"   password reset → QaGetCard@2026")

            # Grant 500 CR if they have less than 500
            if u2.credit_balance < 500:
                needed = 500 - u2.credit_balance
                u2.credit_balance += needed
                svc = CreditService(db)
                svc.create_transaction(
                    user_id=u2.id,
                    user_license_id=None,
                    transaction_type="QA_SETUP_GRANT",
                    amount=needed,
                    balance_after=u2.credit_balance,
                    description="Dev QA setup grant for Get Card testing",
                    idempotency_key=f"qa_get_card_setup_{u2.id}",
                )
                db.flush()
                print(f"   granted {needed} CR → new balance {u2.credit_balance} CR")
            else:
                print(f"   sufficient credits ({u2.credit_balance} CR) — no grant needed")

            db.commit()
        else:
            print(f"   [dry-run] would reset password → QaGetCard@2026")
            needed = max(0, 500 - u2.credit_balance)
            if needed:
                print(f"   [dry-run] would grant {needed} CR ({u2.credit_balance} → {u2.credit_balance + needed})")
            else:
                print(f"   [dry-run] sufficient credits — no grant")

        print()
        print("═" * 60)
        print("Manual QA Ready — test accounts:")
        print()
        print("  USER 1 (Player Card + Welcome Card purchases)")
        print(f"  Email   : seed.player.1@promo-seed.test")
        print(f"  Password: PromoSeed@2026")
        print(f"  Balance : {u1.credit_balance} CR")
        print()
        print("  USER 2 (Challenge Card purchase + export guard)")
        print(f"  Email   : johny7@lfa.com")
        print(f"  Password: {'[unchanged — dry-run]' if dry_run else 'QaGetCard@2026'}")
        print(f"  Balance : {u2.credit_balance} CR (after grant)" if not dry_run else f"  Balance : {u2.credit_balance} CR (before grant)")
        print(f"  VT challenge id: 1 (challenger_id=3617)")
        print()
        print("  Shop URL: http://localhost:8000/my-cards/shop")
        print()
        if dry_run:
            print("  [dry-run] No changes written to DB.")

    finally:
        db.close()


def main() -> None:
    p = argparse.ArgumentParser(description="Dev QA setup for Get Card testing")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    _run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
