"""add_game_config_to_semesters

Adds game_config JSONB column to semesters table for storing tournament-specific
game rules, simulation parameters, and configuration settings.

This enables:
- Reproducible tournament simulations (save/load exact config)
- Explicit configuration (no more hardcoded defaults)
- Auditability (query tournaments by configuration)
- Flexibility (test different configurations easily)

Revision ID: 47ebca7dc3a8
Revises: 3ae0c3d15363
Create Date: 2026-01-28 19:47:44.985484

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '47ebca7dc3a8'
down_revision = '3ae0c3d15363'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add game_config JSONB column to semesters table"""
    # Add game_config column
    op.add_column(
        'semesters',
        sa.Column('game_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )

    # Create GIN index for efficient JSONB queries
    op.create_index(
        'ix_semesters_game_config',
        'semesters',
        ['game_config'],
        postgresql_using='gin'
    )


def downgrade() -> None:
    """Remove game_config column from semesters table"""
    # Drop index first
    op.drop_index('ix_semesters_game_config', table_name='semesters')

    # Drop column
    op.drop_column('semesters', 'game_config')