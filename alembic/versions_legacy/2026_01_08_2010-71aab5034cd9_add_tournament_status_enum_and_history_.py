"""add_tournament_status_enum_and_history_table

Revision ID: 71aab5034cd9
Revises: 1de1b6240676
Create Date: 2026-01-08 20:10:11.787816

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '71aab5034cd9'
down_revision = '1de1b6240676'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create tournament_status enum type
    op.execute("""
        CREATE TYPE tournament_status AS ENUM (
            'DRAFT',
            'SEEKING_INSTRUCTOR',
            'PENDING_INSTRUCTOR_ACCEPTANCE',
            'READY_FOR_ENROLLMENT',
            'ENROLLMENT_OPEN',
            'ENROLLMENT_CLOSED',
            'IN_PROGRESS',
            'COMPLETED',
            'REWARDS_DISTRIBUTED',
            'CANCELLED',
            'ARCHIVED'
        )
    """)

    # 2. Add tournament_status column to semesters table (nullable for existing records)
    op.add_column('semesters', sa.Column('tournament_status', sa.Enum(
        'DRAFT',
        'SEEKING_INSTRUCTOR',
        'PENDING_INSTRUCTOR_ACCEPTANCE',
        'READY_FOR_ENROLLMENT',
        'ENROLLMENT_OPEN',
        'ENROLLMENT_CLOSED',
        'IN_PROGRESS',
        'COMPLETED',
        'REWARDS_DISTRIBUTED',
        'CANCELLED',
        'ARCHIVED',
        name='tournament_status'
    ), nullable=True))

    # 3. Create tournament_status_history table for audit trail
    op.create_table(
        'tournament_status_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tournament_id', sa.Integer(), nullable=False),
        sa.Column('old_status', sa.String(50), nullable=True),  # NULL for creation
        sa.Column('new_status', sa.String(50), nullable=False),
        sa.Column('changed_by', sa.Integer(), nullable=False),
        sa.Column('changed_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tournament_id'], ['semesters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'])
    )

    # 4. Create indexes for performance
    op.create_index('ix_tournament_status_history_tournament_id', 'tournament_status_history', ['tournament_id'])
    op.create_index('ix_tournament_status_history_changed_at', 'tournament_status_history', ['changed_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_tournament_status_history_changed_at', table_name='tournament_status_history')
    op.drop_index('ix_tournament_status_history_tournament_id', table_name='tournament_status_history')

    # Drop history table
    op.drop_table('tournament_status_history')

    # Drop status column from semesters
    op.drop_column('semesters', 'tournament_status')

    # Drop enum type
    op.execute('DROP TYPE tournament_status')