"""add tournament game fields to sessions

Revision ID: add_tournament_game_fields
Revises: d64255498079
Create Date: 2025-12-31 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_tournament_game_fields'
down_revision = 'd64255498079'
branch_labels = None
depends_on = None


def upgrade():
    """Add tournament game fields to sessions table"""

    # Add 3 new columns to sessions table
    op.add_column('sessions', sa.Column('is_tournament_game', sa.Boolean(), nullable=True))
    op.add_column('sessions', sa.Column('game_type', sa.String(length=100), nullable=True))
    op.add_column('sessions', sa.Column('game_results', sa.Text(), nullable=True))

    # Create index for tournament game filtering
    op.create_index('ix_sessions_is_tournament_game', 'sessions', ['is_tournament_game'])

    # Set default value for existing sessions (all FALSE)
    op.execute("UPDATE sessions SET is_tournament_game = FALSE WHERE is_tournament_game IS NULL")

    # Make is_tournament_game non-nullable
    op.alter_column('sessions', 'is_tournament_game', nullable=False)


def downgrade():
    """Remove tournament game fields from sessions table"""

    # Drop index
    op.drop_index('ix_sessions_is_tournament_game', 'sessions')

    # Drop columns
    op.drop_column('sessions', 'game_results')
    op.drop_column('sessions', 'game_type')
    op.drop_column('sessions', 'is_tournament_game')
