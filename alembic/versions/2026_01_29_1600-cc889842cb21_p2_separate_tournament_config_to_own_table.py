"""p2_separate_tournament_config_to_own_table

Revision ID: cc889842cb21
Revises: 82956292b4e4
Create Date: 2026-01-29 16:00:00.000000

P2 Refactoring: Separate tournament configuration to own table
===============================================================

Goal: Clean separation of concerns - Tournament configuration as separate entity

BEFORE (Semester model):
- tournament_type_id: FK column
- participant_type, is_multi_day, max_players: Columns
- match_duration_minutes, break_duration_minutes, parallel_fields: Columns
- scoring_type, measurement_unit, ranking_direction, number_of_rounds: Columns
- assignment_type: Column
- sessions_generated, sessions_generated_at, enrollment_snapshot: Columns

AFTER:
- TournamentConfiguration table with FK to semesters
- Semester.tournament_config_obj: relationship (1:1)
- Semester properties: @property (backward compatible)

Benefits:
✅ Clean layer separation (Tournament Info vs Configuration)
✅ Auditability (track configuration changes over time)
✅ Flexibility (configuration can be changed without affecting tournament info)
✅ Clarity (configuration logic isolated from tournament information)

Migration Strategy:
1. Create tournament_configurations table
2. Migrate existing data from semesters table
3. Drop old columns from semesters table
4. Backward compatibility via @property in Semester model

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'cc889842cb21'
down_revision = '82956292b4e4'  # P1 migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    P2: Separate tournament configuration to own table.

    Steps:
    1. Create tournament_configurations table
    2. Migrate existing data
    3. Drop old columns from semesters
    """

    # ========================================================================
    # STEP 1: Create tournament_configurations table
    # ========================================================================
    op.create_table(
        'tournament_configurations',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('semester_id', sa.Integer(), nullable=False),
        sa.Column('tournament_type_id', sa.Integer(), nullable=True),
        sa.Column('participant_type', sa.String(50), nullable=False, server_default='INDIVIDUAL'),
        sa.Column('is_multi_day', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('max_players', sa.Integer(), nullable=True),
        sa.Column('match_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('break_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('parallel_fields', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('scoring_type', sa.String(50), nullable=False, server_default='PLACEMENT'),
        sa.Column('measurement_unit', sa.String(50), nullable=True),
        sa.Column('ranking_direction', sa.String(10), nullable=True),
        sa.Column('number_of_rounds', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('assignment_type', sa.String(30), nullable=True),
        sa.Column('sessions_generated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sessions_generated_at', sa.DateTime(), nullable=True),
        sa.Column('enrollment_snapshot', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tournament_type_id'], ['tournament_types.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('semester_id', name='uq_tournament_configurations_semester_id')
    )

    # Create indexes
    op.create_index(
        'ix_tournament_configurations_id',
        'tournament_configurations',
        ['id'],
        unique=False
    )
    op.create_index(
        'ix_tournament_configurations_semester_id',
        'tournament_configurations',
        ['semester_id'],
        unique=True
    )
    op.create_index(
        'ix_tournament_configurations_tournament_type_id',
        'tournament_configurations',
        ['tournament_type_id'],
        unique=False
    )

    # ========================================================================
    # STEP 2: Migrate existing data from semesters to tournament_configurations
    # ========================================================================
    # Migrate all semesters that have tournament configuration data
    op.execute("""
        INSERT INTO tournament_configurations (
            semester_id, tournament_type_id, participant_type, is_multi_day,
            max_players, match_duration_minutes, break_duration_minutes,
            parallel_fields, scoring_type, measurement_unit, ranking_direction,
            number_of_rounds, assignment_type, sessions_generated,
            sessions_generated_at, enrollment_snapshot, created_at, updated_at
        )
        SELECT
            id,
            tournament_type_id,
            COALESCE(participant_type, 'INDIVIDUAL'),
            COALESCE(is_multi_day, false),
            max_players,
            match_duration_minutes,
            break_duration_minutes,
            COALESCE(parallel_fields, 1),
            COALESCE(scoring_type, 'PLACEMENT'),
            measurement_unit,
            ranking_direction,
            COALESCE(number_of_rounds, 1),
            assignment_type,
            COALESCE(sessions_generated, false),
            sessions_generated_at,
            enrollment_snapshot,
            COALESCE(created_at, now()),
            COALESCE(updated_at, now())
        FROM semesters
        WHERE tournament_type_id IS NOT NULL
           OR max_players IS NOT NULL
           OR sessions_generated = true
    """)

    # ========================================================================
    # STEP 3: Drop old columns from semesters
    # ========================================================================
    # Drop foreign key constraint first
    op.drop_constraint('semesters_tournament_type_id_fkey', 'semesters', type_='foreignkey')

    # Drop indexes (if they exist)
    try:
        op.drop_index('ix_semesters_tournament_type_id', table_name='semesters')
    except:
        pass  # Index might not exist

    # Drop columns
    op.drop_column('semesters', 'tournament_type_id')
    op.drop_column('semesters', 'participant_type')
    op.drop_column('semesters', 'is_multi_day')
    op.drop_column('semesters', 'max_players')
    op.drop_column('semesters', 'match_duration_minutes')
    op.drop_column('semesters', 'break_duration_minutes')
    op.drop_column('semesters', 'parallel_fields')
    op.drop_column('semesters', 'scoring_type')
    op.drop_column('semesters', 'measurement_unit')
    op.drop_column('semesters', 'ranking_direction')
    op.drop_column('semesters', 'number_of_rounds')
    op.drop_column('semesters', 'assignment_type')
    op.drop_column('semesters', 'sessions_generated')
    op.drop_column('semesters', 'sessions_generated_at')
    op.drop_column('semesters', 'enrollment_snapshot')


def downgrade() -> None:
    """
    Rollback P2: Restore tournament configuration columns to semesters table.

    Steps:
    1. Re-add columns to semesters
    2. Migrate data back from tournament_configurations
    3. Drop tournament_configurations table
    """

    # ========================================================================
    # STEP 1: Re-add columns to semesters
    # ========================================================================
    op.add_column('semesters', sa.Column('tournament_type_id', sa.Integer(), nullable=True))
    op.add_column('semesters', sa.Column('participant_type', sa.String(50), nullable=True, server_default='INDIVIDUAL'))
    op.add_column('semesters', sa.Column('is_multi_day', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('semesters', sa.Column('max_players', sa.Integer(), nullable=True))
    op.add_column('semesters', sa.Column('match_duration_minutes', sa.Integer(), nullable=True))
    op.add_column('semesters', sa.Column('break_duration_minutes', sa.Integer(), nullable=True))
    op.add_column('semesters', sa.Column('parallel_fields', sa.Integer(), nullable=True, server_default='1'))
    op.add_column('semesters', sa.Column('scoring_type', sa.String(50), nullable=False, server_default='PLACEMENT'))
    op.add_column('semesters', sa.Column('measurement_unit', sa.String(50), nullable=True))
    op.add_column('semesters', sa.Column('ranking_direction', sa.String(10), nullable=True))
    op.add_column('semesters', sa.Column('number_of_rounds', sa.Integer(), nullable=True, server_default='1'))
    op.add_column('semesters', sa.Column('assignment_type', sa.String(30), nullable=True))
    op.add_column('semesters', sa.Column('sessions_generated', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('semesters', sa.Column('sessions_generated_at', sa.DateTime(), nullable=True))
    op.add_column('semesters', sa.Column('enrollment_snapshot', postgresql.JSONB, nullable=True))

    # Recreate FK
    op.create_foreign_key(
        'fk_semesters_tournament_type_id',
        'semesters', 'tournament_types',
        ['tournament_type_id'], ['id'],
        ondelete='SET NULL'
    )

    # Recreate index
    op.create_index('ix_semesters_tournament_type_id', 'semesters', ['tournament_type_id'], unique=False)

    # ========================================================================
    # STEP 2: Migrate data back to semesters
    # ========================================================================
    op.execute("""
        UPDATE semesters s
        SET
            tournament_type_id = tc.tournament_type_id,
            participant_type = tc.participant_type,
            is_multi_day = tc.is_multi_day,
            max_players = tc.max_players,
            match_duration_minutes = tc.match_duration_minutes,
            break_duration_minutes = tc.break_duration_minutes,
            parallel_fields = tc.parallel_fields,
            scoring_type = tc.scoring_type,
            measurement_unit = tc.measurement_unit,
            ranking_direction = tc.ranking_direction,
            number_of_rounds = tc.number_of_rounds,
            assignment_type = tc.assignment_type,
            sessions_generated = tc.sessions_generated,
            sessions_generated_at = tc.sessions_generated_at,
            enrollment_snapshot = tc.enrollment_snapshot
        FROM tournament_configurations tc
        WHERE s.id = tc.semester_id
    """)

    # ========================================================================
    # STEP 3: Drop tournament_configurations table
    # ========================================================================
    op.drop_index('ix_tournament_configurations_tournament_type_id', table_name='tournament_configurations')
    op.drop_index('ix_tournament_configurations_semester_id', table_name='tournament_configurations')
    op.drop_index('ix_tournament_configurations_id', table_name='tournament_configurations')
    op.drop_table('tournament_configurations')
