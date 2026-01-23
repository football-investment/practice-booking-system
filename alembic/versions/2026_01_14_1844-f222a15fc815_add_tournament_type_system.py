"""add_tournament_type_system

Adds tournament type configuration system for auto-generating tournament sessions.

Key changes:
1. Creates tournament_types table with pre-defined tournament formats
2. Adds tournament_type_id FK to semesters table
3. Adds session generation tracking fields to semesters
4. Adds auto-generation metadata fields to sessions table

CRITICAL: Sessions are generated AFTER enrollment closes (tournament_status = IN_PROGRESS)

Revision ID: f222a15fc815
Revises: 4d901ba96e8f
Create Date: 2026-01-14 18:44:06.768254

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision = 'f222a15fc815'
down_revision = '4d901ba96e8f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create tournament_types table
    op.create_table(
        'tournament_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('min_players', sa.Integer(), nullable=False, server_default='4'),
        sa.Column('max_players', sa.Integer(), nullable=True),
        sa.Column('requires_power_of_two', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('session_duration_minutes', sa.Integer(), nullable=False, server_default='90'),
        sa.Column('break_between_sessions_minutes', sa.Integer(), nullable=False, server_default='15'),
        sa.Column('config', JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_tournament_types_id', 'tournament_types', ['id'])
    op.create_index('ix_tournament_types_code', 'tournament_types', ['code'])

    # 2. Add tournament_type_id FK to semesters table
    op.add_column('semesters', sa.Column('tournament_type_id', sa.Integer(), nullable=True,
                                         comment='FK to tournament_types table (for auto-generating session structure)'))
    op.create_foreign_key('fk_semesters_tournament_type_id', 'semesters', 'tournament_types',
                         ['tournament_type_id'], ['id'], ondelete='SET NULL')

    # 3. Add session generation tracking fields to semesters
    op.add_column('semesters', sa.Column('sessions_generated', sa.Boolean(), nullable=False,
                                         server_default='false',
                                         comment='True if tournament sessions have been auto-generated (prevents duplicate generation)'))
    op.add_column('semesters', sa.Column('sessions_generated_at', sa.DateTime(), nullable=True,
                                         comment='Timestamp when sessions were auto-generated'))

    # 4. Add auto-generation metadata fields to sessions table
    op.add_column('sessions', sa.Column('auto_generated', sa.Boolean(), nullable=False,
                                        server_default='false',
                                        comment='True if this session was auto-generated from tournament type config'))
    op.add_column('sessions', sa.Column('tournament_phase', sa.String(length=50), nullable=True,
                                        comment="Tournament phase: 'Group Stage', 'Knockout Stage', 'Finals'"))
    op.add_column('sessions', sa.Column('tournament_round', sa.Integer(), nullable=True,
                                        comment='Round number within the tournament (1, 2, 3, ...)'))
    op.add_column('sessions', sa.Column('tournament_match_number', sa.Integer(), nullable=True,
                                        comment='Match number within the round (1, 2, 3, ...)'))


def downgrade() -> None:
    # Remove session metadata fields
    op.drop_column('sessions', 'tournament_match_number')
    op.drop_column('sessions', 'tournament_round')
    op.drop_column('sessions', 'tournament_phase')
    op.drop_column('sessions', 'auto_generated')

    # Remove semester tracking fields
    op.drop_column('semesters', 'sessions_generated_at')
    op.drop_column('semesters', 'sessions_generated')

    # Remove FK and column
    op.drop_constraint('fk_semesters_tournament_type_id', 'semesters', type_='foreignkey')
    op.drop_column('semesters', 'tournament_type_id')

    # Drop tournament_types table
    op.drop_index('ix_tournament_types_code', 'tournament_types')
    op.drop_index('ix_tournament_types_id', 'tournament_types')
    op.drop_table('tournament_types')