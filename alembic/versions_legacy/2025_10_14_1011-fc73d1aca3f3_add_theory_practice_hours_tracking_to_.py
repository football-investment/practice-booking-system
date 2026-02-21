"""add_theory_practice_hours_tracking_to_specialization_progress

Revision ID: fc73d1aca3f3
Revises: 9d6cb6c21651
Create Date: 2025-10-14 10:11:44.116686

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fc73d1aca3f3'
down_revision = '9d6cb6c21651'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add theory_hours_completed and practice_hours_completed columns to specialization_progress table
    op.add_column('specialization_progress',
        sa.Column('theory_hours_completed', sa.Integer(), nullable=False, server_default='0',
                  comment='Completed theory hours for COACH specialization'))
    op.add_column('specialization_progress',
        sa.Column('practice_hours_completed', sa.Integer(), nullable=False, server_default='0',
                  comment='Completed practice hours for COACH specialization'))


def downgrade() -> None:
    # Remove theory/practice hours tracking columns
    op.drop_column('specialization_progress', 'practice_hours_completed')
    op.drop_column('specialization_progress', 'theory_hours_completed')