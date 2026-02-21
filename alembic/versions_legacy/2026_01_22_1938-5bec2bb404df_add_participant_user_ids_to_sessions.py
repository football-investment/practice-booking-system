"""add_participant_user_ids_to_sessions

Revision ID: 5bec2bb404df
Revises: 98e008cea123
Create Date: 2026-01-22 19:38:07.204840

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5bec2bb404df'
down_revision = '98e008cea123'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add participant_user_ids column to sessions table for explicit match participant tracking.

    This fixes the architectural issue where match participants were determined at runtime
    by filtering logic. Now, match participants are explicitly defined at session creation time.
    """
    # Add participant_user_ids column (nullable for backward compatibility with existing data)
    op.add_column('sessions', sa.Column(
        'participant_user_ids',
        sa.ARRAY(sa.Integer),
        nullable=True,
        comment='Explicit list of user_ids participating in THIS MATCH (not tournament-wide)'
    ))


def downgrade() -> None:
    """Remove participant_user_ids column"""
    op.drop_column('sessions', 'participant_user_ids')