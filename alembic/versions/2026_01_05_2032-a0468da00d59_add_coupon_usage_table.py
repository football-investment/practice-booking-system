"""add_coupon_usage_table

Revision ID: a0468da00d59
Revises: 0af9be21a7db
Create Date: 2026-01-05 20:32:45.492698

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a0468da00d59'
down_revision = '0af9be21a7db'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create coupon_usages table
    op.create_table(
        'coupon_usages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('coupon_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('credits_awarded', sa.Integer(), nullable=False, comment='Amount of credits awarded from this coupon'),
        sa.Column('used_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['coupon_id'], ['coupons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_coupon_usages_coupon_id'), 'coupon_usages', ['coupon_id'], unique=False)
    op.create_index(op.f('ix_coupon_usages_user_id'), 'coupon_usages', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_coupon_usages_user_id'), table_name='coupon_usages')
    op.drop_index(op.f('ix_coupon_usages_coupon_id'), table_name='coupon_usages')
    op.drop_table('coupon_usages')