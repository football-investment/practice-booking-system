"""add_format_to_semesters

Revision ID: add_format_to_semesters_001
Revises: ce946116d053
Create Date: 2026-01-23 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_format_to_semesters_001'
down_revision = 'ce946116d053'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add format column to semesters table
    # Default to INDIVIDUAL_RANKING for backward compatibility
    op.add_column('semesters', sa.Column('format', sa.String(length=50), nullable=False, server_default='INDIVIDUAL_RANKING'))


def downgrade() -> None:
    # Remove format column from semesters
    op.drop_column('semesters', 'format')
