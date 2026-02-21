"""add_coupon_type_enum_and_purchase_fields

Revision ID: 1de1b6240676
Revises: a0468da00d59
Create Date: 2026-01-06 16:49:23.148880

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1de1b6240676'
down_revision = 'a0468da00d59'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add new coupon types and purchase-related fields

    Steps:
    1. Add new enum values to coupontype enum (outside transaction)
    2. Add requires_purchase column
    3. Add requires_admin_approval column
    4. Set default values for existing coupons based on their type
    """
    # Step 1: Add new enum values to coupontype
    # PostgreSQL requires ALTER TYPE to be executed outside of a transaction
    # Use connection.execute with autocommit to avoid transaction block
    connection = op.get_bind()

    # Check if we're in a transaction and need to commit enum changes separately
    connection.execute(sa.text("COMMIT"))

    # Add enum values outside transaction
    connection.execute(sa.text("ALTER TYPE coupontype ADD VALUE IF NOT EXISTS 'bonus_credits'"))
    connection.execute(sa.text("ALTER TYPE coupontype ADD VALUE IF NOT EXISTS 'purchase_discount_percent'"))
    connection.execute(sa.text("ALTER TYPE coupontype ADD VALUE IF NOT EXISTS 'purchase_bonus_credits'"))

    # Step 2: Add requires_purchase column (default False for existing coupons)
    op.add_column('coupons', sa.Column('requires_purchase', sa.Boolean(), nullable=False, server_default='false'))

    # Step 3: Add requires_admin_approval column (default False for existing coupons)
    op.add_column('coupons', sa.Column('requires_admin_approval', sa.Boolean(), nullable=False, server_default='false'))

    # Step 4: Migrate existing coupons from old types to new types
    # All legacy types (PERCENT, FIXED, CREDITS) → bonus_credits (instant free credits)
    op.execute("""
        UPDATE coupons
        SET type = 'bonus_credits'::coupontype,
            requires_purchase = false,
            requires_admin_approval = false
        WHERE type IN ('PERCENT'::coupontype, 'FIXED'::coupontype, 'CREDITS'::coupontype);
    """)

    # Remove server_default after setting initial values
    op.alter_column('coupons', 'requires_purchase', server_default=None)
    op.alter_column('coupons', 'requires_admin_approval', server_default=None)


def downgrade() -> None:
    """
    Revert coupon type changes

    Steps:
    1. Migrate bonus_credits back to credits
    2. Migrate purchase_* types back to credits (data loss warning!)
    3. Drop requires_purchase column
    4. Drop requires_admin_approval column
    """
    # Step 1: Migrate all new types back to 'CREDITS' (best approximation)
    op.execute("""
        UPDATE coupons
        SET type = 'CREDITS'::coupontype
        WHERE type IN ('bonus_credits'::coupontype, 'purchase_discount_percent'::coupontype, 'purchase_bonus_credits'::coupontype);
    """)

    # Step 2: Drop new columns
    op.drop_column('coupons', 'requires_admin_approval')
    op.drop_column('coupons', 'requires_purchase')

    # Note: We cannot easily remove enum values from PostgreSQL enum type
    # They will remain but won't be used