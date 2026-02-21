"""create_skill_rewards_table

Revision ID: 831da85c3ff5
Revises: d1e2f3a4b5c6
Create Date: 2026-02-01 14:13:06.297501

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '831da85c3ff5'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create skill_rewards table
    # Purpose: Persist skill point rewards from tournaments and training sessions
    # Separation of concerns: FootballSkillAssessment = measurements, SkillReward = auditable events
    op.create_table(
        'skill_rewards',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(length=20), nullable=False),  # 'TOURNAMENT' or 'TRAINING'
        sa.Column('source_id', sa.Integer(), nullable=False),  # tournament_id or training_id
        sa.Column('skill_name', sa.String(length=50), nullable=False),
        sa.Column('points_awarded', sa.Integer(), nullable=False),  # Can be positive or negative
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for performance
    op.create_index('ix_skill_rewards_user_id', 'skill_rewards', ['user_id'])
    op.create_index('ix_skill_rewards_source', 'skill_rewards', ['source_type', 'source_id'])
    op.create_index('ix_skill_rewards_created_at', 'skill_rewards', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_skill_rewards_created_at', 'skill_rewards')
    op.drop_index('ix_skill_rewards_source', 'skill_rewards')
    op.drop_index('ix_skill_rewards_user_id', 'skill_rewards')

    # Drop table
    op.drop_table('skill_rewards')