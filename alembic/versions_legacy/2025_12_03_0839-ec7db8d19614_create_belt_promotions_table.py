"""create_belt_promotions_table

Revision ID: ec7db8d19614
Revises: ecc960454088
Create Date: 2025-12-03 08:39:10.762350

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ec7db8d19614'
down_revision = 'ecc960454088'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'belt_promotions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_license_id', sa.Integer(), nullable=False),
        sa.Column('from_belt', sa.String(50), nullable=True),  # NULL for initial belt
        sa.Column('to_belt', sa.String(50), nullable=False),
        sa.Column('promoted_by', sa.Integer(), nullable=False),
        sa.Column('promoted_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('exam_score', sa.Integer(), nullable=True),  # Optional exam score (0-100)
        sa.Column('exam_notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_license_id'], ['user_licenses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['promoted_by'], ['users.id'], ondelete='RESTRICT')
    )

    # Indexes for performance
    op.create_index('ix_belt_promotions_user_license_id', 'belt_promotions', ['user_license_id'])
    op.create_index('ix_belt_promotions_to_belt', 'belt_promotions', ['to_belt'])
    op.create_index('ix_belt_promotions_promoted_at', 'belt_promotions', ['promoted_at'])


def downgrade() -> None:
    op.drop_index('ix_belt_promotions_promoted_at', 'belt_promotions')
    op.drop_index('ix_belt_promotions_to_belt', 'belt_promotions')
    op.drop_index('ix_belt_promotions_user_license_id', 'belt_promotions')
    op.drop_table('belt_promotions')