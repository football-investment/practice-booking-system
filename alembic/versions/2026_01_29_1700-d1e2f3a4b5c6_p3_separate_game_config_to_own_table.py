"""p3_separate_game_config_to_own_table

Revision ID: d1e2f3a4b5c6
Revises: cc889842cb21
Create Date: 2026-01-29 17:00:00.000000

P3 Refactoring: Separate game configuration to own table
=========================================================

Goal: Clean separation of concerns - Game configuration as separate entity

BEFORE (Semester model):
- game_preset_id: FK column
- game_config: JSONB column
- game_config_overrides: JSONB column

AFTER:
- GameConfiguration table with FK to semesters
- Semester.game_config_obj: relationship (1:1)
- Semester properties: @property (backward compatible)

Benefits:
✅ Clean layer separation (Tournament Info vs Game Configuration)
✅ Auditability (track game config changes over time)
✅ Flexibility (game config can be changed without affecting tournament info)
✅ Clarity (game simulation logic isolated from tournament information)

Migration Strategy:
1. Create game_configurations table
2. Migrate existing data from semesters table
3. Drop old columns from semesters table
4. Backward compatibility via @property in Semester model

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd1e2f3a4b5c6'
down_revision = 'cc889842cb21'  # P2 migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    P3: Separate game configuration to own table.

    Steps:
    1. Create game_configurations table
    2. Migrate existing data
    3. Drop old columns from semesters
    """

    # ========================================================================
    # STEP 1: Create game_configurations table
    # ========================================================================
    op.create_table(
        'game_configurations',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('semester_id', sa.Integer(), nullable=False),
        sa.Column('game_preset_id', sa.Integer(), nullable=True),
        sa.Column('game_config', postgresql.JSONB, nullable=True),
        sa.Column('game_config_overrides', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['game_preset_id'], ['game_presets.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('semester_id', name='uq_game_configurations_semester_id')
    )

    # Create indexes
    op.create_index(
        'ix_game_configurations_id',
        'game_configurations',
        ['id'],
        unique=False
    )
    op.create_index(
        'ix_game_configurations_semester_id',
        'game_configurations',
        ['semester_id'],
        unique=True
    )
    op.create_index(
        'ix_game_configurations_game_preset_id',
        'game_configurations',
        ['game_preset_id'],
        unique=False
    )

    # ========================================================================
    # STEP 2: Migrate existing data from semesters to game_configurations
    # ========================================================================
    # Migrate all semesters that have game configuration data
    op.execute("""
        INSERT INTO game_configurations (
            semester_id, game_preset_id, game_config, game_config_overrides,
            created_at, updated_at
        )
        SELECT
            id,
            game_preset_id,
            game_config,
            game_config_overrides,
            COALESCE(created_at, now()),
            COALESCE(updated_at, now())
        FROM semesters
        WHERE game_preset_id IS NOT NULL
           OR game_config IS NOT NULL
           OR game_config_overrides IS NOT NULL
    """)

    # ========================================================================
    # STEP 3: Drop old columns from semesters
    # ========================================================================
    # Drop foreign key constraint first
    op.drop_constraint('fk_semesters_game_preset', 'semesters', type_='foreignkey')

    # Drop indexes (if they exist)
    try:
        op.drop_index('ix_semesters_game_preset_id', table_name='semesters')
    except:
        pass  # Index might not exist

    try:
        op.drop_index('ix_semesters_game_config_overrides', table_name='semesters')
    except:
        pass  # Index might not exist

    # Drop columns
    op.drop_column('semesters', 'game_preset_id')
    op.drop_column('semesters', 'game_config')
    op.drop_column('semesters', 'game_config_overrides')


def downgrade() -> None:
    """
    Rollback P3: Restore game configuration columns to semesters table.

    Steps:
    1. Re-add columns to semesters
    2. Migrate data back from game_configurations
    3. Drop game_configurations table
    """

    # ========================================================================
    # STEP 1: Re-add columns to semesters
    # ========================================================================
    op.add_column('semesters', sa.Column('game_preset_id', sa.Integer(), nullable=True))
    op.add_column('semesters', sa.Column('game_config', postgresql.JSONB, nullable=True))
    op.add_column('semesters', sa.Column('game_config_overrides', postgresql.JSONB, nullable=True))

    # Recreate FK
    op.create_foreign_key(
        'fk_semesters_game_preset',
        'semesters', 'game_presets',
        ['game_preset_id'], ['id'],
        ondelete='SET NULL'
    )

    # Recreate indexes
    op.create_index('ix_semesters_game_preset_id', 'semesters', ['game_preset_id'], unique=False)
    op.create_index('ix_semesters_game_config_overrides', 'semesters', ['game_config_overrides'], unique=False)

    # ========================================================================
    # STEP 2: Migrate data back to semesters
    # ========================================================================
    op.execute("""
        UPDATE semesters s
        SET
            game_preset_id = gc.game_preset_id,
            game_config = gc.game_config,
            game_config_overrides = gc.game_config_overrides
        FROM game_configurations gc
        WHERE s.id = gc.semester_id
    """)

    # ========================================================================
    # STEP 3: Drop game_configurations table
    # ========================================================================
    op.drop_index('ix_game_configurations_game_preset_id', table_name='game_configurations')
    op.drop_index('ix_game_configurations_semester_id', table_name='game_configurations')
    op.drop_index('ix_game_configurations_id', table_name='game_configurations')
    op.drop_table('game_configurations')
