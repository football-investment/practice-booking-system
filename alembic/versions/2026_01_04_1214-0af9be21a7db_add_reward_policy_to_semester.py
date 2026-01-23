"""add_reward_policy_to_semester

Revision ID: 0af9be21a7db
Revises: 7cba9938911d
Create Date: 2026-01-04 12:14:15.102105

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '0af9be21a7db'
down_revision = '7cba9938911d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add reward_policy_name column (String, defaults to 'default')
    op.add_column('semesters', sa.Column(
        'reward_policy_name',
        sa.String(length=100),
        nullable=True,
        server_default='default',
        comment='Name of the reward policy applied to this tournament semester'
    ))

    # Add reward_policy_snapshot column (JSONB, nullable - will be populated at tournament creation)
    op.add_column('semesters', sa.Column(
        'reward_policy_snapshot',
        JSONB,
        nullable=True,
        comment='Immutable snapshot of the reward policy at tournament creation time'
    ))

    # Set default value for existing rows
    op.execute("UPDATE semesters SET reward_policy_name = 'default' WHERE reward_policy_name IS NULL")

    # Make reward_policy_name non-nullable after setting defaults
    op.alter_column('semesters', 'reward_policy_name', nullable=False)


def downgrade() -> None:
    # Remove the columns
    op.drop_column('semesters', 'reward_policy_snapshot')
    op.drop_column('semesters', 'reward_policy_name')