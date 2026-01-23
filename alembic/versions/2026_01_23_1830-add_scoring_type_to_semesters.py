"""add_scoring_type_to_semesters

Revision ID: add_scoring_type_002
Revises: add_format_to_semesters_001
Create Date: 2026-01-23 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_scoring_type_002'
down_revision = 'add_format_to_semesters_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add scoring_type column to semesters table
    # Default to PLACEMENT for backward compatibility
    op.add_column('semesters', sa.Column('scoring_type', sa.String(length=50), nullable=False, server_default='PLACEMENT'))


def downgrade() -> None:
    # Remove scoring_type column from semesters
    op.drop_column('semesters', 'scoring_type')
