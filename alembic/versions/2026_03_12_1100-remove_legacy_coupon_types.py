"""remove_legacy_coupon_types

Remove deprecated PERCENT, FIXED, CREDITS values from the coupontype PostgreSQL enum.
Any rows using these types are migrated to BONUS_CREDITS first (expected: 0 rows in prod).

Revision ID: 2026_03_12_1100
Revises: 2026_03_12_1000
Create Date: 2026-03-12 11:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2026_03_12_1100'
down_revision = '2026_03_12_1000'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Migrate any legacy rows (expected: 0 in practice)
    op.execute("UPDATE coupons SET type = 'BONUS_CREDITS' WHERE type IN ('PERCENT', 'FIXED', 'CREDITS')")

    # 2. Recreate the enum without legacy values (PostgreSQL cannot drop enum values directly)
    op.execute("CREATE TYPE coupontype_new AS ENUM ('BONUS_CREDITS', 'PURCHASE_DISCOUNT_PERCENT', 'PURCHASE_BONUS_CREDITS')")
    op.execute("ALTER TABLE coupons ALTER COLUMN type TYPE coupontype_new USING type::text::coupontype_new")
    op.execute("DROP TYPE coupontype")
    op.execute("ALTER TYPE coupontype_new RENAME TO coupontype")


def downgrade() -> None:
    # Restore the enum with legacy values
    op.execute("CREATE TYPE coupontype_old AS ENUM ('BONUS_CREDITS', 'PURCHASE_DISCOUNT_PERCENT', 'PURCHASE_BONUS_CREDITS', 'PERCENT', 'FIXED', 'CREDITS')")
    op.execute("ALTER TABLE coupons ALTER COLUMN type TYPE coupontype_old USING type::text::coupontype_old")
    op.execute("DROP TYPE coupontype")
    op.execute("ALTER TYPE coupontype_old RENAME TO coupontype")
