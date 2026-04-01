"""Add card_theme and unlocked_card_themes to user_licenses

Revision ID: 2026_04_01_card_theme
Revises: 2026_03_28_1200
Create Date: 2026-04-01 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '2026_04_01_card_theme'
down_revision = '2026_03_28_1200'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'user_licenses',
        sa.Column(
            'card_theme',
            sa.String(32),
            nullable=False,
            server_default='default',
            comment='Active player card colour theme (e.g. default, midnight, gold)'
        )
    )
    op.add_column(
        'user_licenses',
        sa.Column(
            'unlocked_card_themes',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='[]',
            comment='List of premium theme IDs unlocked by this user (e.g. ["gold", "crimson"])'
        )
    )


def downgrade():
    op.drop_column('user_licenses', 'unlocked_card_themes')
    op.drop_column('user_licenses', 'card_theme')
