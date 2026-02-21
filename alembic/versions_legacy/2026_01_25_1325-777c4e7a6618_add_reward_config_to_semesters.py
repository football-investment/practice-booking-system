"""add_reward_config_to_semesters

Revision ID: 777c4e7a6618
Revises: 2026_01_25_1600
Create Date: 2026-01-25 13:25:00.200060

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '777c4e7a6618'
down_revision = '2026_01_25_1600'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add reward_config JSONB column to semesters table
    op.add_column('semesters', sa.Column('reward_config', postgresql.JSONB, nullable=True))

    # Create index for faster JSONB queries
    op.create_index(
        'ix_semesters_reward_config',
        'semesters',
        ['reward_config'],
        postgresql_using='gin',
        unique=False
    )


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_semesters_reward_config', table_name='semesters')

    # Drop column
    op.drop_column('semesters', 'reward_config')