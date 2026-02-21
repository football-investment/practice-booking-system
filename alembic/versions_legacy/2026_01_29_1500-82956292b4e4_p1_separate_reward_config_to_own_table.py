"""p1_separate_reward_config_to_own_table

Revision ID: 82956292b4e4
Revises: 562a39020263
Create Date: 2026-01-29 15:00:00.000000

P1 Refactoring: Separate reward_config to own table
====================================================

Goal: Clean separation of concerns - Reward configuration as separate entity

BEFORE (Semester model):
- reward_policy_name: String column
- reward_policy_snapshot: JSONB column
- reward_config: JSONB column

AFTER:
- TournamentRewardConfig table with FK to semesters
- Semester.reward_config_obj: relationship (1:1)
- Semester.reward_config: @property (backward compatible)

Benefits:
✅ Clean layer separation (Tournament Info → Config → Game Config → Reward Config)
✅ Auditability (track reward changes over time)
✅ Reusability (future: share reward policies across tournaments)
✅ Clarity (reward logic isolated from tournament configuration)

Migration Strategy:
1. Create tournament_reward_configs table
2. Migrate existing data from semesters table
3. Drop old columns from semesters table
4. Backward compatibility via @property in Semester model

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime, timezone

# revision identifiers, used by Alembic.
revision = '82956292b4e4'
down_revision = '562a39020263'  # P0.2 migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    P1: Separate reward_config to own table.

    Steps:
    1. Create tournament_reward_configs table
    2. Migrate existing data
    3. Drop old columns from semesters
    """

    # ========================================================================
    # STEP 1: Create tournament_reward_configs table
    # ========================================================================
    op.create_table(
        'tournament_reward_configs',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('semester_id', sa.Integer(), nullable=False),
        sa.Column('reward_policy_name', sa.String(100), nullable=False, server_default='default'),
        sa.Column('reward_policy_snapshot', postgresql.JSONB, nullable=True),
        sa.Column('reward_config', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('semester_id', name='uq_tournament_reward_configs_semester_id')
    )

    # Create indexes
    op.create_index(
        'ix_tournament_reward_configs_id',
        'tournament_reward_configs',
        ['id'],
        unique=False
    )
    op.create_index(
        'ix_tournament_reward_configs_semester_id',
        'tournament_reward_configs',
        ['semester_id'],
        unique=True
    )

    # ========================================================================
    # STEP 2: Migrate existing data from semesters to tournament_reward_configs
    # ========================================================================
    # Only migrate semesters that have reward_config data
    op.execute("""
        INSERT INTO tournament_reward_configs (semester_id, reward_policy_name, reward_policy_snapshot, reward_config, created_at, updated_at)
        SELECT
            id,
            COALESCE(reward_policy_name, 'default'),
            reward_policy_snapshot,
            reward_config,
            COALESCE(created_at, now()),
            COALESCE(updated_at, now())
        FROM semesters
        WHERE reward_config IS NOT NULL
           OR reward_policy_snapshot IS NOT NULL
           OR reward_policy_name IS NOT NULL
    """)

    # ========================================================================
    # STEP 3: Drop old columns from semesters
    # ========================================================================
    # Drop index first (if exists)
    op.drop_index('ix_semesters_reward_config', table_name='semesters')

    # Drop columns
    op.drop_column('semesters', 'reward_config')
    op.drop_column('semesters', 'reward_policy_snapshot')
    op.drop_column('semesters', 'reward_policy_name')


def downgrade() -> None:
    """
    Rollback P1: Restore reward_config columns to semesters table.

    Steps:
    1. Re-add columns to semesters
    2. Migrate data back from tournament_reward_configs
    3. Drop tournament_reward_configs table
    """

    # ========================================================================
    # STEP 1: Re-add columns to semesters
    # ========================================================================
    op.add_column('semesters', sa.Column('reward_policy_name', sa.String(100), nullable=False, server_default='default'))
    op.add_column('semesters', sa.Column('reward_policy_snapshot', postgresql.JSONB, nullable=True))
    op.add_column('semesters', sa.Column('reward_config', postgresql.JSONB, nullable=True))

    # Recreate index
    op.create_index(
        'ix_semesters_reward_config',
        'semesters',
        ['reward_config'],
        postgresql_using='gin',
        unique=False
    )

    # ========================================================================
    # STEP 2: Migrate data back to semesters
    # ========================================================================
    op.execute("""
        UPDATE semesters s
        SET
            reward_policy_name = trc.reward_policy_name,
            reward_policy_snapshot = trc.reward_policy_snapshot,
            reward_config = trc.reward_config
        FROM tournament_reward_configs trc
        WHERE s.id = trc.semester_id
    """)

    # ========================================================================
    # STEP 3: Drop tournament_reward_configs table
    # ========================================================================
    op.drop_index('ix_tournament_reward_configs_semester_id', table_name='tournament_reward_configs')
    op.drop_index('ix_tournament_reward_configs_id', table_name='tournament_reward_configs')
    op.drop_table('tournament_reward_configs')
