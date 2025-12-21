"""
Create Retroactive License Renewal Transactions
================================================
This script creates credit_transaction records for all existing license renewals
that were performed before the credit transaction tracking was implemented.

It identifies licenses that:
1. Have been renewed (last_renewed_at is not null)
2. Have no corresponding credit_transaction records
3. User has credits deducted but no transaction history

For each such license, it creates a transaction record showing the -1000 credit deduction.
"""

from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.license import UserLicense
from app.models.user import User
from app.models.credit_transaction import CreditTransaction


def create_retroactive_transactions():
    """Create credit transactions for existing license renewals"""
    db: Session = SessionLocal()

    try:
        print("=" * 70)
        print("Creating Retroactive License Renewal Transactions")
        print("=" * 70)

        # Get all licenses that have been renewed (last_renewed_at is set)
        renewed_licenses = db.query(UserLicense).filter(
            UserLicense.last_renewed_at.isnot(None)
        ).all()

        print(f"\n✅ Found {len(renewed_licenses)} licenses with renewal history")

        # Check which ones already have transaction records
        transactions_created = 0
        transactions_skipped = 0

        for license in renewed_licenses:
            # Check if transaction already exists for this license
            existing_transaction = db.query(CreditTransaction).filter(
                CreditTransaction.user_license_id == license.id,
                CreditTransaction.transaction_type == "LICENSE_RENEWAL"
            ).first()

            if existing_transaction:
                print(f"⏭️  Skipping License #{license.id} - transaction already exists")
                transactions_skipped += 1
                continue

            # Get user for balance information
            user = db.query(User).filter(User.id == license.user_id).first()
            if not user:
                print(f"❌ Error: User not found for license #{license.id}")
                continue

            # Determine renewal cost
            renewal_cost = license.renewal_cost or 1000

            # Create retroactive transaction
            # Note: We use last_renewed_at as the transaction timestamp
            credit_transaction = CreditTransaction(
                user_license_id=license.id,
                transaction_type="LICENSE_RENEWAL",
                amount=-renewal_cost,
                balance_after=user.credit_balance,  # Current balance (best approximation)
                description=f"License renewed ({license.specialization_type} Level {license.current_level}) - Retroactive record",
                semester_id=None,
                enrollment_id=None,
                created_at=license.last_renewed_at  # Use actual renewal date
            )

            db.add(credit_transaction)
            transactions_created += 1

            print(f"✅ Created transaction for License #{license.id} ({license.specialization_type} L{license.current_level}) - {user.email}")
            print(f"   Amount: -{renewal_cost} credits | Date: {license.last_renewed_at}")

        # Commit all transactions
        db.commit()

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Total licenses reviewed: {len(renewed_licenses)}")
        print(f"Transactions created: {transactions_created}")
        print(f"Transactions skipped (already exist): {transactions_skipped}")
        print("=" * 70)

        if transactions_created > 0:
            print("\n✅ SUCCESS: Retroactive transactions created!")
            print("Users can now see their license renewal history in the dashboard.")
        else:
            print("\nℹ️  No new transactions needed - all renewals already have records.")

    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_retroactive_transactions()
